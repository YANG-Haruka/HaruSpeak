"use client";

import { useEffect, useRef, useState } from "react";
import { wsChatURL } from "@/lib/api";

export type Token = {
  surface: string;
  reading?: string | null;
  ipa?: string | null;
  gloss?: string | null;
  pos?: string | null;
  is_new?: boolean;
};

export type AnnotatedTextDTO = {
  language: string;
  tokens: Token[];
};

export type AITurn = {
  role: "assistant";
  text: string;
  annotated: AnnotatedTextDTO | null;
  translation?: string | null;
  audio_mime?: string | null;
  audio_b64?: string | null;
  suggestions?: Suggestion[];
};

export type Suggestion = {
  tier: "short" | "polite" | "detailed";
  text: string;
  annotated: AnnotatedTextDTO;
  translation?: string | null;
};

export type TurnResult = {
  transcript: { text: string; language: string };
  ai_reply: AITurn;
  suggestions: Suggestion[];
};

type Options = {
  l1: string;
  l2: string;
  sceneId: string;
  /** Populated when sceneId === "__custom__" — user-typed scene payload. */
  customScene?: { title: string; description: string; persona?: string; opening_line?: string } | null;
  /** Fired for the scene's opening AI message (includes audio + suggestions). */
  onAITurn?: (t: AITurn) => void;
  /** Fired as soon as LLM text is ready (before TTS / translation / suggestions). */
  onAIText?: (p: { text: string; annotated: AnnotatedTextDTO | null }) => void;
  /** Fired for each token/chunk of the streamed LLM reply (append to UI live). */
  onAITextDelta?: (delta: string) => void;
  /** Fired when TTS MP3 is ready. */
  onAIAudio?: (p: { audio_mime: string | null; audio_b64: string | null }) => void;
  /** Fired when the L1 translation of the AI reply is ready. */
  onAITranslation?: (translation: string) => void;
  /** Fired when the three-tier reply suggestions are ready. */
  onSuggestions?: (s: Suggestion[]) => void;
  /** Fired when user's STT transcript is ready (before AI reply). */
  onTranscript?: (t: { text: string; language: string }) => void;
  /** Fired when all pipeline stages for the current turn are done. */
  onTurnDone?: () => void;
  onError?: (msg: string) => void;
};

export function useChatSocket({
  l1,
  l2,
  sceneId,
  customScene,
  onAITurn,
  onAIText,
  onAITextDelta,
  onAIAudio,
  onAITranslation,
  onSuggestions,
  onTranscript,
  onTurnDone,
  onError,
}: Options) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!l1 || !l2 || !sceneId) return;
    const ws = new WebSocket(wsChatURL());
    wsRef.current = ws;

    ws.onopen = () => {
      const init: Record<string, unknown> = { l1, l2, scene_id: sceneId };
      if (customScene) init.custom_scene = customScene;
      ws.send(JSON.stringify(init));
      setConnected(true);
    };
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        switch (data.type) {
          case "ai_turn":
            // Opening line (all in one frame)
            onAITurn?.({
              role: "assistant",
              text: data.text,
              annotated: data.annotated ?? null,
              translation: data.translation ?? null,
              audio_mime: data.audio_mime ?? null,
              audio_b64: data.audio_b64 ?? null,
              suggestions: data.suggestions ?? [],
            });
            break;
          case "transcript":
            onTranscript?.(data.transcript);
            break;
          case "ai_text_delta":
            onAITextDelta?.(data.delta ?? "");
            break;
          case "ai_text":
            onAIText?.({ text: data.text, annotated: data.annotated ?? null });
            break;
          case "ai_audio":
            onAIAudio?.({
              audio_mime: data.audio_mime ?? null,
              audio_b64: data.audio_b64 ?? null,
            });
            break;
          case "ai_translation":
            onAITranslation?.(data.translation ?? "");
            break;
          case "suggestions":
            onSuggestions?.(data.suggestions ?? []);
            break;
          case "turn_done":
            onTurnDone?.();
            break;
          case "error":
            onError?.(data.message ?? "unknown error");
            break;
        }
      } catch {
        /* ignore malformed frames */
      }
    };

    return () => ws.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [l1, l2, sceneId]);

  const sendAudio = (buf: ArrayBuffer) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    const b64 = arrayBufferToBase64(buf);
    ws.send(JSON.stringify({ audio_b64: b64, done: true }));
  };

  return { connected, sendAudio };
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}
