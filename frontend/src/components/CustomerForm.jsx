import { selS } from './ui/buttons'

// Formulari compartit de Customer (identitat + fiscal/comercial). Extret de CustomerModal (M2)
// perquè el reutilitzin TANT el modal de creació ràpida COM la fitxa /clients/:id (tab Dades),
// sense duplicar els camps (llei: unificar el ja construït). Controlat: rep `form` + `set`.
const MONO = 'IBM Plex Mono, monospace'
export const REGIMES = ['DOMESTIC', 'INTRA_EU', 'EXPORT', 'EXEMPT']
export const METHODS = ['TRANSFER', 'DIRECT_DEBIT', 'CONFIRMING', 'CASH']

export function initCustomerForm(c = {}) {
  return {
    codi: c?.codi || '', nom: c?.nom || '', active: c?.active ?? true,
    nif: c?.nif || '', adreca_linia1: c?.adreca_linia1 || '',
    adreca_linia2: c?.adreca_linia2 || '', ciutat: c?.ciutat || '',
    codi_postal: c?.codi_postal || '', pais: c?.pais || 'ES',
    email_facturacio: c?.email_facturacio || '',
    condicions_pagament: c?.condicions_pagament || '',
    descompte_pct: c?.descompte_pct ?? '',
    persona_contacte: c?.persona_contacte || '',
    telefon_contacte: c?.telefon_contacte || '',
    tax_regime: c?.tax_regime || 'DOMESTIC', vat_number: c?.vat_number || '',
    payment_method: c?.payment_method || 'TRANSFER',
    payment_terms: c?.payment_terms ?? '',
  }
}

export function customerFormInvalid(f) {
  return !f.codi.trim() || !f.nom.trim()
}

export function customerPayload(f) {
  return {
    codi: f.codi.trim().toUpperCase(), nom: f.nom.trim(), active: f.active,
    nif: f.nif.trim(), adreca_linia1: f.adreca_linia1, adreca_linia2: f.adreca_linia2,
    ciutat: f.ciutat, codi_postal: f.codi_postal, pais: f.pais.trim().toUpperCase(),
    email_facturacio: f.email_facturacio, condicions_pagament: f.condicions_pagament,
    descompte_pct: f.descompte_pct === '' ? 0 : f.descompte_pct,
    persona_contacte: f.persona_contacte, telefon_contacte: f.telefon_contacte,
    tax_regime: f.tax_regime, vat_number: f.vat_number, payment_method: f.payment_method,
    payment_terms: f.payment_terms === '' ? null : f.payment_terms,
  }
}

export function Row({ children }) {
  return <div style={{ display: 'flex', gap: 10 }}>{children}</div>
}

export function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14, flex: 1 }}>
      <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  )
}

// section: 'dades' | 'comercial' | 'all'. `terms` = opcions de PaymentTerms.
export default function CustomerForm({ form, set, terms = [], t, section = 'all' }) {
  const showDades = section === 'all' || section === 'dades'
  const showCom = section === 'all' || section === 'comercial'
  return (
    <>
      {showDades && <>
        <Field label={t('clients.col_codi')}>
          <input value={form.codi} maxLength={3} onChange={e => set('codi', e.target.value.toUpperCase())}
            placeholder="ex: LOS" style={{ ...selS, width: '100%', textTransform: 'uppercase' }} />
        </Field>
        <Field label={t('clients.col_nom')}>
          <input value={form.nom} onChange={e => set('nom', e.target.value)} style={{ ...selS, width: '100%' }} />
        </Field>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', marginTop: 4, marginBottom: showCom ? 18 : 0 }}>
          <input type="checkbox" checked={form.active} onChange={e => set('active', e.target.checked)} /><span>{t('clients.active')}</span>
        </label>
      </>}

      {showCom && <>
        <Field label={t('clients.nif')}>
          <input value={form.nif} onChange={e => set('nif', e.target.value)} style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('clients.adreca_facturacio')}>
          <input value={form.adreca_linia1} onChange={e => set('adreca_linia1', e.target.value)}
            placeholder={t('clients.adreca1')} style={{ ...selS, width: '100%', marginBottom: 6 }} />
          <input value={form.adreca_linia2} onChange={e => set('adreca_linia2', e.target.value)}
            placeholder={t('clients.adreca2')} style={{ ...selS, width: '100%' }} />
        </Field>
        <Row>
          <Field label={t('clients.codi_postal')}>
            <input value={form.codi_postal} onChange={e => set('codi_postal', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
          <Field label={t('clients.ciutat')}>
            <input value={form.ciutat} onChange={e => set('ciutat', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
          <Field label={t('clients.pais')}>
            <input value={form.pais} maxLength={2} onChange={e => set('pais', e.target.value.toUpperCase())}
              style={{ ...selS, width: '100%', textTransform: 'uppercase' }} />
          </Field>
        </Row>
        <Field label={t('clients.email_facturacio')}>
          <input value={form.email_facturacio} onChange={e => set('email_facturacio', e.target.value)}
            type="email" style={{ ...selS, width: '100%' }} />
        </Field>
        <Row>
          <Field label={t('clients.tax_regime')}>
            <select value={form.tax_regime} onChange={e => set('tax_regime', e.target.value)} style={{ ...selS, width: '100%' }}>
              {REGIMES.map(r => <option key={r} value={r}>{t(`clients.tax_regime_${r}`)}</option>)}
            </select>
          </Field>
          <Field label={t('clients.vat_number')}>
            <input value={form.vat_number} onChange={e => set('vat_number', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
        </Row>
        <Row>
          <Field label={t('clients.payment_method')}>
            <select value={form.payment_method} onChange={e => set('payment_method', e.target.value)} style={{ ...selS, width: '100%' }}>
              {METHODS.map(m => <option key={m} value={m}>{t(`clients.payment_method_${m}`)}</option>)}
            </select>
          </Field>
          <Field label={t('clients.payment_terms')}>
            <select value={form.payment_terms ?? ''} onChange={e => set('payment_terms', e.target.value)} style={{ ...selS, width: '100%' }}>
              <option value="">{t('clients.payment_terms_none')}</option>
              {terms.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
        </Row>
        <Field label={t('clients.condicions_pagament')}>
          <input value={form.condicions_pagament} onChange={e => set('condicions_pagament', e.target.value)}
            style={{ ...selS, width: '100%' }} />
        </Field>
        <Field label={t('clients.descompte_pct')}>
          <input value={form.descompte_pct} onChange={e => set('descompte_pct', e.target.value)}
            type="number" step="0.01" min="0" style={{ ...selS, width: '100%' }} />
        </Field>
        <Row>
          <Field label={t('clients.persona_contacte')}>
            <input value={form.persona_contacte} onChange={e => set('persona_contacte', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
          <Field label={t('clients.telefon_contacte')}>
            <input value={form.telefon_contacte} onChange={e => set('telefon_contacte', e.target.value)} style={{ ...selS, width: '100%' }} />
          </Field>
        </Row>
      </>}
    </>
  )
}
