# Adding a new L2 (language) to HaruSpeak

Adding, say, Korean takes ~1 day once you have the libraries. The plug-in shape:

```
backend/languages/ko/
├── __init__.py        # register_language(KoreanModule())
├── module.py          # class KoreanModule(LanguageModule)
├── g2p.py             # text → phoneme list
├── annotator.py       # text → AnnotatedText
├── prosody.py         # prosody target + scoring (Korean: pitch-less, just stress?)
├── errors.py          # L1→ko common mistakes
└── config.yaml        # STT/TTS/wav2vec2 identifiers
```

## Step-by-step

### 1. Pick libraries for G2P
Korean: `python-mecab-ko` or `KoNLPy` for morpheme split + `hangul-jamo` for phoneme breakdown.

### 2. Decide the `unit_kind`
- Korean: syllable (each 가/나/다 is one syllable)
- French: syllable
- Arabic: phoneme (script doesn't mark vowels)

This is what `UnitDisplay` on the frontend colorizes, so it must match
what `score_prosody` returns in `unit_labels`.

### 3. Decide the prosody objective
- Korean: intonation + stress (like English)
- Thai/Vietnamese: lexical tones (like Chinese)
- French: final-syllable stress (like English but simpler)

Copy the closest existing module's `prosody.py` and adapt.

### 4. Annotator rules
- Does the script have inherent phonetic info?
  - Hangul: yes → no reading needed (like EN)
  - Hiragana-only text: yes → no furigana needed
  - Han characters (CJK): no → need reading annotation
- Follow `AnnotatedText` per-token semantics: `reading=None` when the
  script is already phonetic.

### 5. Wire TTS + STT
- `config.yaml`:
  - `stt.language_code`: SenseVoice supports JA/ZH/EN/KO/YUE out of the box
  - `tts.reference.backend`: pick one of `voicevox` (JA), `cosyvoice` (multi),
    `piper` (EN, many voices)
- If you need a new TTS backend, add `backend/tts/<name>.py` following
  the `TTSBackend` Protocol in `tts/base.py`.

### 6. Register
In `backend/main.py`, extend `ensure_loaded([...])` to include your new code.
In frontend `LanguageSelector`, no change needed — it pulls from `/api/languages`.

### 7. Tests
Copy `tests/languages/test_ja.py` to `tests/languages/test_<code>.py`,
change fixtures to your L2, verify:
- `annotate(sample_text)` has the right reading shape
- `prosody_target(sample_text)` produces the expected number of units
- `common_errors("zh")` and `common_errors("en")` return non-empty lists
  for at least the top-3 L1s you support

## Checklist
- [ ] Subdir with all 6 files
- [ ] `register_language` in `__init__.py`
- [ ] Unit tests in `tests/languages/test_<code>.py`
- [ ] Config includes `stt`, `tts.reference`, `tts.conversation`, `wav2vec2`
- [ ] Scenes: add `backend/scenes/<code>/<scene>.yaml` for culturally specific situations
- [ ] Persona: add `backend/personas/<code>.yaml`
- [ ] Frontend: verify `<AnnotatedText lang="<code>">` renders correctly

When all items are checked, the new language appears in the Home page's
L2 picker automatically and is ready to use.
