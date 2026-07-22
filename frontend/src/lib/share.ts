export interface ShareParams {
  puzzleId: string
  isWon: boolean
  guessCount: number
  unlocksUsed: number
  score: number
  streak: number
  easyMode: boolean
}

export function generateShareText(p: ShareParams): string {
  const outcome = p.isWon ? `✅ ${p.guessCount}/5` : '❌ X/5'
  const hints = `💡 ${p.unlocksUsed}/3`
  const scoreLine = p.isWon ? ` · 🏆 ${p.score} pts${p.easyMode ? ' 🗺️' : ''}` : ''
  const streakLine = p.streak > 0 ? ` · 🔥 ${p.streak}` : ''
  return `Redactica #${p.puzzleId}\n${outcome} · ${hints}${scoreLine}${streakLine}\n\nhttps://jnoguert.github.io/Redactica/`
}

export function copyToClipboard(text: string): Promise<void> {
  return navigator.clipboard.writeText(text)
}

export function countryToFlag(iso2: string): string {
  if (!iso2 || iso2.length !== 2) return '🌍'
  const codePoints = iso2
    .toUpperCase()
    .split('')
    .map((char) => 127397 + char.charCodeAt(0))
  return String.fromCodePoint(...codePoints)
}
