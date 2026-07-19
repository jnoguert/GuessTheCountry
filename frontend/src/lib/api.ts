// Determine API base URL based on environment
const API_BASE = import.meta.env.VITE_API_BASE
  ? import.meta.env.VITE_API_BASE
  : `${window.location.origin}/api`

export interface PuzzleData {
  puzzle_id: string
  max_guesses: number
  paragraphs: string[]
}

export interface GuessResponse {
  correct: boolean
  game_over: boolean
  next_paragraph?: string
  answer?: {
    name: string
    capital: string
    iso2: string
  }
}

export interface CountryOption {
  name: string
  iso2: string
  aliases?: string[]
}

export async function fetchPuzzle(lang: string): Promise<PuzzleData> {
  const res = await fetch(`${API_BASE}/puzzle/${lang}`)
  if (!res.ok) throw new Error('Failed to fetch puzzle')
  return res.json()
}

export async function submitGuess(
  lang: string,
  puzzleId: string,
  guessNumber: number,
  guessText: string
): Promise<GuessResponse> {
  const res = await fetch(`${API_BASE}/guess`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ lang, puzzle_id: puzzleId, guess_number: guessNumber, guess_text: guessText }),
  })
  if (!res.ok) throw new Error('Failed to submit guess')
  return res.json()
}

export async function fetchCountries(lang: string): Promise<CountryOption[]> {
  const res = await fetch(`${API_BASE}/countries/${lang}`)
  if (!res.ok) throw new Error('Failed to fetch countries')
  return res.json()
}
