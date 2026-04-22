# HaruSpeak architecture

## Two independent pipelines

The whole system is structured around two pipelines that share **no
runtime state** with each other:

```
┌─────────────── Conversation pipeline ────────────────┐
│  STT → LLM → annotate → TTS                          │
│  Used for: normal back-and-forth chat                │
│  Replaceable with: Moshi / Qwen3-Omni end-to-end     │
└──────────────────────────────────────────────────────┘

┌─────────────── Evaluation pipeline ──────────────────┐
│  audio → F0 → prosody score + wav2vec2 phoneme GOP   │
│  Used for: pronunciation feedback, shadowing         │
│  NOT replaceable by end-to-end speech LLMs (they     │
│  don't expose phoneme posteriors)                    │
└──────────────────────────────────────────────────────┘
```

**Why separate?** The conversation pipeline is an IO-bound orchestrator.
The evaluation pipeline is CPU/GPU-bound acoustic analysis. They share
`LanguageModule` (for per-L2 G2P and prosody target) but nothing else.

## The LanguageModule contract

Every L2 (ja, zh, en, and future additions) implements
`backend.languages.base.LanguageModule`. The conversation pipeline and
evaluation pipeline both take a `LanguageModule` injection — the caller
picks the L2 once at session start and everything downstream works
polymorphically.

See `docs/ADDING_A_LANGUAGE.md` for the template.

## L1 vs L2 asymmetry

- **L1** (learner's native language) costs **O(N)** to support: UI i18n +
  LLM prompt output language + error-pattern library per (L1, L2) pair.
- **L2** (target language) costs **O(N) per language**: a full G2P,
  prosody scorer, annotator, TTS choice, and wav2vec2 head.

Practical consequence: adding a new display language is cheap; adding a
new target language is a Phase.

## Data flywheel

`backend/telemetry/logger.py` logs per-turn records with:
- Anonymized `user_id` (random UUID, stored locally)
- L1, L2, scene_id
- Transcript text
- Audio SHA256 (+ blob if user opts in)
- Three pronunciation scores

Phase 6 uses the consented audio to:
1. Fine-tune wav2vec2 per-L2 on real learner audio
2. Cluster errors by (L1, L2) to grow per-pair error libraries
3. Train a dedicated MDD model for "Chinese-native Japanese-learner" etc.

Default is opt-out; no data leaves the machine unless the user explicitly
enables a sync endpoint (not yet implemented).
