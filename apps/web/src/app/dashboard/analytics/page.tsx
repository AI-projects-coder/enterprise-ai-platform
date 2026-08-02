import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { apiFetch } from "@/lib/api";

type DailyUsage = {
  day: string;
  llm_calls: number;
  total_tokens: number;
};

type UsageSummary = {
  since_days: number;
  conversation_count: number;
  message_count: number;
  document_count: number;
  llm_call_count: number;
  total_tokens: number;
  daily: DailyUsage[];
};

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="border border-black/10 dark:border-white/10 rounded-lg p-4">
      <div className="text-sm text-black/50 dark:text-white/50">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value.toLocaleString()}</div>
    </div>
  );
}

export default async function AnalyticsPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const summary: UsageSummary = await apiFetch("/analytics/me?since_days=30", {
    headers: { Authorization: `Bearer ${token}` },
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          Your usage over the last {summary.since_days} days.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
        <StatCard label="Conversations" value={summary.conversation_count} />
        <StatCard label="Messages sent" value={summary.message_count} />
        <StatCard label="Documents uploaded" value={summary.document_count} />
        <StatCard label="LLM calls" value={summary.llm_call_count} />
        <StatCard label="Total tokens" value={summary.total_tokens} />
      </div>

      <h2 className="text-lg font-medium mb-3">Daily token usage</h2>
      {summary.daily.length === 0 ? (
        <p className="text-sm text-black/50 dark:text-white/50">No usage yet in this period.</p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-left text-black/50 dark:text-white/50 border-b border-black/10 dark:border-white/10">
              <th className="py-2 pr-4 font-normal">Date</th>
              <th className="py-2 pr-4 font-normal">LLM calls</th>
              <th className="py-2 pr-4 font-normal">Total tokens</th>
            </tr>
          </thead>
          <tbody>
            {summary.daily.map((d) => (
              <tr key={d.day} className="border-b border-black/5 dark:border-white/5">
                <td className="py-2 pr-4">{d.day}</td>
                <td className="py-2 pr-4">{d.llm_calls}</td>
                <td className="py-2 pr-4">{d.total_tokens.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
