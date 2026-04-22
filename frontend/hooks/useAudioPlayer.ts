"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Audio playback with:
 *   - play(base64, mime)  swap src on a persistent <audio> element
 *   - stop()              pause without destroying the element (barge-in)
 *   - unlock()            call ONCE from inside a user-gesture handler
 *
 * Why one persistent element? iOS Safari's autoplay unlock is per-element,
 * not per-origin. If you `new Audio()` after the gesture, the new element
 * is NOT unlocked and `play()` silently rejects. So we create the element
 * during unlock() and reuse it for every turn.
 */

const SILENT_MP3 =
  "data:audio/mpeg;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4LjQ1LjEwMAAAAAAAAAAAAAAA//uQZAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAADAAABgAA8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8PDw8P////////////////////////////////8AAAAATGF2YzU4LjkxAAAAAAAAAAAAAAAAJAAAAAAAAAAAAYBBVXiYwAAAAAAAAAAAAAAAAAAAAP/7kGQAD/AAAGkAAAAIAAANIAAAAQAAAaQAAAAgAAA0gAAABExBTUUzLjEwMFVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV";

export function useAudioPlayer(onEnded?: () => void) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);
  const unlockedRef = useRef(false);
  const [playing, setPlaying] = useState(false);

  const _ensureElement = (): HTMLAudioElement => {
    if (audioRef.current) return audioRef.current;
    const audio = new Audio();
    audio.preload = "auto";
    audio.onended = () => {
      setPlaying(false);
      onEnded?.();
    };
    audio.onerror = () => setPlaying(false);
    audioRef.current = audio;
    return audio;
  };

  /** Must be invoked synchronously inside a click/touchend handler, ONCE. */
  const unlock = useCallback(() => {
    if (unlockedRef.current) return;
    const audio = _ensureElement();
    // Satisfy the gesture requirement: play silent mp3 on the element we'll
    // keep reusing. iOS remembers this element as "user-initiated".
    audio.src = SILENT_MP3;
    audio.play().catch(() => {
      /* even a rejected play() here often unlocks the element; swallow */
    });
    unlockedRef.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Pause without destroying the element, so subsequent play() still works. */
  const stop = useCallback(() => {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      try {
        audio.currentTime = 0;
      } catch {
        /* some browsers throw if src not set yet */
      }
    }
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
    setPlaying(false);
  }, []);

  const play = useCallback(
    (base64: string, mime: string = "audio/mpeg") => {
      // Release previous blob URL (but keep the <audio> element alive)
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
        urlRef.current = null;
      }
      const bytes = base64ToBytes(base64);
      const blob = new Blob([bytes], { type: mime });
      const url = URL.createObjectURL(blob);
      urlRef.current = url;

      const audio = _ensureElement();
      audio.src = url;
      audio.load();             // safe to call; forces re-read of new src
      setPlaying(true);
      audio.play().catch((err) => {
        console.warn("[audio] play() rejected:", err);
        setPlaying(false);
      });
      // eslint-disable-next-line react-hooks/exhaustive-deps
    },
    [onEnded]
  );

  // Final cleanup when the component unmounts
  useEffect(() => {
    return () => {
      const audio = audioRef.current;
      if (audio) {
        audio.pause();
        audio.removeAttribute("src");
        audio.load();
      }
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current);
        urlRef.current = null;
      }
    };
  }, []);

  return { play, stop, unlock, playing };
}

function base64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}
