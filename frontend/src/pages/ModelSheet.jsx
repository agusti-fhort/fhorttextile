import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Feedback from '../components/ui/Feedback'
import ActionsMenu from '../components/model/ActionsMenu'
import WatchpointDrawer from '../components/model/WatchpointDrawer'
import CheckMeasureEditor from '../components/model/CheckMeasureEditor'
import MeasuresEntryPanel from '../components/model/MeasuresEntryPanel'
import PropagatedEditor from './PropagatedEditor'
import Modal from '../components/ui/Modal'
import RuleSetCard from '../components/model/RuleSetCard'
import { models, watchpoints, modelTasks } from '../api/endpoints'
import { UPLOAD_ACCEPT } from '../utils/uploads'
import RegistreActivitatTab from '../components/model/RegistreActivitatTab'
import DashboardTab from '../components/model/DashboardTab'
import TasksTab from '../components/model/TasksTab'

const API = import.meta.env.VITE_API_URL || ''
// Menú net (PEÇA 5): Size Check absorbit a Mesures (taula base amb estadis), Producció retirat;
// Fitting → Escalat (editor propagat). v2: el Size Check antic queda jubilat — /size-check
// redirigeix a /mesures (App.jsx), aquí ja no hi ha cap branca 'Size Check'.
// 'Anàlisi IA' OCULTAT del menú (peça F): inert avui. El case i el component TabAIAnalysis es
// conserven (no destructiu); simplement no apareix a la banda de pestanyes.
const TABS = ['Dashboard', 'Resum', 'Mesures', 'Escalat', 'Fitxa tècnica', 'Fitxers', "Registre d'activitat", 'Tasques']
// L'id del tab (clau de lògica: activeTab===, defaultTab) es manté; només se'n tradueix l'etiqueta.
const TAB_LABELS = {
  'Dashboard': 'model_sheet.tab_dashboard',
  'Tasques': 'model_sheet.tab_tasks',
  'Resum': 'model_sheet.tab_summary',
  'Mesures': 'model.tabs.mesures',
  'Escalat': 'model_sheet.tab_grading',
  'Fitxa tècnica': 'model_sheet.tab_tech_sheet',
  'Fitxers': 'model.tabs.fitxers',
  "Registre d'activitat": 'model_sheet.tab_activity_log',
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

function afegirDiesLaborables(dataISO, dies) {
  if (!dataISO || !dies || dies <= 0) return null
  const d = new Date(dataISO + 'T00:00:00')
  let restants = Math.ceil(dies)
  while (restants > 0) {
    d.setDate(d.getDate() + 1)
    const dow = d.getDay()
    if (dow !== 0 && dow !== 6) restants--
  }
  return d.toISOString().slice(0, 10)
}

// Retorna { latestStart, semafor, diesNecessaris }. semafor: on_track|at_risk|critical
function calcViabilitat(totalMinuts, dataObjectiu, predictedEnd) {
  if (!totalMinuts || !dataObjectiu) return null
  const diesNecessaris = totalMinuts / 420   // jornada 1 tècnic
  const latestStart = restarDiesLaborables(dataObjectiu, Math.ceil(diesNecessaris))
  const avui = new Date().toISOString().slice(0, 10)
  let semafor = 'on_track'
  if (predictedEnd && predictedEnd > dataObjectiu) {
    semafor = latestStart && latestStart < avui ? 'critical' : 'at_risk'
  }
  return { latestStart, semafor, diesNecessaris }
}

const btnSecondary = {
  background: 'transparent',
  border: '0.5px solid var(--border)',
  borderRadius: 6, padding: '6px 12px', fontSize: 'var(--fs-body)',
  cursor: 'pointer', color: 'var(--text-main)',
  display: 'flex', alignItems: 'center', gap: 4,
}

const taskListFromResponse = (data) => data?.results || (Array.isArray(data) ? data : [])

export default function ModelSheet({ defaultTab = 'Dashboard', autoEdit = null }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const { t } = useTranslation()
  const [sp] = useSearchParams()
  // ?tab= permet obrir el full directament en una pestanya concreta (p.ex. ModelFabric → tab Mesures).
  // El task_id/session entrants (J1b) es plomaran a sobre d'aquest mateix mecanisme més endavant.
  const tabParam = sp.get('tab')
  const taskParam = sp.get('task_id')
  // ?mode=entry → "Definició POM" via URL: obre el tab Mesures en mode ENTRADA (genesi/wizard) encara
  // que el model JA tingui mesures (l'usuari ve a definir/afegir POMs, no a consultar).
  const entryMode = sp.get('mode') === 'entry'
  const [model, setModel] = useState(null)
  const [activeTab, setActiveTab] = useState(TABS.includes(tabParam) ? tabParam : defaultTab)
  const [taulaRows, setTaulaRows] = useState([])
  const [modelTaskRows, setModelTaskRows] = useState([])
  const [sizesAmbDades, setSizesAmbDades] = useState(null)
  const [deltes, setDeltes] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState(null)
  // Coherència B↔C: en tancar el drawer (escriptura) es bumpa per refrescar el fil del dashboard.
  const [wpVersion, setWpVersion] = useState(0)

  const reloadModel = useCallback(() => {
    fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders })
      .then(r => r.json()).then(setModel).catch(() => {})
  }, [id])

  // Rellegeix la taula de mesures (post-genesi: seed/import/manual). El tab Mesures decideix genesi↔
  // consulta a partir d'aquestes files (verge = cap base_value_cm).
  const reloadTaula = useCallback(() => {
    fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => { setTaulaRows(d.rows || []); setSizesAmbDades(d.sizes_amb_dades || null); setDeltes(d.deltes || null) })
      .catch(() => {})
  }, [id])

  const reloadTasks = useCallback(() => {
    modelTasks.listByModel(id)
      .then(res => setModelTaskRows(taskListFromResponse(res.data)))
      .catch(() => {})
  }, [id])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders }).then(r => r.json()),
      fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders }).then(r => r.json()),
      modelTasks.listByModel(id).then(r => r.data).catch(() => []),
    ]).then(([modelData, taulaData, taskData]) => {
      setModel(modelData)
      setTaulaRows(taulaData.rows || [])
      setSizesAmbDades(taulaData.sizes_amb_dades || null)
      setDeltes(taulaData.deltes || null)
      setModelTaskRows(taskListFromResponse(taskData))
    }).catch(() => setError(t('model_sheet.err_load')))
    .finally(() => setLoading(false))
  }, [id])

  const pomTask = modelTaskRows.find(task => task.task_type_code === 'pom')
  const hasBaseValue = taulaRows.some(r => r.base_value_cm != null)
  const pomDone = pomTask?.status === 'Done'
  const pomGenesisOpen = pomTask && ['InProgress', 'Paused'].includes(pomTask.status)
  const pomReady = pomDone && hasBaseValue

  // POM-genesi surt del tab Mesures lliure: Mesures només és treballable amb POM Done + base.
  // `task_id` de size_check continua sent treball, no genesi; `mode=entry` i pom oberta/pausada
  // obren la pantalla POM pròpia.
  const [mesuresEntry, setMesuresEntry] = useState(false)
  const prevTabRef = useRef(null)
  useEffect(() => {
    // Mentre carrega no decidim NI actualitzem el ref (si no, l'entrada directa ?tab=Mesures fixaria el
    // ref a 'Mesures' durant la càrrega i la genesi no s'avaluaria mai en acabar de carregar).
    if (loading) return
    if (activeTab === 'Mesures' && prevTabRef.current !== 'Mesures') {
      setMesuresEntry((entryMode || pomGenesisOpen) && !taskParam)
    }
    prevTabRef.current = activeTab
  }, [activeTab, loading, entryMode, taskParam, pomGenesisOpen])

  // Porta-menú: obre (crea-si-falta + auto-assign + En curs) la tasca `code` i navega a l'eina amb el
  // task_id. Reusa el servei open-task; el botó funciona encara que el model no tingui la tasca creada.
  const [openingTask, setOpeningTask] = useState(false)
  const openTaskAndGo = (code, toRoute) => {
    if (openingTask) return
    setOpeningTask(true)
    models.openTask(parseInt(id), code)
      .then(res => navigate(toRoute(res.data.task_id)))
      .catch(() => setFeedback({ type: 'err', text: t('model_sheet.open_task_err') }))
      .finally(() => setOpeningTask(false))
  }

  // FASE A — edició INLINE: la tab commuta consulta↔edició mantenint el context (sidebar+tabs+
  // capçalera+watchpoint), en comptes de navegar a /mesures·/escalat. openTask posa la tasca
  // InProgress (compta-temps); en sortir de mode edició es pausa. El lifecycle del timer es mou de
  // mount/unmount de ruta (EscalatTask/ModelMeasurements) a enter/exit de mode.
  const [editing, setEditing] = useState(null)        // null | 'Mesures' | 'Escalat'
  const [editTaskId, setEditTaskId] = useState(null)
  // PEÇA 2 — guard 400: open-task deixa la tasca En curs (InProgress). Aquest ref recorda quina tasca està
  // VIVA per pausar-la EXACTAMENT UN COP. Sense ell, exitEdit i el cleanup de desmuntatge demanaven tots
  // dos transition→Paused sobre la mateixa tasca → la 2a era Paused→Paused, que ALLOWED rebutja amb 400
  // (services_c.py). Nul = res a pausar (≈ task.status !== 'InProgress').
  const activeTaskRef = useRef(null)
  const pauseActiveTask = useCallback(() => {
    const tid = activeTaskRef.current
    if (tid == null) return                 // ja pausada o cap tasca En curs → no demanem transició (evita 400)
    activeTaskRef.current = null
    modelTasks.transition(tid, { to_status: 'Paused' }).catch(() => {})
  }, [])
  const enterEdit = (tab, code) => {
    if (openingTask) return
    setOpeningTask(true)
    models.openTask(parseInt(id), code)
      .then(res => {
        setEditTaskId(res.data.task_id)
        activeTaskRef.current = res.data.task_id   // open-task la deixa En curs → viva per pausar després
        // PUNT COMÚ: una tasca 'pom' obre el tab Mesures en mode ENTRADA (wizard), no edició de graella.
        // (size_check ve per URL i passa per editing='Mesures'; grading → tab Escalat.)
        if (tab === 'Mesures' && code === 'pom') setMesuresEntry(true)
        else setEditing(tab)
      })
      .catch(() => setFeedback({ type: 'err', text: t('model_sheet.open_task_err') }))
      .finally(() => setOpeningTask(false))
  }
  const exitEdit = useCallback(() => {
    pauseActiveTask()
    setEditTaskId(null)
    setEditing(null)
    setMesuresEntry(false)
  }, [pauseActiveTask])
  const finishPomEntry = useCallback(() => {
    activeTaskRef.current = null
    setEditTaskId(null)
    setEditing(null)
    setMesuresEntry(false)
    setModelTaskRows(prev => prev.map(task => (
      task.task_type_code === 'pom' ? { ...task, status: 'Done' } : task
    )))
    reloadTaula()
    reloadModel()
    reloadTasks()
    setWpVersion(v => v + 1)
  }, [reloadModel, reloadTaula, reloadTasks])
  // Sortir de mode edició/entrada en canviar de tab (pausa la tasca si n'hi havia).
  useEffect(() => {
    if ((editing && editing !== activeTab) || (mesuresEntry && activeTab !== 'Mesures')) exitEdit()
  }, [activeTab, editing, mesuresEntry, exitEdit])
  // Pausa la tasca NOMÉS en desmuntar el ModelSheet si quedava En curs (idempotent: si exitEdit ja
  // l'ha pausada, activeTaskRef és null i no es demana res → cap 400 Paused→Paused).
  useEffect(() => () => { pauseActiveTask() }, [pauseActiveTask])
  // Entrada directa en mode edició (rutes de tasca /mesures·/escalat → ModelSheet defaultTab+autoEdit):
  // obre la tasca i commuta a edició un sol cop en muntar (preserva el compta-temps de les portes Kanban/
  // WorkPlan sense pàgina externa).
  const autoEditRef = useRef(false)
  useEffect(() => {
    if (autoEdit && !autoEditRef.current) {
      autoEditRef.current = true
      enterEdit(autoEdit, autoEdit === 'Escalat' ? 'grading' : 'pom')
    }
  }, [autoEdit])   // eslint-disable-line react-hooks/exhaustive-deps

  // J1b — CONSUM de la tasca entrant: si el full s'obre amb ?tab=Mesures&task_id= (size_check "Mesurar
  // prenda" via WorkPlan / redirect /size-check), el tab entra en mode TREBALL lligat a ESA tasca
  // (compta-temps + origen de watchpoints), SENSE encunyar-ne una de nova (a diferència del botó "Editar
  // mides", que crida openTask). La tasca ja ve En curs des del Kanban/WorkPlan; aquí es consumeix i, BLOC 1,
  // es REGISTRA a activeTaskRef (PUNT COMÚ) perquè pauseActiveTask la pausi en sortir/desmuntar. Un sol cop.
  const autoTaskRef = useRef(false)
  useEffect(() => {
    if (autoTaskRef.current || loading) return
    if (activeTab === 'Mesures' && taskParam) {
      autoTaskRef.current = true
      const tid = parseInt(taskParam)
      setEditTaskId(tid)
      activeTaskRef.current = tid   // BLOC 1: tasca viva → pausada en sortir (abans no es feia: GAP P3 size_check)
      setEditing('Mesures')
    }
  }, [loading, activeTab, taskParam])

  // BLOC 1 — pom via URL ?mode=entry (WorkPlan/menú "Definició POM"): la tasca ve En curs però SENSE task_id
  // a la URL, així que el ModelSheet no la coneixia → quedava InProgress orfe (GAP P3 pom). La registrem pel
  // MATEIX punt comú que el botó intern: enterEdit('Mesures','pom') (openTask idempotent → activeTaskRef),
  // de manera que es pausi en sortir/desmuntar. NOMÉS amb ?mode=entry (NO toca la genesi del model verge).
  const entryEditRef = useRef(false)
  useEffect(() => {
    if (entryEditRef.current || loading) return
    if (entryMode && !taskParam && activeTab === 'Mesures') {
      entryEditRef.current = true
      enterEdit('Mesures', 'pom')
    }
  }, [loading, entryMode, taskParam, activeTab])   // eslint-disable-line react-hooks/exhaustive-deps

  // "Propagar a grading" des de MESURES (origen): inicia una FASE NOVA sobre llenç net
  // (generate_grading_view new_version → esborra propagació anterior + regenera) i porta a la tab Escalat.
  // MIRA ABANS (grading-status) i adverteix en 2 passos si ja hi ha propagació: pas 1 segons gravetat
  // (segellada/producció → es perden dades; o substitució simple), pas 2 universal de confirmació. Sobre
  // segellada s'envia allow_reopen_sealed (deixa un watchpoint de traça).
  const [propagating, setPropagating] = useState(false)
  const [propStatus, setPropStatus] = useState(null)   // {te_dades_propagades, segellada, version_number}
  const [propStep, setPropStep] = useState(0)           // 0 cap modal · 1 avís adaptat · 2 confirmació final
  // MIRA ABANS d'executar: si no hi ha propagació prèvia → propaga directe; si n'hi ha → avís de 2 passos
  // (pas 1 segons gravetat: segellada/producció vs substitució; pas 2 universal "n'estàs segur?").
  const onPropagarClick = () => {
    if (propagating) return
    models.gradingStatus(parseInt(id))
      .then(res => {
        const st = res.data
        if (!st.te_dades_propagades) execPropagar(false)   // llenç ja net → directe
        else { setPropStatus(st); setPropStep(1) }
      })
      .catch(() => setFeedback({ type: 'err', text: t('grading_propagate.err') }))
  }
  const execPropagar = (allowReopen) => {
    if (propagating) return
    setPropagating(true)
    const body = { new_version: true }
    if (allowReopen) body.allow_reopen_sealed = true
    models.generarGrading(parseInt(id), body)
      .then(() => { setPropStatus(null); setPropStep(0); setActiveTab('Escalat') })   // porta a Escalat (inline)
      .catch(() => setFeedback({ type: 'err', text: t('grading_propagate.err') }))
      .finally(() => setPropagating(false))
  }

  const handleDelete = async () => {
    if (!window.confirm(t('model_sheet.confirm_delete', { codi: model?.codi_intern }))) return
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/`, {
        method: 'DELETE', headers: authHeaders,
      })
      if (r.ok || r.status === 204) navigate('/models')
      else setError(t('model_sheet.err_delete'))
    } catch {
      setError(t('model_sheet.err_connection'))
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center',
                    color: 'var(--text-muted)',
                    fontSize: 'var(--fs-body)' }}>
        {t('model_sheet.loading')}
      </div>
    )
  }

  return (
    <div style={{ width: '100%' }}>
      <ModelSheetHeader model={model} onDelete={handleDelete} onFeedback={setFeedback} onChanged={reloadModel} />

      <div style={{ padding: '0 1.5rem' }}>
        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />
      </div>

      <div style={{
        display: 'flex', gap: 8, padding: '0.75rem 1.5rem',
        borderBottom: '0.5px solid var(--border)',
        background: 'var(--bg-main)',
      }}>
        {TABS.map(tab => (
          <button key={tab} type="button"
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '6px 16px', borderRadius: 6, border: 'none',
              background: activeTab === tab ? 'var(--gold)' : 'var(--bg-muted)',
              color: activeTab === tab ? 'var(--white)' : 'var(--text-muted)',
              cursor: 'pointer', fontSize: 'var(--fs-body)',
              fontWeight: activeTab === tab ? 500 : 400,
            }}>
            {t(TAB_LABELS[tab])}
          </button>
        ))}
        {/* B — Watchpoints: pastilla destacada ancorada a la dreta de la banda de pestanyes.
            Obre el drawer flotant (escriptura); visible des de qualsevol tab. */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center' }}>
          <WatchpointTrigger modelId={model.id} onClosed={() => setWpVersion(v => v + 1)} />
        </div>
      </div>

      {error && (
        <div style={{
          margin: '1rem 1.5rem', padding: '0.75rem 1rem',
          background: '#fee', border: '1px solid #fcc', borderRadius: 8,
          fontSize: 'var(--fs-body)', color: '#c00',
        }}>{error}</div>
      )}

      <div style={{ padding: '1.5rem' }}>
        {activeTab === 'Dashboard' && (
          <DashboardTab
            modelId={parseInt(id)}
            onOpenTab={setActiveTab}
            navigate={navigate}
            wpVersion={wpVersion}
          />
        )}
        {activeTab === 'Tasques' && (
          <TasksTab
            modelId={parseInt(id)}
            onOpenTab={setActiveTab}
            modelTaskRows={modelTaskRows}
            onTasksChanged={reloadTasks}
          />
        )}
        {activeTab === 'Resum' && (
          <div>
            {/* P4: edició del MODEL aquí (a Resum), no a la capçalera global. */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
              <button type="button" onClick={() => navigate(`/models/${id}/editar`)}
                style={{ ...btnSecondary, borderColor: 'var(--gold)', color: 'var(--gold)' }}>
                <i className="ti ti-edit" style={{ fontSize: 14 }} aria-hidden="true" /> {t('app.edit')}
              </button>
            </div>
            <TabSummary
              model={model}
              modelId={parseInt(id)}
              sizesAmbDades={sizesAmbDades}
              onUpdated={reloadModel}
            />
            {/* P3 — ruleset CANVIABLE al model (SPEC §1.6): triar/canviar el joc de regles de grading. */}
            {model && <RuleSetCard model={model} onChanged={reloadModel} />}
          </div>
        )}
        {activeTab === 'Mesures' && (
          mesuresEntry && editing !== 'Mesures' ? (
            <MeasuresEntryPanel model={model} entryMode={mesuresEntry}
              onMaterialized={() => { exitEdit(); reloadTaula(); reloadModel() }}
              onPomSaved={finishPomEntry} />
          ) : (!taskParam && editing !== 'Mesures' && !pomReady) ? (
            <div style={{
              border: '0.5px dashed var(--border)', borderRadius: 8, padding: '1.25rem',
              background: 'var(--bg-muted)', color: 'var(--text-muted)', fontSize: 'var(--fs-body)',
              display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'center', flexWrap: 'wrap',
            }}>
              <div>
                <div style={{ fontSize: 'var(--fs-h3)', color: 'var(--text-main)', marginBottom: 4 }}>
                  {t('model_sheet.measures_empty_title')}
                </div>
                <div>{t('model_sheet.measures_empty_body')}</div>
              </div>
              <button type="button" disabled={openingTask}
                onClick={() => enterEdit('Mesures', 'pom')}
                style={{ ...btnSecondary, borderColor: 'var(--gold)', color: 'var(--gold)',
                         opacity: openingTask ? 0.6 : 1, cursor: openingTask ? 'default' : 'pointer' }}>
                <i className="ti ti-ruler-2" style={{ fontSize: 14 }} />
                {t('model_sheet.start_pom')}
              </button>
            </div>
          ) : (
	          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                          marginBottom: 10, gap: 12 }}>
              <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                {editing === 'Mesures' ? t('model_sheet.measures_editing') : t('model_sheet.measures_consult')}
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {/* Commuta consulta↔edició DINS la tab (no navega): manté tot el context. */}
                {editing === 'Mesures' ? (
                  <button type="button" onClick={exitEdit}
                    style={{ ...btnSecondary, borderColor: 'var(--gold)', color: 'var(--gold)' }}>
                    <i className="ti ti-eye" style={{ fontSize: 14 }} />
                    {t('model_sheet.back_to_consult')}
                  </button>
                ) : (
                  <button type="button" disabled={openingTask}
                    onClick={() => enterEdit('Mesures', 'pom')}
                    style={{ ...btnSecondary, borderColor: 'var(--gold)', color: 'var(--gold)',
                             opacity: openingTask ? 0.6 : 1, cursor: openingTask ? 'default' : 'pointer' }}>
                    <i className="ti ti-ruler-2" style={{ fontSize: 14 }} />
                    {t('model_sheet.edit_pom')}
                  </button>
                )}
                {/* Propagar a grading (origen): inicia fase nova sobre llenç net i porta a Escalat.
                    Mira abans i adverteix (2 passos) si ja hi ha propagació. */}
                <button type="button" disabled={openingTask || propagating}
                  onClick={onPropagarClick}
                  style={{ ...btnSecondary, borderColor: 'var(--gold)', color: 'var(--gold)',
                           opacity: (openingTask || propagating) ? 0.6 : 1,
                           cursor: (openingTask || propagating) ? 'default' : 'pointer' }}>
                  <i className="ti ti-git-branch" style={{ fontSize: 14 }} />
                  {propagating ? t('grading_propagate.running') : t('grading_propagate.button')}
                </button>
              </div>
            </div>
            {editing === 'Mesures' ? (
              <CheckMeasureEditor model={model} readOnly={false} taskId={editTaskId}
                onFeedback={fb => setFeedback(fb)} onResolved={exitEdit} onBack={exitEdit} />
            ) : (
              <CheckMeasureEditor model={model} readOnly />
            )}
          </div>
          )
        )}
        {/* Escalat: consulta ↔ edició DINS la tab (inline, sense overlay; manté el context). */}
        {activeTab === 'Escalat' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
              {editing === 'Escalat' ? (
                <button type="button" onClick={exitEdit}
                  style={{ ...btnSecondary, borderColor: 'var(--gold)', color: 'var(--gold)' }}>
                  <i className="ti ti-eye" style={{ fontSize: 14 }} />
                  {t('model_sheet.back_to_consult')}
                </button>
              ) : (
                <button type="button" disabled={openingTask}
                  onClick={() => enterEdit('Escalat', 'grading')}
                  style={{ ...btnSecondary, borderColor: 'var(--gold)', color: 'var(--gold)',
                           opacity: openingTask ? 0.6 : 1, cursor: openingTask ? 'default' : 'pointer' }}>
                  <i className="ti ti-resize" style={{ fontSize: 14 }} />
                  {t('model_sheet.edit_grading')}
                </button>
              )}
            </div>
            <PropagatedEditor modelId={parseInt(id)} inline readOnly={editing !== 'Escalat'} />
          </div>
        )}
        {/* FaseB — avís de 2 passos en propagar amb dades existents (mira abans). Pas 1 segons gravetat. */}
        {propStatus && propStep === 1 && (
          <Modal
            title={t('grading_propagate.warn_title')}
            subtitle={propStatus.segellada
              ? t('grading_propagate.warn_sealed', { version: propStatus.version_number })
              : t('grading_propagate.warn_substitute')}
            confirmLabel={t('grading_propagate.continue')}
            cancelLabel={t('app.cancel')}
            onCancel={() => { setPropStatus(null); setPropStep(0) }}
            onConfirm={() => setPropStep(2)}
          />
        )}
        {propStatus && propStep === 2 && (
          <Modal
            title={t('grading_propagate.confirm_title')}
            subtitle={t('grading_propagate.confirm_sure')}
            confirmLabel={t('grading_propagate.confirm_supersede')}
            cancelLabel={t('app.cancel')}
            onCancel={() => { setPropStatus(null); setPropStep(0) }}
            onConfirm={() => execPropagar(propStatus.segellada)}
          />
        )}
        {activeTab === 'Fitxers' && <TabFiles modelId={parseInt(id)} />}
        {activeTab === 'Fitxa tècnica' && <TechSheetTab modelId={id} navigate={navigate} />}
        {activeTab === 'Anàlisi IA' && <TabAIAnalysis modelId={parseInt(id)} />}
        {activeTab === "Registre d'activitat" && <RegistreActivitatTab modelId={id} />}
      </div>
    </div>
  )
}

// Pestanya "Fitxa tècnica": resum read-only + accessos a l'editor (/fitxa).
// Consulta des del Model obre sense task_id → mode consulta. L'edició registrada
// es fa des del Kanban (que passa ?task_id=...). Vegeu TechSheetEditor.
function TechSheetTab({ modelId, navigate }) {
  // Cutover .ftt (F8): la fitxa és un ModelFitxer tipus TECHSHEET (no el TechSheet O2O). El
  // resum llegeix el cap de cadena vigent; els botons van a /fitxa (resolver que obre/crea el .ftt).
  const [fitxer, setFitxer] = useState(null)
  const [loading, setLoading] = useState(true)
  const token   = localStorage.getItem('access_token')
  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    fetch(`${API}/api/v1/model-fitxers/?model=${modelId}&tipus=TECHSHEET&is_current=true&ordering=-data_pujada`, { headers })
      .then(r => r.ok ? r.json() : null)
      .then(data => { const list = data?.results || data || []; setFitxer(list[0] || null); setLoading(false) })
      .catch(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId])

  if (loading) return (
    <div style={{ padding: '24px', color: 'var(--text-muted)',
      fontSize: 'var(--fs-body)' }}>
      Carregant…
    </div>
  )

  // Estil compartit per botons outline discrets
  const btnOutline = {
    background: 'transparent',
    border: '1px solid var(--border)',
    color: 'var(--text-main)',
    fontSize: 'var(--fs-body)',
    padding: '5px 12px',
    cursor: 'pointer',
  }

  // --- NO HI HA FITXA ---
  if (!fitxer) {
    return (
      <div style={{ padding: '24px',
        }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)',
          marginBottom: '16px' }}>
          Encara no hi ha fitxa tècnica per a aquest model.
        </p>
        <button
          onClick={() => navigate(`/models/${modelId}/fitxa`)}
          style={{ ...btnOutline, borderColor: 'var(--gold)',
            color: 'var(--gold)' }}>
          Crear fitxa tècnica
        </button>
      </div>
    )
  }

  // --- HI HA FITXA ---
  const updatedAt = fitxer.data_pujada
    ? new Date(fitxer.data_pujada).toLocaleDateString('ca-ES',
        { day:'2-digit', month:'2-digit', year:'numeric' })
    : '—'

  return (
    <div style={{ }}>

      {/* Barra superior: info + botons */}
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-muted)',
      }}>
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
          display: 'flex', gap: '16px' }}>
          <span>v{fitxer.versio}</span>
          <span>{fitxer.nom_fitxer}</span>
          <span>Actualitzat: {updatedAt}</span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => navigate(`/models/${modelId}/fitxa`)}
            style={btnOutline}>
            Previsualitzar
          </button>
          <button
            onClick={() => navigate(`/models/${modelId}/fitxa`)}
            style={btnOutline}>
            Modificar
          </button>
        </div>
      </div>

      {/* Cos: resum de l'estat */}
      <div style={{ padding: '16px', fontSize: 'var(--fs-body)',
        color: 'var(--text-muted)' }}>
        <p>
          La fitxa es pot editar des del Kanban (tasca
          <strong style={{ color: 'var(--text-main)' }}>
            {' '}Fitxa tècnica
          </strong>
          ) o des del botó Modificar.
          El PDF definitiu es generarà en congelar la fitxa.
        </p>
      </div>

    </div>
  )
}

function ModelSheetHeader({ model, onDelete, onFeedback, onChanged }) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  if (!model) return null

  return (
    <div style={{ borderBottom: '0.5px solid var(--border)' }}>
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0.75rem 1.5rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button type="button" onClick={() => navigate('/models')}
          style={{ background: 'none', border: 'none', cursor: 'pointer',
                   fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                   }}>
          ← {t('nav.models')}
        </button>
        <span style={{ color: 'var(--border)' }}>›</span>
        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                       }}>
          {model.codi_intern}
        </span>
        {model.codi_client && model.codi_client !== model.codi_intern && (
          <>
            <span style={{ color: 'var(--border)' }}>·</span>
            <span style={{ fontSize: 'var(--fs-body)', 
                           color: 'var(--text-main)', fontWeight: 500 }}>
              {model.codi_client}
            </span>
          </>
        )}
        {model.nom_prenda && (
          <>
            <span style={{ color: 'var(--border)' }}>·</span>
            <span style={{ fontSize: 'var(--fs-h3)', fontWeight: 500,
                           color: 'var(--text-main)' }}>
              {model.nom_prenda}
            </span>
          </>
        )}
        <span style={{
          fontSize: 'var(--fs-body)', padding: '2px 8px', borderRadius: 20, fontWeight: 600,
          background: 'var(--gold)', color: 'var(--white)',
        }} title={t('model_sheet.phase')}>
          {model.fase_actual ? t(`model_sheet.dashboard.phase.${model.fase_actual}`, model.fase_actual) : '—'}
        </span>
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        {/* P4: "Editar" (edita el MODEL) s'ha mogut a la pestanya Resum perquè no confongui que edita
            la pantalla visible. Aquí queden les accions de fase i l'esborrat. */}
        <ActionsMenu model={model} onChanged={onChanged} onFeedback={onFeedback} />
        <button type="button" onClick={onDelete}
          style={{ ...btnSecondary, color: '#c5221f', borderColor: '#f5c6c6' }}>
          <i className="ti ti-trash" aria-hidden="true" /> {t('app.delete')}
        </button>
      </div>
    </div>
    </div>
  )
}

// Disparador del Watchpoint flotant: icona (outline) + badge amb el TOTAL d'entrades del model
// (mateixa font que el panell: watchpoints.list). Un sol pols breu quan el comptador PUJA respecte
// l'anterior (entrada nova) — mai en la càrrega inicial, mai en bucle. En tancar el drawer, refresca
// el comptador. Estat local i aïllat: obrir-lo no toca l'estat del model ni re-munta cap pestanya.
function WatchpointTrigger({ modelId, onClosed }) {
  const { t } = useTranslation()
  const [count, setCount] = useState(0)
  const [open, setOpen] = useState(false)
  const badgeRef = useRef(null)
  const prevCount = useRef(0)
  const initialized = useRef(false)

  const fetchCount = useCallback(() => {
    if (!modelId) return
    watchpoints.list({ model: modelId })
      .then(r => {
        const total = typeof r.data?.count === 'number'
          ? r.data.count
          : (r.data?.results ?? r.data ?? []).length
        if (initialized.current && total > prevCount.current && badgeRef.current) {
          // Pols one-shot via Web Animations API (cap CSS global, cap bucle).
          badgeRef.current.animate(
            [{ transform: 'scale(1)' }, { transform: 'scale(1.4)' }, { transform: 'scale(1)' }],
            { duration: 500, easing: 'ease-out' },
          )
        }
        prevCount.current = total
        initialized.current = true
        setCount(total)
      })
      .catch(() => {})
  }, [modelId])

  useEffect(() => { fetchCount() }, [fetchCount])

  const handleClose = () => { setOpen(false); fetchCount(); onClosed?.() }

  return (
    <div style={{ position: 'relative' }}>
      {/* Pastilla destacada amb CONTORN DAURAT: icona outline + etiqueta + badge comptador. */}
      <button type="button" onClick={() => setOpen(true)}
        title={t('watchpoints.tab_label')} aria-label={t('watchpoints.tab_label')}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '6px 14px', borderRadius: 20,
          border: '1px solid var(--gold)', background: 'transparent', color: 'var(--gold)',
          cursor: 'pointer', fontSize: 'var(--fs-body)', fontWeight: 500,
        }}>
        <i className="ti ti-message-2" aria-hidden="true" style={{ fontSize: 16 }} />
        {t('watchpoints.tab_label')}
        {count > 0 && (
          <span ref={badgeRef} style={{
            minWidth: 18, height: 18, padding: '0 5px', borderRadius: 9,
            background: 'var(--gold)', color: 'var(--white)',
            fontSize: 'var(--fs-label)', fontWeight: 600, lineHeight: '18px', textAlign: 'center',
          }}>{count}</span>
        )}
      </button>
      <WatchpointDrawer modelId={modelId} open={open} onClose={handleClose} />
    </div>
  )
}

function TabSummary({ model, modelId, sizesAmbDades, onUpdated }) {
  const { t, i18n } = useTranslation()
  const dateLocale = i18n.language === 'es' ? 'es-ES' : i18n.language === 'en' ? 'en-GB' : 'ca-ES'
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    nom_prenda: model?.nom_prenda || '',
    codi_client: (model?.codi_client !== model?.codi_intern ? model?.codi_client : '') || '',
    descripcio: model?.descripcio || '',
  })
  const [saving, setSaving] = useState(false)
  const token = localStorage.getItem('access_token')

  // ── Viabilitat: estat del panell + total de minuts de les tasques ─────────
  const [numTecnics, setNumTecnics] = useState(1)
  const [modeCalc, setModeCalc] = useState('fi')   // 'fi'=inici→fi · 'inici'=fi→inici
  const [inputData, setInputData] = useState(
    model?.predicted_start?.slice(0, 10) || new Date().toISOString().slice(0, 10)
  )
  const [totalMinuts, setTotalMinuts] = useState(null)
  const [loadingMinuts, setLoadingMinuts] = useState(true)

  // ── Deadline (data_objectiu): edició inline pròpia ────────────────────────
  const [editingDeadline, setEditingDeadline] = useState(false)
  const [deadlineVal, setDeadlineVal] = useState(model?.data_objectiu || '')
  const [savingDeadline, setSavingDeadline] = useState(false)

  useEffect(() => {
    if (!modelId) return
    const tk = localStorage.getItem('access_token')
    fetch(`${API}/api/v1/model-task-items/?model=${modelId}`,
      { headers: { Authorization: `Bearer ${tk}` } })
      .then(r => (r.ok ? r.json() : { results: [] }))
      .then(data => {
        const items = data.results || data
        const total = items.reduce((s, item) => s + (item.estimated_minutes || 0), 0)
        setTotalMinuts(total)
        setLoadingMinuts(false)
      })
      .catch(() => setLoadingMinuts(false))
  }, [modelId])

  const handleSave = async () => {
    setSaving(true)
    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          nom_prenda: form.nom_prenda,
          codi_client: form.codi_client || model.codi_intern,
          descripcio: form.descripcio,
        }),
      })
      if (r.ok) { setEditing(false); if (onUpdated) onUpdated() }
    } finally { setSaving(false) }
  }

  if (!model) return null

  const saveDeadline = async () => {
    setSavingDeadline(true)
    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ data_objectiu: deadlineVal || null }),
      })
      if (r.ok) { setEditingDeadline(false); if (onUpdated) onUpdated() }
    } finally { setSavingDeadline(false) }
  }

  // Cel·la del deadline: edició inline (date input + ✓/✕) o display (gold / sense).
  const deadlineCell = editingDeadline ? (
    <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
      <input type="date" value={deadlineVal} onChange={e => setDeadlineVal(e.target.value)}
        style={{ padding: '3px 6px', fontSize: 'var(--fs-body)', 
                 border: '1px solid var(--border)', borderRadius: 4 }} />
      <button type="button" onClick={saveDeadline} disabled={savingDeadline}
        style={{ padding: '3px 10px', background: 'var(--gold)', color: 'var(--white)', border: 'none',
                 borderRadius: 4, fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
        {savingDeadline ? '…' : '✓'}
      </button>
      <button type="button" onClick={() => { setDeadlineVal(model.data_objectiu || ''); setEditingDeadline(false) }}
        style={{ padding: '3px 8px', background: 'transparent', border: '0.5px solid var(--border)',
                 borderRadius: 4, fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
        ✕
      </button>
    </span>
  ) : (
    <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
      {model.data_objectiu
        ? <strong style={{ color: 'var(--gold)' }}>{model.data_objectiu}</strong>
        : <span style={{ color: 'var(--text-muted)' }}>{t('model_sheet.no_deadline')}</span>}
      <button type="button" onClick={() => setEditingDeadline(true)} title={t('model_sheet.edit_deadline')}
        style={{ background: 'transparent', border: 'none', cursor: 'pointer',
                 color: 'var(--text-muted)', fontSize: 'var(--fs-body)', padding: 0 }}>
        <i className="ti ti-pencil" />
      </button>
    </span>
  )

  const fmtDateTime = (v) => v ? new Date(v).toLocaleString(dateLocale, { dateStyle: 'medium', timeStyle: 'short' }) : '—'
  const readOnlyFields = [
    { label: t('model_sheet.field_internal_ref'), value: model.codi_intern, mono: true, secondary: true },
    { label: t('model.fields.temporada'), value: `${model.temporada} ${model.any}` },
    { label: t('model_sheet.field_collection'), value: model.collection || '—' },
    { label: t('model_sheet.field_target'), value: model.target ? t(`model_wizard.target_${model.target}`, model.target) : '—' },
    { label: t('model_sheet.field_garment_type'), value: model.garment_type_nom || '—' },
    { label: t('model_sheet.field_garment_item'), value: model.garment_type_item_nom || '—' },
    { label: t('model_sheet.field_construction'), value: model.construction ? t(`model_wizard.construction_${model.construction}`, model.construction) : '—' },
    { label: t('model.fields.fit_type'), value: model.fit_type ? t(`model_wizard.fit_${model.fit_type}`, model.fit_type) : '—' },
    { label: t('model_sheet.field_size_system'), value: model.size_system_nom || '—' },
    { label: t('model.fields.base_size_label'), value: model.base_size_label || '—' },
    { label: t('model_sheet.field_size_run'), value: (sizesAmbDades && sizesAmbDades.length
      ? sizesAmbDades.join('·')
      : model.size_run_model) || '—', mono: true },
    { label: t('model.sections.grading'), value: model.grading_rule_set ? t('model_sheet.grading_configured') : '—' },
    { label: t('model_sheet.phase'), value: model.fase_actual ? t(`model_sheet.dashboard.phase.${model.fase_actual}`, model.fase_actual) : '—' },
    { label: t('model_sheet.field_created_by'), value: model.created_by_nom || '—' },
    { label: t('model_sheet.field_created_at'), value: fmtDateTime(model.created_at) },
    ...(model.fabric_main ? [
      { label: t('model_sheet.field_main_fabric'), value: model.fabric_main },
      { label: t('model_sheet.field_composition'), value: model.fabric_composition || '—' },
      { label: t('model_sheet.field_shrinkage'), value: model.shrinkage_warp != null
        ? t('model_sheet.shrinkage_value', { warp: model.shrinkage_warp, weft: model.shrinkage_weft, type: model.shrinkage_type })
        : model.shrinkage_pct != null
          ? t('model_sheet.shrinkage_value_simple', { pct: model.shrinkage_pct, type: model.shrinkage_type })
          : '—' },
    ] : []),
    { label: t('model_sheet.field_deadline'), value: deadlineCell },
  ]

  // ── Viabilitat: càlculs derivats (render) ─────────────────────────────────
  const diesBase = totalMinuts ? totalMinuts / 420 : null
  const diesAjustats = diesBase ? diesBase / numTecnics : null
  const dataFiCalc = modeCalc === 'fi' && diesAjustats
    ? afegirDiesLaborables(inputData, Math.ceil(diesAjustats))
    : null
  const dataIniciCalc = modeCalc === 'inici' && diesAjustats
    ? restarDiesLaborables(model.data_objectiu, Math.ceil(diesAjustats))
    : null
  const viab = totalMinuts
    ? calcViabilitat(totalMinuts, model.data_objectiu, model.predicted_end?.slice(0, 10))
    : null
  const avuiISO = new Date().toISOString().slice(0, 10)

  return (
    <div style={{ maxWidth: 640 }}>
      {editing ? (
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                            display: 'block', marginBottom: 4 }}>
              {t('model_sheet.field_garment_name')}
            </label>
            <input value={form.nom_prenda}
              onChange={e => setForm(f => ({...f, nom_prenda: e.target.value}))}
              style={{ width: '100%', padding: '6px 10px', fontSize: 'var(--fs-body)',
                       border: '1px solid var(--border)', borderRadius: 6 }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                            display: 'block', marginBottom: 4 }}>
              {t('model.fields.codi_client')}
            </label>
            <input value={form.codi_client}
              onChange={e => setForm(f => ({...f, codi_client: e.target.value}))}
              style={{ width: '100%', padding: '6px 10px', fontSize: 'var(--fs-body)',
                       border: '1px solid var(--border)', borderRadius: 6 }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                            display: 'block', marginBottom: 4 }}>
              {t('model.fields.descripcio')}
            </label>
            <textarea value={form.descripcio}
              onChange={e => setForm(f => ({...f, descripcio: e.target.value}))}
              rows={3}
              style={{ width: '100%', padding: '6px 10px', fontSize: 'var(--fs-body)',
                       border: '1px solid var(--border)', borderRadius: 6,
                       resize: 'vertical' }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={handleSave} disabled={saving}
              style={{ padding: '6px 16px', background: 'var(--gold)', color: 'var(--white)',
                       border: 'none', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer' }}>
              {saving ? t('model_sheet.saving') : t('model_sheet.save')}
            </button>
            <button type="button" onClick={() => setEditing(false)}
              style={{ padding: '6px 14px', background: 'transparent', fontSize: 'var(--fs-body)',
                       border: '0.5px solid var(--border)',
                       borderRadius: 6, cursor: 'pointer' }}>
              {t('common.cancel')}
            </button>
          </div>
        </div>
      ) : (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 'var(--fs-h2)', fontWeight: 500 }}>
                {model.nom_prenda || <span style={{color:'var(--text-muted)'}}>{t('model_sheet.no_name')}</span>}
              </div>
              {model.codi_client && model.codi_client !== model.codi_intern && (
                <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                              marginTop: 2 }}>
                  {model.codi_client}
                </div>
              )}
              {model.descripcio && (
                <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                              marginTop: 6 }}>
                  {model.descripcio}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
        <tbody>
          {readOnlyFields.map(({ label, value, mono, secondary }) => (
            <tr key={label}
              style={{ borderBottom: '0.5px solid var(--border)' }}>
              <td style={{ padding: '7px 0', color: 'var(--text-muted)',
                           width: 180, fontSize: 'var(--fs-body)' }}>
                {label}
              </td>
              <td style={{ padding: '7px 0',
                           fontFamily: mono ? 'monospace' : undefined,
                           color: secondary
                             ? 'var(--text-muted)' : 'var(--text-main)' }}>
                {value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {model.data_objectiu && (
        <div style={{
          marginTop: '24px',
          border: '1px solid var(--border)',
          borderRadius: '4px',
          overflow: 'hidden',
        }}>
          {/* Capçalera del panel */}
          <div style={{
            background: 'var(--bg-sidebar)',
            borderBottom: '1px solid var(--base-hairline)',
            padding: '8px 12px',
            display: 'flex', alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <span style={{ fontSize: 'var(--fs-body)', fontWeight: 600,
              color: 'var(--gold)', textTransform: 'uppercase',
              letterSpacing: '0.05em' }}>
              {t('model_sheet.viability_title')}
            </span>
            {viab && (
              <span style={{
                fontSize: 'var(--fs-label)', padding: '2px 8px',
                background: viab.semafor === 'on_track' ? '#dcfce7'
                           : viab.semafor === 'at_risk'  ? '#fef9c3'
                           : '#fee2e2',
                color: viab.semafor === 'on_track' ? '#166534'
                     : viab.semafor === 'at_risk'  ? '#854d0e'
                     : '#991b1b',
                border: `1px solid ${
                  viab.semafor === 'on_track' ? '#86efac'
                : viab.semafor === 'at_risk'  ? '#fde047'
                : '#fca5a5'}`,
              }}>
                {viab.semafor === 'on_track' ? t('model_sheet.viab_on_track')
               : viab.semafor === 'at_risk'  ? t('model_sheet.viab_at_risk')
               : t('model_sheet.viab_critical')}
              </span>
            )}
          </div>

          {/* Cos del panel */}
          <div style={{ padding: '12px', background: 'var(--bg-muted)' }}>
            {loadingMinuts ? (
              <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                {t('model_sheet.calculating')}
              </p>
            ) : !totalMinuts ? (
              <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                {t('model_sheet.viab_no_tasks')}
              </p>
            ) : (
              <>
                {/* Fila d'info base */}
                <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                  marginBottom: '12px', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                  <span>
                    {t('model_sheet.hours_estimated', { h: Math.round(totalMinuts / 60 * 10) / 10 })}
                  </span>
                  {viab?.latestStart && (
                    <span>
                      {t('model_sheet.latest_start')}
                      <strong style={{ color: viab.semafor === 'critical'
                        ? 'var(--err)' : 'var(--text-main)',
                        marginLeft: '4px' }}>
                        {viab.latestStart}
                      </strong>
                    </span>
                  )}
                  {model.data_objectiu && (
                    <span>{t('model_sheet.deadline_inline')} {model.data_objectiu}</span>
                  )}
                </div>

                {/* Calculadora interactiva */}
                <div style={{ display: 'flex', gap: '8px',
                  alignItems: 'center', flexWrap: 'wrap',
                  fontSize: 'var(--fs-body)' }}>

                  {/* Toggle mode */}
                  <select
                    value={modeCalc}
                    onChange={e => setModeCalc(e.target.value)}
                    style={{ 
                      fontSize: 'var(--fs-body)', padding: '4px 6px',
                      border: '1px solid var(--border)',
                      background: 'var(--bg-card)' }}>
                    <option value="fi">{t('model_sheet.calc_mode_start_to_end')}</option>
                    <option value="inici">
                      {t('model_sheet.calc_mode_end_to_start')}
                    </option>
                  </select>

                  {/* Input data (només en mode 'fi') */}
                  {modeCalc === 'fi' && (
                    <input type="date" value={inputData}
                      onChange={e => setInputData(e.target.value)}
                      style={{ 
                        fontSize: 'var(--fs-body)', padding: '4px 6px',
                        border: '1px solid var(--border)',
                        background: 'var(--bg-card)' }}
                    />
                  )}

                  {/* Nº tècnics */}
                  <div style={{ display: 'flex', gap: '4px' }}>
                    {[1, 2, 3, 4].map(n => (
                      <button key={n} onClick={() => setNumTecnics(n)}
                        style={{
                          fontSize: 'var(--fs-body)', padding: '4px 10px',
                          cursor: 'pointer',
                          background: numTecnics === n
                            ? 'var(--gold)' : 'transparent',
                          color: numTecnics === n
                            ? 'var(--white)' : 'var(--text-main)',
                          border: '1px solid var(--border)',
                        }}>
                        {n}T
                      </button>
                    ))}
                  </div>

                  {/* Resultat */}
                  {modeCalc === 'fi' && dataFiCalc && (
                    <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>
                      {t('model_sheet.estimated_end')}
                      <strong style={{
                        color: model.data_objectiu && dataFiCalc > model.data_objectiu
                          ? 'var(--err)' : 'var(--ok)',
                        marginLeft: '4px'
                      }}>
                        {dataFiCalc}
                      </strong>
                      {model.data_objectiu && dataFiCalc > model.data_objectiu &&
                        <span style={{ color: 'var(--err)', marginLeft: '6px', fontSize: 'var(--fs-label)' }}>
                          {t('model_sheet.out_of_deadline')}
                        </span>
                      }
                    </span>
                  )}
                  {modeCalc === 'inici' && dataIniciCalc && (
                    <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>
                      {t('model_sheet.needed_start')}
                      <strong style={{
                        color: dataIniciCalc < avuiISO ? 'var(--err)' : 'var(--ok)',
                        marginLeft: '4px'
                      }}>
                        {dataIniciCalc}
                      </strong>
                      {dataIniciCalc < avuiISO &&
                        <span style={{ color: 'var(--err)', marginLeft: '6px', fontSize: 'var(--fs-label)' }}>
                          {t('model_sheet.past_date')}
                        </span>
                      }
                    </span>
                  )}
                </div>

                <p style={{ marginTop: '8px', fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
                  {t('model_sheet.viab_disclaimer')}
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Finder: llista plana. La icona i l'ordre "Tipus" surten de l'extensió del fitxer,
// no del rol intern (tipus/categoria, que es conserven al backend però el Finder ignora).
const PREVIEW_IMG_RE = /\.(jpg|jpeg|png|svg|webp|gif)$/i
const FILES_MONO = 'IBM Plex Mono, monospace'

// D13: <img>/<iframe> no poden portar Authorization → URL signada de curta vida. `inline=1`
// perquè el PDF es renderitzi a l'iframe en lloc de descarregar-se (Content-Disposition).
// El regex de preview s'aplica al NOM del fitxer, mai a la URL: ara acaba en ?token=…
function previewUrl(f) {
  if (!f) return null
  return f.download_url ? `${f.download_url}&inline=1` : (f.url_extern || null)
}

function fileExt(nom) {
  const m = (nom || '').match(/\.([a-z0-9]+)$/i)
  return m ? m[1].toLowerCase() : ''
}

function iconForExt(ext) {
  if (['jpg', 'jpeg', 'png', 'svg', 'webp', 'gif'].includes(ext)) return 'ti-photo'
  if (ext === 'pdf') return 'ti-file-text'
  if (ext === 'dxf') return 'ti-vector-triangle'
  if (['xlsx', 'xls', 'csv'].includes(ext)) return 'ti-table'
  return 'ti-file'
}

function TabFiles({ modelId }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { Authorization: `Bearer ${token}` }

  const [fitxers, setFitxers] = useState([])
  const [orderBy, setOrderBy] = useState('data')
  const [uploading, setUploading] = useState(false)
  const [popup, setPopup] = useState(null)
  const [history, setHistory] = useState(null)   // { fitxer, chain[], loading }
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)   // Finder: CAP selecció per defecte

  useEffect(() => {
    fetch(`${API}/api/v1/model-fitxers/?model=${modelId}&is_current=true&ordering=-data_pujada`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => setFitxers(d.results || d || []))
      .catch(() => setError(t('model_sheet.err_load_files')))
  }, [modelId])

  // versioAnteriorId opcional: encadena una nova versió i, com que la llista mostra només
  // is_current, el nou cap substitueix el predecessor a la llista.
  const handleUpload = async (file, versioAnteriorId = null) => {
    setUploading(true)
    const formData = new FormData()
    formData.append('fitxer', file)
    formData.append('nom', file.name)
    if (versioAnteriorId) formData.append('versio_anterior_id', versioAnteriorId)
    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/upload-fitxer/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      const d = await r.json()
      if (r.ok) {
        setFitxers(prev => versioAnteriorId
          ? [d, ...prev.filter(f => f.id !== versioAnteriorId)]
          : [d, ...prev])
      } else {
        setError(JSON.stringify(d))
      }
    } catch {
      setError(t('model_sheet.err_upload'))
    } finally {
      setUploading(false)
    }
  }

  const openHistory = async (fitxer) => {
    setHistory({ fitxer, chain: [], loading: true })
    try {
      const r = await fetch(`${API}/api/v1/model-fitxers/${fitxer.id}/versions/`, { headers: authHeaders })
      const d = await r.json()
      setHistory({ fitxer, chain: (d.results || d || []), loading: false })
    } catch {
      setHistory({ fitxer, chain: [], loading: false })
    }
  }

  const handleDelete = async (fitxerId) => {
    if (!window.confirm(t('model_sheet.confirm_delete_file'))) return
    await fetch(`${API}/api/v1/model-fitxers/${fitxerId}/`, {
      method: 'DELETE', headers: authHeaders,
    })
    setFitxers(prev => prev.filter(f => f.id !== fitxerId))
  }

  const ORDERS = [
    { key: 'data', label: t('model_sheet.sort_date') },
    { key: 'tipus', label: t('model_sheet.sort_type') },
    { key: 'nom', label: t('model_sheet.sort_name') },
  ]

  const sorted = [...fitxers].sort((a, b) => {
    if (orderBy === 'nom') return (a.nom_fitxer || '').localeCompare(b.nom_fitxer || '')
    if (orderBy === 'tipus') return fileExt(a.nom_fitxer).localeCompare(fileExt(b.nom_fitxer))
    return (b.data_pujada || '').localeCompare(a.data_pujada || '')   // 'data' — recent primer
  })
  // Selecció vigent (null si cap, o si el seleccionat ja no hi és, p.ex. després d'eliminar).
  const selected = sorted.find(f => f.id === selectedId) || null

  return (
    <div style={{ width: '100%' }}>
      {error && (
        <div style={{
          background: '#fee', border: '1px solid #fcc', borderRadius: 6,
          padding: '8px 12px', marginBottom: 12, fontSize: 'var(--fs-body)', color: '#c00',
        }}>{error}</div>
      )}

      {popup && (
        <div onClick={() => setPopup(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
          <div onClick={e => e.stopPropagation()}
            style={{ background: 'var(--white)', borderRadius: 8, padding: 16,
                     maxWidth: '90vw', maxHeight: '90vh' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500 }}>{popup.nom}</span>
              <button type="button" onClick={() => setPopup(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 'var(--fs-h2)' }}>✕</button>
            </div>
            {PREVIEW_IMG_RE.test(popup.nom || '') ? (
              <img src={popup.url} alt={popup.nom}
                style={{ maxWidth: '80vw', maxHeight: '80vh', objectFit: 'contain' }} />
            ) : (
              <iframe src={popup.url} title={popup.nom}
                style={{ width: '80vw', height: '80vh', border: 'none' }} />
            )}
          </div>
        </div>
      )}

      {history && (
        <div onClick={() => setHistory(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
          <div onClick={e => e.stopPropagation()}
            style={{ background: 'var(--white)', borderRadius: 8, padding: 16,
                     minWidth: 360, maxWidth: '90vw', maxHeight: '80vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <span style={{ fontSize: 'var(--fs-h3)', fontWeight: 500 }}>{t('model_sheet.version_history')}</span>
              <button type="button" onClick={() => setHistory(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 'var(--fs-h2)' }}>✕</button>
            </div>
            {history.loading ? (
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>…</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {[...history.chain].sort((a, b) => (b.versio || 0) - (a.versio || 0)).map(v => (
                  <div key={v.id}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '6px 10px', borderRadius: 6,
                      border: '0.5px solid var(--border)',
                      background: v.is_current ? 'var(--bg-muted)' : 'transparent',
                    }}>
                    <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, minWidth: 32 }}>v{v.versio}</span>
                    <span style={{
                      flex: 1, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }} title={v.nom_fitxer}>{v.nom_fitxer}</span>
                    {v.is_current && (
                      <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
                        {t('model_sheet.current_version')}
                      </span>
                    )}
                    <button type="button"
                      onClick={() => setPopup({ url: previewUrl(v), nom: v.nom_fitxer })}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                      <i className="ti ti-eye" aria-hidden="true" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('model_sheet.sort_by')}</span>
        {ORDERS.map(o => (
          <button key={o.key} type="button" onClick={() => setOrderBy(o.key)}
            style={{
              padding: '3px 12px', fontSize: 'var(--fs-body)', borderRadius: 6, cursor: 'pointer',
              border: '0.5px solid var(--border)',
              background: orderBy === o.key ? 'var(--bg-muted)' : 'transparent',
              color: orderBy === o.key ? 'var(--text-main)' : 'var(--text-muted)',
              fontWeight: orderBy === o.key ? 500 : 400,
            }}>
            {o.label}
          </button>
        ))}
        <label style={{
          marginLeft: 'auto', padding: '4px 12px', fontSize: 'var(--fs-body)',
          border: '0.5px solid var(--border)', borderRadius: 6,
          cursor: 'pointer', color: 'var(--text-muted)',
          background: uploading ? 'var(--bg-muted)' : 'transparent',
        }}>
          {uploading ? t('model_sheet.uploading') : t('model_sheet.upload')}
          <input type="file" style={{ display: 'none' }}
            accept={UPLOAD_ACCEPT}
            disabled={uploading}
            onChange={e => e.target.files[0] && handleUpload(e.target.files[0])} />
        </label>
      </div>

      {sorted.length === 0 ? (
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                      padding: '8px 0', fontStyle: 'italic' }}>
          {t('model_sheet.no_files')}
        </div>
      ) : (
        // Patró Finder: llista (esq) + detall lateral (dre). Cap selecció per defecte.
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          {/* ESQUERRA — una FILA per fitxer, amb capçaleres de columna. */}
          <div style={{ flex: '1 1 0', minWidth: 0, border: '0.5px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px',
              borderBottom: '0.5px solid var(--border)', background: 'var(--bg-muted)',
              fontSize: 'var(--fs-label)', fontFamily: FILES_MONO, color: 'var(--text-muted)', textTransform: 'uppercase',
            }}>
              <span style={{ width: 18, flexShrink: 0 }} />
              <span style={{ flex: 1, minWidth: 0 }}>{t('model_sheet.files.col_name')}</span>
              <span style={{ width: 80, flexShrink: 0 }}>{t('model_sheet.files.col_type')}</span>
              <span style={{ width: 96, flexShrink: 0 }}>{t('model_sheet.files.col_date')}</span>
              <span style={{ width: 44, flexShrink: 0, textAlign: 'right' }}>{t('model_sheet.files.col_version')}</span>
            </div>
            {sorted.map(f => (
              <FileRow key={f.id} fitxer={f} selected={f.id === selectedId}
                onSelect={() => setSelectedId(f.id)} />
            ))}
          </div>
          {/* DRETA — detall del fitxer seleccionat; buit discret si cap. */}
          <div style={{ width: 340, flexShrink: 0 }}>
            {selected ? (
              <FileDetail key={selected.id} fitxer={selected}
                onPreview={() => setPopup({ url: previewUrl(selected), nom: selected.nom_fitxer })}
                onHistory={() => openHistory(selected)}
                onNewVersion={file => handleUpload(file, selected.id)}
                onEdit={() => navigate(`/models/${modelId}/ftt/${selected.id}`)}
                onDelete={() => handleDelete(selected.id)} />
            ) : (
              <div style={{
                border: '0.5px solid var(--border)', borderRadius: 8, padding: '40px 20px',
                textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)', fontStyle: 'italic',
              }}>
                <i className="ti ti-click" aria-hidden="true"
                   style={{ fontSize: 'var(--fs-display)', display: 'block', marginBottom: 8, color: 'var(--gray)' }} />
                {t('model_sheet.files.select_prompt')}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Una fila de la llista (esquerra). Columnes: icona · nom · tipus · data · versió.
function FileRow({ fitxer, selected, onSelect }) {
  const { t, i18n } = useTranslation()
  const ext = fileExt(fitxer.nom_fitxer)
  const date = fitxer.data_pujada
    ? new Date(fitxer.data_pujada).toLocaleDateString(i18n.language || 'ca', { day: '2-digit', month: '2-digit', year: '2-digit' })
    : '—'
  return (
    <div onClick={onSelect} title={fitxer.nom_fitxer}
      style={{
        display: 'flex', alignItems: 'center', gap: 12, padding: '8px 12px', cursor: 'pointer',
        borderBottom: '0.5px solid var(--border)',
        background: selected ? 'var(--gold-pale)' : 'transparent',
        borderLeft: selected ? '2px solid var(--gold)' : '2px solid transparent',
      }}>
      <i className={`ti ${iconForExt(ext)}`} aria-hidden="true"
         style={{ fontSize: 18, color: 'var(--text-muted)', flexShrink: 0, width: 18 }} />
      <span style={{ flex: 1, minWidth: 0, fontSize: 'var(--fs-body)', color: 'var(--text-main)',
                     overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{fitxer.nom_fitxer}</span>
      <span style={{ width: 80, flexShrink: 0, fontSize: 'var(--fs-label)', fontFamily: FILES_MONO,
                     color: 'var(--text-muted)', textTransform: 'uppercase' }}>{ext || '—'}</span>
      <span style={{ width: 96, flexShrink: 0, fontSize: 'var(--fs-label)', fontFamily: FILES_MONO,
                     color: 'var(--text-muted)' }}>{date}</span>
      <span style={{ width: 44, flexShrink: 0, textAlign: 'right', fontSize: 'var(--fs-label)',
                     fontFamily: FILES_MONO, color: 'var(--text-muted)' }}>v{fitxer.versio}</span>
    </div>
  )
}

// Línia etiqueta · valor del panell de detall.
function DetailRow({ label, value }) {
  return (
    <div style={{ display: 'flex', gap: 8, padding: '3px 0', fontSize: 'var(--fs-body)' }}>
      <span style={{ width: 92, flexShrink: 0, color: 'var(--text-muted)', fontFamily: FILES_MONO, fontSize: 'var(--fs-label)' }}>{label}</span>
      <span style={{ flex: 1, minWidth: 0, color: 'var(--text-main)', wordBreak: 'break-word' }}>{value}</span>
    </div>
  )
}

// Panell de detall (dreta): miniatura en cascada de degradació + característiques + accions.
function FileDetail({ fitxer, onPreview, onHistory, onNewVersion, onEdit, onDelete }) {
  const { t, i18n } = useTranslation()
  const [imgError, setImgError] = useState(false)
  const ext = fileExt(fitxer.nom_fitxer)
  // Document .ftt editable: el botó "Edita" obre l'editor de fitxa sobre aquest ModelFitxer.
  const isTechSheet = fitxer.tipus === 'TECHSHEET' || ext === 'ftt'
  const isEditable = isTechSheet
  const url = previewUrl(fitxer)
  const mt = fitxer.mimetype || ''
  // Cascada: imatge → <img>; PDF → icona (no hi ha pdf.js, no rasteritzem); altres → icona.
  const isImg = (mt.startsWith('image/') || PREVIEW_IMG_RE.test(fitxer.nom_fitxer || '')) && url && !imgError
  const isPdf = mt === 'application/pdf' || ext === 'pdf'
  const date = fitxer.data_pujada
    ? new Date(fitxer.data_pujada).toLocaleDateString(i18n.language || 'ca', { day: '2-digit', month: 'long', year: 'numeric' })
    : '—'

  const actBtn = {
    padding: '4px 8px', fontSize: 'var(--fs-body)', border: '0.5px solid var(--border)',
    background: 'transparent', borderRadius: 4, cursor: 'pointer', color: 'var(--text-muted)',
  }

  return (
    <div style={{ border: '0.5px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
      {/* Miniatura */}
      <div style={{ height: 200, background: 'var(--bg-muted)', display: 'flex', flexDirection: 'column',
                    alignItems: 'center', justifyContent: 'center', gap: 8 }}>
        {isImg ? (
          <img src={url} alt={fitxer.nom_fitxer} onError={() => setImgError(true)}
               style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
        ) : (
          <>
            <i className={`ti ${isPdf ? 'ti-file-text' : iconForExt(ext)}`} aria-hidden="true"
               style={{ fontSize: 'var(--fs-display)', color: 'var(--text-muted)' }} />
            <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              {t('model_sheet.files.no_preview')}
            </span>
          </>
        )}
      </div>
      {/* Característiques */}
      <div style={{ padding: '12px 14px' }}>
        <div style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)',
                      wordBreak: 'break-word', marginBottom: 8 }}>{fitxer.nom_fitxer}</div>
        <DetailRow label={t('model_sheet.files.col_type')} value={mt || (ext ? ext.toUpperCase() : '—')} />
        <DetailRow label={t('model_sheet.files.col_version')} value={`v${fitxer.versio}`} />
        <DetailRow label={t('model_sheet.files.col_date')} value={date} />
        {/* Accions (deleguen als endpoints existents; cap canvi de backend). */}
        <div style={{ display: 'flex', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
          {isTechSheet ? (
            <>
              <button type="button" onClick={onEdit} style={{ ...actBtn, color: 'var(--gold)', borderColor: 'var(--gold)' }}>
                <i className="ti ti-edit" aria-hidden="true" /> {t('model_sheet.files.edit')}
              </button>
              <button type="button" onClick={onHistory} style={actBtn}>
                <i className="ti ti-history" aria-hidden="true" /> {t('model_sheet.version_history')}
              </button>
              <button type="button" onClick={onDelete}
                style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }}>
                <i className="ti ti-trash" aria-hidden="true" /> {t('model_sheet.files.delete')}
              </button>
            </>
          ) : (
            <>
              <button type="button" onClick={onPreview} style={{ ...actBtn, color: 'var(--text-main)' }}>
                <i className="ti ti-eye" aria-hidden="true" /> {t('model_sheet.view')}
              </button>
              {isEditable && (
                <button type="button" onClick={onEdit} style={{ ...actBtn, color: 'var(--gold)', borderColor: 'var(--gold)' }}>
                  <i className="ti ti-edit" aria-hidden="true" /> {t('model_sheet.files.edit')}
                </button>
              )}
              <label title={t('model_sheet.new_version')} style={{ ...actBtn }}>
                <i className="ti ti-plus" aria-hidden="true" /> {t('model_sheet.new_version')}
                <input type="file" style={{ display: 'none' }}
                  accept={UPLOAD_ACCEPT}
                  onChange={e => e.target.files[0] && onNewVersion(e.target.files[0])} />
              </label>
              <button type="button" onClick={onHistory} title={t('model_sheet.version_history')} style={actBtn}>
                <i className="ti ti-history" aria-hidden="true" />
              </button>
              <button type="button" onClick={onDelete} title={t('model_sheet.files.delete')}
                style={{ ...actBtn, color: 'var(--err)', borderColor: 'var(--err)' }}>
                <i className="ti ti-trash" aria-hidden="true" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

const GRAVETAT_STYLE = {
  CRITICA:     { bg: '#fce8e6', color: '#c5221f', border: '#f5c6c6' },
  IMPORTANT:   { bg: '#fff3e0', color: '#c8900a', border: '#f0c040' },
  INFORMATIVA: { bg: '#e6f4ea', color: '#137333', border: '#a8d5b5' },
}

function TabAIAnalysis({ modelId }) {
  const { t } = useTranslation()
  const token = localStorage.getItem('access_token')
  const [analisi, setAnalisi] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleAnalyze = async () => {
    setLoading(true); setError(''); setAnalisi(null)
    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/analisi-ia/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({}),
      })
      const d = await r.json()
      if (r.ok) setAnalisi(d.analisi)
      else setError(d.error || t('model_sheet.err_unknown'))
    } catch {
      setError(t('model_sheet.err_connection'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <div style={{ marginBottom: 16 }}>
        <p style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 12 }}>
          {t('model_sheet.ai_description')}
        </p>
        <button type="button" onClick={handleAnalyze} disabled={loading}
          style={{
            padding: '8px 20px', background: loading ? '#ccc' : 'var(--gold)',
            color: 'var(--white)', border: 'none', borderRadius: 6,
            fontSize: 'var(--fs-body)', fontWeight: 500, cursor: loading ? 'not-allowed' : 'pointer',
          }}>
          {loading ? (
            <><i className="ti ti-loader" aria-hidden="true" /> {t('model_sheet.analyzing')}</>
          ) : (
            <><i className="ti ti-cpu" aria-hidden="true" /> {t('model_sheet.launch_ai')}</>
          )}
        </button>
      </div>

      {error && (
        <div style={{ background: '#fee', border: '1px solid #fcc', borderRadius: 6,
                      padding: '8px 12px', fontSize: 'var(--fs-body)', color: '#c00', marginBottom: 12 }}>
          {error}
        </div>
      )}

      {analisi && (
        <div>
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                        marginBottom: 12 }}>
            {analisi.resum}
            {' · '}{t('model_sheet.files_analyzed', { count: analisi.fitxers_analitzats })}
          </div>

          {(analisi.alertes || []).length === 0 ? (
            <div style={{ fontSize: 'var(--fs-body)', color: '#137333', padding: '12px 0' }}>
              ✓ {t('model_sheet.no_discrepancies')}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {analisi.alertes.map((alerta, i) => {
                const style = GRAVETAT_STYLE[alerta.gravetat] || GRAVETAT_STYLE.INFORMATIVA
                return (
                  <div key={i} style={{
                    background: style.bg, border: `1px solid ${style.border}`,
                    borderRadius: 8, padding: '12px 14px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8,
                                  marginBottom: 4 }}>
                      <span style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: style.color,
                                     padding: '1px 8px', background: 'rgba(255,255,255,0.6)',
                                     borderRadius: 20 }}>
                        {t(`alerts.gravetat.${alerta.gravetat}`, alerta.gravetat)}
                      </span>
                      <span style={{ fontSize: 'var(--fs-body)', color: style.color }}>
                        {alerta.tipus?.replace(/_/g, ' ')}
                      </span>
                      {alerta.pom_afectat && (
                        <span style={{ fontSize: 'var(--fs-body)',
                                       color: style.color, fontWeight: 500 }}>
                          {alerta.pom_afectat}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)',
                                  marginBottom: 6 }}>
                      {alerta.descripcio}
                    </div>
                    {(alerta.valor_taula || alerta.valor_patro) && (
                      <div style={{ fontSize: 'var(--fs-body)', color: style.color, marginBottom: 4 }}>
                        {t('model_sheet.compare_values', { table: alerta.valor_taula || '—', pattern: alerta.valor_patro || '—' })}
                      </div>
                    )}
                    <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
                                  fontStyle: 'italic' }}>
                      → {alerta.accio_suggerida}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
