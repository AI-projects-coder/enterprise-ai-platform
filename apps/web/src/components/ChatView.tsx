"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export type Message = { role: "user" | "assistant"; content: string };

export function ChatView({
  conversationId: initialConversationId,
  initialMessages,
}: {
  conversationId: string | null;
  initialMessages: Message[];
}) {
  const router = useRouter();
  const [conversationId, setConversationId] = useState(initialConversationId);
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || loading) return;

    setError(null);
    setLoading(true);
    const content = input;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content }]);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        body: JSON.stringify({ message: content, conversation_id: conversationId }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Something went wrong");

      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);

      if (!conversationId) {
        setConversationId(data.conversation_id);
        router.push(`/dashboard/chat/${data.conversation_id}`);
        router.refresh();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col max-w-2xl gap-4">
      <div className="flex flex-col gap-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "self-end bg-foreground text-background rounded px-3 py-2 max-w-[80%]"
                : "self-start bg-black/5 dark:bg-white/10 rounded px-3 py-2 max-w-[80%] whitespace-pre-wrap"
            }
          >
            {m.content}
          </div>
        ))}
        {loading && (
          <div className="text-sm text-black/50 dark:text-white/50">Thinking...</div>
        )}
      </div>

      {error && <p className="text-sm text-red-500">{error}</p>}

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask something..."
          className="flex-1 border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        />
        <button
          type="submit"
          disabled={loading}
          className="bg-foreground text-background rounded px-4 py-2 font-medium disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
