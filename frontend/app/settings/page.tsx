"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { TopNav } from "@/components/TopNav";
import { STTModelPicker } from "@/components/STTModelPicker";
import { useT } from "@/lib/i18n";

type Current = {
  llm_provider: string;

  openai_model: string;
  openai_api_base: string;
  openai_api_key: string;

  lmstudio_model: string;
  lmstudio_base: string;

  stt_provider: string;
  faster_whisper_size: string;
  whisper_model: string;
  sensevoice_model_path: string;
  tts_voice_ja: string;
  tts_voice_zh: string;
  tts_voice_en: string;
};

type LlmProvider = {
  id: string;
  name: string;
  available?: boolean;
  models?: string[];
  error?: string | null;
  probed_url?: string;
};

type Voice = { id: string; description_key: string };

type Candidates = {
  llm_providers: LlmProvider[];
  stt_providers: { id: string; name: string }[];
  faster_whisper_sizes: string[];
  tts_voices: { ja: Voice[]; zh: Voice[]; en: Voice[] };
};

type SaveState = "idle" | "saving" | "saved";

export default function SettingsPage() {
  const t = useT();
  const [cur, setCur] = useState<Current | null>(null);
  const [cand, setCand] = useState<Candidates | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  // `form` holds ONLY the user's pending (unsaved) changes. Empty after
  // each successful auto-save. Read with `form.x ?? cur.x` everywhere.
  const [form, setForm] = useState<Partial<Current>>({});
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [showKey, setShowKey] = useState(false);

  const reloadCandidates = async () => {
    const c = await fetch("/api/settings/candidates").then((r) => r.json());
    setCand(c);
  };

  useEffect(() => {
    (async () => {
      const [a, b] = await Promise.all([
        fetch("/api/settings").then((r) => r.json()),
        fetch("/api/settings/candidates").then((r) => r.json()),
      ]);
      setCur(a);
      setCand(b);
    })().catch((e) => setMsg(`${t("load_failed")}: ${e}`));
  }, []);

  const field = <K extends keyof Current>(key: K, value: Current[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  // Auto-save: fires 400ms after the user stops changing settings.
  // Debouncing prevents one save per keystroke while still feeling instant.
  useEffect(() => {
    if (!cur) return;
    if (Object.keys(form).length === 0) return;
    const id = window.setTimeout(async () => {
      setSaveState("saving");
      setMsg(null);
      try {
        const r = await fetch("/api/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });
        if (!r.ok) throw new Error(await r.text());
        const a = await fetch("/api/settings").then((r) => r.json());
        setCur(a);
        setForm({});                 // clear pending changes
        setSaveState("saved");
        window.setTimeout(() => setSaveState("idle"), 1500);
      } catch (e) {
        setMsg(`${t("save_failed")}: ${e instanceof Error ? e.message : e}`);
        setSaveState("idle");
      }
    }, 400);
    return () => window.clearTimeout(id);
  }, [form, cur, t]);

  if (!cur || !cand) {
    return (
      <>
        <TopNav back hideSettings />
        <main className="max-w-2xl mx-auto px-6 py-16 text-muted text-sm">
          {t("loading")}
        </main>
      </>
    );
  }

  const llmChoice = form.llm_provider ?? cur.llm_provider;
  const lmStudio = cand.llm_providers.find((p) => p.id === "openai_lmstudio");

  return (
    <>
      <TopNav back hideSettings />
      <main className="max-w-2xl mx-auto px-6 pt-10 pb-16 space-y-10">
        <h1 className="text-2xl font-semibold tracking-tight">{t("settings")}</h1>

        {msg && (
          <div className="text-xs bg-muted-bg border border-border rounded-xl px-4 py-3 text-fg">
            {msg}
          </div>
        )}

        <Card title={t("settings_tab_llm")}>
          <Row label={t("settings_provider")}>
            <Select
              value={llmChoice}
              onChange={(v) => field("llm_provider", v)}
              options={cand.llm_providers.map((p) => ({
                value: p.id,
                label:
                  p.name +
                  (p.id === "openai_lmstudio"
                    ? p.available
                      ? " — detected ✓"
                      : " — offline"
                    : ""),
              }))}
            />
          </Row>

          {llmChoice === "openai" && (
            <>
              <Row label={t("settings_api_base")}>
                <Input
                  value={form.openai_api_base ?? cur.openai_api_base}
                  onChange={(v) => field("openai_api_base", v)}
                  placeholder="https://api.openai.com/v1"
                />
              </Row>
              <Row label={t("settings_model")}>
                <Input
                  value={form.openai_model ?? cur.openai_model}
                  onChange={(v) => field("openai_model", v)}
                  placeholder="gpt-4o-mini"
                />
              </Row>
              <Row label={t("settings_api_key")}>
                <KeyInput
                  value={form.openai_api_key ?? cur.openai_api_key}
                  onChange={(v) => field("openai_api_key", v)}
                  reveal={showKey}
                  onToggle={() => setShowKey((s) => !s)}
                  placeholder="sk-..."
                />
              </Row>
            </>
          )}

          {llmChoice === "openai_lmstudio" && (
            <>
              {/* Server status (only shown when LM Studio / Ollama is selected) */}
              <div className="flex items-start gap-3">
                <div
                  className={
                    "flex-1 text-[12px] rounded-xl px-3.5 py-2.5 border " +
                    (lmStudio?.available
                      ? "border-success/40 bg-success/10 text-success"
                      : "border-warn/40 bg-warn/10 text-warn")
                  }
                >
                  {lmStudio?.available ? (
                    <div>
                      ✓ {t("settings_lmstudio_detected")} —{" "}
                      {lmStudio.models?.length ?? 0} model(s){" "}
                      <code className="text-[11px] opacity-70">
                        {lmStudio.probed_url}
                      </code>
                    </div>
                  ) : (
                    <div className="space-y-1">
                      <div>
                        ⚠ {t("settings_lmstudio_offline")}{" "}
                        <code className="text-[11px]">{lmStudio?.probed_url}</code>
                      </div>
                      {lmStudio?.error && (
                        <div className="text-[11px] opacity-80 break-all">
                          {lmStudio.error}
                        </div>
                      )}
                      <div className="text-[11px] opacity-80">
                        {t("settings_lmstudio_hint")}
                      </div>
                    </div>
                  )}
                </div>
                <button
                  type="button"
                  className="text-[14px] text-muted hover:text-fg transition shrink-0 pt-2"
                  onClick={reloadCandidates}
                  title={t("settings_refresh_lmstudio")}
                >
                  ↻
                </button>
              </div>

              <Row label={t("settings_api_base")}>
                <Input
                  value={form.lmstudio_base ?? cur.lmstudio_base}
                  onChange={(v) => field("lmstudio_base", v)}
                  placeholder="http://localhost:1234/v1"
                />
              </Row>
              <Row label={t("settings_model")}>
                {lmStudio && lmStudio.models && lmStudio.models.length > 0 ? (
                  <Select
                    value={form.lmstudio_model ?? cur.lmstudio_model}
                    onChange={(v) => field("lmstudio_model", v)}
                    options={[
                      ...(form.lmstudio_model || cur.lmstudio_model ? [] : [{ value: "", label: "—" }]),
                      ...lmStudio.models.map((m) => ({ value: m, label: m })),
                    ]}
                  />
                ) : (
                  <Input
                    value={form.lmstudio_model ?? cur.lmstudio_model}
                    onChange={(v) => field("lmstudio_model", v)}
                    placeholder={t("lm_studio_model_hint")}
                  />
                )}
              </Row>
            </>
          )}
        </Card>

        <Card title={t("settings_tab_stt")}>
          <Row label={t("stt_models_label")}>
            <STTModelPicker
              currentProvider={form.stt_provider ?? cur.stt_provider}
              currentWhisperSize={form.faster_whisper_size ?? cur.faster_whisper_size}
              onPick={(next) => {
                field("stt_provider", next.provider);
                if (next.faster_whisper_size) {
                  field("faster_whisper_size", next.faster_whisper_size);
                }
              }}
            />
          </Row>
        </Card>

        <Card title={t("settings_tab_tts")}>
          <Row label={t("settings_ja_voice")}>
            <VoiceSelect
              value={form.tts_voice_ja ?? cur.tts_voice_ja}
              onChange={(v) => field("tts_voice_ja", v)}
              voices={cand.tts_voices.ja}
            />
          </Row>
          <Row label={t("settings_zh_voice")}>
            <VoiceSelect
              value={form.tts_voice_zh ?? cur.tts_voice_zh}
              onChange={(v) => field("tts_voice_zh", v)}
              voices={cand.tts_voices.zh}
            />
          </Row>
          <Row label={t("settings_en_voice")}>
            <VoiceSelect
              value={form.tts_voice_en ?? cur.tts_voice_en}
              onChange={(v) => field("tts_voice_en", v)}
              voices={cand.tts_voices.en}
            />
          </Row>
        </Card>

      </main>

      {/* Floating auto-save indicator — subtle pill that appears in the
          bottom-right only while saving or briefly after success. */}
      <SaveIndicator state={saveState} />
    </>
  );
}

/* ---------- form primitives ---------- */

function SaveIndicator({ state }: { state: SaveState }) {
  const t = useT();
  if (state === "idle") return null;
  return (
    <div className="fixed bottom-5 right-5 z-40 px-3.5 py-2 rounded-full bg-bg-elev border border-border shadow-lg text-[12px] flex items-center gap-2 animate-[fadeIn_160ms_ease-out]">
      {state === "saving" ? (
        <>
          <span className="w-3 h-3 rounded-full border-2 border-muted border-t-transparent animate-spin" />
          <span className="text-muted">{t("settings_saving")}</span>
        </>
      ) : (
        <>
          <span className="text-success">✓</span>
          <span className="text-fg">{t("settings_saved_short")}</span>
        </>
      )}
    </div>
  );
}

const inputCls =
  "w-full px-3.5 py-2.5 rounded-xl bg-bg-elev border border-border text-fg text-sm focus:outline-none focus:border-accent transition";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-[11px] uppercase tracking-widest text-muted font-semibold">
        {title}
      </h2>
      <div className="space-y-4 p-5 rounded-2xl border border-border bg-bg-elev/40">
        {children}
      </div>
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className="text-xs text-muted font-medium">{label}</span>
      {children}
    </label>
  );
}

function Input({
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <input
      className={inputCls}
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
    />
  );
}

function KeyInput({
  value,
  onChange,
  reveal,
  onToggle,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  reveal: boolean;
  onToggle: () => void;
  placeholder?: string;
}) {
  const t = useT();
  return (
    <div className="relative">
      <input
        className={inputCls + " pr-11 font-mono"}
        type={reveal ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        spellCheck={false}
      />
      <button
        type="button"
        onClick={onToggle}
        aria-label={reveal ? t("hide_key") : t("show_key")}
        title={reveal ? t("hide_key") : t("show_key")}
        className="absolute right-1 top-1/2 -translate-y-1/2 w-9 h-9 rounded-lg text-muted hover:text-fg hover:bg-muted-bg transition flex items-center justify-center text-[15px]"
      >
        {reveal ? "🙈" : "👁"}
      </button>
    </div>
  );
}

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      className={inputCls}
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

/** Radio-style voice picker that renders each voice's human-friendly
 *  description under its edge-tts ID. A plain <select> can't show two
 *  lines per option across browsers, so we use buttons in a bordered list. */
function VoiceSelect({
  value,
  onChange,
  voices,
}: {
  value: string;
  onChange: (v: string) => void;
  voices: { id: string; description_key: string }[];
}) {
  const t = useT();
  return (
    <div className="rounded-xl border border-border bg-bg-elev/40 divide-y divide-border overflow-hidden">
      {voices.map((v) => {
        const selected = v.id === value;
        return (
          <button
            key={v.id}
            type="button"
            onClick={() => onChange(v.id)}
            className={clsx(
              "w-full text-left px-3.5 py-2.5 transition",
              selected ? "bg-accent/10" : "hover:bg-muted-bg"
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span
                className={clsx(
                  "text-[13px] font-mono truncate",
                  selected ? "text-accent" : "text-fg"
                )}
              >
                {v.id}
              </span>
              {selected && <span className="text-accent text-[12px]">✓</span>}
            </div>
            <div className="text-[11px] text-muted mt-0.5 leading-relaxed">
              {t(v.description_key)}
            </div>
          </button>
        );
      })}
    </div>
  );
}
