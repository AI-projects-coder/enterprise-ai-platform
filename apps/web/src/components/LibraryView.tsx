"use client";

import { useState } from "react";
import Link from "next/link";
import { UploadVideoModal } from "@/components/UploadVideoModal";
import type { VideoSummary } from "@/lib/videoTypes";

const STATUS_LABEL: Record<VideoSummary["status"], string> = {
  processing: "Processing…",
  ready: "Ready",
  failed: "Failed",
};

// No currentUserId prop needed — the backend only ever returns published
// videos (any user) plus the current user's own drafts (see
// video/service.py::list_videos), so any non-published card here is
// guaranteed to belong to the current user already — same trick
// JobDrivesView uses.
export function LibraryView({ initialVideos }: { initialVideos: VideoSummary[] }) {
  const [showUpload, setShowUpload] = useState(false);

  return (
    <div>
      <div className="mb-6">
        <button
          onClick={() => setShowUpload(true)}
          className="bg-foreground text-background rounded px-3 py-2 text-sm font-medium"
        >
          Upload Video
        </button>
      </div>

      {initialVideos.length === 0 ? (
        <p className="text-sm text-black/50 dark:text-white/50">No videos yet.</p>
      ) : (
        <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {initialVideos.map((v) => (
            <VideoCard key={v.id} video={v} />
          ))}
        </ul>
      )}

      {showUpload && <UploadVideoModal onClose={() => setShowUpload(false)} />}
    </div>
  );
}

function VideoCard({ video }: { video: VideoSummary }) {
  const ready = video.status === "ready";
  const [publishing, setPublishing] = useState(false);
  const [published, setPublished] = useState(video.visibility === "published");

  async function onPublish() {
    setPublishing(true);
    try {
      const res = await fetch(`/api/videos/${video.id}/publish`, { method: "PATCH" });
      if (res.ok) setPublished(true);
    } finally {
      setPublishing(false);
    }
  }

  return (
    <li className="border border-black/10 dark:border-white/10 rounded-lg overflow-hidden">
      <div className="aspect-video bg-black/10 dark:bg-white/10 flex items-center justify-center text-4xl">
        🎬
      </div>
      <div className="p-3">
        <p className="font-medium truncate" title={video.title}>
          {video.title}
        </p>
        <p className="text-xs text-black/50 dark:text-white/50 mb-2">
          {new Date(video.created_at).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}{" "}
          · {STATUS_LABEL[video.status]}
        </p>

        <div className="flex flex-wrap gap-1.5 text-xs mb-2">
          <CardBadge href={`/dashboard/library/video/${video.id}`} enabled={ready} label="▶ Play Video" />
          <CardBadge
            href={`/dashboard/library/practice/${video.id}`}
            enabled={ready}
            label="📝 Q&A Assessment"
          />
          <CardBadge
            href={`/dashboard/library/summary/${video.id}`}
            enabled={ready}
            label="📄 Summary Notes"
          />
        </div>

        {published ? (
          <span className="text-xs text-black/50 dark:text-white/50">Published</span>
        ) : (
          <button
            onClick={onPublish}
            disabled={publishing}
            className="text-xs bg-foreground text-background rounded px-2 py-1 disabled:opacity-50"
          >
            {publishing ? "..." : "Publish"}
          </button>
        )}
      </div>
    </li>
  );
}

function CardBadge({ href, enabled, label }: { href: string; enabled: boolean; label: string }) {
  if (!enabled) {
    return (
      <span className="px-2 py-1 rounded border border-black/10 dark:border-white/10 opacity-40">
        {label}
      </span>
    );
  }
  return (
    <Link
      href={href}
      className="px-2 py-1 rounded border border-black/10 dark:border-white/10 hover:bg-black/5 dark:hover:bg-white/5"
    >
      {label}
    </Link>
  );
}
