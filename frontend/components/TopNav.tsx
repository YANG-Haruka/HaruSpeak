"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useSessionStore } from "@/lib/store";
import { useT } from "@/lib/i18n";

type Props = {
  back?: boolean;
  hideSettings?: boolean;
};

export function TopNav({ back = false, hideSettings = false }: Props) {
  const router = useRouter();
  const t = useT();
  const { uiLang, setUiLang, theme, toggleTheme } = useSessionStore();

  return (
    <header className="sticky top-0 z-40 bg-bg/85 backdrop-blur-xl border-b border-border">
      <div className="max-w-readable mx-auto h-12 px-4 flex items-center justify-between">
        {back ? (
          <button
            onClick={() => router.back()}
            className="h-8 px-2 -ml-2 text-[15px] text-accent hover:opacity-80 transition flex items-center gap-0.5"
          >
            <span className="text-lg leading-none">‹</span>
            <span>{t("back")}</span>
          </button>
        ) : (
          <Link href="/" className="h-8 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-[radial-gradient(circle_at_30%_30%,var(--accent)_0%,#1a1a40_70%,#000_100%)]" />
            <span className="text-[15px] font-semibold tracking-tight">
              {t("app_name")}
            </span>
          </Link>
        )}

        <div className="flex items-center gap-0.5">
          <select
            aria-label={t("ui_language")}
            value={uiLang}
            onChange={(e) => setUiLang(e.target.value)}
            className="h-8 px-2 text-[13px] bg-transparent text-fg rounded-lg border-0 cursor-pointer focus:outline-none hover:bg-muted-bg"
            title={t("ui_language")}
          >
            <option value="en">EN</option>
            <option value="zh">中文</option>
            <option value="ja">日本語</option>
          </select>

          <button
            onClick={toggleTheme}
            aria-label={t("toggle_theme")}
            title={t(theme === "dark" ? "theme_light" : "theme_dark")}
            className="w-8 h-8 rounded-lg hover:bg-muted-bg text-muted hover:text-fg transition flex items-center justify-center text-[14px]"
          >
            {theme === "dark" ? "☀" : "☾"}
          </button>

          {!hideSettings && (
            <Link
              href="/settings"
              aria-label={t("settings")}
              title={t("settings")}
              className="w-8 h-8 rounded-lg hover:bg-muted-bg text-muted hover:text-fg transition flex items-center justify-center text-[15px]"
            >
              ⚙
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
