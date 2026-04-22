"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import {
  fetchSTTModels,
  startSTTDownload,
  fetchSTTDownloadStatus,
  deleteSTTModel,
  type STTModelMeta,
} from "@/lib/api";
import { useT } from "@/lib/i18n";

type Props = {
  // Current backend selection expressed as the (provider, faster_whisper_size) pair.
  currentProvider: string;
  currentWhisperSize: string;
  onPick: (next: { provider: string; faster_whisper_size?: string }) => void;
};

function humanMB(mb: number): string {
  if (mb <= 0) return "—";
  return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb} MB`;
}

export function STTModelPicker({ currentProvider, currentWhisperSize, onPick }: Props) {
  const t = useT();
  const [models, setModels] = useState<STTModelMeta[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    const m = await fetchSTTModels();
    setModels(m);
  };

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, []);

  const isSelected = (m: STTModelMeta) => {
    if (m.provider !== currentProvider) return false;
    if (m.provider === "faster_whisper") {
      return m.faster_whisper_size === currentWhisperSize;
    }
    return true;
  };

  const download = async (m: STTModelMeta) => {
    setModels((prev) =>
      prev.map((x) => (x.id === m.id ? { ...x, download_state: "downloading" } : x))
    );
    await startSTTDownload(m.id);
    const id = window.setInterval(async () => {
      const s = await fetchSTTDownloadStatus(m.id);
      if (s.state === "done" || s.state === "error") {
        window.clearInterval(id);
        await refresh();
      }
    }, 2000);
  };

  const remove = async (m: STTModelMeta) => {
    const prompt = t("stt_confirm_delete").replace("{name}", m.name);
    if (!window.confirm(prompt)) return;
    try {
      await deleteSTTModel(m.id);
      await refresh();
    } catch (e) {
      console.error("[stt] delete failed", e);
    }
  };

  const select = (m: STTModelMeta) => {
    // If the user clicks an un-downloaded local model, auto-start the
    // download instead of silently doing nothing. Selection only applies
    // once the download completes — they'll need to click again then.
    if (!m.installed && m.hf_repo) {
      if (m.download_state !== "downloading") download(m);
      return;
    }
    onPick({
      provider: m.provider,
      faster_whisper_size: m.faster_whisper_size,
    });
  };

  if (loading) return <div className="text-[12px] text-muted">…</div>;

  return (
    <div className="rounded-2xl border border-border bg-bg-elev/40 divide-y divide-border overflow-hidden">
      {models.map((m) => {
        const selected = isSelected(m);
        const local = Boolean(m.hf_repo);
        return (
          <div
            key={m.id}
            className={clsx(
              "px-4 py-3 flex items-start gap-3 transition",
              selected && "bg-accent/10"
            )}
          >
            <button
              onClick={() => select(m)}
              className="flex-1 text-left min-w-0 cursor-pointer"
            >
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={clsx(
                    "text-[14px] font-medium truncate",
                    selected ? "text-accent" : "text-fg"
                  )}
                >
                  {m.name}
                </span>
                {m.recommended && (
                  <span className="text-[10px] bg-success/15 text-success px-1.5 py-0.5 rounded-full font-medium">
                    {t("stt_recommended")}
                  </span>
                )}
                {selected && <span className="text-accent text-[12px]">✓</span>}
              </div>
              <div className="text-[11px] text-muted mt-0.5 leading-relaxed">
                {t(m.description_key)}
              </div>
              <div className="text-[11px] text-muted mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
                {local ? (
                  <>
                    <span>{t("stt_size")} · {humanMB(m.size_mb)}</span>
                    <span>{t("stt_vram")} · {humanMB(m.vram_mb)}</span>
                  </>
                ) : (
                  <span>{t("stt_api_based")}</span>
                )}
              </div>
            </button>

            {/* Right-hand status cell */}
            <div className="flex-shrink-0 w-28 text-right">
              {!local ? (
                <span className="text-[11px] text-muted">—</span>
              ) : m.installed ? (
                <div className="flex flex-col items-end gap-1">
                  <span className="text-[12px] text-success inline-flex items-center gap-1">
                    ✓ {t("stt_installed")}
                  </span>
                  <button
                    onClick={() => remove(m)}
                    className="text-[11px] text-muted hover:text-danger transition"
                    title={t("stt_delete")}
                  >
                    {t("stt_delete")}
                  </button>
                </div>
              ) : m.download_state === "downloading" ? (
                <span className="text-[11px] text-muted inline-flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full border-2 border-muted border-t-transparent animate-spin" />
                  {t("stt_downloading")}
                </span>
              ) : m.download_state === "error" ? (
                <button
                  onClick={() => download(m)}
                  className="text-[11px] text-danger underline"
                  title={m.download_error ?? ""}
                >
                  {t("stt_download_failed")}
                </button>
              ) : (
                <button
                  onClick={() => download(m)}
                  className="text-[12px] px-3 py-1 rounded-lg bg-accent text-accent-fg font-medium hover:opacity-90 transition"
                >
                  {t("stt_download")}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
