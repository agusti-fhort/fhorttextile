import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { models as modelsApi, modelTasks as modelTaskItems, users as usersApi } from '../api/endpoints'

// Tram 2 — Pantalla "Planificació": dues carpetes Pendents/Assignades (gated define_tasks/configure).
// Pendents = models amb tasques no-Done SENSE tècnic. Assignades = totes les no-Done amb tècnic.
// Les tasques Done NO compten per a la classificació i són IMMUTABLES (autor + dates es conserven).
// Assignar/desassignar/reassignar = compute automàtic al backend (cua sencera del tècnic).
// DATES: planned_* venen en UTC del serializer → es converteixen a LOCAL (Europe/Madrid) per pintar;
// data_objectiu és una data de calendari. NO es barreja amb cap altra font.
const MONO = 'IBM Plex Mono, monospace'
const CREMA = 'var(--warn-bg)'
const AMBER = 'var(--warn)'
const TZ = 'Europe/Madrid'

const selS = {
  fontFamily: MONO, fontSize: 12, padding: '6px 10px',
  border: '0.5px solid var(--gray-l)', borderRadius: 6, background: 'var(--white)', color: 'var(--text-main)',
}
const thS = {
  fontFamily: MONO, fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textAlign: 'left',
  padding: '8px 10px', textTransform: 'uppercase', letterSpacing: '.04em',
  borderBottom: '0.5px solid var(--gray-l)', whiteSpace: 'nowrap',
}
const tdS = { padding: '8px 10px', fontSize: 12, borderBottom: '0.5px solid var(--gray-l)', verticalAlign: 'middle' }

function localDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ca-ES',
    { timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function localDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('ca-ES', { timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric' })
}
function localISODate(iso) {   // 'YYYY-MM-DD' en hora local (per comparar amb data_objectiu)
  if (!iso) return null
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(iso))
}
function fmtMins(m) {
  if (!m) return '—'
  const h = Math.floor(m / 60), mm = m % 60
  return h ? (mm ? `${h}h ${mm}m` : `${h}h`) : `${mm}m`
}

async function fetchAllPages(apiFn, baseParams = {}) {
  const out = []; let page = 1
  for (;;) {
    const res = await apiFn({ ...baseParams, page })
    const data = res.data
    out.push(...(data?.results ?? (Array.isArray(data) ? data : [])))
    if (data?.next) page++; else break
  }
  return out
}

export default function Planning() {
  const { t } = useTranslation()
  const me = useAuthStore(s => s.user)
  const canPlan = !!me?.capabilities?.some(c => c === 'define_tasks' || c === 'configure')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)   // { type, text }
  const [tab, setTab] = useState('pending')
  const [search, setSearch] = useState('')
  const [rows, setRows] = useState([])
  const [usersById, setUsersById] = useState({})
  const [techOptions, setTechOptions] = useState([])
  const [selected, setSelected] = useState(new Set())   // model_ids a Pendents
  const [expanded, setExpanded] = useState(new Set())   // model_ids desplegats a Assignades
  const [modal, setModal] = useState(null)              // { modelIds:[], single?:row }

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([
      fetchAllPages(modelTaskItems.byModel, { all: 'true' }),
      fetchAllPages(modelTaskItems.list, {}),
      fetchAllPages(usersApi.list, {}),
    ]).then(([meta, tasks, users]) => {
      // ModelTask.assignee és un UserProfile.id → mapegem i seleccionem SEMPRE per profile_id
      // (no User.id), per no dependre de cap coincidència d'ids.
      const ubi = {}; users.forEach(u => { if (u.profile_id != null) ubi[u.profile_id] = u.full_name || u.username })
      setUsersById(ubi)
      setTechOptions(users.filter(u => u.actiu !== false && u.profile_id != null)
        .map(u => ({ id: u.profile_id, name: u.full_name || u.username })))
      const byModel = {}; tasks.forEach(tk => { (byModel[tk.model] ||= []).push(tk) })
      const out = []
      meta.forEach(m => {
        const ts = byModel[m.model_id] || []
        const nonDone = ts.filter(x => x.status !== 'Done')
        if (nonDone.length === 0) return
        const done = ts.filter(x => x.status === 'Done')
        const unassigned = nonDone.filter(x => !x.assignee)
        const techIds = [...new Set(nonDone.map(x => x.assignee).filter(Boolean))]
        const starts = nonDone.map(x => x.planned_start).filter(Boolean).sort()
        const ends = nonDone.map(x => x.planned_end).filter(Boolean).sort()
        const predEnd = ends.length ? ends[ends.length - 1] : null
        const risc = !!(predEnd && m.data_objectiu && localISODate(predEnd) > m.data_objectiu)
        out.push({
          id: m.model_id, codi: m.model_codi, nom: m.model_nom, prioritat: m.prioritat,
          data_objectiu: m.data_objectiu, temporada: m.temporada,
          folder: unassigned.length ? 'pending' : 'assigned',
          nonDoneCount: nonDone.length, techIds,
          predStart: starts.length ? starts[0] : null, predEnd,
          temps: nonDone.reduce((s, x) => s + (x.estimated_minutes || 0), 0),
          risc, tasks: ts.slice().sort((a, b) => (a.task_type_code || '').localeCompare(b.task_type_code || '')),
          nonDone,
        })
      })
      out.sort((a, b) => (a.codi || '').localeCompare(b.codi || ''))
      setRows(out); setSelected(new Set())
    }).catch(() => setFeedback({ type: 'err', text: t('planning.error') }))
      .finally(() => setLoading(false))
  }, [t])

  useEffect(() => { if (canPlan) load() }, [canPlan, load])

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase()
    return rows.filter(r => r.folder === tab &&
      (!s || (r.codi || '').toLowerCase().includes(s) || (r.nom || '').toLowerCase().includes(s)))
  }, [rows, tab, search])

  const toggleSel = (id) => setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  const toggleExp = (id) => setExpanded(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  const doAssign = (assigneeId, taskIdsByModel) => {
    setSaving(true); setFeedback(null)
    Promise.all(modal.modelIds.map(mid =>
      modelsApi.assign(mid, { assignee_id: assigneeId, task_ids: taskIdsByModel?.[mid] })))
      .then(() => { setFeedback({ type: 'ok', text: t('planning.saved_assign') }); setModal(null); load() })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.error || t('planning.error') }))
      .finally(() => setSaving(false))
  }
  const doUnassign = (modelId) => {
    setSaving(true); setFeedback(null)
    modelsApi.unassign(modelId)
      .then(() => { setFeedback({ type: 'ok', text: t('planning.saved_unassign') }); load() })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.error || t('planning.error') }))
      .finally(() => setSaving(false))
  }
  const doReassign = (taskId, assigneeId) => {
    setSaving(true); setFeedback(null)
    modelTaskItems.patch(taskId, { assignee: assigneeId })
      .then(() => { setFeedback({ type: 'ok', text: t('planning.saved_reassign') }); load() })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.assignee?.[0] || e?.response?.data?.error || t('planning.error') }))
      .finally(() => setSaving(false))
  }

  if (me == null) return <Center>{t('planning.loading')}</Center>
  if (!canPlan) return (
    <div style={{ padding: '4rem 2rem', textAlign: 'center' }}>
      <i className="ti ti-lock" style={{ fontSize: 32, color: 'var(--gray)' }} />
      <p style={{ marginTop: 12, fontSize: 13, color: 'var(--gray)' }}>{t('planning.no_access')}</p>
    </div>
  )

  return (
    <div style={{ minWidth: 0, maxWidth: '100%' }}>
      <div style={{ marginBottom: '1rem' }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('planning.title')}</h1>
        <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('planning.subtitle')}</p>
      </div>

      {feedback && (
        <div style={{
          fontSize: 12, padding: '8px 12px', borderRadius: 6, marginBottom: 12,
          background: feedback.type === 'ok' ? 'var(--ok-bg)' : 'var(--err-bg)',
          color: feedback.type === 'ok' ? 'var(--ok)' : 'var(--err)',
        }}>{feedback.text}</div>
      )}

      {/* Tabs de carpeta + cerca */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', border: '0.5px solid var(--gray-l)', borderRadius: 8, overflow: 'hidden' }}>
          {[['pending', 'tab_pending'], ['assigned', 'tab_assigned']].map(([val, key]) => (
            <button key={val} onClick={() => setTab(val)} style={{
              fontFamily: MONO, fontSize: 12, padding: '7px 16px', border: 'none', cursor: 'pointer',
              background: tab === val ? CREMA : 'var(--white)', color: tab === val ? AMBER : 'var(--gray)',
              fontWeight: tab === val ? 600 : 400,
            }}>{t(`planning.${key}`)} ({rows.filter(r => r.folder === val).length})</button>
          ))}
        </div>
        <input value={search} onChange={e => setSearch(e.target.value)}
               placeholder={t('planning.search_ph')} style={{ ...selS, flex: '0 1 280px', minWidth: 180 }} />
        {tab === 'pending' && selected.size > 0 && (
          <button onClick={() => setModal({ modelIds: [...selected], single: selected.size === 1 ? rows.find(r => r.id === [...selected][0]) : null })}
                  style={primaryBtn}>
            <i className="ti ti-user-plus" style={{ fontSize: 14 }} />{t('planning.assign')} ({selected.size})
          </button>
        )}
      </div>

      {loading ? <Center>{t('planning.loading')}</Center>
        : filtered.length === 0 ? <Center>{t(tab === 'pending' ? 'planning.empty_pending' : 'planning.empty_assigned')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                {tab === 'pending' ? (
                  <>
                    <thead><tr>
                      <th style={{ ...thS, width: 34 }}></th>
                      <th style={thS}>{t('planning.col_model')}</th>
                      <th style={thS}>{t('planning.col_name')}</th>
                      <th style={thS}>{t('planning.col_priority')}</th>
                      <th style={thS}>{t('planning.col_deadline')}</th>
                      <th style={thS}>{t('planning.col_pending_count')}</th>
                    </tr></thead>
                    <tbody>
                      {filtered.map(r => (
                        <tr key={r.id}>
                          <td style={tdS}><input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSel(r.id)} /></td>
                          <td style={{ ...tdS, fontFamily: MONO, fontWeight: 600 }}>{r.codi}</td>
                          <td style={tdS}>{r.nom}</td>
                          <td style={tdS}>{r.prioritat}</td>
                          <td style={tdS}>{r.data_objectiu || '—'}</td>
                          <td style={tdS}>{r.nonDoneCount}</td>
                        </tr>
                      ))}
                    </tbody>
                  </>
                ) : (
                  <>
                    <thead><tr>
                      <th style={{ ...thS, width: 28 }}></th>
                      <th style={thS}>{t('planning.col_model')}</th>
                      <th style={thS}>{t('planning.col_technician')}</th>
                      <th style={thS}>{t('planning.col_start')}</th>
                      <th style={thS}>{t('planning.col_estimate')}</th>
                      <th style={thS}>{t('planning.col_end')}</th>
                      <th style={thS}></th>
                    </tr></thead>
                    <tbody>
                      {filtered.map(r => (
                        <RowAssigned key={r.id} r={r} t={t} usersById={usersById} techOptions={techOptions}
                                     expanded={expanded.has(r.id)} onToggle={() => toggleExp(r.id)}
                                     onUnassign={() => doUnassign(r.id)} onReassign={doReassign} saving={saving} />
                      ))}
                    </tbody>
                  </>
                )}
              </table>
            </div>
          )}

      {modal && (
        <AssignModal t={t} modal={modal} techOptions={techOptions} saving={saving}
                     onCancel={() => setModal(null)} onConfirm={doAssign} />
      )}
    </div>
  )
}

function Center({ children }) {
  return <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--gray)', fontSize: 13 }}>{children}</div>
}
const primaryBtn = {
  display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto', background: 'var(--gold)', color: '#fff',
  border: 'none', borderRadius: 6, padding: '7px 14px', fontSize: 12, fontWeight: 600, cursor: 'pointer', fontFamily: MONO,
}

function RowAssigned({ r, t, usersById, techOptions, expanded, onToggle, onUnassign, onReassign, saving }) {
  const techLabel = r.techIds.length === 1 ? (usersById[r.techIds[0]] || `#${r.techIds[0]}`)
    : t('planning.several', { n: r.techIds.length })
  return (
    <>
      <tr style={{ cursor: 'pointer', background: expanded ? CREMA : 'transparent' }} onClick={onToggle}>
        <td style={tdS}><i className={`ti ti-chevron-${expanded ? 'down' : 'right'}`} style={{ fontSize: 14 }} /></td>
        <td style={{ ...tdS, fontFamily: MONO, fontWeight: 600 }}>
          {r.codi}{r.risc && <span title={t('planning.at_risk')} style={{ marginLeft: 8, color: 'var(--err)', fontSize: 11, fontWeight: 600 }}>⚠ {t('planning.at_risk')}</span>}
          <div style={{ fontFamily: 'inherit', fontWeight: 400, color: 'var(--gray)', fontSize: 11 }}>{r.nom}</div>
        </td>
        <td style={tdS}>{techLabel}</td>
        <td style={tdS}>{localDate(r.predStart)}</td>
        <td style={tdS}>{fmtMins(r.temps)}</td>
        <td style={{ ...tdS, color: r.risc ? 'var(--err)' : 'inherit' }}>{localDate(r.predEnd)}</td>
        <td style={tdS} onClick={e => e.stopPropagation()}>
          <button onClick={onUnassign} disabled={saving} title={t('planning.unassign')} style={{
            background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
            padding: '4px 9px', fontSize: 11, fontFamily: MONO, color: 'var(--text-muted)',
          }}>{t('planning.unassign')}</button>
        </td>
      </tr>
      {expanded && (
        <tr><td colSpan={7} style={{ padding: 0, background: 'var(--bg, #faf9f7)' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <tbody>
              {r.tasks.map(tk => {
                const done = tk.status === 'Done'
                return (
                  <tr key={tk.id}>
                    <td style={{ ...tdS, paddingLeft: 40, width: 180, fontFamily: MONO }}>{tk.task_type_code}</td>
                    <td style={{ ...tdS, width: 200 }}>
                      {done ? (
                        <span style={{ color: 'var(--gray)' }}>{t('planning.author')}: {usersById[tk.assignee] || '—'}</span>
                      ) : (
                        <select value={tk.assignee || ''} disabled={saving} onChange={e => onReassign(tk.id, Number(e.target.value))} style={{ ...selS, padding: '3px 6px' }}>
                          {!tk.assignee && <option value="">—</option>}
                          {techOptions.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
                        </select>
                      )}
                    </td>
                    <td style={{ ...tdS, width: 110 }}>
                      <span style={{ fontFamily: MONO, fontSize: 11, color: done ? 'var(--ok)' : 'var(--text-muted)' }}>{tk.status}</span>
                    </td>
                    <td style={tdS}>
                      {done ? `${t('planning.done_at')}: ${localDate(tk.finished_at)}`
                        : `${localDateTime(tk.planned_start)} → ${localDateTime(tk.planned_end)}`}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </td></tr>
      )}
    </>
  )
}

function AssignModal({ t, modal, techOptions, saving, onCancel, onConfirm }) {
  const [assignee, setAssignee] = useState('')
  const single = modal.single
  const [taskSel, setTaskSel] = useState(() => new Set((single?.nonDone || []).map(x => x.id)))
  const toggleTask = (id) => setTaskSel(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  const confirm = () => {
    if (!assignee) return
    let taskIdsByModel
    if (single) taskIdsByModel = { [single.id]: [...taskSel] }   // selecció opcional de tasques (1 model)
    onConfirm(Number(assignee), taskIdsByModel)
  }
  return (
    <div onClick={onCancel} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50 }}>
      <div onClick={e => e.stopPropagation()} style={{ background: 'var(--white)', borderRadius: 12, padding: 22, width: 460, maxWidth: '92vw', maxHeight: '85vh', overflowY: 'auto' }}>
        <h2 style={{ fontSize: 16, fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('planning.assign_title')}</h2>
        <p style={{ fontSize: 12, color: 'var(--gray)', marginBottom: 16 }}>
          {single ? single.codi : t('planning.n_models', { n: modal.modelIds.length })}
        </p>
        <label style={{ fontSize: 11, fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{t('planning.choose_tech')}</label>
        <select value={assignee} onChange={e => setAssignee(e.target.value)} style={{ ...selS, width: '100%', marginTop: 6, marginBottom: 16 }}>
          <option value="">—</option>
          {techOptions.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
        </select>
        {single && (
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 11, fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase' }}>{t('planning.choose_tasks')}</label>
            <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 4 }}>
              {single.nonDone.map(x => (
                <label key={x.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                  <input type="checkbox" checked={taskSel.has(x.id)} onChange={() => toggleTask(x.id)} />
                  <span style={{ fontFamily: MONO }}>{x.task_type_code}</span>
                </label>
              ))}
            </div>
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button onClick={onCancel} style={{ ...selS, cursor: 'pointer' }}>{t('planning.cancel')}</button>
          <button onClick={confirm} disabled={!assignee || saving || (single && taskSel.size === 0)} style={{
            ...primaryBtn, marginLeft: 0, opacity: (!assignee || saving || (single && taskSel.size === 0)) ? 0.5 : 1,
          }}>{t('planning.confirm')}</button>
        </div>
      </div>
    </div>
  )
}
