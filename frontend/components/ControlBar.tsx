"use client";

import clsx from "clsx";
import { useT } from "@/lib/i18n";

type Props = {
  connected: boolean;
  paused: boolean;
  speaking: boolean;
  onTogglePaused: () => void;
  onInterrupt?: () => void;
};

export function ControlBar({
  connected,
  paused,
  speaking,
  onTogglePaused,
  onInterrupt,
}: Props) {
  const t = useT();
  return (
    <div className="border-t border-border bg-bg">
      <div className="max-w-readable mx-auto flex items-center justify-center gap-12 px-5 py-8">
        <button
          className="w-11 h-11 rounded-full flex items-center justify-center text-muted hover:text-fg hover:bg-muted-bg transition"
          aria-label={t("interrupt_ai")}
          onClick={onInterrupt}
          title={t("interrupt_ai")}
        >
          <span className="text-[18px]">⏸</span>
        </button>

        <button
          aria-label={paused ? t("listen_resume") : t("listen_pause")}
          onClick={onTogglePaused}
          disabled={!connected}
          className={clsx(
            "w-16 h-16 rounded-full flex items-center justify-center text-white shadow-md transition-transform active:scale-95",
            paused
              ? "bg-muted"
              : speaking
              ? "bg-danger animate-pulse"
              : "bg-accent",
            !connected && "!bg-muted-bg !text-muted cursor-not-allowed"
          )}
        >
          <span className="text-[22px]">{paused ? "🔇" : "🎙"}</span>
        </button>

        <div
          className={clsx(
            "w-11 text-[11px] tracking-wide text-center",
            paused ? "text-muted" : speaking ? "text-danger" : "text-accent"
          )}
        >
          {paused
            ? t("mic_muted")
            : speaking
            ? t("mic_speaking")
            : t("mic_listening")}
        </div>
      </div>
    </div>
  );
}
