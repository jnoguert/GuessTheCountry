import { useState, useMemo } from 'react'
import { CountryOption } from '../lib/api'

interface GuessInputProps {
  countries: CountryOption[]
  onSubmit: (guess: string) => void
  disabled: boolean
  isShaking: boolean
  placeholder: string
  submitLabel: string
}

export function GuessInput({ countries, onSubmit, disabled, isShaking, placeholder, submitLabel }: GuessInputProps) {
  const [input, setInput] = useState('')
  const [open, setOpen] = useState(false)

  const filtered = useMemo(() => {
    const query = input.toLowerCase()
    return countries.filter((c) => c.name.toLowerCase().includes(query) || c.iso2.toLowerCase().includes(query)).slice(0, 10)
  }, [input, countries])

  const handleSubmit = (guess: string) => {
    if (guess.trim()) {
      onSubmit(guess)
      setInput('')
      setOpen(false)
    }
  }

  return (
    <div className="mb-6">
      <div className={`relative ${isShaking ? 'shake' : ''}`}>
        <input
          type="text"
          value={input}
          onChange={(e) => {
            setInput(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleSubmit(input)
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          className="input-base mb-2"
        />

        {open && filtered.length > 0 && (
          <div className="absolute top-full left-0 right-0 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg z-10 max-h-48 overflow-y-auto">
            {filtered.map((country) => (
              <button
                key={country.iso2}
                onClick={() => handleSubmit(country.name)}
                className="w-full text-left px-4 py-2 hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-white transition-colors"
              >
                {country.name}
              </button>
            ))}
          </div>
        )}
      </div>

      <button
        onClick={() => handleSubmit(input)}
        disabled={disabled || !input.trim()}
        className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitLabel}
      </button>
    </div>
  )
}
