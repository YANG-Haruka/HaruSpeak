"use client";

import { useRouter } from "next/navigation";
import { LanguageSelector } from "@/components/LanguageSelector";
import { TopNav } from "@/components/TopNav";
import { useSessionStore } from "@/lib/store";
import { useT } from "@/lib/i18n";

export default function HomePage() {
  const router = useRouter();
  const t = useT();
  const { l1, l2, setL1, setL2 } = useSessionStore();

  const canProceed = l1 && l2 && l1 !== l2;

  return (
    <>
      <TopNav />
      <main className="max-w-md mx-auto w-full px-5 pt-10 pb-12 space-y-10">
        <div className="text-center">
          <div className="mx-auto w-20 h-20 rounded-full bg-[radial-gradient(circle_at_30%_30%,var(--accent)_0%,#1a1a40_65%,#000_100%)] mb-5 orb-idle" />
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
