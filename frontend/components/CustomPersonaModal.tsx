"use client";

import { useState } from "react";
import { useT } from "@/lib/i18n";
import type { PersonaOverride } from "@/lib/api";

export function CustomPersonaModal({
  onCancel,
  onSubmit,
}: {
  onCancel: () => void;
  onSubmit: (p: PersonaOverride) => void;
}) {
  const t = useT();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const ready = description.trim();

  return (
    <div
      className="fixed inset-0 z-50 bg-bg/80 backdrop-blur-xl flex items-center justify-center p-4 animate-[fadeIn_180ms_ease-out]"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-md rounded-3xl bg-bg-elev border border-border p-6 space-y-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-[18px] font-semibold tracking-tight">
          {t("create_custom_persona")}
        </h3>

        <Field label={t("persona_name_label")}>
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("persona_name_placeholder")}
            className={inputCls}
          />
        </Field>

        <Field label={t("persona_description_label")}>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t("persona_description_placeholder")}
            rows={3}
            className={inputCls + " resize-none"}
          />
        </Field>

        <div className="flex gap-2 pt-2">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 rounded-xl border border-border text-muted hover:text-fg hover:bg-muted-bg transition text-sm"
          >
            {t("cancel")}
          </button>
          <button
            onClick={() =>
              ready &&
              onSubmit({
                name: name.trim() || undefined,
                description: description.trim(),
              })
            }
            disabled={!ready}
            className="flex-1 py-2.5 rounded-xl bg-accent text-accent-fg font-medium disabled:bg-muted-bg disabled:text-muted disabled:cursor-not-allowed transition text-sm"
          >
            {t("use_it")}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[12px] text-muted font-medium">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "w-full px-3 py-2.5 rounded-xl bg-bg border border-border text-fg text-sm focus:outline-none focus:border-accent transition";
