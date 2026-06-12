import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { suppliers as suppliersApi, productions, fittingSessions, models as modelsApi, plan } from '../../api/endpoints'
import Modal from '../ui/Modal'
import { selS } from '../ui/buttons'
import TaskAssignWizard from '../TaskAssignWizard'

export const PHASES = ['Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']
const CURRENT = '__current__'   // "fase actual de cada model" (bulk)
const MONO = 'IBM Plex Mono, monospace'
// Cercle de color d'assignació (color_avatar). Fallback --gold si null. (replica de TaskAssignWizard)
const ColorDot = ({ color, size = 16 }) => (
  <span style={{ display: 'inline-block', width: size, height: size, borderRadius: '50%',
    background: color || 'var(--gold)', border: '0.5px solid var(--gray-l)', flexShrink: 0 }} />
)
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
  const [confirmPending, setConfirmPending] = useState(null)   // {payload, text} — conflicte suau a confirmar
  const [supps, setSupps] = useState([])
  const [prods, setProds] = useState([])   // només per al cas single (precondició fitting + defaults)
  const [form, setForm] = useState({})
  const [elegibles, setElegibles] = useState([])   // assistents amb schedule_fittings (modal fitting)
  const [loadingEleg, setLoadingEleg] = useState(false)

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
    if (kind === 'fitting') {
      setForm({ fase: single ? single.fase_actual : CURRENT, data: todayISO(), expected_at: '',
                start_time: '', duracio_minuts: '', attendee_ids: [] })
      setLoadingEleg(true)
      plan.eligibleAttendees()
        .then(r => {
          const listE = r.data?.results ?? r.data ?? []
          setElegibles(listE)
          // Preseleccionar el primer elegible per defecte (si encara no n'hi ha cap).
          if (listE.length > 0) setForm(f => (f.attendee_ids?.length ? f : { ...f, attendee_ids: [listE[0].profile_id] }))
        })
        .catch(() => setElegibles([]))
        .finally(() => setLoadingEleg(false))
    }
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
  // Schedule single amb gestió de conflictes (P1): 409 dur (sense força) i
  // 200 requires_confirmation (suau → confirmació i recrida amb force=true).
  const submitSchedule = async (payload, force = false) => {
    setBusy(true)
    try {
      const r = await fittingSessions.schedule(force ? { ...payload, force: true } : payload)
      if (r.data?.requires_confirmation) {   // conflicte suau → demanar confirmació
        setBusy(false)
        setConfirmPending({ payload, text: r.data.warning })
        return
      }
      setBusy(false); setModal(null); setConfirmPending(null)
      onFeedback({ type: 'ok', text: t('model_sheet.fitting_scheduled', 'Fitting programat') })
      onChanged && onChanged()
    } catch (e) {
      setBusy(false)
      if (e.response?.status === 409) {   // conflicte DUR: no es pot forçar
        onFeedback({ type: 'err', text: t('model_sheet.fitting_overlap',
          'Ja existeix una sessió en aquesta franja per aquest model.') })
      } else {
        onFeedback({ type: 'err', text: e.response?.data?.error || 'error' })
      }
    }
  }

  const runFitting = () => {
    // Single → schedule individual (retrocompat P5; gestiona expected_at via adaptativa).
    if (list.length === 1) {
      const m = list[0]
      return submitSchedule({
        fase: (form.fase === CURRENT ? m.fase_actual : form.fase),
        data: form.data,
        model_id: m.id,
        start_time: form.start_time || undefined,
        duracio_minuts: form.duracio_minuts ? parseInt(form.duracio_minuts, 10) : undefined,
        attendee_ids: form.attendee_ids || [],
        ...(form.expected_at ? { expected_at: form.expected_at } : {}),
      })
    }
    // Bulk → sessions ENCADENADES via schedule-bulk (convocatòria UUID). schedule-bulk pren UNA
    // fase; amb CURRENT els models poden tenir fase_actual diferents → 1 convocatòria per fase.
    const groups = {}
    for (const m of list) {
      const fase = form.fase === CURRENT ? m.fase_actual : form.fase
      ;(groups[fase] = groups[fase] || []).push(m)
    }
    setBusy(true)
    Promise.all(Object.entries(groups).map(([fase, ms]) =>
      fittingSessions.scheduleBulk({
        model_ids: ms.map(m => m.id),
        fase,
        data: form.data,
        start_time: form.start_time || undefined,
        duracio_minuts: form.duracio_minuts ? parseInt(form.duracio_minuts, 10) : undefined,
        attendee_ids: form.attendee_ids || [],
        ...(form.expected_at ? { expected_at: form.expected_at } : {}),
      })
    ))
      .then(results => {
        setBusy(false); setModal(null)
        // P1: schedule-bulk retorna {created, skipped, warnings} (ja no n_sessions).
        const created = results.reduce((a, r) => a + (r.data?.created?.length ?? 0), 0)
        const skipped = results.reduce((a, r) => a + (r.data?.skipped?.length ?? 0), 0)
        const warnings = results.flatMap(r => r.data?.warnings ?? [])
        let txt = t('model_sheet.fitting_bulk_scheduled', { n: created, defaultValue: '{{n}} sessions creades' })
        if (skipped > 0) txt += ' · ' + t('model_sheet.fitting_bulk_skipped', { n: skipped, defaultValue: '{{n}} omeses' })
        if (warnings.length > 0) txt += ' · ' + t('model_sheet.fitting_bulk_warnings', { n: warnings.length, defaultValue: '{{n}} amb avís' })
        onFeedback({ type: (skipped > 0 || warnings.length > 0) ? 'err' : 'ok', text: txt })
        onChanged && onChanged()
      })
      .catch(e => {
        setBusy(false)
        onFeedback({ type: 'err', text: e.response?.data?.error || 'error' })
      })
  }
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
          <Row label={t('model_sheet.fitting_start_time', "Hora d'inici")}>
            <input type="time" style={fullSel} value={form.start_time || ''}
              onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))} />
          </Row>
          <Row label={t('model_sheet.fitting_duration', 'Durada (min)')}>
            <input type="number" min={5} step={5} style={fullSel} value={form.duracio_minuts || ''}
              placeholder={t('model_sheet.fitting_duration_ph', 'Default: 10 min per model')}
              onChange={e => setForm(f => ({ ...f, duracio_minuts: e.target.value }))} />
          </Row>
          <div style={{ marginBottom: 12, marginTop: -4 }}>
            <small style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {form.start_time
                ? t('model_sheet.fitting_franja_note', { dur: form.duracio_minuts || '10', hora: form.start_time,
                    defaultValue: `El fitting ocuparà ${form.duracio_minuts || '10'} min a les ${form.start_time} a la cua dels assistents.` })
                : t('model_sheet.fitting_nofranja_note', "Sense hora, no s'assignarà franja al calendari.")}
            </small>
          </div>
          <Row label={t('model_sheet.fitting_attendees', 'Assistents')}>
            {loadingEleg
              ? <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('model_sheet.loading', 'Carregant…')}</span>
              : elegibles.length === 0
                ? <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{t('model_sheet.fitting_no_attendees', 'Cap assistent elegible.')}</span>
                : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 120, overflowY: 'auto' }}>
                    {elegibles.map(e => {
                      const sel = (form.attendee_ids || []).includes(e.profile_id)
                      return (
                        <label key={e.profile_id} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
                          padding: '4px 6px', borderRadius: 6, fontSize: 12, fontFamily: MONO,
                          background: sel ? 'var(--gold-pale)' : 'transparent' }}>
                          <input type="checkbox" checked={sel} style={{ accentColor: 'var(--gold)' }}
                            onChange={() => setForm(f => ({ ...f,
                              attendee_ids: sel
                                ? f.attendee_ids.filter(id => id !== e.profile_id)
                                : [...(f.attendee_ids || []), e.profile_id] }))} />
                          <ColorDot color={e.color_avatar} size={14} />
                          {e.full_name}
                        </label>
                      )
                    })}
                  </div>
                )}
          </Row>
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

      {/* Conflicte SUAU (P1): el model ja té fitting d'aquesta fase en una altra franja. */}
      {confirmPending && (
        <Modal title={t('model_sheet.fitting_dup_title', 'Fitting duplicat?')}
          confirmLabel={busy ? t('model_sheet.working') : t('model_sheet.fitting_create_anyway', 'Crear igualment')}
          cancelLabel={t('model_sheet.cancel')} confirmDisabled={busy}
          onConfirm={() => submitSchedule(confirmPending.payload, true)}
          onCancel={() => !busy && setConfirmPending(null)}>
          <p style={{ fontSize: 13, lineHeight: 1.5 }}>
            {confirmPending.text || t('model_sheet.fitting_dup_warn',
              'Aquest model ja té un fitting programat en aquesta fase. Vols crear-ne un altre igualment?')}
          </p>
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
