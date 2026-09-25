import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Real config only - never a placeholder that silently "works". If these
// aren't set, auth features fail loudly instead of pretending to log in.
export const supabaseConfigured = Boolean(url && anonKey);

export const supabase = supabaseConfigured
  ? createClient(url as string, anonKey as string)
  : null;
