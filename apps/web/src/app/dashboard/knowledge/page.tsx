import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { KnowledgeView } from "@/components/KnowledgeView";
import { apiFetch } from "@/lib/api";

export default async function KnowledgePage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const documents = await apiFetch("/documents", {
    headers: { Authorization: `Bearer ${token}` },
  });

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Knowledge</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          Upload text your chats can draw on for context.
        </p>
      </div>
      <KnowledgeView initialDocuments={documents} />
    </div>
  );
}
