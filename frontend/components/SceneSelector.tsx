"use client";

import clsx from "clsx";
import type { SceneMeta } from "@/lib/api";
import { useT } from "@/lib/i18n";

function titleFor(s: SceneMeta, l2: string): string {
  if (s.titles && s.titles[l2]) return s.titles[l2];
  if (typeof s.title === "string") return s.title;
  return s.id;
}

function descFor(s: SceneMeta, l2: string): string {
  if (typeof s.description === "string") return s.description;
  if (s.description && typeof s.description === "object") return s.description[l2] ?? "";
  return "";
}

export function SceneSelector({
  scenes,
  l2,
  onPick,
  onCustom,
}: {
  scenes: SceneMeta[];
  l2: string;
  onPick: (id: string) => void;
  onCustom?: () => void;
}) {
  const t = useT();
  const common = scenes.filter((s) => s.source === "common");
  const specific = scenes.filter((s) => s.source !== "common");

  return (
    <div className="space-y-8">
      {common.length > 0 && (
        <Section title={t("common_scenes")}>
          {common.map((s) => (
            <Pill
              key={s.id}
              label={titleFor(s, l2)}
              hint={descFor(s, l2)}
              onClick={() => onPick(s.id)}
            />
          ))}
        </Section>
      )}

      {specific.length > 0 && (
        <Section title={t("specific_scenes_for").replace("{l2}", l2.toUpperCase())}>
          {specific.map((s) => (
            <Pill
              key={s.id}
              label={titleFor(s, l2)}
              hint={descFor(s, l2)}
              onClick={() => onPick(s.id)}
            />
          ))}
          {onCustom && (
            <Pill
              label={`+ ${t("custom_scene")}`}
              hint={t("create_custom_scene")}
              onClick={onCustom}
              dashed
            />
          )}
        </Section>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-[13px] text-muted mb-3 font-medium">{title}</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">{children}</div>
    </div>
  );
}

function Pill({
  label,
  hint,
  onClick,
  dashed = false,
}: {
  label: string;
  hint?: string;
  onClick: () => void;
  dashed?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={hint}
      className={clsx(
        "px-3 py-3 rounded-2xl border text-[14px] text-center transition",
        "bg-bg-elev text-fg hover:border-muted hover:bg-muted-bg",
        dashed ? "border-dashed border-border text-muted" : "border-border"
      )}
    >
      <div className="font-medium truncate">{label}</div>
    </button>
  );
}
