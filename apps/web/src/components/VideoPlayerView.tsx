"use client";

import { useEffect, useRef, useState } from "react";
import videojs from "video.js";
import "video.js/dist/video-js.css";
import type { VideoDetail } from "@/lib/videoTypes";

type VjsPlayer = ReturnType<typeof videojs>;

function formatTime(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

function postEvent(
  videoId: string,
  eventType: "play" | "pause" | "complete",
  watchDurationSeconds?: number,
  completionPct?: number
) {
  // Fire-and-forget — nothing in the UI depends on this succeeding, it's
  // purely for the future recommendation engine (see video/service.py).
  fetch(`/api/videos/${videoId}/events`, {
    method: "POST",
    body: JSON.stringify({
      event_type: eventType,
      watch_duration_seconds: watchDurationSeconds ?? null,
      completion_pct: completionPct ?? null,
    }),
  }).catch(() => {});
}

export function VideoPlayerView({ video }: { video: VideoDetail }) {
  const videoElRef = useRef<HTMLVideoElement | null>(null);
  const playerRef = useRef<VjsPlayer | null>(null);
  const transcriptRefs = useRef<(HTMLDivElement | null)[]>([]);
  const completedRef = useRef(false);
  const [currentSegmentIndex, setCurrentSegmentIndex] = useState(-1);

  const segments = video.transcript_segments ?? [];
  // Local dev has no GCS to sign a real URL against, so the backend hands
  // back a relative FastAPI path instead (see video/service.py::
  // get_playback_url) — that path needs to go through our own /api proxy
  // (api/videos/[id]/stream/route.ts), which attaches the auth header a
  // <video> tag can't set itself. A real signed GCS URL (deployed envs)
  // already starts with https:// and is used as-is, no proxying needed.
  const playbackSrc = video.playback_url.startsWith("http")
    ? video.playback_url
    : `/api${video.playback_url}`;

  useEffect(() => {
    if (!videoElRef.current) return;

    const player = videojs(videoElRef.current, {
      controls: true,
      fluid: true,
      // Quality selection is deliberately out of scope for v1 — that needs
      // a transcoding pipeline producing multiple renditions, a separate
      // infra investment. Speed and fullscreen are native video.js controls.
      playbackRates: [0.5, 0.75, 1, 1.25, 1.5, 2],
      sources: [{ src: playbackSrc, type: video.content_type }],
    });
    playerRef.current = player;

    function onPlay() {
      postEvent(video.id, "play");
    }
    function onPause() {
      postEvent(video.id, "pause", player.currentTime() ?? undefined);
    }
    function onTimeUpdate() {
      const t = player.currentTime() ?? 0;
      const idx = segments.findIndex((s) => t >= s.start_seconds && t < s.end_seconds);
      setCurrentSegmentIndex(idx);

      const duration = player.duration() ?? 0;
      if (!completedRef.current && duration > 0 && t / duration > 0.9) {
        completedRef.current = true;
        postEvent(video.id, "complete", t, 100);
      }
    }

    player.on("play", onPlay);
    player.on("pause", onPause);
    player.on("timeupdate", onTimeUpdate);

    return () => {
      player.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [video.id]);

  useEffect(() => {
    if (currentSegmentIndex >= 0) {
      transcriptRefs.current[currentSegmentIndex]?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    }
  }, [currentSegmentIndex]);

  function seekTo(seconds: number) {
    playerRef.current?.currentTime(seconds);
    playerRef.current?.play();
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2">
        <div data-vjs-player>
          <video ref={videoElRef} className="video-js vjs-big-play-centered" playsInline />
        </div>
      </div>

      <div className="border border-black/10 dark:border-white/10 rounded-lg p-3 max-h-[480px] overflow-y-auto">
        <p className="text-sm font-medium mb-2">Transcript</p>
        {segments.length === 0 ? (
          <p className="text-sm text-black/50 dark:text-white/50">No transcript available.</p>
        ) : (
          segments.map((seg, i) => (
            <div
              key={i}
              ref={(el) => {
                transcriptRefs.current[i] = el;
              }}
              onClick={() => seekTo(seg.start_seconds)}
              className={`text-sm px-2 py-1.5 rounded cursor-pointer ${
                i === currentSegmentIndex
                  ? "bg-foreground text-background"
                  : "hover:bg-black/5 dark:hover:bg-white/5"
              }`}
            >
              <span
                className={`text-xs font-mono mr-2 ${
                  i === currentSegmentIndex
                    ? "text-background/70"
                    : "text-black/40 dark:text-white/40"
                }`}
              >
                {formatTime(seg.start_seconds)}
              </span>
              {seg.text}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
