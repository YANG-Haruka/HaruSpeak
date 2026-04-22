"use client";

import clsx from "clsx";
import { useT } from "@/lib/i18n";

export type OrbState = "idle" | "speaking" | "listening" | "processing";

const GRADIENTS: Record<OrbState, string> = {
  idle:       "bg-[radial-gradient(circle_at_30%_30%,#4f46e5_0%,#1e1b4b_55%,#000_100%)]",
  speaking:   "bg-[radial-gradient(circle_at_30%_30%,#60a5fa_0%,#1e3a8a_55%,#000_100%)]",
  listening:  "bg-[radial-gradient(circle_at_30%_30%,#fb7185_0%,#881337_55%,#000_100%)]",
  processing: "bg-[radial-gradient(circle_at_30%_30%,#a1a1aa_0%,#27272a_55%,#000_100%)]",
};

const ANIM: Record<OrbState, string> = {
  idle: "orb-idle",
  speaking: "orb-speaking",
  listening: "orb-listening",
  processing: "orb-processing",
};

const LABEL_KEY: Record<OrbState, string> = {
  idle: "tap_to_speak",
  listening: "listening",
  speaking: "ai_speaking",
  processing: "processing",
};

export function VoiceOrb({
  state,
  intensity = 0,
}: {
  state: OrbState;
  intensity?: number;
}) {
  const t = useT();
  const scale = 1 + Math.min(0.2, Math.max(0, intensity) * 0.2);
  return (
    <div className="flex flex-col items-center gap-6">
      <div className="relative w-56 h-56 sm:w-64 sm:h-64">
        <div
          className={clsx(
            "absolute inset-0 rounded-full transition-[background] duration-700",
            GRADIENTS[state],
            ANIM[state]
          )}
          style={{ transform: `scale(${scale.toFixed(3)})` }}
        />
        {/* glossy highlight */}
        <div className="absolute inset-0 rounded-full bg-[radial-gradient(circle_at_25%_20%,rgba(255,255,255,0.18)_0%,transparent_35%)] pointer-events-none" />
      </div>
      <span className="text-[11px] tracking-widest uppercase text-muted font-medium">
        {t(LABEL_KEY[state])}
      </span>
    </div>
  );
}
