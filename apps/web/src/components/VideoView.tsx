"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Video = {
  id: string;
  title: string;
  status: string;
  created_at: string;
};

export function VideoView({ initialVideos }: { initialVideos: Video[] }) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("title", title);
      formData.append("file", file);

      const res = await fetch("/api/videos", { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.json()).detail);

      setTitle("");
      setFile(null);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <form onSubmit={onSubmit} className="flex flex-col gap-3 mb-8 max-w-md">
        <input
          type="text"
          required
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        />
        <input
          type="file"
          accept="video/*"
          required
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="text-sm"
        />
        {error && <p className="text-sm text-red-500">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="bg-foreground text-background rounded px-3 py-2 text-sm font-medium disabled:opacity-50 w-fit"
        >
          {loading ? "Uploading..." : "Upload video"}
        </button>
      </form>

      {initialVideos.length === 0 ? (
        <p className="text-sm text-black/50 dark:text-white/50">No videos yet.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {initialVideos.map((v) => (
            <li
              key={v.id}
              className="border border-black/10 dark:border-white/10 rounded-lg p-3 flex justify-between items-center"
            >
              <span>{v.title}</span>
              <span className="text-sm text-black/50 dark:text-white/50">{v.status}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
