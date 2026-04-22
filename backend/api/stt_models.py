"""STT model registry — list/check/download local speech-recognition models.

Models are downloaded into `<repo>/models/<local_dir>/` via
huggingface_hub.snapshot_download. We also accept an install as "already
there" if the model is present in the default HF cache
(`~/.cache/huggingface/hub/models--<owner>--<name>/`) so users who ran
the app before this UI existed don't see false "not installed" states.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stt", tags=["stt"])

# Repo root = parents[2] from backend/api/stt_models.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODELS_ROOT = _REPO_ROOT / "models"


# --- Registry -----------------------------------------------------------------

# (id, provider, faster_whisper_size?, display_name, hf_repo,
#  size_mb, vram_mb, recommended, description)
STT_MODELS: list[dict[str, Any]] = [
    {
        "id": "sensevoice_small",
        "provider": "sensevoice",
        "name": "SenseVoice-Small",
        "hf_repo": "FunAudioLLM/SenseVoiceSmall",
        "local_dir": "sensevoice-small",
        "size_mb": 901,
        "vram_mb": 1024,
        "recommended": True,
        "description": "5x faster than Whisper, best accuracy for JA/ZH/EN. Default choice.",
    },
    {
        "id": "faster_whisper_tiny",
        "provider": "faster_whisper",
        "faster_whisper_size": "tiny",
        "name": "faster-whisper · tiny",
        "hf_repo": "Systran/faster-whisper-tiny",
        "local_dir": "faster-whisper-tiny",
        "size_mb": 78,
        "vram_mb": 1024,
        "description": "Tiny model. Fastest but lowest accuracy. Good for testing.",
    },
    {
        "id": "faster_whisper_base",
        "provider": "faster_whisper",
        "faster_whisper_size": "base",
        "name": "faster-whisper · base",
        "hf_repo": "Systran/faster-whisper-base",
        "local_dir": "faster-whisper-base",
        "size_mb": 148,
        "vram_mb": 1024,
        "description": "Baseline Whisper model. Small footprint, usable accuracy.",
    },
    {
        "id": "faster_whisper_small",
        "provider": "faster_whisper",
        "faster_whisper_size": "small",
        "name": "faster-whisper · small",
        "hf_repo": "Systran/faster-whisper-small",
        "local_dir": "faster-whisper-small",
        "size_mb": 488,
        "vram_mb": 2048,
        "description": "Good balance of speed and accuracy for most users.",
    },
    {
        "id": "faster_whisper_medium",
        "provider": "faster_whisper",
        "faster_whisper_size": "medium",
        "name": "faster-whisper · medium",
        "hf_repo": "Systran/faster-whisper-medium",
        "local_dir": "faster-whisper-medium",
        "size_mb": 1530,
        "vram_mb": 5120,
        "description": "Higher accuracy. Needs ~5 GB VRAM.",
    },
    {
        "id": "faster_whisper_large_v3",
        "provider": "faster_whisper",
        "faster_whisper_size": "large-v3",
        "name": "faster-whisper · large-v3",
        "hf_repo": "Systran/faster-whisper-large-v3",
        "local_dir": "faster-whisper-large-v3",
        "size_mb": 3090,
        "vram_mb": 10240,
        "description": "Highest accuracy. Requires ~10 GB VRAM.",
    },
    {
        "id": "faster_whisper_large_v3_turbo",
        "provider": "faster_whisper",
        "faster_whisper_size": "large-v3-turbo",
        "name": "faster-whisper · large-v3-turbo",
        "hf_repo": "Systran/faster-whisper-large-v3-turbo",
        "local_dir": "faster-whisper-large-v3-turbo",
        "size_mb": 1620,
        "vram_mb": 6144,
        "description": "Distilled large-v3 — near-flagship accuracy at half the size.",
    },
]


# --- Install detection --------------------------------------------------------


def _hf_cache_path(hf_repo: str) -> Path:
    """Default huggingface_hub cache location for a repo."""
    slug = hf_repo.replace("/", "--")
    return Path.home() / ".cache" / "huggingface" / "hub" / f"models--{slug}"


def _is_installed(model: dict[str, Any]) -> bool:
    """Strict: a model is "installed" only if it lives in <repo>/models/.

    We used to also count the HF default cache, but that confused users who
    saw "installed" while nothing actually existed under `models/`.
    Call `_migrate_from_hf_cache()` on startup to lift existing caches in.
    """
    local = _MODELS_ROOT / model["local_dir"]
    return local.is_dir() and any(local.iterdir())


def _migrate_from_hf_cache(model: dict[str, Any]) -> bool:
    """If a model exists in ~/.cache/huggingface/hub/ but not in
    <repo>/models/<local_dir>/, copy its latest snapshot over. Returns True
    if a migration happened. No-op (fast path) if dest already populated
    or source missing.
    """
    repo = model.get("hf_repo")
    if not repo:
        return False
    target = _MODELS_ROOT / model["local_dir"]
    if target.is_dir() and any(target.iterdir()):
        return False  # already in place
    cache = _hf_cache_path(repo)
    snapshots = cache / "snapshots"
    if not snapshots.is_dir():
        return False
    snapshot_dirs = [p for p in snapshots.iterdir() if p.is_dir()]
    if not snapshot_dirs:
        return False
    src = max(snapshot_dirs, key=lambda p: p.stat().st_mtime)

    import shutil
    log.info("[stt_models] migrating %s from HF cache → %s", model["id"], target)
    target.mkdir(parents=True, exist_ok=True)
    try:
        for item in src.iterdir():
            dest = target / item.name
            # HF cache stores files as symlinks into ../../blobs/<sha>. We
            # follow them so the copy is self-contained.
            if item.is_dir():
                shutil.copytree(item, dest, symlinks=False, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest, follow_symlinks=True)
        return True
    except Exception as e:
        log.error("[stt_models] migrate failed id=%s err=%s", model["id"], e)
        return False


# Run migration on module import. Cheap if nothing to do.
_MODELS_ROOT.mkdir(parents=True, exist_ok=True)
for _m in STT_MODELS:
    try:
        _migrate_from_hf_cache(_m)
    except Exception as _e:  # pragma: no cover — defensive
        log.error("[stt_models] migration crashed id=%s err=%s", _m["id"], _e)


# --- Download state -----------------------------------------------------------

# model_id → {"state": "idle"|"downloading"|"done"|"error", "error"?: str}
_status: dict[str, dict[str, Any]] = {}


async def _do_download(model: dict[str, Any]) -> None:
    model_id = model["id"]
    _status[model_id] = {"state": "downloading"}
    repo = model["hf_repo"]
    target = _MODELS_ROOT / model["local_dir"]
    target.mkdir(parents=True, exist_ok=True)
    log.info("[stt_models] download start  id=%s  repo=%s  target=%s", model_id, repo, target)
    try:
        # huggingface_hub's snapshot_download is sync/blocking — run in executor
        from huggingface_hub import snapshot_download

        def _blocking():
            snapshot_download(
                repo_id=repo,
                local_dir=str(target),
                local_dir_use_symlinks=False,
            )

        await asyncio.get_event_loop().run_in_executor(None, _blocking)
        _status[model_id] = {"state": "done"}
        log.info("[stt_models] download done  id=%s", model_id)
    except Exception as e:
        _status[model_id] = {"state": "error", "error": str(e)}
        log.error("[stt_models] download FAILED  id=%s  err=%s", model_id, e)


# --- Endpoints ----------------------------------------------------------------


@router.get("/models")
def list_models() -> dict[str, Any]:
    out = []
    for m in STT_MODELS:
        s = _status.get(m["id"], {}).get("state", "idle")
        out.append({
            "id": m["id"],
            "provider": m["provider"],
            "faster_whisper_size": m.get("faster_whisper_size"),
            "name": m["name"],
            "hf_repo": m.get("hf_repo"),
            "size_mb": m["size_mb"],
            "vram_mb": m["vram_mb"],
            "recommended": m.get("recommended", False),
            # Frontend looks up `stt_desc_<id>` in its i18n bundle.
            "description_key": f"stt_desc_{m['id']}",
            "installed": _is_installed(m),
            "download_state": s,
            "download_error": _status.get(m["id"], {}).get("error"),
        })
    return {"models": out, "models_root": str(_MODELS_ROOT)}


@router.post("/models/{model_id}/download")
async def start_download(model_id: str) -> dict[str, Any]:
    model = next((m for m in STT_MODELS if m["id"] == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id}")
    if not model.get("hf_repo"):
        raise HTTPException(status_code=400, detail="This model has no local download (API-based)")
    if _status.get(model_id, {}).get("state") == "downloading":
        return {"state": "downloading"}
    asyncio.create_task(_do_download(model))
    return {"state": "downloading"}


@router.get("/models/{model_id}/status")
def get_status(model_id: str) -> dict[str, Any]:
    return _status.get(model_id, {"state": "idle"})


@router.delete("/models/{model_id}")
def delete_model(model_id: str) -> dict[str, Any]:
    """Remove a downloaded model's files from <repo>/models/<local_dir>/.
    The HF default cache (~/.cache/huggingface/) is NOT touched — only
    our explicit local copy.
    """
    model = next((m for m in STT_MODELS if m["id"] == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id}")
    if not model.get("hf_repo"):
        raise HTTPException(status_code=400, detail="This model has no local files to delete")
    target = _MODELS_ROOT / model["local_dir"]
    if not target.is_dir():
        return {"ok": True, "deleted": False}
    try:
        shutil.rmtree(target)
        log.info("[stt_models] deleted id=%s path=%s", model_id, target)
        # Clear any residual download status so UI reflects clean state.
        _status.pop(model_id, None)
        return {"ok": True, "deleted": True}
    except Exception as e:
        log.error("[stt_models] delete FAILED id=%s err=%s", model_id, e)
        raise HTTPException(status_code=500, detail=str(e))
