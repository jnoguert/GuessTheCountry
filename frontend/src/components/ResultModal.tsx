import { useState } from 'react'
import { countryToFlag, generateShareText, copyToClipboard } from '../lib/share'
import { Stats } from '../lib/storage'

interface ResultModalProps {
  isOpen: boolean
  isWon: boolean
  answer: {
    name: string
    capital: string
    iso2: string
  } | null
  guessCount: number
  unlocksUsed: number
  score: number
  stats: Stats
  puzzleId: string
  easyMode: boolean
  onClose: () => void
  t: Record<string, any>
}

export function ResultModal({
  isOpen, isWon, answer, guessCount, unlocksUsed, score, stats, puzzleId, easyMode, onClose, t,
}: ResultModalProps) {
  const [copied, setCopied] = useState(false)
  if (!isOpen || !answer) return null

  const handleShare = () => {
    const shareText = generateShareText({
      puzzleId, isWon, guessCount, unlocksUsed, score, streak: stats.currentStreak, easyMode,
    })
    copyToClipboard(shareText).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="card p-8 max-w-sm w-full mx-4 text-center">
        <div className="text-6xl mb-4">{isWon ? '🎉' : '😔'}</div>

        <h2 className="text-3xl font-bold mb-4 text-gray-900 dark:text-white">
          {isWon ? t.you_won : t.you_lost}
        </h2>

        <div className="mb-4">
          <p className="text-gray-600 dark:text-gray-400 mb-2">{t.the_answer_was}</p>
          <div className="text-5xl mb-2">{countryToFlag(answer.iso2)}</div>
          <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">{answer.name}</h3>
          <p className="text-lg text-gray-600 dark:text-gray-400">
            {t.capital}: {answer.capital}
          </p>
        </div>

        <div className="mb-6 grid grid-cols-2 gap-2 text-sm">
          <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{score}</div>
            <div className="text-gray-500 dark:text-gray-400">
              {t.points}{easyMode && <span title={t.easy_mode_active}> 🗺️</span>}
            </div>
          </div>
          <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">🔥 {stats.currentStreak}</div>
            <div className="text-gray-500 dark:text-gray-400">{t.day_streak}</div>
          </div>
          <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">{guessCount}/5</div>
            <div className="text-gray-500 dark:text-gray-400">{t.guesses_used}</div>
          </div>
          <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">💡 {unlocksUsed}/3</div>
            <div className="text-gray-500 dark:text-gray-400">{t.hints_used}</div>
          </div>
        </div>

        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">{t.come_back}</p>

        <div className="flex gap-2">
          <button onClick={handleShare} className="btn-primary flex-1">
            {copied ? t.copied : t.share}
          </button>
          <button onClick={onClose} className="btn-secondary flex-1">
            {t.close}
          </button>
        </div>
      </div>
    </div>
  )
}
