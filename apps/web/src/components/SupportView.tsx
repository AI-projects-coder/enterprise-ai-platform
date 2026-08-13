"use client";

import { useState } from "react";
import Link from "next/link";
import { RaiseIssueModal } from "@/components/RaiseIssueModal";
import type { Priority, Ticket } from "@/lib/supportTypes";

const PRIORITY_COLOR: Record<Priority, string> = {
  low: "text-black/50 dark:text-white/50",
  medium: "text-blue-500",
  high: "text-orange-500",
  highest: "text-red-500",
};

export function SupportView({
  initialTickets,
  currentUserId,
}: {
  initialTickets: Ticket[];
  currentUserId: string;
}) {
  const [tab, setTab] = useState<"in_progress" | "completed">("in_progress");
  const [showModal, setShowModal] = useState(false);

  const filtered = initialTickets.filter((t) =>
    tab === "completed" ? t.status === "resolved" : t.status !== "resolved"
  );

  return (
    <div>
      <div className="mb-6 flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 border border-black/10 dark:border-white/10 rounded-lg p-1 w-fit">
          <button
            onClick={() => setTab("in_progress")}
            className={`px-3 py-1.5 text-sm rounded-md ${
              tab === "in_progress" ? "bg-foreground text-background" : ""
            }`}
          >
            In Progress
          </button>
          <button
            onClick={() => setTab("completed")}
            className={`px-3 py-1.5 text-sm rounded-md ${
              tab === "completed" ? "bg-foreground text-background" : ""
            }`}
          >
            Completed
          </button>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="bg-foreground text-background rounded px-3 py-2 text-sm font-medium"
        >
          Raise Issue
        </button>
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-black/50 dark:text-white/50">
          {tab === "completed" ? "No resolved issues yet." : "No open issues."}
        </p>
      ) : (
        // Every ticket here already belongs to the current user — list_tickets
        // only ever returns your own (see support/service.py), so unlike the
        // similar-ticket cards in the raise-issue modal, these are always
        // safe to link straight to the detail page.
        <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map((t) => (
            <li key={t.id}>
              <Link
                href={`/dashboard/support/${t.id}`}
                className="block border border-black/10 dark:border-white/10 rounded-lg p-4 hover:bg-black/5 dark:hover:bg-white/5"
              >
                <p className="text-sm line-clamp-2 mb-2">{t.description}</p>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs text-black/50 dark:text-white/50">
                    <span>
                      {new Date(t.created_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                    <span>· {t.status.replace("_", " ")}</span>
                  </div>
                  {t.priority && (
                    <span
                      className={`text-xs font-medium uppercase shrink-0 ${PRIORITY_COLOR[t.priority]}`}
                    >
                      {t.priority}
                    </span>
                  )}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {showModal && (
        <RaiseIssueModal currentUserId={currentUserId} onClose={() => setShowModal(false)} />
      )}
    </div>
  );
}
