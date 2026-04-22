"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type Options = {
  onSpeechStart?: () => void;
  onUtterance?: (blob: Blob) => void;
  onError?: (message: string) => void;
  /** RMS threshold in [0, 1]. Typical speech hovers 0.02–0.08. */
  speechThreshold?: number;
  /** Silence duration (ms) before closing an utterance. */
  silenceMs?: number;
  /** Minimum sustained loudness before declaring speech start. */
  sustainedSpeechMs?: number;
  /** Ignore "utterances" shorter than this (kills mouse clicks, taps). */
  minUtteranceMs?: number;
  /** Max seconds the MediaRecorder will keep buffering when no speech has been
   *  detected in the current segment. Caps blob size while keeping pre-roll. */
  idleRotateSeconds?: number;
  /** If true, keep mic + analyser alive but don't trigger utterances. */
  paused?: boolean;
};

type Handle = {
  start: () => Promise<void>;
  stop: () => void;
  active: boolean;
  speaking: boolean;
  level: number;
};

/**
 * Always-on microphone + always-on MediaRecorder, with VAD-driven segmenting.
 *
 * Why a continuous MediaRecorder? If we only start recording AFTER VAD
 * declares speech, the first ~150ms of the user's utterance (the "loud
 * enough for long enough" sustainedSpeechMs window) is NEVER captured. By
 * keeping MediaRecorder running and rotating it when speech ends, each
 * emitted blob naturally includes pre-roll before the detected speech-start.
 */
export function useVADRecorder(options: Options): Handle {
  const optsRef = useRef(options);
  optsRef.current = options;

  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const mimeTypeRef = useRef<string>("audio/webm");
  const chunksRef = useRef<Blob[]>([]);
  const segmentStartedAtRef = useRef<number>(0);   // when current MR started
  const segmentSpokeRef = useRef(false);           // did we detect speech in it?
  const speechStartTsRef = useRef<number>(0);
  const loudStartTsRef = useRef<number | null>(null);
  const silenceStartTsRef = useRef<number | null>(null);
  const loopIdRef = useRef<number | null>(null);
  const stoppedRef = useRef(false);

  const [active, setActive] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [level, setLevel] = useState(0);

  const _pickMimeType = (): string => {
    const candidates = [
      "audio/webm",
      "audio/webm;codecs=opus",
      "audio/mp4",
      "audio/ogg",
    ];
    for (const t of candidates) {
      if (
        typeof MediaRecorder !== "undefined" &&
        MediaRecorder.isTypeSupported?.(t)
      ) {
        return t;
      }
    }
    return "";
  };

  const _startSegment = useCallback(() => {
    if (stoppedRef.current) return;
    const stream = streamRef.current;
    if (!stream) return;

    const mimeType = mimeTypeRef.current;
    const mr = mimeType
      ? new MediaRecorder(stream, { mimeType })
      : new MediaRecorder(stream);
    chunksRef.current = [];
    segmentSpokeRef.current = false;
    segmentStartedAtRef.current = performance.now();

    mr.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    mr.onstop = () => {
      const blob = new Blob(chunksRef.current, {
        type: mimeType || "audio/webm",
      });
      chunksRef.current = [];

      const spoke = segmentSpokeRef.current;
      const dur = performance.now() - speechStartTsRef.current;
      const minDur = optsRef.current.minUtteranceMs ?? 250;

      if (spoke && blob.size > 0 && dur >= minDur) {
        console.debug("[VAD] emit utterance", { size: blob.size, dur });
        optsRef.current.onUtterance?.(blob);
      } else if (spoke) {
        console.debug("[VAD] segment dropped (too short)", { size: blob.size, dur });
      }
      // Always start the next segment so the mic is never "off" during chat.
      _startSegment();
    };

    try {
      mr.start();
    } catch (e) {
      optsRef.current.onError?.(`recorder start failed: ${(e as Error).message}`);
      return;
    }
    recorderRef.current = mr;
  }, []);

  const stop = useCallback(() => {
    stoppedRef.current = true;
    if (loopIdRef.current != null) {
      cancelAnimationFrame(loopIdRef.current);
      loopIdRef.current = null;
    }
    if (recorderRef.current?.state === "recording") {
      try {
        recorderRef.current.stop();
      } catch {
        /* swallow */
      }
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioCtxRef.current?.close().catch(() => {});
    streamRef.current = null;
    audioCtxRef.current = null;
    analyserRef.current = null;
    recorderRef.current = null;
    chunksRef.current = [];
    setActive(false);
    setSpeaking(false);
    setLevel(0);
  }, []);

  const start = useCallback(async () => {
    if (active) return;
    stoppedRef.current = false;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext })
          .webkitAudioContext;
      const ctx = new AudioCtx();
      audioCtxRef.current = ctx;
      if (ctx.state === "suspended") {
        await ctx.resume().catch(() => {});
      }

      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      analyser.smoothingTimeConstant = 0.2;
      source.connect(analyser);
      analyserRef.current = analyser;

      mimeTypeRef.current = _pickMimeType();
      setActive(true);

      // Start the first MediaRecorder segment IMMEDIATELY — this is what
      // guarantees we capture audio from before VAD recognises speech.
      _startSegment();

      console.info(
        "[VAD] mic started; threshold=%s silenceMs=%s mimeType=%s",
        optsRef.current.speechThreshold ?? 0.008,
        optsRef.current.silenceMs ?? 800,
        mimeTypeRef.current
      );

      const buf = new Float32Array(analyser.fftSize);
      const loop = () => {
        if (stoppedRef.current || !analyserRef.current) return;
        analyserRef.current.getFloatTimeDomainData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
        const rms = Math.sqrt(sum / buf.length);
        setLevel(rms);

        const threshold = optsRef.current.speechThreshold ?? 0.008;
        const silenceMs = optsRef.current.silenceMs ?? 800;
        const sustainedMs = optsRef.current.sustainedSpeechMs ?? 150;
        const idleRotateS = optsRef.current.idleRotateSeconds ?? 5;
        const paused = optsRef.current.paused ?? false;

        if (!paused) {
          const now = performance.now();
          const isLoud = rms > threshold;
          const spokeInSegment = segmentSpokeRef.current;

          if (isLoud) {
            silenceStartTsRef.current = null;
            if (!spokeInSegment) {
              // First detection in this segment — still require sustained
              // loudness to avoid marking a cough as real speech.
              if (loudStartTsRef.current == null) {
                loudStartTsRef.current = now;
              } else if (now - loudStartTsRef.current >= sustainedMs) {
                // NOTE: recorder is already running; we only flip the flag.
                // The existing MR's buffer already contains the first ~Nms
                // of audio leading up to this moment.
                segmentSpokeRef.current = true;
                speechStartTsRef.current = now - sustainedMs;
                setSpeaking(true);
                console.debug("[VAD] speech start (preroll captured)");
                optsRef.current.onSpeechStart?.();
                loudStartTsRef.current = null;
              }
            }
          } else {
            loudStartTsRef.current = null;
            if (spokeInSegment) {
              if (silenceStartTsRef.current == null) {
                silenceStartTsRef.current = now;
              } else if (now - silenceStartTsRef.current >= silenceMs) {
                // Speech ended: stop the current MR. onstop will emit + rotate.
                if (recorderRef.current?.state === "recording") {
                  try {
                    recorderRef.current.stop();
                  } catch {
                    /* swallow */
                  }
                }
                silenceStartTsRef.current = null;
                setSpeaking(false);
              }
            }
          }

          // Memory cap: if no speech detected in the last idleRotateS,
          // silently rotate so the blob doesn't grow unbounded.
          const segAge = (now - segmentStartedAtRef.current) / 1000;
          if (!spokeInSegment && segAge > idleRotateS) {
            if (recorderRef.current?.state === "recording") {
              try {
                recorderRef.current.stop();
              } catch {
                /* swallow */
              }
            }
          }
        }

        loopIdRef.current = requestAnimationFrame(loop);
      };
      loopIdRef.current = requestAnimationFrame(loop);
    } catch (err) {
      const msg =
        err instanceof Error
          ? `${err.name}: ${err.message}`
          : "Unknown microphone error";
      optsRef.current.onError?.(msg);
      stop();
    }
  }, [active, _startSegment, stop]);

  useEffect(() => () => stop(), [stop]);

  return { start, stop, active, speaking, level };
}
