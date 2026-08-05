"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const inviteToken = searchParams.get("invite");

  const [mode, setMode] = useState<"login" | "register">(inviteToken ? "register" : "login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [profession, setProfession] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (mode === "register") {
        const res = await fetch("/api/auth/register", {
          method: "POST",
          body: JSON.stringify({ email, password, profession, invite_token: inviteToken || undefined }),
        });
        if (!res.ok) throw new Error((await res.json()).detail);
      }

      const res = await fetch("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) throw new Error((await res.json()).detail);

      router.push("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={onSubmit} className="w-80 flex flex-col gap-4">
        <h1 className="text-xl font-semibold">
          {mode === "login" ? "Log in" : "Create account"}
        </h1>

        {inviteToken && mode === "register" && (
          <p className="text-sm text-black/60 dark:text-white/60">
            You&apos;ve been invited to join an organization — creating an account will add you
            as a member.
          </p>
        )}

        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        />
        <input
          type="password"
          required
          minLength={8}
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
        />

        {mode === "register" && (
          <select
            required
            value={profession}
            onChange={(e) => setProfession(e.target.value)}
            className="border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
          >
            <option value="" disabled>
              Profession
            </option>
            <option value="student">Student</option>
            <option value="job_seeker">Job Seeker</option>
            <option value="it_professional">IT Professional</option>
          </select>
        )}

        {error && <p className="text-sm text-red-500">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="bg-foreground text-background rounded px-3 py-2 font-medium disabled:opacity-50"
        >
          {loading ? "..." : mode === "login" ? "Log in" : "Sign up"}
        </button>

        {!inviteToken && (
          <button
            type="button"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
            className="text-sm underline"
          >
            {mode === "login" ? "Need an account? Sign up" : "Have an account? Log in"}
          </button>
        )}
      </form>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
