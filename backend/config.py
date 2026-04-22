"""Runtime configuration for HaruSpeak.

Loaded from environment variables at import time (optionally from a .env
file for convenience). A running settings API (backend.api.settings) can
mutate fields in place and persist to `data/config.json` so users can
switch LLM/STT providers without a restart.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


_REPO_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _REPO_ROOT / "config" / "config.json"
# Legacy load paths, in order of preference (newest first):
_LEGACY_PATHS = [
    _REPO_ROOT / "data" / "config.json",    # pre-config-folder rename
    _REPO_ROOT / "data" / "settings.json",  # pre-file rename
]


class Settings(BaseSettings):
    # ---- LLM ---------------------------------------------------------------
    # Two providers supported:
    #   "openai"          → OpenAI-compatible endpoint (cloud or proxy)
    #   "openai_lmstudio" → LM Studio / Ollama local server
    # Each provider keeps its OWN model so switching doesn't carry a bogus
    # model name across.
    llm_provider: str = "openai"

    openai_model: str = "gpt-4o-mini"
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    openai_temperature: float = 1.0

    lmstudio_model: str = ""
    lmstudio_base: str = "http://localhost:1234/v1"

    # ---- STT ---------------------------------------------------------------
    stt_provider: str = "sensevoice"
    whisper_model: str = "whisper-1"
    faster_whisper_size: str = "small"
    sensevoice_model_path: str = "FunAudioLLM/SenseVoiceSmall"

    # ---- TTS ---------------------------------------------------------------
    tts_voice_ja: str = "ja-JP-NanamiNeural"
    tts_voice_zh: str = "zh-CN-XiaoxiaoNeural"
    tts_voice_en: str = "en-US-AriaNeural"

    # ---- Runtime -----------------------------------------------------------
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",            # optional — read if present
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def apply_overrides(self, data: dict) -> None:
        """Mutate settings in place from a trusted dict of overrides.

        Migrations:
          - legacy `llm_model` → `openai_model` (single-model → per-provider)
          - stt_provider `whisper_openai` → `sensevoice` (removed provider)
        """
        if "llm_model" in data and "openai_model" not in data:
            data = {**data, "openai_model": data["llm_model"]}
        data = {k: v for k, v in data.items() if k != "llm_model"}
        if data.get("stt_provider") == "whisper_openai":
            data = {**data, "stt_provider": "sensevoice"}
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def save_overrides(self) -> None:
        """Persist override dict to data/config.json for next launch."""
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        persisted = {
            k: getattr(self, k)
            for k in (
                "llm_provider",
                "openai_model",
                "openai_api_base",
                "openai_api_key",
                "lmstudio_model",
                "lmstudio_base",
                "stt_provider",
                "faster_whisper_size",
                "whisper_model",
                "tts_voice_ja",
                "tts_voice_zh",
                "tts_voice_en",
            )
        }
        _CONFIG_PATH.write_text(json.dumps(persisted, indent=2, ensure_ascii=False))


# Pydantic-settings reads UPPERCASE env vars by default, so LLM_MODEL from
# the environment needs mapping into openai_model for the OpenAI path.
_legacy_model = os.environ.get("LLM_MODEL")
settings = Settings()
if _legacy_model and settings.openai_model == "gpt-4o-mini":
    settings.openai_model = _legacy_model

# Load persisted overrides. Prefer new path; otherwise try legacy paths
# in order and one-time migrate into the new location.
_path = _CONFIG_PATH if _CONFIG_PATH.exists() else next(
    (p for p in _LEGACY_PATHS if p.exists()), None
)
if _path is not None:
    try:
        settings.apply_overrides(json.loads(_path.read_text(encoding="utf-8")))
        if _path != _CONFIG_PATH:
            # Migrate into the new location; old file stays (user can delete).
            settings.save_overrides()
    except Exception as e:
        print(f"[config] could not load {_path}: {e}")
