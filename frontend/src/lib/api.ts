// Game "API": everything is computed client-side from static game.json
// (see engine.ts), so the app runs on GitHub Pages or any static host.
// The function shapes mirror the old HTTP API so the rest of the app
// doesn't care where answers come from.

import {
  loadGameData, getDailyCountry, checkGuess as engineCheckGuess,
  listCountries, todayDayIndex, puzzleIdForDay,
} from './engine'

export interface PuzzleData {
  puzzle_id: string
  max_guesses: number
  paragraphs: string[]
}

export interface GuessResponse {
  correct: boolean
  game_over: boolean
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
  const data = await loadGameData()
  const dayIndex = todayDayIndex(data.epoch)
  const daily = getDailyCountry(data, dayIndex)
  if (!daily) throw new Error('No puzzle available')

  const paragraphs = daily.country.i18n[lang]?.paragraphs ?? []
  if (!paragraphs.length) throw new Error('No puzzle available in this language')

  return {
    puzzle_id: puzzleIdForDay(data.epoch, dayIndex),
    max_guesses: paragraphs.length,
    paragraphs: [paragraphs[0]],
  }
}

export async function submitGuess(
  lang: string,
  puzzleId: string,
  guessNumber: number,
  guessText: string
): Promise<GuessResponse> {
  const data = await loadGameData()
  const epochMs = new Date(data.epoch + 'T00:00:00Z').getTime()
  const puzzleMs = new Date(puzzleId + 'T00:00:00Z').getTime()
  const dayIndex = Math.round((puzzleMs - epochMs) / 86400000)

  const daily = getDailyCountry(data, dayIndex)
  if (!daily) throw new Error('No puzzle available')

  const i18n = daily.country.i18n[lang]
  const answer = {
    name: i18n?.name ?? '',
    capital: i18n?.capital ?? '',
    iso2: daily.country.iso2,
  }

  if (engineCheckGuess(daily.country, lang, guessText)) {
    return { correct: true, game_over: true, answer }
  }

  // Wrong guess: paragraphs are only revealed via hint unlocks now,
  // so a wrong guess just consumes one of the MAX_GUESSES attempts.
  const gameOver = guessNumber >= 5
  return {
    correct: false,
    game_over: gameOver,
    answer: gameOver ? answer : undefined,
  }
}

export async function fetchCountries(lang: string): Promise<CountryOption[]> {
  const data = await loadGameData()
  return listCountries(data, lang)
}

/** Full uncensored article for the day's country, shown once the game
 * is over so players can read everything about the answer. Falls back
 * to the censored text if the plain version isn't in the dataset. */
export async function fetchFullText(lang: string, puzzleId: string): Promise<string[]> {
  const data = await loadGameData()
  const epochMs = new Date(data.epoch + 'T00:00:00Z').getTime()
  const puzzleMs = new Date(puzzleId + 'T00:00:00Z').getTime()
  const dayIndex = Math.round((puzzleMs - epochMs) / 86400000)

  const daily = getDailyCountry(data, dayIndex)
  if (!daily) return []

  const i18n = daily.country.i18n[lang]
  return (i18n?.plain?.length ? i18n.plain : i18n?.paragraphs) ?? []
}

/** Puzzle state for a given day in a given language: the first
 * `revealedCount` paragraphs plus the answer. Used when the player
 * switches language mid-game (reveal parity in the new language). */
export async function fetchPuzzleState(
  lang: string,
  puzzleId: string,
  revealedCount: number
): Promise<{ paragraphs: string[]; maxGuesses: number; answer: NonNullable<GuessResponse['answer']> }> {
  const data = await loadGameData()
  const epochMs = new Date(data.epoch + 'T00:00:00Z').getTime()
  const puzzleMs = new Date(puzzleId + 'T00:00:00Z').getTime()
  const dayIndex = Math.round((puzzleMs - epochMs) / 86400000)

  const daily = getDailyCountry(data, dayIndex)
  if (!daily) throw new Error('No puzzle available')

  const i18n = daily.country.i18n[lang]
  const paragraphs = i18n?.paragraphs ?? []
  return {
    paragraphs: paragraphs.slice(0, revealedCount),
    maxGuesses: paragraphs.length,
    answer: {
      name: i18n?.name ?? '',
      capital: i18n?.capital ?? '',
      iso2: daily.country.iso2,
    },
  }
}
