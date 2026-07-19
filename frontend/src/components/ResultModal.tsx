import { countryToFlag, generateShareText, copyToClipboard } from '../lib/share'

interface ResultModalProps {
  isOpen: boolean
  isWon: boolean
  answer: {
    name: string
    capital: string
    iso2: string
  } | null
  guessCount: number
  puzzleId: string
  onNewGame: () => void
  t: Record<string, any>
}

export function ResultModal({ isOpen, isWon, answer, guessCount, puzzleId, onNewGame, t }: ResultModalProps) {
  if (!isOpen || !answer) return null

  const handleShare = () => {
    const shareText = generateShareText(guessCount, isWon, puzzleId)
    copyToClipboard(shareText).then(() => {
      alert('Copied to clipboard!')
    })
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="card p-8 max-w-sm w-full mx-4 text-center">
        <div className="text-6xl mb-4">{isWon ? '🎉' : '😔'}</div>

        <h2 className="text-3xl font-bold mb-4 text-gray-900 dark:text-white">
          {isWon ? t.you_won : t.you_lost}
        </h2>

        <div className="mb-6">
          <p className="text-gray-600 dark:text-gray-400 mb-2">{t.the_answer_was}</p>
          <div className="text-5xl mb-2">{countryToFlag(answer.iso2)}</div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">{answer.name}</h3>
          <p className="text-lg text-gray-600 dark:text-gray-400">
            {t.capital}: {answer.capital}
          </p>
        </div>

        <div className="mb-6 p-4 bg-gray-100 dark:bg-gray-700 rounded-lg">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
            {isWon ? `${t.placements[`guess${guessCount}`]}` : `0/${5} 🟥🟥🟥🟥🟥`}
          </p>
        </div>

        <div className="flex gap-2">
          <button onClick={handleShare} className="btn-secondary flex-1">
            {t.share}
          </button>
          <button onClick={onNewGame} className="btn-primary flex-1">
            {t.new_game}
          </button>
        </div>
      </div>
    </div>
  )
}
