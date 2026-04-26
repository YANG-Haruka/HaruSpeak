import logging

from .base import LLMBackend
from .lmstudio import LMStudioLLM
from .openai_cloud import OpenAICloudLLM

log = logging.getLogger(__name__)

__all__ = ["LLMBackend", "LMStudioLLM", "OpenAICloudLLM", "make_llm"]


def make_llm(settings):
    """Factory: pick the right LLMBackend based on settings.llm_provider.

    Two providers:
      - "openai"          → OpenAICloudLLM (cloud / proxy)
      - "openai_lmstudio" → LMStudioLLM (local reasoning-model aware)
    """
    provider = settings.llm_provider.lower()
    if provider == "openai_lmstudio":
        model = settings.lmstudio_model
        base = settings.lmstudio_base
        log.info("[llm] using LM Studio  base=%s  model=%r", base, model)
        if not model:
            log.warning("[llm] LM Studio selected but lmstudio_model is EMPTY — "
                        "pick a model in Settings and save.")
        return LMStudioLLM(
            base_url=base,
            model=model,
            temperature=settings.openai_temperature,
            api_key=settings.openai_api_key or "lm-studio",
        )
    if provider in ("openai", "openai-compat"):
        model = settings.openai_model
        base = settings.openai_api_base
        key_tail = settings.openai_api_key[-4:] if settings.openai_api_key else "(none)"
        log.info("[llm] using OpenAI-cloud  base=%s  model=%r  key=…%s", base, model, key_tail)
        return OpenAICloudLLM(
            api_key=settings.openai_api_key,
            base_url=base,
            model=model,
            temperature=settings.openai_temperature,
            thinking_mode=getattr(settings, "openai_thinking_mode", "disabled"),
        )
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
