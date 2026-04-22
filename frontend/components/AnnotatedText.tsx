"use client";

import type { AnnotatedTextDTO, Token } from "@/hooks/useChatSocket";
import { useSessionStore } from "@/lib/store";

/**
 * Renders annotated text using HTML5 <ruby>.
 * JP: furigana (hiragana above kanji)
 * ZH: pinyin with tones above hanzi
 * EN: no base reading; optional IPA tooltip for is_new tokens
 */
export function AnnotatedText({ annotated }: { annotated: AnnotatedTextDTO }) {
  const show = useSessionStore((s) => s.showReading);

  return (
    <span>
      {annotated.tokens.map((t, i) => (
        <TokenSpan key={i} token={t} lang={annotated.language} showReading={show} />
      ))}
    </span>
  );
}

function TokenSpan({
  token,
  lang,
  showReading,
}: {
  token: Token;
  lang: string;
  showReading: boolean;
}) {
  const hasReading = showReading && !!token.reading && lang !== "en";
  if (hasReading) {
    return (
      <ruby>
        {token.surface}
        <rt>{token.reading}</rt>
      </ruby>
    );
  }
  if (lang === "en" && token.is_new && token.ipa) {
    return (
      <span title={token.ipa} className="underline decoration-dotted decoration-neutral-400">
        {token.surface}
      </span>
    );
  }
  return <span>{token.surface}</span>;
}
