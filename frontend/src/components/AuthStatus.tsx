"use client";

import { useState } from "react";
import { useAuth } from "@/lib/AuthProvider";

export default function AuthStatus() {
  const { session, roles, configured, signInWithPassword, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!configured) {
    return <span className="text-xs text-gray-400 ml-auto">Auth not configured</span>;
  }

  if (session) {
    return (
      <div className="ml-auto flex items-center gap-2 text-xs text-gray-600">
        <span>{session.user.email}</span>
        {roles.length > 0 && (
          <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">{roles.join(", ")}</span>
        )}
        <button onClick={() => signOut()} className="text-gray-500 hover:text-red-600 underline">
          Sign out
        </button>
      </div>
    );
  }

  return (
    <div className="ml-auto relative">
      <button onClick={() => setOpen((v) => !v)} className="text-xs text-blue-600 hover:underline">
        Sign in
      </button>
      {open && (
        <div className="absolute right-0 top-6 bg-white border rounded-lg shadow-lg p-3 w-64 z-30 space-y-2">
          <input
            type="email"
            placeholder="Email"
            className="border rounded px-2 py-1 text-sm w-full"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <input
            type="password"
            placeholder="Password"
            className="border rounded px-2 py-1 text-sm w-full"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <div className="text-red-500 text-xs">{error}</div>}
          <button
            disabled={submitting}
            onClick={async () => {
              setSubmitting(true);
              setError(null);
              const err = await signInWithPassword(email, password);
              setSubmitting(false);
              if (err) setError(err);
              else setOpen(false);
            }}
            className="bg-blue-600 disabled:bg-gray-300 text-white text-xs px-3 py-1.5 rounded w-full"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </div>
      )}
    </div>
  );
}
