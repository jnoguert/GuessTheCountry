import { useState, useEffect } from 'react'
import { fetchPuzzle, fetchCountries, submitGuess, CountryOption, PuzzleData } from './lib/api'
import { getGameState, saveGameState, clearGameState, getLanguage, setLanguage, getTheme, setTheme } from './lib/storage'
import { useI18n } from './hooks/useI18n'
import { LanguageSwitcher } from './components/LanguageSwitcher'
import { ThemeToggle } from './components/ThemeToggle'
import { ParagraphReveal } from './components/ParagraphReveal'
import { GuessInput } from './components/GuessInput'
import { GuessHistory } from './components/GuessHistory'
import { ResultModal } from './components/ResultModal'

export default function App() {
  const [lang, setLang] = useState(getLanguage())
  const [theme, setThemeState] = useState(getTheme())
  const [puzzle, setPuzzle] = useState<PuzzleData | null>(null)
  const [countries, setCountries] = useState<CountryOption[]>([])
  const [guesses, setGuesses] = useState<string[]>([])
  const [revealedCount, setRevealedCount] = useState(1)
  const [isWon, setIsWon] = useState(false)
  const [isLost, setIsLost] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isShaking, setIsShaking] = useState(false)
  const [answer, setAnswer] = useState<any>(null)

  const t = useI18n(lang)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  useEffect(() => {
    const loadPuzzle = async () => {
      try {
        setLoading(true)
        setError('')

        const savedState = getGameState()
        if (savedState && savedState.puzzleId === new Date().toISOString().split('T')[0]) {
          setPuzzle({
            puzzle_id: savedState.puzzleId,
            max_guesses: 5,
            paragraphs: [],
          })
          setGuesses(savedState.guesses)
          setIsWon(savedState.isWon)
          setIsLost(savedState.isLost)
          setAnswer(savedState.answer)
          setRevealedCount(savedState.guesses.length + 1)
        } else {
          const puzzleData = await fetchPuzzle(lang)
          setPuzzle(puzzleData)
          clearGameState()
          setGuesses([])
          setIsWon(false)
          setIsLost(false)
          setAnswer(null)
          setRevealedCount(1)
        }

        const countriesData = await fetchCountries(lang)
        setCountries(countriesData)
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : 'Unknown error'
        console.error('Failed to load puzzle:', errorMsg)
        setError(`${t.error} (${errorMsg})`)
      } finally {
        setLoading(false)
      }
    }

    loadPuzzle()
  }, [lang, t.error])

  const handleGuess = async (guessText: string) => {
    if (!puzzle || isWon || isLost) return

    try {
      setIsShaking(false)
      await new Promise((resolve) => setTimeout(resolve, 10))

      const result = await submitGuess(lang, puzzle.puzzle_id, guesses.length + 1, guessText)

      if (result.correct) {
        setIsWon(true)
        setAnswer(result.answer)
        saveGameState({
          puzzleId: puzzle.puzzle_id,
          guesses: [...guesses, guessText],
          isWon: true,
          isLost: false,
          answer: result.answer,
        })
      } else {
        const newGuesses = [...guesses, guessText]
        setGuesses(newGuesses)

        if (result.game_over) {
          setIsLost(true)
          setAnswer(result.answer)
          saveGameState({
            puzzleId: puzzle.puzzle_id,
            guesses: newGuesses,
            isWon: false,
            isLost: true,
            answer: result.answer,
          })
        } else if (result.next_paragraph) {
          setRevealedCount((prev) => prev + 1)
          saveGameState({
            puzzleId: puzzle.puzzle_id,
            guesses: newGuesses,
            isWon: false,
            isLost: false,
          })
        }

        setIsShaking(true)
      }
    } catch (err) {
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

  const handleNewGame = () => {
    clearGameState()
    setGuesses([])
    setIsWon(false)
    setIsLost(false)
    setAnswer(null)
    setRevealedCount(1)
    setError('')
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
        ) : puzzle ? (
          <>
            {puzzle.paragraphs.length > 0 && <ParagraphReveal paragraphs={puzzle.paragraphs} revealedCount={revealedCount} />}

            {!isWon && !isLost && (
              <>
                <GuessHistory guesses={guesses} maxGuesses={5} />
                <GuessInput countries={countries} onSubmit={handleGuess} disabled={isWon || isLost} isShaking={isShaking} />
              </>
            )}
          </>
        ) : null}

        <ResultModal isOpen={isWon || isLost} isWon={isWon} answer={answer} guessCount={guesses.length + (isWon ? 1 : 0)} puzzleId={puzzle?.puzzle_id || ''} onNewGame={handleNewGame} t={t} />
      </div>
    </div>
  )
}
