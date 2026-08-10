"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Mode = "file" | "link";

async function uploadViaFile(title: string, description: string, file: File) {
  const urlRes = await fetch("/api/videos/upload-url", {
    method: "POST",
    body: JSON.stringify({ title, description, content_type: file.type || "video/mp4" }),
  });
  if (!urlRes.ok) throw new Error((await urlRes.json()).detail);
  const { video_id, upload_url } = await urlRes.json();

  if (upload_url) {
    // Deployed envs: PUT straight to GCS via the presigned URL — this
    // request never touches our own servers at all.
    const putRes = await fetch(upload_url, {
      method: "PUT",
      body: file,
      headers: { "Content-Type": file.type || "video/mp4" },
    });
    if (!putRes.ok) throw new Error("Upload to storage failed");

    const confirmRes = await fetch(`/api/videos/${video_id}/confirm-upload`, { method: "POST" });
    if (!confirmRes.ok) throw new Error((await confirmRes.json()).detail);
  } else {
    // Local dev fallback — no GCS configured, so the file goes through our
    // own API instead (see video/service.py::create_local_upload).
    const formData = new FormData();
    formData.append("title", title);
    formData.append("description", description);
    formData.append("file", file);
    const localRes = await fetch("/api/videos/local-upload", { method: "POST", body: formData });
    if (!localRes.ok) throw new Error((await localRes.json()).detail);
  }
}

async function uploadViaLink(title: string, description: string, sourceUrl: string) {
  const res = await fetch("/api/videos/from-link", {
    method: "POST",
    body: JSON.stringify({ title, description, source_url: sourceUrl }),
  });
  if (!res.ok) throw new Error((await res.json()).detail);
}

export function UploadVideoModal({ onClose }: { onClose: () => void }) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [mode, setMode] = useState<Mode>("file");
  const [file, setFile] = useState<File | null>(null);
  const [link, setLink] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "file") {
        if (!file) throw new Error("Choose a video file");
        await uploadViaFile(title, description, file);
      } else {
        if (!link.trim()) throw new Error("Enter a video link");
        await uploadViaLink(title, description, link.trim());
      }
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function onDone() {
    router.refresh();
    onClose();
  }

  if (success) {
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onDone}>
        <div
          className="bg-background border border-black/10 dark:border-white/10 rounded-lg p-6 max-w-sm w-full text-center"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="font-medium mb-1">Video uploaded successfully</p>
          <p className="text-sm text-black/50 dark:text-white/50 mb-4">
            Check the library list to see its processing status.
          </p>
          <button
            onClick={onDone}
            className="bg-foreground text-background rounded px-4 py-2 text-sm font-medium"
          >
            OK
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <form
        onSubmit={onSubmit}
        onClick={(e) => e.stopPropagation()}
        className="bg-background border border-black/10 dark:border-white/10 rounded-lg p-6 max-w-md w-full flex flex-col gap-3"
      >
        <h2 className="text-lg font-semibold">Upload Video</h2>

        <input
          type="text"
          required
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        />
        <textarea
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        />

        <div className="flex gap-4 text-sm">
          <label className="flex items-center gap-1.5">
            <input type="radio" checked={mode === "file"} onChange={() => setMode("file")} />
            Upload from device
          </label>
          <label className="flex items-center gap-1.5">
            <input type="radio" checked={mode === "link"} onChange={() => setMode("link")} />
            Paste a link
          </label>
        </div>

        {mode === "file" ? (
          <input
            type="file"
            accept="video/*"
            required
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm"
          />
        ) : (
          <input
            type="url"
            required
            placeholder="https://example.com/video.mp4"
            value={link}
            onChange={(e) => setLink(e.target.value)}
            className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
          />
        )}

        {error && <p className="text-sm text-red-500">{error}</p>}

        <div className="flex justify-end gap-2 mt-2">
          <button type="button" onClick={onClose} className="px-3 py-2 text-sm">
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="bg-foreground text-background rounded px-3 py-2 text-sm font-medium disabled:opacity-50"
          >
            {loading ? "Uploading..." : "Upload"}
          </button>
        </div>
      </form>
    </div>
  );
}
