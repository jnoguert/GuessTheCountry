// Scoring formula for the leaderboard Edge Function. This is a deliberate
// manual duplicate of frontend/src/lib/score.ts, NOT a shared import -- the
// frontend keeps its own standalone copy (Deno can't import across into the
// Vite bundle without a build step, and a cross-directory re-export was
// tried and reverted). If you change one, change the other; the Deno unit
// tests here and the frontend's own tests both assert the same cases so a
// drift between them should show up as a test mismatch, not silently.
export const MAX_UNLOCKS = 3
export const MAX_GUESSES = 5

const UNLOCK_SCORES = [100, 70, 50, 30] // indexed by unlocks used
const WRONG_GUESS_PENALTY = 10
const MIN_WIN_SCORE = 10

export function computeScore(unlocksUsed: number, wrongGuesses: number, won: boolean): number {
  if (!won) return 0
  const base = UNLOCK_SCORES[Math.min(unlocksUsed, MAX_UNLOCKS)]
  return Math.max(MIN_WIN_SCORE, base - wrongGuesses * WRONG_GUESS_PENALTY)
}

export function applyEasyModePenalty(score: number, easyMode: boolean): number {
  return easyMode ? Math.floor(score / 2) : score
}
