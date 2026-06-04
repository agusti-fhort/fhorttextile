import { useState } from 'react'
import { customers } from '../api/endpoints'
import Modal from './ui/Modal'
import { selS } from './ui/buttons'

// Modal d'alta/edició de Customer (client). Compartit per la pàgina Clients (Pas 7) i pel
// selector del wizard de model (Pas 8, opció "crear nou client"). Gestiona la seva pròpia
// crida HTTP i el seu estat saving. onSaved(customer, msg) torna l'objecte creat/editat
// perquè el wizard el pugui seleccionar immediatament.
const MONO = 'IBM Plex Mono, monospace'

export default function CustomerModal({ mode, customer, t, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  const [codi, setCodi] = useState(customer?.codi || '')
  const [nom, setNom] = useState(customer?.nom || '')
  const [active, setActive] = useState(customer?.active ?? true)
  const [saving, setSaving] = useState(false)
  const invalid = !codi.trim() || !nom.trim()

  const submit = () => {
    if (invalid) { onError(t('clients.required')); return }
    setSaving(true)
    const payload = { codi: codi.trim().toUpperCase(), nom: nom.trim(), active }
    const req = isEdit ? customers.update(customer.id, payload) : customers.create(payload)
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
      <Field label={t('clients.col_codi')}>
        <input value={codi} maxLength={3} onChange={e => setCodi(e.target.value.toUpperCase())}
          placeholder="ex: LOS" style={{ ...selS, width: '100%', textTransform: 'uppercase' }} />
      </Field>
      <Field label={t('clients.col_nom')}>
        <input value={nom} onChange={e => setNom(e.target.value)} style={{ ...selS, width: '100%' }} />
      </Field>
      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, marginTop: 4 }}>
        <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /><span>{t('clients.active')}</span>
      </label>
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
