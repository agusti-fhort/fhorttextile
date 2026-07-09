import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Modal from '../components/ui/Modal'
import Table from '../components/ui/Table'
import { selS, primaryBtn } from '../components/ui/buttons'
import TranslatableField, { pickTranslation } from '../components/ui/TranslatableField'

// Mòdul Comercial — M4 · Condicions de pagament (PaymentTerms). Llista + fitxa amb fraccions
// (percentage, days_offset, position). Les fraccions s'editen com a conjunt i es desen amb la
// condició en una sola crida (nested writable); el guard Σ%=100 viu al backend i s'hi mostra.
const MONO = 'IBM Plex Mono, monospace'
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}

export default function PaymentTerms() {
  const { t, i18n } = useTranslation()
  const lang = i18n.resolvedLanguage || i18n.language || 'ca'
  const me = useAuthStore(s => s.user)
  const canEdit = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [feedback, setFeedback] = useState(null)
  const [saving, setSaving] = useState(false)
  const [modal, setModal] = useState(null)   // { mode:'create'|'edit', term? }

  const fetchList = () => commerce.paymentTerms.list({ ordering: 'code', page_size: 500 })
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

  const toggleActive = (term) => {
    setSaving(true); setFeedback(null)
    commerce.paymentTerms.update(term.id, { active: !term.active })
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('payment_terms.saved') }))
      .catch(() => setFeedback({ type: 'err', text: t('payment_terms.error') }))
      .finally(() => setSaving(false))
  }

  const remove = (term) => {
    if (!window.confirm(t('payment_terms.confirm_delete', { name: term.name }))) return
    setSaving(true); setFeedback(null)
    commerce.paymentTerms.remove(term.id)
      .then(() => load())
      .then(() => setFeedback({ type: 'ok', text: t('payment_terms.deleted') }))
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('payment_terms.error') }))
      .finally(() => setSaving(false))
  }

  const fractionsSummary = (r) => (r.lines || [])
    .map(l => `${Number(l.percentage)}% · +${l.days_offset}d`).join('  |  ') || '—'

  const columns = [
    { key: 'code', label: t('payment_terms.col_code'), render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.code}</span> },
    { key: 'name', label: t('payment_terms.col_name'), render: r => pickTranslation(r, 'name', lang) },
    { key: 'fractions', label: t('payment_terms.col_fractions'), render: r => (
      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)' }}>{fractionsSummary(r)}</span>
    ) },
    { key: 'active', label: t('payment_terms.col_active'), render: r => (
      <span style={{
        fontSize: 'var(--fs-label)', fontWeight: 600, padding: '2px 8px', borderRadius: 999, fontFamily: MONO,
        background: r.active ? 'var(--ok-bg)' : 'var(--gray-l)', color: r.active ? 'var(--ok)' : 'var(--gray)',
      }}>{r.active ? t('payment_terms.active') : t('payment_terms.inactive')}</span>
    ) },
    ...(canEdit ? [{ key: '_a', label: '', align: 'right', render: r => (
      <span style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
        <button onClick={() => setModal({ mode: 'edit', term: r })} disabled={saving} style={actBtn}>{t('payment_terms.edit')}</button>
        <button onClick={() => toggleActive(r)} disabled={saving} style={actBtn}>{r.active ? t('payment_terms.deactivate') : t('payment_terms.activate')}</button>
        <button onClick={() => remove(r)} disabled={saving} style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }}>{t('payment_terms.delete')}</button>
      </span>) }] : []),
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 900 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('payment_terms.title')}</h1>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('payment_terms.subtitle')}</p>
        </div>
        {canEdit && (
          <button onClick={() => setModal({ mode: 'create' })} style={{ ...primaryBtn, marginLeft: 0 }}>
            <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('payment_terms.new')}
          </button>
        )}
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('payment_terms.loading')}</Center>
        : error ? <Center>{t('payment_terms.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={items} loading={false} empty={t('payment_terms.empty')} />
            </div>
          )}

      {modal && (
        <PaymentTermModal mode={modal.mode} term={modal.term} t={t} saving={saving} setSaving={setSaving}
          onCancel={() => setModal(null)}
          onSaved={(msg) => { setModal(null); load().then(() => setFeedback({ type: 'ok', text: msg })) }}
          onError={(text) => setFeedback({ type: 'err', text })} />
      )}
    </div>
  )
}

function PaymentTermModal({ mode, term, t, saving, setSaving, onCancel, onSaved, onError }) {
  const isEdit = mode === 'edit'
  const [code, setCode] = useState(term?.code || '')
  const [name, setName] = useState(term?.name || '')
  const [translations, setTranslations] = useState(term?.translations || {})
  const [active, setActive] = useState(term?.active ?? true)
  const [lines, setLines] = useState(
    (term?.lines || []).map(l => ({ percentage: String(l.percentage), days_offset: String(l.days_offset), position: l.position }))
  )
  const invalid = !code.trim() || !name.trim()
  const total = lines.reduce((s, l) => s + (parseFloat(l.percentage) || 0), 0)
  const totalOk = lines.length === 0 || Math.abs(total - 100) < 0.005

  const setLine = (i, k, v) => setLines(prev => prev.map((l, idx) => idx === i ? { ...l, [k]: v } : l))
  const addLine = () => setLines(prev => [...prev, { percentage: '', days_offset: '0', position: prev.length }])
  const removeLine = (i) => setLines(prev => prev.filter((_, idx) => idx !== i).map((l, idx) => ({ ...l, position: idx })))

  const submit = () => {
    if (invalid) { onError(t('payment_terms.required')); return }
    setSaving(true)
    const payload = {
      code: code.trim(), name: name.trim(), translations, active,
      lines: lines.map((l, idx) => ({
        percentage: l.percentage === '' ? '0' : l.percentage,
        days_offset: l.days_offset === '' ? 0 : parseInt(l.days_offset, 10),
        position: idx,
      })),
    }
    const req = isEdit ? commerce.paymentTerms.update(term.id, payload) : commerce.paymentTerms.create(payload)
    req
      .then(() => onSaved(isEdit ? t('payment_terms.saved') : t('payment_terms.created')))
      .catch(e => onError(
        e?.response?.data?.lines?.[0] || e?.response?.data?.lines
        || e?.response?.data?.code?.[0] || e?.response?.data?.detail || t('payment_terms.error')))
      .finally(() => setSaving(false))
  }

  return (
    <Modal title={isEdit ? t('payment_terms.edit_title') : t('payment_terms.new_title')}
      cancelLabel={t('payment_terms.cancel')} confirmLabel={isEdit ? t('payment_terms.save') : t('payment_terms.create')}
      onCancel={onCancel} onConfirm={submit} confirmDisabled={saving || invalid}>
      <Field label={t('payment_terms.col_code')}>
        <input value={code} onChange={e => setCode(e.target.value)} placeholder="ex: 50-50" style={{ ...selS, width: '100%' }} />
      </Field>
      <TranslatableField label={t('payment_terms.col_name')} field="name" value={name} onChange={setName}
        translations={translations} onTranslationsChange={setTranslations} />

      <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
          {t('payment_terms.fractions')}
        </label>
        <button onClick={addLine} style={{ ...actBtn }}>
          <i className="ti ti-plus" style={{ fontSize: 12 }} /> {t('payment_terms.add_fraction')}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 6, marginBottom: 4 }}>
        <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO }}>{t('payment_terms.percentage')}</span>
        <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO }}>{t('payment_terms.days_offset')}</span>
        <span />
      </div>
      {lines.map((l, i) => (
        <div key={i} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 6, marginBottom: 6, alignItems: 'center' }}>
          <input type="text" inputMode="decimal" value={l.percentage} onChange={e => setLine(i, 'percentage', e.target.value)} style={{ ...selS, width: '100%' }} />
          <input type="text" inputMode="numeric" value={l.days_offset} onChange={e => setLine(i, 'days_offset', e.target.value)} style={{ ...selS, width: '100%' }} />
          <button onClick={() => removeLine(i)} style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }} title={t('payment_terms.remove_fraction')}>
            <i className="ti ti-trash" style={{ fontSize: 13 }} />
          </button>
        </div>
      ))}
      {lines.length === 0 && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', margin: '4px 0 10px' }}>{t('payment_terms.no_fractions')}</p>}

      <div style={{
        marginTop: 8, marginBottom: 4, fontFamily: MONO, fontSize: 'var(--fs-body)',
        color: totalOk ? 'var(--ok)' : 'var(--err)', fontWeight: 600,
      }}>
        {t('payment_terms.total_pct')}: {total.toFixed(2)}%
        {!totalOk && ` · ${t('payment_terms.total_must_be_100')}`}
      </div>

      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', marginTop: 8 }}>
        <input type="checkbox" checked={active} onChange={e => setActive(e.target.checked)} /><span>{t('payment_terms.active')}</span>
      </label>
    </Modal>
  )
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
    </div>
  )
}
