"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { MarkdownContent } from "@/components/MarkdownContent";

const ROLES = [
  "Sales Representative",
  "Account Executive",
  "Business Development Manager",
  "Marketing Specialist",
  "frontend",
  "backend",
  "bpo",
  "call center",
  "Software Developer",
  "Systems Analyst",
  "Operations Analyst",
];

const CITIES = ["Hyderabad", "Bangalore", "Chennai"];

const EXPERIENCE_BANDS = [
  "0-1",
  "1-2",
  "2-3",
  "3-4",
  "4-5",
  "5-6",
  "6-7",
  "7-8",
  "8-9",
  "9-10",
  "10+",
];

type JobDrive = {
  id: string;
  user_id: string;
  role: string;
  city: string;
  experience_band: string;
  generated_content: string;
  status: "draft" | "published";
  published_at: string | null;
  created_at: string;
};

// No currentUserId prop needed — the backend only ever returns published
// drives (any user) plus the current user's own drafts (see
// job_drives/service.py::list_job_drives), so any non-published item in
// this list is guaranteed to belong to the current user already.
export function JobDrivesView({ initialDrives }: { initialDrives: JobDrive[] }) {
  const router = useRouter();
  const [role, setRole] = useState("");
  const [city, setCity] = useState("");
  const [experienceBand, setExperienceBand] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [openId, setOpenId] = useState<string | null>(null);
  const [publishingId, setPublishingId] = useState<string | null>(null);

  async function onGenerate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/job-drives", {
        method: "POST",
        body: JSON.stringify({ role, city, experience_band: experienceBand }),
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      const created: JobDrive = await res.json();

      setRole("");
      setCity("");
      setExperienceBand("");
      setOpenId(created.id);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function onPublish(id: string) {
    setPublishingId(id);
    try {
      const res = await fetch(`/api/job-drives/${id}/publish`, { method: "PATCH" });
      if (!res.ok) throw new Error((await res.json()).detail);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setPublishingId(null);
    }
  }

  return (
    <div>
      <form onSubmit={onGenerate} className="flex flex-col gap-3 mb-8 max-w-md">
        <select
          required
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        >
          <option value="" disabled>
            Role
          </option>
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>

        <select
          required
          value={city}
          onChange={(e) => setCity(e.target.value)}
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        >
          <option value="" disabled>
            City
          </option>
          {CITIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        <select
          required
          value={experienceBand}
          onChange={(e) => setExperienceBand(e.target.value)}
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        >
          <option value="" disabled>
            Years of Experience
          </option>
          {EXPERIENCE_BANDS.map((band) => (
            <option key={band} value={band}>
              {band}
            </option>
          ))}
        </select>

        {error && <p className="text-sm text-red-500">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="bg-foreground text-background rounded px-3 py-2 text-sm font-medium disabled:opacity-50 w-fit"
        >
          {loading ? "Generating..." : "Generate"}
        </button>
      </form>

      {initialDrives.length === 0 ? (
        <p className="text-sm text-black/50 dark:text-white/50">No drives yet.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {initialDrives.map((d) => (
            <li key={d.id} className="border border-black/10 dark:border-white/10 rounded-lg">
              <details open={openId === d.id}>
                <summary className="flex justify-between items-center px-3 py-2 cursor-pointer list-none">
                  <span>
                    <span className="text-black/50 dark:text-white/50">
                      {new Date(d.created_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}{" "}
                      ·{" "}
                    </span>
                    <span className="font-medium">{d.role}</span>
                    <span className="text-black/50 dark:text-white/50">
                      {" "}
                      · {d.city} · {d.experience_band} yrs
                    </span>
                  </span>
                  {d.status === "published" ? (
                    <span className="text-sm text-black/50 dark:text-white/50">Published</span>
                  ) : (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        onPublish(d.id);
                      }}
                      disabled={publishingId === d.id}
                      className="bg-foreground text-background rounded px-2 py-1 text-xs font-medium disabled:opacity-50"
                    >
                      {publishingId === d.id ? "..." : "Publish"}
                    </button>
                  )}
                </summary>
                <div className="px-3 pb-3 border-t border-black/10 dark:border-white/10 pt-3">
                  <MarkdownContent content={d.generated_content} />
                </div>
              </details>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
