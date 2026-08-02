import { ChatView } from "@/components/ChatView";

export default function ChatPage() {
  return (
    <div>
      <div className="mb-4">
        <h1 className="text-2xl font-semibold">Chat</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          Start a new conversation.
        </p>
      </div>
      <ChatView conversationId={null} initialMessages={[]} />
    </div>
  );
}
