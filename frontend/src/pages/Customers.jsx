import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { customers } from '../api/endpoints'
import CustomerModal from '../components/CustomerModal'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Table from '../components/ui/Table'
import { primaryBtn } from '../components/ui/buttons'

// Estudi tècnic — Arxiu de clients (Customer). Mirall de Suppliers.jsx (Plantilla Peça 0).
// Backend: CustomerViewSet (CRUD); escriptura gated CONFIGURE; destroy→409 si té models.
const MONO = 'IBM Plex Mono, monospace'
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 11, fontFamily: MONO, color: 'var(--text-muted)',
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

  const fetchList = () => customers.list({ ordering: 'codi', page_size: 500 })
    .then(res => res.data?.results ?? (Array.isArray(res.data) ? res.data : []))

  const load = useCallback(() => {
    setError(false)
    return fetchList().then(setItems).catch(() => setError(true))
  }, [])

  useEffect(() => {
    let alive = true
    fetchList()
      .then(rows => { if (alive) setItems(rows) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

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
      <span style={{ fontFamily: MONO, fontWeight: 600 }}>
        {r.codi}{r.is_self && <span style={{ marginLeft: 6, fontSize: 9, color: 'var(--gray)' }}>({t('clients.self')})</span>}
      </span>
    ) },
    { key: 'nom', label: t('clients.col_nom'), render: r => r.nom },
    { key: 'active', label: t('clients.col_active'), render: r => (
      <span style={{
        fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999, fontFamily: MONO,
        background: r.active ? 'var(--ok-bg)' : 'var(--gray-l)', color: r.active ? 'var(--ok)' : 'var(--gray)',
      }}>{r.active ? t('clients.active') : t('clients.inactive')}</span>
    ) },
    ...(canEdit ? [{ key: '_a', label: '', align: 'right', render: r => (
      <span style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
        <button onClick={() => { logoTargetRef.current = r.id; logoRef.current?.click() }} disabled={saving}
          title={r.logo ? t('clients.logo_replace') : t('clients.logo_upload')} style={r.logo ? { ...actBtn, color: 'var(--gold)', borderColor: 'var(--gold)' } : actBtn}>
          <i className="ti ti-photo" aria-hidden="true" style={{ fontSize: 13 }} />
        </button>
        <button onClick={() => navigate(`/clients/${r.id}/plantilla`)} disabled={saving} title={t('clients.template')} style={actBtn}>
          <i className="ti ti-layout" aria-hidden="true" style={{ fontSize: 13 }} />
        </button>
        <button onClick={() => setModal({ mode: 'edit', customer: r })} disabled={saving} style={actBtn}>{t('clients.edit')}</button>
        <button onClick={() => toggleActive(r)} disabled={saving} style={actBtn}>{r.active ? t('clients.deactivate') : t('clients.activate')}</button>
        <button onClick={() => remove(r)} disabled={saving} style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }}>{t('clients.delete')}</button>
      </span>) }] : []),
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 900 }}>
      <input ref={logoRef} type="file" accept="image/*" hidden onChange={handleLogoUpload} />
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('clients.title')}</h1>
          <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('clients.subtitle')}</p>
        </div>
        {canEdit && (
          <button onClick={() => setModal({ mode: 'create' })} style={{ ...primaryBtn, marginLeft: 0 }}>
            <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('clients.new')}
          </button>
        )}
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
