import { useState, useEffect, useCallback } from 'react'
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
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'
import { StatusBadge } from './Quotes'
import { OrderStatusBadge } from './Orders'
import { DNStatusBadge } from './DeliveryNotes'
import { primaryBtn, selS } from '../components/ui/buttons'

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

  const [sp, setSp] = useSearchParams()
  const tabParam = sp.get('tab')
  const setTab = (tab) => setSp({ tab })

  const [customer, setCustomer] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const load = useCallback(() => {
    setError(false)
    return customers.get(id).then(res => setCustomer(res.data)).catch(() => setError(true))
  }, [id])

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
    <div style={{ minWidth: 0 }}>
      {/* Capçalera */}
      <div style={{ padding: '0 0 0.75rem' }}>
        <button onClick={() => navigate('/clients')} style={{
          background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)',
          fontFamily: MONO, fontSize: 'var(--fs-body)', padding: 0, marginBottom: 8,
        }}>
          <i className="ti ti-arrow-left" style={{ fontSize: 13, marginRight: 4 }} />{t('clients.back_to_list')}
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, fontFamily: MONO, margin: 0 }}>
            <span style={{ color: 'var(--gold)', fontWeight: 700 }}>{customer.codi}</span>
            <span style={{ marginLeft: 10 }}>{customer.nom}</span>
          </h1>
          <span style={{
            fontSize: 'var(--fs-label)', fontWeight: 600, padding: '2px 8px', borderRadius: 999, fontFamily: MONO,
            background: customer.active ? 'var(--ok-bg)' : 'var(--gray-l)', color: customer.active ? 'var(--ok)' : 'var(--gray)',
          }}>{customer.active ? t('clients.active') : t('clients.inactive')}</span>
          {/* La fitxa del client propi no es distingia de cap altra: hi entraves i no sabies que
              estaves mirant casa teva. Mateix badge que a la llista (definició única). */}
          {customer.is_self && <SelfBadge t={t} />}
        </div>
      </div>

      {/* Barra de tabs */}
      <div style={{ display: 'flex', gap: 8, padding: '0.5rem 0', borderBottom: '0.5px solid var(--border)', marginBottom: '1.25rem' }}>
        {tabs.map(tab => (
          <button key={tab} onClick={() => setTab(tab)} style={{
            fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 14px', cursor: 'pointer', borderRadius: 8, border: 'none',
            background: activeTab === tab ? 'var(--gold)' : 'var(--bg-muted)',
            color: activeTab === tab ? 'var(--white)' : 'var(--text-muted)', fontWeight: activeTab === tab ? 500 : 400,
          }}>{t(`clients.tab_${tab}`)}</button>
        ))}
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      <div style={{ maxWidth: 820 }}>
        {activeTab === 'dades' && (
          <DadesTab customer={customer} canEdit={canEdit} t={t}
            onSaved={(msg) => load().then(() => setFeedback({ type: 'ok', text: msg }))}
            onError={(text) => setFeedback({ type: 'err', text })} />
        )}
        {activeTab === 'tecnic' && (
          <TecnicTab customer={customer} canEdit={canEdit} t={t} navigate={navigate}
            notify={setFeedback} />
        )}
        {activeTab === 'comercial' && (
          <ComercialTab customer={customer} t={t} navigate={navigate} />
        )}
      </div>
    </div>
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
      {canEdit && (
        <button onClick={submit} disabled={saving || invalid} style={{ ...primaryBtn, marginLeft: 0, marginTop: 8 }}>
          <i className="ti ti-device-floppy" style={{ fontSize: 14 }} />{t('clients.save')}
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

  const aliasCols = [
    { key: 'client_code', label: t('clients.alias_code'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.client_code}</span> },
    // Descripció: EN a dalt (canònica), local a sota amb el codi d'idioma (mateixa convenció que
    // el pas 2 del wizard, DictionaryWizard.jsx:177-182). Els escriu el diccionari; abans la
    // columna llegia el camp obsolet i sortia '—' per a TOTS els àlies del wizard (QA-S8 · D4b).
    { key: 'description_en', label: t('clients.alias_desc'), render: r => {
      const en = r.description_en || legacyDesc(r)
      const local = r.description_local
      if (!en && !local) return <span style={{ color: 'var(--text-muted)' }}>—</span>
      return (
        <div style={{ lineHeight: 1.2 }}>
          {en && <div>{en}</div>}
          {local && (
            <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
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
    { key: 'pom', label: t('clients.alias_pom'), render: r => {
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
          {secondary && <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>{secondary}</div>}
        </div>
      )
    } },
    // Origen com a badge; sota, la data. TODO: CustomerPOMAlias no té camp autor (només dates);
    // el diccionari futur pot afegir-lo.
    { key: 'origen', label: t('clients.alias_origen'), render: r => (
      <div style={{ lineHeight: 1.3 }}>
        <Badge variant={ORIGEN_VARIANT[r.origen] || 'gray'}>{t(`clients.origen_${r.origen}`)}</Badge>
        {r.creat_at && <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginTop: 3 }}>{r.creat_at.slice(0, 10)}</div>}
      </div>
    ) },
    ...(canEdit ? [{ key: '_a', label: '', align: 'right', render: r => (
      <button onClick={() => removeAlias(r)} title={t('clients.delete')} style={{
        background: 'none', border: '0.5px solid var(--err)', borderRadius: 6, cursor: 'pointer',
        padding: '3px 8px', color: 'var(--err)', fontFamily: MONO, fontSize: 'var(--fs-body)',
      }}><i className="ti ti-trash" style={{ fontSize: 13 }} /></button>
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
          {canEdit && (
            <button onClick={() => setShowDict(true)} style={{ ...primaryBtn, marginLeft: 0 }}>
              <i className="ti ti-file-spreadsheet" style={{ fontSize: 14 }} />{t('clients.load_dictionary')}
            </button>
          )}
        </div>
        {canEdit && <AliasAddRow customer={customer} t={t}
          onCreated={() => loadAliases().then(() => notify({ type: 'ok', text: t('clients.alias_saved') }))}
          onError={(text) => notify({ type: 'err', text })} />}
        {busy ? <Center>{t('clients.loading')}</Center> : (
          <Table columns={aliasCols} data={aliases} loading={false} empty={t('clients.alias_empty')} />
        )}
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
                <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
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
                <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
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
      <button onClick={() => setOpen(true)} style={{
        ...miniBtn, borderColor: 'var(--warn)', color: 'var(--warn)', cursor: 'pointer',
      }}>
        <i className="ti ti-map-pin-plus" style={{ fontSize: 13, marginRight: 4 }} />{label}
      </button>
    )
  }
  return (
    <div>
      <input autoFocus value={q} onChange={e => search(e.target.value)}
        onKeyDown={e => { if (e.key === 'Escape') { setOpen(false); setQ(''); setResults([]) } }}
        placeholder={t('clients.alias_search_pom')} style={{ ...selS, width: 220 }} />
      {results.length > 0 && (
        <ul style={{
          listStyle: 'none', padding: 0, margin: '4px 0 0', maxHeight: 160, overflowY: 'auto',
          border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)',
        }}>
          {results.map(pm => (
            <li key={pm.id}>
              <button onClick={() => { setOpen(false); setQ(''); setResults([]); onPick(pm) }}
                style={{
                  width: '100%', textAlign: 'left', background: 'none', border: 'none',
                  cursor: 'pointer', padding: '5px 8px', fontSize: 'var(--fs-body)',
                  borderBottom: '0.5px solid var(--border)',
                }}>
                <span style={{ fontFamily: MONO, fontWeight: 600 }}>{pm.codi_client}</span> · {pm.nom_client}
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
    <div style={{ paddingBottom: 14, marginBottom: 14, borderBottom: '0.5px solid var(--gray-l)' }}>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <label style={miniLabel}>{t('clients.alias_code')}
          <input value={code} onChange={e => setCode(e.target.value)} maxLength={60}
            style={{ ...selS, width: 120, display: 'block', marginTop: 4, fontFamily: MONO }} />
        </label>
        <label style={miniLabel}>{t('clients.alias_desc_en')}
          <input value={descEn} onChange={e => setDescEn(e.target.value)} maxLength={200}
            style={{ ...selS, width: 200, display: 'block', marginTop: 4 }} />
        </label>
        <label style={miniLabel}>{t('clients.alias_desc_local')}
          <input value={descLocal} onChange={e => setDescLocal(e.target.value)} maxLength={200}
            style={{ ...selS, width: 180, display: 'block', marginTop: 4 }} />
        </label>
        <label style={miniLabel}>{t('clients.alias_lang')}
          <input value={lang} onChange={e => setLang(e.target.value)} maxLength={2} placeholder="es"
            style={{ ...selS, width: 56, display: 'block', marginTop: 4, fontFamily: MONO }} />
        </label>
        <label style={miniLabel}>{t('clients.alias_pom')}
          <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
            <input value={q} onChange={e => setQ(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); search() } }}
              placeholder={t('clients.alias_search_pom')} style={{ ...selS, width: 200 }} />
            <button onClick={search} type="button" style={miniBtn}><i className="ti ti-search" style={{ fontSize: 13 }} /></button>
          </div>
        </label>
        <button onClick={create} disabled={saving} style={{ ...primaryBtn, marginLeft: 0 }}>
          <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('clients.alias_add')}
        </button>
      </div>

      {pom && (
        <div style={{ marginTop: 8, fontSize: 'var(--fs-body)' }}>
          {t('clients.alias_pom')}: <span style={{ fontFamily: MONO, fontWeight: 600 }}>{pom.codi_client}</span> · {pom.nom_client}
          <button onClick={() => setPom(null)} type="button" style={{ ...miniBtn, marginLeft: 8 }}>×</button>
        </div>
      )}
      {!pom && results.length > 0 && (
        <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0', maxHeight: 160, overflowY: 'auto', border: '0.5px solid var(--gray-l)', borderRadius: 8, background: 'var(--white)' }}>
          {results.map(r => (
            <li key={r.id}>
              <button onClick={() => { setPom(r); setResults([]) }} type="button" style={{
                width: '100%', textAlign: 'left', background: 'none', border: 'none', cursor: 'pointer',
                padding: '6px 10px', fontSize: 'var(--fs-body)', borderBottom: '0.5px solid var(--border)',
              }}><span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.codi_client}</span> · {r.nom_client}</button>
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

  // Columnes llegibles: número de document (mai la PK), data, total, estat com a badge.
  const docCols = (badge) => [
    { key: 'num', label: t('clients.col_num'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.document_number || `#${r.id}`}</span> },
    { key: 'data', label: t('clients.col_data'),
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{dayOf(r) || '—'}</span> },
    { key: 'total', label: t('clients.col_total'), align: 'right',
      render: r => <span style={{ fontFamily: MONO }}>{money(r.total)}</span> },
    { key: 'estat', label: t('clients.col_estat'), render: badge },
  ]

  if (busy) return <Center>{t('clients.loading')}</Center>

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      <section>
        <SectionTitle t={t} title="clients.quotes_title" count={quotes.length} />
        <Table columns={docCols(r => <StatusBadge status={r.status} t={t} />)}
          data={quotes} loading={false} empty={t('clients.quotes_empty')}
          onRowClick={r => navigate(`/comercial/ofertes/${r.id}`)} />
      </section>
      <section>
        <SectionTitle t={t} title="clients.orders_title" count={orders.length} />
        <Table columns={docCols(r => <OrderStatusBadge status={r.status} t={t} />)}
          data={orders} loading={false} empty={t('clients.orders_empty')}
          onRowClick={r => navigate(`/comercial/comandes/${r.id}`)} />
      </section>
      <section>
        <SectionTitle t={t} title="clients.deliverynotes_title" count={deliveryNotes.length} />
        <Table columns={docCols(r => <DNStatusBadge status={r.status} t={t} />)}
          data={deliveryNotes} loading={false} empty={t('clients.deliverynotes_empty')}
          onRowClick={r => navigate(`/comercial/albarans/${r.id}`)} />
      </section>
    </div>
  )
}

// ── helpers de presentació ──────────────────────────────────────────────────────────
const rowCard = {
  display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10,
  padding: '10px 14px', border: '0.5px solid var(--gray-l)', borderRadius: 10,
  background: 'var(--white)', cursor: 'pointer',
}
const miniLabel = { fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase' }
const miniBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 'var(--fs-body)',
}

// Capçalera de secció a l'estil de la casa (Grading Rules): títol + comptador gris al costat.
function SectionTitle({ t, title, subtitle, count, meta }) {
  const metaText = meta != null ? meta : (count != null ? String(count) : null)
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, fontFamily: MONO, margin: 0 }}>{t(title)}</h2>
        {metaText && <span style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{metaText}</span>}
      </div>
      {subtitle && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: '2px 0 0', fontWeight: 300 }}>{t(subtitle)}</p>}
    </div>
  )
}

// Secció buida amb context: explica què és i on es crea, amb enllaços a la pàgina d'origen.
function EmptyContext({ t, help, actions = [], navigate }) {
  return (
    <div style={{
      border: '1px dashed var(--border)', borderRadius: 10, padding: '1.25rem',
      background: 'var(--bg-card)',
    }}>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', margin: '0 0 10px' }}>{t(help)}</p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {actions.map(([labelKey, to]) => (
          <button key={to} onClick={() => navigate(to)} style={{
            background: 'var(--white)', border: '0.5px solid var(--border)', borderRadius: 6,
            padding: '5px 11px', cursor: 'pointer', fontFamily: MONO, fontSize: 'var(--fs-body)',
            color: 'var(--text-muted)',
          }}>
            <i className="ti ti-external-link" style={{ fontSize: 13, marginRight: 5 }} />{t(labelKey)}
          </button>
        ))}
      </div>
    </div>
  )
}
