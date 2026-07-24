import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { customers, tenantConfig } from '../api/endpoints'
import CustomerModal from '../components/CustomerModal'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Table from '../components/ui/Table'
import { primaryBtn } from '../components/ui/buttons'

// Estudi tècnic — Arxiu de clients (Customer). Mirall de Suppliers.jsx (Plantilla Peça 0).
// Backend: CustomerViewSet (CRUD); escriptura gated CONFIGURE; destroy→409 si té models.
const MONO = 'IBM Plex Mono, monospace'
const numCell = { fontFamily: MONO, fontSize: 'var(--fs-body)' }
// Comptador mono; discret (gris) quan és 0.
function Num({ v }) {
  const n = v ?? 0
  return <span style={{ ...numCell, color: n ? 'var(--text-main)' : 'var(--gray-l)' }}>{n}</span>
}
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}

export default function Customers() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [modal, setModal] = useState(null)   // { mode:'create'|'edit', customer? }
  const [search, setSearch] = useState('')
  // Tipologia del tenant ('estudi'|'marca'|'enterprise'), de /api/v1/tenant-config/. `null` =
  // encara no carregada: mentre ho estigui NO es demana el llistat, perquè fer-ho amb un valor
  // endevinat pintaria la llista amb el filtre equivocat i després la corregiria (flash).
  const [tipologia, setTipologia] = useState(null)
  // TS-4c: upload de logo. Un input global reutilitzat + id del client objectiu.
  const logoRef = useRef(null)
  const logoTargetRef = useRef(null)
  const API = import.meta.env.VITE_API_URL || ''

  const handleLogoUpload = (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    const customerId = logoTargetRef.current
    if (!file || !customerId) return
    setSaving(true); setFeedback(null)
    const fd = new FormData(); fd.append('logo', file)
    fetch(`${API}/api/v1/customers/${customerId}/upload-logo/`, {
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

  // Tipologia del tenant: una sola lectura, en muntar. Si la crida falla es cau a 'estudi', que
  // és el comportament històric de la pàgina (amagar el self) — mai deixar la llista penjada.
  useEffect(() => {
    let alive = true
    tenantConfig.get()
      .then(r => { if (alive) setTipologia(r.data?.tipologia || 'estudi') })
      .catch(() => { if (alive) setTipologia('estudi') })
    return () => { alive = false }
  }, [])

  // exclude_self: en un ESTUDI el customer propi és fontaneria del sistema i la pàgina l'amaga;
  // en una MARCA el self és el seu propi patrimoni i s'ha de veure (amb el badge `(self)`), que
  // si no la pàgina Clients d'una Marca pot sortir buida. Els altres consumidors del llistat
  // (selectors de client, filtre del Dashboard) no envien mai el filtre. Cerca server-side
  // (codi/nom): arrossega aquest mateix filtre, i per tant queda coherent amb la llista sola.
  const fetchList = useCallback(() => customers.list({
    ordering: 'codi', page_size: 500,
    ...(tipologia === 'marca' ? {} : { exclude_self: true }),
    ...(search ? { search } : {}),
  }).then(res => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])), [search, tipologia])

  const load = useCallback(() => {
    setError(false)
    return fetchList().then(setItems).catch(() => setError(true))
  }, [fetchList])

  // Càrrega inicial + recàrrega amb debounce quan canvia la cerca (loading només al primer cop).
  // Espera la tipologia: sense ella no se sap si toca `exclude_self` (vegeu fetchList).
  useEffect(() => {
    if (!tipologia) return
    let alive = true
    const id = setTimeout(() => {
      fetchList()
        .then(rows => { if (alive) setItems(rows) })
        .catch(() => { if (alive) setError(true) })
        .finally(() => { if (alive) setLoading(false) })
    }, 200)
    return () => { alive = false; clearTimeout(id) }
  }, [fetchList])

  const toggleActive = (c) => {
    setSaving(true); setFeedback(null)
    customers.update(c.id, { active: !c.active })
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('clients.saved') }))
      .catch(() => setFeedback({ type: 'err', text: t('clients.error') }))
      .finally(() => setSaving(false))
  }

  const remove = (c) => {
    if (!window.confirm(t('clients.confirm_delete', { name: c.nom }))) return
    setSaving(true); setFeedback(null)
    customers.remove(c.id)
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('clients.deleted') }))
      // PROTECT → 409 amb {detail} del backend; fallback i18n.
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('clients.delete_protected') }))
      .finally(() => setSaving(false))
  }

  const columns = [
    { key: 'codi', label: t('clients.col_codi'), render: r => (
      <span style={{ fontFamily: MONO, fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        {r.codi}
        {/* El client propi és el tenant mateix. En una MARCA hi pengen els seus propis models, així
            que conviu a la llista amb els clients de debò: sense una marca clara, la fila que ets TU
            sembla una fila més. Un "(propi)" en gris no ho deia; un badge sí. */}
        {r.is_self && <SelfBadge t={t} />}
      </span>
    ) },
    { key: 'nom', label: t('clients.col_nom'), render: r => r.nom },
    { key: 'active', label: t('clients.col_active'), render: r => (
      <span style={{
        fontSize: 'var(--fs-label)', fontWeight: 600, padding: '2px 8px', borderRadius: 999, fontFamily: MONO,
        background: r.active ? 'var(--ok-bg)' : 'var(--gray-l)', color: r.active ? 'var(--ok)' : 'var(--gray)',
      }}>{r.active ? t('clients.active') : t('clients.inactive')}</span>
    ) },
    { key: 'offers', label: t('clients.col_offers'), render: r => (
      <span style={numCell} title={t('clients.offers_hint')}>
        <b style={{ color: 'var(--text-main)' }}>{r.quotes_sent ?? 0}</b>
        <span style={{ color: 'var(--gray)' }}> / {r.quotes_accepted ?? 0}</span>
      </span>
    ) },
    { key: 'orders_open', label: t('clients.col_orders_open'), render: r => <Num v={r.orders_open} /> },
    { key: 'delivery_notes', label: t('clients.col_delivery_notes'), render: r => <Num v={r.delivery_notes_count} /> },
    ...(canEdit ? [{ key: '_a', label: '', align: 'right', render: r => (
      <span style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
        <button onClick={() => { logoTargetRef.current = r.id; logoRef.current?.click() }} disabled={saving}
          title={r.logo ? t('clients.logo_replace') : t('clients.logo_upload')} style={r.logo ? { ...actBtn, color: 'var(--gold)', borderColor: 'var(--gold)' } : actBtn}>
          <i className="ti ti-photo" aria-hidden="true" style={{ fontSize: 13 }} />
        </button>
        <button onClick={() => navigate(`/clients/${r.id}`)} disabled={saving} style={actBtn}>{t('clients.open_sheet')}</button>
        {/* El client propi no es pot desactivar ni esborrar: el tenant es quedaria sense casa.
            Amagar-ho aquí és cortesia — qui blinda de debò és el backend (views_b.py, 409 amb
            `code: self_customer_protected`). */}
        {!r.is_self && <>
          <button onClick={() => toggleActive(r)} disabled={saving} style={actBtn}>{r.active ? t('clients.deactivate') : t('clients.activate')}</button>
          <button onClick={() => remove(r)} disabled={saving} style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }}>{t('clients.delete')}</button>
        </>}
      </span>) }] : []),
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1100 }}>
      <input ref={logoRef} type="file" accept="image/*" hidden onChange={handleLogoUpload} />
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('clients.title')}</h1>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('clients.subtitle')}</p>
        </div>
        {canEdit && (
          <button onClick={() => setModal({ mode: 'create' })} style={{ ...primaryBtn, marginLeft: 0 }}>
            <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('clients.new')}
          </button>
        )}
      </div>

      {/* Cercador (codi, nom) — patró pàgina Models */}
      <div style={{ marginBottom: 12 }}>
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder={t('clients.search_ph')}
          style={{ padding: '6px 10px', border: '0.5px solid var(--gray-l)', borderRadius: 6, fontSize: 'var(--fs-body)', fontFamily: MONO, background: 'var(--white)', color: 'var(--text-main)', width: '100%', maxWidth: 340 }} />
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('clients.loading')}</Center>
        : error ? <Center>{t('clients.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={items} loading={false} empty={t('clients.empty')} />
            </div>
          )}

      {modal && (
        <CustomerModal mode={modal.mode} customer={modal.customer} t={t}
          onCancel={() => setModal(null)}
          onSaved={(_cust, msg) => { setModal(null); load().then(() => setFeedback({ type: 'ok', text: msg })) }}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </div>
  )
}

// Marca visual del client propi. Viu aquí i s'importa a la fitxa: una sola definició, perquè
// la llista i el detall no puguin divergir en el que és la identitat del tenant.
export function SelfBadge({ t }) {
  return (
    <span style={{
      fontSize: 'var(--fs-caption)', fontWeight: 600, padding: '1px 7px', borderRadius: 999,
      fontFamily: 'IBM Plex Mono, monospace',
      background: 'var(--gold-pale)', color: 'var(--gold)', border: '0.5px solid var(--gold)',
      whiteSpace: 'nowrap',
    }} title={t('clients.self_badge_hint')}>
      <i className="ti ti-home" style={{ marginRight: 4 }} aria-hidden="true" />
      {t('clients.self_badge')}
    </span>
  )
}
