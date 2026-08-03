import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { apiFetch, ApiError } from "@/lib/api";

type ErrorEntry = { timestamp: string; severity: string; service: string; message: string };
type RecentErrors = { minutes?: number; error_count?: number; errors?: ErrorEntry[]; error?: string };
type AlertPolicy = { name: string; enabled: boolean };
type AlertPolicies = { policies?: AlertPolicy[]; error?: string };
type Deployment = { service: string; revision: string; created_at: string; healthy: boolean };
type RecentDeployments = { deployments?: Deployment[]; error?: string };

type IncidentStatus = {
  recent_errors: RecentErrors;
  alert_policies: AlertPolicies;
  recent_deployments: RecentDeployments;
};

export default async function IncidentsPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  let status: IncidentStatus | null = null;
  let forbidden = false;

  try {
    status = await apiFetch("/incidents/status", {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 403) {
      forbidden = true;
    } else {
      throw err;
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Incident Response</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          Live status from this platform&apos;s own deployed environment — real Cloud Logging,
          Monitoring, and Cloud Run data. Owner-only. Ask chat questions like &quot;is anything
          wrong right now?&quot; to have the agent investigate using the same data.
        </p>
      </div>

      {forbidden && (
        <p className="text-sm text-black/50 dark:text-white/50">
          Only the org owner can view incident status.
        </p>
      )}

      {status && (
        <div className="flex flex-col gap-6">
          <section>
            <h2 className="font-medium mb-2">
              Recent errors ({status.recent_errors.minutes ?? "—"} min)
            </h2>
            {status.recent_errors.error ? (
              <p className="text-sm text-black/50 dark:text-white/50">{status.recent_errors.error}</p>
            ) : (status.recent_errors.errors?.length ?? 0) === 0 ? (
              <p className="text-sm text-black/50 dark:text-white/50">No errors — looking good.</p>
            ) : (
              <ul className="flex flex-col gap-1 text-sm">
                {status.recent_errors.errors!.map((e, i) => (
                  <li key={i} className="border border-black/10 dark:border-white/10 rounded p-2">
                    <span className="text-red-500 font-medium">{e.severity}</span> · {e.service} ·{" "}
                    {e.message}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2 className="font-medium mb-2">Alert policies</h2>
            {status.alert_policies.error ? (
              <p className="text-sm text-black/50 dark:text-white/50">{status.alert_policies.error}</p>
            ) : (
              <ul className="flex flex-col gap-1 text-sm">
                {status.alert_policies.policies?.map((p, i) => (
                  <li key={i} className="flex justify-between border border-black/10 dark:border-white/10 rounded p-2">
                    <span>{p.name}</span>
                    <span>{p.enabled ? "enabled" : "disabled"}</span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section>
            <h2 className="font-medium mb-2">Recent deployments</h2>
            {status.recent_deployments.error ? (
              <p className="text-sm text-black/50 dark:text-white/50">{status.recent_deployments.error}</p>
            ) : (
              <ul className="flex flex-col gap-1 text-sm">
                {status.recent_deployments.deployments?.map((d, i) => (
                  <li key={i} className="flex justify-between border border-black/10 dark:border-white/10 rounded p-2">
                    <span>
                      {d.service} · {d.revision}
                    </span>
                    <span>
                      {d.healthy ? "healthy" : "unhealthy"} · {new Date(d.created_at).toLocaleString()}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
