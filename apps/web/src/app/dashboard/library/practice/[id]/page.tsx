import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LibraryPageHeader } from "@/components/LibraryPageHeader";
import { QuizView } from "@/components/QuizView";
import { apiFetch } from "@/lib/api";
import type { VideoDetail } from "@/lib/videoTypes";

export default async function PracticePage({ params }: { params: Promise<{ id: string }> }) {
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
      <LibraryPageHeader title={`Q&A Assessment — ${video.title}`} />
      {video.quiz && video.quiz.length > 0 ? (
        <QuizView videoId={video.id} quiz={video.quiz} />
      ) : (
        <p className="text-sm text-black/50 dark:text-white/50">No quiz available for this video.</p>
      )}
    </div>
  );
}
