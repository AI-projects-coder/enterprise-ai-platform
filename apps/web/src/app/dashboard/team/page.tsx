import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { InvitePanel } from "@/components/InvitePanel";
import { apiFetch } from "@/lib/api";

type Member = {
  id: string;
  email: string;
  role: string;
  created_at: string;
};

type AuditEntry = {
  id: string;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
};

export default async function TeamPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const authHeader = { Authorization: `Bearer ${token}` };
  const me = await apiFetch("/auth/me", { headers: authHeader });
  const isOwner = me.role === "owner";

  const members: Member[] = await apiFetch("/enterprise/members", { headers: authHeader });
  const auditLog: AuditEntry[] = isOwner
    ? await apiFetch("/enterprise/audit-log", { headers: authHeader })
    : [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Team</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          {members.length} {members.length === 1 ? "member" : "members"} in your organization.
        </p>
      </div>

      {isOwner && <InvitePanel />}

      <h2 className="text-lg font-medium mb-3">Members</h2>
      <table className="w-full text-sm border-collapse mb-8">
        <thead>
          <tr className="text-left text-black/50 dark:text-white/50 border-b border-black/10 dark:border-white/10">
            <th className="py-2 pr-4 font-normal">Email</th>
            <th className="py-2 pr-4 font-normal">Role</th>
            <th className="py-2 pr-4 font-normal">Joined</th>
          </tr>
        </thead>
        <tbody>
          {members.map((m) => (
            <tr key={m.id} className="border-b border-black/5 dark:border-white/5">
              <td className="py-2 pr-4">{m.email}</td>
              <td className="py-2 pr-4">{m.role}</td>
              <td className="py-2 pr-4">{new Date(m.created_at).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {isOwner && (
        <>
          <h2 className="text-lg font-medium mb-3">Audit log</h2>
          {auditLog.length === 0 ? (
            <p className="text-sm text-black/50 dark:text-white/50">No activity recorded yet.</p>
          ) : (
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="text-left text-black/50 dark:text-white/50 border-b border-black/10 dark:border-white/10">
                  <th className="py-2 pr-4 font-normal">Action</th>
                  <th className="py-2 pr-4 font-normal">Details</th>
                  <th className="py-2 pr-4 font-normal">When</th>
                </tr>
              </thead>
              <tbody>
                {auditLog.map((a) => (
                  <tr key={a.id} className="border-b border-black/5 dark:border-white/5">
                    <td className="py-2 pr-4">{a.action}</td>
                    <td className="py-2 pr-4 text-black/60 dark:text-white/60">
                      {JSON.stringify(a.details)}
                    </td>
                    <td className="py-2 pr-4">{new Date(a.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  );
}
