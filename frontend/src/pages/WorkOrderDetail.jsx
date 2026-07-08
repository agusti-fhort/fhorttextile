import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams, useNavigate } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { commerce, suppliers as suppliersApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Badge from '../components/ui/Badge'
import { selS, primaryBtn } from '../components/ui/buttons'
import { WOStatusBadge, WOKindBadge } from './WorkOrders'
import { formatMinutes } from '../utils/format'

// Mòdul Comercial — B4b · fitxa d'encàrrec. El TÈCNIC tanca (feina feta, bloqueja només
// InProgress/Paused); el COMERCIAL revisa després en preu de venda (bloc Revisió, si CLOSED).
// A més: bloc Despeses (línies externes amb proveïdor i marge).
const MONO = 'IBM Plex Mono, monospace'
const smallBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '4px 9px', fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)',
}
const inp = { ...selS, minWidth: 0 }
const TASK_STATUS_VARIANT = { Done: 'ok', InProgress: 'gold', Paused: 'warn', Pending: 'gray' }
const sectionTitle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 500,
  textTransform: 'uppercase', letterSpacing: '0.04em', margin: '18px 0 8px',
}
const cell = { padding: '6px 10px', fontSize: 'var(--fs-body)', borderTop: '0.5px solid var(--gray-l)' }
const money = (v) => `${Number(v ?? 0).toFixed(2)} €`
const rows = (res) => res.data?.results ?? (Array.isArray(res.data) ? res.data : [])

export default function WorkOrderDetail() {
  const { t } = useTranslation()
  const { id } = useParams()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canClose = !!me?.capabilities?.includes('define_tasks')
  const canConfigure = !!me?.capabilities?.includes('configure')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [wo, setWo] = useState(null)
  const [feedback, setFeedback] = useState(null)
  const [busy, setBusy] = useState(false)
  const [modal, setModal] = useState(null)            // resposta estructurada del close

  // Despeses
  const [expenses, setExpenses] = useState([])
  const [products, setProducts] = useState([])
  const [suppliers, setSuppliers] = useState([])
  const [prodSuppliers, setProdSuppliers] = useState([])   // ProductSupplier del producte triat
  const blankExp = { product: '', supplier: '', cost_price: '', sale_price: '', quantity: '1', description: '' }
  const [newExp, setNewExp] = useState(blankExp)

  // Revisió comercial: model_task_id → {kind, amount}
  const [review, setReview] = useState({})

  const reload = useCallback(() => commerce.workOrders.get(id)
    .then(res => setWo(res.data)).catch(() => setError(true)), [id])
  const loadExpenses = useCallback(() => commerce.expenses.list({ work_order: id, page_size: 200 })
    .then(rows).then(setExpenses).catch(() => {}), [id])

  useEffect(() => {
    let alive = true
    Promise.all([
      commerce.workOrders.get(id).then(res => res.data),
      commerce.expenses.list({ work_order: id, page_size: 200 }).then(rows).catch(() => []),
      commerce.products.list({ page_size: 500 }).then(rows).catch(() => []),
      suppliersApi.list({ active: true, page_size: 500 }).then(rows).catch(() => []),
    ]).then(([w, ex, ps, sup]) => {
      if (!alive) return
      setWo(w); setExpenses(ex)
      setProducts(ps.filter(p => p.nature === 'EXTERNAL_SERVICE' || p.nature === 'GOODS'))
      setSuppliers(sup)
    }).catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [id])

  // Pre-omplir la revisió amb els adjustments existents (preu ja fixat o marcador del close).
  useEffect(() => {
    if (!wo) return
    const seed = {}
    for (const a of (wo.adjustments || [])) {
      if (a.model_task != null) seed[a.model_task] = { kind: a.kind, amount: String(a.amount ?? '0') }
    }
    for (const tk of (wo.tasks || [])) {
      if (tk.off_recipe && !seed[tk.id]) seed[tk.id] = { kind: 'EXTRA_BILL', amount: '0' }
    }
    setReview(seed)
  }, [wo])

  // En triar producte a la despesa: proposa proveïdor per defecte + cost, i preu de venda.
  const onPickProduct = (pid) => {
    const p = products.find(x => String(x.id) === String(pid))
    setNewExp(e => ({ ...e, product: pid }))
    if (!pid) { setProdSuppliers([]); return }
    commerce.productSuppliers.list({ product: pid, page_size: 200 }).then(rows).then(list => {
      setProdSuppliers(list)
      const def = list.find(s => s.is_default) || list[0]
      const markup = p?.markup_pct ? (1 + Number(p.markup_pct) / 100) : 1
      const sale = p?.base_price != null ? (Number(p.base_price) * markup).toFixed(2) : ''
      setNewExp(e => ({
        ...e, product: pid,
        supplier: def ? String(def.supplier) : e.supplier,
        cost_price: def ? String(def.cost_price) : e.cost_price,
        sale_price: sale || e.sale_price,
      }))
    }).catch(() => setProdSuppliers([]))
  }

  const addExpense = () => {
    setBusy(true); setFeedback(null)
    commerce.expenses.create({ work_order: Number(id), ...newExp })
      .then(() => { setNewExp(blankExp); setProdSuppliers([]); return loadExpenses() })
      .then(() => setFeedback({ type: 'ok', text: t('workorders.exp_saved') }))
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('workorders.exp_error') }))
      .finally(() => setBusy(false))
  }
  const removeExpense = (eid) => {
    setBusy(true)
    commerce.expenses.remove(eid).then(loadExpenses).finally(() => setBusy(false))
  }

  const doClose = (opts = {}) => {
    setBusy(true); setFeedback(null)
    return commerce.workOrders.close(id, opts)
      .then(() => { setModal(null); return reload().then(() => setFeedback({ type: 'ok', text: t('workorders.closed_ok') })) })
      .catch(err => {
        const data = err?.response?.data
        if (data && (data.blockers || data.pending_proposals)) setModal(data)
        else setFeedback({ type: 'err', text: t('workorders.close_error') })
      })
      .finally(() => setBusy(false))
  }

  const saveReview = () => {
    const items = Object.entries(review).map(([mt, v]) => ({
      model_task_id: Number(mt), kind: v.kind, amount: v.amount === '' ? '0' : v.amount,
    }))
    setBusy(true); setFeedback(null)
    commerce.workOrders.review(id, { items })
      .then(() => reload()).then(() => setFeedback({ type: 'ok', text: t('workorders.review_saved') }))
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.detail || t('workorders.review_error') }))
      .finally(() => setBusy(false))
  }

  if (loading) return <Center>{t('workorders.loading')}</Center>
  if (error || !wo) return <Center>{t('workorders.error')}</Center>

  const tasks = wo.tasks || []
  const adjustments = wo.adjustments || []
  const isOpen = wo.status === 'OPEN'
  const isClosed = wo.status === 'CLOSED'
  const hardBlockers = modal?.blockers || []
  const pending = modal?.pending_proposals || []
  // Files revisables: extres (tasques off_recipe) + deduccions (adjustments DEDUCTION del close).
  const reviewRows = [
    ...tasks.filter(tk => tk.off_recipe).map(tk => ({ mt: tk.id, label: tk.task_type_name || tk.task_type_code, minutes: tk.minutes, isDeduction: false })),
    ...adjustments.filter(a => a.kind === 'DEDUCTION' && a.model_task != null)
      .map(a => ({ mt: a.model_task, label: a.description || `#${a.model_task}`, minutes: null, isDeduction: true })),
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 900 }}>
      <button onClick={() => navigate('/comercial/encarrecs')} style={{ ...smallBtn, marginBottom: 12 }}>
        <i className="ti ti-arrow-left" style={{ fontSize: 14 }} /> {t('workorders.back')}
      </button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6, flexWrap: 'wrap' }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, fontFamily: MONO }}>{wo.number}</h1>
        <WOKindBadge kind={wo.kind} t={t} />
        <WOStatusBadge status={wo.status} t={t} />
      </div>
      <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 16 }}>
        {wo.customer_nom} · {wo.kind === 'COLLECTOR' ? wo.period : (wo.model_codi || '—')}
      </p>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {canClose && isOpen && (
        <button onClick={() => doClose()} disabled={busy} style={{ ...primaryBtn, marginBottom: 8 }}>
          <i className="ti ti-lock" style={{ fontSize: 14, marginRight: 6 }} /> {t('workorders.close_action')}
        </button>
      )}

      {/* Tasques */}
      <div style={sectionTitle}>{t('workorders.tasks')}</div>
      {tasks.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>{t('workorders.tasks_empty')}</p> : (
        <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '6px 10px' }}>{t('workorders.task_type')}</th>
                <th style={{ padding: '6px 10px' }}>{t('workorders.task_status')}</th>
                <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('workorders.task_minutes')}</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map(tk => (
                <tr key={tk.id} style={{ borderLeft: tk.off_recipe ? '3px solid var(--err)' : '3px solid transparent' }}>
                  <td style={cell}>
                    <span style={{ fontWeight: 500 }}>{tk.task_type_name || tk.task_type_code}</span>
                    {tk.off_recipe && (
                      <span style={{ marginLeft: 8, fontSize: 'var(--fs-label)', color: 'var(--err)' }}>
                        <i className="ti ti-flag" style={{ fontSize: 12, marginRight: 3 }} />{t('workorders.off_recipe')}
                      </span>
                    )}
                  </td>
                  <td style={cell}>
                    <Badge variant={TASK_STATUS_VARIANT[tk.status] || 'gray'}>{t(`workorders.status_task_${tk.status}`, { defaultValue: tk.status })}</Badge>
                  </td>
                  <td style={{ ...cell, textAlign: 'right', fontFamily: MONO, color: 'var(--text-muted)' }}>{formatMinutes(tk.minutes ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Despeses (línies externes) */}
      <div style={sectionTitle}>{t('workorders.expenses')}</div>
      {expenses.length > 0 && (
        <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 10, overflow: 'hidden', marginBottom: 10 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '6px 10px' }}>{t('workorders.exp_product')}</th>
                <th style={{ padding: '6px 10px' }}>{t('workorders.exp_supplier')}</th>
                <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('workorders.exp_cost')}</th>
                <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('workorders.exp_sale')}</th>
                <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('workorders.exp_qty')}</th>
                {canConfigure && <th style={{ padding: '6px 10px' }} />}
              </tr>
            </thead>
            <tbody>
              {expenses.map(ex => (
                <tr key={ex.id}>
                  <td style={cell}>{ex.product_name}</td>
                  <td style={cell}>{ex.supplier_name}</td>
                  <td style={{ ...cell, textAlign: 'right', fontFamily: MONO, color: 'var(--text-muted)' }}>{money(ex.cost_price)}</td>
                  <td style={{ ...cell, textAlign: 'right', fontFamily: MONO }}>{money(ex.sale_price)}</td>
                  <td style={{ ...cell, textAlign: 'right', fontFamily: MONO }}>{Number(ex.quantity ?? 0)}</td>
                  {canConfigure && (
                    <td style={{ ...cell, textAlign: 'right' }}>
                      <button onClick={() => removeExpense(ex.id)} disabled={busy} style={smallBtn} title={t('workorders.exp_remove')}>
                        <i className="ti ti-trash" style={{ fontSize: 13 }} />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {canConfigure && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end', marginBottom: 6 }}>
          <select value={newExp.product} onChange={e => onPickProduct(e.target.value)} style={inp}>
            <option value="">{t('workorders.exp_product')}…</option>
            {products.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select value={newExp.supplier} onChange={e => setNewExp({ ...newExp, supplier: e.target.value })} style={inp}>
            <option value="">{t('workorders.exp_supplier')}…</option>
            {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <input type="number" step="0.01" placeholder={t('workorders.exp_cost')} value={newExp.cost_price}
            onChange={e => setNewExp({ ...newExp, cost_price: e.target.value })} style={{ ...inp, width: 90 }} />
          <input type="number" step="0.01" placeholder={t('workorders.exp_sale')} value={newExp.sale_price}
            onChange={e => setNewExp({ ...newExp, sale_price: e.target.value })} style={{ ...inp, width: 90 }} />
          <input type="number" step="0.01" placeholder={t('workorders.exp_qty')} value={newExp.quantity}
            onChange={e => setNewExp({ ...newExp, quantity: e.target.value })} style={{ ...inp, width: 70 }} />
          <button onClick={addExpense} disabled={busy || !newExp.product || !newExp.supplier} style={{ ...primaryBtn }}>
            <i className="ti ti-plus" style={{ fontSize: 14, marginRight: 4 }} />{t('workorders.exp_add')}
          </button>
        </div>
      )}
      {canConfigure && prodSuppliers.length > 0 && (
        <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 8 }}>
          {t('workorders.exp_suppliers_compare')}: {prodSuppliers.map(s => `${s.supplier_name} ${money(s.cost_price)}${s.is_default ? ' ★' : ''}`).join(' · ')}
        </div>
      )}

      {/* Revisió comercial (preu de venda) — visible si el WO està tancat */}
      {isClosed && reviewRows.length > 0 && (
        <>
          <div style={sectionTitle}>{t('workorders.review')}</div>
          <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 10, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', textAlign: 'left' }}>
                  <th style={{ padding: '6px 10px' }}>{t('workorders.review_item')}</th>
                  <th style={{ padding: '6px 10px' }}>{t('workorders.review_kind')}</th>
                  <th style={{ padding: '6px 10px', textAlign: 'right' }}>{t('workorders.review_amount')}</th>
                </tr>
              </thead>
              <tbody>
                {reviewRows.map(r => {
                  const v = review[r.mt] || { kind: r.isDeduction ? 'DEDUCTION' : 'EXTRA_BILL', amount: '0' }
                  return (
                    <tr key={r.mt}>
                      <td style={cell}>
                        {r.label}
                        {r.minutes != null && <span style={{ marginLeft: 8, fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO }}>{formatMinutes(r.minutes)}</span>}
                      </td>
                      <td style={cell}>
                        {r.isDeduction ? (
                          <Badge variant="gray">{t('workorders.adj_DEDUCTION')}</Badge>
                        ) : (
                          <select value={v.kind} disabled={!canConfigure}
                            onChange={e => setReview({ ...review, [r.mt]: { ...v, kind: e.target.value } })} style={inp}>
                            <option value="EXTRA_BILL">{t('workorders.adj_EXTRA_BILL')}</option>
                            <option value="EXTRA_ABSORB">{t('workorders.adj_EXTRA_ABSORB')}</option>
                          </select>
                        )}
                      </td>
                      <td style={{ ...cell, textAlign: 'right' }}>
                        <input type="number" step="0.01" value={v.amount} disabled={!canConfigure}
                          onChange={e => setReview({ ...review, [r.mt]: { ...v, kind: v.kind, amount: e.target.value } })}
                          style={{ ...inp, width: 90, textAlign: 'right' }} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {canConfigure && (
            <button onClick={saveReview} disabled={busy} style={{ ...primaryBtn, marginTop: 8 }}>
              <i className="ti ti-device-floppy" style={{ fontSize: 14, marginRight: 6 }} />{t('workorders.review_save')}
            </button>
          )}
        </>
      )}

      {/* Modal de tancament (només feina inacabada bloqueja; els extres NO) */}
      {modal && (
        <div onClick={() => setModal(null)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 50, padding: 16,
        }}>
          <div onClick={e => e.stopPropagation()} style={{
            background: 'var(--white)', borderRadius: 12, padding: '1.2rem 1.4rem',
            maxWidth: 520, width: '100%', maxHeight: '80vh', overflowY: 'auto',
            border: '0.5px solid var(--gray-l)',
          }}>
            <h2 style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, marginBottom: 10, fontFamily: MONO }}>
              {t('workorders.close_title')}
            </h2>
            {hardBlockers.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ color: 'var(--err)', fontWeight: 600, marginBottom: 6 }}>{t('workorders.blockers_hard')}</div>
                {hardBlockers.map((b, i) => (
                  <div key={i} style={{ fontSize: 'var(--fs-body)', color: 'var(--err)' }}>
                    · {b.task_type} — {t(`workorders.status_task_${b.reason}`, { defaultValue: b.reason })}
                  </div>
                ))}
              </div>
            )}
            {pending.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>{t('workorders.pending_title')}</div>
                {pending.map((p, i) => (
                  <div key={i} style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>· {p.task_type}</div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
              {hardBlockers.length === 0 && (
                <button onClick={() => doClose({ cancel_pending: pending.length > 0 })} disabled={busy} style={{ ...primaryBtn }}>
                  {pending.length > 0 ? t('workorders.close_deduct') : t('workorders.close_confirm')}
                </button>
              )}
              <button onClick={() => setModal(null)} disabled={busy} style={smallBtn}>{t('workorders.close_cancel')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
