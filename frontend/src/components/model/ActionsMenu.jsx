import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { suppliers as suppliersApi, productions, fittingSessions, models as modelsApi } from '../../api/endpoints'
import Modal from '../ui/Modal'
import { selS } from '../ui/buttons'
import TaskAssignWizard from '../TaskAssignWizard'

export const PHASES = ['Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']
const CURRENT = '__current__'   // "fase actual de cada model" (bulk)
const MONO = 'IBM Plex Mono, monospace'
const nextPhase = (f) => { const i = PHASES.indexOf(f); return i >= 0 && i < PHASES.length - 1 ? PHASES[i + 1] : null }
const prevPhase = (f) => { const i = PHASES.indexOf(f); return i > 0 ? PHASES[i - 1] : null }
const todayISO = () => new Date().toISOString().slice(0, 10)

// Pas 5C · TRAM 2 — Desplegable "Accions" per a UN model (fitxa) o N (selecció a la llista).
// Bulk = itera les crides per-model existents; cada model va a la SEVA next/prev. Feedback agregat.
export default function ActionsMenu({ targets, model, onChanged, onFeedback, triggerLabel }) {
  const { t } = useTranslation()
  const list = (targets && targets.length ? targets : (model ? [model] : []))
  const single = list.length === 1 ? list[0] : null

  const [open, setOpen] = useState(false)
  const [modal, setModal] = useState(null)
  const [busy, setBusy] = useState(false)
  const [supps, setSupps] = useState([])
  const [prods, setProds] = useState([])   // només per al cas single (precondició fitting + defaults)
  const [form, setForm] = useState({})

  useEffect(() => {
    suppliersApi.list({ active: 'true', ordering: 'name', page_size: 500 }).then(r => setSupps(r.data?.results ?? r.data ?? [])).catch(() => {})
  }, [])
  useEffect(() => {
    if (!single) { setProds([]); return }
    productions.list({ model: single.id, page_size: 200 }).then(r => setProds(r.data?.results ?? r.data ?? [])).catch(() => setProds([]))
  }, [single?.id])

  // Informatiu (✓ a la fase i decisió de mostrar el camp de recepció prevista). Ja NO bloqueja.
  const deliveredPhases = new Set(prods.filter(p => p.status === 'Delivered').map(p => p.phase))
  const someNext = list.some(m => nextPhase(m.fase_actual))
  const somePrev = list.some(m => prevPhase(m.fase_actual))
  const defaultPhase = single ? single.fase_actual : CURRENT

  const openModal = (kind) => {
    setOpen(false)
    if (kind === 'production') setForm({ supplier_id: '', phase: defaultPhase, expected_at: '', notes: '' })
    if (kind === 'fitting') setForm({ fase: single ? single.fase_actual : CURRENT, data: todayISO(), expected_at: '' })
    setModal(kind)
  }

  // Itera per-model amb feedback agregat: "X fet, Y omesos".
  const runBulk = async (perModel) => {
    setBusy(true)
    let ok = 0; const omesos = []
    for (const m of list) {
      try { await perModel(m); ok++ }
      catch (e) { omesos.push(`${m.codi_intern}: ${e.response?.data?.error || 'error'}`) }
    }
    setBusy(false); setModal(null)
    const txt = t('model_sheet.bulk_done', { ok }) + (omesos.length ? ' · ' + t('model_sheet.bulk_skipped', { n: omesos.length }) : '')
    onFeedback({ type: omesos.length ? 'err' : 'ok', text: txt })
    onChanged && onChanged()
  }

  const phaseFor = (m) => (form.phase === CURRENT ? m.fase_actual : form.phase)
  const runProduction = () => {
    if (!form.supplier_id) { onFeedback({ type: 'err', text: t('model_sheet.select_supplier') }); return }
    if (!form.expected_at) { onFeedback({ type: 'err', text: t('model_sheet.expected_required') }); return }
    runBulk(async m => {
      const r = await productions.requestProduction(m.id, { supplier_id: Number(form.supplier_id), phase: phaseFor(m), expected_at: form.expected_at, notes: form.notes || '' })
      return r
    })
  }
  const runFitting = () => runBulk(m => fittingSessions.schedule({
    fase: (form.fase === CURRENT ? m.fase_actual : form.fase),
    data: form.data,
    model_id: m.id,
    ...(form.expected_at ? { expected_at: form.expected_at } : {}),
  }))
  const runAdvance = () => runBulk(m => { const nx = nextPhase(m.fase_actual); if (!nx) throw { response: { data: { error: t('model_sheet.phase_top') } } }; return modelsApi.gate(m.id, { to_phase: nx }) })
  const runBack = () => runBulk(m => { const pv = prevPhase(m.fase_actual); if (!pv) throw { response: { data: { error: t('model_sheet.phase_first') } } }; return modelsApi.regress(m.id, { to_phase: pv }) })

  const items = [
    { key: 'assign', label: t('model_sheet.assign_tasks', 'Assignar tasques'), icon: 'ti-users-plus', enabled: list.length > 0 },
    { key: 'production', label: t('model_sheet.send_to_production'), icon: 'ti-send', enabled: list.length > 0 },
    { key: 'fitting', label: t('model_sheet.schedule_fitting'), icon: 'ti-calendar-plus', enabled: list.length > 0 },
    { key: 'advance', label: t('model_sheet.advance_phase'), icon: 'ti-arrow-right', enabled: someNext },
    { key: 'back', label: t('model_sheet.back_phase'), icon: 'ti-arrow-left', enabled: somePrev },
  ]
  const phaseSelectOptions = (withCurrent) => (
    <>
      {!single && withCurrent && <option value={CURRENT}>{t('model_sheet.current_phase')}</option>}
      {PHASES.map(p => <option key={p} value={p}>{p}{single && p === single.fase_actual ? ' ●' : ''}</option>)}
    </>
  )

  return (
    <div style={{ position: 'relative' }}>
      <button type="button" onClick={() => list.length && setOpen(o => !o)} disabled={!list.length}
        style={{ ...triggerBtn, opacity: list.length ? 1 : 0.5, cursor: list.length ? 'pointer' : 'not-allowed' }}>
        {triggerLabel || t('model_sheet.actions')}{list.length > 1 ? ` (${list.length})` : ''} <i className="ti ti-chevron-down" aria-hidden="true" />
      </button>
      {open && (
        <>
          <div onClick={() => setOpen(false)} style={{ position: 'fixed', inset: 0, zIndex: 40 }} />
          <div style={menuBox}>
            {items.map(it => (
              <button key={it.key} type="button" disabled={!it.enabled} onClick={() => it.enabled && openModal(it.key)} title={it.hint || ''}
                style={{ ...menuItem, opacity: it.enabled ? 1 : 0.45, cursor: it.enabled ? 'pointer' : 'not-allowed' }}>
                <i className={`ti ${it.icon}`} aria-hidden="true" /> {it.label}
                {it.hint && <span style={{ fontSize: 9, color: 'var(--gray)', marginLeft: 'auto' }}>ⓘ</span>}
              </button>
            ))}
          </div>
        </>
      )}

      {modal === 'assign' && (
        <TaskAssignWizard
          modelIds={list.map(m => m.id)}
          onClose={() => setModal(null)}
          onSuccess={() => { setModal(null); onChanged?.() }}
        />
      )}

      {modal === 'production' && (
        <Modal title={t('model_sheet.send_to_production')} confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.send')} cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy} onConfirm={runProduction} onCancel={() => !busy && setModal(null)}>
          {!single && <div style={infoBox}>{t('model_sheet.bulk_apply', { n: list.length })}</div>}
          <Row label={t('model_sheet.supplier')}>
            <select style={fullSel} value={form.supplier_id} onChange={e => setForm(f => ({ ...f, supplier_id: e.target.value }))}>
              <option value="">— {t('model_sheet.select_supplier')} —</option>
              {supps.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </Row>
          <Row label={t('model_sheet.phase')}><select style={fullSel} value={form.phase} onChange={e => setForm(f => ({ ...f, phase: e.target.value }))}>{phaseSelectOptions(true)}</select></Row>
          <Row label={t('model_sheet.expected_at') + ' *'}><input type="date" style={fullSel} value={form.expected_at} onChange={e => setForm(f => ({ ...f, expected_at: e.target.value }))} /></Row>
          <Row label={t('model_sheet.notes')}><textarea style={{ ...fullSel, minHeight: 50, resize: 'vertical' }} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} /></Row>
        </Modal>
      )}

      {modal === 'fitting' && (
        <Modal title={t('model_sheet.schedule_fitting')} confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.schedule_fitting')} cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy} onConfirm={runFitting} onCancel={() => !busy && setModal(null)}>
          {!single && <div style={infoBox}>{t('model_sheet.fitting_bulk_note', { n: list.length })}</div>}
          <Row label={t('model_sheet.phase')}>
            <select style={fullSel} value={form.fase} onChange={e => setForm(f => ({ ...f, fase: e.target.value }))}>
              {single
                ? PHASES.map(p => <option key={p} value={p}>{p}{deliveredPhases.has(p) ? ' ✓' : ''}</option>)
                : phaseSelectOptions(true)}
            </select>
          </Row>
          <Row label={t('model_sheet.date')}><input type="date" style={fullSel} value={form.data} onChange={e => setForm(f => ({ ...f, data: e.target.value }))} /></Row>
          {!deliveredPhases.has(form.fase) && (
            <div style={{ marginTop: 8 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {t('fitting_expected_at_label', 'Data prevista de recepció de la mostra')}
              </label>
              <input
                type="date"
                value={form.expected_at || ''}
                onChange={e => setForm(f => ({ ...f, expected_at: e.target.value }))}
                style={{ width: '100%', marginTop: 4, fontSize: 12, border: '1px solid var(--border)', borderRadius: 4, padding: '4px 8px' }}
              />
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                {t('fitting_expected_at_hint', 'Si no has rebut la mostra, informa quan l\'esperes.')}
              </div>
            </div>
          )}
        </Modal>
      )}

      {(modal === 'advance' || modal === 'back') && (() => {
        const isAdv = modal === 'advance'
        const target = single ? (isAdv ? nextPhase(single.fase_actual) : prevPhase(single.fase_actual)) : null
        const titleKey = single
          ? (isAdv ? 'model_sheet.advance_confirm' : 'model_sheet.back_confirm')
          : (isAdv ? 'model_sheet.advance_bulk_confirm' : 'model_sheet.back_bulk_confirm')
        return (
          <Modal title={t(titleKey, { phase: target, n: list.length })}
            confirmLabel={busy ? t('model_sheet.working') : t(isAdv ? 'model_sheet.advance_phase' : 'model_sheet.back_phase')}
            cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy}
            onConfirm={() => (isAdv ? runAdvance() : runBack())} onCancel={() => !busy && setModal(null)}>
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

const triggerBtn = { display: 'flex', alignItems: 'center', gap: 6, background: 'var(--gold)', color: '#fff', border: 'none', borderRadius: 6, padding: '7px 14px', fontSize: 12, fontWeight: 600, fontFamily: MONO }
const menuBox = { position: 'absolute', right: 0, top: 'calc(100% + 4px)', zIndex: 41, background: 'var(--white)', border: '0.5px solid var(--gray-l)', borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.12)', padding: 4, minWidth: 230 }
const menuItem = { display: 'flex', alignItems: 'center', gap: 8, width: '100%', textAlign: 'left', background: 'none', border: 'none', padding: '8px 10px', borderRadius: 6, fontFamily: MONO, fontSize: 12, color: 'var(--text-main)' }
const fullSel = { ...selS, width: '100%' }
const warnBox = { background: 'var(--warn-bg)', border: '0.5px solid var(--warn)', color: 'var(--warn)', borderRadius: 8, padding: '8px 12px', marginBottom: 12, fontSize: 12, lineHeight: 1.5, fontFamily: MONO }
const infoBox = { background: 'var(--gray-l)', borderRadius: 8, padding: '8px 12px', marginBottom: 12, fontSize: 12, fontFamily: MONO, color: 'var(--text-main)' }
