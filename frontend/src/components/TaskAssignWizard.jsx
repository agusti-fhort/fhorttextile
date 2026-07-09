import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { taskTypes as taskTypesApi, plan as planApi, modelTasks as modelTaskItems, timeAnalysis } from '../api/endpoints'
import { taskTypeLabel } from '../utils/taskType'
import { selS, primaryBtn } from './ui/buttons'

// Wizard modal d'assignació de tasques (task_type × persona × data opcional) sobre 1..N models.
// Substitueix l'AssignModal de Planning; s'integrarà a ActionsMenu (Peça 4). Backend: Peça 2
// (plan/eligible-technicians + plan/assign-batch). NO té sistema de toast global → feedback
// inline amb el patró Feedback (--ok-bg/--warn-bg/--err-bg).
const MONO = 'IBM Plex Mono, monospace'

// Cercle de color d'assignació (color_avatar). Fallback --gold si null. (replica de UsersRoles.ColorDot)
function ColorDot({ color, size = 16 }) {
  return (
    <span style={{
      display: 'inline-block', width: size, height: size, borderRadius: '50%',
      background: color || 'var(--gold)', border: '0.5px solid var(--gray-l)',
      boxSizing: 'border-box', verticalAlign: 'middle', flexShrink: 0,
    }} />
  )
}

// ISO (amb o sense offset) → 'dd/mm/yy'. null/'' → ''.
function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d)) return ''
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${String(d.getFullYear()).slice(-2)}`
}
// ISO → 'dd/mm HH:MM' (per als resultats post-submit).
function fmtDateTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (isNaN(d)) return ''
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)} ${p(d.getHours())}:${p(d.getMinutes())}`
}

const labelS = { fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em' }
const secondaryBtn = { ...selS, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }

export default function TaskAssignWizard({ modelIds = [], onClose, onSuccess }) {
  const { t } = useTranslation()
  const nModels = modelIds.length

  const [taskTypes, setTaskTypes] = useState([])
  const [loadingTT, setLoadingTT] = useState(true)
  const [blockedTypes, setBlockedTypes] = useState(new Set()) // task_type_code ja assignats en algun model
  const [selectedTT, setSelectedTT] = useState(null)        // {id,code,name}
  const [elegibles, setElegibles] = useState([])
  const [loadingEleg, setLoadingEleg] = useState(false)
  const [selectedPerson, setSelectedPerson] = useState(null) // {profile_id,full_name,color_avatar,disponible_des_de,models_en_cua}
  const [dateMode, setDateMode] = useState('none')           // 'none'|'start'|'end'
  const [dateValue, setDateValue] = useState('')             // YYYY-MM-DD
  const [lines, setLines] = useState([])
  const [duplicateWarning, setDuplicateWarning] = useState(null) // task_type_code pendent
  const [submitting, setSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState(null)
  const [submitError, setSubmitError] = useState(null)
  const [captureVals, setCaptureVals] = useState({})         // task_code → minuts (captura conscient)
  const [capturing, setCapturing] = useState(false)

  // ── Càrrega de TaskType actius + tasques ja assignades dels models (mount) ───
  useEffect(() => {
    let cancelled = false
    setLoadingTT(true)
    taskTypesApi.list({ page_size: 200 })
      .then(r => {
        if (cancelled) return
        const all = r.data?.results ?? r.data ?? []
        setTaskTypes(all.filter(x => x.active !== false))
      })
      .catch(() => { if (!cancelled) setTaskTypes([]) })
      .finally(() => { if (!cancelled) setLoadingTT(false) })

    // task_type_code que JA tenen tècnic en QUALSEVOL dels models → bloquejats al select.
    if (modelIds.length) {
      Promise.all(modelIds.map(id => modelTaskItems.list({ model: id })))
        .then(results => {
          if (cancelled) return
          const blocked = new Set(
            results
              .flatMap(r => r.data?.results ?? r.data ?? [])
              .filter(mt => mt.assignee)
              .map(mt => mt.task_type_code)
          )
          setBlockedTypes(blocked)
        })
        .catch(() => {})
    }
    return () => { cancelled = true }
  }, [])

  // ── Càrrega d'elegibles quan canvia el task_type ────────────────────────────
  useEffect(() => {
    if (!selectedTT) { setElegibles([]); return }
    let cancelled = false
    setLoadingEleg(true)
    setElegibles([])
    planApi.eligibleTechnicians(selectedTT.code)
      .then(r => { if (!cancelled) setElegibles(Array.isArray(r.data) ? r.data : (r.data?.results ?? [])) })
      .catch(() => { if (!cancelled) setElegibles([]) })
      .finally(() => { if (!cancelled) setLoadingEleg(false) })
    return () => { cancelled = true }
  }, [selectedTT])

  const onChangeTT = (e) => {
    const tt = taskTypes.find(x => String(x.id) === e.target.value) || null
    setSelectedTT(tt)
    setSelectedPerson(null)
  }

  const onChangeDateMode = (mode) => {
    setDateMode(mode)
    if (mode === 'none') setDateValue('')
  }

  // Construeix una línia a partir de l'estat actual de selecció.
  const buildLine = () => {
    const planned_start = dateMode === 'start' && dateValue ? `${dateValue}T08:00` : undefined
    const planned_end = dateMode === 'end' && dateValue ? `${dateValue}T17:00` : undefined
    // TODO: llegir inici/fi jornada de CompanyCalendar
    return {
      task_type_code: selectedTT.code,
      task_type_nom: selectedTT.name,
      assignee_profile_id: selectedPerson.profile_id,
      assignee_nom: selectedPerson.full_name,
      assignee_color: selectedPerson.color_avatar,
      ...(planned_start ? { planned_start } : {}),
      ...(planned_end ? { planned_end } : {}),
    }
  }

  const resetSelection = () => { setSelectedPerson(null); setDateMode('none'); setDateValue('') }

  const addLine = () => {
    if (!selectedTT || !selectedPerson) return
    if (lines.some(l => l.task_type_code === selectedTT.code)) {
      setDuplicateWarning(selectedTT.code)   // demanar confirmació, no afegir encara
      return
    }
    setLines(prev => [...prev, buildLine()])
    resetSelection()
  }

  const confirmReplace = () => {
    const newLine = buildLine()
    setLines(prev => [...prev.filter(l => l.task_type_code !== selectedTT.code), newLine])
    setDuplicateWarning(null)
    resetSelection()
  }

  const removeLine = (idx) => setLines(prev => prev.filter((_, i) => i !== idx))

  const totalTasques = lines.length * nModels

  // ── Submit ──────────────────────────────────────────────────────────────────
  const onConfirm = () => {
    if (!lines.length || submitting) return
    setSubmitting(true)
    setSubmitError(null)
    const payload = {
      model_ids: modelIds,
      assignacions: lines.map(l => ({
        task_type_code: l.task_type_code,
        assignee_profile_id: l.assignee_profile_id,
        planned_start: l.planned_start,
        planned_end: l.planned_end,
      })),
    }
    planApi.assignBatch(payload)
      .then(r => {
        setSubmitResult(r.data)
        if (r.data.needs_estimate?.length) {
          // Captura conscient: no tanquem; el PM entra els minuts que falten i es reintenta.
          const init = {}
          r.data.needs_estimate.forEach(ne => { init[ne.task_code] = '' })
          setCaptureVals(init)
        } else {
          setTimeout(() => { onSuccess?.(); onClose?.() }, 2000)
        }
      })
      .catch(err => {
        setSubmitError(err.response?.data?.error || t('taskassign.err_assign'))
      })
      .finally(() => setSubmitting(false))
  }

  // Desa les llavors capturades (origen=CAPTURA) i reintenta l'assignació.
  const onCaptureAndRetry = () => {
    const entries = submitResult?.needs_estimate || []
    for (const ne of entries) {
      const v = parseInt(captureVals[ne.task_code], 10)
      if (!v || v <= 0) { setSubmitError(t('taskassign.capture_invalid')); return }
    }
    setCapturing(true)
    setSubmitError(null)
    Promise.all(entries.map(ne =>
      timeAnalysis.captureSeed({ task_code: ne.task_code, minuts: parseInt(captureVals[ne.task_code], 10) })
    ))
      .then(() => { setSubmitResult(null); setCaptureVals({}); onConfirm() })
      .catch(err => setSubmitError(err.response?.data?.error || t('taskassign.err_capture')))
      .finally(() => setCapturing(false))
  }

  const ttNom = (code) => taskTypes.find(x => x.code === code)?.name || code

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'var(--white)', borderRadius: 12, width: 700, maxWidth: '94vw',
        maxHeight: '88vh', display: 'flex', flexDirection: 'column', fontFamily: MONO,
      }}>
        {/* ── CAPÇALERA ── */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10, padding: '18px 22px',
          borderBottom: '1px solid var(--border)',
        }}>
          <i className="ti ti-users-plus" style={{ fontSize: 18, color: 'var(--gold)' }} />
          <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, fontFamily: MONO }}>{t('taskassign.title')}</h2>
          <span style={{
            fontSize: 'var(--fs-body)', padding: '2px 8px', borderRadius: 10, background: 'var(--gold-pale)',
            color: 'var(--gold)', fontWeight: 600,
          }}>{nModels} {nModels === 1 ? t('taskassign.model') : t('taskassign.models')}</span>
          <button onClick={onClose} style={{
            marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-muted)', fontSize: 'var(--fs-h2)', display: 'flex', alignItems: 'center',
          }} title={t('app.close')}><i className="ti ti-x" /></button>
        </div>

        {/* ── COS (scroll) ── */}
        <div style={{ padding: 22, overflowY: 'auto', flex: 1 }}>
          <div style={{ display: 'flex', gap: 20 }}>
            {/* COLUMNA ESQUERRA 45% — Zona A + Zona C */}
            <div style={{ flexBasis: '45%', display: 'flex', flexDirection: 'column', gap: 18 }}>
              {/* [A] TaskType */}
              <div>
                <label style={labelS}>{t('taskassign.task_type')}</label>
                <select
                  value={selectedTT?.id ?? ''}
                  onChange={onChangeTT}
                  disabled={loadingTT}
                  style={{ ...selS, width: '100%', marginTop: 6, cursor: 'pointer' }}
                >
                  <option value="">{loadingTT ? t('common.loading') : t('taskassign.select_task')}</option>
                  {taskTypes.map(tt => {
                    const isBlocked = blockedTypes.has(tt.code)
                    return (
                      <option key={tt.id} value={tt.id} disabled={isBlocked}
                        style={isBlocked ? { color: 'var(--text-muted)' } : undefined}>
                        {tt.code} · {taskTypeLabel(t, tt.code, tt.name)}{isBlocked ? ` ${t('taskassign.already_assigned')}` : ''}
                      </option>
                    )
                  })}
                </select>
              </div>

              {/* [C] Dates */}
              <div>
                <label style={labelS}>{t('taskassign.date')}</label>
                <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {[
                    ['none', t('taskassign.date_none')],
                    ['start', t('taskassign.date_start')],
                    ['end', t('taskassign.date_end')],
                  ].map(([val, lbl]) => (
                    <label key={val} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
                      <input type="radio" name="dateMode" checked={dateMode === val}
                             onChange={() => onChangeDateMode(val)} />
                      <span>{lbl}</span>
                    </label>
                  ))}
                </div>
                {dateMode !== 'none' && (
                  <input type="date" value={dateValue} onChange={e => setDateValue(e.target.value)}
                         style={{ ...selS, width: '100%', marginTop: 8, cursor: 'pointer' }} />
                )}
                {dateMode !== 'none' && (
                  <div style={{
                    marginTop: 8, fontSize: 'var(--fs-body)', padding: '6px 8px', borderRadius: 6,
                    background: 'var(--warn-bg)', color: 'var(--warn)',
                  }}>
                    <i className="ti ti-alert-triangle" /> {t('taskassign.date_warn')}
                  </div>
                )}
              </div>
            </div>

            {/* COLUMNA DRETA 55% — Zona B */}
            <div style={{ flexBasis: '55%' }}>
              <label style={labelS}>{t('taskassign.person')}</label>
              <div style={{ marginTop: 8, maxHeight: 240, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {!selectedTT && (
                  <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', padding: '12px 4px' }}>
                    {t('taskassign.select_task_first')}
                  </div>
                )}
                {selectedTT && loadingEleg && (
                  <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', padding: '12px 4px', textAlign: 'center' }}>
                    <i className="ti ti-loader-2" style={{ marginRight: 6 }} />{t('taskassign.loading_techs')}
                  </div>
                )}
                {selectedTT && !loadingEleg && elegibles.length === 0 && (
                  <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', padding: '12px 4px' }}>
                    {t('taskassign.no_eligible')}
                  </div>
                )}
                {selectedTT && !loadingEleg && elegibles.map(p => {
                  const sel = selectedPerson?.profile_id === p.profile_id
                  return (
                    <button key={p.profile_id} type="button" onClick={() => setSelectedPerson(p)}
                      style={{
                        display: 'flex', alignItems: 'flex-start', gap: 10, padding: '8px 10px',
                        borderRadius: 6, textAlign: 'left', cursor: 'pointer', width: '100%',
                        border: '1px solid var(--border)',
                        borderLeft: sel ? '3px solid var(--gold)' : '1px solid var(--border)',
                        background: sel ? 'var(--gold-pale)' : 'var(--white)',
                      }}
                      onMouseEnter={e => { if (!sel) e.currentTarget.style.background = 'var(--bg-muted)' }}
                      onMouseLeave={e => { if (!sel) e.currentTarget.style.background = 'var(--white)' }}
                    >
                      <ColorDot color={p.color_avatar} size={20} />
                      <span style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500 }}>{p.full_name}</span>
                        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                          {t('taskassign.free_from')} {p.disponible_des_de ? fmtDate(p.disponible_des_de) : t('taskassign.free_now')}
                        </span>
                        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                          {p.models_en_cua} {p.models_en_cua === 1 ? t('taskassign.model') : t('taskassign.models')} {t('taskassign.in_queue')}
                        </span>
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* + Afegir assignació */}
          <div style={{ marginTop: 18 }}>
            <button type="button" onClick={addLine}
              disabled={!selectedTT || !selectedPerson}
              style={{
                ...secondaryBtn, width: '100%',
                opacity: (!selectedTT || !selectedPerson) ? 0.5 : 1,
                cursor: (!selectedTT || !selectedPerson) ? 'not-allowed' : 'pointer',
              }}>
              <i className="ti ti-plus" /> {t('taskassign.add_assignment')}
            </button>
          </div>

          {/* Avís duplicat */}
          {duplicateWarning && (
            <div style={{
              marginTop: 10, padding: '10px 12px', borderRadius: 6,
              background: 'var(--warn-bg)', color: 'var(--warn)', fontSize: 'var(--fs-body)',
              border: '1px solid var(--warn)',
            }}>
              <div style={{ marginBottom: 8 }}>
                {t('taskassign.duplicate_warn', { name: ttNom(duplicateWarning) })}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="button" onClick={confirmReplace}
                  style={{ ...primaryBtn, marginLeft: 0, padding: '5px 12px' }}>{t('taskassign.replace')}</button>
                <button type="button" onClick={() => setDuplicateWarning(null)}
                  style={{ ...selS, cursor: 'pointer' }}>{t('app.cancel')}</button>
              </div>
            </div>
          )}

          {/* ── ZONA D — Resum / Resultats ── */}
          <div style={{ marginTop: 18, borderTop: '1px solid var(--border)', paddingTop: 14 }}>
            {submitResult?.needs_estimate?.length ? (
              // Captura conscient del PM: falten estimacions per poder planificar.
              <div>
                <div style={{
                  fontSize: 'var(--fs-body)', padding: '8px 12px', borderRadius: 6, marginBottom: 10,
                  background: 'var(--warn-bg)', color: 'var(--warn)',
                }}>
                  <i className="ti ti-clock-question" />{' '}
                  {t('taskassign.needs_estimate_intro', { count: submitResult.needs_estimate.length })}
                </div>
                <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                  {submitResult.needs_estimate.map(ne => (
                    <div key={ne.task_code} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                      <span style={{ flex: 1, fontSize: 'var(--fs-body)', fontWeight: 500 }}>
                        {taskTypeLabel(t, ne.task_code)}
                        <span style={{ color: 'var(--text-muted)', marginLeft: 6, fontSize: 'var(--fs-label)' }}>{ne.fase}</span>
                      </span>
                      <input type="number" min="1" inputMode="numeric"
                        value={captureVals[ne.task_code] ?? ''}
                        onChange={e => setCaptureVals(v => ({ ...v, [ne.task_code]: e.target.value }))}
                        placeholder={t('taskassign.minutes')}
                        style={{ ...selS, width: 110 }} />
                      <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>{t('taskassign.min_abbr')}</span>
                    </div>
                  ))}
                </div>
                {submitError && (
                  <div style={{ fontSize: 'var(--fs-body)', color: 'var(--err)', marginTop: 8 }}>{submitError}</div>
                )}
                <button onClick={onCaptureAndRetry} disabled={capturing} style={{ ...primaryBtn, marginTop: 12 }}>
                  {capturing ? t('taskassign.capturing') : t('taskassign.capture_save_retry')}
                </button>
              </div>
            ) : submitResult ? (
              // Resultats post-submit (visibles 2s abans de tancar)
              <div>
                <div style={{
                  fontSize: 'var(--fs-body)', padding: '8px 12px', borderRadius: 6, marginBottom: 10,
                  background: 'var(--ok-bg)', color: 'var(--ok)',
                }}>
                  <i className="ti ti-check" /> {t('taskassign.completed', { done: submitResult.fets, created: submitResult.creats })}
                </div>
                {submitResult.reassignats?.length > 0 && (
                  <div style={{ fontSize: 'var(--fs-body)', padding: '6px 12px', borderRadius: 6, marginBottom: 8, background: 'var(--warn-bg)', color: 'var(--warn)' }}>
                    {t('taskassign.reassigned', { count: submitResult.reassignats.length })}
                  </div>
                )}
                {submitResult.warnings?.length > 0 && (
                  <div style={{ fontSize: 'var(--fs-body)', padding: '6px 12px', borderRadius: 6, marginBottom: 8, background: 'var(--warn-bg)', color: 'var(--warn)' }}>
                    {submitResult.warnings.join(' · ')}
                  </div>
                )}
                <div style={{ maxHeight: 160, overflowY: 'auto' }}>
                  {submitResult.resultats?.map((r, i) => (
                    <div key={`r${i}`} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', padding: '5px 0', borderBottom: '1px solid var(--border)' }}>
                      <i className="ti ti-circle-check" style={{ color: 'var(--ok)' }} />
                      <span style={{ fontWeight: 500 }}>{ttNom(r.task_type_code)}</span>
                      <span style={{ color: 'var(--text-muted)' }}>
                        · {r.planned_start ? `${fmtDateTime(r.planned_start)} → ${fmtDateTime(r.planned_end)}` : t('taskassign.queue')}
                      </span>
                      {r.en_risc && (
                        <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-label)', color: 'var(--err)', fontWeight: 600 }}>
                          <i className="ti ti-alert-triangle" /> {t('taskassign.at_risk')}
                        </span>
                      )}
                    </div>
                  ))}
                  {submitResult.omesos?.map((o, i) => (
                    <div key={`o${i}`} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', padding: '5px 0', borderBottom: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                      <i className="ti ti-alert-circle" />
                      <span>{ttNom(o.task_type_code)} · {t('taskassign.model')} {o.model_id} · {o.motiu}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              // Resum de línies acumulades
              <div>
                {lines.length === 0 ? (
                  <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', textAlign: 'center', padding: '10px 0' }}>
                    {t('taskassign.empty')}
                  </div>
                ) : (
                  <div style={{ maxHeight: 120, overflowY: 'auto' }}>
                    {lines.map((l, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--fs-body)', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                        <ColorDot color={l.assignee_color} size={14} />
                        <span style={{ fontWeight: 500 }}>{l.task_type_nom}</span>
                        <span style={{ color: 'var(--text-muted)' }}>· {l.assignee_nom} ·</span>
                        <span style={{ color: 'var(--text-muted)' }}>
                          {l.planned_start ? `${t('taskassign.start')} ${fmtDate(l.planned_start)}`
                            : l.planned_end ? `${t('taskassign.end')} ${fmtDate(l.planned_end)}` : t('taskassign.queue')}
                        </span>
                        <button type="button" onClick={() => removeLine(i)}
                          style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', fontSize: 'var(--fs-h3)' }}
                          title={t('app.delete')}><i className="ti ti-x" /></button>
                      </div>
                    ))}
                  </div>
                )}
                <div style={{ marginTop: 10, fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                  {lines.length} {t('taskassign.assign_abbr')} × {nModels} {t('taskassign.models')} = <strong style={{ color: 'var(--text-main)' }}>{totalTasques}</strong> {t('taskassign.tasks')}
                </div>
              </div>
            )}

            {submitError && (
              <div style={{ marginTop: 10, fontSize: 'var(--fs-body)', padding: '8px 12px', borderRadius: 6, background: 'var(--err-bg)', color: 'var(--err)' }}>
                {submitError}
              </div>
            )}
          </div>
        </div>

        {/* ── FOOTER ── */}
        <div style={{
          display: 'flex', justifyContent: 'flex-end', gap: 8, padding: '14px 22px',
          borderTop: '1px solid var(--border)',
        }}>
          <button onClick={onClose} style={{ ...selS, cursor: 'pointer' }}>{t('app.cancel')}</button>
          <button onClick={onConfirm} disabled={!lines.length || submitting}
            style={{
              ...primaryBtn, marginLeft: 0,
              opacity: (!lines.length || submitting) ? 0.5 : 1,
              cursor: (!lines.length || submitting) ? 'not-allowed' : 'pointer',
            }}>
            {submitting
              ? <><i className="ti ti-loader-2" /> {t('taskassign.assigning')}</>
              : <><i className="ti ti-arrow-right" /> {t('app.confirm')} → {totalTasques} {totalTasques === 1 ? t('taskassign.task') : t('taskassign.tasks')}</>}
          </button>
        </div>
      </div>
    </div>
  )
}
