import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { DatasetsView } from "@/components/DatasetsView";
import { apiFetch } from "@/lib/api";

export default async function DatasetsPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const datasets = await apiFetch("/datasets", {
    headers: { Authorization: `Bearer ${token}` },
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Data Scientist</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          Upload a CSV dataset, then ask chat questions about it — summary statistics,
          correlations, and group-by aggregations, computed live against the real data.
        </p>
      </div>
      <DatasetsView initialDatasets={datasets} />
    </div>
  );
}
