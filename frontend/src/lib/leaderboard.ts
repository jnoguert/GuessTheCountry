// Leaderboard client. The game itself is fully static, but rankings need a
// real backend: Supabase (Postgres + Auth + Row Level Security) provides
// that without us hosting anything. Reads are public (RLS SELECT policies);
// writes go through the `submit-score` Edge Function, which is the only
// thing allowed to insert into `scores` at all.
import { supabase } from './supabaseClient'

export interface Identity {
  username: string
}

export interface TodayEntry {
  username: string
  score: number
  guesses: number
  unlocks: number
  won: boolean
}

export interface AlltimeEntry {
  username: string
  total_score: number
  wins: number
  games: number
}

/** Build-time feature detection: no Supabase project configured (e.g. a
 * plain static deploy with no env vars set) means no leaderboard, full
 * stop -- no network probe needed, unlike the old runtime ping. */
export function isLeaderboardAvailable(): boolean {
  return supabase !== null
}

/** Existing session's claimed username, if any. Reads are public and don't
 * need a session at all -- this is only used to decide whether to show the
 * "choose a username" form or the player's own row highlighted. */
export async function getIdentity(): Promise<Identity | null> {
  if (!supabase) return null
  const { data } = await supabase.auth.getSession()
  const uid = data.session?.user?.id
  if (!uid) return null

  const { data: profile } = await supabase
    .from('profiles')
    .select('username')
    .eq('id', uid)
    .maybeSingle()

  return profile ? { username: profile.username as string } : null
}

export type ClaimResult = 'ok' | 'username_taken' | 'error'

/** Claims a username for this browser, immediately and durably (a real row
 * in `profiles`, not just a local pending value) -- so the player finds out
 * right away if the name is taken, rather than discovering it only after
 * playing a full game. Mints an anonymous Supabase session on first use
 * only (checked via getSession() first); opening the leaderboard to just
 * look at it never creates a session, only actually choosing a name does.
 * The insert goes through the user-scoped client, so RLS's
 * `auth.uid() = id` check is the actual enforcement, not just app logic. */
export async function claimUsername(username: string): Promise<ClaimResult> {
  if (!supabase) return 'error'
  try {
    const { data: existing } = await supabase.auth.getSession()
    let uid = existing.session?.user?.id

    if (!uid) {
      const { data: signInData, error } = await supabase.auth.signInAnonymously()
      if (error || !signInData.session) return 'error'
      uid = signInData.session.user.id
    }

    const { error: insertErr } = await supabase
      .from('profiles')
      .insert({ id: uid, username })

    if (insertErr) {
      return insertErr.code === '23505' ? 'username_taken' : 'error'
    }
    return 'ok'
  } catch {
    return 'error'
  }
}

export type SubmitResult = 'ok' | 'error'

/** Records today's result. Requires an existing session (i.e. a username
 * must already have been claimed) -- the Edge Function rejects
 * unauthenticated calls outright. The score itself is never sent; the
 * function recomputes it server-side from these inputs. */
export async function submitScore(
  won: boolean,
  guessCount: number,
  unlocksUsed: number,
  easyMode: boolean
): Promise<SubmitResult> {
  if (!supabase) return 'error'
  try {
    const { data: sessionData } = await supabase.auth.getSession()
    if (!sessionData.session) return 'error' // no claimed username yet

    const { error } = await supabase.functions.invoke('submit-score', {
      body: { won, guessCount, unlocksUsed, easyMode },
    })

    // "already submitted today" is a soft-success from the caller's point
    // of view -- their result IS recorded, just from an earlier attempt.
    const errorBody = (error as { context?: { error?: string } } | null)?.context
    if (error && errorBody?.error !== 'already_submitted') return 'error'
    return 'ok'
  } catch {
    return 'error'
  }
}

export async function fetchToday(): Promise<TodayEntry[]> {
  if (!supabase) return []
  const today = new Date().toISOString().slice(0, 10)
  const { data, error } = await supabase
    .from('scores')
    .select('score, guesses, unlocks, won, profiles(username)')
    .eq('puzzle_id', today)
    .order('score', { ascending: false })
    .order('guesses', { ascending: true })
    .order('created_at', { ascending: true })
    .limit(50)

  if (error || !data) return []
  return data.map((row: any) => ({
    username: row.profiles?.username ?? '?',
    score: row.score,
    guesses: row.guesses,
    unlocks: row.unlocks,
    won: row.won,
  }))
}

export async function fetchAlltime(): Promise<AlltimeEntry[]> {
  if (!supabase) return []
  const { data, error } = await supabase
    .from('alltime_leaderboard')
    .select('*')
    .limit(50)

  if (error || !data) return []
  return data as AlltimeEntry[]
}
