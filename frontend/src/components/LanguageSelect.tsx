const LANG_LABELS: Record<string, string> = {
  en: 'English',
  ca: 'Català',
  es: 'Español',
}

interface LanguageSelectProps {
  onSelect: (lang: string) => void
}

/** First-visit screen: the language is a deliberate choice, because
 * switching later reveals extra clues and costs a hint unlock. */
export function LanguageSelect({ onSelect }: LanguageSelectProps) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="card p-8 max-w-sm w-full mx-4 text-center">
        <div className="text-6xl mb-4">🌍</div>
        <h1 className="text-3xl font-bold mb-2 text-gray-900 dark:text-white">Redactica</h1>
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          Choose your language · Tria el teu idioma · Elige tu idioma
        </p>
        <div className="space-y-3">
          {Object.entries(LANG_LABELS).map(([code, label]) => (
            <button
              key={code}
              onClick={() => onSelect(code)}
              className="btn-primary w-full text-lg py-3"
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export { LANG_LABELS }
