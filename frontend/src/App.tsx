import { useState, useEffect, useMemo } from 'react'
import { fetchPuzzle, fetchCountries, submitGuess, fetchPuzzleState, CountryOption } from './lib/api'
import { normalizeText } from './lib/engine'
import {
  getGameState, saveGameState, clearGameState, getLanguage, setLanguage,
  getTheme, setTheme, getStats, recordGameEnd, GameState, Stats,
} from './lib/storage'
import { computeScore, MAX_GUESSES, MAX_UNLOCKS } from './lib/score'
import { useI18n } from './hooks/useI18n'
import { LanguageSwitcher } from './components/LanguageSwitcher'
import { LanguageSelect, LANG_LABELS } from './components/LanguageSelect'
import { LanguageWarningModal } from './components/LanguageWarningModal'
import { ThemeToggle } from './components/ThemeToggle'
import { ParagraphReveal } from './components/ParagraphReveal'
import { GuessInput } from './components/GuessInput'
import { GuessHistory } from './components/GuessHistory'
import { HintPanel } from './components/HintPanel'
import { ResultModal } from './components/ResultModal'

export default function App() {
  const [lang, setLang] = useState<string | null>(getLanguage())
  const [theme, setThemeState] = useState(getTheme())
  const [puzzleId, setPuzzleId] = useState('')
  const [paragraphs, setParagraphs] = useState<string[]>([])
  const [countries, setCountries] = useState<CountryOption[]>([])
  const [guesses, setGuesses] = useState<string[]>([])
  const [unlocksUsed, setUnlocksUsed] = useState(0)
  const [isWon, setIsWon] = useState(false)
  const [isLost, setIsLost] = useState(false)
  const [score, setScore] = useState(0)
  const [stats, setStats] = useState<Stats>(getStats())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [isShaking, setIsShaking] = useState(false)
  const [answer, setAnswer] = useState<GameState['answer'] | null>(null)
  const [showResult, setShowResult] = useState(false)
  const [pendingLang, setPendingLang] = useState<string | null>(null)

  const t = useI18n(lang ?? 'en')
  const gameOver = isWon || isLost

  // Countries already tried disappear from the autocomplete list
  const availableCountries = useMemo(() => {
    const tried = new Set(guesses.map((g) => normalizeText(g)))
    return countries.filter((c) => !tried.has(normalizeText(c.name)))
  }, [countries, guesses])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  useEffect(() => {
    if (isWon || isLost) setShowResult(true)
  }, [isWon, isLost])

  useEffect(() => {
    if (!lang) return

    const loadPuzzle = async () => {
      try {
        setLoading(true)
        setError('')

        const puzzleData = await fetchPuzzle(lang)
        setPuzzleId(puzzleData.puzzle_id)

        const saved = getGameState()
        if (saved && saved.puzzleId === puzzleData.puzzle_id && saved.lang === lang && saved.paragraphs?.length) {
          // Same day, same language: resume
          setParagraphs(saved.paragraphs)
          setGuesses(saved.guesses)
          setUnlocksUsed(saved.unlocksUsed ?? 0)
          setIsWon(saved.isWon)
          setIsLost(saved.isLost)
          setScore(saved.score ?? 0)
          setAnswer(saved.answer ?? null)
        } else if (saved && saved.puzzleId === puzzleData.puzzle_id && (saved.isWon || saved.isLost)) {
          // Finished game viewed in another language: keep the result,
          // translate the visible content (free once the game is over)
          const state = await fetchPuzzleState(lang, puzzleData.puzzle_id, saved.paragraphs.length)
          setParagraphs(state.paragraphs)
          setGuesses(saved.guesses)
          setUnlocksUsed(saved.unlocksUsed ?? 0)
          setIsWon(saved.isWon)
          setIsLost(saved.isLost)
          setScore(saved.score ?? 0)
          setAnswer(state.answer)
        } else {
          // New day: start fresh
          clearGameState()
          setParagraphs(puzzleData.paragraphs)
          setGuesses([])
          setUnlocksUsed(0)
          setIsWon(false)
          setIsLost(false)
          setScore(0)
          setAnswer(null)
          setShowResult(false)
        }

        const countriesData = await fetchCountries(lang)
        setCountries(countriesData)
      } catch (err) {
        console.error('Failed to load puzzle:', err)
        setError(t.error)
      } finally {
        setLoading(false)
      }
    }

    loadPuzzle()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang])

  const persist = (partial: Partial<GameState>) => {
    if (!lang) return
    saveGameState({
      puzzleId, lang, guesses, paragraphs, unlocksUsed,
      isWon, isLost, score,
      answer: answer ?? undefined,
      ...partial,
    })
  }

  const handleGuess = async (guessText: string) => {
    if (!lang || !puzzleId || gameOver) return

    // Repeating an already-tried country must not waste an attempt
    if (guesses.some((g) => normalizeText(g) === normalizeText(guessText))) {
      setIsShaking(false)
      await new Promise((r) => setTimeout(r, 10))
      setIsShaking(true)
      return
    }

    try {
      setIsShaking(false)
      const result = await submitGuess(lang, puzzleId, guesses.length + 1, guessText)
      const newGuesses = [...guesses, guessText]
      setGuesses(newGuesses)

      if (result.correct) {
        const wonScore = computeScore(unlocksUsed, newGuesses.length - 1, true)
        setIsWon(true)
        setScore(wonScore)
        setAnswer(result.answer ?? null)
        setStats(recordGameEnd(puzzleId, true, wonScore))
        persist({ guesses: newGuesses, isWon: true, score: wonScore, answer: result.answer })
        return
      }

      setIsShaking(true)
      if (result.game_over) {
        setIsLost(true)
        setAnswer(result.answer ?? null)
        setStats(recordGameEnd(puzzleId, false, 0))
        persist({ guesses: newGuesses, isLost: true, score: 0, answer: result.answer })
      } else {
        persist({ guesses: newGuesses })
      }
    } catch (err) {
      console.error('Failed to submit guess:', err)
      setError(t.error)
    }
  }

  const handleUnlock = async () => {
    if (!lang || gameOver || unlocksUsed >= MAX_UNLOCKS) return
    try {
      const newUnlocks = unlocksUsed + 1
      const state = await fetchPuzzleState(lang, puzzleId, paragraphs.length + 1)
      setParagraphs(state.paragraphs)
      setUnlocksUsed(newUnlocks)
      persist({ paragraphs: state.paragraphs, unlocksUsed: newUnlocks })
    } catch (err) {
      console.error('Failed to unlock hint:', err)
    }
  }

  const handleLangRequest = (newLang: string) => {
    if (!lang || newLang === lang) return
    if (gameOver || guesses.length + unlocksUsed === 0 && paragraphs.length === 0) {
      // Free switch when nothing has been seen or the game is over
      setLanguage(newLang)
      setLang(newLang)
      return
    }
    setPendingLang(newLang)
  }

  const confirmLangSwitch = async () => {
    if (!lang || !pendingLang || unlocksUsed >= MAX_UNLOCKS) return
    try {
      const newUnlocks = unlocksUsed + 1
      // Reveal parity in the new language; the unlock is the switch cost
      const state = await fetchPuzzleState(pendingLang, puzzleId, paragraphs.length)
      setParagraphs(state.paragraphs)
      setUnlocksUsed(newUnlocks)
      setLanguage(pendingLang)
      setLang(pendingLang)
      saveGameState({
        puzzleId, lang: pendingLang, guesses, paragraphs: state.paragraphs,
        unlocksUsed: newUnlocks, isWon, isLost, score,
        answer: answer ?? undefined,
      })
    } catch (err) {
      console.error('Failed to switch language:', err)
    } finally {
      setPendingLang(null)
    }
  }

  const handleThemeChange = (newTheme: 'light' | 'dark') => {
    setThemeState(newTheme)
    setTheme(newTheme)
  }

  if (!lang) {
    return <LanguageSelect onSelect={(l) => { setLanguage(l); setLang(l) }} />
  }

  return (
    <div className={`min-h-screen ${theme === 'dark' ? 'dark bg-gray-900' : 'bg-gradient-to-br from-blue-50 to-indigo-100'}`}>
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <header className="flex justify-between items-center mb-8 gap-3">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white">{t.title}</h1>
            <p className="text-gray-600 dark:text-gray-400 text-sm mt-1">{t.subtitle}</p>
          </div>
          <div className="flex gap-2 items-center shrink-0">
            {stats.currentStreak > 0 && (
              <span className="text-sm font-semibold text-gray-900 dark:text-white" title={t.day_streak}>
                🔥 {stats.currentStreak}
              </span>
            )}
            <ThemeToggle theme={theme} onThemeChange={handleThemeChange} />
            <LanguageSwitcher currentLang={lang} onLangChange={handleLangRequest} />
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

            {!gameOver && (
              <>
                <HintPanel unlocksUsed={unlocksUsed} onUnlock={handleUnlock} disabled={gameOver} t={t} />
                <GuessHistory guesses={guesses} maxGuesses={MAX_GUESSES} label={t.guesses_remaining} />
                <GuessInput
                  countries={availableCountries}
                  onSubmit={handleGuess}
                  disabled={gameOver}
                  isShaking={isShaking}
                  placeholder={t.guess_placeholder}
                  submitLabel={t.submit}
                />
              </>
            )}

            {gameOver && !showResult && answer && (
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

        <LanguageWarningModal
          isOpen={pendingLang !== null}
          targetLangLabel={pendingLang ? LANG_LABELS[pendingLang] : ''}
          canSwitch={unlocksUsed < MAX_UNLOCKS}
          onConfirm={confirmLangSwitch}
          onCancel={() => setPendingLang(null)}
          t={t}
        />

        <ResultModal
          isOpen={showResult}
          isWon={isWon}
          answer={answer ?? null}
          guessCount={guesses.length}
          unlocksUsed={unlocksUsed}
          score={score}
          stats={stats}
          puzzleId={puzzleId}
          onClose={() => setShowResult(false)}
          t={t}
        />
      </div>
    </div>
  )
}
