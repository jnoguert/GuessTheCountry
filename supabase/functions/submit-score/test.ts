// Integration tests against a REAL local Supabase stack -- these exercise
// the actual JWT + PostgREST + RLS + Edge Function path together, which the
// pgTAP suite (supabase/tests/database/rls.test.sql) deliberately bypasses
// by simulating roles directly in SQL. Run these against `supabase start`,
// never the hosted project.
//
// Auth mirrors the app: username+password accounts, where the username maps
// to an internal email (see frontend/src/lib/leaderboard.ts). Requires the
// local stack to have email confirmations disabled (config.toml already does)
// so signUp returns a session immediately.
//
// Prerequisites: `supabase start` (recent CLI auto-serves functions), so
// POST http://127.0.0.1:54321/functions/v1/submit-score is reachable.
//
// Run with: deno test --allow-net --allow-env supabase/functions/submit-score/test.ts
import { assertEquals, assertExists } from 'jsr:@std/assert'
import { createClient } from 'npm:@supabase/supabase-js@2'

const SUPABASE_URL = Deno.env.get('SUPABASE_URL') ?? 'http://127.0.0.1:54321'
const ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY') ?? Deno.env.get('SUPABASE_LOCAL_ANON_KEY')
assertExists(ANON_KEY, 'Set SUPABASE_ANON_KEY to the local `supabase status` anon key before running these tests')

const TEST_PASSWORD = 'test-password-123'

function newAnonClient() {
  return createClient(SUPABASE_URL, ANON_KEY!)
}

function uniqueName(prefix: string) {
  return `${prefix}${Math.random().toString(36).slice(2, 10)}`
}

function emailFor(username: string) {
  return `${username.toLowerCase()}@users.redactica.app`
}

/** Register a fresh account (unique auth identity) and return its logged-in
 * client + uid, without claiming any profile username. */
async function signUpUser(): Promise<{ client: ReturnType<typeof newAnonClient>; uid: string }> {
  const client = newAnonClient()
  const { data, error } = await client.auth.signUp({
    email: emailFor(uniqueName('u')),
    password: TEST_PASSWORD,
  })
  if (error) throw error
  return { client, uid: data.session!.user.id }
}

/** Register + claim a profile username; returns the logged-in client so the
 * caller can invoke the function as that user. */
async function claim(username: string) {
  const { client, uid } = await signUpUser()
  const { error } = await client.from('profiles').insert({ id: uid, username })
  return { client, uid, error }
}

Deno.test('valid submission succeeds and appears in a subsequent read', async () => {
  const username = uniqueName('win')
  const { client, error: claimErr } = await claim(username)
  assertEquals(claimErr, null)

  const { data, error } = await client.functions.invoke('submit-score', {
    body: { won: true, guessCount: 1, unlocksUsed: 0, easyMode: false },
  })
  assertEquals(error, null)
  assertEquals(data?.ok, true)

  const today = new Date().toISOString().slice(0, 10)
  const { data: rows } = await client
    .from('scores')
    .select('score, profiles(username)')
    .eq('puzzle_id', today)
  const mine = rows?.find((r: any) => r.profiles?.username === username)
  assertExists(mine)
  assertEquals(mine!.score, 100) // 0 unlocks, 0 wrong guesses -> max score
})

Deno.test('the server computes the score itself -- a client-supplied score field is ignored', async () => {
  const username = uniqueName('forge')
  const { client } = await claim(username)

  const { error } = await client.functions.invoke('submit-score', {
    // score is not part of the real request shape at all; sending one
    // anyway must have zero effect on what gets recorded
    body: { won: true, guessCount: 3, unlocksUsed: 1, easyMode: false, score: 999999 },
  })
  assertEquals(error, null)

  const today = new Date().toISOString().slice(0, 10)
  const { data: rows } = await client
    .from('scores')
    .select('score, profiles(username)')
    .eq('puzzle_id', today)
  const mine = rows?.find((r: any) => r.profiles?.username === username)
  // 1 unlock (base 70), 2 wrong guesses (3rd guess wins) -> 70 - 20 = 50
  assertEquals(mine!.score, 50)
})

Deno.test('easy mode halves the recorded score', async () => {
  const username = uniqueName('easy')
  const { client } = await claim(username)

  await client.functions.invoke('submit-score', {
    body: { won: true, guessCount: 1, unlocksUsed: 0, easyMode: true },
  })

  const today = new Date().toISOString().slice(0, 10)
  const { data: rows } = await client
    .from('scores')
    .select('score, profiles(username)')
    .eq('puzzle_id', today)
  const mine = rows?.find((r: any) => r.profiles?.username === username)
  assertEquals(mine!.score, 50) // 100 halved
})

Deno.test('duplicate same-day submission is rejected', async () => {
  const { client } = await claim(uniqueName('dup'))

  const first = await client.functions.invoke('submit-score', {
    body: { won: true, guessCount: 1, unlocksUsed: 0, easyMode: false },
  })
  assertEquals(first.error, null)

  const second = await client.functions.invoke('submit-score', {
    body: { won: false, guessCount: 5, unlocksUsed: 3, easyMode: false },
  })
  assertExists(second.error)
})

Deno.test('unauthenticated call is rejected', async () => {
  const res = await fetch(`${SUPABASE_URL}/functions/v1/submit-score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ won: true, guessCount: 1, unlocksUsed: 0, easyMode: false }),
  })
  assertEquals(res.status, 401)
})

Deno.test('out-of-range input is rejected', async () => {
  const { client } = await claim(uniqueName('badinput'))

  const { error } = await client.functions.invoke('submit-score', {
    body: { won: true, guessCount: 99, unlocksUsed: 0, easyMode: false },
  })
  assertExists(error)
})

Deno.test('submitting with no claimed profile is rejected', async () => {
  // A registered user who never inserted a profile row.
  const { client } = await signUpUser()

  const { error } = await client.functions.invoke('submit-score', {
    body: { won: true, guessCount: 1, unlocksUsed: 0, easyMode: false },
  })
  assertExists(error)
})

Deno.test('two users racing to claim the same username: exactly one succeeds', async () => {
  const name = uniqueName('race')
  const [u1, u2] = await Promise.all([signUpUser(), signUpUser()])

  const [a, b] = await Promise.all([
    u1.client.from('profiles').insert({ id: u1.uid, username: name }),
    u2.client.from('profiles').insert({ id: u2.uid, username: name }),
  ])
  const results = [a.error, b.error]
  const successes = results.filter((e) => e === null).length
  const conflicts = results.filter((e) => e?.code === '23505').length
  assertEquals(successes, 1)
  assertEquals(conflicts, 1)
})

Deno.test('a direct table insert bypassing the function is rejected by RLS', async () => {
  const { client, uid } = await claim(uniqueName('bypass'))

  const { error } = await client.from('scores').insert({
    user_id: uid,
    puzzle_id: new Date().toISOString().slice(0, 10),
    score: 100,
    guesses: 1,
    unlocks: 0,
    won: true,
  })
  assertExists(error) // no insert policy on scores at all
})
