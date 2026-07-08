import { useState, useEffect } from 'react'
import { customers, commerce } from '../api/endpoints'
import Modal from './ui/Modal'
import { selS } from './ui/buttons'

// Modal d'alta/edició de Customer (client). Compartit per la pàgina Clients (Pas 7) i pel
// selector del wizard de model (Pas 8, opció "crear nou client"). Gestiona la seva pròpia
// crida HTTP i el seu estat saving. onSaved(customer, msg) torna l'objecte creat/editat
// perquè el wizard el pugui seleccionar immediatament.
// B3-M (M2): pestanya "Comercial" amb els camps fiscals/comercials que ja viatgen per API
// (B1-P3 + B3a). Tab "Dades" = identitat mínima; tab "Comercial" = fiscalitat i condicions.
const MONO = 'IBM Plex Mono, monospace'
const REGIMES = ['DOMESTIC', 'INTRA_EU', 'EXPORT', 'EXEMPT']
const METHODS = ['TRANSFER', 'DIRECT_DEBIT', 'CONFIRMING', 'CASH']

export default function CustomerModal({ mode, customer, t, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  const [tab, setTab] = useState('dades')
  const [codi, setCodi] = useState(customer?.codi || '')
  const [nom, setNom] = useState(customer?.nom || '')
  const [active, setActive] = useState(customer?.active ?? true)
  // Camps comercials/fiscals (B1-P3 + B3a). Tots additius i opcionals.
  const [f, setF] = useState({
    nif: customer?.nif || '', adreca_linia1: customer?.adreca_linia1 || '',
    adreca_linia2: customer?.adreca_linia2 || '', ciutat: customer?.ciutat || '',
    codi_postal: customer?.codi_postal || '', pais: customer?.pais || 'ES',
    email_facturacio: customer?.email_facturacio || '',
    condicions_pagament: customer?.condicions_pagament || '',
    descompte_pct: customer?.descompte_pct ?? '',
    persona_contacte: customer?.persona_contacte || '',
    telefon_contacte: customer?.telefon_contacte || '',
    tax_regime: customer?.tax_regime || 'DOMESTIC', vat_number: customer?.vat_number || '',
    payment_method: customer?.payment_method || 'TRANSFER',
    payment_terms: customer?.payment_terms ?? '',
  })
  const set = (k, v) => setF(prev => ({ ...prev, [k]: v }))
  const [terms, setTerms] = useState([])
  const [saving, setSaving] = useState(false)
  const invalid = !codi.trim() || !nom.trim()

  useEffect(() => {
    commerce.paymentTerms.list({ active: true })
      .then(res => setTerms(res.data?.results ?? (Array.isArray(res.data) ? res.data : [])))
      .catch(() => setTerms([]))
  }, [])

  const submit = () => {
    if (invalid) { onError(t('clients.required')); return }
    setSaving(true)
    const payload = {
      codi: codi.trim().toUpperCase(), nom: nom.trim(), active,
      nif: f.nif.trim(), adreca_linia1: f.adreca_linia1, adreca_linia2: f.adreca_linia2,
      ciutat: f.ciutat, codi_postal: f.codi_postal, pais: f.pais.trim().toUpperCase(),
      email_facturacio: f.email_facturacio, condicions_pagament: f.condicions_pagament,
      descompte_pct: f.descompte_pct === '' ? 0 : f.descompte_pct,
      persona_contacte: f.persona_contacte, telefon_contacte: f.telefon_contacte,
      tax_regime: f.tax_regime, vat_number: f.vat_number, payment_method: f.payment_method,
      payment_terms: f.payment_terms === '' ? null : f.payment_terms,
    }
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
      <TabBar tab={tab} setTab={setTab}
        tabs={[['dades', t('clients.tab_dades')], ['comercial', t('clients.tab_comercial')]]} />

      {tab === 'dades' && <>
        <Field label={t('clients.col_codi')}>
          <input value={codi} maxLength={3} onChange={e => setCodi(e.target.value.toUpperCase())}
            placeholder="ex: LOS" style={{ ...selS, width: '100%', textTransform: 'uppercase' }} />
        </Field>
        <Field label={t('clients.col_nom')}>
          <input value={nom} onChange={e => setNom(e.target.value)} style={{ ...selS, width: '100%' }} />
        </Field>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', marginTop: 4 }}>
          <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /><span>{t('clients.active')}</span>
        </label>
      </>}

      {tab === 'comercial' && <>
        <Field label={t('clients.nif')}>
          <input value={f.nif} onChange={e => set('nif', e.target.value)}
            style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('clients.adreca_facturacio')}>
          <input value={f.adreca_linia1} onChange={e => set('adreca_linia1', e.target.value)}
            placeholder={t('clients.adreca1')} style={{ ...selS, width: '100%', marginBottom: 6 }} />
          <input value={f.adreca_linia2} onChange={e => set('adreca_linia2', e.target.value)}
            placeholder={t('clients.adreca2')} style={{ ...selS, width: '100%' }} />
        </Field>
        <Row>
          <Field label={t('clients.codi_postal')}>
            <input value={f.codi_postal} onChange={e => set('codi_postal', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
          <Field label={t('clients.ciutat')}>
            <input value={f.ciutat} onChange={e => set('ciutat', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
          <Field label={t('clients.pais')}>
            <input value={f.pais} maxLength={2} onChange={e => set('pais', e.target.value.toUpperCase())}
              style={{ ...selS, width: '100%', textTransform: 'uppercase' }} />
          </Field>
        </Row>
        <Field label={t('clients.email_facturacio')}>
          <input value={f.email_facturacio} onChange={e => set('email_facturacio', e.target.value)}
            type="email" style={{ ...selS, width: '100%' }} />
        </Field>

        <Row>
          <Field label={t('clients.tax_regime')}>
            <select value={f.tax_regime} onChange={e => set('tax_regime', e.target.value)} style={{ ...selS, width: '100%' }}>
              {REGIMES.map(r => <option key={r} value={r}>{t(`clients.tax_regime_${r}`)}</option>)}
            </select>
          </Field>
          <Field label={t('clients.vat_number')}>
            <input value={f.vat_number} onChange={e => set('vat_number', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
        </Row>
        <Row>
          <Field label={t('clients.payment_method')}>
            <select value={f.payment_method} onChange={e => set('payment_method', e.target.value)} style={{ ...selS, width: '100%' }}>
              {METHODS.map(m => <option key={m} value={m}>{t(`clients.payment_method_${m}`)}</option>)}
            </select>
          </Field>
          <Field label={t('clients.payment_terms')}>
            <select value={f.payment_terms ?? ''} onChange={e => set('payment_terms', e.target.value)} style={{ ...selS, width: '100%' }}>
              <option value="">{t('clients.payment_terms_none')}</option>
              {terms.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
        </Row>
        <Field label={t('clients.condicions_pagament')}>
          <input value={f.condicions_pagament} onChange={e => set('condicions_pagament', e.target.value)}
            style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('clients.descompte_pct')}>
          <input value={f.descompte_pct} onChange={e => set('descompte_pct', e.target.value)}
            type="number" step="0.01" min="0" style={{ ...selS, width: '100%' }} />
        </Field>
        <Row>
          <Field label={t('clients.persona_contacte')}>
            <input value={f.persona_contacte} onChange={e => set('persona_contacte', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
          <Field label={t('clients.telefon_contacte')}>
            <input value={f.telefon_contacte} onChange={e => set('telefon_contacte', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
        </Row>
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
