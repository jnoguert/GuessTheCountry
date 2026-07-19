import { MAX_UNLOCKS } from '../lib/score'

interface HintPanelProps {
  unlocksUsed: number
  onUnlock: () => void
  disabled: boolean
  t: Record<string, any>
}

/** Voluntary hint unlocks: each reveals one more censored paragraph.
 * Fewer unlocks -> higher score. */
export function HintPanel({ unlocksUsed, onUnlock, disabled, t }: HintPanelProps) {
  const remaining = MAX_UNLOCKS - unlocksUsed

  return (
    <div className="card p-4 mb-6 flex items-center justify-between gap-3">
      <div>
        <p className="text-sm font-medium text-gray-900 dark:text-white">
          💡 {t.hints_remaining}: {'●'.repeat(remaining)}{'○'.repeat(unlocksUsed)}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">{t.hints_cost_note}</p>
      </div>
      <button
        onClick={onUnlock}
        disabled={disabled || remaining === 0}
        className="btn-secondary whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {t.unlock_hint}
      </button>
    </div>
  )
}
