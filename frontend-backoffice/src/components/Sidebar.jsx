import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import logo from '../assets/logo.svg'

const MONO = "'IBM Plex Mono', monospace"

// Paleta del sidebar (alineada amb el producte: fons blanc, actiu daurat pàl·lid).
const C = {
  bg:        '#ffffff',
  text:      'var(--text-main)',
  textMuted: 'var(--text-muted)',
  icon:      'var(--gold)',
  active:    'var(--gold-pale)',   // #f5e6d0
  activeFg:  'var(--gold)',
  hover:     'var(--bg-muted)',    // #f5f0e8
  border:    'var(--border)',
}

// Logo de marca oficial (SVG vectoritzat "Fhort Textile Tech").
const Logo = () => (
  <img src={logo} alt="FHORT Backoffice" style={{ width: '130px', display: 'block' }} />
)

// Seccions de navegació. "COMPTE" queda reservada (buida) per a futur.
const SECTIONS = [
  {
    title: 'GESTIÓ',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: 'ti-layout-dashboard' },
      { to: '/tenants', label: 'Tenants', icon: 'ti-building-store' },
    ],
  },
  {
    title: 'COMPTE',
    items: [],
  },
]

function NavLeaf({ to, label, icon }) {
  const [hover, setHover] = useState(false)
  return (
    <NavLink
      to={to}
      end
      style={{ textDecoration: 'none' }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      {({ isActive }) => (
        <div
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '0.6rem 1rem', margin: '1px 0.5rem', borderRadius: 8,
            color: isActive ? C.activeFg : C.textMuted,
            background: isActive ? C.active : (hover ? C.hover : 'transparent'),
            fontSize: 12, fontWeight: isActive ? 500 : 400,
            fontFamily: MONO, transition: 'all .15s',
          }}
        >
          <i className={`ti ${icon}`} style={{ fontSize: 17, color: C.icon }} />
          <span style={{ flex: 1 }}>{label}</span>
        </div>
      )}
    </NavLink>
  )
}

function SectionHeader({ title }) {
  return (
    <div style={{
      fontFamily: MONO, fontSize: 10, fontWeight: 600, letterSpacing: '.08em',
      textTransform: 'uppercase', color: C.textMuted, padding: '12px 1.5rem 6px',
    }}>
      {title}
    </div>
  )
}

export default function Sidebar() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const rol = useAuthStore((s) => s.rol)
  const clearAuth = useAuthStore((s) => s.clearAuth)
  const [logoutHover, setLogoutHover] = useState(false)

  const nom = user?.nom_complet || user?.nom || user?.username || user?.email || 'Usuari'
  const rolLabel = (rol || user?.rol || '—').toString().toUpperCase()

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  return (
    <aside style={{
      width: 240,
      background: C.bg,
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      position: 'fixed',
      left: 0,
      top: 0,
      borderRight: `1px solid ${C.border}`,
      overflowY: 'auto',
    }}>
      {/* Capçalera amb logo */}
      <div style={{
        height: 56,
        display: 'flex',
        alignItems: 'center',
        padding: '0 1.2rem',
        borderBottom: `1px solid ${C.border}`,
        flexShrink: 0,
        background: C.bg,
      }}>
        <Logo />
      </div>

      {/* Navegació per seccions */}
      <div style={{ flex: 1, padding: '0.4rem 0' }}>
        {SECTIONS.map((sec) => (
          <div key={sec.title} style={{ marginBottom: 6 }}>
            <SectionHeader title={sec.title} />
            {sec.items.map((item) => (
              <NavLeaf key={item.to} {...item} />
            ))}
          </div>
        ))}
      </div>

      {/* Peu: usuari + tancar sessió */}
      <div style={{ borderTop: `1px solid ${C.border}`, padding: '0.8rem' }}>
        <div style={{ padding: '0 .5rem 8px' }}>
          <div style={{ fontFamily: MONO, fontSize: 12, fontWeight: 600, color: C.text, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {nom}
          </div>
          <div style={{ fontFamily: MONO, fontSize: 10, letterSpacing: '.12em', color: C.textMuted, marginTop: 2 }}>
            {rolLabel}
          </div>
        </div>
        <button
          onClick={handleLogout}
          onMouseEnter={() => setLogoutHover(true)}
          onMouseLeave={() => setLogoutHover(false)}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '0.6rem 1rem', borderRadius: 8,
            color: 'var(--err)',
            background: logoutHover ? C.hover : 'none',
            border: 'none', cursor: 'pointer',
            fontSize: 12, fontFamily: MONO,
            width: '100%', transition: 'background .15s',
          }}
        >
          <i className="ti ti-logout" style={{ fontSize: 17, color: 'var(--err)' }} />
          Tancar sessió
        </button>
      </div>
    </aside>
  )
}
