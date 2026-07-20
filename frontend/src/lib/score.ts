// Inverse scoring: the fewer hints you unlock, the more points you earn.
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

/** Easy Mode trade-off: the discard/consider map halves the day's score. */
export function applyEasyModePenalty(score: number, easyMode: boolean): number {
  return easyMode ? Math.floor(score / 2) : score
}
