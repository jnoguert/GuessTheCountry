// Client-side game engine: the whole game runs in the browser against the
// static game.json produced by the pipeline. This is what lets the app be
// hosted on GitHub Pages (or any static host) with no backend at all.
//
// The rules deliberately mirror backend/app/puzzle.py: same epoch, same
// skip-to-playable walk, same accent-insensitive matching — so the API
// mode and static mode always agree on the daily country.

export const LANGUAGES = ['en', 'ca', 'es'] as const

export interface CountryI18n {
  name: string
  capital: string
  aliases: string[]
  paragraphs: string[]
  /** Uncensored text, revealed once the game is over */
  plain?: string[]
}

export interface Country {
  iso2: string
  iso3?: string
  i18n: Record<string, CountryI18n>
}

export interface GameData {
  epoch: string
  dailyOrder: string[]
  countries: Record<string, Country>
}

let gameData: GameData | null = null

export async function loadGameData(): Promise<GameData> {
  if (gameData) return gameData
  const res = await fetch(`${import.meta.env.BASE_URL}game.json`)
  if (!res.ok) throw new Error('Failed to load game data')
  gameData = await res.json()
  return gameData!
}

export function normalizeText(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim()
}

export function todayDayIndex(epoch: string): number {
  const epochDate = new Date(epoch + 'T00:00:00Z')
  const now = new Date()
  const todayUtc = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
  return Math.floor((todayUtc - epochDate.getTime()) / 86400000)
}

export function puzzleIdForDay(epoch: string, dayIndex: number): string {
  const epochDate = new Date(epoch + 'T00:00:00Z')
  const d = new Date(epochDate.getTime() + dayIndex * 86400000)
  return d.toISOString().split('T')[0]
}

function hasAllLanguages(country: Country): boolean {
  return LANGUAGES.every((lang) => (country.i18n[lang]?.paragraphs?.length ?? 0) > 0)
}

/** Same country for every player and every language on a given day. */
export function getDailyCountry(data: GameData, dayIndex: number): { qid: string; country: Country } | null {
  const n = data.dailyOrder.length
  if (n === 0) return null
  for (let offset = 0; offset < n; offset++) {
    const qid = data.dailyOrder[(dayIndex + offset) % n]
    const country = data.countries[qid]
    if (country && hasAllLanguages(country)) {
      return { qid, country }
    }
  }
  return null
}

export function checkGuess(country: Country, lang: string, guessText: string): boolean {
  const i18n = country.i18n[lang]
  if (!i18n) return false
  const guess = normalizeText(guessText)
  if (guess === normalizeText(i18n.name)) return true
  return (i18n.aliases ?? []).some((alias) => guess === normalizeText(alias))
}

export function listCountries(data: GameData, lang: string): { name: string; iso2: string }[] {
  return Object.values(data.countries)
    .filter((c) => c.i18n[lang]?.name)
    .map((c) => ({ name: c.i18n[lang].name, iso2: c.iso2 }))
    .sort((a, b) => a.name.localeCompare(b.name, lang))
}
