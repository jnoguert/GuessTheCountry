export function generateShareText(guessCount: number, isWon: boolean, puzzleId: string): string {
  const emoji = isWon ? '🟩' : '🟥'
  const result = emoji.repeat(guessCount)
  return `Guess the Country #${puzzleId}\n${result}\n\nhttps://jnoguert.github.io/GuessTheCountry/`
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
