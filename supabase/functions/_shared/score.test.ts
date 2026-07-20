// Run with: deno test supabase/functions/_shared/score.test.ts
// Mirrors backend/tests/test_censor_edge_cases.py-style unit coverage for
// the scoring formula -- these cases previously only existed in Python
// (backend/app/scoring.py, now retired) and TypeScript (frontend), tested
// separately in each language. This tests the Edge Function's copy of the
// formula (./score.ts); frontend/src/lib/score.ts is a deliberately separate
// standalone copy with its own tests -- see the comment atop ./score.ts.
import { assertEquals } from 'jsr:@std/assert'
import { computeScore, applyEasyModePenalty, MAX_UNLOCKS, MAX_GUESSES } from './score.ts'

Deno.test('loss always scores 0, regardless of unlocks or wrong guesses', () => {
  assertEquals(computeScore(0, 0, false), 0)
  assertEquals(computeScore(3, 5, false), 0)
})

Deno.test('win with 0 unlocks and 0 wrong guesses scores the max (100)', () => {
  assertEquals(computeScore(0, 0, true), 100)
})

Deno.test('base score decreases with each additional unlock used', () => {
  assertEquals(computeScore(0, 0, true), 100)
  assertEquals(computeScore(1, 0, true), 70)
  assertEquals(computeScore(2, 0, true), 50)
  assertEquals(computeScore(3, 0, true), 30)
})

Deno.test('unlocks beyond MAX_UNLOCKS clamp to the same floor as the max', () => {
  assertEquals(computeScore(MAX_UNLOCKS, 0, true), computeScore(MAX_UNLOCKS + 5, 0, true))
})

Deno.test('each wrong guess costs 10 points', () => {
  assertEquals(computeScore(0, 1, true), 90)
  assertEquals(computeScore(0, 2, true), 80)
})

Deno.test('score never drops below the minimum win score (10) while still won', () => {
  assertEquals(computeScore(3, MAX_GUESSES, true), 10)
})

Deno.test('easy mode halves a winning score, rounded down', () => {
  assertEquals(applyEasyModePenalty(100, true), 50)
  assertEquals(applyEasyModePenalty(70, true), 35)
  assertEquals(applyEasyModePenalty(31, true), 15) // floor(31/2) = 15, not 16
})

Deno.test('easy mode leaves a non-easy-mode score untouched', () => {
  assertEquals(applyEasyModePenalty(100, false), 100)
})

Deno.test('easy mode on a loss (0) stays 0', () => {
  assertEquals(applyEasyModePenalty(computeScore(0, 0, false), true), 0)
})

Deno.test('full pipeline: 2 unlocks, won on the 3rd guess (2 wrong), easy mode', () => {
  // base for 2 unlocks = 50, minus 2*10 = 30, halved (easy mode) -> 15
  const wrongGuesses = 3 - 1 // last guess is the winning one, not "wrong"
  const raw = computeScore(2, wrongGuesses, true)
  assertEquals(raw, 30)
  assertEquals(applyEasyModePenalty(raw, true), 15)
})
