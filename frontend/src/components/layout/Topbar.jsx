import { useLocation } from 'react-router-dom'

const breadcrumbs = {
  '/': 'Dashboard',
  '/models': 'Models',
  '/fitting': 'Size & Fitting',
  '/fittings': 'Fittings',
  '/tasques': 'Tasques',
  '/temps': 'Temps',
  '/fitxers': 'Fitxers',
  '/poms': 'POMs & Grading',
  '/ia': 'IA',
  '/configuracio': 'Configuració',
}

export default function Topbar() {
  const { pathname } = useLocation()
  const title = breadcrumbs[pathname] || 'Fhort Textile Tech'

  return (
    <header style={{
      height: 56,
      background: 'var(--white)',
      borderBottom: '0.5px solid var(--gray-m, #e4e4e2)',
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
        <span>Fhort Textile Tech</span>
        <i className="ti ti-chevron-right" style={{fontSize: 14}} />
        <strong style={{color: 'var(--charcoal)', fontWeight: 500}}>{title}</strong>
      </div>
      <div style={{marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '0.8rem'}}>
        <button style={{
          width: 32, height: 32,
          border: '0.5px solid #e4e4e2',
          borderRadius: 8,
          background: 'none',
          cursor: 'pointer',
          color: 'var(--gray)',
          fontSize: 17,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <i className="ti ti-bell" />
        </button>
        <button style={{
          width: 32, height: 32,
          border: '0.5px solid #e4e4e2',
          borderRadius: 8,
          background: 'none',
          cursor: 'pointer',
          color: 'var(--gray)',
          fontSize: 17,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <i className="ti ti-search" />
        </button>
        <button style={{
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
        }}>
          <i className="ti ti-plus" style={{fontSize: 15}} />
          Nou model
        </button>
      </div>
    </header>
  )
}
