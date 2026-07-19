interface LanguageWarningModalProps {
  isOpen: boolean
  targetLangLabel: string
  canSwitch: boolean
  onConfirm: () => void
  onCancel: () => void
  t: Record<string, any>
}

/** Switching language mid-game shows the same clues written differently,
 * so it costs one hint unlock — the player confirms or stays. */
export function LanguageWarningModal({ isOpen, targetLangLabel, canSwitch, onConfirm, onCancel, t }: LanguageWarningModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="card p-6 max-w-sm w-full mx-4 text-center">
        <div className="text-5xl mb-3">⚠️</div>
        <h2 className="text-xl font-bold mb-2 text-gray-900 dark:text-white">
          {t.switch_lang_title}
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          {canSwitch
            ? t.switch_lang_body.replace('{lang}', targetLangLabel)
            : t.switch_lang_blocked}
        </p>
        <div className="flex gap-2">
          {canSwitch && (
            <button onClick={onConfirm} className="btn-primary flex-1">
              {t.switch_lang_confirm}
            </button>
          )}
          <button onClick={onCancel} className="btn-secondary flex-1">
            {t.switch_lang_cancel}
          </button>
        </div>
      </div>
    </div>
  )
}
