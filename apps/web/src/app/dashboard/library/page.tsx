import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { LibraryView } from "@/components/LibraryView";
import { apiFetch } from "@/lib/api";

export default async function LibraryPage() {
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
        <h1 className="text-2xl font-semibold">Library</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          Upload a video from your device or a direct link — Gemini transcribes it, writes a
          summary, and generates a quiz, all in one pass. Your upload stays private until you
          publish it, after which it shows up in everyone&apos;s library below.
        </p>
      </div>
      <LibraryView initialVideos={videos} />
    </div>
  );
}
