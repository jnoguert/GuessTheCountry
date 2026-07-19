interface LanguageSwitcherProps {
  currentLang: string
  onLangChange: (lang: string) => void
}

export function LanguageSwitcher({ currentLang, onLangChange }: LanguageSwitcherProps) {
  return (
    <div className="flex gap-2">
      {['en', 'ca', 'es'].map((lang) => (
        <button
          key={lang}
          onClick={() => onLangChange(lang)}
          className={`px-3 py-1 rounded-lg font-medium transition-all text-sm ${
            currentLang === lang
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-600'
          }`}
        >
          {lang.toUpperCase()}
        </button>
      ))}
    </div>
  )
}
