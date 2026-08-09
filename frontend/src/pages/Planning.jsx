import { useState, useEffect, useCallback, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import i18n from '../i18n'
import {
  DndContext, closestCenter, PointerSensor, KeyboardSensor, useSensor, useSensors,
} from '@dnd-kit/core'
import {
  SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy, useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import useAuthStore from '../store/auth'
import { models as modelsApi, modelTasks as modelTaskItems, users as usersApi, plan as planApi } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import PageMenu from '../components/ui/PageMenu'
import { apagat, botoPri, botoTer, selS } from '../components/ui/buttons'
import TaskAssignWizard from '../components/TaskAssignWizard'
import DashboardGovPanel from '../components/planning/DashboardGovPanel'
import ProjectGantt from '../components/planning/ProjectGantt'
import InformesPanel from '../components/planning/InformesPanel'
import RegistreActivitat from './RegistreActivitat'

// Tram 2 — Pantalla "Planificació": dues carpetes Pendents/Assignades (gated define_tasks/configure).
// Pendents = models SENSE cap tasca no-Done assignada. Assignades = models amb ALMENYS UNA no-Done amb tècnic.
// Les tasques Done NO compten per a la classificació i són IMMUTABLES (autor + dates es conserven).
// Assignar/desassignar/reassignar = compute automàtic al backend (cua sencera del tècnic).
// DATES: planned_* venen en UTC del serializer → es converteixen a LOCAL (Europe/Madrid) per pintar;
// data_objectiu és una data de calendari. NO es barreja amb cap altra font.
const MONO = 'IBM Plex Mono, monospace'
// §1 · LA SELECCIÓ DE LA CASA ÉS `--sel`, NO EL TARONJA. `CREMA`/`AMBER` eren `--warn-bg`/
// `--warn` fent de fons de fila seleccionada i de rètol de carpeta: taronja de SEMÀFOR fent de
// selecció, que és exactament el defecte que A4 va haver de treure de `/garment-types`. El
// semàfor és per a la DADA (aquí, els tres estats de viabilitat), mai per a «on soc».
const SEL = 'var(--sel)'
const TZ = 'Europe/Madrid'

// §2 · capçalera de llista = th 10px MAJÚSCULES tracking .08em «a tot arreu». I el filet intern
// de taula és `--line-soft`, no mig píxel d'un àlies de farciment.
const thS = {
  fontFamily: MONO, fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-soft)', textAlign: 'left',
  padding: '8px 10px', textTransform: 'uppercase', letterSpacing: '.08em',
  borderBottom: '1px solid var(--line)', whiteSpace: 'nowrap',
}
const tdS = { padding: '8px 10px', fontSize: 'var(--fs-body)', borderBottom: '1px solid var(--line-soft)', verticalAlign: 'middle' }

function localDateTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(i18n.language || 'ca',
    { timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}
function localDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString(i18n.language || 'ca', { timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric' })
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

// ── Helpers de viabilitat (purs) ──────────────────────────────────────────
// Aproximació estàndard: dl-dv laborables, sense festius. Jornada 420 min/dia.
function restarDiesLaborables(dataISO, dies) {
  if (!dataISO || !dies || dies <= 0) return null
  const d = new Date(dataISO + 'T00:00:00')
  let restants = Math.ceil(dies)
  while (restants > 0) {
    d.setDate(d.getDate() - 1)
    const dow = d.getDay()
    if (dow !== 0 && dow !== 6) restants--   // 0=diumenge, 6=dissabte
  }
  return d.toISOString().slice(0, 10)
}

// Retorna { latestStart, semafor, diesNecessaris }. semafor: on_track|at_risk|critical
function calcViabilitat(totalMinuts, dataObjectiu, predictedEnd) {
  if (!totalMinuts || !dataObjectiu) return null
  const diesNecessaris = totalMinuts / 420
  const latestStart = restarDiesLaborables(dataObjectiu, Math.ceil(diesNecessaris))
  const avui = new Date().toISOString().slice(0, 10)
  let semafor = 'on_track'
  if (predictedEnd && predictedEnd > dataObjectiu) {
    semafor = latestStart && latestStart < avui ? 'critical' : 'at_risk'
  }
  return { latestStart, semafor, diesNecessaris }
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

// Panell de la cua de tasques. UNA sola lògica de càrrega (les 3 fonts) i un sol estat; el `mode`
// decideix QUINA carpeta es mostra:
//   mode='pending'  → tab PLANIFICACIÓ: només models NO assignats (el que falta per col·locar).
//   mode='assigned' → tab ASSIGNACIÓ: models assignats per tècnic, amb reordenar/desassignar/reassignar.
// Abans era un sol panell amb un selector intern Pendents/Assignades; M-Planning-complet el parteix en
// dos tabs del shell de govern reusant EXACTAMENT la mateixa lògica (assignar/reordenar/reassignar).
// La gestió de l'accés (canPlan) la fa el shell; aquí només es carrega quan l'usuari hi té dret.
function PlanificacioPanel({ mode = 'pending' }) {
  const { t } = useTranslation()
  const me = useAuthStore(s => s.user)
  const canPlan = !!me?.capabilities?.some(c => c === 'define_tasks' || c === 'configure')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)   // { type, text }
  const tab = mode === 'assigned' ? 'assigned' : 'pending'   // carpeta fixada pel tab que munta el panell
  const [search, setSearch] = useState('')
  const [rows, setRows] = useState([])
  const [usersById, setUsersById] = useState({})
  const [techOptions, setTechOptions] = useState([])
  const [selected, setSelected] = useState(new Set())   // model_ids a Pendents
  const [expanded, setExpanded] = useState(new Set())   // model_ids desplegats a Assignades
  const [modal, setModal] = useState(null)              // { modelIds:[], single?:row }
  const [optimistic, setOptimistic] = useState({})      // { [techId]: [model_ids ordenats] } (reorder òptic)

  const load = useCallback(() => {
    setLoading(true)
    return Promise.all([
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
        const techIds = [...new Set(nonDone.map(x => x.assignee).filter(Boolean))]
        const starts = nonDone.map(x => x.planned_start).filter(Boolean).sort()
        const ends = nonDone.map(x => x.planned_end).filter(Boolean).sort()
        const predEnd = ends.length ? ends[ends.length - 1] : null
        const risc = !!(predEnd && m.data_objectiu && localISODate(predEnd) > m.data_objectiu)
        const temps = nonDone.reduce((s, x) => s + (x.estimated_minutes || 0), 0)
        const viab = calcViabilitat(temps, m.data_objectiu, localISODate(predEnd))
        out.push({
          id: m.model_id, codi: m.model_codi, nom: m.model_nom, prioritat: m.prioritat,
          reanchored_by_start: m.reanchored_by_start,   // C4d — marcador "+"
          data_objectiu: m.data_objectiu, temporada: m.temporada,
          folder: techIds.length ? 'assigned' : 'pending',
          nonDoneCount: nonDone.length, techIds,
          predStart: starts.length ? starts[0] : null, predEnd,
          temps, viab,
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
  // C4 — invalidació: un inici real (auto-start) en una altra superfície pot reancorar el pla;
  // Planificació és lectora del mateix pla → recarrega quan s'emet 'plan:changed'.
  useEffect(() => {
    if (!canPlan) return
    const h = () => load()
    window.addEventListener('plan:changed', h)
    return () => window.removeEventListener('plan:changed', h)
  }, [canPlan, load])

  const filtered = useMemo(() => {
    const s = search.trim().toLowerCase()
    return rows.filter(r => r.folder === tab &&
      (!s || (r.codi || '').toLowerCase().includes(s) || (r.nom || '').toLowerCase().includes(s)))
  }, [rows, tab, search])

  // Assignades AGRUPAT per tècnic: cada model "explotat" per tècnic (apareix al grup de CADA tècnic
  // que hi té tasques no-Done). predStart/predEnd/temps es calculen sobre les tasques d'AQUELL tècnic.
  // (Explotat per tècnic, lògicament correcte; pendent de validació visual quan existeixi un model
  //  repartit entre tècnics — avui NO n'hi ha cap a les dades; no s'assumeix techIds.length===1.)
  const assignedGroups = useMemo(() => {
    const s = search.trim().toLowerCase()
    const groups = {}
    for (const r of rows) {
      if (r.folder !== 'assigned') continue
      if (s && !(r.codi || '').toLowerCase().includes(s) && !(r.nom || '').toLowerCase().includes(s)) continue
      for (const techId of r.techIds) {
        const tts = r.tasks.filter(x => x.assignee === techId && x.status !== 'Done')
        const starts = tts.map(x => x.planned_start).filter(Boolean).sort()
        const ends = tts.map(x => x.planned_end).filter(Boolean).sort()
        const predStart = starts.length ? starts[0] : null
        const predEnd = ends.length ? ends[ends.length - 1] : null
        const risc = !!(predEnd && r.data_objectiu && localISODate(predEnd) > r.data_objectiu)
        const temps = tts.reduce((a, x) => a + (x.estimated_minutes || 0), 0)
        const viab = calcViabilitat(temps, r.data_objectiu, localISODate(predEnd))
        ;(groups[techId] ||= { techId, name: usersById[techId] || `#${techId}`, rows: [] })
          .rows.push({ ...r, _techId: techId, predStart, predEnd, risc, temps, viab })
      }
    }
    const list = Object.values(groups)
    for (const g of list) {
      g.rows.sort((a, b) => (a.predStart || '').localeCompare(b.predStart || ''))   // ordre real planificat
      const ord = optimistic[g.techId]
      if (ord) {   // reorder òptic pendent: respecta l'ordre arrossegat fins que load() reconciliï
        const pos = new Map(ord.map((id, i) => [id, i]))
        g.rows.sort((a, b) => (pos.get(a.id) ?? 1e9) - (pos.get(b.id) ?? 1e9))
      }
    }
    return list.sort((a, b) => a.name.localeCompare(b.name))
  }, [rows, search, usersById, optimistic])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  // Drag dins un grup de tècnic → reorder òptic immediat + plan/reorder + load() (reconcilia dates).
  // Drag NOMÉS dins el grup (cada grup és un SortableContext aïllat → no es pot moure entre tècnics).
  const onGroupReorder = (techId, rowsOfGroup) => ({ active, over }) => {
    if (!over || active.id === over.id) return
    const oldIdx = rowsOfGroup.findIndex(r => r.id === active.id)
    const newIdx = rowsOfGroup.findIndex(r => r.id === over.id)
    if (oldIdx < 0 || newIdx < 0) return
    const model_ids = arrayMove(rowsOfGroup, oldIdx, newIdx).map(r => r.id)
    setOptimistic(o => ({ ...o, [techId]: model_ids }))
    setSaving(true); setFeedback(null)
    planApi.reorder({ assignee_id: techId, model_ids })
      .then(() => load())
      .then(() => { setOptimistic(o => { const n = { ...o }; delete n[techId]; return n }); setFeedback({ type: 'ok', text: t('planning.saved_reorder') }) })
      .catch(e => { setOptimistic(o => { const n = { ...o }; delete n[techId]; return n }); setFeedback({ type: 'err', text: e?.response?.data?.error || t('planning.error') }) })
      .finally(() => setSaving(false))
  }

  const toggleSel = (id) => setSelected(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })
  const toggleExp = (id) => setExpanded(s => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

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
  // C3 — esborrar una tasca PENDING (el backend només ho permet en Pending; 409 altrament).
  // La cascada de pla (recompute + cua + predicted_*) la fa el backend; aquí només recarreguem.
  const doDeleteTask = (taskId) => {
    if (!window.confirm(t('planning.confirm_delete_task'))) return
    setSaving(true); setFeedback(null)
    modelTaskItems.remove(taskId)
      .then(() => { setFeedback({ type: 'ok', text: t('planning.deleted_task') }); load() })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.error || t('planning.error') }))
      .finally(() => setSaving(false))
  }

  return (
    <div style={{ minWidth: 0, maxWidth: '100%' }}>
      <Feedback feedback={feedback} />

      {/* §8e · EL COMPTADOR MANA I LA CERCA HI VA AL COSTAT, mateixa línia — la forma canònica
          de tota llista de la casa, la mateixa de `/models`. Aquí hi havia una PÍNDOLA TARONJA
          (`--warn-bg` + `--warn` a pes 600) fent de rètol de carpeta amb el recompte a dins:
          semàfor pintant una etiqueta de navegació, i un comptador amagat entre parèntesis
          quan la §8e diu que «ELS VALORS MANEN». */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 600, color: 'var(--text-main)' }}>
          {rows.filter(r => r.folder === tab).length}
        </span>
        <span style={{
          fontFamily: MONO, fontSize: 'var(--fs-caption)', fontWeight: 600, letterSpacing: '.08em',
          textTransform: 'uppercase', color: 'var(--text-soft)',
        }}>{t(`planning.${tab === 'assigned' ? 'tab_assigned' : 'tab_pending'}`)}</span>
        <input value={search} onChange={e => setSearch(e.target.value)}
               placeholder={t('planning.search_ph')} aria-label={t('planning.search_ph')}
               style={{ ...selS, flex: '0 1 280px', minWidth: 180 }} />
        {/* §5.1 · L'acció primària de la carpeta «pendents»: assignar és el que has vingut a fer
            aquí. És l'ÚNIC blau de la pantalla i només apareix quan hi ha selecció. */}
        {tab === 'pending' && selected.size > 0 && (
          <button onClick={() => setModal({ modelIds: [...selected], single: selected.size === 1 ? rows.find(r => r.id === [...selected][0]) : null })}
                  style={{ ...botoPri, marginLeft: 'auto' }}>
            <i className="ti ti-user-plus" aria-hidden="true" style={{ fontSize: 14, color: 'currentColor' }} />
            {t('planning.assign')} ({selected.size})
          </button>
        )}
      </div>

      {loading ? <Center>{t('planning.loading')}</Center>
        : tab === 'pending' ? (
            filtered.length === 0 ? <Center>{t('planning.empty_pending')}</Center>
              : (
                <div style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-card)', background: 'var(--panel)', fontSize: 'var(--fs-body)', overflowX: 'auto' }}>
                  <table style={{ borderCollapse: 'collapse', width: '100%' }}>
                    <thead><tr>
                      <th style={{ ...thS, width: 34 }}></th>
                      <th style={thS}>{t('planning.col_model')}</th>
                      <th style={thS}>{t('planning.col_name')}</th>
                      <th style={thS}>{t('planning.col_priority')}</th>
                      <th style={thS}>{t('planning.col_deadline')}</th>
                      <th style={thS}>{t('planning.col_max_start')}</th>
                      <th style={thS}>{t('planning.col_pending_count')}</th>
                    </tr></thead>
                    <tbody>
                      {filtered.map(r => (
                        <tr key={r.id}>
                          <td style={tdS}><input type="checkbox" checked={selected.has(r.id)} onChange={() => toggleSel(r.id)} /></td>
                          <td style={{ ...tdS, fontFamily: MONO, fontWeight: 600 }}>
                            {r.reanchored_by_start && <i className="ti ti-plus" title={t('planning.gantt.reanchored')} style={{ color: 'var(--gold)', marginRight: 4 }} />}
                            {r.codi}</td>
                          <td style={tdS}>{r.nom}</td>
                          <td style={tdS}>{r.prioritat}</td>
                          <td style={tdS}>{r.data_objectiu || '—'}</td>
                          <td style={{ ...tdS, color: (r.viab?.latestStart && r.viab.latestStart < new Date().toISOString().slice(0, 10)) ? 'var(--err)' : 'inherit' }}>
                            {r.viab?.latestStart || '—'}
                          </td>
                          <td style={tdS}>{r.nonDoneCount}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
          ) : (
            assignedGroups.length === 0 ? <Center>{t('planning.empty_assigned')}</Center>
              : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                  {assignedGroups.map(g => (
                    <TechGroup key={g.techId} g={g} t={t} usersById={usersById} techOptions={techOptions}
                               sensors={sensors} expanded={expanded} onToggle={toggleExp}
                               onDragEnd={onGroupReorder(g.techId, g.rows)}
                               onUnassign={doUnassign} onReassign={doReassign} onDeleteTask={doDeleteTask} saving={saving} />
                  ))}
                </div>
              )
          )}

      {modal?.modelIds && (
        <TaskAssignWizard
          modelIds={modal.modelIds}
          onClose={() => setModal(null)}
          onSuccess={() => { setModal(null); load() }}
        />
      )}
    </div>
  )
}

// Grup d'una cua de tècnic: capçalera + taula amb DnD (un SortableContext aïllat → drag NOMÉS
// dins el grup). Reaprofita el patró @dnd-kit d'EditableTable.
function TechGroup({ g, t, usersById, techOptions, sensors, expanded, onToggle, onDragEnd, onUnassign, onReassign, onDeleteTask, saving }) {
  return (
    <div style={{ border: '1px solid var(--line)', borderRadius: 'var(--r-card)', background: 'var(--panel)', fontSize: 'var(--fs-body)', overflowX: 'auto' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid var(--line)' }}>
        <i className="ti ti-user" aria-hidden="true" style={{ fontSize: 16, color: 'var(--text-soft)' }} />
        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', fontWeight: 600, color: 'var(--text-main)' }}>{g.name}</span>
        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }}>· {g.rows.length} {t('planning.models_word')}</span>
        <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontFamily: MONO }}>{t('planning.drag_hint')}</span>
      </div>
      <table style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead><tr>
          <th style={{ ...thS, width: 28 }}></th>
          <th style={{ ...thS, width: 28 }}></th>
          <th style={thS}>{t('planning.col_model')}</th>
          <th style={thS}>{t('planning.col_start')}</th>
          <th style={thS}>{t('planning.col_estimate')}</th>
          <th style={thS}>{t('planning.col_end')}</th>
          <th style={thS}></th>
        </tr></thead>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={g.rows.map(r => r.id)} strategy={verticalListSortingStrategy}>
            <tbody>
              {g.rows.map(r => (
                <SortableRowAssigned key={r.id} r={r} t={t} usersById={usersById} techOptions={techOptions}
                  expanded={expanded.has(r.id)} onToggle={() => onToggle(r.id)}
                  onUnassign={() => onUnassign(r.id)} onReassign={onReassign} onDeleteTask={onDeleteTask} saving={saving} />
              ))}
            </tbody>
          </SortableContext>
        </DndContext>
      </table>
    </div>
  )
}

function SortableRowAssigned({ r, t, usersById, techOptions, expanded, onToggle, onUnassign, onReassign, onDeleteTask, saving }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: r.id })
  const style = {
    transform: CSS.Transform.toString(transform), transition,
    opacity: isDragging ? 0.5 : 1,
    // §1 · «on soc» = `--sel`. Era `--warn-bg` (taronja de semàfor) tant per a la fila que
    // s'arrossega com per a la desplegada: el taronja és marca de DADA (aquí, la viabilitat de
    // la fila), i fer-lo servir per a la selecció desdibuixa totes dues coses alhora.
    background: isDragging || expanded ? SEL : 'transparent',
  }
  return (
    <>
      <tr ref={setNodeRef} style={style}>
        <td style={tdS}>
          {/* §8 · icona Tabler de 16px, no un CARÀCTER tipogràfic. El `⠿` és un braille: no té
              ni el traç ni la mida del sistema, i cada font el dibuixa d'una manera. Mateixa
              correcció que A10 va fer amb el `▼` de les seccions plegables. */}
          <span {...attributes} {...listeners} title={t('planning.drag_hint')} aria-label={t('planning.drag_hint')}
            style={{ cursor: 'grab', color: 'var(--text-soft)', fontSize: 16, display: 'inline-flex', lineHeight: 1 }}>
            <i className="ti ti-grip-vertical" aria-hidden="true" style={{ fontSize: 'inherit', color: 'currentColor' }} />
          </span>
        </td>
        <td style={{ ...tdS, cursor: 'pointer' }} onClick={onToggle}>
          <i className={`ti ti-chevron-${expanded ? 'down' : 'right'}`} style={{ fontSize: 14 }} />
        </td>
        <td style={{ ...tdS, fontFamily: MONO, fontWeight: 600, cursor: 'pointer' }} onClick={onToggle}>
          {r.reanchored_by_start && <i className="ti ti-plus" title={t('planning.gantt.reanchored')} style={{ color: 'var(--gold)', marginRight: 4 }} />}
          {r.codi}
          {r.viab?.semafor === 'critical' && <span style={{ marginLeft: 8, color: 'var(--err)', fontSize: 'var(--fs-body)', fontWeight: 600 }}>{t('planning.critical')}</span>}
          {/* §1b(d) · el taronja de TEXT és `--warn-ink` (5.32:1), no `--warn-state`: com a text
              sobre el seu fons, el taronja de marca dona 1.86:1 i contradiu el vet de C5. */}
          {r.viab?.semafor === 'at_risk' && <span style={{ marginLeft: 8, color: 'var(--warn-ink)', fontSize: 'var(--fs-body)', fontWeight: 600 }}>{t('planning.at_risk')}</span>}
          {r.viab?.semafor === 'on_track' && <span style={{ marginLeft: 8, color: 'var(--ok)', fontSize: 'var(--fs-body)' }}>{t('planning.on_track')}</span>}
          <div style={{ fontFamily: 'inherit', fontWeight: 400, color: 'var(--text-soft)', fontSize: 'var(--fs-body)' }}>{r.nom}</div>
        </td>
        <td style={tdS}>{localDate(r.predStart)}</td>
        <td style={tdS}>{fmtMins(r.temps)}</td>
        <td style={{ ...tdS, color: r.risc ? 'var(--err)' : 'inherit' }}>{localDate(r.predEnd)}</td>
        <td style={tdS}>
          {/* §5.4 · TERCIÀRIA: desassignar és un gest de la fila, no l'acció de la pantalla. */}
          <button onClick={onUnassign} disabled={saving} title={t('planning.unassign')}
            style={{ ...botoTer, padding: '4px 10px', ...(saving ? apagat : null) }}>{t('planning.unassign')}</button>
        </td>
      </tr>
      {/* 🚨 AL FONS D'AQUESTA FILA HI HAVIA `var(--bg, #faf9f7)` I `--bg` NO EXISTEIX A `:root`:
          el que es pintava era SEMPRE el literal de reserva, un crema que ningú havia decidit i
          que cap cerca de tokens troba. El fons de pàgina de la norma és `--bg-page`.
          (El comentari va AQUÍ i no dins del `{expanded && (…)}`: allà encara ets en context
          d'expressió i les claus es llegirien com un OBJECTE literal, no com un comentari.) */}
      {expanded && (
        <tr><td colSpan={7} style={{ padding: 0, background: 'var(--bg-page)' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <tbody>
              {r.tasks.map(tk => {
                const done = tk.status === 'Done'
                return (
                  <tr key={tk.id}>
                    <td style={{ ...tdS, paddingLeft: 40, width: 180, fontFamily: MONO }}>{tk.task_type_code}</td>
                    <td style={{ ...tdS, width: 200 }}>
                      {done ? (
                        <span style={{ color: 'var(--text-soft)' }}>{t('planning.author')}: {usersById[tk.assignee] || '—'}</span>
                      ) : (
                        <select value={tk.assignee || ''} disabled={saving} onChange={e => onReassign(tk.id, Number(e.target.value))} style={{ ...selS, padding: '3px 6px' }}>
                          {!tk.assignee && <option value="">—</option>}
                          {techOptions.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}
                        </select>
                      )}
                    </td>
                    <td style={{ ...tdS, width: 110 }}>
                      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: done ? 'var(--ok)' : 'var(--text-soft)' }}>{tk.status}</span>
                    </td>
                    <td style={tdS}>
                      {done ? `${t('planning.done_at')}: ${localDate(tk.finished_at)}`
                        : `${localDateTime(tk.planned_start)} → ${localDateTime(tk.planned_end)}`}
                    </td>
                    <td style={{ ...tdS, width: 36, textAlign: 'right' }}>
                      {/* Esborrar només visible/actiu en tasques Pending (C3). */}
                      {tk.status === 'Pending' && (
                        <button onClick={() => onDeleteTask(tk.id)} disabled={saving} title={t('planning.delete_task')}
                          style={{ background: 'none', border: 'none', cursor: saving ? 'not-allowed' : 'pointer', color: 'var(--err)', padding: 2, fontSize: 14, lineHeight: 1 }}>
                          {/* §8 · tinta DESTRUCTIVA i 14px (icona dins d'un botó). */}
                          <i className="ti ti-trash" aria-hidden="true" style={{ fontSize: 'inherit', color: 'currentColor' }} />
                        </button>
                      )}
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

// Shell de govern (patró del shell de tabs de ModelSheet): capçalera + banda de pestanyes.
// Tabs: Dashboard (panell de govern, s'omple per blocs) · Planificació (contingut actual) ·
// Assignació (futur) · Calendari de projecte (Gantt, model/dies) · Informes (futur).
// El tab "Calendari" antic (PlanningCalendar incrustat) s'ha jubilat; el calendari de l'EXECUTOR
// segueix viu via ruta /planificacio/calendari + entrada de menú del tècnic (Sidebar, cap 'execute').
// Gating de pantalla: define_tasks||configure (el mateix que tenia Planning).
const GOV_TABS = ['dashboard', 'planificacio', 'assignacio', 'calendari_projecte', 'informes', 'registre']

export default function Planning() {
  const { t } = useTranslation()
  const me = useAuthStore(s => s.user)
  const canPlan = !!me?.capabilities?.some(c => c === 'define_tasks' || c === 'configure')
  const [activeTab, setActiveTab] = useState('dashboard')

  if (me == null) return <Center>{t('planning.loading')}</Center>
  // §8c · l'estat sense accés era una caixa centrada amb una icona de 32px (fora de les tres
  // mides de la §8) i tinta `--gray`. Passa a la forma de la casa: frase tènue cursiva.
  if (!canPlan) return (
    <div style={{ padding: 16, fontSize: 'var(--fs-body)', color: 'var(--text-faint)', fontStyle: 'italic', fontFamily: MONO }}>
      {t('planning.no_access')}
    </div>
  )

  return (
    <>
      {/* §8b · MENÚ DE PANTALLA. Els sis tabs de govern eren botons amb l'ACTIU EN DAURAT PLE i
          els altres sobre `--bg-muted`: daurat ple fent de navegació, que és el que la norma
          prohibeix («ni blau ni daurat ple: navegar no és ni acció ni marca»). Són seccions
          grans d'una mateixa entitat → píndoles del §8b-bis. La fletxa porta al tauler, que és
          d'on penja aquesta pantalla al menú lateral. */}
      <div style={{ margin: '-1.5rem -1.5rem 0' }}>
        <PageMenu
          backTo="/"
          backTitle={t('planning.back_title')}
          items={GOV_TABS.map(tab => ({
            key: tab, label: t(`planning.tabs.${tab}`),
            active: activeTab === tab, onClick: () => setActiveTab(tab),
          }))}
        />
      </div>

      <div style={{ minWidth: 0, maxWidth: '100%', paddingTop: 16 }}>
      {/* §8b.3 · IDENTITAT sobre el fons de pàgina, sense contenidor. El subtítol baixa a
          caption i deixa el pes 300, que no és cap pes de la casa (§2: 400 · 500 · 600). */}
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', lineHeight: '28px', fontWeight: 500, marginBottom: 4, color: 'var(--text-main)', fontFamily: MONO }}>{t('planning.title')}</h1>
        <p style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', fontFamily: MONO }}>{t('planning.gov_subtitle')}</p>
      </div>

      {activeTab === 'dashboard' && <DashboardGovPanel me={me} />}
      {activeTab === 'planificacio' && <PlanificacioPanel mode="pending" />}
      {activeTab === 'assignacio' && <PlanificacioPanel mode="assigned" />}
      {activeTab === 'calendari_projecte' && <ProjectGantt t={t} />}
      {activeTab === 'informes' && <InformesPanel me={me} />}
      {activeTab === 'registre' && <RegistreActivitat />}
      </div>
    </>
  )
}

