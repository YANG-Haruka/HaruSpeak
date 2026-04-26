/**
 * Backend URL resolution.
 *
 * By default we use RELATIVE paths — Next.js reverse-proxies /api/* and /ws/*
 * to the backend (see next.config.js rewrites). This means the whole app
 * speaks a single origin, so one HTTPS tunnel (cloudflared/ngrok) pointed at
 * port 3000 covers both frontend + backend without CORS or mixed-content.
 *
 * NEXT_PUBLIC_BACKEND_URL overrides everything — only needed if you want the
 * browser to bypass the proxy and talk to the backend directly.
 */
function backendBase(): string {
  return process.env.NEXT_PUBLIC_BACKEND_URL ?? "";
}

export type SceneMeta = {
  id: string;
  title?: string;
  titles?: Record<string, string>;
  description?: string | Record<string, string>;
  difficulty?: string;
  source?: string;
  language?: string;
  languages?: string[];
};

export type CustomScene = {
  title: string;
  description: string;
  /** Scene-level role for the AI (e.g. "real estate agent"). Goes into
   * the scene definition, not the deprecated user-pickable persona system. */
  persona?: string;
  opening_line?: string;
};

export type LanguageMeta = {
  code: string;
  display_names: Record<string, string>;
  unit_kind: string;
  implemented: boolean;
};

export async function fetchLanguages(): Promise<LanguageMeta[]> {
  const r = await fetch(`${backendBase()}/api/languages`);
  const j = await r.json();
  return j.languages;
}

export async function fetchScenes(l2: string): Promise<SceneMeta[]> {
  const r = await fetch(`${backendBase()}/api/scenes?l2=${l2}`);
  const j = await r.json();
  return j.scenes;
}

export type STTModelMeta = {
  id: string;
  provider: string;
  faster_whisper_size?: string;
  name: string;
  hf_repo: string | null;
  size_mb: number;
  vram_mb: number;
  recommended?: boolean;
  description_key: string;  // frontend looks up in its i18n bundle
  installed: boolean;
  download_state: "idle" | "downloading" | "done" | "error";
  download_error?: string | null;
};

export async function fetchSTTModels(): Promise<STTModelMeta[]> {
  const r = await fetch(`${backendBase()}/api/stt/models`);
  const j = await r.json();
  return j.models ?? [];
}

export async function startSTTDownload(modelId: string): Promise<{ state: string }> {
  const r = await fetch(`${backendBase()}/api/stt/models/${modelId}/download`, { method: "POST" });
  return r.json();
}

export async function fetchSTTDownloadStatus(modelId: string): Promise<{ state: string; error?: string }> {
  const r = await fetch(`${backendBase()}/api/stt/models/${modelId}/status`);
  return r.json();
}

export async function deleteSTTModel(modelId: string): Promise<{ ok: boolean; deleted?: boolean }> {
  const r = await fetch(`${backendBase()}/api/stt/models/${modelId}`, { method: "DELETE" });
  if (!r.ok) throw new Error(`delete failed: ${r.status}`);
  return r.json();
}

export function wsChatURL(): string {
  const override = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (override) return override.replace(/^http/, "ws") + "/ws/chat";
  if (typeof window === "undefined") return "ws://localhost:3000/ws/chat";
  // Same origin — lets the Next.js dev server proxy the WS upgrade to :8000
  // (and lets HTTPS tunnels like cloudflared cover WS too via wss://).
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  return `${scheme}://${window.location.host}/ws/chat`;
}
