"use client";

import clsx from "clsx";

type Props = {
  level: number;
  threshold?: number;
};

export function LevelMeter({ level, threshold = 0.008 }: Props) {
  const pct = Math.min(100, Math.sqrt(level) * 500);
  const thrPct = Math.min(100, Math.sqrt(threshold) * 500);
  const over = level > threshold;
  return (
    <div className="w-32">
      <div className="h-0.5 bg-muted-bg rounded-full overflow-hidden relative">
        <div
          className={clsx(
            "h-full transition-all duration-100",
            over ? "bg-success" : "bg-muted"
          )}
          style={{ width: `${pct}%` }}
        />
        <div
          className="absolute top-0 h-full w-px bg-danger/40"
          style={{ left: `${thrPct}%` }}
        />
      </div>
    </div>
  );
}
