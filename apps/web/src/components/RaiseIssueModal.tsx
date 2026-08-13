"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { Ticket } from "@/lib/supportTypes";

type Step = "form" | "checking" | "similar" | "submitting" | "success";

async function uploadOneAttachment(ticketId: string, file: File) {
  const urlRes = await fetch(`/api/tickets/${ticketId}/attachments/upload-url`, {
    method: "POST",
    body: JSON.stringify({ content_type: file.type || "application/octet-stream" }),
  });
  if (!urlRes.ok) throw new Error((await urlRes.json()).detail);
  const { attachment_id, upload_url } = await urlRes.json();

  if (upload_url) {
    // Deployed envs: PUT straight to GCS via the presigned URL, same as
    // video/job_drives uploads — bytes never touch our own servers.
    const putRes = await fetch(upload_url, {
      method: "PUT",
      body: file,
      headers: { "Content-Type": file.type || "application/octet-stream" },
    });
    if (!putRes.ok) throw new Error("Upload to storage failed");

    const confirmRes = await fetch(
      `/api/tickets/${ticketId}/attachments/${attachment_id}/confirm-upload`,
      { method: "POST" }
    );
    if (!confirmRes.ok) throw new Error((await confirmRes.json()).detail);
  } else {
    // Local dev fallback — no GCS configured, upload through our own API.
    const formData = new FormData();
    formData.append("file", file);
    const localRes = await fetch(`/api/tickets/${ticketId}/attachments/local-upload`, {
      method: "POST",
      body: formData,
    });
    if (!localRes.ok) throw new Error((await localRes.json()).detail);
  }
}

export function RaiseIssueModal({
  currentUserId,
  onClose,
}: {
  currentUserId: string;
  onClose: () => void;
}) {
  const router = useRouter();
  const [description, setDescription] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [step, setStep] = useState<Step>("form");
  const [similarTickets, setSimilarTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [createdTicketId, setCreatedTicketId] = useState<string | null>(null);

  async function onCheckSimilar(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setStep("checking");
    try {
      const res = await fetch("/api/tickets/similar", {
        method: "POST",
        body: JSON.stringify({ description }),
      });
      if (!res.ok) throw new Error((await res.json()).detail);
      const matches: Ticket[] = await res.json();

      if (matches.length > 0) {
        setSimilarTickets(matches);
        setStep("similar");
      } else {
        await raiseTicket();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setStep("form");
    }
  }

  async function raiseTicket() {
    setStep("submitting");
    setError(null);
    try {
      const createRes = await fetch("/api/tickets", {
        method: "POST",
        body: JSON.stringify({ description }),
      });
      if (!createRes.ok) throw new Error((await createRes.json()).detail);
      const ticket: Ticket = await createRes.json();

      for (const file of files) {
        await uploadOneAttachment(ticket.id, file);
      }

      const submitRes = await fetch(`/api/tickets/${ticket.id}/submit`, { method: "POST" });
      if (!submitRes.ok) throw new Error((await submitRes.json()).detail);

      setCreatedTicketId(ticket.id);
      setStep("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setStep("form");
    }
  }

  function onDone() {
    router.refresh();
    onClose();
  }

  if (step === "success") {
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onDone}>
        <div
          className="bg-background border border-black/10 dark:border-white/10 rounded-lg p-6 max-w-sm w-full text-center"
          onClick={(e) => e.stopPropagation()}
        >
          <p className="font-medium mb-1">Thank you for raising this</p>
          <p className="text-sm text-black/50 dark:text-white/50 mb-1">
            Ticket ID: <span className="font-mono">{createdTicketId}</span>
          </p>
          <p className="text-sm text-black/50 dark:text-white/50 mb-4">
            You&apos;ll get an email once it&apos;s resolved.
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

  if (step === "similar") {
    return (
      <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
        <div
          className="bg-background border border-black/10 dark:border-white/10 rounded-lg p-6 max-w-lg w-full"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 className="text-lg font-semibold mb-1">Is this your issue?</h2>
          <p className="text-sm text-black/50 dark:text-white/50 mb-4">
            We found similar issues already raised — take a look before raising a new one.
          </p>
          <ul className="flex flex-col gap-2 mb-4 max-h-64 overflow-y-auto">
            {similarTickets.map((t) => {
              const isMine = t.user_id === currentUserId;
              const cardContent = (
                <>
                  <p className="mb-1 line-clamp-2">{t.description}</p>
                  <p className="text-xs text-black/50 dark:text-white/50">
                    Status: {t.status.replace("_", " ")}
                    {t.priority ? ` · Priority: ${t.priority}` : ""}
                    {isMine ? "" : " · from another user"}
                  </p>
                </>
              );
              // Only your own tickets are safe to link to the detail page —
              // get_ticket() 404s on anyone else's, and the similarity
              // search deliberately spans all users (see support/service.py
              // ::find_similar_tickets), so a non-owned match still shows
              // useful context here without navigating anywhere.
              return (
                <li key={t.id}>
                  {isMine ? (
                    <Link
                      href={`/dashboard/support/${t.id}`}
                      className="block border border-black/10 dark:border-white/10 rounded p-3 text-sm hover:bg-black/5 dark:hover:bg-white/5"
                    >
                      {cardContent}
                    </Link>
                  ) : (
                    <div className="border border-black/10 dark:border-white/10 rounded p-3 text-sm opacity-80">
                      {cardContent}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
          {error && <p className="text-sm text-red-500 mb-3">{error}</p>}
          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="px-3 py-2 text-sm">
              Never mind
            </button>
            <button
              onClick={raiseTicket}
              className="bg-foreground text-background rounded px-3 py-2 text-sm font-medium"
            >
              Not my issue — raise a new one
            </button>
          </div>
        </div>
      </div>
    );
  }

  const busy = step === "checking" || step === "submitting";

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={onClose}>
      <form
        onSubmit={onCheckSimilar}
        onClick={(e) => e.stopPropagation()}
        className="bg-background border border-black/10 dark:border-white/10 rounded-lg p-6 max-w-md w-full flex flex-col gap-3"
      >
        <h2 className="text-lg font-semibold">Raise an issue</h2>

        <textarea
          required
          placeholder="Describe the problem — what happened, what page, what you expected instead"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={5}
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        />

        <div>
          <label className="text-sm block mb-1">Screenshots or a video (optional)</label>
          <input
            type="file"
            multiple
            accept="image/*,video/*"
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
            className="text-sm"
          />
        </div>

        {error && <p className="text-sm text-red-500">{error}</p>}

        <div className="flex justify-end gap-2 mt-2">
          <button type="button" onClick={onClose} className="px-3 py-2 text-sm">
            Cancel
          </button>
          <button
            type="submit"
            disabled={busy}
            className="bg-foreground text-background rounded px-3 py-2 text-sm font-medium disabled:opacity-50"
          >
            {step === "checking" ? "Checking..." : step === "submitting" ? "Raising..." : "Raise Issue"}
          </button>
        </div>
      </form>
    </div>
  );
}
