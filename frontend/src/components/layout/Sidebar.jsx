import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../../store/auth'
import client from '../../api/client'
import FhortLogo from '../brand/FhortLogo'

// Paleta del sidebar (locked spec):
const C = {
  bg:        'var(--white)',
  text:      'var(--text-main)',
  textMuted: 'var(--text-muted)',
  icon:      'var(--gold)',
  active:    '#f5e6d0',
  activeFg:  'var(--gold)',
  hover:     '#fdf6ee',
  border:    '#e8e8e8',
}


// Structure: a single main section with 5 top-level items + expandable submenus.
// Dashboard queda visible sempre al top com a accés directe.
// 3 famílies amb capçalera de secció. `cap` = capability requerida (es filtra al component):
//   'plan' (define_tasks/configure) · 'configure' · 'manage_users' · 'onboarding' (<100%).
const navGroups = [
  { sectionKey: 'nav.section_projectes', items: [
    { to: '/', labelKey: 'nav.dashboard', icon: 'ti-layout-dashboard' },
    { to: '/models', labelKey: 'nav.models', icon: 'ti-shirt' },
    { to: '/planificacio', labelKey: 'nav.planning', icon: 'ti-subtask', cap: 'plan' },
    // Jubilades les entrades "El meu calendari" (/planificacio/calendari) i "Temps" (/temps): la
    // planificació de l'executor viu ara al Gantt de la home (tab "Planificació"). Les <Route>
    // segueixen vives (accessibles per URL); només es retira l'entrada de menú.
    { to: '/fittings', labelKey: 'nav.fittings', icon: 'ti-ruler-2' },
  ]},
  { sectionKey: 'nav.section_config_tecnica', items: [
    { to: '/garment-types', labelKey: 'nav.garment_types', icon: 'ti-shirt' },
    { to: '/poms', labelKey: 'nav.poms_list', icon: 'ti-ruler-measure' },
    { to: '/size-library', labelKey: 'nav.size_library', icon: 'ti-books' },
    { to: '/poms/grading', labelKey: 'nav.grading', icon: 'ti-chart-dots' },
  ]},
  // Disseny — documents .ftt (fitxes/maquetació) i patró DXF. Consulta oberta (sense `cap`).
  { sectionKey: 'nav.section_disseny', items: [
    { to: '/disseny/documents', labelKey: 'nav.documents', icon: 'ti-file-text' },
    { to: '/disseny/patro-dxf', labelKey: 'nav.patro_dxf', icon: 'ti-vector' },
  ]},
  // Estudi tècnic — gestió INTERNA del tenant (NO el backoffice futur de tots els tenants).
  // B3-M: Clients i Proveïdors s'han mogut a Comercial (mestres comercials). La secció queda
  // reservada (buida → auto-oculta) per als futurs interns previstos: Configuració de l'Estudi ·
  // Equip/usuaris · Catàleg de serveis/tasques. Les rutes /clients i /suppliers no canvien.
  { sectionKey: 'nav.section_technical_studio', items: [
  ]},
  // Comercial Studio — mestres comercials (Clients, Proveïdors, Productes) + documents (Ofertes).
  // El gate de tier del mòdul arriba a B5; de moment sense `cap` (visible; l'escriptura la
  // gateja CONFIGURE dins la pàgina).
  { sectionKey: 'nav.section_comercial', items: [
    { to: '/clients', labelKey: 'nav.clients', icon: 'ti-users-group' },
    { to: '/suppliers', labelKey: 'nav.suppliers', icon: 'ti-building-factory' },
    { to: '/comercial/productes', labelKey: 'nav.products', icon: 'ti-package' },
    { to: '/comercial/ofertes', labelKey: 'nav.quotes', icon: 'ti-file-invoice' },
    { to: '/comercial/condicions-pagament', labelKey: 'nav.payment_terms', icon: 'ti-calendar-dollar' },
  ]},
  { sectionKey: 'nav.section_sistema', items: [
    { to: '/onboarding', labelKey: 'nav.onboarding', icon: 'ti-rocket', cap: 'onboarding' },
    { to: '/configuracio/calendari', labelKey: 'nav.company_calendar', icon: 'ti-calendar-cog', cap: 'configure' },
    { to: '/configuracio/usuaris', labelKey: 'nav.users', icon: 'ti-users', cap: 'manage_users' },
    // G9 "consulta sí / edició no": catàleg de tasques consultable per a tothom (sense `cap`).
    { to: '/task-types', labelKey: 'nav.tasques_catalog', icon: 'ti-list-details' },
    { to: '/perfil', labelKey: 'nav.perfil', icon: 'ti-user' },
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
          fontSize: 'var(--fs-body)', fontFamily: 'inherit', textAlign: 'left',
          transition: 'background 0.15s',
        }}
      >
        <i className={`ti ${item.icon}`} style={{fontSize: 17, color: C.icon}} />
        <span style={{flex: 1, fontWeight: 500}}>{t(item.labelKey)}</span>
        <i
          className={`ti ${expanded ? 'ti-chevron-down' : 'ti-chevron-right'}`}
          style={{fontSize: 'var(--fs-body)', color: C.textMuted}}
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
        fontSize: 'var(--fs-body)',
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
        fontSize: 'var(--fs-body)', fontWeight: isActive ? 500 : 400,
        transition: 'all 0.15s',
      }}
    >
      <i className={`ti ${item.icon}`} style={{fontSize: 17, color: isActive ? C.activeFg : C.icon}} />
      <span style={{flex: 1}}>{t(item.labelKey)}</span>
      {badge > 0 && (
        <span style={{
          fontSize: 'var(--fs-label)', fontWeight: 600,
          padding: '1px 7px', borderRadius: 10,
          background: 'var(--err)', color: 'var(--white)',
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
  const canExecute = !!user?.capabilities?.includes('execute_tasks')
  const [expanded, setExpanded] = useState({['nav.models']: true})
  const [logoutHover, setLogoutHover] = useState(false)
  const [onboardingPct, setOnboardingPct] = useState(100)
  // Plegat de grups (per sectionKey). Persistit a localStorage; clau absent = obert per defecte.
  const [openGroups, setOpenGroups] = useState(() => {
    try { return JSON.parse(localStorage.getItem('sidebarGroups') || '{}') } catch { return {} }
  })
  const isGroupOpen = (sectionKey) => openGroups[sectionKey] !== false
  const toggleGroup = (sectionKey) => {
    setOpenGroups(prev => {
      const next = { ...prev, [sectionKey]: prev[sectionKey] === false }
      localStorage.setItem('sidebarGroups', JSON.stringify(next))
      return next
    })
  }

  useEffect(() => {
    client.get('/api/v1/onboarding/status/')
      .then(res => {
        const pct = res.data?.percentatge
        if (typeof pct === 'number') setOnboardingPct(pct)
      })
      .catch(() => {})
  }, [])

  const badges = {}
  const toggle = (key) => setExpanded(s => ({...s, [key]: !s[key]}))

  // Filtra cada secció pels gates (cap). Sense `cap` → sempre visible.
  const groups = useMemo(() => {
    const allowed = (it) => {
      switch (it.cap) {
        case 'plan': return canPlan
        case 'execute': return canExecute
        case 'configure': return canConfigure
        case 'manage_users': return canManageUsers
        case 'onboarding': return onboardingPct < 100
        default: return true
      }
    }
    return navGroups
      .map(g => ({ sectionKey: g.sectionKey, items: g.items.filter(allowed) }))
      .filter(g => g.items.length > 0)
  }, [canPlan, canExecute, canConfigure, canManageUsers, onboardingPct])

  const allItems = useMemo(() => groups.flatMap(g => g.items), [groups])

  // Conjunt de totes les rutes del sidebar (leaves + children)
  const allRoutes = useMemo(() => {
    const routes = []
    allItems.forEach(item => {
      if (item.to) routes.push(item.to)
      if (item.children) item.children.forEach(c => routes.push(c.to))
    })
    return routes
  }, [allItems])

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
    allItems.forEach(item => {
      if (!item.children) return
      const hasMatch = item.children.some(c =>
        path === c.to || path.startsWith(c.to + '/')
      )
      if (hasMatch) {
        setExpanded(s => s[item.labelKey] ? s : { ...s, [item.labelKey]: true })
      }
    })
  }, [location.pathname, allItems])

  // Auto-obrir el GRUP que conté la ruta activa (si l'usuari l'havia tancat).
  useEffect(() => {
    groups.forEach(g => {
      const hasActive = g.items.some(item =>
        item.to === activeRoute || item.children?.some(c => c.to === activeRoute))
      if (hasActive && openGroups[g.sectionKey] === false) {
        setOpenGroups(prev => {
          const next = { ...prev, [g.sectionKey]: true }
          localStorage.setItem('sidebarGroups', JSON.stringify(next))
          return next
        })
      }
    })
  }, [activeRoute, groups])  // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <aside style={{
      width: 240,
      background: C.bg,
      height: import.meta.env.VITE_STAGING === 'true' ? 'calc(100vh - 28px)' : '100vh',
      display: 'flex',
      flexDirection: 'column',
      position: 'fixed',
      left: 0,
      top: import.meta.env.VITE_STAGING === 'true' ? '28px' : '0',
      zIndex: 100,            // per sobre de capçaleres sticky de pàgina (Topbar/FittingDetail zIndex:10)
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
        <FhortLogo width={130} />
      </div>
      <div style={{flex: 1, padding: '0.4rem 0'}}>
        {groups.map(g => {
          const open = isGroupOpen(g.sectionKey)
          return (
          <div key={g.sectionKey} style={{ marginBottom: 6 }}>
            <button
              onClick={() => toggleGroup(g.sectionKey)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                width: '100%', background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 'var(--fs-label)', fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase',
                color: C.textMuted, padding: '12px 1.5rem 6px', fontFamily: 'inherit',
                opacity: open ? 1 : 0.7,
              }}
            >
              <span>{t(g.sectionKey)}</span>
              <i className={`ti ${open ? 'ti-chevron-down' : 'ti-chevron-right'}`}
                 style={{ fontSize: 'var(--fs-body)', color: C.textMuted }} />
            </button>
            <div style={{
              overflow: 'hidden',
              maxHeight: open ? '600px' : '0px',
              transition: 'max-height 0.2s ease',
            }}>
              {g.items.map(item => (
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
          </div>
          )
        })}
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
            cursor: 'pointer', fontSize: 'var(--fs-body)',
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
