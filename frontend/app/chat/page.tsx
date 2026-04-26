"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/store";
import {
  useChatSocket,
  type AITurn,
  type Suggestion,
} from "@/hooks/useChatSocket";
import { useVADRecorder } from "@/hooks/useVADRecorder";
import { useAudioPlayer } from "@/hooks/useAudioPlayer";
import { useT } from "@/lib/i18n";
import { TopNav } from "@/components/TopNav";
import { VoiceOrb, type OrbState } from "@/components/VoiceOrb";
import { AnnotatedText } from "@/components/AnnotatedText";
import { ReplySuggestions } from "@/components/ReplySuggestions";
import { ControlBar } from "@/components/ControlBar";
import { LevelMeter } from "@/components/LevelMeter";

export default function ChatPage() {
  const router = useRouter();
  const t = useT();
  const { l1, l2, sceneId, showTranslation, customScene } = useSessionStore();
  const [orb, setOrb] = useState<OrbState>("idle");
  const [aiTurn, setAiTurn] = useState<AITurn | null>(null);
  const [streamingText, setStreamingText] = useState<string>("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [lastUserTranscript, setLastUserTranscript] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [micPaused, setMicPaused] = useState(false);
  const [started, setStarted] = useState(false);
  const [sttReady, setSttReady] = useState(false);
  const [openingReady, setOpeningReady] = useState(false);
  const pendingOpeningRef = useRef<AITurn | null>(null);

  const player = useAudioPlayer(() => setOrb("idle"));

  // Poll /healthz until STT reports ready. Cheap enough: a few GETs over
  // the first 5-10 seconds, then silent.
  useEffect(() => {
    if (sttReady) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const r = await fetch("/healthz", { cache: "no-store" });
        const j = await r.json();
        if (!cancelled && j.stt_ready) setSttReady(true);
      } catch {
        /* backend not up yet — keep polling */
      }
    };
    tick();
    const id = window.setInterval(tick, 1200);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [sttReady]);

  const handleAITurn = useCallback(
    (turn: AITurn) => {
      setAiTurn(turn);
      if (turn.suggestions && turn.suggestions.length > 0) {
        setSuggestions(turn.suggestions);
      }
      // Always buffer the opening turn and flag "ready" — the Start button
      // stays in loading state until this fires, then becomes clickable.
      // Audio only plays when the user actually clicks Start (also satisfies
      // browser autoplay policy).
      pendingOpeningRef.current = turn;
      setOpeningReady(true);
      setOrb("idle");
    },
    []
  );

  const { sendAudio, connected } = useChatSocket({
    l1,
    l2,
    sceneId,
    customScene,
    onAITurn: handleAITurn,
    onTranscript: (t) => setLastUserTranscript(t.text),
    onAITextDelta: (delta) => {
      setStreamingText((prev) => {
        if (prev === "") {
          setSuggestions([]);
          setAiTurn(null);
          setOrb("idle");
        }
        return prev + delta;
      });
    },
    onAIText: ({ text, annotated }) => {
      setStreamingText("");
      setAiTurn({
        role: "assistant",
        text,
        annotated,
        audio_b64: null,
        audio_mime: null,
        translation: null,
      });
    },
    onAIAudio: ({ audio_b64, audio_mime }) => {
      if (audio_b64) {
        setOrb("speaking");
        player.play(audio_b64, audio_mime ?? "audio/mpeg");
      }
    },
    onAITranslation: (translation) => {
      setAiTurn((prev) => (prev ? { ...prev, translation } : prev));
    },
    onSuggestions: (s) => setSuggestions(s),
    onError: (msg) => {
      setErrorMsg(msg);
      setOrb("idle");
    },
  });

  const vad = useVADRecorder({
    paused: micPaused || !started,
    onSpeechStart: () => {
      player.stop();
      setErrorMsg(null);
      setOrb("listening");
    },
    onUtterance: async (blob) => {
      setOrb("processing");
      const buf = await blob.arrayBuffer();
      sendAudio(buf);
    },
    onError: (msg) => {
      setErrorMsg(msg);
      setOrb("idle");
    },
  });

  useEffect(() => {
    if (!l1 || !l2 || !sceneId) {
      router.replace("/");
    }
  }, [l1, l2, sceneId, router]);

  useEffect(() => {
    if (orb !== "processing") return;
    const id = window.setTimeout(() => {
      setErrorMsg(t("timeout_error"));
      setOrb("idle");
    }, 45_000);
    return () => window.clearTimeout(id);
  }, [orb, t]);

  // Gate the Start button on *all three*:
  //   - WS connected                  (can talk to backend)
  //   - STT weights warm              (first user utterance won't freeze)
  //   - opening turn received         (something to actually play on click)
  const ready = connected && sttReady && openingReady;

  const handleStart = async () => {
    setStarted(true);
    // Kick off mic permission + VAD now that the user interacted (also
    // satisfies browser autoplay policy for the pending opening audio).
    try {
      await vad.start();
    } catch {
      /* error surfaces through vad.onError → errorMsg */
    }
    const pending = pendingOpeningRef.current;
    if (pending && pending.audio_b64) {
      setOrb("speaking");
      player.play(pending.audio_b64, pending.audio_mime ?? "audio/mpeg");
      pendingOpeningRef.current = null;
    }
  };

  if (!l1 || !l2) return null;

  return (
    <div className="min-h-screen flex flex-col bg-bg text-fg relative">
      <TopNav back />

      {errorMsg && (
        <div className="max-w-readable mx-auto w-full px-5 pt-3">
          <div className="text-[13px] bg-danger/10 text-danger px-4 py-2 rounded-xl">
            {errorMsg}
          </div>
        </div>
      )}

      <main className="flex-1 flex flex-col items-center justify-center gap-10 px-5 py-10 overflow-auto">
        <VoiceOrb
          state={orb}
          intensity={vad.speaking ? Math.min(1, vad.level * 30) : 0}
        />

        <div className="w-full max-w-readable text-center min-h-[4rem] flex flex-col items-center justify-center gap-3">
          {streamingText ? (
            <div className="text-[19px] sm:text-[21px] leading-relaxed">
              <span className="text-cursor">{streamingText}</span>
            </div>
          ) : aiTurn?.annotated ? (
            <>
              <div className="text-[19px] sm:text-[21px] leading-loose">
                <AnnotatedText annotated={aiTurn.annotated} />
              </div>
              {showTranslation && aiTurn.translation && (
                <div className="text-[13px] text-muted leading-relaxed">
                  {aiTurn.translation}
                </div>
              )}
            </>
          ) : null}
        </div>

        {lastUserTranscript && (
          <div className="w-full max-w-readable text-[12px] text-muted text-center px-4">
            {t("you_said")} · <span className="text-fg">{lastUserTranscript}</span>
          </div>
        )}

        {suggestions.length > 0 && <ReplySuggestions suggestions={suggestions} />}

        <LevelMeter level={vad.level} threshold={0.008} />
      </main>

      <ControlBar
        connected={connected}
        paused={micPaused}
        speaking={vad.speaking}
        onTogglePaused={() => setMicPaused((p) => !p)}
        onInterrupt={() => {
          player.stop();
          setOrb("idle");
        }}
      />

      {!started && (
        <StartOverlay
          ready={ready}
          onStart={handleStart}
          startLabel={t("start_conversation")}
          loadingLabel={t("loading_prepare")}
        />
      )}
    </div>
  );
}

function StartOverlay({
  ready,
  onStart,
  startLabel,
  loadingLabel,
}: {
  ready: boolean;
  onStart: () => void;
  startLabel: string;
  loadingLabel: string;
}) {
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-bg/70 backdrop-blur-xl animate-[fadeIn_200ms_ease-out]">
      <div className="flex flex-col items-center gap-6 px-6">
        <img
          src="/icon.png"
          alt=""
          className="w-24 h-24 orb-idle"
          draggable={false}
        />
        <button
          onClick={onStart}
          disabled={!ready}
          aria-busy={!ready}
          className={
            "min-w-[180px] py-3.5 px-8 rounded-full text-[16px] font-semibold transition active:scale-[0.98] " +
            (ready
              ? "bg-accent text-accent-fg shadow-lg shadow-accent/30 hover:opacity-90"
              : "bg-transparent text-muted border border-border cursor-wait")
          }
        >
          {ready ? startLabel : (
            <span className="inline-flex items-center gap-2">
              <span className="w-3 h-3 rounded-full border-2 border-muted border-t-transparent animate-spin" />
              {loadingLabel}
            </span>
          )}
        </button>
      </div>
    </div>
  );
}
