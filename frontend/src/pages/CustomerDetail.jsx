import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import {
  customers, customerAliases, commerce, poms, gradingRuleSets, sizingProfiles,
} from '../api/endpoints'
import CustomerForm, { initCustomerForm, customerPayload, customerFormInvalid } from '../components/CustomerForm'
import { SelfBadge } from './Customers'
import DictionaryWizard from '../components/DictionaryWizard'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Badge from '../components/ui/Badge'
import PageMenu from '../components/ui/PageMenu'
import TaulaLlista from '../components/ui/TaulaLlista'
import { BotoEsborrar, EstatBuit, camp, buit, forceBarra } from '../components/llista/ChromLlista'
import { StatusBadge } from './Quotes'
import { OrderStatusBadge } from './Orders'
import { DNStatusBadge } from './DeliveryNotes'
import { botoPri, botoSec, botoDestructiu, apagat } from '../components/ui/buttons'

const money = (v) => `${Number(v ?? 0).toFixed(2)} €`
const dayOf = (r) => (r.issued_at || r.created_at || '').slice(0, 10)

// Fitxa completa del client (patró ModelSheet: capçalera + barra de tabs ?tab= + cos).
// 3 tabs: Dades (identitat + fiscal, reusa CustomerForm de M2) · Tècnic (biblioteca de
// nomenclatura: CustomerPOMAlias CRUD + graduacions/perfils del client, lectura) · Comercial
// (ofertes/comandes del client). L'edició d'àlies està gated CONFIGURE al backend.
const MONO = 'IBM Plex Mono, monospace'
const TABS = ['dades', 'tecnic', 'comercial']
// Els QUATRE choices d'origen del model (pom/models.py:243-246). Han d'estar tots aquí i tots
// als tres i18n (clients.origen_*): la clau es construeix per interpolació (`origen_${r.origen}`)
// i, si falta, i18next pinta la clau crua a la cel·la (QA-S8 · D4c).
const ORIGEN_VARIANT = { IMPORT: 'gold', MANUAL: 'ok', MIGRACIO: 'gray', DICCIONARI: 'gate' }

export default function CustomerDetail() {
  const { id } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')
  // Amunt de qualsevol return: els dos returns primerencs de sota (loading · error) fan que
  // el primer render en registri MENYS que el segon si aquest hook queda a sota — React #310.
  const isStudio = useAuthStore(st => st.tenant?.tipologia === 'estudi')

  const [sp, setSp] = useSearchParams()
  const tabParam = sp.get('tab')
  const setTab = (tab) => setSp({ tab })

  const [customer, setCustomer] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)
  // EL GOVERN DEL CLIENT VIU A LA SEVA FITXA (§8e · §5.6). La llista de Clients tenia, a cada
  // fila, quatre botons de text: obrir · pujar logo · activar/desactivar · esborrar. La graella
  // canònica no en dona cap columna —només la paperera— i la §5.6 reserva el menú d'accions als
  // gestos OCASIONALS. «Pujar el logo» i «desactivar» ho són, i totes dues parlen d'UN client:
  // el seu lloc és aquí, on la pantalla parla d'una entitat, i no a la llista, on en parla de
  // moltes. Entren en aquest tram i no en el següent a posta: així la llista no perd cap
  // capacitat en cap moment intermedi.
  const [saving, setSaving] = useState(false)
  const logoRef = useRef(null)
  const API = import.meta.env.VITE_API_URL || ''

  const load = useCallback(() => {
    setError(false)
    return customers.get(id).then(res => setCustomer(res.data)).catch(() => setError(true))
  }, [id])

  // El logo del client no passa per `customers.update`: té endpoint propi multipart. `fetch` i
  // no el client d'API perquè el cos és un `FormData` i el `Content-Type` l'ha de posar el
  // navegador amb el `boundary` (mateix codi que tenia la llista).
  const pujaLogo = (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !customer) return
    setSaving(true); setFeedback(null)
    const fd = new FormData(); fd.append('logo', file)
    fetch(`${API}/api/v1/customers/${customer.id}/upload-logo/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      body: fd,
    })
      .then(r => { if (!r.ok) throw new Error('upload'); return r.json() })
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('clients.logo_uploaded') }))
      .catch(() => setFeedback({ type: 'err', text: t('clients.error') }))
      .finally(() => setSaving(false))
  }

  // Activar/desactivar. El client propi (is_self) no s'ofereix: el tenant es quedaria sense
  // casa. Amagar-ho és cortesia — qui blinda de debò és el backend (409 `self_customer_protected`).
  const commutaActiu = () => {
    setSaving(true); setFeedback(null)
    customers.update(customer.id, { active: !customer.active })
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('clients.saved') }))
      .catch(() => setFeedback({ type: 'err', text: t('clients.error') }))
      .finally(() => setSaving(false))
  }

  useEffect(() => {
    let alive = true
    customers.get(id)
      .then(res => { if (alive) setCustomer(res.data) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [id])

  if (loading) return <Center>{t('clients.loading')}</Center>
  if (error || !customer) return <Center>{t('clients.error')}</Center>

  // El client propi del tenant (is_self) no es ven res a si mateix: el tab Comercial no hi té
  // sentit i queda fora. `activeTab` es resol contra els tabs VISIBLES, de manera que entrar per
  // l'URL directa (?tab=comercial) tampoc hi cau — es queda a Dades.
  const tabs = customer.is_self ? TABS.filter(x => x !== 'comercial') : TABS
  const activeTab = tabs.includes(tabParam) ? tabParam : 'dades'

  return (
    <>
      {/* §8b.2 · MENÚ DE PANTALLA — la barra blanca de costat a costat, amb el ← SEMPRE PRIMER i
          amb destí EXPLÍCIT. Els tres tabs del client són SECCIONS D'UNA ENTITAT (§8b-bis: «un
          sol tipus de menú de pantalla a tot el producte») i per tant són PÍNDOLES d'aquesta
          barra, no una segona banda de navegació a sota.

          El que se'n va: una banda pròpia amb l'activa en DAURAT PLE sobre `--bg-muted`. Era el
          defecte exacte que A6 va haver de corregir al dashboard del model —dos patrons de
          navegació al mateix nivell, i el daurat fent d'estat de navegació quan és marca. */}
      <div style={forceBarra}>
        <PageMenu
          backTo="/clients"
          backTitle={t('clients.back_to_list')}
          items={tabs.map(tab => ({
            key: tab, label: t(`clients.tab_${tab}`), active: activeTab === tab,
            onClick: () => setTab(tab),
          }))}
        />
      </div>

      {/* §8b.3 · IDENTITAT — SOBRE EL FONS DE PÀGINA, SENSE CONTENIDOR (és informativa, no un
          panell): codi en CAPTION a dalt + nom a 22/500 + badges + accions a la dreta.
          El codi deixa d'anar en daurat pes 700 dins de l'h1: el daurat és marca, no una dada,
          i un codi no és el títol de la pàgina — el nom sí. */}
      <div style={{ padding: '16px 0 12px' }}>
        <div style={{ fontSize: 'var(--fs-caption)', letterSpacing: '.08em', textTransform: 'uppercase',
          color: 'var(--text-soft)', fontFamily: MONO, fontWeight: 600, marginBottom: 4 }}>
          {customer.codi}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500,
            fontFamily: MONO, color: 'var(--text-main)', margin: 0 }}>
            {customer.nom}
          </h1>
          <Badge variant={customer.active ? 'ok' : 'gray'}>
            {customer.active ? t('clients.active') : t('clients.inactive')}
          </Badge>
          {/* La fitxa del client propi no es distingia de cap altra: hi entraves i no sabies que
              estaves mirant casa teva. Mateix badge que a la llista (definició única). */}
          {customer.is_self && <SelfBadge t={t} />}

          {/* §8b.3 · les accions de la identitat van A LA DRETA. Cap de les dues és blava: el
              blau és «el que has vingut a fer» (§5.1) i a la fitxa d'un client això és DESAR les
              dades, que ja porta el seu botó al tab. Pujar un logo i desactivar són gestos de la
              casa: secundari amb vora daurada, i la de desactivar amb VORA vermella i mai plena
              (§5.5 — el vermell ple només al botó que confirma dins d'un modal). */}
          {canEdit && (
            <span style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
              <input ref={logoRef} type="file" accept="image/*" hidden onChange={pujaLogo} />
              <button type="button" onClick={() => logoRef.current?.click()} disabled={saving}
                style={{ ...botoSec, ...(saving ? apagat : null) }}>
                <i className="ti ti-photo" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
                {customer.logo ? t('clients.logo_replace') : t('clients.logo_upload')}
              </button>
              {!customer.is_self && (
                <button type="button" onClick={commutaActiu} disabled={saving}
                  style={{ ...(customer.active ? botoDestructiu : botoSec), ...(saving ? apagat : null) }}>
                  {customer.active ? t('clients.deactivate') : t('clients.activate')}
                </button>
              )}
            </span>
          )}
        </div>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      <div style={{ maxWidth: 820 }}>
        {activeTab === 'dades' && (
          <>
            <DadesTab customer={customer} canEdit={canEdit} t={t}
              onSaved={(msg) => load().then(() => setFeedback({ type: 'ok', text: msg }))}
              onError={(text) => setFeedback({ type: 'err', text })} />
            {/* P8 — la connexió amb el tenant del client. Només en un ESTUDI: qui enganxa el
                token és qui rep encàrrecs. En una Marca aquesta secció no vol dir res (és ella
                qui l'emet, des de Recursos), i el client propi no es connecta a si mateix. */}
            {isStudio && !customer.is_self && (
              <ConnexioTenant customer={customer} canEdit={canEdit} t={t}
                onSaved={(msg) => load().then(() => setFeedback({ type: 'ok', text: msg }))}
                onError={(text) => setFeedback({ type: 'err', text })} />
            )}
          </>
        )}
        {activeTab === 'tecnic' && (
          <TecnicTab customer={customer} canEdit={canEdit} t={t} navigate={navigate}
            notify={setFeedback} />
        )}
        {activeTab === 'comercial' && (
          <ComercialTab customer={customer} t={t} navigate={navigate} />
        )}
      </div>
    </>
  )
}

// ── Tab DADES — reusa el formulari de M2 (identitat + fiscal), editable ─────────────
function DadesTab({ customer, canEdit, t, onSaved, onError }) {
  const [form, setForm] = useState(() => initCustomerForm(customer))
  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }))
  const [terms, setTerms] = useState([])
  const [saving, setSaving] = useState(false)
  const invalid = customerFormInvalid(form)

  useEffect(() => {
    commerce.paymentTerms.list({ active: true })
      .then(res => setTerms(res.data?.results ?? (Array.isArray(res.data) ? res.data : [])))
      .catch(() => setTerms([]))
  }, [])

  const submit = () => {
    if (invalid) { onError(t('clients.required')); return }
    setSaving(true)
    customers.update(customer.id, customerPayload(form))
      .then(() => onSaved(t('clients.saved')))
      .catch(e => onError(e?.response?.data?.detail || t('clients.error')))
      .finally(() => setSaving(false))
  }

  return (
    <div>
      <SectionTitle t={t} title="clients.dades_section" subtitle="clients.dades_section_help" />
      <CustomerForm form={form} set={set} terms={terms} t={t} section="all" />
      {/* §5.1 · L'ACCIÓ PRIMÀRIA del tab Dades, i l'única: desar la fitxa és el que has vingut
          a fer aquí. Les del §8b.3 (logo, desactivar) són gestos de la casa i no li competeixen. */}
      {canEdit && (
        <button type="button" onClick={submit} disabled={saving || invalid}
          style={{ ...botoPri, marginTop: 8, ...(saving || invalid ? apagat : null) }}>
          <i className="ti ti-device-floppy" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
          {t('clients.save')}
        </button>
      )}
    </div>
  )
}

// ── Tab TÈCNIC — biblioteca de nomenclatura (àlies CRUD) + graduacions/perfils ──────
function TecnicTab({ customer, canEdit, t, navigate, notify }) {
  const [aliases, setAliases] = useState([])
  const [rulesets, setRulesets] = useState([])
  const [profiles, setProfiles] = useState([])
  const [busy, setBusy] = useState(true)
  const [showDict, setShowDict] = useState(false)

  // La biblioteca ha de mostrar TOTA la nomenclatura del client, no la primera pàgina: la llista
  // ve paginada (PAGE_SIZE=25, max_page_size=200) i el client 7 en té 95 -> se'n pintaven 25
  // (QA-S8 · D5). Recorrem les pàgines fins que `next` s'esgota.
  const fetchAllAliases = useCallback(async () => {
    const out = []
    for (let page = 1; ; page += 1) {
      const res = await customerAliases.list({ customer: customer.id, page, page_size: 200 })
      const d = res.data
      out.push(...(d?.results ?? (Array.isArray(d) ? d : [])))
      if (!d?.next) return out
    }
  }, [customer.id])

  const loadAliases = useCallback(() => fetchAllAliases().then(setAliases), [fetchAllAliases])

  useEffect(() => {
    let alive = true
    Promise.all([
      fetchAllAliases(),
      gradingRuleSets.list({ customer: customer.id }),
      sizingProfiles.list({ customer_codi: customer.codi }),
    ]).then(([a, g, p]) => {
      if (!alive) return
      setAliases(a)
      setRulesets(g.data?.results ?? (Array.isArray(g.data) ? g.data : []))
      const prows = p.data?.results ?? (Array.isArray(p.data) ? p.data : [])
      setProfiles(prows.filter(r => r.customer_codi === customer.codi))
    }).finally(() => { if (alive) setBusy(false) })
    return () => { alive = false }
  }, [customer.id, customer.codi, fetchAllAliases])

  const removeAlias = (a) => {
    if (!window.confirm(t('clients.alias_confirm_delete', { code: a.client_code }))) return
    customerAliases.remove(a.id)
      .then(() => loadAliases())
      .then(() => notify({ type: 'ok', text: t('clients.alias_deleted') }))
      .catch(() => notify({ type: 'err', text: t('clients.error') }))
  }

  // Mapa un àlies pendent (pom=null) al POM canònic que el tècnic tria a la mateixa fila.
  const mapAlias = (a, pm) => {
    customerAliases.update(a.id, { pom: pm.id, pendent_revisio: false })
      .then(() => loadAliases())
      .then(() => notify({ type: 'ok', text: t('clients.alias_mapped', { code: a.client_code, pom: pm.codi_client }) }))
      .catch(() => notify({ type: 'err', text: t('clients.error') }))
  }

  // Descripció LLEGAT: `client_description` és el camp obsolet (models.py:255-258) i només
  // s'usa de reserva per als àlies antics. Mai si duplica el codi: la migració 0031 hi va
  // copiar el codi del client, i pintar-ho seria repetir la columna del costat.
  const legacyDesc = (r) => {
    const cd = (r.client_description || '').trim()
    return cd.toLowerCase() === (r.client_code || '').trim().toLowerCase() ? '' : cd
  }

  // ⚠️ DESVIACIÓ DECLARADA DE LA §8e, i el motiu. La graella canònica imposa UNA LÍNIA per fila
  // amb ellipsis, i aquí tres columnes en porten DUES. No és un salt de línia (que és el que la
  // norma prohibeix, perquè trenca la fila): és una PILA de dos camps diferents —descripció EN +
  // descripció local amb el seu codi d'idioma, i codi global de POM + abreviatura/nom—. Aplanar-
  // les a una línia no comprimiria res: faria desaparèixer dades que aquesta pantalla existeix
  // per ensenyar. Les tres columnes ho declaren amb `whiteSpace: 'normal'`; la resta de la
  // graella (capçaleres, filets, hover, amplades per contingut) és la canònica.
  const pila = { whiteSpace: 'normal' }

  const aliasCols = [
    { key: 'client_code', label: t('clients.alias_code'), min: 100, max: 130,
      estil: { fontWeight: 600 }, titol: r => r.client_code,
      render: r => r.client_code },
    // Descripció: EN a dalt (canònica), local a sota amb el codi d'idioma (mateixa convenció que
    // el pas 2 del wizard, DictionaryWizard.jsx:177-182). Els escriu el diccionari; abans la
    // columna llegia el camp obsolet i sortia '—' per a TOTS els àlies del wizard (QA-S8 · D4b).
    { key: 'description_en', label: t('clients.alias_desc'), min: 200, max: 320, estil: pila, render: r => {
      const en = r.description_en || legacyDesc(r)
      const local = r.description_local
      if (!en && !local) return <span style={{ color: 'var(--text-soft)' }}>—</span>
      return (
        <div style={{ lineHeight: 1.2 }}>
          {en && <div>{en}</div>}
          {local && (
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>
              {r.language && <span style={{ fontFamily: MONO, marginRight: 4 }}>[{r.language}]</span>}{local}
            </div>
          )}
        </div>
      )
    } },
    // POM canònic: codi global (POM-XXX) com a element principal; a sota, abreviatura + nom EN.
    // Fallback per a POMs tenant-only (sense pom_global): el codi_client fa d'identificador i
    // no repetim l'abreviatura si coincideix amb el principal.
    // Sense POM (pom=null): és vocabulari del client PENDENT DE MAPAR (QA-S8-R1) — es pot mapar
    // des de la mateixa fila amb el cercador de POM.
    { key: 'pom', label: t('clients.alias_pom'), min: 160, max: 240, estil: pila, render: r => {
      if (!r.pom) {
        return canEdit
          ? <PomPicker t={t} onPick={pm => mapAlias(r, pm)} label={t('clients.alias_pendent_map')} />
          : <Badge variant="warn">{t('clients.alias_pendent_map')}</Badge>
      }
      const primary = r.pom_code_global || r.pom_codi
      const abbr = r.pom_abbreviation && r.pom_abbreviation !== primary ? r.pom_abbreviation : null
      const nomEn = r.pom_nom_en || r.pom_nom
      const secondary = [abbr, nomEn].filter(Boolean).join(' · ')
      return (
        <div style={{ lineHeight: 1.2 }}>
          <div style={{ fontFamily: MONO, fontWeight: 600, color: 'var(--gold)' }}>{primary}</div>
          {secondary && <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)' }}>{secondary}</div>}
        </div>
      )
    } },
    // Origen com a badge; sota, la data. TODO: CustomerPOMAlias no té camp autor (només dates);
    // el diccionari futur pot afegir-lo.
    { key: 'origen', label: t('clients.alias_origen'), min: 110, max: 140, estil: pila, render: r => (
      <div style={{ lineHeight: 1.3 }}>
        <Badge variant={ORIGEN_VARIANT[r.origen] || 'gray'}>{t(`clients.origen_${r.origen}`)}</Badge>
        {r.creat_at && <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', marginTop: 3 }}>{r.creat_at.slice(0, 10)}</div>}
      </div>
    ) },
    // §8e · la paperera de fila de la casa: 26×26, icona 14, VORA només al hover i mai vermella
    // plena en repòs (§5.5). Abans portava la vora d'error sempre encesa a cada fila.
    ...(canEdit ? [{ key: '_a', amplada: 36, render: r => (
      <BotoEsborrar onClick={() => removeAlias(r)} title={t('clients.delete')} />
    ) }] : []),
  ]

  const nPoms = new Set(aliases.map(a => a.pom)).size

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      {/* Biblioteca d'àlies */}
      <section>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
          <SectionTitle t={t} title="clients.biblioteca_title" subtitle="clients.biblioteca_subtitle"
            meta={t('clients.biblioteca_count', { aliases: aliases.length, poms: nPoms })} />
          {/* PORTA, no primària (§5.3): «Carregar diccionari» obre un assistent a part i no
              completa cap feina d'aquesta pantalla. El blau del tab Tècnic és l'«Afegir àlies»
              de la fila d'alta, que és el gest que sí que hi acaba una feina. */}
          {canEdit && (
            <button type="button" onClick={() => setShowDict(true)} style={botoSec}>
              <i className="ti ti-file-spreadsheet" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
              {t('clients.load_dictionary')}
            </button>
          )}
        </div>
        {canEdit && <AliasAddRow customer={customer} t={t}
          onCreated={() => loadAliases().then(() => notify({ type: 'ok', text: t('clients.alias_saved') }))}
          onError={(text) => notify({ type: 'err', text })} />}
        {busy ? <EstatBuit>{t('clients.loading')}</EstatBuit>
          : aliases.length === 0 ? <EstatBuit>{t('clients.alias_empty')}</EstatBuit>
            : <TaulaLlista cols={aliasCols} files={aliases} clau={(a) => a.id} />}
      </section>

      {showDict && (
        <DictionaryWizard customer={customer} t={t}
          onClose={() => setShowDict(false)}
          onDone={(res) => {
            setShowDict(false)
            loadAliases().then(() => notify({ type: 'ok', text: t('clients.dictionary_saved', {
              linked: res.linked, created: res.created_pom, skipped: res.skipped }) }))
          }} />
      )}

      {/* Graduacions del client (lectura, enllaç a Grading Rules / Size Library) */}
      <section>
        <SectionTitle t={t} title="clients.grading_title" count={rulesets.length} />
        {rulesets.length === 0 ? (
          <EmptyContext t={t} help="clients.grading_empty_help"
            actions={[['clients.open_grading', '/poms/grading'], ['clients.open_size_library', '/size-library']]}
            navigate={navigate} />
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {rulesets.map(rs => (
              <li key={rs.id} style={rowCard} onClick={() => navigate('/poms/grading')} role="button" tabIndex={0}>
                <span style={{ fontFamily: MONO }}>{rs.nom}</span>
                <span style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-body)' }}>
                  {rs.size_system_nom || rs.size_system_codi} · {rs.regles_count} {t('clients.rules')}
                  <i className="ti ti-external-link" style={{ fontSize: 13, marginLeft: 8 }} />
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Perfils de talles del client (lectura) */}
      <section>
        <SectionTitle t={t} title="clients.profiles_title" count={profiles.length} />
        {profiles.length === 0 ? (
          <EmptyContext t={t} help="clients.profiles_empty_help"
            actions={[['clients.open_size_library', '/size-library']]} navigate={navigate} />
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {profiles.map(p => (
              <li key={p.id} style={{ ...rowCard, cursor: 'default' }}>
                <span style={{ fontFamily: MONO }}>{p.size_system?.nom || p.size_system?.codi}</span>
                <span style={{ color: 'var(--text-soft)', fontSize: 'var(--fs-body)' }}>
                  {p.target?.nom_en} · {p.fit_type_nom}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

// Cercador de POM del catàleg. Únic per a tot el tab tècnic: el fan servir l'alta d'àlies
// (AliasAddRow) i el mapatge en línia d'un àlies pendent (QA-S8-R1). `label` és el text del
// botó quan el desplegable està tancat; `onPick` rep el POMMaster triat.
function PomPicker({ t, onPick, label }) {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])

  const search = (value) => {
    setQ(value)
    if (!value.trim()) { setResults([]); return }
    poms.list({ search: value.trim(), page_size: 15 })
      .then(res => setResults(res.data?.results ?? (Array.isArray(res.data) ? res.data : [])))
      .catch(() => setResults([]))
  }

  if (!open) {
    return (
      // §1b(d) · el taronja de TEXT s'enfosqueix: `--warn-state` com a tinta no arriba a AA.
      // La marca (la vora) es queda al to viu; el text va a `--warn-ink`.
      <button type="button" onClick={() => setOpen(true)} style={{
        ...miniBtn, borderColor: 'var(--warn-state)', color: 'var(--warn-ink)',
      }}>
        <i className="ti ti-map-pin-plus" aria-hidden="true"
          style={{ fontSize: 14, marginRight: 6, color: 'currentColor' }} />{label}
      </button>
    )
  }
  return (
    <div>
      <input autoFocus value={q} onChange={e => search(e.target.value)}
        onKeyDown={e => { if (e.key === 'Escape') { setOpen(false); setQ(''); setResults([]) } }}
        placeholder={t('clients.alias_search_pom')} style={{ ...camp, width: 220 }} />
      {results.length > 0 && (
        <ul style={llistaResultats}>
          {results.map(pm => (
            <li key={pm.id}>
              <button type="button" onClick={() => { setOpen(false); setQ(''); setResults([]); onPick(pm) }}
                style={itemResultat}>
                <span style={{ fontWeight: 600 }}>{pm.codi_client}</span> · {pm.nom_client}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// Fila d'alta d'un àlies: codi + descripció + cercador de POM del catàleg.
function AliasAddRow({ customer, t, onCreated, onError }) {
  const [code, setCode] = useState('')
  const [descEn, setDescEn] = useState('')
  const [descLocal, setDescLocal] = useState('')
  const [lang, setLang] = useState('')
  const [q, setQ] = useState('')
  const [results, setResults] = useState([])
  const [pom, setPom] = useState(null)   // {id, codi_client, nom_client}
  const [saving, setSaving] = useState(false)

  const search = () => {
    if (!q.trim()) { setResults([]); return }
    poms.list({ search: q.trim(), page_size: 20 })
      .then(res => setResults(res.data?.results ?? (Array.isArray(res.data) ? res.data : [])))
      .catch(() => setResults([]))
  }

  const create = () => {
    if (!code.trim()) { onError(t('clients.required')); return }
    if (!pom) { onError(t('clients.alias_pom_required')); return }
    setSaving(true)
    // Escriu els camps VIUS (description_en/local + language), no `client_description`: el model
    // el declara obsolet i prohibeix escriure-hi (models.py:255-258). Fins ara l'alta manual hi
    // anava, i era l'únic camí que encara alimentava el camp mort (QA-S8 · D4b).
    customerAliases.create({
      customer: customer.id, client_code: code.trim(),
      description_en: descEn.trim(), description_local: descLocal.trim(),
      language: lang.trim().toLowerCase(),
      pom: pom.id, origen: 'MANUAL',
    })
      .then(() => {
        setCode(''); setDescEn(''); setDescLocal(''); setLang('')
        setQ(''); setResults([]); setPom(null); onCreated()
      })
      .catch(e => onError(e?.response?.data?.non_field_errors?.[0] || e?.response?.data?.detail || t('clients.error')))
      .finally(() => setSaving(false))
  }

  return (
    <div style={{
      paddingBottom: 14, marginBottom: 14,
      borderBottomWidth: 1, borderBottomStyle: 'solid', borderBottomColor: 'var(--line)',
    }}>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <label style={miniLabel}>{t('clients.alias_code')}
          <input value={code} onChange={e => setCode(e.target.value)} maxLength={60}
            style={{ ...camp, width: 120, display: 'block', marginTop: 4, fontFamily: MONO }} />
        </label>
        <label style={miniLabel}>{t('clients.alias_desc_en')}
          <input value={descEn} onChange={e => setDescEn(e.target.value)} maxLength={200}
            style={{ ...camp, width: 200, display: 'block', marginTop: 4 }} />
        </label>
        <label style={miniLabel}>{t('clients.alias_desc_local')}
          <input value={descLocal} onChange={e => setDescLocal(e.target.value)} maxLength={200}
            style={{ ...camp, width: 180, display: 'block', marginTop: 4 }} />
        </label>
        <label style={miniLabel}>{t('clients.alias_lang')}
          <input value={lang} onChange={e => setLang(e.target.value)} maxLength={2} placeholder="es"
            style={{ ...camp, width: 56, display: 'block', marginTop: 4, fontFamily: MONO }} />
        </label>
        <label style={miniLabel}>{t('clients.alias_pom')}
          <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
            <input value={q} onChange={e => setQ(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); search() } }}
              placeholder={t('clients.alias_search_pom')} style={{ ...camp, width: 200 }} />
            <button onClick={search} type="button" style={miniBtn}><i className="ti ti-search" style={{ fontSize: 13 }} /></button>
          </div>
        </label>
        <button type="button" onClick={create} disabled={saving}
          style={{ ...botoPri, ...(saving ? apagat : null) }}>
          <i className="ti ti-plus" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
          {t('clients.alias_add')}
        </button>
      </div>

      {pom && (
        <div style={{ marginTop: 8, fontSize: 'var(--fs-body)' }}>
          {t('clients.alias_pom')}: <span style={{ fontFamily: MONO, fontWeight: 600 }}>{pom.codi_client}</span> · {pom.nom_client}
          <button onClick={() => setPom(null)} type="button" style={{ ...miniBtn, marginLeft: 8 }}>×</button>
        </div>
      )}
      {!pom && results.length > 0 && (
        <ul style={{ ...llistaResultats, margin: '8px 0 0' }}>
          {results.map(r => (
            <li key={r.id}>
              <button type="button" onClick={() => { setPom(r); setResults([]) }} style={itemResultat}>
                <span style={{ fontWeight: 600 }}>{r.codi_client}</span> · {r.nom_client}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Tab COMERCIAL — ofertes i comandes del client (enllaç a la fitxa de detall) ─────
function ComercialTab({ customer, t, navigate }) {
  const [quotes, setQuotes] = useState([])
  const [orders, setOrders] = useState([])
  const [deliveryNotes, setDeliveryNotes] = useState([])
  const [busy, setBusy] = useState(true)

  useEffect(() => {
    let alive = true
    const asList = (r) => r.data?.results ?? (Array.isArray(r.data) ? r.data : [])
    Promise.all([
      commerce.quotes.list({ customer: customer.id, ordering: '-created_at', page_size: 500 }),
      commerce.orders.list({ customer: customer.id, ordering: '-created_at', page_size: 500 }),
      commerce.deliveryNotes.list({ customer: customer.id, ordering: '-created_at', page_size: 500 }),
    ]).then(([q, o, d]) => {
      if (!alive) return
      setQuotes(asList(q)); setOrders(asList(o)); setDeliveryNotes(asList(d))
    }).catch(() => {}).finally(() => { if (alive) setBusy(false) })
    return () => { alive = false }
  }, [customer.id])

  // Columnes llegibles: número de document (mai la PK), data, total, estat com a badge. Aquestes
  // tres llistes SÍ que són d'una línia per fila i entren a la graella canònica sense excepcions:
  // la dada reina és el NÚMERO (a un document, el número és l'entitat — l'invers d'un client).
  const docCols = (badge) => [
    { key: 'num', label: t('clients.col_num'), min: 120, max: 160,
      estil: { fontWeight: 600 }, titol: r => r.document_number || `#${r.id}`,
      render: r => r.document_number || `#${r.id}` },
    { key: 'data', label: t('clients.col_data'), min: 90, max: 110,
      estil: { fontSize: 11, color: 'var(--text-soft)' },
      render: r => dayOf(r) || '—' },
    { key: 'total', label: t('clients.col_total'), min: 90, max: 120, align: 'right',
      render: r => money(r.total) },
    { key: 'estat', label: t('clients.col_estat'), min: 100, max: 130, render: badge },
  ]

  if (busy) return <EstatBuit>{t('clients.loading')}</EstatBuit>

  const seccio = (titolKey, files, buitKey, badge, ruta) => (
    <section>
      <SectionTitle t={t} title={titolKey} count={files.length} />
      {files.length === 0 ? <EstatBuit>{t(buitKey)}</EstatBuit> : (
        <TaulaLlista cols={docCols(badge)} files={files} clau={(r) => r.id}
          onObrir={(r) => navigate(`${ruta}/${r.id}`)} />
      )}
    </section>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      {seccio('clients.quotes_title', quotes, 'clients.quotes_empty',
        r => <StatusBadge status={r.status} t={t} />, '/comercial/ofertes')}
      {seccio('clients.orders_title', orders, 'clients.orders_empty',
        r => <OrderStatusBadge status={r.status} t={t} />, '/comercial/comandes')}
      {seccio('clients.deliverynotes_title', deliveryNotes, 'clients.deliverynotes_empty',
        r => <DNStatusBadge status={r.status} t={t} />, '/comercial/albarans')}
    </div>
  )
}

// ── helpers de presentació ──────────────────────────────────────────────────────────
// §3 · targeta = radi 12 (`--r-card`) i filet d'1px `--line`. El 10 no és cap dels tres radis
// del sistema, i `0.5px` no és cap amplada de la casa. Vores en LONGHAND a posta: una shorthand
// `border` col·locada després de la seva pròpia longhand la reescriu sencera, i és el defecte
// que el bloc A va haver de caçar amb el navegador (línies negres de 3px on hi havia d'haver
// un filet).
const rowCard = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10,
  padding: '10px 14px',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
  borderRadius: 'var(--r-card)', background: 'var(--panel)', cursor: 'pointer',
}
const miniLabel = {
  fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-soft)',
  textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 600,
}
const miniBtn = {
  background: 'var(--panel)', color: 'var(--text-main)', cursor: 'pointer',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--gold-border)',
  borderRadius: 'var(--r-ctrl)', padding: '6px 10px',
  fontFamily: MONO, fontSize: 'var(--fs-body)', lineHeight: '16px',
}
// El desplegable de resultats del cercador de POM: mateixa forma que el menú desplegable de la
// casa (`ChromLlista`) — panell blanc, filet `--line`, radi de control. El 8 de radi que hi
// havia no és cap dels tres del sistema.
const llistaResultats = {
  listStyle: 'none', padding: 0, margin: '4px 0 0', maxHeight: 160, overflowY: 'auto',
  borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
  borderRadius: 'var(--r-ctrl)', background: 'var(--panel)',
}
const itemResultat = {
  width: '100%', textAlign: 'left', background: 'none', cursor: 'pointer',
  padding: '6px 10px', fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
  borderWidth: 0, borderBottomWidth: 1, borderStyle: 'solid', borderColor: 'var(--line-soft)',
}

// §2 · h2 de secció a 18/24. El comptador al costat, en caption i tinta suau — «KPI/recomptes
// NEUTRES» (§8c). El pes 300 dels subtítols se'n va: no és cap dels pesos del sistema.
function SectionTitle({ t, title, subtitle, count, meta }) {
  const metaText = meta != null ? meta : (count != null ? String(count) : null)
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <h2 style={{ fontSize: 'var(--fs-h2)', lineHeight: '24px', fontWeight: 500,
          fontFamily: MONO, color: 'var(--text-main)', margin: 0 }}>{t(title)}</h2>
        {metaText && <span style={{ fontSize: 'var(--fs-caption)', fontFamily: MONO,
          color: 'var(--text-soft)' }}>{metaText}</span>}
      </div>
      {subtitle && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)',
        margin: '2px 0 0', fontFamily: MONO }}>{t(subtitle)}</p>}
    </div>
  )
}

// §8c · ESTAT BUIT AMB CONTEXT: explica què és la secció i on es crea, amb portes a la pàgina
// d'origen. La caixa DISCONTÍNUA sobre `--bg-card` se'n va —el filet trencat és la forma d'un
// avís, i això no n'és cap: és una secció que encara no té contingut— i passa a la caixa de la
// casa amb la frase en `--text-faint` cursiva. Els enllaços són PORTES (§5.3), no botons grisos.
function EmptyContext({ t, help, actions = [], navigate }) {
  return (
    <div style={{
      borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
      borderRadius: 'var(--r-card)', padding: '24px 16px', background: 'var(--panel)',
      textAlign: 'center', marginBottom: 16,
    }}>
      <p style={{ ...buit, margin: '0 0 12px' }}>{t(help)}</p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
        {actions.map(([labelKey, to]) => (
          <button key={to} type="button" onClick={() => navigate(to)} style={miniBtn}>
            <i className="ti ti-external-link" aria-hidden="true"
              style={{ fontSize: 14, marginRight: 6, color: 'currentColor' }} />{t(labelKey)}
          </button>
        ))}
      </div>
    </div>
  )
}

// ── P8 · CONNEXIÓ AMB TENANT — l'aterratge del token del Brand ─────────────────────
//
// El Brand emet un token des de la seva pàgina Recursos i el fa arribar pel canal que vulgui.
// Aquí el Studio l'enganxa i el sistema resol tot sol de quin tenant es tracta: no cal que
// ningú escrigui codis a mà ni que les dues bandes es posin d'acord en cap identificador.
//
// El token NO es mostra mai un cop connectat, i no és que s'amagui: el backend no el torna.
// El que es veu és l'ESTAT DEL PONT, que és l'única cosa que el Studio necessita saber-ne.
function ConnexioTenant({ customer, canEdit, t, onSaved, onError }) {
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const connectat = !!customer.codi_global

  const vincula = () => {
    if (!token.trim()) return
    setBusy(true)
    customers.vincularToken(customer.id, token.trim())
      .then(() => { setToken(''); onSaved(t('clients.vincle_ok')) })
      .catch(e => onError(e?.response?.data?.detail || t('clients.error')))
      .finally(() => setBusy(false))
  }

  const desvincula = () => {
    if (!window.confirm(t('clients.vincle_confirm_treure', { codi: customer.codi_global }))) return
    setBusy(true)
    customers.desvincular(customer.id)
      .then(() => onSaved(t('clients.vincle_tret')))
      .catch(e => onError(e?.response?.data?.detail || t('clients.error')))
      .finally(() => setBusy(false))
  }

  // 🛑 BLOQUEJAT-PER-S1 · `vincle_estat` és `tenants.TenantLink.ESTAT_CHOICES`
  // (`fhort/tenants/models.py:345` — ACTIU · ATURAT · REVOCAT) i cap endpoint la publica. Aquí
  // NO es declara la llista: només es distingeix l'estat sa de la resta, que és l'única
  // pregunta que aquesta secció respon («¿em segueixen arribant encàrrecs?»). El dia que
  // l'enumeració es publiqui, el codi i la seva etiqueta vindran d'allà.
  const estat = customer.vincle_estat

  return (
    <div style={{
      marginTop: 28, paddingTop: 20,
      borderTopWidth: 1, borderTopStyle: 'solid', borderTopColor: 'var(--line)',
    }}>
      <SectionTitle t={t} title="clients.vincle_section" subtitle="clients.vincle_section_help" />
      {connectat ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)' }}>
            <i className="ti ti-plug-connected" style={{ marginRight: 6, color: 'var(--gold)' }} aria-hidden="true" />
            {t('clients.vincle_connectat', { codi: customer.codi_global })}
          </span>
          {/* Un pont ATURAT es veu igual de clar que un d'ACTIU: el Studio ha de saber per què
              han deixat d'arribar-li encàrrecs sense haver-ho d'endevinar. §1 · badge de la
              casa: fons suau + tinta + VORA FINA del mateix color. */}
          <Badge variant={estat === 'ACTIU' ? 'ok' : 'warn'}>
            {t(`recursos.estat_${estat}`, estat || '—')}
          </Badge>
          {canEdit && (
            <button type="button" onClick={desvincula} disabled={busy}
              style={{ ...botoDestructiu, ...(busy ? apagat : null) }}>
              {t('clients.vincle_treure')}
            </button>
          )}
        </div>
      ) : canEdit ? (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <input value={token} onChange={e => setToken(e.target.value)}
            placeholder={t('clients.vincle_ph')} disabled={busy}
            style={{ ...camp, flex: 1, minWidth: 260, fontFamily: MONO }} />
          {/* §5.7 · deshabilitat: BAIXA EL FONS, no la tinta. L'`opacity` que hi havia apagava
              també el text i el deixava per sota d'AA — i un botó que no es pot prémer ha de
              seguir sent llegible, perquè el que diu és justament el que ara no es pot fer. */}
          <button type="button" onClick={vincula} disabled={busy || !token.trim()}
            style={{ ...botoPri, ...((busy || !token.trim()) ? apagat : null) }}>
            <i className="ti ti-plug" style={{ fontSize: 14, color: 'currentColor' }} aria-hidden="true" />
            {t('clients.vincle_connectar')}
          </button>
        </div>
      ) : (
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>
          {t('clients.vincle_no_connectat')}
        </div>
      )}
    </div>
  )
}
