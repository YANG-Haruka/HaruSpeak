"use client";

import { useEffect } from "react";
import { useSessionStore } from "@/lib/store";

/**
 * Syncs the <html> element's dark/light class with the persisted theme.
 * Renders nothing — just a side effect on theme changes.
 */
export function ThemeProvider() {
  const theme = useSessionStore((s) => s.theme);

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
      root.classList.remove("light");
    } else {
      root.classList.add("light");
      root.classList.remove("dark");
    }
  }, [theme]);

  return null;
}
