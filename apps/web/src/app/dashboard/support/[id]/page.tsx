import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/api";
import type { TicketDetail } from "@/lib/supportTypes";

const STATUS_LABEL: Record<TicketDetail["status"], string> = {
  open: "In Progress",
  in_progress: "In Progress",
  resolved: "Closed",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function resolveSrc(viewUrl: string) {
  return viewUrl.startsWith("http") ? viewUrl : `/api${viewUrl}`;
}

export default async function TicketDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const [ticket, currentUser]: [TicketDetail, { email: string }] = await Promise.all([
    apiFetch(`/tickets/${id}`, { headers: { Authorization: `Bearer ${token}` } }),
    apiFetch("/auth/me", { headers: { Authorization: `Bearer ${token}` } }),
  ]);

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/dashboard/support"
          aria-label="Back to Support"
          className="text-lg leading-none px-2.5 py-1.5 rounded border border-black/10 dark:border-white/10 hover:bg-black/5 dark:hover:bg-white/5"
        >
          ←
        </Link>
        <h1 className="text-2xl font-semibold">Ticket details</h1>
      </div>

      <div className="border border-black/10 dark:border-white/10 rounded-lg p-5 max-w-2xl">
        <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5 text-sm">
          <div>
            <dt className="text-xs text-black/50 dark:text-white/50 mb-0.5">Ticket ID</dt>
            <dd className="font-mono text-xs">{ticket.id}</dd>
          </div>
          <div>
            <dt className="text-xs text-black/50 dark:text-white/50 mb-0.5">Raised by</dt>
            <dd>{currentUser.email}</dd>
          </div>
          <div>
            <dt className="text-xs text-black/50 dark:text-white/50 mb-0.5">Raised</dt>
            <dd>{formatDate(ticket.created_at)}</dd>
          </div>
          <div>
            <dt className="text-xs text-black/50 dark:text-white/50 mb-0.5">Resolved</dt>
            <dd>{ticket.resolved_at ? formatDate(ticket.resolved_at) : "—"}</dd>
          </div>
        </dl>

        <div className="flex items-center gap-2 mb-5">
          <span
            className={`text-xs font-medium px-2 py-1 rounded ${
              ticket.status === "resolved"
                ? "bg-green-500/10 text-green-600 dark:text-green-400"
                : "bg-blue-500/10 text-blue-600 dark:text-blue-400"
            }`}
          >
            {STATUS_LABEL[ticket.status]}
          </span>
          {ticket.priority && (
            <span className="text-xs font-medium uppercase text-black/50 dark:text-white/50">
              {ticket.priority} priority
            </span>
          )}
          {ticket.jira_issue_key && (
            <span className="text-xs font-mono text-black/50 dark:text-white/50">
              {ticket.jira_issue_key}
            </span>
          )}
        </div>

        <div className="mb-6">
          <h2 className="text-xs text-black/50 dark:text-white/50 mb-1.5">Description</h2>
          <p className="text-sm whitespace-pre-wrap">{ticket.description}</p>
        </div>

        <div>
          <h2 className="text-xs text-black/50 dark:text-white/50 mb-2">
            Attachments {ticket.attachments.length > 0 ? `(${ticket.attachments.length})` : ""}
          </h2>
          {ticket.attachments.length === 0 ? (
            <p className="text-sm text-black/50 dark:text-white/50">No attachments.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {ticket.attachments.map((a) =>
                a.content_type.startsWith("video/") ? (
                  <video key={a.id} src={resolveSrc(a.view_url)} controls className="w-full rounded border border-black/10 dark:border-white/10" />
                ) : (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={a.id}
                    src={resolveSrc(a.view_url)}
                    alt="Ticket attachment"
                    className="w-full rounded border border-black/10 dark:border-white/10"
                  />
                )
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
