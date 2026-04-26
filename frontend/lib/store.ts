import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { CustomScene } from "./api";

export type Theme = "light" | "dark";

type SessionState = {
  // App chrome
  uiLang: string;          // language the UI is shown in (en/zh/ja)
  theme: Theme;

  // Learning session
  l1: string;              // your native language (used for translations)
  l2: string;              // language you're practicing
  sceneId: string;         // "__custom__" when user-defined
  level: string;
  showReading: boolean;
  showTranslation: boolean;

  // One-off overrides sent to the WS on chat start
  customScene: CustomScene | null;     // populated when sceneId === "__custom__"

  setUiLang: (v: string) => void;
  setTheme: (v: Theme) => void;
  toggleTheme: () => void;
  setL1: (v: string) => void;
  setL2: (v: string) => void;
  setSceneId: (v: string) => void;
  setLevel: (v: string) => void;
  toggleReading: () => void;
  toggleTranslation: () => void;
  setCustomScene: (v: CustomScene | null) => void;
};

const _browserDefault = (): string => {
  if (typeof navigator === "undefined") return "en";
  const lang = navigator.language || "en";
  const short = lang.slice(0, 2).toLowerCase();
  return ["en", "zh", "ja"].includes(short) ? short : "en";
};

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      uiLang: "en",
      theme: "dark",
      l1: "",
      l2: "",
      sceneId: "",
      level: "B1",
      showReading: true,
      showTranslation: true,
      customScene: null,
      setUiLang: (v) => set({ uiLang: v }),
      setTheme: (v) => set({ theme: v }),
      toggleTheme: () =>
        set((s) => ({ theme: s.theme === "dark" ? "light" : "dark" })),
      setL1: (v) => set({ l1: v }),
      setL2: (v) => set({ l2: v }),
      setSceneId: (v) => set({ sceneId: v }),
      setLevel: (v) => set({ level: v }),
      toggleReading: () => set((s) => ({ showReading: !s.showReading })),
      toggleTranslation: () => set((s) => ({ showTranslation: !s.showTranslation })),
      setCustomScene: (v) => set({ customScene: v }),
    }),
    {
      name: "haruspeak.session",
      onRehydrateStorage: () => (state) => {
        if (state && !state.uiLang) state.uiLang = _browserDefault();
      },
    }
  )
);
