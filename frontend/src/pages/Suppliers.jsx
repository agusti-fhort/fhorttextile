import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { suppliers } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import Table from '../components/ui/Table'
import { selS, primaryBtn } from '../components/ui/buttons'

// Fase catàlegs — Pas 4A · Catàleg de proveïdors (tallers/fàbrica). Plantilla Peça 0.
// Backend: SupplierViewSet (CRUD); escriptura gated SCHEDULE_FITTINGS; destroy→409 si té confeccions.
const MONO = 'IBM Plex Mono, monospace'
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}

export default function Suppliers() {
  const { t } = useTranslation()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('schedule_fittings')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [modal, setModal] = useState(null)   // { mode:'create'|'edit', sup? }

  const fetchList = () => suppliers.list({ ordering: 'name', page_size: 500 })
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

  const toggleActive = (sup) => {
    setSaving(true); setFeedback(null)
    suppliers.update(sup.id, { active: !sup.active })
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('suppliers.saved') }))
      .catch(() => setFeedback({ type: 'err', text: t('suppliers.error') }))
      .finally(() => setSaving(false))
  }

  const remove = (sup) => {
    if (!window.confirm(t('suppliers.confirm_delete', { name: sup.name }))) return
    setSaving(true); setFeedback(null)
    suppliers.remove(sup.id)
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('suppliers.deleted') }))
      // PROTECT → 409 amb {detail} del backend; fallback i18n.
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('suppliers.delete_protected') }))
      .finally(() => setSaving(false))
  }

  const typeLabel = (type) => type === 'factory' ? t('suppliers.factory') : t('suppliers.workshop')

  const columns = [
    { key: 'name', label: t('suppliers.col_name'), render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.name}</span> },
    { key: 'type', label: t('suppliers.col_type'), render: r => typeLabel(r.type) },
    { key: 'active', label: t('suppliers.col_active'), render: r => (
      <span style={{
        fontSize: 'var(--fs-label)', fontWeight: 600, padding: '2px 8px', borderRadius: 999, fontFamily: MONO,
        background: r.active ? 'var(--ok-bg)' : 'var(--gray-l)', color: r.active ? 'var(--ok)' : 'var(--gray)',
      }}>{r.active ? t('suppliers.active') : t('suppliers.inactive')}</span>
    ) },
    ...(canEdit ? [{ key: '_a', label: '', align: 'right', render: r => (
      <span style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
        <button onClick={() => setModal({ mode: 'edit', sup: r })} disabled={saving} style={actBtn}>{t('suppliers.edit')}</button>
        <button onClick={() => toggleActive(r)} disabled={saving} style={actBtn}>{r.active ? t('suppliers.deactivate') : t('suppliers.activate')}</button>
        <button onClick={() => remove(r)} disabled={saving} style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }}>{t('suppliers.delete')}</button>
      </span>) }] : []),
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 900 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('suppliers.title')}</h1>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('suppliers.subtitle')}</p>
        </div>
        {canEdit && (
          <button onClick={() => setModal({ mode: 'create' })} style={{ ...primaryBtn, marginLeft: 0 }}>
            <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('suppliers.new')}
          </button>
        )}
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('suppliers.loading')}</Center>
        : error ? <Center>{t('suppliers.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={items} loading={false} empty={t('suppliers.empty')} />
            </div>
          )}

      {modal && (
        <SupplierModal mode={modal.mode} sup={modal.sup} t={t} saving={saving} setSaving={setSaving} typeLabel={typeLabel}
          onCancel={() => setModal(null)}
          onSaved={(msg) => { setModal(null); load().then(() => setFeedback({ type: 'ok', text: msg })) }}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </div>
  )
}

// B3-M (M3): pestanya "Comercial" amb els camps fiscals/de compra/contacte del proveïdor
// (B1-P4). Tab "Dades" = identitat; tab "Comercial" = fiscalitat, condicions de compra i contacte.
function SupplierModal({ mode, sup, t, saving, setSaving, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  const [tab, setTab] = useState('dades')
  const [name, setName] = useState(sup?.name || '')
  const [type, setType] = useState(sup?.type || 'workshop')
  const [active, setActive] = useState(sup?.active ?? true)
  const [f, setF] = useState({
    rao_social: sup?.rao_social || '', nif: sup?.nif || '',
    adreca_linia1: sup?.adreca_linia1 || '', adreca_linia2: sup?.adreca_linia2 || '',
    codi_postal: sup?.codi_postal || '', ciutat: sup?.ciutat || '', pais: sup?.pais || 'ES',
    condicions_compra: sup?.condicions_compra || '', email_contacte: sup?.email_contacte || '',
    persona_contacte: sup?.persona_contacte || '', telefon_contacte: sup?.telefon_contacte || '',
  })
  const set = (k, v) => setF(prev => ({ ...prev, [k]: v }))
  const invalid = !name.trim()

  const submit = () => {
    if (invalid) { onError(t('suppliers.required')); return }
    setSaving(true)
    const payload = {
      name: name.trim(), type, active,
      rao_social: f.rao_social, nif: f.nif.trim(), adreca_linia1: f.adreca_linia1,
      adreca_linia2: f.adreca_linia2, codi_postal: f.codi_postal, ciutat: f.ciutat,
      pais: f.pais.trim().toUpperCase(), condicions_compra: f.condicions_compra,
      email_contacte: f.email_contacte, persona_contacte: f.persona_contacte,
      telefon_contacte: f.telefon_contacte,
    }
    const req = isEdit ? suppliers.update(sup.id, payload) : suppliers.create(payload)
    req
      .then(() => onSaved(isEdit ? t('suppliers.saved') : t('suppliers.created')))
      .catch(e => onError(e?.response?.data?.name?.[0] || e?.response?.data?.detail || t('suppliers.error')))
      .finally(() => setSaving(false))
  }

  return (
    <Modal title={isEdit ? t('suppliers.edit_title') : t('suppliers.new_title')}
      cancelLabel={t('suppliers.cancel')} confirmLabel={isEdit ? t('suppliers.save') : t('suppliers.create')}
      onCancel={onCancel} onConfirm={submit} confirmDisabled={saving || invalid}>
      <TabBar tab={tab} setTab={setTab}
        tabs={[['dades', t('suppliers.tab_dades')], ['comercial', t('suppliers.tab_comercial')]]} />

      {tab === 'dades' && <>
        <Field label={t('suppliers.col_name')}><input value={name} onChange={e => setName(e.target.value)} style={{ ...selS, width: '100%' }} /></Field>
        <Field label={t('suppliers.col_type')}>
          <select value={type} onChange={e => setType(e.target.value)} style={{ ...selS, width: '100%' }}>
            <option value="workshop">{t('suppliers.workshop')}</option>
            <option value="factory">{t('suppliers.factory')}</option>
          </select>
        </Field>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', marginTop: 4 }}>
          <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /><span>{t('suppliers.active')}</span>
        </label>
      </>}

      {tab === 'comercial' && <>
        <Field label={t('suppliers.rao_social')}>
          <input value={f.rao_social} onChange={e => set('rao_social', e.target.value)} style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('suppliers.nif')}>
          <input value={f.nif} onChange={e => set('nif', e.target.value)} style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('suppliers.adreca')}>
          <input value={f.adreca_linia1} onChange={e => set('adreca_linia1', e.target.value)}
            placeholder={t('suppliers.adreca1')} style={{ ...selS, width: '100%', marginBottom: 6 }} />
          <input value={f.adreca_linia2} onChange={e => set('adreca_linia2', e.target.value)}
            placeholder={t('suppliers.adreca2')} style={{ ...selS, width: '100%' }} />
        </Field>
        <Row>
          <Field label={t('suppliers.codi_postal')}>
            <input value={f.codi_postal} onChange={e => set('codi_postal', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
          <Field label={t('suppliers.ciutat')}>
            <input value={f.ciutat} onChange={e => set('ciutat', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
          <Field label={t('suppliers.pais')}>
            <input value={f.pais} maxLength={2} onChange={e => set('pais', e.target.value.toUpperCase())}
              style={{ ...selS, width: '100%', textTransform: 'uppercase' }} />
          </Field>
        </Row>
        <Field label={t('suppliers.condicions_compra')}>
          <input value={f.condicions_compra} onChange={e => set('condicions_compra', e.target.value)} style={{ ...selS, width: '100%' }} />
        </Field>
        <Row>
          <Field label={t('suppliers.persona_contacte')}>
            <input value={f.persona_contacte} onChange={e => set('persona_contacte', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
          <Field label={t('suppliers.telefon_contacte')}>
            <input value={f.telefon_contacte} onChange={e => set('telefon_contacte', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
        </Row>
        <Field label={t('suppliers.email_contacte')}>
          <input value={f.email_contacte} onChange={e => set('email_contacte', e.target.value)} type="email" style={{ ...selS, width: '100%' }} />
        </Field>
      </>}
    </Modal>
  )
}

function TabBar({ tab, setTab, tabs }) {
  return (
    <div style={{ display: 'flex', gap: 4, borderBottom: '0.5px solid var(--border)', marginBottom: 16 }}>
      {tabs.map(([k, label]) => (
        <button key={k} onClick={() => setTab(k)} style={{
          fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '6px 12px', cursor: 'pointer',
          background: 'none', border: 'none', color: tab === k ? 'var(--gold)' : 'var(--text-muted)',
          borderBottom: tab === k ? '2px solid var(--gold)' : '2px solid transparent', marginBottom: -1,
        }}>{label}</button>
      ))}
    </div>
  )
}

function Row({ children }) {
  return <div style={{ display: 'flex', gap: 10 }}>{children}</div>
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14, flex: 1 }}>
      <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  )
}
