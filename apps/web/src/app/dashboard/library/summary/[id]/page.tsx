import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LibraryPageHeader } from "@/components/LibraryPageHeader";
import { SummaryView } from "@/components/SummaryView";
import { apiFetch } from "@/lib/api";
import type { VideoDetail } from "@/lib/videoTypes";

export default async function SummaryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const video: VideoDetail = await apiFetch(`/videos/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  return (
    <div>
      <LibraryPageHeader title={`Summary Notes — ${video.title}`} />
      <SummaryView video={video} />
    </div>
  );
}
