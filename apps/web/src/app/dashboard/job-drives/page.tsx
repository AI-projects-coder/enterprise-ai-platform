import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { JobDrivesView } from "@/components/JobDrivesView";
import { apiFetch } from "@/lib/api";

export default async function JobDrivesPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const drives = await apiFetch("/job-drives", {
    headers: { Authorization: `Bearer ${token}` },
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Campus Drives</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          Pick a role, city, and experience level, then Generate — Gemini searches the real web
          for campus drives in the next two weeks matching your criteria. Your result stays
          private until you click Publish, after which everyone can see it in the feed below.
          Always verify directly with the company/college before attending.
        </p>
      </div>
      <JobDrivesView initialDrives={drives} />
    </div>
  );
}
