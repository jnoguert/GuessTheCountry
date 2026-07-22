import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

// Both env vars are optional at build time: on a plain static host with no
// Supabase project configured, the leaderboard feature-detects their
// absence (see lib/leaderboard.ts) and simply doesn't render. Guard against
// constructing a client with undefined values, which supabase-js throws on.
export const supabase = url && anonKey ? createClient(url, anonKey) : null
