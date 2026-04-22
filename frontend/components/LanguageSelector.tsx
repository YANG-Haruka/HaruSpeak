"use client";

import { useEffect, useState } from "react";
import clsx from "clsx";
import { fetchLanguages, type LanguageMeta } from "@/lib/api";
import { useT } from "@/lib/i18n";

type Props = {
  label: string;
  value: string;
  onChange: (code: string) => void;
  excludeCode?: string;
};

export function LanguageSelector({ label, value, onChange, excludeCode }: Props) {
  const t = useT();
  const [langs, setLangs] = useState<LanguageMeta[]>([]);

  useEffect(() => {
    fetchLanguages().then(setLangs).catch(() => setLangs([]));
  }, []);

  const available = langs.filter((l) => l.code !== excludeCode);

  return (
    <div>
      <label className="block text-[11px] uppercase tracking-widest text-muted mb-2.5 font-medium">
        {label}
      </label>
      <div className="grid grid-cols-3 gap-2">
        {available.map((l) => {
          const selected = value === l.code;
          return (
            <button
              key={l.code}
              disabled={!l.implemented}
              onClick={() => onChange(l.code)}
              className={clsx(
                "px-3 py-3 rounded-2xl border text-[14px] transition",
                selected
                  ? "border-accent bg-accent text-accent-fg shadow-sm"
                  : l.implemented
                  ? "border-border bg-bg-elev text-fg hover:border-muted"
                  : "border-border bg-bg-elev text-muted opacity-50 cursor-not-allowed"
              )}
            >
              <div className="font-medium">{l.display_names[l.code] ?? l.code}</div>
              {!l.implemented && (
                <div className="text-[10px] mt-1 opacity-80">{t("coming_soon")}</div>
              )}
            </button>
          );
        })}
        {langs.length === 0 && (
          <div className="col-span-3 text-[12px] text-muted text-center py-4">
            {t("backend_unreachable")}
          </div>
        )}
      </div>
    </div>
  );
}
