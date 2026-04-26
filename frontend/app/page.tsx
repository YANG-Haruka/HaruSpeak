"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LanguageSelector } from "@/components/LanguageSelector";
import { TopNav } from "@/components/TopNav";
import { useSessionStore } from "@/lib/store";
import { useT } from "@/lib/i18n";

export default function HomePage() {
  const router = useRouter();
  const t = useT();
  const { l1, l2, setL1, setL2 } = useSessionStore();

  // null = still checking, true/false = decided. Treated as `true` while
  // checking so the user doesn't see a spurious warning flash on first paint.
  const [llmConfigured, setLlmConfigured] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/settings")
      .then((r) => r.json())
      .then((s) => {
        if (cancelled) return;
        // Quick local check, not a live probe — settings page does the real
        // probe. For openai we only need an api_key; for LM Studio we only
        // need a model id (assume the user-configured server is running).
        const ok =
          s.llm_provider === "openai_lmstudio"
            ? Boolean(s.lmstudio_model)
            : Boolean(s.openai_api_key);
        setLlmConfigured(ok);
      })
      .catch(() => {
        // Backend unreachable; let the user proceed and fail visibly later.
        if (!cancelled) setLlmConfigured(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const llmReady = llmConfigured !== false;
  const canProceed = l1 && l2 && l1 !== l2 && llmReady;

  return (
    <>
      <TopNav />
      <main className="max-w-md mx-auto w-full px-5 pt-10 pb-12 space-y-10">
        <div className="text-center">
          <img
            src="/icon.png"
            alt={t("app_name")}
            className="mx-auto w-20 h-20 mb-5 orb-idle"
            draggable={false}
          />
          <h1 className="text-[26px] font-semibold tracking-tight">
            {t("app_name")}
          </h1>
          <p className="text-[14px] text-muted mt-2">{t("tagline")}</p>
        </div>

        <div className="space-y-5">
          <LanguageSelector
            label={t("select_l1")}
            value={l1}
            onChange={setL1}
          />
          <LanguageSelector
            label={t("select_l2")}
            value={l2}
            onChange={setL2}
            excludeCode={l1}
          />
        </div>

        {llmConfigured === false && (
          <button
            onClick={() => router.push("/settings/")}
            className="w-full px-4 py-3 rounded-2xl border border-amber-500/40 bg-amber-500/10 text-[13px] text-amber-200 hover:bg-amber-500/15 transition text-left flex items-start gap-2.5"
          >
            <span className="text-base leading-tight">⚠</span>
            <span className="flex-1">
              <span className="block font-medium">{t("setup_llm_required")}</span>
              <span className="block text-amber-300/80 mt-0.5">
                {t("go_to_settings")} ›
              </span>
            </span>
          </button>
        )}

        <button
          disabled={!canProceed}
          onClick={() => router.push("/scene")}
          className="w-full py-3.5 rounded-full text-[16px] font-semibold transition active:scale-[0.98] bg-accent text-accent-fg shadow-sm hover:opacity-90 disabled:bg-transparent disabled:text-muted disabled:border disabled:border-border disabled:shadow-none disabled:cursor-not-allowed"
        >
          {t("next")}
        </button>
      </main>
    </>
  );
}
