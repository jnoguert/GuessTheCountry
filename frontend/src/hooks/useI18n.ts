import { useMemo } from 'react'
import en from '../i18n/en.json'
import ca from '../i18n/ca.json'
import es from '../i18n/es.json'

const translations: Record<string, any> = { en, ca, es }

export function useI18n(lang: string) {
  return useMemo(() => translations[lang] || translations['en'], [lang])
}
