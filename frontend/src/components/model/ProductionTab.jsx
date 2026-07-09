import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { productions, commerce } from '../../api/endpoints'
import Table from '../ui/Table'

const MONO = 'IBM Plex Mono, monospace'
const fmtDate = (v) => v ? new Date(v).toLocaleDateString('ca-ES', { dateStyle: 'medium' }) : '—'

// Pas 5B-fix · TRAM 3 — Tab Producció = LOG. Llista les Production del model. L'alta ("Enviar a
// confecció") viu al desplegable Accions; aquí només es gestiona l'ESTAT (confirmar recepció).
export default function ProductionTab({ model, onFeedback, onChanged }) {
  const { t } = useTranslation()
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    productions.list({ model: model.id, ordering: '-requested_at', page_size: 200 })
      .then(r => setList(r.data?.results ?? r.data ?? []))
      .catch(() => setList([]))
      .finally(() => setLoading(false))
  }, [model.id])

  useEffect(() => { load() }, [load])

  const setStatus = async (prod, status) => {
    try {
      await productions.setStatus(prod.id, { status })
      onFeedback({ type: 'ok', text: t('model_sheet.status_changed') })
      load(); onChanged && onChanged()
    } catch (e) {
      onFeedback({ type: 'err', text: e.response?.data?.error || t('model_sheet.action_error') })
    }
  }

  const columns = [
    { key: 'supplier_name', label: t('model_sheet.supplier') },
    { key: 'phase', label: t('model_sheet.phase') },
    { key: 'status', label: t('model_sheet.status'), render: r => <StatusBadge status={r.status} /> },
    { key: 'requested_at', label: t('model_sheet.requested_at'), render: r => fmtDate(r.requested_at) },
    { key: 'expected_at', label: t('model_sheet.expected_at'), render: r => fmtDate(r.expected_at) },
    { key: 'delivered_at', label: t('model_sheet.delivered_at'), render: r => fmtDate(r.delivered_at) },
    {
      key: 'actions', label: '', align: 'right', render: r => (
        <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
          {r.status === 'Requested' && (
            <button style={miniBtn} onClick={() => setStatus(r, 'InProgress')}>{t('model_sheet.mark_inprogress')}</button>
          )}
          {(r.status === 'Requested' || r.status === 'InProgress') && (
            <button style={miniBtn} onClick={() => setStatus(r, 'Delivered')}>{t('model_sheet.mark_delivered')}</button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <CommercialChain modelId={model.id} t={t} />
      <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, margin: '0 0 14px', fontFamily: MONO }}>{t('model_sheet.production_title')}</h2>
      <Table columns={columns} data={list} loading={loading} empty={t('model_sheet.no_productions')} />
    </div>
  )
}

// v2 albarà — traçabilitat de lectura pura: la cadena comanda → encàrrec (WO) → albarà del model.
// Els albarans v2 (composició per model) es recullen via ?model= a les línies; els v1 via WO.
function CommercialChain({ modelId, t }) {
  const [wos, setWos] = useState([])
  const [notes, setNotes] = useState(new Map())
  const [ready, setReady] = useState(false)
  useEffect(() => {
    let alive = true
    Promise.all([
      commerce.workOrders.list({ model: modelId, page_size: 100 }).then(r => r.data?.results ?? r.data ?? []).catch(() => []),
      commerce.deliveryNoteLines.list({ model: modelId, page_size: 500 }).then(r => r.data?.results ?? r.data ?? []).catch(() => []),
    ]).then(([w, lines]) => {
      if (!alive) return
      const m = new Map()
      for (const x of w) if (x.delivery_note_number) m.set(x.delivery_note_number, null)
      for (const l of lines) if (l.dn_number) m.set(l.dn_number, l.dn_status)
      setWos(w); setNotes(m); setReady(true)
    })
    return () => { alive = false }
  }, [modelId])
  if (!ready || (wos.length === 0 && notes.size === 0)) return null
  const orders = [...new Set(wos.map(w => w.order_number).filter(Boolean))]
  return (
    <div style={chainBox}>
      <div style={chainTitle}>{t('model_sheet.trace_title')}</div>
      <ChainRow label={t('model_sheet.trace_orders')}
        value={orders.length ? orders.join(' · ') : t('model_sheet.trace_direct')} />
      <ChainRow label={t('model_sheet.trace_wos')}
        value={wos.length ? wos.map(w => `${w.number} · ${w.kind} · ${w.status}`).join('   ') : '—'} />
      <ChainRow label={t('model_sheet.trace_notes')}
        value={notes.size ? [...notes].map(([n, s]) => s ? `${n} (${s})` : n).join('   ') : '—'} />
    </div>
  )
}
function ChainRow({ label, value }) {
  return (
    <div style={{ display: 'flex', gap: 10, padding: '2px 0', fontSize: 'var(--fs-body)' }}>
      <span style={{ minWidth: 90, color: 'var(--gray)', fontFamily: MONO, textTransform: 'uppercase', fontSize: 'var(--fs-caption)', letterSpacing: '.04em', paddingTop: 2 }}>{label}</span>
      <span style={{ fontFamily: MONO, color: 'var(--text-main)' }}>{value}</span>
    </div>
  )
}
const chainBox = { border: '0.5px solid var(--gray-l)', borderRadius: 10, padding: '10px 14px', marginBottom: 18, background: 'var(--white)' }
const chainTitle = { fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 500, textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: 6 }

const STATUS_COLORS = { Requested: 'var(--gold)', InProgress: '#2a5a8a', Delivered: '#3b6d11' }
function StatusBadge({ status }) {
  return <span style={{ fontSize: 'var(--fs-body)', fontWeight: 600, color: STATUS_COLORS[status] || 'var(--gray)', fontFamily: MONO }}>{status}</span>
}
const miniBtn = {
  fontFamily: MONO, fontSize: 'var(--fs-body)', padding: '3px 8px', borderRadius: 4, cursor: 'pointer',
  background: 'var(--white)', color: 'var(--text-main)', border: '0.5px solid var(--gray-l)',
}
