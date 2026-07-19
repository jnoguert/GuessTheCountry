"""Server-side mirror of frontend/src/lib/score.ts — submitted scores
must match what the game rules can actually produce."""

MAX_UNLOCKS = 3
MAX_GUESSES = 5

UNLOCK_SCORES = [100, 70, 50, 30]  # indexed by unlocks used
WRONG_GUESS_PENALTY = 10
MIN_WIN_SCORE = 10


def compute_score(unlocks_used: int, wrong_guesses: int, won: bool) -> int:
    if not won:
        return 0
    base = UNLOCK_SCORES[min(unlocks_used, MAX_UNLOCKS)]
    return max(MIN_WIN_SCORE, base - wrong_guesses * WRONG_GUESS_PENALTY)
