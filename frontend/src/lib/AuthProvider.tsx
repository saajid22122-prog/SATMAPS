"use client";

import { createContext, useContext, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase, supabaseConfigured } from "./supabase";
import { api } from "./api";

interface AuthState {
  session: Session | null;
  roles: string[];
  loading: boolean;
  configured: boolean;
  signInWithPassword: (email: string, password: string) => Promise<string | null>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_event, s) => setSession(s));
    setLoading(false);
    return () => sub.subscription.unsubscribe();
  }, []);

  // Real roles fetched from our own backend (user_roles table), not from
  // Supabase session metadata - a client can't grant itself a role this way.
  useEffect(() => {
    if (!session) {
      setRoles([]);
      return;
    }
    api
      .getMe()
      .then((me) => setRoles(me.roles))
      .catch(() => setRoles([]));
  }, [session]);

  const signInWithPassword = async (email: string, password: string) => {
    if (!supabase) return "Supabase is not configured (missing NEXT_PUBLIC_SUPABASE_URL/ANON_KEY).";
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    return error ? error.message : null;
  };

  const signOut = async () => {
    if (!supabase) return;
    await supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider
      value={{ session, roles, loading, configured: supabaseConfigured, signInWithPassword, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
