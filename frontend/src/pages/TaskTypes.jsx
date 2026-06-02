import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { taskTypes } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import Table from '../components/ui/Table'
import { selS, primaryBtn } from '../components/ui/buttons'

// Fase catàlegs — Pas 2 · Catàleg de TaskType (editable). Primera pàgina amb la plantilla Peça 0:
// capçalera MONO+subtítol · i18n · tokens · api/endpoints · Center (loading/buit/error) · Feedback ·
// ui/Table + ui/Modal per al CRUD. Backend: TaskTypeViewSet (CRUD); escriptura gated DEFINE_TASKS.
const MONO = 'IBM Plex Mono, monospace'

const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 11, fontFamily: MONO, color: 'var(--text-muted)',
}

export default function TaskTypes() {
  const { t } = useTranslation()
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('define_tasks')   // escriptura (el backend també ho força)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [modal, setModal] = useState(null)   // { mode:'create'|'edit', tt? }

  const fetchList = () => taskTypes.list({ ordering: 'default_order' })
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

  const toggleActive = (tt) => {
    setSaving(true); setFeedback(null)
    taskTypes.update(tt.id, { active: !tt.active })
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('task_types.saved') }))
      .catch(() => setFeedback({ type: 'err', text: t('task_types.error') }))
      .finally(() => setSaving(false))
  }

  const remove = (tt) => {
    if (!window.confirm(t('task_types.confirm_delete', { code: tt.code }))) return
    setSaving(true); setFeedback(null)
    taskTypes.remove(tt.id)
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('task_types.deleted') }))
      // PROTECT al backend → 409 amb `detail` (el missatge ve del backend); fallback i18n per altres errors.
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('task_types.delete_protected') }))
      .finally(() => setSaving(false))
  }

  const columns = [
    { key: 'code', label: t('task_types.col_code'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.code}</span> },
    { key: 'name', label: t('task_types.col_name') },
    { key: 'default_order', label: t('task_types.col_order'), align: 'right',
      render: r => <span style={{ fontFamily: MONO }}>{r.default_order}</span> },
    { key: 'active', label: t('task_types.col_active'),
      render: r => (
        <span style={{
          fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 999, fontFamily: MONO,
          background: r.active ? 'var(--ok-bg)' : 'var(--gray-l)',
          color: r.active ? 'var(--ok)' : 'var(--gray)',
        }}>{r.active ? t('task_types.active') : t('task_types.inactive')}</span>
      ) },
    ...(canEdit ? [{
      key: '_act', label: '', align: 'right',
      render: r => (
        <span style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
          <button onClick={() => setModal({ mode: 'edit', tt: r })} disabled={saving} style={actBtn}>{t('task_types.edit')}</button>
          <button onClick={() => toggleActive(r)} disabled={saving} style={actBtn}>
            {r.active ? t('task_types.deactivate') : t('task_types.activate')}
          </button>
          <button onClick={() => remove(r)} disabled={saving}
            style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }}>{t('task_types.delete')}</button>
        </span>
      ) }] : []),
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('task_types.title')}</h1>
          <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('task_types.subtitle')}</p>
        </div>
        {canEdit && (
          <button onClick={() => setModal({ mode: 'create' })} style={{ ...primaryBtn, marginLeft: 0 }}>
            <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('task_types.new')}
          </button>
        )}
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('task_types.loading')}</Center>
        : error ? <Center>{t('task_types.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={items} loading={false} empty={t('task_types.empty')} />
            </div>
          )}

      {modal && (
        <TaskTypeModal mode={modal.mode} tt={modal.tt} t={t} saving={saving} setSaving={setSaving}
          onCancel={() => setModal(null)}
          onSaved={(msg) => { setModal(null); load().then(() => setFeedback({ type: 'ok', text: msg })) }}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </div>
  )
}

function TaskTypeModal({ mode, tt, t, saving, setSaving, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  const [code, setCode] = useState(tt?.code || '')
  const [name, setName] = useState(tt?.name || '')
  const [order, setOrder] = useState(tt?.default_order ?? 0)
  const [active, setActive] = useState(tt?.active ?? true)

  const invalid = !name.trim() || (!isEdit && !code.trim())

  const submit = () => {
    if (invalid) { onError(t('task_types.required')); return }
    setSaving(true)
    const payload = isEdit
      ? { name: name.trim(), default_order: Number(order) || 0 }                                  // code read-only en editar
      : { code: code.trim(), name: name.trim(), default_order: Number(order) || 0, active }
    const req = isEdit ? taskTypes.update(tt.id, payload) : taskTypes.create(payload)
    req
      .then(() => onSaved(isEdit ? t('task_types.saved') : t('task_types.created')))
      .catch(e => onError(e?.response?.data?.code?.[0] || e?.response?.data?.detail || t('task_types.error')))
      .finally(() => setSaving(false))
  }

  return (
    <Modal
      title={isEdit ? t('task_types.edit_title') : t('task_types.new_title')}
      cancelLabel={t('task_types.cancel')}
      confirmLabel={isEdit ? t('task_types.save') : t('task_types.create')}
      onCancel={onCancel} onConfirm={submit}
      confirmDisabled={saving || invalid}
    >
      <Field label={t('task_types.col_code')}>
        <input value={code} disabled={isEdit} onChange={e => setCode(e.target.value)}
          placeholder="pattern_cad" style={{ ...selS, width: '100%', opacity: isEdit ? 0.6 : 1 }} />
        {isEdit && <Hint>{t('task_types.code_locked')}</Hint>}
      </Field>
      <Field label={t('task_types.col_name')}>
        <input value={name} onChange={e => setName(e.target.value)} style={{ ...selS, width: '100%' }} />
      </Field>
      <Field label={t('task_types.col_order')}>
        <input type="number" value={order} onChange={e => setOrder(e.target.value)} style={{ ...selS, width: '100%' }} />
        <Hint>{t('task_types.order_hint')}</Hint>
      </Field>
      {!isEdit && (
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginTop: 4 }}>
          <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} />
          <span>{t('task_types.active')}</span>
        </label>
      )}
    </Modal>
  )
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ fontSize: 11, fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  )
}
function Hint({ children }) {
  return <div style={{ fontSize: 10, color: 'var(--gray)', marginTop: 4 }}>{children}</div>
}
