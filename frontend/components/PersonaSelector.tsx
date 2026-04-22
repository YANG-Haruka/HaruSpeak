"use client";

import clsx from "clsx";
import type { PersonaMeta } from "@/lib/api";
import { useT } from "@/lib/i18n";

export function PersonaSelector({
  personas,
  selectedId,
  onPick,
  onCustom,
}: {
  personas: PersonaMeta[];
  selectedId: string | null;
  onPick: (p: PersonaMeta | null) => void;
  onCustom: () => void;
}) {
  const t = useT();
  if (personas.length === 0) return null;

  return (
    <div>
      <h3 className="text-[13px] text-muted mb-3 font-medium">
        {t("characters")}
      </h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <Pill
          label={t("skip_persona")}
          hint={t("use_scene_default_persona")}
          active={selectedId === null}
          onClick={() => onPick(null)}
          dashed
        />
        {personas.map((p) => (
          <Pill
            key={p.id}
            label={p.name}
            hint={p.description}
            active={selectedId === p.id}
            onClick={() => onPick(p)}
          />
        ))}
        <Pill
          label={`+ ${t("custom_persona")}`}
          hint={t("create_custom_persona")}
          onClick={onCustom}
          dashed
        />
      </div>
    </div>
  );
}

function Pill({
  label,
  hint,
  active = false,
  onClick,
  dashed = false,
}: {
  label: string;
  hint?: string;
  active?: boolean;
  onClick: () => void;
  dashed?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={hint}
      className={clsx(
        "px-3 py-3 rounded-2xl border text-[14px] text-center transition",
        active
          ? "border-accent bg-accent text-accent-fg shadow-sm"
          : dashed
          ? "border-dashed border-border bg-bg-elev text-muted hover:border-muted hover:bg-muted-bg"
          : "border-border bg-bg-elev text-fg hover:border-muted hover:bg-muted-bg"
      )}
    >
      <div className="font-medium truncate">{label}</div>
    </button>
  );
}
