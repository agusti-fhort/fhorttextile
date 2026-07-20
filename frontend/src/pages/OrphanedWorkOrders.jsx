import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { commerce } from '../api/endpoints'
import Center from '../components/ui/Center'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'

// Mòdul Comercial — D6 · Informe d'ENCÀRRECS ORFES (WO desassignats d'una línia de comanda):
// pendents de reassignar. E5 — acció "Reassignar" (reattach) per fila: picker de línies candidates
// (comandes OPEN del mateix client amb qty lliure) → re-adopta el WO orfe. Font: work-orders/orphaned/.
const MONO = 'IBM Plex Mono, monospace'
const STATUS_VARIANT = { OPEN: 'gold', CLOSED: 'gray' }
const actBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const primaryBtn = {
  ...actBtn, borderColor: 'var(--gold)', color: 'var(--gold)',
}
const overlay = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
  alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
}
const modalBox = {
  background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 12,
  padding: 20, width: 'min(560px, 100%)', maxHeight: '80vh', overflowY: 'auto',
}

export default function OrphanedWorkOrders() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [items, setItems] = useState([])
  const [feedback, setFeedback] = useState(null)   // { type: 'ok'|'err', text }

  // E5 — reassignació: fila orfe triada + candidates + línia seleccionada.
  const [reattach, setReattach] = useState(null)   // { woId, number, codi } | null
  const [candidates, setCandidates] = useState([])
  const [candLoading, setCandLoading] = useState(false)
  const [selectedLine, setSelectedLine] = useState(null)
  const [busy, setBusy] = useState(false)

  const reload = useCallback(() => {
    setLoading(true)
    return commerce.workOrders.orphaned()
      .then(res => setItems(res.data?.orphaned || []))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { reload() }, [reload])

  const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString(i18n.language || 'ca',
    { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—'

  const openReattach = (r) => {
    setReattach({ woId: r.id, number: r.number, codi: r.model?.codi_intern || r.number })
    setSelectedLine(null)
    setCandidates([])
    setCandLoading(true)
    commerce.workOrders.reattachCandidates(r.id)
      .then(res => setCandidates(res.data?.candidates || []))
      .catch(() => setCandidates([]))
      .finally(() => setCandLoading(false))
  }

  const doReattach = () => {
    if (!reattach || !selectedLine) return
    setBusy(true)
    commerce.workOrders.reattach(reattach.woId, { order_line_id: selectedLine })
      .then(() => { setReattach(null); return reload() })
      .then(() => setFeedback({ type: 'ok', text: t('orphans.reattach_done') }))
      .catch(err => setFeedback({ type: 'err', text: err?.response?.data?.detail || t('orphans.reattach_error') }))
      .finally(() => setBusy(false))
  }

  const columns = [
    { key: 'date', label: t('orphans.col_date'),
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{fmtDate(r.created_at)}</span> },
    { key: 'wo', label: t('orphans.col_wo'),
      render: r => <span style={{ fontFamily: MONO, fontWeight: 600 }}>{r.number}</span> },
    { key: 'model', label: t('orphans.col_model'),
      render: r => <span style={{ fontFamily: MONO, color: 'var(--gold)' }}>{r.model?.codi_intern || '—'}</span> },
    { key: 'customer', label: t('orphans.col_customer'), render: r => r.customer || '—' },
    { key: 'order', label: t('orphans.col_order'),
      render: r => <span style={{ fontFamily: MONO }}>{r.order?.document_number || '—'}</span> },
    { key: 'total', label: t('orphans.col_total'), align: 'right',
      render: r => <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{r.order?.total ?? '—'}</span> },
    { key: 'status', label: t('orphans.col_status'),
      render: r => <Badge variant={STATUS_VARIANT[r.status] || 'gray'}>{t(`workorders.status_${r.status}`, r.status)}</Badge> },
    { key: '_a', label: '', align: 'right', render: r => (
      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
        {/* Reassignar només si el WO és OPEN (guard del reattach: un CLOSED no es re-adopta). */}
        {r.status === 'OPEN' && (
          <button onClick={() => openReattach(r)} style={primaryBtn} title={t('orphans.reattach')}>
            <i className="ti ti-link" style={{ fontSize: 13, marginRight: 4 }} />{t('orphans.reattach')}
          </button>
        )}
        {r.order && (
          <button onClick={() => navigate(`/comercial/comandes/${r.order.id}`)} style={actBtn}>{t('orphans.open_order')}</button>
        )}
      </div>
    ) },
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1000 }}>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('orphans.title')}</h1>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('orphans.subtitle')}</p>
      </div>
      {feedback && (
        <p style={{ fontSize: 'var(--fs-body)', marginBottom: 12,
          color: feedback.type === 'ok' ? 'var(--gold)' : 'var(--grana)' }}>{feedback.text}</p>
      )}
      {loading ? <Center>{t('orphans.loading')}</Center>
        : error ? <Center>{t('orphans.error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={items} loading={false} empty={t('orphans.empty')} />
            </div>
          )}

      {/* Modal — reassignar (reattach) el WO orfe a una línia de comanda nova */}
      {reattach && (
        <div onClick={() => !busy && setReattach(null)} style={overlay}>
          <div onClick={e => e.stopPropagation()} style={modalBox}>
            <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, fontFamily: MONO, marginBottom: 6 }}>
              {t('orphans.reattach_title')}
            </h2>
            <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 14 }}>
              {t('orphans.reattach_help', { codi: reattach.codi })}
            </p>
            {candLoading ? <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('orphans.reattach_loading')}</p>
              : candidates.length === 0
                ? <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{t('orphans.reattach_empty')}</p>
                : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 14 }}>
                    {candidates.map(c => {
                      const sel = selectedLine === c.id
                      return (
                        <div key={c.id} onClick={() => setSelectedLine(c.id)} style={{
                          border: `0.5px solid ${sel ? 'var(--gold)' : 'var(--gray-l)'}`, borderRadius: 8,
                          padding: '8px 12px', cursor: 'pointer', display: 'flex', justifyContent: 'space-between',
                          alignItems: 'center', gap: 10,
                        }}>
                          <div style={{ minWidth: 0 }}>
                            <span style={{ fontFamily: MONO, fontWeight: 600 }}>{c.order_number}</span>
                            <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginLeft: 8 }}>{c.description}</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap' }}>
                            <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                              {c.qty_allocated}/{c.quantity}
                            </span>
                            {sel && <i className="ti ti-check" style={{ fontSize: 14, color: 'var(--gold)' }} />}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
              <button onClick={() => setReattach(null)} disabled={busy} style={actBtn}>{t('common.cancel')}</button>
              <button onClick={doReattach} disabled={busy || !selectedLine} style={primaryBtn}>{t('orphans.reattach_confirm')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
