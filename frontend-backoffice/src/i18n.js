import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// Infraestructura i18n mínima per al backoffice. Els recursos de traducció
// s'aniran omplint en sprints posteriors; de moment només establim l'idioma base.
export const DEFAULT_LANGUAGE = 'ca'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      ca: { translation: {} },
      es: { translation: {} },
      en: { translation: {} },
    },
    lng: DEFAULT_LANGUAGE,
    fallbackLng: DEFAULT_LANGUAGE,
    interpolation: { escapeValue: false },
  })

export default i18n
