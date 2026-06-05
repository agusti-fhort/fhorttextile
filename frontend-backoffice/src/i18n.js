import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// Infraestructura i18n del backoffice. De moment només conté els textos del login;
// s'anirà ampliant en sprints posteriors.
export const SUPPORTED_LANGUAGES = ['ca', 'es', 'en']
export const DEFAULT_LANGUAGE = 'ca'

const ca = {
  login: {
    tagline: "Panell d'administració",
    tagline_sub: 'Accés restringit · només personal autoritzat',
    welcome: 'Inicia sessió',
    welcome_sub: 'Introdueix les teves credencials',
    email: 'Correu electrònic',
    email_placeholder: 'nom@empresa.com',
    password: 'Contrasenya',
    remember: "Recorda'm",
    submit: 'ENTRAR',
    loading: 'ENTRANT...',
    or: 'o',
    no_access: 'No tens accés?',
    contact_admin: "Contacta amb l'administrador",
    error_invalid: 'Credencials incorrectes',
    error_generic: 'Error de connexió. Torna-ho a intentar.',
  },
}

const es = {
  login: {
    tagline: 'Panel de administración',
    tagline_sub: 'Acceso restringido · solo personal autorizado',
    welcome: 'Inicia sesión',
    welcome_sub: 'Introduce tus credenciales',
    email: 'Correo electrónico',
    email_placeholder: 'nombre@empresa.com',
    password: 'Contraseña',
    remember: 'Recuérdame',
    submit: 'ENTRAR',
    loading: 'ENTRANDO...',
    or: 'o',
    no_access: '¿No tienes acceso?',
    contact_admin: 'Contacta con el administrador',
    error_invalid: 'Credenciales incorrectas',
    error_generic: 'Error de conexión. Inténtalo de nuevo.',
  },
}

const en = {
  login: {
    tagline: 'Administration panel',
    tagline_sub: 'Restricted access · authorized staff only',
    welcome: 'Sign in',
    welcome_sub: 'Enter your credentials',
    email: 'Email',
    email_placeholder: 'name@company.com',
    password: 'Password',
    remember: 'Remember me',
    submit: 'SIGN IN',
    loading: 'SIGNING IN...',
    or: 'or',
    no_access: 'No access?',
    contact_admin: 'Contact your administrator',
    error_invalid: 'Invalid credentials',
    error_generic: 'Connection error. Please try again.',
  },
}

i18n
  .use(initReactI18next)
  .init({
    resources: {
      ca: { translation: ca },
      es: { translation: es },
      en: { translation: en },
    },
    lng: DEFAULT_LANGUAGE,
    fallbackLng: DEFAULT_LANGUAGE,
    supportedLngs: SUPPORTED_LANGUAGES,
    interpolation: { escapeValue: false },
  })

export default i18n
