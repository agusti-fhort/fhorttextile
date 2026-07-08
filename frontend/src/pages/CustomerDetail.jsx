import { useState, useEffect, useCallback } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import {
  customers, customerAliases, commerce, poms, gradingRuleSets, sizingProfiles,
} from '../api/endpoints'
import CustomerForm, { initCustomerForm, customerPayload, customerFormInvalid } from '../components/CustomerForm'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'
import { StatusBadge } from './Quotes'
import { OrderStatusBadge } from './Orders'
import { primaryBtn, selS } from '../components/ui/buttons'

const money = (v) => `${Number(v ?? 0).toFixed(2)} €`
const dayOf = (r) => (r.issued_at || r.created_at || '').slice(0, 10)

// Fitxa completa del client (patró ModelSheet: capçalera + barra de tabs ?tab= + cos).
// 3 tabs: Dades (identitat + fiscal, reusa CustomerForm de M2) · Tècnic (biblioteca de
// nomenclatura: CustomerPOMAlias CRUD + graduacions/perfils del client, lectura) · Comercial
// (ofertes/comandes del client). L'edició d'àlies està gated CONFIGURE al backend.
const MONO = 'IBM Plex Mono, monospace'
const TABS = ['dades', 'tecnic', 'comercial']
const ORIGEN_VARIANT = { IMPORT: 'gold', MANUAL: 'ok', MIGRACIO: 'gray' }

export default function CustomerDetail() {
  const { id } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [sp, setSp] = useSearchParams()
  const tabParam = sp.get('tab')
  const activeTab = TABS.includes(tabParam) ? tabParam : 'dades'
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
        </div>
      </div>

      {/* Barra de tabs */}
      <div style={{ display: 'flex', gap: 8, padding: '0.5rem 0', borderBottom: '0.5px solid var(--border)', marginBottom: '1.25rem' }}>
        {TABS.map(tab => (
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

  const loadAliases = useCallback(() => customerAliases.list({ customer: customer.id })
    .then(res => setAliases(res.data?.results ?? (Array.isArray(res.data) ? res.data : []))), [customer.id])

  useEffect(() => {
    let alive = true
    Promise.all([
      customerAliases.list({ customer: customer.id }),
      gradingRuleSets.list({ customer: customer.id }),
      sizingProfiles.list({ customer_codi: customer.codi }),
    ]).then(([a, g, p]) => {
      if (!alive) return
      setAliases(a.data?.results ?? (Array.isArray(a.data) ? a.data : []))
      setRulesets(g.data?.results ?? (Array.isArray(g.data) ? g.data : []))
      const prows = p.data?.results ?? (Array.isArray(p.data) ? p.data : [])
      setProfiles(prows.filter(r => r.customer_codi === customer.codi))
    }).finally(() => { if (alive) setBusy(false) })
    return () => { alive = false }
  }, [customer.id, customer.codi])

  const removeAlias = (a) => {
    if (!window.confirm(t('clients.alias_confirm_delete', { code: a.client_code }))) return
    customerAliases.remove(a.id)
      .then(() => loadAliases())
      .then(() => notify({ type: 'ok', text: t('clients.alias_deleted') }))
      .catch(() => notify({ type: 'err', text: t('clients.error') }))
  }

  // Regla NOMÉS de visualització (no toca dades): si la descripció duplica el codi del
  // client, mostrem '—'. El diccionari (description_en/local) omplirà això de veritat.
  const descDup = (r) => !r.client_description ||
    r.client_description.trim().toLowerCase() === (r.client_code || '').trim().toLowerCase()

  const aliasCols = [
    { key: 'client_code', label: t('clients.alias_code'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.client_code}</span> },
    { key: 'client_description', label: t('clients.alias_desc'),
      render: r => descDup(r) ? <span style={{ color: 'var(--text-muted)' }}>—</span> : r.client_description },
    // POM canònic: codi global (POM-XXX) com a element principal; a sota, abreviatura + nom EN.
    // Fallback per a POMs tenant-only (sense pom_global): el codi_client fa d'identificador i
    // no repetim l'abreviatura si coincideix amb el principal.
    { key: 'pom', label: t('clients.alias_pom'), render: r => {
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
        <SectionTitle t={t} title="clients.biblioteca_title" subtitle="clients.biblioteca_subtitle"
          meta={t('clients.biblioteca_count', { aliases: aliases.length, poms: nPoms })} />
        {canEdit && <AliasAddRow customer={customer} t={t}
          onCreated={() => loadAliases().then(() => notify({ type: 'ok', text: t('clients.alias_saved') }))}
          onError={(text) => notify({ type: 'err', text })} />}
        {busy ? <Center>{t('clients.loading')}</Center> : (
          <Table columns={aliasCols} data={aliases} loading={false} empty={t('clients.alias_empty')} />
        )}
      </section>

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

// Fila d'alta d'un àlies: codi + descripció + cercador de POM del catàleg.
function AliasAddRow({ customer, t, onCreated, onError }) {
  const [code, setCode] = useState('')
  const [desc, setDesc] = useState('')
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
    customerAliases.create({
      customer: customer.id, client_code: code.trim(), client_description: desc.trim(),
      pom: pom.id, origen: 'MANUAL',
    })
      .then(() => { setCode(''); setDesc(''); setQ(''); setResults([]); setPom(null); onCreated() })
      .catch(e => onError(e?.response?.data?.non_field_errors?.[0] || e?.response?.data?.detail || t('clients.error')))
      .finally(() => setSaving(false))
  }

  return (
    <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 10, padding: 12, marginBottom: 14, background: 'var(--bg-muted)' }}>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <label style={miniLabel}>{t('clients.alias_code')}
          <input value={code} onChange={e => setCode(e.target.value)} maxLength={60}
            style={{ ...selS, width: 120, display: 'block', marginTop: 4, fontFamily: MONO }} />
        </label>
        <label style={miniLabel}>{t('clients.alias_desc')}
          <input value={desc} onChange={e => setDesc(e.target.value)} maxLength={200}
            style={{ ...selS, width: 200, display: 'block', marginTop: 4 }} />
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
  const [busy, setBusy] = useState(true)

  useEffect(() => {
    let alive = true
    Promise.all([
      commerce.quotes.list({ customer: customer.id, ordering: '-created_at', page_size: 500 }),
      commerce.orders.list({ customer: customer.id, ordering: '-created_at', page_size: 500 }),
    ]).then(([q, o]) => {
      if (!alive) return
      setQuotes(q.data?.results ?? (Array.isArray(q.data) ? q.data : []))
      setOrders(o.data?.results ?? (Array.isArray(o.data) ? o.data : []))
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

function Empty({ t, k }) {
  return <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', fontStyle: 'italic', margin: 0 }}>{t(k)}</p>
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
