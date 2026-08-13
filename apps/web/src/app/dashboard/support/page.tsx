import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { SupportView } from "@/components/SupportView";
import { apiFetch } from "@/lib/api";

export default async function SupportPage() {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  const [tickets, currentUser] = await Promise.all([
    apiFetch("/tickets", { headers: { Authorization: `Bearer ${token}` } }),
    apiFetch("/auth/me", { headers: { Authorization: `Bearer ${token}` } }),
  ]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold">Support</h1>
        <p className="text-sm text-black/50 dark:text-white/50 mt-1">
          Found a bug or something not working right? Describe it below — we&apos;ll check for
          similar reports first, then Gemini classifies its priority and files it with the team.
        </p>
      </div>
      <SupportView initialTickets={tickets} currentUserId={currentUser.id} />
    </div>
  );
}
