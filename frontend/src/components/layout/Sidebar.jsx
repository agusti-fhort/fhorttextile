import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../../store/auth'
import { pomAlerts } from '../../api/endpoints'
import client from '../../api/client'

// Paleta del sidebar (locked spec):
const C = {
  bg:        '#ffffff',
  text:      '#1d1d1b',
  textMuted: '#868685',
  icon:      '#c27a2a',
  active:    '#f5e6d0',
  activeFg:  '#c27a2a',
  hover:     '#fdf6ee',
  border:    '#e8e8e8',
}

const Logo = () => (
  <svg viewBox="0 0 222.7 79.76" xmlns="http://www.w3.org/2000/svg" style={{width: 130, height: 'auto'}}>
    {/* "Fhort" — gold */}
    <path fill="#c27a2a" d="M31.22,0H1.07C.48,0,0,.48,0,1.07v38.22c0,.59.48,1.07,1.07,1.07h9.04c.59,0,1.07-.48,1.07-1.07v-12.27c0-.59.48-1.07,1.07-1.07h16.94c.59,0,1.07-.48,1.07-1.07v-7.14c0-.59-.48-1.07-1.07-1.07H12.26c-.59,0-1.07-.48-1.07-1.07v-4.72c0-.59.48-1.07,1.07-1.07h18.96c.59,0,1.07-.48,1.07-1.07V1.07c0-.59-.48-1.07-1.07-1.07Z"/>
    <path fill="#c27a2a" d="M54.21,8.48c-4.38,0-7.24,2.3-9.25,4.85-.03.04-.09.02-.09-.03V1.07c0-.59-.48-1.07-1.07-1.07h-8.81c-.59,0-1.07.48-1.07,1.07v38.22c0,.59.48,1.07,1.07,1.07h8.81c.59,0,1.07-.48,1.07-1.07v-15.82c0-3.46,1.96-5.31,4.61-5.31s4.44,1.85,4.44,5.31v15.82c0,.59.48,1.07,1.07,1.07h8.75c.59,0,1.07-.48,1.07-1.07v-19.34c0-7.09-3.98-11.48-10.61-11.48Z"/>
    <path fill="#c27a2a" d="M83.62,8.48c-9.98,0-17.24,7.44-17.24,16.32v.12c0,8.88,7.21,16.2,17.13,16.2s17.3-7.44,17.3-16.32v-.12c0-8.88-7.21-16.2-17.18-16.2ZM90.19,24.91c0,3.75-2.59,6.92-6.57,6.92s-6.63-3.23-6.63-7.04v-.12c0-3.39,2.02-6.28,5.27-6.87,4.16-.75,7.93,2.62,7.93,6.84v.26Z"/>
    <path fill="#c27a2a" d="M137.24,20.18h6.14c.59,0,1.07-.48,1.07-1.07v-9.39c0-.59-.48-1.07-1.07-1.07h-6.14s-.05-.02-.05-.05V1.07c0-.59-.48-1.07-1.07-1.07h-8.75c-.59,0-1.07.48-1.07,1.07v7.53s-.02.05-.05.05h-2.89c-5.22,0-7.98,2.45-9.77,6.58-.02.05-.1.04-.1-.02v-4.97c0-.59-.48-1.07-1.07-1.07h-8.81c-.59,0-1.07.48-1.07,1.07v29.05c0,.59.48,1.07,1.07,1.07h8.81c.59,0,1.07-.48,1.07-1.07v-8.67c0-7.15,3.23-10.44,8.94-10.44h3.81s.05.02.05.05v10.45c0,7.44,3.86,10.32,10.44,10.32h6.54c.59,0,1.07-.48,1.07-1.07v-8.76c0-.59-.48-1.07-1.07-1.07-1.07,0-1.91-.02-3.08-.02-2.02,0-3-.92-3-3.11v-6.73s.02-.05.05-.05Z"/>
    {/* "Textile Tech" — charcoal */}
    <path fill="#1d1d1b" d="M10.21,51.84H0v-1.27h21.86v1.27h-10.25v27.43h-1.39v-27.43Z"/>
    <path fill="#1d1d1b" d="M20.83,68.94v-.08c0-6.07,4.18-10.74,9.88-10.74,6.23,0,9.47,5.33,9.47,10.87v.45h-17.92c.25,5.62,4.22,9.1,8.86,9.1,3.2,0,5.78-1.68,7.42-3.81l.98.78c-1.89,2.46-4.67,4.26-8.45,4.26-5.58,0-10.25-4.22-10.25-10.83ZM38.75,68.24c-.2-4.51-2.95-8.9-8.12-8.9-4.68,0-8.12,3.81-8.37,8.9h16.48Z"/>
    <path fill="#1d1d1b" d="M52.44,67.87l7.75-9.27h1.56l-8.49,10.13,8.82,10.54h-1.64l-8.04-9.64-8.04,9.64h-1.56l8.82-10.5-8.49-10.17h1.64l7.67,9.27Z"/>
    <path fill="#1d1d1b" d="M68.55,73.98v-14.19h-3.16v-1.19h3.16v-6.93h1.31v6.93h7.5v1.19h-7.5v14.07c0,3.03,1.6,4.55,4.3,4.55,1.03,0,2.05-.25,3.12-.74v1.27c-1.03.49-2.09.7-3.24.7-3.32,0-5.49-1.93-5.49-5.66Z"/>
    <path fill="#1d1d1b" d="M83.22,50.4h1.77v2.5h-1.77v-2.5ZM83.43,58.6h1.35v20.67h-1.35v-20.67Z"/>
    <path fill="#1d1d1b" d="M92.9,49.34h1.35v29.94h-1.35v-29.94Z"/>
    <path fill="#1d1d1b" d="M100.69,68.94v-.08c0-6.07,4.18-10.74,9.88-10.74,6.23,0,9.47,5.33,9.47,10.87v.45h-17.92c.25,5.62,4.22,9.1,8.86,9.1,3.2,0,5.78-1.68,7.42-3.81l.98.78c-1.89,2.46-4.68,4.26-8.45,4.26-5.58,0-10.25-4.22-10.25-10.83ZM118.61,68.24c-.2-4.51-2.95-8.9-8.12-8.9-4.68,0-8.12,3.81-8.37,8.9h16.48Z"/>
    <path fill="#1d1d1b" d="M145.78,51.84h-10.21v-1.27h21.86v1.27h-10.25v27.43h-1.39v-27.43Z"/>
    <path fill="#1d1d1b" d="M156.4,68.94v-.08c0-6.07,4.18-10.74,9.88-10.74,6.23,0,9.47,5.33,9.47,10.87v.45h-17.92c.25,5.62,4.22,9.1,8.86,9.1,3.2,0,5.78-1.68,7.42-3.81l.98.78c-1.89,2.46-4.68,4.26-8.45,4.26-5.58,0-10.25-4.22-10.25-10.83ZM174.32,68.24c-.2-4.51-2.95-8.9-8.12-8.9-4.68,0-8.12,3.81-8.37,8.9h16.48Z"/>
    <path fill="#1d1d1b" d="M180.3,68.98v-.08c0-5.82,4.59-10.79,10.58-10.79,3.81,0,6.23,1.72,8.24,3.81l-.94.94c-1.8-1.93-4.06-3.53-7.34-3.53-5.21,0-9.15,4.31-9.15,9.52v.08c0,5.21,4.06,9.6,9.23,9.6,3.28,0,5.62-1.68,7.42-3.69l.94.82c-2.01,2.34-4.59,4.1-8.45,4.1-5.95,0-10.54-4.92-10.54-10.79Z"/>
    <path fill="#1d1d1b" d="M204.9,49.34h1.31v14.19c.94-2.46,3.53-5.41,7.96-5.41,5.45,0,8.53,3.69,8.53,9.06v12.1h-1.31v-11.89c0-4.8-2.58-8.04-7.38-8.04-4.35,0-7.79,3.57-7.79,8.28v11.65h-1.31v-29.94Z"/>
  </svg>
)

// Structure: a single main section with 5 top-level items + expandable submenus.
// Dashboard i Avisos queden visibles sempre al top com a accessos directes.
const navGroups = [
  { items: [
    { to: '/', labelKey: 'nav.dashboard', icon: 'ti-layout-dashboard' },
    { to: '/avisos', labelKey: 'nav.avisos', icon: 'ti-alert-triangle', badgeKey: 'alerts' },
    { to: '/models', labelKey: 'nav.models', icon: 'ti-shirt' },
    { labelKey: 'nav.poms', icon: 'ti-ruler-measure', children: [
      { to: '/size-library',  labelKey: 'nav.size_library' },
      { to: '/poms',          labelKey: 'nav.poms_list' },
      { to: '/poms/sizes',    labelKey: 'nav.sizes' },
      { to: '/poms/grading',  labelKey: 'nav.grading' },
    ]},
    { labelKey: 'nav.tasques', icon: 'ti-checklist', children: [
      { to: '/tasques',         labelKey: 'nav.tasques_list' },
      { to: '/tasques/catalog', labelKey: 'nav.tasques_catalog' },
      { to: '/tasques/paquets', labelKey: 'nav.tasques_paquets' },
      { to: '/tasques/kanban',  labelKey: 'nav.kanban' },
      { to: '/planificacio/calendari', labelKey: 'nav.planning_calendar' },
      { to: '/temps',           labelKey: 'nav.temps' },
    ]},
    { labelKey: 'nav.fittings', icon: 'ti-ruler-2', children: [
      { to: '/fitting',  labelKey: 'nav.fitting_list' },
      { to: '/fittings', labelKey: 'nav.fittings_sessions' },
    ]},
    { labelKey: 'nav.configuracio', icon: 'ti-settings', children: [
      { to: '/configuracio/garment-types', labelKey: 'nav.garment_types' },
      { to: '/garment-pom-map',            labelKey: 'nav.garment_pom_map' },
      { to: '/configuracio',               labelKey: 'nav.configuracio_general' },
      { to: '/perfil',                     labelKey: 'nav.perfil' },
    ]},
  ]},
]

function NavParent({ item, t, expanded, onToggle, activeRoute }) {
  const [hover, setHover] = useState(false)
  return (
    <div>
      <button
        onClick={onToggle}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        style={{
          display: 'flex', alignItems: 'center', gap: 10, width: 'calc(100% - 1rem)',
          padding: '0.55rem 1rem', margin: '1px 0.5rem',
          border: 'none',
          background: hover ? C.hover : 'transparent',
          cursor: 'pointer',
          borderRadius: 8, color: C.text,
          fontSize: 12, fontFamily: 'inherit', textAlign: 'left',
          transition: 'background 0.15s',
        }}
      >
        <i className={`ti ${item.icon}`} style={{fontSize: 17, color: C.icon}} />
        <span style={{flex: 1, fontWeight: 500}}>{t(item.labelKey)}</span>
        <i
          className={`ti ${expanded ? 'ti-chevron-down' : 'ti-chevron-right'}`}
          style={{fontSize: 13, color: C.textMuted}}
        />
      </button>
      {expanded && (
        <div style={{marginLeft: '1.7rem'}}>
          {item.children.map(child => (
            <NavChild
              key={child.to}
              child={child}
              t={t}
              isActive={activeRoute === child.to}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function NavChild({ child, t, isActive }) {
  const [hover, setHover] = useState(false)
  return (
    <NavLink
      to={child.to}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'block',
        padding: '0.45rem 1rem',
        margin: '1px 0.5rem',
        borderRadius: 6,
        color: isActive ? C.activeFg : C.text,
        background: isActive ? C.active : (hover ? C.hover : 'none'),
        textDecoration: 'none',
        fontSize: 11.5,
        fontWeight: isActive ? 500 : 400,
        transition: 'all 0.15s',
      }}
    >
      {t(child.labelKey)}
    </NavLink>
  )
}

function NavLeaf({ item, badges, t, isActive }) {
  const [hover, setHover] = useState(false)
  const badge = item.badgeKey ? badges[item.badgeKey] : null
  return (
    <NavLink
      to={item.to}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '0.6rem 1rem', margin: '1px 0.5rem',
        borderRadius: 8,
        color: isActive ? C.activeFg : C.text,
        background: isActive ? C.active : (hover ? C.hover : 'none'),
        textDecoration: 'none',
        fontSize: 12, fontWeight: isActive ? 500 : 400,
        transition: 'all 0.15s',
      }}
    >
      <i className={`ti ${item.icon}`} style={{fontSize: 17, color: isActive ? C.activeFg : C.icon}} />
      <span style={{flex: 1}}>{t(item.labelKey)}</span>
      {badge > 0 && (
        <span style={{
          fontSize: 10, fontWeight: 600,
          padding: '1px 7px', borderRadius: 10,
          background: 'var(--err)', color: '#ffffff',
          fontVariantNumeric: 'tabular-nums',
        }}>{badge}</span>
      )}
    </NavLink>
  )
}

function NavItem({ item, badges, t, expanded, onToggle, activeRoute }) {
  if (item.children) {
    return (
      <NavParent
        item={item} t={t}
        expanded={expanded} onToggle={onToggle}
        activeRoute={activeRoute}
      />
    )
  }
  return <NavLeaf item={item} badges={badges} t={t} isActive={activeRoute === item.to} />
}

export default function Sidebar() {
  const { t } = useTranslation()
  const location = useLocation()
  const logout = useAuthStore(s => s.logout)
  const user = useAuthStore(s => s.user)
  const canManageUsers = !!user?.capabilities?.includes('manage_users')
  const canConfigure = !!user?.capabilities?.includes('configure')
  const canPlan = !!user?.capabilities?.some(c => c === 'define_tasks' || c === 'configure')
  const [alertsPending, setAlertsPending] = useState(0)
  const [expanded, setExpanded] = useState({['nav.models']: true})
  const [logoutHover, setLogoutHover] = useState(false)
  const [onboardingPct, setOnboardingPct] = useState(100)

  useEffect(() => {
    pomAlerts.list({ estat: 'Pendent', page_size: 1 })
      .then(res => setAlertsPending(res.data.count || 0))
      .catch(() => {})
    client.get('/api/v1/onboarding/status/')
      .then(res => {
        const pct = res.data?.percentatge
        if (typeof pct === 'number') setOnboardingPct(pct)
      })
      .catch(() => {})
  }, [])

  const badges = { alerts: alertsPending }
  const toggle = (key) => setExpanded(s => ({...s, [key]: !s[key]}))

  // Injeccions condicionals dins de Configuració: "Configuració inicial" (onboarding < 100%)
  // i "Usuaris i rols" (només si l'usuari té manage_users).
  const items = useMemo(() => navGroups[0].items.map(item => {
    // Tasques: injectar "Planificació" (assignació de models a tècnics) si es té define_tasks/configure.
    if (item.labelKey === 'nav.tasques') {
      if (!canPlan) return item
      return { ...item, children: [...item.children, { to: '/planificacio', labelKey: 'nav.planning' }] }
    }
    if (item.labelKey !== 'nav.configuracio') return item
    let children = item.children
    if (onboardingPct < 100) {
      children = [{ to: '/onboarding', labelKey: 'nav.onboarding' }, ...children]
    }
    if (canManageUsers) {
      children = [...children, { to: '/configuracio/usuaris', labelKey: 'nav.users' }]
    }
    if (canConfigure) {
      children = [...children, { to: '/configuracio/calendari', labelKey: 'nav.company_calendar' }]
    }
    return children === item.children ? item : { ...item, children }
  }), [onboardingPct, canManageUsers, canConfigure, canPlan])

  // Conjunt de totes les rutes del sidebar (leaves + children)
  const allRoutes = useMemo(() => {
    const routes = []
    items.forEach(item => {
      if (item.to) routes.push(item.to)
      if (item.children) item.children.forEach(c => routes.push(c.to))
    })
    return routes
  }, [items])

  // Exact match or, failing that, the most specific prefix (longest match wins).
  // '/' only counts as an exact match to avoid matching every route.
  const activeRoute = useMemo(() => {
    const path = location.pathname
    const matches = allRoutes.filter(r => {
      if (r === '/') return path === '/'
      return path === r || path.startsWith(r + '/')
    })
    matches.sort((a, b) => b.length - a.length)
    return matches[0] || null
  }, [allRoutes, location.pathname])

  // Auto-expand: if the current route is (or is a subroute of) any child of a
  // group, we expand the group. startsWith() is used ONLY here, not for the highlight
  // of child items (which follows the most-specific-match logic).
  useEffect(() => {
    const path = location.pathname
    items.forEach(item => {
      if (!item.children) return
      const hasMatch = item.children.some(c =>
        path === c.to || path.startsWith(c.to + '/')
      )
      if (hasMatch) {
        setExpanded(s => s[item.labelKey] ? s : { ...s, [item.labelKey]: true })
      }
    })
  }, [location.pathname, items])

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
      <div style={{flex: 1, padding: '0.8rem 0'}}>
        {items.map(item => (
          <NavItem
            key={item.to || item.labelKey}
            item={item}
            badges={badges}
            t={t}
            expanded={!!expanded[item.labelKey]}
            onToggle={() => toggle(item.labelKey)}
            activeRoute={activeRoute}
          />
        ))}
      </div>
      <div style={{
        borderTop: `1px solid ${C.border}`,
        padding: '0.8rem',
      }}>
        <button
          onClick={logout}
          onMouseEnter={() => setLogoutHover(true)}
          onMouseLeave={() => setLogoutHover(false)}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '0.6rem 1rem', borderRadius: 8,
            color: C.text,
            background: logoutHover ? C.hover : 'none',
            border: 'none',
            cursor: 'pointer', fontSize: 12,
            width: '100%', fontFamily: 'inherit',
            transition: 'background 0.15s',
          }}
        >
          <i className="ti ti-logout" style={{fontSize: 17, color: C.icon}} />
          {t('nav.logout')}
        </button>
      </div>
    </aside>
  )
}
