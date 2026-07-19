import { useState, useEffect } from 'react'
import { fetchPuzzle, fetchCountries, submitGuess, CountryOption } from './lib/api'
import { getGameState, saveGameState, clearGameState, getLanguage, setLanguage, getTheme, setTheme, GameState } from './lib/storage'
import { useI18n } from './hooks/useI18n'
import { LanguageSwitcher } from './components/LanguageSwitcher'
import { ThemeToggle } from './components/ThemeToggle'
import { ParagraphReveal } from './components/ParagraphReveal'
import { GuessInput } from './components/GuessInput'
import { GuessHistory } from './components/GuessHistory'
import { ResultModal } from './components/ResultModal'

const MAX_GUESSES = 5

export default function App() {
  const [lang, setLang] = useState(getLanguage())
  const [theme, setThemeState] = useState(getTheme())
  const [puzzleId, setPuzzleId] = useState('')
  const [paragraphs, setParagraphs] = useState<string[]>([])
  const [countries, setCountries] = useState<CountryOption[]>([])
  const [guesses, setGuesses] = useState<string[]>([])
  const [isWon, setIsWon] = useState(false)
  const [isLost, setIsLost] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isShaking, setIsShaking] = useState(false)
  const [answer, setAnswer] = useState<GameState['answer'] | null>(null)
  const [showResult, setShowResult] = useState(false)

  const t = useI18n(lang)

  useEffect(() => {
    if (isWon || isLost) setShowResult(true)
  }, [isWon, isLost])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  useEffect(() => {
    const loadPuzzle = async () => {
      try {
        setLoading(true)
        setError('')

        // Always fetch today's puzzle: it tells us today's puzzle id
        const puzzleData = await fetchPuzzle(lang)
        setPuzzleId(puzzleData.puzzle_id)

        const savedState = getGameState()
        if (savedState && savedState.puzzleId === puzzleData.puzzle_id && savedState.lang === lang && savedState.paragraphs?.length) {
          // Same day: resume where the player left off
          setParagraphs(savedState.paragraphs)
          setGuesses(savedState.guesses)
          setIsWon(savedState.isWon)
          setIsLost(savedState.isLost)
          setAnswer(savedState.answer ?? null)
        } else {
          // New day (or first visit): start fresh
          clearGameState()
          setParagraphs(puzzleData.paragraphs)
          setGuesses([])
          setIsWon(false)
          setIsLost(false)
          setAnswer(null)
        }

        const countriesData = await fetchCountries(lang)
        setCountries(countriesData)
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error'
        console.error('Failed to load puzzle:', errorMsg)
        setError(t.error)
      } finally {
        setLoading(false)
      }
    }

    loadPuzzle()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang])

  const handleGuess = async (guessText: string) => {
    if (!puzzleId || isWon || isLost) return

    try {
      setIsShaking(false)

      const result = await submitGuess(lang, puzzleId, guesses.length + 1, guessText)
      const newGuesses = [...guesses, guessText]

      if (result.correct) {
        setIsWon(true)
        setGuesses(newGuesses)
        setAnswer(result.answer ?? null)
        saveGameState({
          puzzleId,
          lang,
          guesses: newGuesses,
          paragraphs,
          isWon: true,
          isLost: false,
          answer: result.answer,
        })
        return
      }

      // Wrong guess: reveal the next paragraph if the game continues
      const newParagraphs = result.next_paragraph
        ? [...paragraphs, result.next_paragraph]
        : paragraphs

      setGuesses(newGuesses)
      setParagraphs(newParagraphs)
      setIsShaking(true)

      if (result.game_over) {
        setIsLost(true)
        setAnswer(result.answer ?? null)
      }

      saveGameState({
        puzzleId,
        lang,
        guesses: newGuesses,
        paragraphs: newParagraphs,
        isWon: false,
        isLost: result.game_over,
        answer: result.answer,
      })
    } catch (err) {
      console.error('Failed to submit guess:', err)
      setError(t.error)
    }
  }

  const handleLanguageChange = (newLang: string) => {
    setLang(newLang)
    setLanguage(newLang)
  }

  const handleThemeChange = (newTheme: 'light' | 'dark') => {
    setThemeState(newTheme)
    setTheme(newTheme)
  }

  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'dark bg-gray-900' : 'bg-gradient-to-br from-blue-50 to-indigo-100'}`}>
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-900 dark:text-white">{t.title}</h1>
            <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">{t.subtitle}</p>
          </div>
          <div className="flex gap-3 items-center">
            <ThemeToggle theme={theme} onThemeChange={handleThemeChange} />
            <LanguageSwitcher currentLang={lang} onLangChange={handleLanguageChange} />
          </div>
        </header>

        {error && (
          <div className="card p-4 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 mb-6 rounded-lg">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="text-2xl text-gray-600 dark:text-gray-400">{t.loading}</div>
          </div>
        ) : paragraphs.length > 0 ? (
          <>
            <ParagraphReveal paragraphs={paragraphs} revealedCount={paragraphs.length} />

            {!isWon && !isLost && (
              <>
                <GuessHistory guesses={guesses} maxGuesses={MAX_GUESSES} />
                <GuessInput countries={countries} onSubmit={handleGuess} disabled={isWon || isLost} isShaking={isShaking} />
              </>
            )}

            {(isWon || isLost) && !showResult && answer && (
              <div className="card p-4 flex items-center justify-between">
                <p className="text-gray-900 dark:text-white font-medium">
                  {t.the_answer_was}: <strong>{answer.name}</strong>
                </p>
                <button onClick={() => setShowResult(true)} className="btn-primary">
                  {t.share}
                </button>
              </div>
            )}
          </>
        ) : null}

        <ResultModal
          isOpen={showResult}
          isWon={isWon}
          answer={answer ?? null}
          guessCount={guesses.length}
          puzzleId={puzzleId}
          onClose={() => setShowResult(false)}
          t={t}
        />
      </div>
    </div>
  )
}
