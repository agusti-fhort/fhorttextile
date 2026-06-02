import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { taskTypes, suppliers as suppliersApi, productions, fittingSessions, models as modelsApi } from '../../api/endpoints'
import Modal from '../ui/Modal'
import { selS } from '../ui/buttons'

export const PHASES = ['Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']
const MONO = 'IBM Plex Mono, monospace'
const nextPhase = (f) => { const i = PHASES.indexOf(f); return i >= 0 && i < PHASES.length - 1 ? PHASES[i + 1] : null }
const prevPhase = (f) => { const i = PHASES.indexOf(f); return i > 0 ? PHASES[i - 1] : null }
const todayISO = () => new Date().toISOString().slice(0, 10)

// Pas 5B-fix · TRAM 2 — Desplegable "Accions" de la fitxa (reutilitzable per a selecció múltiple al 5C).
// Accions: Generar tasques · Ordenar producció · Programar fitting · Avançar fase · Retrocedir fase.
export default function ActionsMenu({ model, onChanged, onFeedback }) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [modal, setModal] = useState(null)   // 'tasks'|'production'|'fitting'|'advance'|'back'
  const [busy, setBusy] = useState(false)
  // dades de suport
  const [tts, setTts] = useState([])
  const [supps, setSupps] = useState([])
  const [prods, setProds] = useState([])
  const [form, setForm] = useState({})

  useEffect(() => {
    taskTypes.list({ page_size: 200 }).then(r => setTts((r.data?.results ?? r.data ?? []).filter(x => x.active !== false))).catch(() => {})
    suppliersApi.list({ active: 'true', ordering: 'name', page_size: 500 }).then(r => setSupps(r.data?.results ?? r.data ?? [])).catch(() => {})
    refreshProds()
  }, [model.id])

  const refreshProds = () => productions.list({ model: model.id, page_size: 200 })
    .then(r => setProds(r.data?.results ?? r.data ?? [])).catch(() => setProds([]))

  const deliveredPhases = new Set(prods.filter(p => p.status === 'Delivered').map(p => p.phase))
  const next = nextPhase(model.fase_actual)
  const prev = prevPhase(model.fase_actual)

  const openModal = (kind) => {
    setOpen(false)
    if (kind === 'tasks') setForm({ ids: tts.map(t => t.id) })
    if (kind === 'production') setForm({ supplier_id: '', phase: model.fase_actual, expected_at: '', notes: '' })
    if (kind === 'fitting') setForm({ fase: deliveredPhases.has(model.fase_actual) ? model.fase_actual : [...deliveredPhases][0] || model.fase_actual, data: todayISO() })
    setModal(kind)
  }

  const done = (text) => { onFeedback({ type: 'ok', text }); setModal(null); onChanged && onChanged() }
  const fail = (e) => onFeedback({ type: 'err', text: e.response?.data?.error || t('model_sheet.action_error') })

  const runTasks = async () => {
    setBusy(true)
    try {
      const r = await modelsApi.defineTasks(model.id, { task_type_ids: form.ids })
      onFeedback({ type: 'ok', text: t('model_sheet.tasks_done', { created: r.data?.created_ids?.length ?? 0, skipped: r.data?.skipped_existing?.length ?? 0 }) })
      setModal(null)
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const runProduction = async () => {
    if (!form.supplier_id) { onFeedback({ type: 'err', text: t('model_sheet.select_supplier') }); return }
    if (!form.expected_at) { onFeedback({ type: 'err', text: t('model_sheet.expected_required') }); return }
    setBusy(true)
    try {
      const r = await productions.requestProduction(model.id, { supplier_id: Number(form.supplier_id), phase: form.phase, expected_at: form.expected_at, notes: form.notes || '' })
      onFeedback({ type: r.data?.warning ? 'err' : 'ok', text: r.data?.warning || t('model_sheet.prod_sent') })
      setModal(null); refreshProds(); onChanged && onChanged()
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const runFitting = async () => {
    setBusy(true)
    try {
      await fittingSessions.schedule({ fase: form.fase, data: form.data, model_id: model.id })
      done(t('model_sheet.scheduled'))
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const runGate = async (to) => {
    setBusy(true)
    try {
      await modelsApi.gate(model.id, { to_phase: to })
      done(t('model_sheet.phase_advanced', { phase: to }))
    } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const runRegress = async (to) => {
    setBusy(true)
    try {
      await modelsApi.regress(model.id, { to_phase: to })
      done(t('model_sheet.phase_regressed', { phase: to }))
    } catch (e) { fail(e) } finally { setBusy(false) }
  }

  const canFitting = deliveredPhases.size > 0
  const items = [
    { key: 'tasks', label: t('model_sheet.generate_tasks'), icon: 'ti-list-check', enabled: true },
    { key: 'production', label: t('model_sheet.send_to_production'), icon: 'ti-send', enabled: true },
    { key: 'fitting', label: t('model_sheet.schedule_fitting'), icon: 'ti-calendar-plus', enabled: canFitting, hint: canFitting ? null : t('model_sheet.fitting_needs_delivered') },
    { key: 'advance', label: t('model_sheet.advance_phase'), icon: 'ti-arrow-right', enabled: !!next, hint: next ? null : t('model_sheet.phase_top') },
    { key: 'back', label: t('model_sheet.back_phase'), icon: 'ti-arrow-left', enabled: !!prev, hint: prev ? null : t('model_sheet.phase_first') },
  ]

  return (
    <div style={{ position: 'relative' }}>
      <button type="button" onClick={() => setOpen(o => !o)} style={triggerBtn}>
        {t('model_sheet.actions')} <i className="ti ti-chevron-down" aria-hidden="true" />
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 40 }} />
          <div style={menuBox}>
            {items.map(it => (
              <button key={it.key} type="button" disabled={!it.enabled}
                onClick={() => it.enabled && openModal(it.key)} title={it.hint || ''}
                style={{ ...menuItem, opacity: it.enabled ? 1 : 0.45, cursor: it.enabled ? 'pointer' : 'not-allowed' }}>
                <i className={`ti ${it.icon}`} aria-hidden="true" /> {it.label}
                {it.hint && <span style={{ fontSize: 9, color: 'var(--gray)', marginLeft: 'auto' }}>ⓘ</span>}
              </button>
            ))}
          </div>
        </>
      )}

      {modal === 'tasks' && (
        <Modal title={t('model_sheet.generate_tasks')} confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.generate')} cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy || !(form.ids || []).length} onConfirm={runTasks} onCancel={() => !busy && setModal(null)}>
          {!model.garment_type_item && <div style={warnBox}>{t('model_sheet.tasks_no_item_warn')}</div>}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {tts.map(tt => {
              const checked = (form.ids || []).includes(tt.id)
              return (
                <label key={tt.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: MONO, fontSize: 12, cursor: 'pointer' }}>
                  <input type="checkbox" checked={checked} onChange={() => setForm(f => ({ ...f, ids: checked ? f.ids.filter(x => x !== tt.id) : [...f.ids, tt.id] }))} />
                  {tt.name} <span style={{ color: 'var(--gray)' }}>({tt.code})</span>
                </label>
              )
            })}
          </div>
        </Modal>
      )}

      {modal === 'production' && (
        <Modal title={t('model_sheet.send_to_production')} confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.send')} cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy} onConfirm={runProduction} onCancel={() => !busy && setModal(null)}>
          <Row label={t('model_sheet.supplier')}>
            <select style={fullSel} value={form.supplier_id} onChange={e => setForm(f => ({ ...f, supplier_id: e.target.value }))}>
              <option value="">— {t('model_sheet.select_supplier')} —</option>
              {supps.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Row>
          <Row label={t('model_sheet.phase')}><PhaseSelect value={form.phase} fase={model.fase_actual} onChange={v => setForm(f => ({ ...f, phase: v }))} /></Row>
          <Row label={t('model_sheet.expected_at') + ' *'}><input type="date" style={fullSel} value={form.expected_at} onChange={e => setForm(f => ({ ...f, expected_at: e.target.value }))} /></Row>
          <Row label={t('model_sheet.notes')}><textarea style={{ ...fullSel, minHeight: 50, resize: 'vertical' }} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} /></Row>
        </Modal>
      )}

      {modal === 'fitting' && (
        <Modal title={t('model_sheet.schedule_fitting')} confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.schedule_fitting')} cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy || !deliveredPhases.has(form.fase)} onConfirm={runFitting} onCancel={() => !busy && setModal(null)}>
          {!deliveredPhases.has(form.fase) && <div style={warnBox}>{t('model_sheet.fitting_needs_delivered')}</div>}
          <Row label={t('model_sheet.phase')}>
            <select style={fullSel} value={form.fase} onChange={e => setForm(f => ({ ...f, fase: e.target.value }))}>
              {PHASES.map(p => <option key={p} value={p} disabled={!deliveredPhases.has(p)}>{p}{deliveredPhases.has(p) ? ' ✓' : ''}</option>)}
            </select>
          </Row>
          <Row label={t('model_sheet.date')}><input type="date" style={fullSel} value={form.data} onChange={e => setForm(f => ({ ...f, data: e.target.value }))} /></Row>
        </Modal>
      )}

      {(modal === 'advance' || modal === 'back') && (() => {
        const isAdv = modal === 'advance'
        const target = isAdv ? next : prev
        return (
          <Modal title={t(isAdv ? 'model_sheet.advance_confirm' : 'model_sheet.back_confirm', { phase: target })}
            confirmLabel={busy ? t('model_sheet.working') : t(isAdv ? 'model_sheet.advance_phase' : 'model_sheet.back_phase')}
            cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy}
            onConfirm={() => (isAdv ? runGate(target) : runRegress(target))} onCancel={() => !busy && setModal(null)}>
            <p style={{ fontSize: 13, lineHeight: 1.5 }}>{t(isAdv ? 'model_sheet.advance_help' : 'model_sheet.regress_help')}</p>
          </Modal>
        )
      })()}
    </div>
  )
}

function Row({ label, children }) {
  return <div style={{ marginBottom: 12 }}><div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '.04em', color: 'var(--gray)', marginBottom: 4, fontFamily: MONO }}>{label}</div>{children}</div>
}
function PhaseSelect({ value, fase, onChange }) {
  return <select style={fullSel} value={value} onChange={e => onChange(e.target.value)}>{PHASES.map(p => <option key={p} value={p}>{p}{p === fase ? ' ●' : ''}</option>)}</select>
}

const triggerBtn = { display: 'flex', alignItems: 'center', gap: 6, background: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 6, padding: '7px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer', fontFamily: MONO }
const menuBox = { position: 'absolute', right: 0, top: 'calc(100% + 4px)', zIndex: 41, background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4, minWidth: 220 }
const menuItem = { display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left', background: 'none', border: 'none', padding: '8px 10px', borderRadius: 6, fontFamily: MONO, fontSize: 12, color: 'var(--text-main)' }
const fullSel = { ...selS, width: '100%' }
const warnBox = { background: 'var(--warn-bg)', border: '0.5px solid var(--warn)', color: 'var(--warn)', borderRadius: 8, padding: '8px 12px', marginBottom: 12, fontSize: 12, lineHeight: 1.5, fontFamily: MONO }
