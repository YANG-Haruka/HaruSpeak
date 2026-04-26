# HaruSpeak

<p align="right">
  <a href="README.md">English</a> · <strong>中文</strong> · <a href="README.ja.md">日本語</a>
</p>

> 语音优先的多语言**口语练习**应用。选你的母语（L1）和要练习的语言（L2），挑一个场景或人设，与 AI 进行自然的语音对话 —— 带假名/拼音注音、实时翻译，以及三档回复建议。

目前支持 **日语**、**中文**、**英语** 作为练习语言，后续会扩展。

---

## 功能亮点

- 🎙 **语音对话** —— 浏览器端 VAD，STT → LLM → TTS 流式处理
- 📖 **注音** —— 日语假名、中文拼音
- 🌐 **实时翻译** —— 每句 AI 回复都译回你的母语
- 💡 **回复建议** —— 每轮 3 档（简短 / 自然 / 丰富）
- 🎭 **每语言 16 个场景** + 自定义场景
- 👤 **每语言 7 位人设** + 自定义人设
- 🧠 **任意 LLM** —— OpenAI 兼容云端 或 LM Studio / Ollama 本地
- 🔊 **离线 STT** —— SenseVoice-Small（默认，约 900 MB）或 faster-whisper
- 🗣 **免费 TTS** —— edge-tts（Microsoft Neural 语音，不需要 API key）

---

## 环境要求

- **Python 3.11**
- **Node.js 18+**
- **ffmpeg** 在 PATH 中（解码浏览器音频）
- **miniconda** 或 **Anaconda**（推荐，ffmpeg 一键装）
- 可选：**CUDA GPU** 让 STT 更快
- 可选：**LM Studio** 或 **Ollama** 用于完全本地的 LLM

---

## 从零安装

**一条命令搞定** —— 自动创建 conda 环境、装 ffmpeg、装 Python 依赖（用 uv，比 pip 快 10 倍）、装前端依赖：

```bash
git clone <this-repo>
cd haruspeak
python scripts/setup.py
```

脚本是幂等的，随时可以重跑。可选参数：
`--recreate`（删除重建 conda env）、`--backend-only`、`--frontend-only`。

> **前置要求：** Python 3.11+、Miniconda 或 Anaconda、Node.js 18+。
>
> **日语音高（可选）：** 想要高质量的日语音高注音可单独装 `pyopenjtalk`（需 C++ 编译器 —— Windows 上是 MSVC，Linux 上是 gcc）。不装也能用，会 fallback 到 fugashi。

<details><summary>手动安装（如果你更喜欢）</summary>

```bash
conda create -n haruspeak python=3.11 -y
conda install -n haruspeak -c conda-forge ffmpeg -y
conda run -n haruspeak pip install uv
conda run -n haruspeak uv pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

</details>

---

## 启动

```bash
python scripts/dev.py
```

会打开 `http://localhost:3000`。Ctrl+C 同时停止前后端。

首次对话时懒加载 SenseVoice 模型（约 900 MB），之后每段识别本地约 200ms。

---

## 应用内设置

点击顶部齿轮 ⚙。所有设置保存到 `config/config.json`，下次对话生效：

- **LLM 提供方** —— OpenAI 兼容云端（任何代理）或
  LM Studio / Ollama 本地（通过 `/v1/models` 自动检测已加载模型）
  - **推荐模型**：
    - `deepseek-v4-flash`（默认）—— 接口 `https://api.deepseek.com/v1`
    - `gpt-5.4-mini` —— 接口 `https://api.openai.com/v1`（或任意
      OpenAI 兼容代理）
  - 推理模型（DeepSeek v4 / OpenAI o1+ / Anthropic 扩展思考）在
    `config.json` 里有 **思考开关**：`openai_thinking_mode`，默认
    `disabled`——这样翻译/建议这种小调用才会真的输出可见 content。
    想体验完整推理就改成 `enabled`（注意会消耗更多 token）。
- **STT 模型** —— SenseVoice-Small（推荐）或任意大小的 faster-whisper，
  带下载/删除 UI，权重放在 `<repo>/models/`
- **TTS 声音** —— 每种目标语言一份，附音色说明
- **界面语言 + 深浅色主题**

---

## 仓库结构

```
backend/
  main.py                  FastAPI + WebSocket
  api/settings.py          GET/POST /api/settings, LM Studio 探测
  api/stt_models.py        列出/下载/删除 STT 模型
  languages/{ja,zh,en}/    按 L2 分：G2P、注音、常见错误库
  llm/
    openai_cloud.py        OpenAI 兼容云端
    lmstudio.py            LM Studio / Ollama（感知 reasoning 模型）
    _thinking.py           <think> / CoT 剥离器
  stt/
    sensevoice.py          SenseVoice-Small（默认）
    faster_whisper_local.py
  tts/edge.py              edge-tts 包装
  pipeline/conversation.py 流式对话编排

frontend/
  app/page.tsx             L1/L2 选择
  app/scene/page.tsx       场景 + 人设选择
  app/chat/page.tsx        语音对话界面
  app/settings/page.tsx    运行时设置（自动保存）
  components/              VoiceOrb、AnnotatedText (ruby)、ControlBar 等

prompts/                   所有 LLM / 场景 / 人设内容（容易贡献）
  logic/*.md               LLM 脚手架 prompt（对话、翻译等）
  scenes/common/*.yaml     9 个跨语言场景
  scenes/{ja,zh,en}/*.yaml 每语言 8 个专属场景
  personas/{ja,zh,en}.yaml 每语言 7 位人设

models/                    已下载的 STT 权重（gitignore）
config/config.sample.json    仓库自带的占位模板（不含密钥）
config/config.json           你真实的设置（由 Settings UI 写入，gitignore）
logs/backend.log           最新 30 条日志（gitignore）
```

---

## 贡献

- **添加场景 / 人设** —— 在 `prompts/scenes/<lang>/` 扔个 YAML 或编辑
  `prompts/personas/<lang>.yaml`。无需改代码。
- **添加新语言** —— 见 [docs/ADDING_A_LANGUAGE.md](docs/ADDING_A_LANGUAGE.md)
- **架构概览** —— 见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 许可证

MIT —— 见 [LICENSE](LICENSE)。
