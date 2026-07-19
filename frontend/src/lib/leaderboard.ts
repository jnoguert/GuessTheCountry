// Leaderboard client. The game itself is fully static, but rankings need
// a server: when the app is served by the FastAPI container (or VITE_API_BASE
// points to a hosted API), the leaderboard lights up; on a pure static host
// (GitHub Pages without an API) it feature-detects the absence and hides.

const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const STORAGE_PREFIX = 'gtc_'

export interface Identity {
  username: string
  token: string
}

export interface TodayEntry {
  username: string
  score: number
  guesses: number
  unlocks: number
  won: number
}

export interface AlltimeEntry {
  username: string
  total_score: number
  wins: number
  games: number
}

let availableCache: boolean | null = null

export async function isLeaderboardAvailable(): Promise<boolean> {
  if (availableCache !== null) return availableCache
  try {
    const res = await fetch(`${API_BASE}/leaderboard/today`, {
      signal: AbortSignal.timeout(4000),
    })
    availableCache = res.ok
  } catch {
    availableCache = false
  }
  return availableCache
}

export function getIdentity(): Identity | null {
  const data = localStorage.getItem(STORAGE_PREFIX + 'identity')
  return data ? JSON.parse(data) : null
}

export function createIdentity(username: string): Identity {
  const identity: Identity = { username, token: crypto.randomUUID() }
  localStorage.setItem(STORAGE_PREFIX + 'identity', JSON.stringify(identity))
  return identity
}

export function clearIdentity(): void {
  localStorage.removeItem(STORAGE_PREFIX + 'identity')
}

export type SubmitResult = 'ok' | 'username_taken' | 'error'

export async function submitScore(
  identity: Identity,
  puzzleId: string,
  score: number,
  guesses: number,
  unlocks: number,
  won: boolean
): Promise<SubmitResult> {
  try {
    const res = await fetch(`${API_BASE}/scores`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: identity.username,
        token: identity.token,
        puzzle_id: puzzleId,
        score, guesses, unlocks, won,
      }),
    })
    if (res.status === 201) return 'ok'
    if (res.status === 409) {
      const detail = (await res.json())?.detail ?? ''
      // Re-submitting the same day is fine; a stolen name is not
      return detail.includes('Username') ? 'username_taken' : 'ok'
    }
    return 'error'
  } catch {
    return 'error'
  }
}

export async function fetchToday(): Promise<TodayEntry[]> {
  const res = await fetch(`${API_BASE}/leaderboard/today`)
  if (!res.ok) throw new Error('Failed to load leaderboard')
  return res.json()
}

export async function fetchAlltime(): Promise<AlltimeEntry[]> {
  const res = await fetch(`${API_BASE}/leaderboard/alltime`)
  if (!res.ok) throw new Error('Failed to load leaderboard')
  return res.json()
}
