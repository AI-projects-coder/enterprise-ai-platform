import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Sidebar } from "@/components/Sidebar";
import { apiFetch, ApiError } from "@/lib/api";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;

  if (!token) {
    redirect("/login");
  }

  let email: string;
  try {
    const user = await apiFetch("/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    email = user.email;
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) {
      redirect("/login");
    }
    throw err;
  }

  return (
    <div className="flex">
      <Sidebar email={email} />
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
