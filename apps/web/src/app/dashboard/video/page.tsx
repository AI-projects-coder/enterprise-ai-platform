import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { VideoView } from "@/components/VideoView";
import { apiFetch } from "@/lib/api";

export default async function VideoPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const videos = await apiFetch("/videos", {
    headers: { Authorization: `Bearer ${token}` },
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Video Intelligence</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          Upload a video — Gemini transcribes and summarizes it, and the content becomes
          searchable in chat, same as an uploaded document. Reload the page to see status
          updates while processing.
        </p>
      </div>
      <VideoView initialVideos={videos} />
    </div>
  );
}
