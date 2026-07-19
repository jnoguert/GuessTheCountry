interface GuessHistoryProps {
  guesses: string[]
  maxGuesses: number
  label: string
}

export function GuessHistory({ guesses, maxGuesses, label }: GuessHistoryProps) {
  const remaining = maxGuesses - guesses.length

  return (
    <div className="mb-6">
      <div className="mb-3 text-sm text-gray-600 dark:text-gray-400">
        <span className="font-semibold text-lg text-gray-900 dark:text-white">{remaining}</span> {label}
      </div>

      {guesses.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {guesses.map((guess, idx) => (
            <div
              key={idx}
              className="px-3 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 rounded-full text-sm font-medium"
            >
              ✕ {guess}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
