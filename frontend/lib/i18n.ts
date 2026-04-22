"use client";

import zh from "@/i18n/zh.json";
import ja from "@/i18n/ja.json";
import en from "@/i18n/en.json";
import { useSessionStore } from "./store";

type Dict = Record<string, string>;
const dicts: Record<string, Dict> = { zh, ja, en };
const fallback: Dict = en;

/** Read UI strings for the user's chosen UI language (independent of L1). */
export function useT() {
  const uiLang = useSessionStore((s) => s.uiLang);
  const dict = dicts[uiLang] ?? fallback;
  return (key: string): string => dict[key] ?? fallback[key] ?? key;
}
