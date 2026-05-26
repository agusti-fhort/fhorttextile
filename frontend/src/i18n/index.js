import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import LanguageDetector from 'i18next-browser-languagedetector'

import ca from './ca.json'
import es from './es.json'
import en from './en.json'

export const SUPPORTED_LANGUAGES = ['ca', 'es', 'en']
export const DEFAULT_LANGUAGE = 'ca'

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      ca: { translation: ca },
      es: { translation: es },
      en: { translation: en },
    },
    fallbackLng: DEFAULT_LANGUAGE,
    supportedLngs: SUPPORTED_LANGUAGES,
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'fhort.lang',
      caches: ['localStorage'],
    },
  })

export default i18n
