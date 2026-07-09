import { useState, useEffect } from 'react'
import { customers, commerce } from '../api/endpoints'
import Modal from './ui/Modal'
import CustomerForm, { initCustomerForm, customerPayload, customerFormInvalid } from './CustomerForm'

// Modal d'alta/edició de Customer (client). Compartit per la pàgina Clients (creació ràpida) i pel
// selector del wizard de model (Pas 8, opció "crear nou client"). Gestiona la seva pròpia crida
// HTTP i el seu estat saving. onSaved(customer, msg) torna l'objecte creat/editat perquè el wizard
// el pugui seleccionar immediatament.
// B3-M (M2): tabs "Dades"/"Comercial" amb els camps fiscals/comercials. Els camps viuen a
// CustomerForm (compartit amb la fitxa /clients/:id).
const MONO = 'IBM Plex Mono, monospace'

export default function CustomerModal({ mode, customer, t, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  const [tab, setTab] = useState('dades')
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
    const req = isEdit
      ? customers.update(customer.id, customerPayload(form))
      : customers.create(customerPayload(form))
    req
      .then(res => onSaved(res.data, isEdit ? t('clients.saved') : t('clients.created')))
      .catch(e => onError(
        e?.response?.data?.codi?.[0] || e?.response?.data?.detail || t('clients.error')))
      .finally(() => setSaving(false))
  }

  return (
    <Modal title={isEdit ? t('clients.edit_title') : t('clients.new_title')}
      cancelLabel={t('clients.cancel')} confirmLabel={isEdit ? t('clients.save') : t('clients.create')}
      onCancel={onCancel} onConfirm={submit} confirmDisabled={saving || invalid}>
      <TabBar tab={tab} setTab={setTab}
        tabs={[['dades', t('clients.tab_dades')], ['comercial', t('clients.tab_comercial')]]} />
      <CustomerForm form={form} set={set} terms={terms} t={t} section={tab} />
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
