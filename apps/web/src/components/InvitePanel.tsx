"use client";

import { useState } from "react";

export function InvitePanel() {
  const [link, setLink] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function generateInvite() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/enterprise/invites", { method: "POST" });
      if (!res.ok) throw new Error((await res.json()).detail);
      const invite = await res.json();
      setLink(`${window.location.origin}/login?invite=${invite.token}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="border border-black/10 dark:border-white/10 rounded-lg p-4 mb-8">
      <h2 className="font-medium mb-2">Invite a teammate</h2>
      <p className="text-sm text-black/50 dark:text-white/50 mb-3">
        Generates a one-time link, valid for 7 days, that adds them to your organization.
      </p>
      <button
        onClick={generateInvite}
        disabled={loading}
        className="bg-foreground text-background rounded px-3 py-2 text-sm font-medium disabled:opacity-50"
      >
        {loading ? "..." : "Generate invite link"}
      </button>
      {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
      {link && (
        <div className="mt-3 text-sm">
          <input
            readOnly
            value={link}
            onFocus={(e) => e.target.select()}
            className="w-full border border-black/20 dark:border-white/20 rounded px-3 py-2 bg-transparent"
          />
        </div>
      )}
    </div>
  );
}
