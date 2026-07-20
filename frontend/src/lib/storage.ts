const STORAGE_PREFIX = 'gtc_'

export type MapMarkState = 'neutral' | 'consider' | 'discard'

export interface GameState {
  puzzleId: string
  lang: string
  guesses: string[]
  paragraphs: string[]
  unlocksUsed: number
  isWon: boolean
  isLost: boolean
  score?: number
  answer?: {
    name: string
    capital: string
    iso2: string
  }
  /** Easy Mode is an explicit, per-day opt-in: it lives on GameState so it
   * resets automatically whenever the day (puzzleId) changes, same as
   * guesses/unlocks. Halves the day's score in exchange for the map tool. */
  easyMode?: boolean
  /** Player's own discard/consider notes on the Easy Mode map, keyed by
   * iso2. Purely a scratchpad - never affects guess checking or scoring. */
  mapMarks?: Record<string, MapMarkState>
}

export interface Stats {
  currentStreak: number
  maxStreak: number
  totalPlayed: number
  totalWon: number
  totalScore: number
  lastPlayedId: string | null
  lastWonId: string | null
}

const EMPTY_STATS: Stats = {
  currentStreak: 0,
  maxStreak: 0,
  totalPlayed: 0,
  totalWon: 0,
  totalScore: 0,
  lastPlayedId: null,
  lastWonId: null,
}

export function getGameState(): GameState | null {
  const data = localStorage.getItem(STORAGE_PREFIX + 'game')
  return data ? JSON.parse(data) : null
}

export function saveGameState(state: GameState): void {
  localStorage.setItem(STORAGE_PREFIX + 'game', JSON.stringify(state))
}

export function clearGameState(): void {
  localStorage.removeItem(STORAGE_PREFIX + 'game')
}

/** null until the player explicitly picks a language (first-visit screen). */
export function getLanguage(): string | null {
  return localStorage.getItem(STORAGE_PREFIX + 'lang')
}

export function setLanguage(lang: string): void {
  localStorage.setItem(STORAGE_PREFIX + 'lang', lang)
}

export function getTheme(): 'light' | 'dark' {
  const theme = localStorage.getItem(STORAGE_PREFIX + 'theme')
  if (theme === 'dark' || theme === 'light') return theme
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export function setTheme(theme: 'light' | 'dark'): void {
  localStorage.setItem(STORAGE_PREFIX + 'theme', theme)
}

export function getStats(): Stats {
  const data = localStorage.getItem(STORAGE_PREFIX + 'stats')
  return data ? { ...EMPTY_STATS, ...JSON.parse(data) } : { ...EMPTY_STATS }
}

function saveStats(stats: Stats): void {
  localStorage.setItem(STORAGE_PREFIX + 'stats', JSON.stringify(stats))
}

function previousDay(isoDate: string): string {
  const d = new Date(isoDate + 'T00:00:00Z')
  d.setUTCDate(d.getUTCDate() - 1)
  return d.toISOString().split('T')[0]
}

/** Update play/win counters, score and the day streak. Idempotent per puzzle. */
export function recordGameEnd(puzzleId: string, won: boolean, score: number = 0): Stats {
  const stats = getStats()
  if (stats.lastPlayedId === puzzleId) return stats

  stats.totalPlayed += 1
  stats.lastPlayedId = puzzleId
  stats.totalScore += score

  if (won) {
    stats.totalWon += 1
    // Streak continues only if the previous win was yesterday's puzzle
    stats.currentStreak = stats.lastWonId === previousDay(puzzleId)
      ? stats.currentStreak + 1
      : 1
    stats.maxStreak = Math.max(stats.maxStreak, stats.currentStreak)
    stats.lastWonId = puzzleId
  } else {
    stats.currentStreak = 0
  }

  saveStats(stats)
  return stats
}
