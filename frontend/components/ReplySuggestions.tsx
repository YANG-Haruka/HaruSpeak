"use client";

import type { Suggestion } from "@/hooks/useChatSocket";
import { useSessionStore } from "@/lib/store";
import { AnnotatedText } from "./AnnotatedText";

const TIER_LABEL: Record<Suggestion["tier"], string> = {
  short: "SHORT",
  polite: "POLITE",
  detailed: "DETAILED",
};

export function ReplySuggestions({ suggestions }: { suggestions: Suggestion[] }) {
  // Honour the same translation toggle the AI's reply uses, so the user
  // can hide everything L1 in one switch.
  const showTranslation = useSessionStore((s) => s.showTranslation);
  return (
    <div className="w-full max-w-readable space-y-2 px-1">
      {suggestions.map((s, i) => (
        <div
          key={i}
          className="p-4 rounded-2xl bg-bg-elev border border-border"
        >
          <div className="text-[10px] font-semibold tracking-widest text-muted mb-1.5">
            {TIER_LABEL[s.tier] ?? s.tier.toUpperCase()}
          </div>
          <div className="text-[15px] leading-relaxed text-fg">
            <AnnotatedText annotated={s.annotated} />
          </div>
          {showTranslation && s.translation && (
            <div className="mt-1.5 text-[12px] leading-relaxed text-muted">
              {s.translation}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
