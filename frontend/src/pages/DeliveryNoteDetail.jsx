import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Badge from '../components/ui/Badge'
import { selS, primaryBtn } from '../components/ui/buttons'
import { DNStatusBadge } from './DeliveryNotes'

// Mòdul Comercial — B4c · fitxa d'albarà. Neix DRAFT amb línies proposades: el comercial edita
// preu/descripció (les FK de traçabilitat són read-only); "Emetre" congela. PDF sense venciments.
const MONO = 'IBM Plex Mono, monospace'
const smallBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const inp = { ...selS, minWidth: 0 }
const cell = { padding: '6px 10px', fontSize: 'var(--fs-body)', borderTop: '0.5px solid var(--gray-l)' }
const sectionTitle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 500,
  textTransform: 'uppercase', letterSpacing: '0.04em', margin: '18px 0 8px',
}
const money = (v) => `${Number(v ?? 0).toFixed(2)} €`
const KIND_VARIANT = { TASK: 'ok', EXTRA: 'gold', DEDUCTION: 'err', EXPENSE: 'warn', MANUAL: 'gray' }

function downloadBlob(blob, filename) {
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  document.body.appendChild(link); link.click(); document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}
function filenameFromHeaders(res, fallback) {
  const cd = res?.headers?.['content-disposition'] || ''
  const m = /filename="?([^"]+)"?/.exec(cd)
  return (m && m[1]) || fallback
}

export default function DeliveryNoteDetail() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canConfigure = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [dn, setDn] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  const [edits, setEdits] = useState({})          // lineId → {unit_price, description}
  const [confirmIssue, setConfirmIssue] = useState(false)

  const reload = useCallback(() => commerce.deliveryNotes.get(id)
    .then(res => { setDn(res.data); setEdits({}) }).catch(() => setError(true)), [id])

  useEffect(() => {
    let alive = true
    commerce.deliveryNotes.get(id)
      .then(res => { if (alive) setDn(res.data) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [id])

  const isDraft = dn?.status === 'DRAFT'
  const editable = isDraft && canConfigure

  const editVal = (line, field) => {
    const e = edits[line.id]
    if (e && e[field] !== undefined) return e[field]
    return field === 'unit_price' ? String(line.unit_price ?? '') : (line.description ?? '')
  }
  const setEdit = (lineId, field, value) =>
    setEdits(prev => ({ ...prev, [lineId]: { ...prev[lineId], [field]: value } }))

  const saveLine = (line) => {
    const e = edits[line.id]
    if (!e) return
    const payload = {}
    if (e.unit_price !== undefined && e.unit_price !== String(line.unit_price ?? '')) payload.unit_price = e.unit_price === '' ? '0' : e.unit_price
    if (e.description !== undefined && e.description !== (line.description ?? '')) payload.description = e.description
    if (Object.keys(payload).length === 0) return
    setBusy(true); setFeedback(null)
    commerce.deliveryNoteLines.update(line.id, payload)
      .then(reload).then(() => setFeedback({ type: 'ok', text: t('deliverynotes.line_saved') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.line_error') }))
      .finally(() => setBusy(false))
  }

  const doIssue = () => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNotes.issue(id)
      .then(() => { setConfirmIssue(false); return reload() })
      .then(() => setFeedback({ type: 'ok', text: t('deliverynotes.issued_ok') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.issue_error') }))
      .finally(() => setBusy(false))
  }

  const doPdf = () => {
    commerce.deliveryNotes.pdf(id)
      .then(res => downloadBlob(res.data, filenameFromHeaders(res, `${dn?.document_number || 'albara'}.pdf`)))
      .catch(() => setFeedback({ type: 'err', text: t('deliverynotes.pdf_error') }))
  }

  const doDelete = () => {
    if (!window.confirm(t('deliverynotes.delete_confirm'))) return
    setBusy(true)
    commerce.deliveryNotes.remove(id)
      .then(() => navigate('/comercial/albarans'))
      .catch(err => { setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.delete_error') }); setBusy(false) })
  }

  if (loading) return <Center>{t('deliverynotes.loading')}</Center>
  if (error || !dn) return <Center>{t('deliverynotes.error')}</Center>

  const lines = dn.lines || []
  const wosIncluded = dn.work_orders_included || []

  return (
    <div style={{ minWidth: 0, maxWidth: 900 }}>
      <button onClick={() => navigate('/comercial/albarans')} style={{ ...smallBtn, marginBottom: 12 }}>
        <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> {t('deliverynotes.back')}
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, fontFamily: MONO }}>{dn.document_number}</h1>
        <DNStatusBadge status={dn.status} t={t} />
      </div>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 16 }}>
        {dn.customer_nom}
        {wosIncluded.length > 0 && <> · {t('deliverynotes.included')}: {wosIncluded.map(w => w.number).join(', ')}</>}
      </p>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <button onClick={doPdf} style={smallBtn}>
          <i className="ti ti-file-download" style={{ fontSize: 14 }} /> {t('deliverynotes.download_pdf')}
        </button>
        {editable && (
          <button onClick={() => setConfirmIssue(true)} disabled={busy || lines.length === 0} style={{ ...primaryBtn }}>
            <i className="ti ti-send" style={{ fontSize: 14, marginRight: 6 }} />{t('deliverynotes.issue_action')}
          </button>
        )}
        {editable && (
          <button onClick={doDelete} disabled={busy} style={smallBtn} title={t('deliverynotes.delete')}>
            <i className="ti ti-trash" style={{ fontSize: 13 }} />
          </button>
        )}
      </div>

      {/* Línies */}
      <div style={sectionTitle}>{t('deliverynotes.lines')}</div>
      <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 10, overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', textAlign: 'left' }}>
              <th style={{ padding: '6px 10px' }}>{t('deliverynotes.line_kind')}</th>
              <th style={{ padding: '6px 10px' }}>{t('deliverynotes.line_desc')}</th>
              <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('deliverynotes.line_qty')}</th>
              <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('deliverynotes.line_price')}</th>
              <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('deliverynotes.line_total')}</th>
            </tr>
          </thead>
          <tbody>
            {lines.map(l => {
              const neg = Number(l.line_total ?? 0) < 0
              return (
                <tr key={l.id}>
                  <td style={cell}><Badge variant={KIND_VARIANT[l.line_kind] || 'gray'}>{t(`deliverynotes.kind_${l.line_kind}`)}</Badge></td>
                  <td style={cell}>
                    {editable ? (
                      <input value={editVal(l, 'description')} disabled={busy}
                        onChange={e => setEdit(l.id, 'description', e.target.value)}
                        onBlur={() => saveLine(l)} style={{ ...inp, width: '100%' }} />
                    ) : (l.description || l.product_name || '—')}
                  </td>
                  <td style={{ ...cell, textAlign: 'right', fontFamily: MONO, color: 'var(--text-muted)' }}>{Number(l.quantity ?? 0)}</td>
                  <td style={{ ...cell, textAlign: 'right' }}>
                    {editable ? (
                      <input type="number" step="0.01" value={editVal(l, 'unit_price')} disabled={busy}
                        onChange={e => setEdit(l.id, 'unit_price', e.target.value)}
                        onBlur={() => saveLine(l)} style={{ ...inp, width: 100, textAlign: 'right' }} />
                    ) : <span style={{ fontFamily: MONO }}>{money(l.unit_price)}</span>}
                  </td>
                  <td style={{ ...cell, textAlign: 'right', fontFamily: MONO, color: neg ? 'var(--err)' : 'inherit' }}>{money(l.line_total)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Totals */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 12 }}>
        <table style={{ borderCollapse: 'collapse', minWidth: 260 }}>
          <tbody>
            <tr><td style={{ padding: '3px 10px', color: 'var(--text-muted)' }}>{t('deliverynotes.subtotal')}</td>
              <td style={{ padding: '3px 10px', textAlign: 'right', fontFamily: MONO }}>{money(dn.subtotal)}</td></tr>
            <tr><td style={{ padding: '3px 10px', color: 'var(--text-muted)' }}>{t('deliverynotes.tax')}</td>
              <td style={{ padding: '3px 10px', textAlign: 'right', fontFamily: MONO }}>{money(dn.tax_amount)}</td></tr>
            <tr style={{ borderTop: '0.5px solid var(--gray-l)' }}>
              <td style={{ padding: '5px 10px', fontWeight: 600 }}>{t('deliverynotes.total')}</td>
              <td style={{ padding: '5px 10px', textAlign: 'right', fontFamily: MONO, fontWeight: 600 }}>{money(dn.total)}</td></tr>
          </tbody>
        </table>
      </div>

      {/* Confirmació d'emissió */}
      {confirmIssue && (
        <div onClick={() => setConfirmIssue(false)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--white)', borderRadius: 12, padding: '1.2rem 1.4rem',
            maxWidth: 460, width: '100%', border: '0.5px solid var(--gray-l)',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 10, fontFamily: MONO }}>
              {t('deliverynotes.issue_title')}
            </h2>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 16 }}>
              {t('deliverynotes.issue_warning')}
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={doIssue} disabled={busy} style={{ ...primaryBtn }}>{t('deliverynotes.issue_confirm')}</button>
              <button onClick={() => setConfirmIssue(false)} disabled={busy} style={smallBtn}>{t('deliverynotes.issue_cancel')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
