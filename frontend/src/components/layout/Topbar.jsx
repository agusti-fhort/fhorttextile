import { useState, useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import LanguageSwitcher from './LanguageSwitcher'
import { UnitToggle } from '../UnitToggle'
import useAuthStore from '../../store/auth'
import { navGroups } from './navGroups'

// BREADCRUMB DE NAVEGACIÓ (NORMA_LAYOUT §8b): «Tenant › secció › pantalla», el tenant SEMPRE
// primer «així sempre se sap on s'està navegant».
//
// Les rutes surten de `navGroups` (Sidebar), que és l'única llista de navegació de la casa.
// El PATH_TO_KEY que hi havia aquí cobria 11 rutes de les 58 del router: fora d'aquelles onze
// el títol requeia a `t('app.title')` i el resultat era «Fhort Textile Tech › Fhort Textile
// Tech» — que és el que es veu a qualsevol captura d'un model.
//
// Guanya el prefix MÉS ESPECÍFIC, la mateixa regla que el Sidebar fa servir per a l'ítem
// actiu (Sidebar.jsx:~281); si les dues no coincidissin, el molla del breadcrumb i el ressaltat
// del menú es contradirien a la mateixa pantalla.
function trobaMolla(pathname) {
  let millor = null
  for (const grup of navGroups) {
    for (const item of grup.items) {
      const candidats = [item, ...(item.children || [])]
      for (const c of candidats) {
        if (!c.to) continue
        const encaixa = c.to === '/' ? pathname === '/' : (pathname === c.to || pathname.startsWith(c.to + '/'))
        if (encaixa && (!millor || c.to.length > millor.c.to.length)) millor = { c, sectionKey: grup.sectionKey }
      }
    }
  }
  return millor
}

export default function Topbar() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()
  const molla = trobaMolla(pathname)
  // Pas 5B-fix: el botó "Nou model" surt de la barra global; baixarà a la llista de Models (5C).
  const showNewModel = false

  // Bloc nom + data + rellotge (esquerra dels icones). Nom des de l'auth store.
  const user = useAuthStore(s => s.user)
  const nom = user?.nom_complet || user?.username || ''
  // LA CASA, no la persona (P7 · Federació v2): `tenant` és { nom, codi_tenant, tipologia } i
  // és null mentre /me no ha respost. Mentrestant es diu el nom del producte, que és el que
  // deia abans: el breadcrumb no pot quedar-se sense primer element ni parpellejar buit.
  const tenant = useAuthStore(s => s.tenant)
  const nomTenant = tenant?.nom || t('app.title')

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
      {/* Tenant › SECCIÓ › pantalla (decisió Agus 08/08). La secció és la del menú lateral, o
          sigui que el molla i el ressaltat del menú no poden dir coses diferents. Els segments
          intermedis van en tinta suau i el darrer —on ets— en pes 600. El chevron només apareix
          si hi ha element següent: a l'arrel no penja res de ningú.
          El QUART segment (entitat › secció de l'entitat) arriba amb el dashboard del model. */}
      <div style={{display: 'flex', alignItems: 'center', gap: 6, fontSize: 'var(--fs-body)', color: 'var(--text-soft)'}}>
        <span style={{fontWeight: 600, color: 'var(--text-main)'}}>{nomTenant}</span>
        {molla && (
          <>
            <span style={{color: 'var(--text-faint)'}}>›</span>
            <span>{t(molla.sectionKey)}</span>
            <span style={{color: 'var(--text-faint)'}}>›</span>
            <span style={{color: 'var(--text-main)', fontWeight: 600}}>{t(molla.c.labelKey)}</span>
          </>
        )}
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
              color: 'var(--text-main)',
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
