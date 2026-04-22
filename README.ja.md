# HaruSpeak

<p align="right">
  <a href="README.md">English</a> · <a href="README.zh.md">中文</a> · <strong>日本語</strong>
</p>

> 音声ファーストの多言語**会話練習**アプリ。母語 (L1) と学習言語 (L2)
> を選び、場面やキャラクターを選ぶと、AI と自然な音声会話ができます ——
> ふりがな / 拼音の注釈、リアルタイム翻訳、3 段階の返信候補付き。

現在サポートする練習言語は **日本語**、**中国語**、**英語**。
今後さらに追加予定。

---

## 特徴

- 🎙 **音声会話** —— ブラウザ側 VAD、STT → LLM → TTS ストリーミング
- 📖 **注釈** —— 日本語のふりがな、中国語の拼音
- 🌐 **リアルタイム翻訳** —— AI の各発話を母語に翻訳
- 💡 **返信候補** —— 各ターン 3 段階（短い / 自然 / 豊か）
- 🎭 **言語ごとに 16 シーン** + カスタムシーン入力
- 👤 **言語ごとに 7 キャラクター** + カスタム入力
- 🧠 **任意の LLM** —— OpenAI 互換クラウド または LM Studio / Ollama ローカル
- 🔊 **オフライン STT** —— SenseVoice-Small（デフォルト、約 900 MB）または faster-whisper
- 🗣 **無料 TTS** —— edge-tts（Microsoft Neural 音声、API キー不要）

---

## 必要環境

- **Python 3.11**
- **Node.js 18+**
- **ffmpeg**(PATH 上 — ブラウザ音声のデコード用)
- **miniconda** または **Anaconda**（推奨 — ffmpeg が楽に入る）
- 任意: **CUDA GPU** — STT をさらに高速化
- 任意: **LM Studio** または **Ollama** — 完全ローカルな LLM 運用

---

## ゼロからのインストール

**ワンコマンドで完了** —— conda 環境作成、ffmpeg、Python 依存（uv 経由、pip より 10 倍高速）、フロントエンド依存をすべて自動で：

```bash
git clone <this-repo>
cd haruspeak
python scripts/setup.py
```

スクリプトは冪等。いつでも再実行安全。オプション：
`--recreate`（conda env を削除して作り直し）、`--backend-only`、`--frontend-only`。

> **事前に必要なもの:** Python 3.11+、Miniconda または Anaconda、Node.js 18+。
>
> **日本語ピッチアクセント（任意）:** 高品質なピッチ注釈が必要なら `pyopenjtalk`
> を別途インストール（C++ コンパイラが必要 — Windows は MSVC、Linux は gcc）。
> なくても fugashi にフォールバックして動作します。

<details><summary>手動インストール（お好みで）</summary>

```bash
conda create -n haruspeak python=3.11 -y
conda install -n haruspeak -c conda-forge ffmpeg -y
conda run -n haruspeak pip install uv
conda run -n haruspeak uv pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

</details>

---

## 起動

```bash
python scripts/dev.py
```

`http://localhost:3000` が開きます。Ctrl+C でバックエンドとフロントエンドを同時に停止。

初回の会話時に SenseVoice モデル（約 900 MB）を遅延ダウンロード。
以降、1 発話あたり約 200 ms でローカル認識。

---

## アプリ内設定

右上のギア ⚙ をクリック。すべての設定は `config/config.json` に保存され、
次回の会話から反映されます：

- **LLM プロバイダ** —— OpenAI 互換クラウド（任意のプロキシ）または
  LM Studio / Ollama ローカル（`/v1/models` でロード済みモデルを自動検出）
- **STT モデル** —— SenseVoice-Small（推奨）または任意サイズの faster-whisper。
  ダウンロード/削除 UI 付き、重みは `<repo>/models/` に配置
- **TTS 音声** —— 各練習言語ごとに、音色の説明付き
- **UI 言語 + ダーク/ライトテーマ**

---

## リポジトリ構成

```
backend/
  main.py                  FastAPI + WebSocket
  api/settings.py          GET/POST /api/settings、LM Studio プローブ
  api/stt_models.py        STT モデル一覧/ダウンロード/削除
  languages/{ja,zh,en}/    L2 ごとに: G2P、注釈、よくあるミス
  llm/
    openai_cloud.py        OpenAI 互換クラウド
    lmstudio.py            LM Studio / Ollama (reasoning モデル対応)
    _thinking.py           <think> / CoT 除去
  stt/
    sensevoice.py          SenseVoice-Small (デフォルト)
    faster_whisper_local.py
  tts/edge.py              edge-tts ラッパー
  pipeline/conversation.py 会話ターンのストリーミング制御

frontend/
  app/page.tsx             L1/L2 セレクター
  app/scene/page.tsx       シーン + キャラクター選択
  app/chat/page.tsx        音声会話 UI
  app/settings/page.tsx    ランタイム設定（自動保存）
  components/              VoiceOrb、AnnotatedText (ruby)、ControlBar ...

prompts/                   LLM / シーン / キャラクター素材（貢献しやすい）
  logic/*.md               LLM 用プロンプト（会話、翻訳など）
  scenes/common/*.yaml     言語共通 9 シーン
  scenes/{ja,zh,en}/*.yaml 各言語 8 シーン
  personas/{ja,zh,en}.yaml 各言語 7 キャラクター

models/                    ダウンロード済み STT 重み (gitignore)
config/config.sample.json    リポジトリ同梱のサンプル（秘密情報なし）
config/config.json           実際の設定 (Settings UI が書き込む、gitignore)
logs/backend.log           最新 30 行のログ (gitignore)
```

---

## 貢献

- **シーン / キャラクター追加** —— `prompts/scenes/<lang>/` に YAML を置くか
  `prompts/personas/<lang>.yaml` を編集。コード変更不要。
- **新言語追加** —— [docs/ADDING_A_LANGUAGE.md](docs/ADDING_A_LANGUAGE.md) 参照
- **アーキテクチャ概要** —— [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) 参照

---

## ライセンス

MIT —— [LICENSE](LICENSE) 参照。
