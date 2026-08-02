"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Document = { id: string; title: string; created_at: string };

export function KnowledgeView({ initialDocuments }: { initialDocuments: Document[] }) {
  const router = useRouter();
  const [documents, setDocuments] = useState(initialDocuments);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !content.trim() || loading) return;

    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/documents", {
        method: "POST",
        body: JSON.stringify({ title, content }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Something went wrong");

      setDocuments((prev) => [data, ...prev]);
      setTitle("");
      setContent("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function onDelete(id: string) {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    await fetch(`/api/documents/${id}`, { method: "DELETE" });
    router.refresh();
  }

  return (
    <div className="max-w-2xl flex flex-col gap-8">
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <h2 className="text-lg font-medium">Add a document</h2>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Title"
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        />
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Paste text content..."
          rows={8}
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        />
        {error && <p className="text-sm text-red-500">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="self-start bg-foreground text-background rounded px-4 py-2 font-medium disabled:opacity-50"
        >
          {loading ? "Ingesting..." : "Add document"}
        </button>
      </form>

      <div>
        <h2 className="text-lg font-medium mb-3">Your documents</h2>
        {documents.length === 0 && (
          <p className="text-sm text-black/50 dark:text-white/50">No documents yet.</p>
        )}
        <ul className="flex flex-col gap-2">
          {documents.map((d) => (
            <li
              key={d.id}
              className="flex items-center justify-between border border-black/10 dark:border-white/10 rounded px-3 py-2"
            >
              <span className="text-sm truncate">{d.title}</span>
              <button
                onClick={() => onDelete(d.id)}
                className="text-sm text-red-500 hover:underline shrink-0 ml-4"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
