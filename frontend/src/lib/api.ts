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
  const paragraphs = i18n?.paragraphs ?? []
  const answer = {
    name: i18n?.name ?? '',
    capital: i18n?.capital ?? '',
    iso2: daily.country.iso2,
  }

  if (engineCheckGuess(daily.country, lang, guessText)) {
    return { correct: true, game_over: true, answer }
  }

  const nextParaIdx = guessNumber
  const gameOver = nextParaIdx >= paragraphs.length
  return {
    correct: false,
    game_over: gameOver,
    next_paragraph: gameOver ? undefined : paragraphs[nextParaIdx],
    answer: gameOver ? answer : undefined,
  }
}

export async function fetchCountries(lang: string): Promise<CountryOption[]> {
  const data = await loadGameData()
  return listCountries(data, lang)
}
