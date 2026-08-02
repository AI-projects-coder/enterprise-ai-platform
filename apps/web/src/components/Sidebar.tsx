"use client";

import { useRouter } from "next/navigation";
import { MODULE_REGISTRY } from "@/lib/modules";

export function Sidebar({ email }: { email: string }) {
  const router = useRouter();

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <aside className="w-64 shrink-0 border-r border-black/10 dark:border-white/10 p-4 flex flex-col justify-between h-screen">
      <div>
        <div className="font-semibold mb-6">Enterprise AI Platform</div>
        <nav className="flex flex-col gap-1">
          {MODULE_REGISTRY.length === 0 && (
            <p className="text-sm text-black/50 dark:text-white/50">
              No products enabled yet.
            </p>
          )}
          {MODULE_REGISTRY.map((m) => (
            <a key={m.route} href={m.route} className="text-sm px-2 py-1.5 rounded hover:bg-black/5 dark:hover:bg-white/10">
              {m.icon} {m.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="text-sm">
        <div className="text-black/50 dark:text-white/50 mb-2 truncate">{email}</div>
        <button onClick={logout} className="text-sm underline">
          Log out
        </button>
      </div>
    </aside>
  );
}
