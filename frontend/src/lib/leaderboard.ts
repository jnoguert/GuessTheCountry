// Leaderboard client. The game itself is fully static, but rankings need a
// real backend: Supabase (Postgres + Auth + Row Level Security) provides
// that without us hosting anything. Reads are public (RLS SELECT policies);
// writes go through the `submit-score` Edge Function, which is the only
// thing allowed to insert into `scores` at all.
//
// Accounts are username + password. Supabase Auth is email-based, so the
// username is mapped to a hidden internal email (`name@INTERNAL_EMAIL_DOMAIN`);
// Supabase still hashes the password (bcrypt) and the address is never shown
// or emailed. This means there is no password recovery by design -- a chosen,
// deliberate trade-off for a frictionless "username only" login. Requires the
// project to have email confirmations DISABLED (an unconfirmable internal
// address would otherwise lock the account out).
import { supabase } from './supabaseClient'

/** Internal-only address domain for the username->email mapping. No mail is
 * ever sent here (email confirmations are off), so it needn't be routable. */
const INTERNAL_EMAIL_DOMAIN = 'users.redactica.app'
export const MIN_PASSWORD_LENGTH = 8

function usernameToEmail(username: string): string {
  // Lower-cased so login is case-insensitive and matches the citext-unique
  // profile username; the display-case username is stored in `profiles`.
  return `${username.trim().toLowerCase()}@${INTERNAL_EMAIL_DOMAIN}`
}

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
 * stop -- no network probe needed. */
export function isLeaderboardAvailable(): boolean {
  return supabase !== null
}

/** The logged-in player's username, if a session exists. Reads are public and
 * don't need a session; this only decides whether to show the auth form or
 * the player's own row highlighted + a log-out button. */
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

export type AuthResult =
  | 'ok'
  | 'username_taken'
  | 'invalid_credentials'
  | 'weak_password'
  | 'error'

/** Create an account: a Supabase user (username -> internal email + password)
 * plus a `profiles` row carrying the display-case username. The profile insert
 * is RLS-enforced (`auth.uid() = id`), so the freshly minted session is the
 * authorization, not app logic. Needs email confirmations disabled on the
 * project, otherwise no session is issued and the profile insert can't run. */
export async function register(username: string, password: string): Promise<AuthResult> {
  if (!supabase) return 'error'
  if (password.length < MIN_PASSWORD_LENGTH) return 'weak_password'
  try {
    const { data, error } = await supabase.auth.signUp({
      email: usernameToEmail(username),
      password,
    })
    if (error) {
      const msg = (error.message || '').toLowerCase()
      if (msg.includes('already') || (error as { code?: string }).code === 'user_already_exists') {
        return 'username_taken'
      }
      if (msg.includes('password')) return 'weak_password'
      return 'error'
    }

    const uid = data.session?.user?.id ?? data.user?.id
    if (!uid || !data.session) return 'error' // no session => confirmations still on

    const { error: insertErr } = await supabase
      .from('profiles')
      .insert({ id: uid, username: username.trim() })
    if (insertErr) {
      return insertErr.code === '23505' ? 'username_taken' : 'error'
    }
    return 'ok'
  } catch {
    return 'error'
  }
}

/** Log in with username + password. As a safety net, if the account somehow
 * has no profile row yet (e.g. a registration that half-completed), create it
 * now so the leaderboard can show a name and the Edge Function accepts writes. */
export async function login(username: string, password: string): Promise<AuthResult> {
  if (!supabase) return 'error'
  try {
    const { data, error } = await supabase.auth.signInWithPassword({
      email: usernameToEmail(username),
      password,
    })
    if (error || !data.session) return 'invalid_credentials'

    const uid = data.session.user.id
    const { data: profile } = await supabase
      .from('profiles')
      .select('id')
      .eq('id', uid)
      .maybeSingle()
    if (!profile) {
      await supabase.from('profiles').insert({ id: uid, username: username.trim() })
    }
    return 'ok'
  } catch {
    return 'invalid_credentials'
  }
}

export async function logout(): Promise<void> {
  if (!supabase) return
  await supabase.auth.signOut()
}

export type SubmitResult = 'ok' | 'error'

/** Records today's result. Requires a logged-in session -- the Edge Function
 * rejects unauthenticated calls outright. The score itself is never sent; the
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
    if (!sessionData.session) return 'error' // not logged in

    const { error } = await supabase.functions.invoke('submit-score', {
      body: { won, guessCount, unlocksUsed, easyMode },
    })

    // "already submitted today" is a soft-success from the caller's point of
    // view -- their result IS recorded, just from an earlier attempt.
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
