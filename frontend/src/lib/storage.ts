const STORAGE_PREFIX = 'gtc_'

export interface GameState {
  puzzleId: string
  guesses: string[]
  isWon: boolean
  isLost: boolean
  answer?: {
    name: string
    capital: string
    iso2: string
  }
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

export function getLanguage(): string {
  return localStorage.getItem(STORAGE_PREFIX + 'lang') || 'en'
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
