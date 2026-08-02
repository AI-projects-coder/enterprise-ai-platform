import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ChatView, type Message } from "@/components/ChatView";
import { apiFetch, ApiError } from "@/lib/api";

type ConversationDetail = {
  id: string;
  title: string | null;
  messages: { role: "user" | "assistant"; content: string }[];
};

export default async function ConversationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  let conversation: ConversationDetail;
  try {
    conversation = await apiFetch(`/conversations/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      redirect("/dashboard/chat");
    }
    throw err;
  }

  const initialMessages: Message[] = conversation.messages.map((m) => ({
    role: m.role,
    content: m.content,
  }));

  return (
    <div>
      <div className="mb-4">
        <h1 className="text-2xl font-semibold">{conversation.title || "Conversation"}</h1>
      </div>
      <ChatView conversationId={conversation.id} initialMessages={initialMessages} />
    </div>
  );
}
