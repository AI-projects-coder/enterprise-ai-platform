import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { apiFetch } from "@/lib/api";

type ConversationSummary = {
  id: string;
  title: string | null;
  updated_at: string;
};

export default async function ChatLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const conversations: ConversationSummary[] = await apiFetch("/conversations", {
    headers: { Authorization: `Bearer ${token}` },
  });

  return (
    <div className="flex gap-8">
      <aside className="w-56 shrink-0">
        <Link href="/dashboard/chat" className="block text-sm font-medium mb-4 hover:underline">
          + New chat
        </Link>
        <nav className="flex flex-col gap-1">
          {conversations.length === 0 && (
            <p className="text-sm text-black/50 dark:text-white/50">No conversations yet.</p>
          )}
          {conversations.map((c) => (
            <Link
              key={c.id}
              href={`/dashboard/chat/${c.id}`}
              className="text-sm px-2 py-1.5 rounded hover:bg-black/5 dark:hover:bg-white/10 truncate"
            >
              {c.title || "Untitled conversation"}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="flex-1">{children}</div>
    </div>
  );
}
