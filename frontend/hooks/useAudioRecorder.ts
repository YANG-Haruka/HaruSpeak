"use client";

import { useCallback, useRef, useState } from "react";

type Options = {
  onStart?: () => void;
  onStop?: (blob: Blob) => void;
  onError?: (message: string) => void;
};

/**
 * Click-to-toggle microphone recorder.
 * Surfaces getUserMedia errors via onError so the UI can show them.
 * Hard cap at 30s to protect against runaway recording.
 */
export function useAudioRecorder({ onStart, onStop, onError }: Options = {}) {
  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const timerRef = useRef<number | null>(null);
  const [recording, setRecording] = useState(false);

  const clearTimer = () => {
    if (timerRef.current != null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const stop = useCallback(() => {
    clearTimer();
    recRef.current?.stop();
  }, []);

  const start = useCallback(async () => {
    if (recording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        if (blob.size === 0) {
          onError?.("No audio captured — speak louder or check mic permission.");
          return;
        }
        onStop?.(blob);
      };
      mr.onerror = (e) => {
        onError?.(`MediaRecorder error: ${(e as any).error?.message ?? e}`);
      };
      mr.start();
      recRef.current = mr;
      setRecording(true);
      onStart?.();
      // Auto-stop after 30s as a runaway safety net
      timerRef.current = window.setTimeout(() => {
        if (recRef.current?.state === "recording") {
          recRef.current.stop();
        }
      }, 30_000);
    } catch (err) {
      const msg =
        err instanceof Error
          ? `${err.name}: ${err.message}`
          : "Unknown microphone error";
      onError?.(msg);
    }
  }, [recording, onStart, onStop, onError]);

  const toggle = useCallback(() => {
    if (recording) stop();
    else start();
  }, [recording, start, stop]);

  return { start, stop, toggle, recording };
}
