# HaruSpeak

<p align="right">
  <strong>English</strong> · <a href="README.zh.md">中文</a> · <a href="README.ja.md">日本語</a>
</p>

> A voice-first multilingual **speaking practice** app. Pick your native
> language (L1) and a language you want to practice (L2), pick a scene
> or character, and have a natural voice conversation with an AI —
> complete with furigana/pinyin annotations, live translations, and
> three-tier reply suggestions.

Supports **Japanese**, **Chinese**, and **English** as practice languages,
with more on the roadmap.

---

## Features

- 🎙 **Voice conversation** — browser-side VAD, streaming STT → LLM → TTS
- 📖 **Annotations** — furigana for Japanese, pinyin for Chinese
- 🌐 **Live translations** — every AI message translated into your L1
- 💡 **Reply suggestions** — 3 tiers (short / natural / rich) per turn
- 🎭 **16 scenes per language** + custom scene input
- 👤 **7 personas per language** + custom persona input
- 🧠 **Any LLM** — OpenAI-compatible cloud OR LM Studio / Ollama locally
- 🔊 **Offline STT** — SenseVoice-Small (default, ~900 MB) or faster-whisper
- 🗣 **Free TTS** — edge-tts (Microsoft Neural voices, no API key)

---

## Requirements

- **Python 3.11**
- **Node.js 18+**
- **ffmpeg** on PATH (for decoding browser audio)
- **miniconda** or **Anaconda** (recommended — installs ffmpeg easily)
- Optional: **CUDA GPU** for faster STT
- Optional: **LM Studio** or **Ollama** for fully local LLM

---

## Install from scratch

**One command does everything** — creates the conda env, installs ffmpeg,
Python deps (via uv, ~10x faster than pip), and frontend deps:

```bash
git clone <this-repo>
cd haruspeak
python scripts/setup.py
```

The script is idempotent — safe to re-run anytime. Flags:
`--recreate` (wipe and rebuild the conda env),
`--backend-only`, `--frontend-only`.

> **Prereqs you need first:** Python 3.11+, Miniconda or Anaconda, Node.js 18+.
>
> **Japanese pitch accent (optional):** install `pyopenjtalk` separately if
> you want high-quality accent annotations (needs a C++ compiler — MSVC on
> Windows, gcc on Linux). Without it, HaruSpeak falls back to fugashi and
> everything still works.

<details><summary>Manual install (if you prefer)</summary>

```bash
conda create -n haruspeak python=3.11 -y
conda install -n haruspeak -c conda-forge ffmpeg -y
conda run -n haruspeak pip install uv
conda run -n haruspeak uv pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

</details>

---

## Run

```bash
python scripts/dev.py
```

Opens `http://localhost:3000`. Ctrl+C stops both backend and frontend.

First chat turn lazy-downloads the SenseVoice model (~900 MB). After that,
transcription runs locally in ~200 ms per clip.

---

## Configure (in-app Settings)

Click the gear ⚙ in the top nav. Everything here persists to
`config/config.json` and applies on the next chat session:

- **LLM provider** — OpenAI-compatible cloud (any proxy) _or_
  LM Studio / Ollama on localhost (auto-detects loaded models via `/v1/models`)
- **STT model** — SenseVoice-Small (recommended) or any faster-whisper size,
  with a built-in download/delete UI; weights land in `<repo>/models/`
- **TTS voice** — per target language, with tone descriptions
- **UI language + dark/light theme**

---

## Repo layout

```
backend/
  main.py                  FastAPI app + WebSocket
  api/settings.py          GET/POST /api/settings, LM Studio probe
  api/stt_models.py        list/download/delete STT models
  languages/{ja,zh,en}/    per-L2: G2P, annotator, common errors
  llm/
    openai_cloud.py        OpenAI-compatible cloud backend
    lmstudio.py            LM Studio / Ollama local backend (reasoning-aware)
    _thinking.py           <think> / CoT stripper
  stt/
    sensevoice.py          SenseVoice-Small (default)
    faster_whisper_local.py
  tts/edge.py              edge-tts wrapper
  pipeline/conversation.py streaming turn orchestrator

frontend/
  app/page.tsx             L1/L2 picker
  app/scene/page.tsx       scene + persona selector
  app/chat/page.tsx        voice conversation UI
  app/settings/page.tsx    runtime settings (auto-save)
  components/              VoiceOrb, AnnotatedText (ruby), ControlBar, ...

prompts/                   all LLM / scene / persona content (easy to contribute)
  logic/*.md               scaffolding prompts (conversation, translate, ...)
  scenes/common/*.yaml     9 cross-language scenes
  scenes/{ja,zh,en}/*.yaml 8 L2-specific scenes each
  personas/{ja,zh,en}.yaml 7 personas each

models/                    downloaded STT weights (gitignored)
config/config.sample.json    template shipped in repo (no secrets)
config/config.json           your actual settings, written by the Settings UI (gitignored)
logs/backend.log           rotating daily log (gitignored)
```

---

## Contributing

- **Adding scenes / personas** — just drop a YAML in `prompts/scenes/<lang>/`
  or edit `prompts/personas/<lang>.yaml`. No code changes needed.
- **Adding a language** — see [docs/ADDING_A_LANGUAGE.md](docs/ADDING_A_LANGUAGE.md)
- **Architecture overview** — see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## License

MIT — see [LICENSE](LICENSE).
