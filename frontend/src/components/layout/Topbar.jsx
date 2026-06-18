import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from './LanguageSwitcher'
import { UnitToggle } from '../UnitToggle'
import useAuthStore from '../../store/auth'

const PATH_TO_KEY = {
  '/':                          'nav.dashboard',
  '/models':                    'nav.models',
  '/models/nou':                'nav.models_new',
  '/models/nou-des-de-fitxer':  'nav.models_from_file',
  '/fittings':                  'nav.fittings',
  '/tasques':                   'nav.tasques',
  '/task-types':                'nav.tasques_catalog',
  '/tasques/kanban':            'nav.kanban',
  '/temps':                     'nav.temps',
  '/fitxers':                   'nav.fitxers',
  '/poms':                      'nav.poms',
  '/poms/grading':              'nav.grading',
  '/ia':                        'nav.ia',
  '/perfil':                    'nav.perfil',
}

export default function Topbar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const key = PATH_TO_KEY[pathname]
  const title = key ? t(key) : t('app.title')
  // Pas 5B-fix: el botó "Nou model" surt de la barra global; baixarà a la llista de Models (5C).
  const showNewModel = false

  // Bloc nom + data + rellotge (esquerra dels icones). Nom des de l'auth store.
  const user = useAuthStore(s => s.user)
  const nom = user?.nom_complet || user?.username || ''

  // Rellotge en viu (patró TimerWidget): tick cada segon, mostra HH:MM. Net al desmuntar.
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  // Locale del i18n → Intl re-formata sol en canviar d'idioma. Data llarga, hora HH:MM.
  const locale = (i18n.resolvedLanguage || i18n.language || 'ca').slice(0, 2)
  const dataRaw = new Intl.DateTimeFormat(locale, {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  }).format(now)
  const data = dataRaw.charAt(0).toUpperCase() + dataRaw.slice(1)   // majúscula inicial (ca/es minúscules)
  const hora = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(now)

  return (
    <header style={{
      height: 56,
      background: 'var(--white)',
      borderBottom: '1px solid #e8e8e8',
      display: 'flex',
      alignItems: 'center',
      padding: '0 1.5rem',
      gap: '1rem',
      position: 'sticky',
      top: import.meta.env.VITE_STAGING === 'true' ? '28px' : '0',
      zIndex: 10,
    }}>
      <div style={{display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', color: 'var(--gray)'}}>
        <i className="ti ti-layout-dashboard" style={{fontSize: 14}} />
        <span>{t('app.title')}</span>
        <i className="ti ti-chevron-right" style={{fontSize: 14}} />
        <strong style={{color: 'var(--charcoal)', fontWeight: 500}}>{title}</strong>
      </div>
      <div style={{marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.8rem'}}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          fontSize: 'var(--fs-body)', color: 'var(--gray)', whiteSpace: 'nowrap',
        }}>
          {nom && <span style={{color: 'var(--charcoal)', fontWeight: 500}}>{nom}</span>}
          {nom && <span style={{opacity: 0.45}}>·</span>}
          <span>{data}</span>
          <span style={{opacity: 0.45}}>·</span>
          <span style={{fontVariantNumeric: 'tabular-nums'}}>{hora}</span>
        </div>
        <UnitToggle />
        <LanguageSwitcher />
        <button
          onClick={() => navigate('/perfil')}
          style={{
            width: 32, height: 32,
            border: '0.5px solid #e4e4e2',
            borderRadius: 8,
            background: 'none',
            cursor: 'pointer',
            color: 'var(--gray)',
            fontSize: 17,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <i className="ti ti-user" />
        </button>
        {showNewModel && (
          <button
            onClick={() => navigate('/models/nou')}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'var(--gold)',
              color: 'white',
              border: 'none',
              borderRadius: 8,
              padding: '0 0.9rem',
              height: 32,
              fontSize: 'var(--fs-body)',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            <i className="ti ti-plus" style={{fontSize: 15}} />
            {t('model.new')}
          </button>
        )}
      </div>
    </header>
  )
}
