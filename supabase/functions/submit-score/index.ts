// Validates and records a daily score. This function is the ENTIRE security
// boundary for writes: `scores` has no INSERT policy, so this is the only
// path in or out. Two rules that must never be relaxed:
//   1. The user id always comes from the caller's verified JWT (auth.uid()
//      equivalent), never from a client-supplied parameter.
//   2. "Today" is always this function's own UTC clock, never a
//      client-supplied puzzle_id -- the request body has no date field.
//
// Username claiming happens separately, client-side, via a direct (RLS-
// enforced) insert into `profiles` before a player ever reaches this
// function -- see frontend/src/lib/leaderboard.ts's claimUsername(). By the
// time this runs, the caller's profile must already exist; if it doesn't,
// that's an error, not something this function creates on the fly.
import { createClient } from 'npm:@supabase/supabase-js@2'
import { computeScore, applyEasyModePenalty, MAX_GUESSES, MAX_UNLOCKS } from '../_shared/score.ts'

const SUPABASE_URL = Deno.env.get('SUPABASE_URL')!
const ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY')!
const SERVICE_ROLE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
  })
}

interface SubmitBody {
  won: boolean
  guessCount: number
  unlocksUsed: number
  easyMode: boolean
}

function todayUTC(): string {
  return new Date().toISOString().slice(0, 10)
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: CORS_HEADERS })
  if (req.method !== 'POST') return json({ error: 'method_not_allowed' }, 405)

  const authHeader = req.headers.get('Authorization')
  if (!authHeader) return json({ error: 'unauthorized' }, 401)

  const userClient = createClient(SUPABASE_URL, ANON_KEY, {
    global: { headers: { Authorization: authHeader } },
  })
  const { data: userData, error: userErr } = await userClient.auth.getUser()
  if (userErr || !userData?.user) return json({ error: 'unauthorized' }, 401)
  const uid = userData.user.id

  let body: SubmitBody
  try {
    body = await req.json()
  } catch {
    return json({ error: 'invalid_input' }, 400)
  }

  const { won, guessCount, unlocksUsed, easyMode } = body
  if (
    typeof won !== 'boolean' ||
    typeof guessCount !== 'number' || guessCount < 0 || guessCount > MAX_GUESSES ||
    typeof unlocksUsed !== 'number' || unlocksUsed < 0 || unlocksUsed > MAX_UNLOCKS ||
    typeof easyMode !== 'boolean'
  ) {
    return json({ error: 'invalid_input' }, 400)
  }

  const adminClient = createClient(SUPABASE_URL, SERVICE_ROLE_KEY)

  // A profile must already exist (created by claimUsername on the client
  // before this function is ever reachable). No profile means no username
  // was ever claimed for this session -- a client bug, not something to
  // paper over here.
  const { data: profile } = await adminClient
    .from('profiles')
    .select('id')
    .eq('id', uid)
    .maybeSingle()
  if (!profile) return json({ error: 'no_profile' }, 400)

  // The client never sends a score at all -- it's derived here, closing the
  // forgery hole by construction rather than by comparing against a
  // client-claimed value.
  const wrongGuesses = won ? Math.max(guessCount - 1, 0) : guessCount
  const score = applyEasyModePenalty(computeScore(unlocksUsed, wrongGuesses, won), easyMode)
  const puzzleId = todayUTC()

  const { error: scoreErr } = await adminClient.from('scores').insert({
    user_id: uid,
    puzzle_id: puzzleId,
    score,
    guesses: guessCount,
    unlocks: unlocksUsed,
    won,
    easy_mode: easyMode,
  })

  if (scoreErr) {
    if (scoreErr.code === '23505') return json({ error: 'already_submitted' }, 409)
    return json({ error: 'server_error' }, 500)
  }

  return json({ ok: true }, 201)
})
