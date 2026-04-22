"""HaruSpeak backend entry point."""
from __future__ import annotations

import asyncio
import base64
import logging
import sys
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Windows: force ProactorEventLoopPolicy so asyncio.subprocess works.
# Some libs (aiohttp via edge-tts) may otherwise flip to Selector policy,
# which raises NotImplementedError on create_subprocess_exec.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Make app-level loggers actually print. Python's default level is WARNING,
# which would swallow the [llm] / [settings] traces we rely on for debugging.
# We also mirror to a tiny ring-buffer file (last 30 entries only) under
# logs/ so you can grep the most recent session without the file growing
# unbounded.
import os as _os  # noqa: E402

_LOG_DIR = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "logs")
_os.makedirs(_LOG_DIR, exist_ok=True)


class _RingFileHandler(logging.Handler):
    """File handler that retains only the last N formatted records.

    Simpler than any rotating handler — on every emit, we append the new
    line and truncate the head so the file always contains <= max_lines.
    Overkill for a high-traffic server; fine for a single-process local app.
    """

    def __init__(self, filename: str, max_lines: int = 30, encoding: str = "utf-8") -> None:
        super().__init__()
        self.filename = filename
        self.max_lines = max_lines
        self.encoding = encoding

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record) + "\n"
            lines: list[str] = []
            try:
                with open(self.filename, "r", encoding=self.encoding) as f:
                    lines = f.readlines()
            except FileNotFoundError:
                pass
            lines.append(msg)
            if len(lines) > self.max_lines:
                lines = lines[-self.max_lines:]
            with open(self.filename, "w", encoding=self.encoding) as f:
                f.writelines(lines)
        except Exception:
            self.handleError(record)


_fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", "%H:%M:%S")
_console = logging.StreamHandler()
_console.setFormatter(_fmt)
_file = _RingFileHandler(_os.path.join(_LOG_DIR, "backend.log"), max_lines=30)
_file.setFormatter(_fmt)

_root = logging.getLogger()
_root.setLevel(logging.INFO)
# Replace any handlers uvicorn/pytest may have installed so we don't double-print.
_root.handlers = [_console, _file]

from . import languages  # noqa: F401  — triggers ja import & registration
from .config import settings
from .languages import list_languages, get_language, register_language
from .languages.registry import ensure_loaded
from .llm import make_llm
from .pipeline.conversation import ConversationPipeline
from .scenes.loader import load_all, load_one
from .stt import make_stt


# Singleton STT. Constructed instantly; its heavy model weights load
# asynchronously in the background so the HTTP server can start serving
# lightweight endpoints (/api/languages, /api/scenes, /healthz) in ~0.5s.
_STT_SINGLETON = None
_STT_READY_EVENT: asyncio.Event | None = None


async def _warm_stt() -> None:
    """Background task: pull model weights into RAM so the first user turn is fast."""
    global _STT_SINGLETON
    print(f"[warmup] loading STT backend: {settings.stt_provider}")
    t0 = time.time()
    _STT_SINGLETON = make_stt(settings)
    loader = getattr(_STT_SINGLETON, "_load", None)
    if callable(loader):
        try:
            await asyncio.get_event_loop().run_in_executor(None, loader)
        except Exception as e:
            print(f"[warmup] STT load failed: {e}")
    print(f"[warmup] STT ready in {time.time() - t0:.1f}s")
    if _STT_READY_EVENT is not None:
        _STT_READY_EVENT.set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _STT_READY_EVENT
    _STT_READY_EVENT = asyncio.Event()
    # Fire and forget — HTTP server starts accepting connections immediately,
    # STT quietly loads in the background.
    asyncio.create_task(_warm_stt())
    yield
    print("[shutdown] bye")


app = FastAPI(title="HaruSpeak", version="0.1.0", lifespan=lifespan)

from .api.settings import router as settings_router  # noqa: E402
from .api.stt_models import router as stt_models_router  # noqa: E402
app.include_router(settings_router)
app.include_router(stt_models_router)

app.add_middleware(
    CORSMiddleware,
    # Use regex so LAN-IP origins work from mobile devices too.
    # Covers http://localhost, http://127.*, http://192.168.*, http://10.*
    allow_origin_regex=r"https?://(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.).*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Import language modules (they self-register). zh/en stubs raise at call time,
# but we still want them discoverable in the UI so users see a "coming soon" state.
ensure_loaded(["ja", "zh", "en"])


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    """Health probe — also reports whether STT weights finished loading
    so the UI can show a "loading…" state instead of freezing on the first
    user turn while the model is still being pulled into RAM.
    """
    stt_ready = bool(_STT_READY_EVENT is not None and _STT_READY_EVENT.is_set())
    return {"status": "ok", "stt_ready": stt_ready}


@app.get("/api/languages")
def get_languages() -> dict[str, Any]:
    """Return metadata about all registered languages."""
    out = []
    for code in list_languages():
        lang = get_language(code)
        out.append(
            {
                "code": code,
                "display_names": lang.display_names,
                "unit_kind": lang.unit_kind,
                "implemented": True,
            }
        )
    return {"languages": out}


@app.get("/api/scenes")
def get_scenes(l2: str) -> dict[str, Any]:
    if l2 not in list_languages():
        raise HTTPException(status_code=404, detail=f"L2 '{l2}' not found")
    return {"scenes": load_all(l2)}


@app.get("/api/personas")
def get_personas(l2: str) -> dict[str, Any]:
    from .personas.loader import list_personas
    if l2 not in list_languages():
        raise HTTPException(status_code=404, detail=f"L2 '{l2}' not found")
    return {"personas": list_personas(l2)}


class AnnotateRequest(BaseModel):
    text: str
    language: str


@app.post("/api/annotate")
def annotate_endpoint(req: AnnotateRequest) -> dict[str, Any]:
    try:
        lang = get_language(req.language)
        return lang.annotate(req.text).model_dump()
    except NotImplementedError:
        raise HTTPException(status_code=501, detail=f"Language '{req.language}' not yet implemented")
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -------- WebSocket conversation --------


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    await ws.accept()

    # First message: JSON with {l1, l2, scene_id, level, custom_scene?, persona_override?}
    # custom_scene shape: {title, description, persona?, opening_line?}
    # persona_override shape: {id?, name?, description?} — at minimum a descriptive string
    init = await ws.receive_json()
    l1 = init.get("l1", "zh")
    l2 = init.get("l2", "ja")
    scene_id = init.get("scene_id", "restaurant")
    level = init.get("level", "B1")
    custom_scene = init.get("custom_scene")
    persona_override = init.get("persona_override")
    logging.getLogger(__name__).info(
        "[ws] chat start  l1=%s l2=%s scene=%s custom=%s persona_override=%s  provider=%s openai_model=%r lmstudio_model=%r",
        l1, l2, scene_id, bool(custom_scene), bool(persona_override),
        settings.llm_provider, settings.openai_model, settings.lmstudio_model,
    )

    if custom_scene and isinstance(custom_scene, dict):
        scene = {
            "id": "__custom__",
            "title": custom_scene.get("title") or "Custom",
            "description": custom_scene.get("description") or "",
            "persona": custom_scene.get("persona") or "native speaker",
            "opening_line": custom_scene.get("opening_line") or "",
        }
    else:
        scene = load_one(scene_id, l2) or {"id": scene_id, "title": "Custom", "description": ""}

    # Wait for the background warmup to finish (no-op if already done).
    if _STT_READY_EVENT is not None and not _STT_READY_EVENT.is_set():
        await _STT_READY_EVENT.wait()
    stt = _STT_SINGLETON or make_stt(settings)
    llm = make_llm(settings)

    # Persona resolution priority:
    #   1. persona_override from client (library pick or user-typed custom)
    #   2. scene's own persona field
    if persona_override and isinstance(persona_override, dict):
        pieces = [
            persona_override.get("name"),
            persona_override.get("description"),
            persona_override.get("tone_hint"),
        ]
        persona = " — ".join(p for p in pieces if p) or "native speaker"
    else:
        persona = scene.get("persona")
        if isinstance(persona, dict):
            persona = persona.get(l2) or persona.get("en") or "native speaker"

    pipeline = ConversationPipeline(
        stt=stt,
        llm=llm,
        l1=l1,
        l2=l2,
        scene=_flatten_scene(scene, l2),
        level=level,
        persona=persona or "native speaker",
    )

    # Send opening line immediately (text + TTS + translation + suggestions)
    opening = scene.get("opening_line", "")
    if isinstance(opening, dict):
        opening = opening.get(l2, "")
    if opening:
        import asyncio as _asyncio

        lang = get_language(l2)
        annotated = lang.annotate(opening)
        audio_bytes, translation, suggestions = await _asyncio.gather(
            lang.tts_reference(opening),
            pipeline._translate(opening),
            pipeline.generate_suggestions(opening),
        )
        await ws.send_json(
            {
                "type": "ai_turn",
                "text": opening,
                "annotated": annotated.model_dump(),
                "translation": translation,
                "audio_mime": "audio/mpeg" if audio_bytes else None,
                "audio_b64": base64.b64encode(audio_bytes).decode("ascii") if audio_bytes else None,
                "suggestions": [s.model_dump() for s in suggestions],
            }
        )

    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break

            # Client sends: {"audio_b64": "...", "done": true}
            if "text" not in msg or msg["text"] is None:
                continue
            payload = _parse_json_safe(msg["text"])
            audio_b64 = payload.get("audio_b64", "")
            if not audio_b64:
                continue
            audio_bytes = base64.b64decode(audio_b64)

            async def _emit(event_type: str, payload: dict) -> None:
                await ws.send_json({"type": event_type, **payload})

            try:
                await pipeline.stream_user_turn(audio_bytes, _emit)
            except Exception as e:
                import traceback

                traceback.print_exc()
                await ws.send_json(
                    {"type": "error", "message": f"{type(e).__name__}: {e}"}
                )
                continue
    except WebSocketDisconnect:
        return


def _flatten_scene(scene: dict[str, Any], l2: str) -> dict[str, Any]:
    """Flatten i18n fields in a common scene to the selected L2."""
    out = dict(scene)
    for key in ("title", "titles", "description", "opening_line", "persona"):
        val = out.get(key)
        if isinstance(val, dict):
            out[key] = val.get(l2) or next(iter(val.values()), "")
    return out


def _parse_json_safe(raw: str) -> dict[str, Any]:
    import json

    try:
        return json.loads(raw)
    except Exception:
        return {}
