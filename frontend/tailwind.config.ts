import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        "bg-elev": "var(--bg-elev)",
        fg: "var(--fg)",
        muted: "var(--muted)",
        "muted-bg": "var(--muted-bg)",
        border: "var(--border)",
        accent: "var(--accent)",
        "accent-fg": "var(--accent-fg)",
        success: "var(--success)",
        warn: "var(--warn)",
        danger: "var(--danger)",
      },
      borderColor: {
        DEFAULT: "var(--border)",
      },
      maxWidth: {
        readable: "42rem",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"SF Pro Text"',
          '"Segoe UI"',
          "Inter",
          '"Hiragino Sans"',
          '"Noto Sans CJK JP"',
          '"PingFang SC"',
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
} satisfies Config;
