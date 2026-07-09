import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Badge from '../components/ui/Badge'
import { selS, primaryBtn } from '../components/ui/buttons'
import { DNStatusBadge } from './DeliveryNotes'

// Mòdul Comercial — v2 · fitxa/composició d'albarà. Es compon per MODEL des de la safata
// d'albaranables del client (tasques Done + extres + despeses + deduccions, seleccionats per check).
// Blocs per model amb capçalera i subtotal; l'ull commuta la visibilitat (les línies amagades no
// compten al total ni surten al PDF). Cicle DRAFT→ISSUED (congela)→INVOICED (presentat al client).
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

// Agrupa les línies per model (les MANUAL/sense model van a un bloc "general" final).
function groupByModel(lines) {
  const blocks = new Map()
  for (const l of lines) {
    const key = l.model ?? '__general__'
    if (!blocks.has(key)) blocks.set(key, { model: l.model, header: l, lines: [] })
    blocks.get(key).lines.push(l)
  }
  return [...blocks.values()]
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
  const [edits, setEdits] = useState({})          // lineId → {unit_price, description, quantity}
  const [confirmIssue, setConfirmIssue] = useState(false)
  // Safata d'albaranables (afegir ítems al DRAFT)
  const [trayOpen, setTrayOpen] = useState(false)
  const [tray, setTray] = useState(null)          // {groups:[…]}
  const [trayBusy, setTrayBusy] = useState(false)
  const [picked, setPicked] = useState(() => new Set())   // "kind:id"

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
  const isIssued = dn?.status === 'ISSUED'
  const editable = isDraft && canConfigure

  const editVal = (line, field) => {
    const e = edits[line.id]
    if (e && e[field] !== undefined) return e[field]
    if (field === 'unit_price') return String(line.unit_price ?? '')
    if (field === 'quantity') return String(line.quantity ?? '')
    return line.description ?? ''
  }
  const setEdit = (lineId, field, value) =>
    setEdits(prev => ({ ...prev, [lineId]: { ...prev[lineId], [field]: value } }))

  const saveLine = (line) => {
    const e = edits[line.id]
    if (!e) return
    const payload = {}
    if (e.unit_price !== undefined && e.unit_price !== String(line.unit_price ?? '')) payload.unit_price = e.unit_price === '' ? '0' : e.unit_price
    if (e.quantity !== undefined && e.quantity !== String(line.quantity ?? '')) payload.quantity = e.quantity === '' ? '0' : e.quantity
    if (e.description !== undefined && e.description !== (line.description ?? '')) payload.description = e.description
    if (Object.keys(payload).length === 0) return
    setBusy(true); setFeedback(null)
    commerce.deliveryNoteLines.update(line.id, payload)
      .then(reload).then(() => setFeedback({ type: 'ok', text: t('deliverynotes.line_saved') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.line_error') }))
      .finally(() => setBusy(false))
  }

  const toggleVisible = (line) => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNoteLines.update(line.id, { visible: !line.visible })
      .then(reload)
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.line_error') }))
      .finally(() => setBusy(false))
  }

  const removeLine = (line) => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNoteLines.remove(line.id)
      .then(reload)
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.line_error') }))
      .finally(() => setBusy(false))
  }

  const addComment = () => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNoteLines.create({ delivery_note: dn.id, description: t('deliverynotes.comment_placeholder'), quantity: 0, unit_price: 0 })
      .then(reload)
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.line_error') }))
      .finally(() => setBusy(false))
  }

  // ── Safata ──
  const openTray = () => {
    setTrayOpen(true); setPicked(new Set()); setTray(null)
    commerce.deliveryNotes.billable({ customer: dn.customer })
      .then(res => setTray(res.data))
      .catch(() => setTray({ groups: [] }))
  }
  const itemKey = (it) => `${it.kind}:${it.model_task_id ?? it.adjustment_id ?? it.expense_id}`
  const togglePick = (it) => setPicked(prev => {
    const n = new Set(prev); const k = itemKey(it); n.has(k) ? n.delete(k) : n.add(k); return n
  })
  const addPicked = () => {
    const items = []
    for (const g of (tray?.groups || [])) for (const it of g.items) {
      if (picked.has(itemKey(it))) {
        const src = it.kind === 'TASK' ? { model_task_id: it.model_task_id }
          : it.kind === 'EXPENSE' ? { expense_id: it.expense_id } : { adjustment_id: it.adjustment_id }
        items.push({ kind: it.kind, ...src })
      }
    }
    if (items.length === 0) { setTrayOpen(false); return }
    setTrayBusy(true); setFeedback(null)
    commerce.deliveryNotes.addLines(dn.id, { items })
      .then(reload)
      .then(() => { setTrayOpen(false); setFeedback({ type: 'ok', text: t('deliverynotes.tray_added', { n: items.length }) }) })
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.tray_error') }))
      .finally(() => setTrayBusy(false))
  }

  const doIssue = () => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNotes.issue(id)
      .then(() => { setConfirmIssue(false); return reload() })
      .then(() => setFeedback({ type: 'ok', text: t('deliverynotes.issued_ok') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.issue_error') }))
      .finally(() => setBusy(false))
  }

  const doMarkInvoiced = () => {
    setBusy(true); setFeedback(null)
    commerce.deliveryNotes.markInvoiced(id)
      .then(reload).then(() => setFeedback({ type: 'ok', text: t('deliverynotes.invoiced_ok') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('deliverynotes.invoice_error') }))
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

  const blocks = useMemo(() => groupByModel(dn?.lines || []), [dn])

  if (loading) return <Center>{t('deliverynotes.loading')}</Center>
  if (error || !dn) return <Center>{t('deliverynotes.error')}</Center>

  const lines = dn.lines || []
  const visibleCount = lines.filter(l => l.visible).length

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <button onClick={() => navigate('/comercial/albarans')} style={{ ...smallBtn, marginBottom: 12 }}>
        <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> {t('deliverynotes.back')}
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, fontFamily: MONO }}>{dn.document_number}</h1>
        <DNStatusBadge status={dn.status} t={t} />
      </div>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 16 }}>
        {dn.customer_nom}
        {dn.invoiced_at && <> · {t('deliverynotes.invoiced_on')} {String(dn.invoiced_at).slice(0, 10)}</>}
      </p>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
        <button onClick={doPdf} style={smallBtn}>
          <i className="ti ti-file-download" style={{ fontSize: 14 }} /> {t('deliverynotes.download_pdf')}
        </button>
        {editable && (
          <button onClick={openTray} disabled={busy} style={smallBtn}>
            <i className="ti ti-inbox" style={{ fontSize: 14, marginRight: 4 }} />{t('deliverynotes.tray_action')}
          </button>
        )}
        {editable && (
          <button onClick={addComment} disabled={busy} style={smallBtn}>
            <i className="ti ti-message-plus" style={{ fontSize: 14, marginRight: 4 }} />{t('deliverynotes.add_comment')}
          </button>
        )}
        {editable && (
          <button onClick={() => setConfirmIssue(true)} disabled={busy || visibleCount === 0} style={{ ...primaryBtn }}>
            <i className="ti ti-send" style={{ fontSize: 14, marginRight: 6 }} />{t('deliverynotes.issue_action')}
          </button>
        )}
        {isIssued && canConfigure && (
          <button onClick={doMarkInvoiced} disabled={busy} style={{ ...primaryBtn }}>
            <i className="ti ti-checkbox" style={{ fontSize: 14, marginRight: 6 }} />{t('deliverynotes.mark_invoiced')}
          </button>
        )}
        {editable && (
          <button onClick={doDelete} disabled={busy} style={smallBtn} title={t('deliverynotes.delete')}>
            <i className="ti ti-trash" style={{ fontSize: 13 }} />
          </button>
        )}
      </div>

      {/* Blocs per model */}
      {lines.length === 0 && (
        <div style={{ ...sectionTitle }}>{t('deliverynotes.empty_lines')}</div>
      )}
      {blocks.map(block => {
        const subtotal = block.lines.filter(l => l.visible).reduce((s, l) => s + Number(l.line_total ?? 0), 0)
        const dates = block.lines.map(l => l.task_finished_at).filter(Boolean).sort()
        const deliveredAt = dates.length ? dates[dates.length - 1].slice(0, 10) : null
        const h = block.header
        const showClient = h.model_codi_client && h.model_codi_client !== h.model_intern
        return (
          <div key={block.model ?? 'general'} style={{ marginBottom: 14 }}>
            {/* Capçalera de bloc-model */}
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap', marginBottom: 4 }}>
              {block.model ? (
                <>
                  <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 'var(--fs-body)' }}>{h.model_intern}</span>
                  {showClient && <span style={{ fontFamily: MONO, color: 'var(--gold)', fontSize: 'var(--fs-label)' }}>· {h.model_codi_client}</span>}
                  {h.model_nom && <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{h.model_nom}</span>}
                  {(h.model_collection || h.model_temporada || h.model_any) && (
                    <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-label)' }}>
                      {[h.model_collection, h.model_temporada, h.model_any].filter(Boolean).join(' · ')}
                    </span>
                  )}
                  {deliveredAt && <span style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-label)' }}>· {t('deliverynotes.delivered_at')} {deliveredAt}</span>}
                </>
              ) : (
                <span style={{ fontFamily: MONO, fontWeight: 600, fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('deliverynotes.general_block')}</span>
              )}
            </div>

            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 10, overflow: 'hidden' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', textAlign: 'left' }}>
                    <th style={{ padding: '6px 10px' }}>{t('deliverynotes.line_kind')}</th>
                    <th style={{ padding: '6px 10px' }}>{t('deliverynotes.line_desc')}</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('deliverynotes.line_qty')}</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('deliverynotes.line_price')}</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('deliverynotes.line_total')}</th>
                    <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('deliverynotes.line_time')}</th>
                    <th style={{ padding: '6px 10px', width: 60 }} />
                  </tr>
                </thead>
                <tbody>
                  {block.lines.map(l => {
                    const neg = Number(l.line_total ?? 0) < 0
                    const faded = !l.visible
                    return (
                      <tr key={l.id} style={{ opacity: faded ? 0.4 : 1 }}>
                        <td style={cell}><Badge variant={KIND_VARIANT[l.line_kind] || 'gray'}>{t(`deliverynotes.kind_${l.line_kind}`)}</Badge></td>
                        <td style={cell}>
                          {editable ? (
                            <input value={editVal(l, 'description')} disabled={busy}
                              onChange={e => setEdit(l.id, 'description', e.target.value)}
                              onBlur={() => saveLine(l)} style={{ ...inp, width: '100%' }} />
                          ) : (l.description || l.product_name || '—')}
                        </td>
                        <td style={{ ...cell, textAlign: 'right' }}>
                          {editable ? (
                            <input type="number" step="0.01" value={editVal(l, 'quantity')} disabled={busy}
                              onChange={e => setEdit(l.id, 'quantity', e.target.value)}
                              onBlur={() => saveLine(l)} style={{ ...inp, width: 70, textAlign: 'right' }} />
                          ) : <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{Number(l.quantity ?? 0)}</span>}
                        </td>
                        <td style={{ ...cell, textAlign: 'right' }}>
                          {editable ? (
                            <input type="number" step="0.01" value={editVal(l, 'unit_price')} disabled={busy}
                              onChange={e => setEdit(l.id, 'unit_price', e.target.value)}
                              onBlur={() => saveLine(l)} style={{ ...inp, width: 100, textAlign: 'right' }} />
                          ) : <span style={{ fontFamily: MONO }}>{money(l.unit_price)}</span>}
                        </td>
                        <td style={{ ...cell, textAlign: 'right', fontFamily: MONO, color: neg ? 'var(--err)' : 'inherit' }}>{money(l.line_total)}</td>
                        <td style={{ ...cell, textAlign: 'right', fontFamily: MONO, color: 'var(--text-muted)', fontSize: 'var(--fs-label)' }}>
                          {l.internal_minutes != null ? `${Number(l.internal_minutes)}′` : '—'}
                        </td>
                        <td style={{ ...cell, textAlign: 'right', whiteSpace: 'nowrap' }}>
                          {editable && (
                            <>
                              <button onClick={() => toggleVisible(l)} disabled={busy} style={{ ...smallBtn, padding: '3px 6px', border: 'none' }}
                                title={l.visible ? t('deliverynotes.hide') : t('deliverynotes.show')}>
                                <i className={`ti ${l.visible ? 'ti-eye' : 'ti-eye-off'}`} style={{ fontSize: 15 }} />
                              </button>
                              <button onClick={() => removeLine(l)} disabled={busy} style={{ ...smallBtn, padding: '3px 6px', border: 'none' }}
                                title={t('deliverynotes.remove_line')}>
                                <i className="ti ti-x" style={{ fontSize: 14 }} />
                              </button>
                            </>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {/* Subtotal per model */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4, fontSize: 'var(--fs-label)' }}>
              <span style={{ color: 'var(--text-muted)' }}>{t('deliverynotes.model_subtotal')}</span>
              <span style={{ fontFamily: MONO, fontWeight: 600, minWidth: 90, textAlign: 'right' }}>{money(subtotal)}</span>
            </div>
          </div>
        )
      })}

      {/* Totals del document */}
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

      {/* Safata d'albaranables */}
      {trayOpen && (
        <div onClick={() => !trayBusy && setTrayOpen(false)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--white)', borderRadius: 12, padding: '1.2rem 1.4rem',
            maxWidth: 720, width: '100%', maxHeight: '85vh', overflowY: 'auto', border: '0.5px solid var(--gray-l)',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>
              {t('deliverynotes.tray_title')}
            </h2>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 14 }}>
              {t('deliverynotes.tray_hint')}
            </p>
            {!tray ? <Center>{t('deliverynotes.loading')}</Center>
              : (tray.groups || []).length === 0 ? <div style={{ color: 'var(--text-muted)', padding: '10px 0' }}>{t('deliverynotes.tray_empty')}</div>
                : (tray.groups.map(g => (
                  <div key={g.model.id ?? 'general'} style={{ marginBottom: 12 }}>
                    <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: 'var(--fs-body)', marginBottom: 4 }}>
                      {g.model.codi_intern || t('deliverynotes.general_block')}
                      {g.model.nom_prenda && <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> · {g.model.nom_prenda}</span>}
                    </div>
                    {g.items.map(it => {
                      const k = itemKey(it)
                      return (
                        <label key={k} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 6px', cursor: 'pointer', borderRadius: 6 }}>
                          <input type="checkbox" checked={picked.has(k)} onChange={() => togglePick(it)} />
                          <Badge variant={KIND_VARIANT[it.kind] || 'gray'}>{t(`deliverynotes.kind_${it.kind}`)}</Badge>
                          <span style={{ flex: 1, fontSize: 'var(--fs-body)' }}>{it.description}</span>
                          <span style={{ fontFamily: MONO, color: 'var(--text-muted)', fontSize: 'var(--fs-label)' }}>{money(it.proposed_price)}</span>
                        </label>
                      )
                    })}
                  </div>
                )))}
            <div style={{ display: 'flex', gap: 8, marginTop: 12, position: 'sticky', bottom: 0, background: 'var(--white)', paddingTop: 8 }}>
              <button onClick={addPicked} disabled={trayBusy || picked.size === 0} style={{ ...primaryBtn }}>
                {t('deliverynotes.tray_add', { n: picked.size })}
              </button>
              <button onClick={() => setTrayOpen(false)} disabled={trayBusy} style={smallBtn}>{t('deliverynotes.issue_cancel')}</button>
            </div>
          </div>
        </div>
      )}

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
