interface InstructionsModalProps {
  isOpen: boolean
  onClose: () => void
  t: Record<string, any>
}

/** "How to Play" reference: explains the daily puzzle, hints, scoring,
 * the language-switch penalty, and what happens after the game ends. */
export function InstructionsModal({ isOpen, onClose, t }: InstructionsModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="card p-6 max-w-lg w-full max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">❓ {t.htp_title}</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-900 dark:hover:text-white text-2xl leading-none"
            aria-label={t.close}
          >
            ×
          </button>
        </div>

        <div className="overflow-y-auto pr-1 space-y-5 text-sm text-gray-700 dark:text-gray-300">
          <p>{t.htp_intro}</p>

          <section>
            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">🎯 {t.htp_goal_title}</h3>
            <p>{t.htp_goal_body}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{t.htp_goal_note}</p>
          </section>

          <section>
            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">💡 {t.htp_guesses_title}</h3>
            <p>{t.htp_guesses_body}</p>
          </section>

          <section>
            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">🏆 {t.htp_scoring_title}</h3>
            <ul className="space-y-1 mb-2">
              <li>{t.htp_score_0}</li>
              <li>{t.htp_score_1}</li>
              <li>{t.htp_score_2}</li>
              <li>{t.htp_score_3}</li>
            </ul>
            <p className="text-xs text-gray-500 dark:text-gray-400">{t.htp_score_penalty}</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">{t.htp_score_loss}</p>
          </section>

          <section>
            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">🗺️ {t.htp_easy_title}</h3>
            <p>{t.htp_easy_body}</p>
          </section>

          <section>
            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">🌐 {t.htp_language_title}</h3>
            <p>{t.htp_language_body}</p>
          </section>

          <section>
            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">📖 {t.htp_after_title}</h3>
            <p>{t.htp_after_body}</p>
          </section>

          <section>
            <h3 className="font-semibold text-gray-900 dark:text-white mb-1">🔥 {t.htp_streak_title}</h3>
            <p>{t.htp_streak_body}</p>
          </section>
        </div>

        <button onClick={onClose} className="btn-primary w-full mt-5">
          {t.htp_got_it}
        </button>
      </div>
    </div>
  )
}
