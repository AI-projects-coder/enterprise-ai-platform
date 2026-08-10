"use client";

import { MarkdownContent } from "@/components/MarkdownContent";
import type { VideoDetail } from "@/lib/videoTypes";

export function SummaryView({ video }: { video: VideoDetail }) {
  function onDownload() {
    const text = [
      `# ${video.title}`,
      "",
      video.summary_notes ?? "",
      "",
      "## Key Points",
      ...(video.key_points ?? []).map((point) => `- ${point}`),
    ].join("\n");

    const blob = new Blob([text], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${video.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}-summary.md`;
    a.click();
    URL.revokeObjectURL(url);

    fetch(`/api/videos/${video.id}/events`, {
      method: "POST",
      body: JSON.stringify({ event_type: "summary_click" }),
    }).catch(() => {});
  }

  return (
    <div className="max-w-2xl">
      <div className="flex justify-end mb-4">
        <button
          onClick={onDownload}
          className="text-sm bg-foreground text-background rounded px-3 py-2 font-medium"
        >
          Download
        </button>
      </div>

      <MarkdownContent content={video.summary_notes ?? "No summary available."} />

      {video.key_points && video.key_points.length > 0 && (
        <div className="mt-6">
          <h2 className="text-lg font-semibold mb-2">Key Points</h2>
          <ul className="list-disc list-inside flex flex-col gap-1 text-sm">
            {video.key_points.map((point, i) => (
              <li key={i}>{point}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
