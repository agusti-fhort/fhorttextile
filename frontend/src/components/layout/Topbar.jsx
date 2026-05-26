import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from './LanguageSwitcher'

const PATH_TO_KEY = {
  '/':                          'nav.dashboard',
  '/models':                    'nav.models',
  '/models/nou':                'nav.models_new',
  '/models/nou-des-de-fitxer':  'nav.models_from_file',
  '/fitting':                   'nav.fitting',
  '/fittings':                  'nav.fittings',
  '/tasques':                   'nav.tasques',
  '/tasques/catalog':           'nav.tasques_catalog',
  '/tasques/paquets':           'nav.tasques_paquets',
  '/tasques/kanban':            'nav.kanban',
  '/temps':                     'nav.temps',
  '/fitxers':                   'nav.fitxers',
  '/poms':                      'nav.poms',
  '/poms/grading':              'nav.grading',
  '/poms/sizes':                'nav.sizes',
  '/configuracio/garment-types':'nav.garment_types',
  '/avisos':                    'nav.avisos',
  '/ia':                        'nav.ia',
  '/configuracio':              'nav.configuracio',
  '/perfil':                    'nav.perfil',
}

export default function Topbar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const key = PATH_TO_KEY[pathname]
  const title = key ? t(key) : t('app.title')

  return (
    <header style={{
      height: 56,
      background: '#ffffff',
      borderBottom: '1px solid #e8e8e8',
      display: 'flex',
      alignItems: 'center',
      padding: '0 1.5rem',
      gap: '1rem',
      position: 'sticky',
      top: 0,
      zIndex: 10,
    }}>
      <div style={{display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--gray)'}}>
        <i className="ti ti-layout-dashboard" style={{fontSize: 14}} />
        <span>{t('app.title')}</span>
        <i className="ti ti-chevron-right" style={{fontSize: 14}} />
        <strong style={{color: 'var(--charcoal)', fontWeight: 500}}>{title}</strong>
      </div>
      <div style={{marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.8rem'}}>
        <LanguageSwitcher />
        <button
          onClick={() => navigate('/avisos')}
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
          <i className="ti ti-bell" />
        </button>
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
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            fontFamily: 'var(--font)',
          }}
        >
          <i className="ti ti-plus" style={{fontSize: 15}} />
          {t('model.new')}
        </button>
      </div>
    </header>
  )
}
