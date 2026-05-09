"""End-to-end smoke test for every supported language.

For each L2 we exercise the full plugin contract:
- Module imports + register_language hook fires
- annotate() returns a non-empty AnnotatedText with the right language
- prosody_target() returns matching unit count and language
- common_errors(l1) has patterns for at least one of zh/en/ja
- Scene loader returns ≥ 8 L2-specific + 9 cross-language scenes
- tts_reference() round-trips through edge-tts and produces non-empty audio
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.languages.registry import ensure_loaded, get_language, list_languages  # noqa: E402
from backend.scenes.loader import load_all  # noqa: E402


SAMPLES = {
    "ja": "こんにちは。今日は天気がいいですね。",
    "zh": "你好，今天天气真不错。",
    "en": "Hello, the weather is really nice today.",
    "ko": "안녕하세요. 오늘 날씨가 참 좋네요.",
    "yue": "你好，今日天氣真係好好呀。",
}

ALL_CODES = ("ja", "zh", "en", "ko", "yue")


async def check_language(code: str) -> list[str]:
    errors: list[str] = []
    sample = SAMPLES[code]
    try:
        lang = get_language(code)
    except KeyError as e:
        return [f"get_language({code!r}) failed: {e}"]

    if not lang.display_names.get(code):
        errors.append(f"display_names missing native key {code!r}")

    annotated = lang.annotate(sample)
    if annotated.language != code:
        errors.append(f"annotate.language={annotated.language!r}, expected {code!r}")
    if not annotated.tokens:
        errors.append("annotate produced zero tokens")

    target = lang.prosody_target(sample)
    if target.language != code:
        errors.append(f"prosody_target.language={target.language!r}, expected {code!r}")
    if not target.unit_labels:
        # ja's prosody depends on pyopenjtalk, which is optional (needs a
        # C++ compiler). Treat empty as skipped, not failed, when the
        # underlying library is missing.
        if code == "ja":
            try:
                import pyopenjtalk  # noqa: F401
                errors.append("prosody_target produced zero unit_labels")
            except ImportError:
                print("  prosody: skipped (pyopenjtalk not installed — optional)")
        else:
            errors.append("prosody_target produced zero unit_labels")

    any_errors = False
    for l1 in ("zh", "en", "ja"):
        if lang.common_errors(l1).patterns:
            any_errors = True
            break
    if not any_errors:
        errors.append("common_errors empty for zh/en/ja")

    scenes = load_all(code)
    l2_specific = [s for s in scenes if s.get("source") == code]
    common = [s for s in scenes if s.get("source") == "common"]
    if len(l2_specific) < 8:
        errors.append(f"only {len(l2_specific)} L2-specific scenes (expected >= 8)")
    if len(common) < 9:
        errors.append(f"only {len(common)} common scenes available (expected >= 9)")

    # edge-tts occasionally 503s — retry once before declaring failure.
    audio = await lang.tts_reference(sample)
    if not audio or len(audio) < 1000:
        await asyncio.sleep(1.5)
        audio = await lang.tts_reference(sample)
    if not audio or len(audio) < 1000:
        errors.append(f"tts_reference returned {len(audio)} bytes after retry")
    else:
        print(f"  tts: {len(audio)} bytes")

    return errors


async def main() -> int:
    ensure_loaded(list(ALL_CODES))
    print(f"Registered: {list_languages()}")
    print(f"Expected:   {sorted(ALL_CODES)}")
    if sorted(list_languages()) != sorted(ALL_CODES):
        print("FAIL: registry mismatch")
        return 1

    failures: dict[str, list[str]] = {}
    for code in ALL_CODES:
        print(f"\n--- {code} ---")
        errs = await check_language(code)
        if errs:
            failures[code] = errs
            for e in errs:
                print(f"  FAIL: {e}")
        else:
            print("  OK")

    print()
    if failures:
        print(f"Smoke test FAILED for: {sorted(failures.keys())}")
        return 1
    print("All 5 languages PASSED end-to-end.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
