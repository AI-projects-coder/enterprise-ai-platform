import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { CloudConfigsView } from "@/components/CloudConfigsView";
import { apiFetch } from "@/lib/api";

export default async function CloudConfigsPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const configs = await apiFetch("/cloud-configs", {
    headers: { Authorization: `Bearer ${token}` },
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Cloud Architect</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          Upload a Terraform (.tf) file, then ask chat about it — resource inventory,
          security/best-practice checks, and a rough cost estimate. Advisory only: no cloud
          credentials are used and nothing is deployed or changed.
        </p>
      </div>
      <CloudConfigsView initialConfigs={configs} />
    </div>
  );
}
