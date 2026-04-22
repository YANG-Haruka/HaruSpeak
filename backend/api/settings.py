"""Settings API: view / update / probe available providers.

Two providers: OpenAI-compatible and LM Studio (local).
Each keeps its own model field so switching doesn't carry a bogus
model name across.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..config import settings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


# -------- DTOs --------


class SettingsPayload(BaseModel):
    llm_provider: str | None = Field(default=None, description="openai | openai_lmstudio")

    openai_model: str | None = None
    openai_api_base: str | None = None
    openai_api_key: str | None = None

    lmstudio_model: str | None = None
    lmstudio_base: str | None = None

    stt_provider: str | None = Field(default=None, description="sensevoice | faster_whisper | whisper_openai")
    faster_whisper_size: str | None = None
    whisper_model: str | None = None

    tts_voice_ja: str | None = None
    tts_voice_zh: str | None = None
    tts_voice_en: str | None = None


class CurrentSettings(BaseModel):
    llm_provider: str

    openai_model: str
    openai_api_base: str
    openai_api_key: str            # returned in plaintext for local-only UI (eye-toggle)

    lmstudio_model: str
    lmstudio_base: str

    stt_provider: str
    faster_whisper_size: str
    whisper_model: str
    sensevoice_model_path: str
    tts_voice_ja: str
    tts_voice_zh: str
    tts_voice_en: str


# -------- endpoints --------


@router.get("", response_model=CurrentSettings)
def get_settings() -> CurrentSettings:
    return CurrentSettings(
        llm_provider=settings.llm_provider,
        openai_model=settings.openai_model,
        openai_api_base=settings.openai_api_base,
        openai_api_key=settings.openai_api_key,
        lmstudio_model=settings.lmstudio_model,
        lmstudio_base=settings.lmstudio_base,
        stt_provider=settings.stt_provider,
        faster_whisper_size=settings.faster_whisper_size,
        whisper_model=settings.whisper_model,
        sensevoice_model_path=settings.sensevoice_model_path,
        tts_voice_ja=settings.tts_voice_ja,
        tts_voice_zh=settings.tts_voice_zh,
        tts_voice_en=settings.tts_voice_en,
    )


@router.post("")
def update_settings(payload: SettingsPayload) -> dict[str, Any]:
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    # Log what's being saved, but redact the API key so it doesn't leak into logs.
    redacted = {
        k: ("sk-…" + v[-4:] if k == "openai_api_key" and isinstance(v, str) and len(v) > 8 else v)
        for k, v in updates.items()
    }
    log.info("[settings] saving %s", redacted)
    settings.apply_overrides(updates)
    settings.save_overrides()
    log.info("[settings] after save → provider=%s  openai_model=%r  lmstudio_model=%r",
             settings.llm_provider, settings.openai_model, settings.lmstudio_model)
    return {"ok": True, "applied": list(updates.keys())}


async def _probe_lmstudio(base: str) -> tuple[bool, list[str], str | None]:
    """Return (available, model_ids, error_message)."""
    url = f"{base.rstrip('/')}/models"
    try:
        async with httpx.AsyncClient(timeout=2.0) as c:
            r = await c.get(url)
        if r.status_code != 200:
            return False, [], f"HTTP {r.status_code} from {url}"
        data = r.json()
        if not (isinstance(data, dict) and isinstance(data.get("data"), list)):
            return False, [], f"Unexpected response shape from {url}"
        models = [m.get("id", "") for m in data["data"] if isinstance(m, dict)]
        models = [m for m in models if m]
        return True, models, None
    except httpx.ConnectError as e:
        return False, [], f"Cannot connect to {url} — is LM Studio running with its Local Server started? ({e})"
    except httpx.TimeoutException:
        return False, [], f"Timeout connecting to {url}"
    except Exception as e:  # noqa: BLE001 — surface any probe failure to the UI
        return False, [], f"{type(e).__name__}: {e}"


@router.get("/candidates")
async def candidates() -> dict[str, Any]:
    """Return the option space the settings page shows.

    LM Studio models are probed live — the result includes an `error` string
    when unreachable so the UI can surface the actual reason.
    """
    lm_available, lm_models, lm_error = await _probe_lmstudio(settings.lmstudio_base)
    if lm_error:
        log.info("LM Studio probe failed: %s", lm_error)
    else:
        log.info("LM Studio probe ok: %d model(s)", len(lm_models))

    return {
        "llm_providers": [
            {"id": "openai", "name": "OpenAI-compatible"},
            {
                "id": "openai_lmstudio",
                "name": "LM Studio / Ollama (local)",
                "available": lm_available,
                "models": lm_models,
                "error": lm_error,
                "probed_url": f"{settings.lmstudio_base.rstrip('/')}/models",
            },
        ],
        "stt_providers": [
            {"id": "sensevoice",     "name": "SenseVoice-Small (local, 900MB, fast)"},
            {"id": "faster_whisper", "name": "faster-whisper (local)"},
        ],
        "faster_whisper_sizes": [
            "tiny", "base", "small", "medium", "large-v3", "large-v3-turbo",
        ],
        # Frontend looks up `voice_desc_<id>` in its i18n bundle.
        "tts_voices": {
            "ja": [
                {"id": vid, "description_key": f"voice_desc_{vid}"} for vid in (
                    "ja-JP-NanamiNeural", "ja-JP-KeitaNeural",
                    "ja-JP-AoiNeural", "ja-JP-DaichiNeural",
                )
            ],
            "zh": [
                {"id": vid, "description_key": f"voice_desc_{vid}"} for vid in (
                    "zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural",
                    "zh-CN-XiaoyiNeural", "zh-CN-YunjianNeural",
                    "zh-CN-XiaomengNeural", "zh-CN-XiaohanNeural",
                )
            ],
            "en": [
                {"id": vid, "description_key": f"voice_desc_{vid}"} for vid in (
                    "en-US-AriaNeural", "en-US-GuyNeural",
                    "en-US-JennyNeural", "en-US-RyanNeural",
                    "en-GB-SoniaNeural", "en-GB-RyanNeural",
                )
            ],
        },
    }
