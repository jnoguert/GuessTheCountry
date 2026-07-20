interface EasyModeWarningModalProps {
  isOpen: boolean
  onConfirm: () => void
  onCancel: () => void
  t: Record<string, any>
}

/** Easy Mode halves the day's score, so turning it on requires an explicit
 * choice — the player confirms switching to Easy Mode or stays in Hard Mode. */
export function EasyModeWarningModal({ isOpen, onConfirm, onCancel, t }: EasyModeWarningModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="card p-6 max-w-sm w-full mx-4 text-center">
        <div className="text-5xl mb-3">🗺️</div>
        <h2 className="text-xl font-bold mb-2 text-gray-900 dark:text-white">
          {t.easy_mode_title}
        </h2>
        <p className="text-gray-600 dark:text-gray-400 mb-6">{t.easy_mode_body}</p>
        <div className="flex gap-2">
          <button onClick={onConfirm} className="btn-primary flex-1">
            {t.easy_mode_confirm}
          </button>
          <button onClick={onCancel} className="btn-secondary flex-1">
            {t.easy_mode_cancel}
          </button>
        </div>
      </div>
    </div>
  )
}
