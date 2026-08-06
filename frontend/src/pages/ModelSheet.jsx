import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Feedback from '../components/ui/Feedback'
import ActionsMenu from '../components/model/ActionsMenu'
import WatchpointDrawer from '../components/model/WatchpointDrawer'
import CheckMeasureEditor from '../components/model/CheckMeasureEditor'
import { fittingSource } from '../components/model/measureSources'
import MeasuresEntryPanel from '../components/model/MeasuresEntryPanel'
import ComprovacioPanel from '../components/model/ComprovacioPanel'
import FittingRepasPanel from '../components/model/FittingRepasPanel'
import PropagatedEditor from './PropagatedEditor'
import GraduacioContenidor from '../components/grading/GraduacioContenidor'
import GraduacioSuperficie from '../components/grading/GraduacioSuperficie'
import Modal from '../components/ui/Modal'
import RuleSetCard from '../components/model/RuleSetCard'
import { MaduresaBadge, EncarrecDelClient } from '../components/model/FederacioBadge'
import { models, watchpoints, modelTasks, fittingSessions, modelFitxers } from '../api/endpoints'
import { authFetch } from '../api/authFetch'
import { missatgeError } from '../api/errorsAuth'
import useAuthStore from '../store/auth'
import ObrirTascaDialog from '../components/model/ObrirTascaDialog'
import ModalAcabarTasca from '../components/model/ModalAcabarTasca'
import BadgeLliurable from '../components/model/BadgeLliurable'
import { CARA_CAP, caraDeError, caraObrirTasca } from '../utils/caraObrirTasca'
import { CODE_PER_TAB, saltDeSuperficie, minutsDeSessio } from '../utils/sessioActiva'
import { UPLOAD_ACCEPT } from '../utils/uploads'
import RegistreActivitatTab from '../components/model/RegistreActivitatTab'
import DashboardTab from '../components/model/DashboardTab'
import TasksTab from '../components/model/TasksTab'
import PatternTab from '../components/pattern/PatternTab'
import useConfirmacioRuleset from '../components/model/useConfirmacioRuleset'

const API = import.meta.env.VITE_API_URL || ''
// Menú net (PEÇA 5): Size Check absorbit a Mesures (taula base amb estadis), Producció retirat;
// Fitting → Escalat (editor propagat). v2: el Size Check antic queda jubilat — /size-check
// redirigeix a /mesures (App.jsx), aquí ja no hi ha cap branca 'Size Check'.
// 'Anàlisi IA' OCULTAT del menú (peça F): inert avui. El case i el component TabAIAnalysis es
// conserven (no destructiu); simplement no apareix a la banda de pestanyes.
// 'Patró' va entre Escalat i Fitxa tècnica: és una etapa del flux tècnic (el patró es
// digitalitza i s'escala), no un annex documental.
const TABS = ['Dashboard', 'Resum', 'Mesures', 'Escalat', 'Patró', 'Fitxa tècnica', 'Fitxers', "Registre d'activitat", 'Tasques']

// ELS PARÀMETRES QUE OBREN UNA SUPERFÍCIE DE TREBALL, i que per tant s'han de netejar en sortir-ne
// (v. `netejaEdicio`). Els tres diuen «entra a treballar», no «mira aquesta pantalla»:
//   · `mode=entry`        → Definició POM (`entryMode` → `enterEdit('Mesures','pom')`)
//   · `mode=graduacio`    → LA GRADUACIÓ (P0.5d): superfície pròpia, no la taula de Gravar POM
//   · `task_id`           → la presa lligada a una tasca ja En curs (J1b, «Mesurar prenda»)
//   · `fitting_session`   → la sessió de fitting (obre la tasca `size_check` si no ve amb task_id)
// `tab` NO hi és a posta: diu quina pantalla es mira, i és exactament el que l'F5 ha de conservar.
//
// LA GRADUACIÓ JA EN TÉ UN (P0.5d · 06/08). Aquí hi deia que no en tenia perquè era un calaix
// d'estat local que l'F5 tancava tot sol; en passar a ser una SUPERFÍCIE PRÒPIA li calia adreça:
// per a l'F5, i perquè la tasca de graduació hi pugui portar quan P0.4 connecti els botons.
// Reusa `mode` en comptes d'estrenar un paràmetre — és la mateixa pregunta («a què véns»).
const PARAMS_DE_TREBALL = ['mode', 'task_id', 'fitting_session']
// L'id del tab (clau de lògica: activeTab===, defaultTab) es manté; només se'n tradueix l'etiqueta.
const TAB_LABELS = {
  'Dashboard': 'model_sheet.tab_dashboard',
  'Tasques': 'model_sheet.tab_tasks',
  'Resum': 'model_sheet.tab_summary',
  'Mesures': 'model.tabs.mesures',
  'Escalat': 'model_sheet.tab_grading',
  'Patró': 'model_sheet.tab_pattern',
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

/**
 * LES ACCIONS PRINCIPALS D'UN TAB — fons BLANC amb la vora de la casa (Agus, 06/08).
 *
 * `btnSecondary` va `background:'transparent'`, i sobre el crema de la pàgina (`--bg-muted`) els
 * botons es fonien amb el fons: semblaven text amb una vora, no accions. Aquestes quatre són el
 * gest principal del tab i han de tenir cos.
 *
 * El blanc és `--white`: **`--panel` no existeix en aquest design system** (és el nom que fa
 * servir la maqueta v8.1, no un token del `index.css`), i inventar-lo aquí crearia un token
 * fantasma que ningú manté.
 */
const btnAccio = (deshabilitat = false) => ({
  ...btnSecondary,
  background: 'var(--white)',
  borderColor: 'var(--gold)',
  color: 'var(--gold)',
  opacity: deshabilitat ? 0.6 : 1,
  cursor: deshabilitat ? 'default' : 'pointer',
})

const taskListFromResponse = (data) => data?.results || (Array.isArray(data) ? data : [])

// EL MOTIU D'UN `open-task` REBUTJAT, en paraules.
//
// `transition_task` té una paret que no és un error tècnic sinó una regla de negoci: una tasca
// amb línia en un albarà EMÈS no es pot reobrir, perquè rectificar-la vol dir una línia nova al
// pròxim albarà, no tornar a obrir la vella. Arribava com un 409 sense codi i el tècnic només
// veia «no s'ha pogut obrir la tasca»: la porta quedava tapiada i muda.
//
// El servidor ja envia `code` (`tasks/services_c.py`); aquí només es tria la frase. Un codi que
// aquest front encara no conegui cau al missatge genèric — mai a una clau i18n inventada.
const MOTIUS_OPEN_TASK = { tasca_albaranada: 'model_sheet.open_task_err_albaranada' }
function motiuOpenTask(e, t) {
  const clau = MOTIUS_OPEN_TASK[e?.response?.data?.code]
  return clau ? t(clau) : t('model_sheet.open_task_err')
}

export default function ModelSheet({ defaultTab = 'Dashboard', autoEdit = null }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const { t } = useTranslation()
  const [sp, setSp] = useSearchParams()
  // ?tab= permet obrir el full directament en una pestanya concreta (p.ex. ModelFabric → tab Mesures).
  // El task_id/session entrants (J1b) es plomaran a sobre d'aquest mateix mecanisme més endavant.
  const tabParam = sp.get('tab')
  const taskParam = sp.get('task_id')
  // Sprint Y — context de sessió de fitting: ?tab=Mesures&task_id=&fitting_session= fa que el tab
  // Mesures obri la font FITTING (eix base, regles read-only) en comptes del check. Es ploma sobre el
  // MATEIX mecanisme de task_id (J1b), sense mecanisme paral·lel.
  const fittingSessionParam = sp.get('fitting_session')
  // ?mode=entry → "Definició POM" via URL: obre el tab Mesures en mode ENTRADA (genesi/wizard) encara
  // que el model JA tingui mesures (l'usuari ve a definir/afegir POMs, no a consultar).
  const entryMode = sp.get('mode') === 'entry'
  // ?mode=graduacio → LA GRADUACIÓ (P0.5d): superfície pròpia dins del tab Mesures. És l'adreça
  // que li faltava —per a l'F5 i perquè la tasca de graduació hi porti— i la font de veritat de
  // si s'hi és: aquí no hi ha estat local paral·lel que se'n pugui desdir.
  const graduacioMode = sp.get('mode') === 'graduacio'
  const [model, setModel] = useState(null)
  const [activeTab, setActiveTab] = useState(TABS.includes(tabParam) ? tabParam : defaultTab)
  const [taulaRows, setTaulaRows] = useState([])
  const [modelTaskRows, setModelTaskRows] = useState([])
  const [sizesAmbDades, setSizesAmbDades] = useState(null)
  const [, setDeltes] = useState(null)
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

  // (`pomTask` també se'n va: el seu únic lector era `pomGenesisOpen`.)
  const hasBaseValue = taulaRows.some(r => r.base_value_cm != null)
  // El gate de Mesures llegeix l'estat de la feina de POM del MODEL, no de la llista de
  // tasques: aquella va escopada per `view_team_tasks`, i qui no tenia la capability veia
  // «Mesures encara no disponibles» amb la tasca Done i la taula plena. Un permís sobre
  // quines tasques veus no pot decidir si el model té mesures.
  const pomDone = !!model?.pom_task_done
  // (Aquí hi havia `pomGenesisOpen` — «la tasca pom està En curs o Paused». Era l'única cosa que
  //  l'usava el gate d'entrada al tab, i obria l'edició sense que ningú l'hagués demanada; v. la
  //  nota de l'efecte de més avall. Sense consumidors, el càlcul se'n va amb ell.)
  const pomReady = pomDone || hasBaseValue

  // POM-genesi surt del tab Mesures lliure: Mesures és treballable si el model està DEFINIT
  // — o bé té POMs amb valor base, o bé la feina de POM del model consta Done. L'AND anterior
  // mesurava el testimoni de procés (la ModelTask), que és un proxy de la definició, no la
  // definició: un model amb POMs amb valor està definit, hi hagi tasca o no. `hasBaseValue` sol
  // ja demostra que no és verge; `pomDone` sol segueix cobrint el model que ve de la gènesi amb
  // POMs materialitzats i encara SENSE valors, que és on el tècnic ha d'entrar a escriure'ls.
  // `task_id` de size_check continua sent treball, no genesi; `mode=entry` i pom oberta/pausada
  // obren la pantalla POM pròpia.
  const [mesuresEntry, setMesuresEntry] = useState(false)
  // Sprint B — la caixa buida té DUES portes (començar de zero / copiar d'un altre model) i
  // totes dues entren al MATEIX panell de gènesi: la intenció viatja perquè el panell hi obri
  // la via correcta, en comptes de duplicar la superfície de còpia aquí (llei del pedaç).
  const [mesuresIntent, setMesuresIntent] = useState(null)   // null | 'copy'
  const prevTabRef = useRef(null)
  useEffect(() => {
    // Mentre carrega no decidim NI actualitzem el ref (si no, l'entrada directa ?tab=Mesures fixaria el
    // ref a 'Mesures' durant la càrrega i la genesi no s'avaluaria mai en acabar de carregar).
    if (loading) return
    if (activeTab === 'Mesures' && prevTabRef.current !== 'Mesures') {
      // EL DEFECTE DEL TAB MESURES ÉS SEMPRE LA CONSULTA (contracte d'Agus, 06/08): amb dades,
      // sense, carregant o amb error. L'edició NOMÉS per gest explícit — el botó ①, `?mode=entry`
      // a la URL, o una tasca entrant (`?task_id=`).
      //
      // AQUÍ HI HAVIA `pomGenesisOpen`, i era el defecte que l'Agus veia: n'hi havia prou que la
      // tasca `pom` del model estigués En curs o PAUSADA perquè una càrrega freda de
      // `/models/<id>?tab=Mesures` —sense cap paràmetre— obrís Definició POM amb píndoles i
      // «Gravar POM». Al MILEY (1308) la `pom` està Paused des d'abans-d'ahir, i per tant el tab
      // no s'havia pogut consultar mai més. Una tasca oberta diu que hi ha feina EN CURS, no que
      // qui obre el full la vulgui reprendre ARA: reprendre-la és el gest del botó.
      //
      // El `triaTab` de `c5e130de` tapava el GEST de canviar de tab; això és L'ENTRADA, que és
      // un altre camí i el que l'Agus fa de debò. Les dues calen: aquesta mata l'origen, i
      // `triaTab` cobreix el cas del modal pendent, on l'estat sobreviu al canvi de pestanya.
      setMesuresEntry(entryMode && !taskParam)
    }
    prevTabRef.current = activeTab
  }, [activeTab, loading, entryMode, taskParam])

  // Porta-menú: obre (crea-si-falta + auto-assign + En curs) la tasca `code` i navega a l'eina amb el
  // task_id. Reusa el servei open-task; el botó funciona encara que el model no tingui la tasca creada.
  const [openingTask, setOpeningTask] = useState(false)
  // F2.1 — `UserProfile.id`, que és contra el que es comparen `assignee` i `obert_per`.
  // MAI `user.id` (User.id): no hi ha cap garantia que coincideixin.
  const jo = useAuthStore(s => s.user?.profile_id ?? null)
  // FASE A — edició INLINE: la tab commuta consulta↔edició mantenint el context (sidebar+tabs+
  // capçalera+watchpoint), en comptes de navegar a /mesures·/escalat. openTask posa la tasca
  // InProgress (compta-temps); en sortir de mode edició es pausa. El lifecycle del timer es mou de
  // mount/unmount de ruta (EscalatTask/ModelMeasurements) a enter/exit de mode.
  const [editing, setEditing] = useState(null)        // null | 'Mesures' | 'Escalat'
  // Subvista de Mesures en CONSULTA: la taula del model ↔ el repàs dels fittings fets. Les dues
  // miren la mateixa matèria (POM × columnes) des de dos costats; no mereixen dues tabs.
  // D-31.17 — la COMPROVACIÓ entra com a tercera subvista de Mesures, que és on la maqueta la
  // posa (`.sub2`: Taula de mesures · Repàs de fittings · Comprovació). No és una tab pròpia del
  // model: el que comprova són les mesures, i sortir de Mesures per mirar-les seria perdre el fil.
  const [mesuresView, setMesuresView] = useState('taula')   // 'taula' | 'repas' | 'comprovacio'
  const [editTaskId, setEditTaskId] = useState(null)
  // Sprint Y — sessió de fitting resolta (quan hi ha ?fitting_session=): la font fitting la rep per
  // sourceCtx. null = camí del check normal.
  const [fittingSession, setFittingSession] = useState(null)
  // PEÇA 2 — guard 400: open-task deixa la tasca En curs (InProgress). Aquest ref recorda quina tasca està
  // VIVA per pausar-la EXACTAMENT UN COP. Sense ell, exitEdit i el cleanup de desmuntatge demanaven tots
  // dos transition→Paused sobre la mateixa tasca → la 2a era Paused→Paused, que ALLOWED rebutja amb 400
  // (services_c.py). Nul = res a pausar (≈ task.status !== 'InProgress').
  const activeTaskRef = useRef(null)
  // EL TAB D'ON ES VE. L'omple `obreDeDebo` (el punt comú de les quatre portes del tab i de les
  // entrades per URL) amb el tab on l'usuari ERA en obrir la superfície, i el modal d'acabar/
  // pausar hi torna. Ref i no estat: no ha de repintar res, només recordar-ho.
  const tabDeRetornRef = useRef(null)
  const pauseActiveTask = useCallback(() => {
    const tid = activeTaskRef.current
    if (tid == null) return                 // ja pausada o cap tasca En curs → no demanem transició (evita 400)
    activeTaskRef.current = null
    modelTasks.transition(tid, { to_status: 'Paused' }).catch(() => {})
  }, [])
  // F2.1 — la tasca VIGENT d'una superfície. El backend ja la marca (`es_vigent`, resolt amb
  // `tasca_vigent`): aquí NO es reimplementa el criteri, només es llegeix.
  const tascaVigentDe = useCallback(
    code => modelTaskRows.find(x => x.task_type_code === code && x.es_vigent) || null,
    [modelTaskRows])

  // Declarat ABANS d'`obreDeDebo`, que el referencia dins d'un useCallback: en aquest fitxer
  // ja hi ha hagut una TDZ que cap gate va veure, i l'ordre de declaració no és cosmètic.
  const [dialeg, setDialeg] = useState(null)   // {cara, tab, code, tasca} | null
  // EL GEST DE GRADUAR viu a MESURES (correcció de rumb, Agus 31/07): el calaix lateral sobre la
  // taula, i Escalat torna a ser la seva pestanya de sempre.
  //
  // PUJAT AQUÍ pel mateix motiu que `dialeg`: des que Graduació passa pel circuit de tasca,
  // `obreDeDebo` l'obre, i `obreDeDebo` és un `useCallback` declarat just a sota. Deixar-lo on
  // era (200 línies més avall) el posava dins la zona morta temporal — que és exactament la
  // petada del 31/07 que `ops/qa/qa_mount_modelsheet.py` vigila.
  const [graduacioObert, setGraduacioObert] = useState(false)

  // El pas final d'obrir: el que enterEdit feia sempre, ara reutilitzable des del modal.
  // ③ «MESURAR PRENDA» VOL UNA SESSIÓ DE FITTING, no només la tasca.
  //
  // Sense sessió, `source={fittingSession ? fittingSource : null}` cau a la font `check` i
  // s'obria la taula de PRESA DE BASE (l'EditableTable amb el carril), que és la de Definició
  // POM i no la pantalla de fitting. La vista de la maqueta v3 —historial paginat, columna REAL,
  // veredictes, nota i PDF— és `fittingSource`, i el seu `load` exigeix `ctx.fittingSession`.
  //
  // Es reutilitza el circuit existent, sense mecanisme nou:
  //   1. una sessió OBERTA del model → s'hi enganxa;
  //   2. si no, una de PROGRAMADA → també (`open-task` amb `fitting_session_id` la passa a
  //      Oberta, que és la baula Y1 que ja existia per a l'entrada per URL);
  //   3. si no n'hi ha cap → la crea amb «Fitting aquí i ara» (`schedule-now`, C4).
  // El conflicte suau es tracta EXACTAMENT com a `FittingSessionList` (confirmar i reintentar
  // amb `force`): mateix acte, mateixa pregunta, mateixos literals.
  //
  // La PEÇA no es resol aquí: `fittingSource.load` ja la crea o la recupera (`resolvePieceFitting`,
  // amb el seu 409 `piece_exists`). Aquí només cal la sessió.
  const sessioDeFitting = useCallback(async (force = false) => {
    for (const estat of ['Oberta', 'Programada']) {
      const r = await fittingSessions.list({ model: id, estat, page_size: 1 })
      const files = r.data?.results ?? r.data ?? []
      if (files.length) return files[0]
    }
    const r = await fittingSessions.scheduleNow({
      model_id: parseInt(id), ...(force ? { force: true } : {}) })
    if (r.data?.requires_confirmation) {
      // Conflicte suau: es demana, no es força en silenci. Si diu que no, no s'entra.
      if (!window.confirm(r.data.warning || t('fitting.now.soft_conflict'))) return null
      return sessioDeFitting(true)
    }
    return r.data
  }, [id, t])

  const obreDeDebo = useCallback((tab, code) => {
    setOpeningTask(true)
    // D'ON VENIM, abans d'obrir res: el tab on l'usuari és ARA. Les quatre portes del tab Mesures
    // hi passen totes, i també les entrades per URL (`?mode=entry`, `?task_id=`), que arriben
    // aquí per `enterEdit`. El modal d'acabar/pausar hi tornarà.
    tabDeRetornRef.current = activeTab
    // ③ vol la SESSIÓ ABANS que la tasca: `open-task` la rep per `fitting_session_id` i, si era
    // Programada, la passa a Oberta (la baula Y1 que ja feia servir l'entrada per URL). Per a la
    // resta de codis no hi ha sessió i el flux és el de sempre, intacte.
    const volSessio = tab === 'Mesures' && code === 'size_check'
    ;(volSessio ? sessioDeFitting() : Promise.resolve(null))
      .then(sessio => {
        if (volSessio && !sessio) {
          // Sense sessió no hi ha pantalla de fitting. Val més no entrar que entrar a una ALTRA
          // taula que se li assembla —que és exactament el defecte que això tanca.
          setOpeningTask(false)
          return null
        }
        if (sessio) setFittingSession(sessio)
        return models.openTask(parseInt(id), code, sessio?.id ?? null)
      })
      .then(res => {
        if (!res) return
        setEditTaskId(res.data.task_id)
        activeTaskRef.current = res.data.task_id   // open-task la deixa En curs → viva per pausar després
        // PUNT COMÚ: una tasca 'pom' obre el tab Mesures en mode ENTRADA (wizard), no edició de graella.
        // `size_check` sobre Mesures passa per `editing='Mesures'` → la superfície de PRESA
        // (`CheckMeasureEditor` editable). Hi arribava només per URL; des del 06/08 també pel
        // botó ③ «Mesurar prenda», pel mateix camí i sense mecanisme nou.
        if (tab === 'Mesures' && code === 'pom') setMesuresEntry(true)
        // GRADUACIÓ DES DE MESURES: la tasca és `grading` però la superfície NO és el tab
        // Escalat. Sense aquesta branca el `setEditing('Mesures')` de sota obriria la presa —una
        // superfície que no té res a veure amb graduar— amb el rellotge de graduació al damunt.
        //
        // P0.5d — ON PORTA, que és l'únic que canvia (com s'hi entra ja era això). Abans obria el
        // CONTENIDOR de tria de joc; ara porta a la SUPERFÍCIE DE GRADUACIÓ, i el contenidor
        // s'obre des d'allà si el model no té joc o se'n vol canviar. Triar joc era només el
        // primer pas de graduar, i era l'únic que tenia pantalla.
        else if (tab === 'Mesures' && code === 'grading') {
          setSp(prev => {
            const net = new URLSearchParams(prev)
            net.set('mode', 'graduacio')
            return net
          }, { replace: true })
        }
        else setEditing(tab)
        reloadTasks()
      })
      // EL TOAST DIU LA PARET, no «no s'ha pogut». Un 409 amb `code` porta el motiu del servidor
      // (avui només `tasca_albaranada`: la tasca ja té línia en un albarà EMÈS i reobrir-la seria
      // refacturar). Sense codi, el missatge genèric de sempre. Al model 188 això eren 7 intents
      // en dues hores amb el mateix toast mut (v. DIAGNOSI_CICLE_TASCA_COMPLET §M-2).
      //
      // F2.1 — si l'estat precalculat anava ranci, el 409 encara pot obrir la cara correcta:
      // el modal té dues entrades (estat i error) i una sola sortida.
      .catch(e => {
        const cara = caraDeError(e)
        if (cara) setDialeg({ cara, tab, code, tasca: tascaVigentDe(code) })
        else setFeedback({ type: 'err', text: motiuOpenTask(e, t) })
      })
      .finally(() => setOpeningTask(false))
  }, [activeTab, id, t, reloadTasks, tascaVigentDe, setSp, sessioDeFitting])

  // F2.2 · D-1 — LA PORTA DE LA FITXA. Era el forat original de tota aquesta feina: «Modificar»
  // navegava sense `task_id`, l'editor autodesava cada 2 s i el temps d'editar la fitxa no
  // existia enlloc. Ara obre sessió sobre la tasca vigent `tech_sheet` i propaga el `task_id` a
  // la URL, que és el que fa que l'editor demani el lock i pausi en sortir.
  const obreFitxa = useCallback((fitxerId) => {
    const anar = tid => navigate(`/models/${id}/ftt/${fitxerId}?task_id=${tid}`)
    const vigent = tascaVigentDe('tech_sheet')
    const cara = caraObrirTasca(vigent, jo)
    if (cara !== CARA_CAP) { setDialeg({ cara, tab: 'Fitxa tècnica', code: 'tech_sheet', tasca: vigent, fitxerId }); return }
    setOpeningTask(true)
    models.openTask(parseInt(id), 'tech_sheet')
      .then(res => anar(res.data.task_id))
      .catch(e => {
        const c = caraDeError(e)
        if (c) setDialeg({ cara: c, tab: 'Fitxa tècnica', code: 'tech_sheet', tasca: vigent, fitxerId })
        else setFeedback({ type: 'err', text: motiuOpenTask(e, t) })
      })
      .finally(() => setOpeningTask(false))
  }, [id, jo, navigate, t, tascaVigentDe])

  // F2.1 · REGLA D'OR — el modal NO surt en el cas normal. `caraObrirTasca` decideix, i si diu
  // CARA_CAP s'obre directament: zero fricció, zero clics. Només quan hi ha conflicte, feina
  // lliurada o albarà emès es demana res a ningú.
  const enterEdit = (tab, code, intent = null) => {
    if (openingTask) return
    setMesuresIntent(intent)
    const vigent = tascaVigentDe(code)
    const cara = caraObrirTasca(vigent, jo)
    if (cara !== CARA_CAP) { setDialeg({ cara, tab, code, tasca: vigent }); return }
    obreDeDebo(tab, code)
  }
  // T4 — SORTIR ÉS DECIDIR. Fins ara sortir pausava en silenci, i acabar una tasca depenia de
  // trobar la píndola flotant de F2.3. Ara, en desar i sortir d'una superfície de treball, el
  // modal central pregunta el que la persona ja està pensant: ho has acabat o hi seguiràs?
  // Sense tram viu (res obert) no hi ha res a decidir i la sortida és neta com abans.
  // {taskId, tasca} | null — `tasca` és la fila FRESCA del servidor, no la de `modelTaskRows`:
  // el modal ensenya temps i decideix opcions, i totes dues coses van amb l'estat d'ara.
  const [acabant, setAcabant] = useState(null)
  // …I LA URL TAMBÉ ÉS ESTAT. Sortir de l'edició deixava els paràmetres que hi havien FET entrar
  // enganxats a la barra d'adreces, i com que qui els consumeix són efectes d'UN SOL COP
  // (`entryEditRef`, `autoTaskRef`, `autoSessionRef`), dins d'aquest muntatge no es notava: la
  // pantalla es quedava a la consulta i tot semblava correcte. **Fins a l'F5.** En remuntar, els
  // refs neixen a zero, la URL encara diu `mode=entry` i el full tornava a obrir la tasca i a
  // entrar en edició — l'usuari premia F5 des de la consulta i es trobava editant.
  //
  // La regla: l'F5 restaura la vista on l'usuari ÉS, no la que la URL arrossega. Els tres
  // paràmetres que obren una superfície de TREBALL es netegen en sortir; `tab` es queda, que és
  // justament la vista on l'usuari és.
  //
  // Va per `setSp(..., {replace:true})` i no per `history.replaceState` cru: el segon canviaria la
  // barra d'adreces sense que el router se n'assabentés, i `sp` seguiria dient `mode=entry` la
  // resta del muntatge. Substitueix l'entrada de l'historial en comptes d'afegir-n'hi una, o sigui
  // que la fletxa Enrere segueix portant d'on es venia i no a un pas intermedi d'aquesta mateixa
  // pantalla.
  const netejaEdicio = useCallback(() => {
    setEditTaskId(null)
    setEditing(null)
    setMesuresEntry(false)
    setMesuresIntent(null)
    setSp(prev => {
      const net = new URLSearchParams(prev)
      let tocat = false
      for (const clau of PARAMS_DE_TREBALL) {
        if (net.has(clau)) { net.delete(clau); tocat = true }
      }
      // Sense res a treure no s'escriu: una crida per cada sortida neta embrutaria l'historial
      // (i `exitEdit` es crida també quan no hi havia cap mode obert).
      return tocat ? net : prev
    }, { replace: true })
  }, [setSp])
  // Q1·Q2·Q3 (06/08) — LA SORTIDA PREGUNTA AL SERVIDOR ABANS DE PREGUNTAR A LA PERSONA.
  //
  // Aquí hi havia tres defectes encadenats, i tots tres sortien de decidir amb `modelTaskRows`,
  // que és una FOTO del moment de carregar la pàgina:
  //
  //  · **«total de la tasca: 0h 00m»** sobre una sessió de mitja hora (el cas de la captura).
  //    La foto es va fer en entrar, quan la tasca encara no havia acumulat res; ni el camí
  //    `?task_id=` ni el pas del temps la refresquen. El modal no mentia sobre el rellotge del
  //    servidor: llegia un altre moment.
  //  · **«Transició no permesa: Paused → Paused»**. El guard de tasca oblidada pausa sol als 30
  //    minuts; la persona segueix a la pantalla, surt, i el modal li ofereix pausar una cosa que
  //    ja està pausada. L'usuari no pot veure MAI un error de la nostra màquina d'estats.
  //  · **el modal sortia sense sessió**: n'hi havia prou d'entrar per `?task_id=` i tornar a
  //    sortir sense tocar res.
  //
  // LA REGLA, ara: es demana la tasca FRESCA i el modal només surt si segueix `InProgress` —
  // que és l'únic estat on hi ha alguna cosa a decidir, i l'únic des del qual les dues opcions
  // del modal són legals. Si el guard (o un altre gest) ja l'ha tancada, sortir és sortir.
  //
  // ⚠️ EL CRITERI NO ÉS LA DURADA. «No hi ha hagut sessió» no vol dir «ha durat poc»: una
  // sessió de dos minuts amb la tasca oberta ensenya el modal igual que una de dues hores
  // (decisió d'Agus). El que el fa callar és que no hi hagi res obert.
  const exitEdit = useCallback(() => {
    const tid = activeTaskRef.current
    if (tid == null) { netejaEdicio(); return }
    modelTasks.get(tid)
      .then(res => {
        const tasca = res.data
        if (tasca?.status !== 'InProgress') {
          // Res obert: cap decisió a prendre i cap transició a demanar.
          activeTaskRef.current = null
          netejaEdicio()
          return
        }
        setAcabant({ taskId: tid, tasca })
      })
      // Sense resposta no s'inventa un modal: val més sortir net que preguntar sobre un estat
      // que no sabem. El guard de tasca oblidada segueix cobrint la tasca que quedi oberta.
      .catch(() => { activeTaskRef.current = null; netejaEdicio() })
  }, [netejaEdicio])
  // La transició la fa el modal; aquí només queda deixar-ho tot al seu lloc. `activeTaskRef` es
  // buida perquè el cleanup de desmuntatge no torni a demanar una pausa ja feta (el 400 de la
  // PEÇA 2), i la reposició va al panell de Tasques del model — el Kanban no existeix.
  // ON ES CAU EN TANCAR LA TASCA: D'ON VENIES (Agus, 06/08).
  //
  // Anava sempre a Tasques, i això contradiu la pantalla d'on se surt: Graduació declara la seva
  // sortida natural amb «Tornar a Mesures», i el modal no la pot desmentir. El panell de Tasques
  // és destinació quan s'hi va expressament, o quan no hi ha context de retorn.
  //
  // El context el desa `obreDeDebo` (el punt comú per on passen les QUATRE portes del tab, i
  // també les entrades per URL): el tab on l'usuari ERA quan va obrir la superfície.
  const acabatOPausat = useCallback(() => {
    activeTaskRef.current = null
    setAcabant(null)
    netejaEdicio()
    reloadTasks(); reloadModel()
    setActiveTab(tabDeRetornRef.current || 'Tasques')
    tabDeRetornRef.current = null
  }, [netejaEdicio, reloadTasks, reloadModel])
  // ENTRAR AL TAB MESURES ÉS ENTRAR A LA CONSULTA. SEMPRE. (Contracte d'Agus, 06/08.)
  //
  // L'edició només s'obre pels quatre botons, per una URL amb mode explícit o per una tasca
  // entrant. Navegar-hi amb el tab, mai.
  //
  // EL DEFECTE QUE TANCA: en marxar de Mesures, l'efecte de sortida crida `exitEdit`, i si la
  // tasca era En curs això OBRE EL MODAL i deixa la neteja per a quan l'usuari respongui —
  // `mesuresEntry` es queda a `true`. En tornar a Mesures, el `sortia` d'aquell efecte ja no es
  // compleix (`activeTab === 'Mesures'`), ningú neteja res, i el panell d'edició reviu: clicar
  // el tab obria Definició POM amb píndoles i «Gravar POM» en comptes de la consulta.
  //
  // ES RESETEJA NOMÉS L'ESTAT DE MESURES, no `editing` sencer: si es ve d'editar Escalat, buidar
  // `editing` aquí li robaria el `sortia` a l'efecte de sortida i la tasca d'Escalat es quedaria
  // oberta sense modal ni pausa. Cada superfície tanca la seva en marxar-ne.
  const triaTab = useCallback((tab) => {
    if (tab === 'Mesures') {
      setMesuresEntry(false)
      setMesuresIntent(null)
      setGraduacioObert(false)
      setEditing(prev => (prev === 'Mesures' ? null : prev))
    }
    setActiveTab(tab)
  }, [])
  const finishPomEntry = useCallback(() => {
    activeTaskRef.current = null
    // Aquí es repetia el cos de `netejaEdicio` línia per línia. Ara el crida: aquest és EL camí
    // normal de sortida de Definició POM —prémer Gravar—, i amb la còpia inline es quedava fora
    // de la neteja de la URL, que és justament on més falta feia (s'hi entra per `?mode=entry`).
    netejaEdicio()
    // F1.2 — AQUÍ s'escrivia `status:'Done'` a la fila i `pom_task_done:true` al model, en local.
    // Desar ja no tanca la tasca (D-2), de manera que aquell optimisme ara MENTIRIA: pintaria
    // Done i el `reloadModel()` de tres línies més avall el desmentiria tot seguit.
    // El gate de Mesures no se'n ressent — és `pomDone || hasBaseValue`, i qui acaba de gravar
    // POM té valors base per definició.
    reloadTaula()
    reloadModel()
    reloadTasks()
    setWpVersion(v => v + 1)
  }, [netejaEdicio, reloadModel, reloadTaula, reloadTasks, setModel])
  // Sortir de mode edició/entrada en canviar de tab (pausa la tasca si n'hi havia).
  //
  // F2.4 · D-1 — I SALTAR, si el tab nou també és una superfície de treball. El tècnic que passa
  // de Mesures a Escalat no ha canviat de feina: ha canviat d'eina, i el rellotge l'ha de
  // seguir. SILENCIÓS per contracte: si el salt no es pot fer net (la tasca la té algú altre,
  // està albaranada, o encara no existeix) NO es pregunta res i simplement no se salta —
  // l'usuari ha canviat de pestanya, no ha demanat obrir res. L'única pista visible és
  // l'indicador de F2.3, que canvia de nom de tasca tot sol.
  useEffect(() => {
    const sortia = (editing && editing !== activeTab) || (mesuresEntry && activeTab !== 'Mesures')
    if (!sortia) return
    exitEdit()
    if (taskParam || fittingSessionParam) return   // context entrant explícit: mana ell
    const code = CODE_PER_TAB[activeTab]
    if (!code) return
    const vigent = tascaVigentDe(code)
    if (!saltDeSuperficie(activeTab, vigent, jo, caraObrirTasca(vigent, jo))) return
    obreDeDebo(activeTab, code)
  }, [activeTab, editing, mesuresEntry, exitEdit, taskParam, fittingSessionParam,
      tascaVigentDe, jo, obreDeDebo])
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

  // Sprint Y — resol la sessió de fitting entrant (?fitting_session=) perquè la font fitting la rebi.
  // Es fa un cop; la sessió és el contenidor, el treball i el compta-temps van per la tasca (task_id).
  useEffect(() => {
    if (!fittingSessionParam) { setFittingSession(null); return }
    let cancelled = false
    fittingSessions.get(fittingSessionParam)
      .then(r => { if (!cancelled) setFittingSession(r.data) })
      .catch(() => { if (!cancelled) setFittingSession(null) })
    return () => { cancelled = true }
  }, [fittingSessionParam])

  // Sprint Y — MATERIALITZACIÓ en obrir (decisió 6): si s'entra amb ?fitting_session= però SENSE
  // task_id (fulla de convocatòria / redirect de /fittings/<id>), s'obre la tasca size_check lligada
  // a la sessió (Y1: FK + obre la sessió Programada) i s'entra en mode Mesures pel MATEIX mecanisme
  // que J1b (activeTaskRef per pausar en sortir). Amb task_id ja present, mana J1b i això no dispara.
  const autoSessionRef = useRef(false)
  useEffect(() => {
    if (autoSessionRef.current || loading) return
    if (activeTab === 'Mesures' && fittingSessionParam && !taskParam) {
      autoSessionRef.current = true
      models.openTask(parseInt(id), 'size_check', fittingSessionParam)
        .then(res => {
          const tid = res.data.task_id
          setEditTaskId(tid)
          activeTaskRef.current = tid
          setEditing('Mesures')
        })
        .catch(e => setFeedback({ type: 'err', text: motiuOpenTask(e, t) }))
    }
  }, [loading, activeTab, fittingSessionParam, taskParam, id, t])

  // Q4 (06/08) — «GRAVAR I TORNAR» TORNA D'ON VENIES: el tab Mesures del model.
  //
  // Anava a la fulla de la convocatòria (o a la llista), i la fulla, en veure la sessió ja
  // segellada, reenviava a la FITXA del fitting (`FittingConvocatoriaSheet:71`): es gravava des
  // de Mesures i s'aterrava en una acta de només lectura d'una altra pantalla. La fitxa és
  // consultable des de Repàs de fittings; no és la sortida d'aquest gest.
  //
  // Se surt pel camí de sortida de sempre (`exitEdit`), que és qui pregunta al servidor si la
  // tasca segueix viva i, si cal, obre el modal d'acabar/pausar. `netejaEdicio` treu
  // `fitting_session` de la URL (és un `PARAMS_DE_TREBALL`) i amb això la superfície torna sola
  // a la consulta de Mesures. El tab de retorn es fixa aquí perquè les entrades per URL (fulla
  // de convocatòria, WorkPlan) no passen per `obreDeDebo` i no en tenen cap d'apuntat.
  const onSessionSaved = useCallback(() => {
    tabDeRetornRef.current = 'Mesures'
    exitEdit()
  }, [exitEdit])

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
  const [propagarEnCua, setPropagarEnCua] = useState(false)
  const [usantJoc, setUsantJoc] = useState(false)
  // D1 + D-31.4 — el mateix component de confirmació que fa servir el wizard (v. `onUsarJoc`).
  const { executa: executaAmbConfirmacio, dialeg: dialegRuleset } = useConfirmacioRuleset()
  // P11 — l'estat que el pas de Graduació necessita i que abans posava el wizard.
  // `jocVist` és el joc seleccionat en aquesta obertura, perquè el picker el marqui abans que
  // `reloadModel` torni. Es neteja en tancar: el contenidor no recorda tries que no s'han
  // arribat a aplicar. (`fitTriat` se'n va amb el pas de fit del panell antic.)
  const [jocVist, setJocVist] = useState(null)

  // El FIT VIGENT i el «què falta de les talles» se'n van amb el `GraduacioPanel`: eren les
  // seves dues portes (triar fit abans del picker · no ensenyar res sense sistema de talles), i
  // el contenidor central no en té cap. Si algun dia tornen, tornen amb qui les demana.

  // El CONTENIDOR de tria de joc (P0.5a). Des de P0.5d ja no és la porta d'entrada a graduar:
  // s'obre DES DE la superfície de graduació, quan el model no té joc o se'n vol canviar.
  const obreGraduacio = useCallback(() => setGraduacioObert(true), [])

  // Porta a la SUPERFÍCIE de graduació sense passar pel circuit de tasca. La fan servir els
  // camins que ja hi són a dins (l'entrada manual del contenidor) o els que hi han d'anar a
  // parar sense obrir feina nova (propagar sense regles).
  const vesAGraduacio = useCallback(() => {
    setActiveTab('Mesures')
    setSp(prev => {
      const net = new URLSearchParams(prev)
      net.set('mode', 'graduacio')
      return net
    }, { replace: true })
  }, [setSp])

  // Rellegir la superfície quan el joc canvia sota seu: assignar-ne un altre canvia TOTES les
  // files resoltes, i la pantalla ha de tornar a demanar la taula. Es fa amb `key` (remuntatge)
  // i no amb un efecte perquè també ha de descartar les edicions a mig fer: amb un joc nou al
  // damunt, el que s'havia teclejat contra l'anterior ja no vol dir el mateix.
  const [graduacioKey, setGraduacioKey] = useState(0)

  // Tancar SENSE triar. Si hi havia una propagació en cua, s'avorta sencera: cap estat a
  // mitges. Tancar no ha escrit res —«Usar aquest joc» és l'únic que escriu—, o sigui que
  // cancel·lar és, literalment, no haver passat per aquí.
  const cancelaGraduacio = useCallback(() => {
    setGraduacioObert(false)
    setPropagarEnCua(false)
    setJocVist(null)
  }, [])

  // ENTRADA MANUAL (P0.5a) — graduar aquest model a mà, sense joc de regles.
  //
  // P0.5d — JA NO S'AMAGA. Abans encenia una bandera de sessió (`graduacioManual`) que només
  // servia per fer sortir quatre columnes buides a Definició POM, i que un F5 perdia perquè al
  // domini no hi ha cap camp «aquest model es gradua a mà». Ara no li cal cap bandera: porta a
  // la superfície de graduació SENSE joc assignat, on totes les files ja són editables des de
  // zero. Que no hi hagi joc és exactament el que vol dir «a mà», i això sí que sobreviu l'F5.
  //
  // Segueix sense escriure res, i segueix sent deliberat: un model amb REGLES RESIDENTS i sense
  // ruleset ja ÉS un model graduat a mà. L'estat es manté sol en escriure la primera regla.
  const onGraduacioManual = useCallback(() => {
    setGraduacioObert(false)
    vesAGraduacio()
  }, [vesAGraduacio])

  // MIRA ABANS d'executar. Dues preguntes, en aquest ordre:
  //   1. Hi ha REGLA? Sense regla no es propaga MAI. Si no n'hi ha, el gest no mor amb un
  //      toast: queda EN CUA i s'obre el pas de Graduació. El backend ja barra el pas; el que
  //      guanya aquí és el camí bo en lloc del 400 mut.
  //   2. Hi ha propagació prèvia? → avís de 2 passos (pas 1 segons gravetat; pas 2 universal).
  // ④ PROPAGAR I LA TASCA — quin criteri hi ha, i quin s'aplica.
  //
  // EL QUE HI HA AL CIRCUIT: ni `onPropagarClick` ni `execPropagar` han cridat mai `openTask`.
  // Propagar només crida `generarGrading` i, en sortir bé, fa `setActiveTab('Escalat')`. Aquest
  // canvi de tab dispara el salt de superfície (`saltDeSuperficie`, D-1), i com que
  // `CODE_PER_TAB.Escalat === 'grading'`, la sessió SALTA a la tasca de graduació **si ja
  // existeix i és lliure** — en silenci, sense crear-ne cap.
  //
  // EL QUE S'APLICA: es manté. Propagar és un acte DINS de la graduació, no una feina a part, i
  // ara el camí natural el precedeix —②, que sí que obre la tasca de graduació. Si el tècnic
  // propaga sense haver graduat abans, el salt de D-1 el posa sota la tasca de graduació vigent
  // si n'hi ha, i si no n'hi ha cap no s'inventa feina.
  //
  // 🚩 A CONFIRMAR AMB L'AGUS: no hi ha cap decisió escrita que digui què ha de fer propagar amb
  // el temps. Això és el criteri que el circuit ja practicava, no una decisió presa aquí.
  const onPropagarClick = () => {
    if (propagating) return
    models.gradingStatus(parseInt(id))
      .then(res => {
        const st = res.data
        // P0.5d — sense regla no es propaga, i el gest no mor amb un toast: queda EN CUA i porta
        // a GRADUAR. Ara això vol dir la superfície (i, a sobre, el contenidor: sense regles el
        // primer que cal decidir és si es gradua per joc o a mà), no només el contenidor.
        if (!st.te_regles) { setPropagarEnCua(true); vesAGraduacio(); setGraduacioObert(true); return }
        if (!st.te_dades_propagades) execPropagar(false)   // llenç ja net → directe
        else { setPropStatus(st); setPropStep(1) }
      })
      .catch(() => setFeedback({ type: 'err', text: t('grading_propagate.err') }))
  }

  // «USAR AQUEST JOC» al pas 4 → el mecanisme VIGENT del wizard (`update-step2`: valida D1 i
  // materialitza les regles al model). Cap mecànica nova.
  //
  // En sortir bé es tanca el calaix i es rellegeix la taula: les columnes de Regla, que ja es
  // veien BUIDES a sota, queden PLENES. I si el gest original era propagar, es reprèn sol —
  // passant altre cop per `onPropagarClick`, no per `execPropagar`, perquè el model pot tenir
  // propagació prèvia i saltar-se l'avís de 2 passos seria colar una substitució.
  //
  // Els 409 d'assignació són AVISOS CONSCIENTS, no errors: aplicar la forma d'un altre client
  // (D1) i migrar un model al catàleg esborrant-ne les regles pròpies (D-31.4) són tots dos
  // fluxos de taller legítims. Es demanen i es reintenten amb el consentiment, pel MATEIX
  // component que fa servir el wizard: `useConfirmacioRuleset` porta el diàleg i el reintent amb
  // el flag que toca —un per cas, mai els dos alhora.
  const onUsarJoc = useCallback((rs) => {
    if (usantJoc) return
    setUsantJoc(true)
    executaAmbConfirmacio(
      flags => models.updateStep2(parseInt(id), { grading_rule_set_id: rs.id, ...flags }))
      .then(() => {
        setGraduacioObert(false)
        reloadModel(); reloadTaula()
        // P0.5d — el joc nou canvia totes les files resoltes de la superfície que hi ha a sota:
        // se li demana la taula un altre cop (v. `graduacioKey`).
        setGraduacioKey(k => k + 1)
        if (propagarEnCua) { setPropagarEnCua(false); onPropagarClick() }
      })
      .catch(e => setFeedback({
        type: 'err',
        text: e?.response?.data?.message || e?.response?.data?.error || t('graduacio.usar_err'),
      }))
      .finally(() => setUsantJoc(false))
  }, [id, usantJoc, propagarEnCua, reloadModel, reloadTaula, t])   // eslint-disable-line react-hooks/exhaustive-deps

  // P11: `acabaGraduacio` se'n va amb el wizard. Era el seu «onSaved» —desar el MODEL sencer des
  // del calaix—, i el calaix ja no desa cap model: l'únic acte que escriu és «Usar aquest joc»,
  // que ja tanca i rellegeix dins de `onUsarJoc`.
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

  // F2.1 — les quatre sortides del modal. `consultar` és la que no toca res: ni rellotge, ni
  // assignació, ni feina nova. Les altres tres escriuen, i cada una diu a la seva nota què fa.
  //
  // ÚLTIM HOOK del component, i per això mateix ha d'anar ABANS del retorn de `loading`: declarat
  // a sota, el primer render (loading=true) no el cridava i el segon sí → React #310 «Rendered
  // more hooks than during the previous render» a cada càrrega del full. Cap hook per sota d'aquí.
  const accioDialeg = useCallback((accio) => {
    const d = dialeg
    setDialeg(null)
    if (!d) return
    // CONSULTAR: el tab i prou. Sense `enterEdit` no hi ha `open-task`, i sense open-task no
    // hi ha ni rellotge ni reassignació — que és exactament el que promet la nota del botó.
    // `netejaEdicio` i no dos `set` solts: qui tria CONSULTAR pot haver arribat per `?mode=entry`
    // (el menú «Definició POM»), i deixar-hi el paràmetre faria que l'F5 el tornés a ficar a
    // editar just després d'haver dit que no hi volia entrar.
    if (accio === 'consultar') { netejaEdicio(); setActiveTab(d.tab); return }
    if (accio === 'treballar') {
      if (d.fitxerId) { obreFitxa(d.fitxerId); return }   // la fitxa té la seva pròpia navegació
      obreDeDebo(d.tab, d.code); return
    }
    // `ronda` i `correccio` van per la MATEIXA porta: una correcció és una volta d'una sola
    // tasca. El backend hi posa el motiu i la genealogia (mare) sense que la UI ho hagi de saber.
    const motiu = accio === 'ronda' ? 'nova_mostra' : 'correccio'
    setOpeningTask(true)
    models.obrirRonda(parseInt(id), { motiu, codes: [d.code] })
      .then(() => {
        reloadTasks(); reloadModel()
        if (d.fitxerId) obreFitxa(d.fitxerId)
        else obreDeDebo(d.tab, d.code)
      })
      .catch(e => setFeedback({
        type: 'err',
        text: e?.response?.data?.error || t('obrir_tasca.ronda_error'),
      }))
      .finally(() => setOpeningTask(false))
  }, [dialeg, netejaEdicio, obreDeDebo, obreFitxa, id, reloadTasks, reloadModel, t])

  // ——— A partir d'aquí, RETORNS. Cap hook per sota. ———
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
      {acabant && (
        <ModalAcabarTasca
          taskId={acabant.taskId}
          nomTasca={acabant.tasca?.task_type_name || ''}
          minutsSessio={minutsDeSessio(acabant.tasca)}
          minutsTotal={acabant.tasca?.temps_consumit_min ?? 0}
          onFet={acabatOPausat}
          onCancel={() => setAcabant(null)} />
      )}
      <ObrirTascaDialog
        cara={dialeg?.cara}
        tasca={dialeg?.tasca}
        rondaOberta={model?.ronda_oberta}
        onAccio={accioDialeg}
        onCancel={() => setDialeg(null)}
      />
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
            onClick={() => triaTab(tab)}
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
            {/* WIZARD-COMPLET C.3 — ruleset en LECTURA enriquida; el canvi viu al wizard (pas 4). */}
            {model && <RuleSetCard model={model} />}
          </div>
        )}
        {activeTab === 'Mesures' && (
          /* P0.5d — LA GRADUACIÓ, PRIMER DE TOT. És una superfície pròpia i pren el tab sencer,
             igual que Definició POM: qui ve a graduar no ve a mirar la taula de mesures amb un
             calaix a sobre. Va davant de `mesuresEntry` perquè les dues són superfícies de
             treball i no poden conviure — `?mode=` només en pot dir una. */
          graduacioMode ? (
            <GraduacioSuperficie
              key={graduacioKey}
              model={model}
              onTancar={exitEdit}
              onObrirContenidor={obreGraduacio}
              onGravat={() => { reloadTaula(); reloadModel() }}
            />
          ) : mesuresEntry && editing !== 'Mesures' ? (
            <MeasuresEntryPanel model={model} entryMode={mesuresEntry} intent={mesuresIntent}
              onMaterialized={() => { exitEdit(); reloadTaula(); reloadModel() }}
              onGraduacio={obreGraduacio}
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
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" disabled={openingTask}
                  onClick={() => enterEdit('Mesures', 'pom')}
                  style={{ ...btnSecondary, borderColor: 'var(--gold)', color: 'var(--gold)',
                           opacity: openingTask ? 0.6 : 1, cursor: openingTask ? 'default' : 'pointer' }}>
                  <i className="ti ti-ruler-2" style={{ fontSize: 14 }} />
                  {t('model_sheet.start_pom')}
                </button>
                {/* Sprint B — la SEGONA superfície de buit del sistema (l'altra és el `selector`
                    de MeasuresEntryPanel). Oferir la còpia només a una deixava mig camí. */}
                <button type="button" disabled={openingTask}
                  onClick={() => enterEdit('Mesures', 'pom', 'copy')}
                  style={{ ...btnSecondary, opacity: openingTask ? 0.6 : 1,
                           cursor: openingTask ? 'default' : 'pointer' }}>
                  <i className="ti ti-copy" style={{ fontSize: 14 }} />
                  {t('measures_entry.copy_title')}
                </button>
              </div>
            </div>
          ) : (
	          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                          marginBottom: 10, gap: 12 }}>
              {editing === 'Mesures' ? (
                <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                  {t('model_sheet.measures_editing')}
                </span>
              ) : (
                // Commutador de subvista (consulta): taula del model ↔ repàs dels fittings fets.
                <div style={{ display: 'flex', gap: 6 }}>
                  {[['taula', 'model_sheet.measures_view_table', 'ti-table'],
                    ['repas', 'model_sheet.measures_view_repas', 'ti-history'],
                    ['comprovacio', 'comprovacio.titol', 'ti-checkup']].map(([key, label, icon]) => (
                    <button key={key} type="button" onClick={() => setMesuresView(key)}
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: 6,
                        padding: '4px 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
                        background: mesuresView === key ? 'var(--gold)' : 'var(--bg-muted)',
                        color: mesuresView === key ? 'var(--white)' : 'var(--text-muted)',
                        fontSize: 'var(--fs-body)', fontWeight: mesuresView === key ? 500 : 400,
                      }}>
                      <i className={`ti ${icon}`} aria-hidden="true" style={{ fontSize: 14 }} />
                      {t(label)}
                    </button>
                  ))}
                </div>
              )}
              {/* LES QUATRE ACCIONS DEL TAB, EN ORDRE DE FLUX DE TREBALL (Agus, 06/08):
                  ① Editar POM · ② Graduació · ③ Mesurar prenda · ④ Propagar.
                  Primer es defineix QUÈ es mesura, després COM s'escala, després es MESURA la
                  peça, i al final es PROPAGA. L'ordre és el que fa el tècnic, no l'ordre en què
                  els botons van néixer.

                  El tab és de CONSULTA i aquests quatre són les vies d'entrada a les seves
                  superfícies. Cadascun passa pel circuit de tasca existent (`enterEdit` →
                  `caraObrirTasca` → `obreDeDebo`/modal de tres cares): obre-si-cal, modal NOMÉS
                  si hi ha conflicte, i el rellotge corrent. Cap mecànica nova. */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {/* Commuta consulta↔edició DINS la tab (no navega): manté tot el context. */}
                {editing === 'Mesures' ? (
                  <button type="button" onClick={exitEdit} style={btnAccio()}>
                    <i className="ti ti-eye" style={{ fontSize: 14 }} />
                    {t('model_sheet.back_to_consult')}
                  </button>
                ) : (
                  /* ① EDITAR POM — Definició de POMs i talla base. «Importar taula» hi viu a
                     dins com a via d'entrada (`MeasuresEntryPanel`), no aquí. */
                  <button type="button" disabled={openingTask}
                    onClick={() => enterEdit('Mesures', 'pom')} style={btnAccio(openingTask)}>
                    <i className="ti ti-ruler-2" style={{ fontSize: 14 }} />
                    {t('model_sheet.edit_pom')}
                  </button>
                )}
                {/* ② GRADUACIÓ — el calaix lateral sobre la taula (P11). Ara ENTRA PEL CIRCUIT:
                    `enterEdit('Mesures','grading')` obre la tasca de graduació i el seu rellotge,
                    i `obreDeDebo` reconeix la parella (Mesures + grading) per obrir el calaix en
                    comptes de saltar al tab Escalat. Abans cridava `obreGraduacio` directament i
                    es graduava SENSE tasca ni temps.
                    Quan la pantalla nova de P0.5d existeixi, el que canvia és on porta —no com
                    s'hi entra. */}
                <button type="button" disabled={openingTask}
                  onClick={() => enterEdit('Mesures', 'grading')} style={btnAccio(openingTask)}>
                  <i className="ti ti-chart-arrows-vertical" style={{ fontSize: 14 }} />
                  {t('graduacio.button')}
                </button>
                {/* ③ MESURAR PRENDA — NOU. La superfície ja existia (`CheckMeasureEditor` en mode
                    presa, maqueta v3) però només s'hi arribava per URL des del WorkPlan o d'un
                    redirect de fitting: des del full del model no hi havia porta. El codi de
                    tasca és `size_check`, i `obreDeDebo` ja el porta a `editing='Mesures'`, que
                    és exactament la presa. Si el model ve amb `?fitting_session=`, la sessió ja
                    resolta mana i la presa s'hi lliga sola (font `fitting`). */}
                <button type="button" disabled={openingTask}
                  onClick={() => enterEdit('Mesures', 'size_check')} style={btnAccio(openingTask)}>
                  <i className="ti ti-ruler-measure" style={{ fontSize: 14 }} />
                  {t('presa.titol')}
                </button>
                {/* ④ PROPAGAR a grading (origen): inicia fase nova sobre llenç net i porta a
                    Escalat. Mira abans i adverteix (2 passos) si ja hi ha propagació.
                    NO OBRE TASCA PRÒPIA, i és deliberat: v. la nota de `onPropagarClick`. */}
                <button type="button" disabled={openingTask || propagating}
                  onClick={onPropagarClick} style={btnAccio(openingTask || propagating)}>
                  <i className="ti ti-git-branch" style={{ fontSize: 14 }} />
                  {propagating ? t('grading_propagate.running') : t('grading_propagate.button')}
                </button>
              </div>
            </div>
            {editing === 'Mesures' ? (
              // Sprint Y — amb sessió de fitting resolta: font FITTING + lockRules (règim/deltes/nom
              // read-only, preses editables). Sense sessió: font check per defecte, comportament idèntic.
              <CheckMeasureEditor model={model} readOnly={false} taskId={editTaskId}
                source={fittingSession ? fittingSource : null}
                sourceCtx={fittingSession ? { fittingSession } : null}
                lockRules={!!fittingSession}
                onSessionSaved={fittingSession ? onSessionSaved : null}
                onFeedback={fb => setFeedback(fb)} onResolved={exitEdit} onBack={exitEdit} />
            ) : mesuresView === 'repas' ? (
              <FittingRepasPanel model={model} />
            ) : mesuresView === 'comprovacio' ? (
              // CONSULTA PURA: l'enllaç «veure →» no escriu res, porta a la taula (i a l'edició
              // només si el tècnic hi entra pel seu gest). Comprovar i entrar són dos moments.
              <ComprovacioPanel model={model} onVeureFila={() => setMesuresView('taula')} />
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
        {/* P11 — EL CALAIX DE GRADUACIÓ ÉS EL PAS DE GRADUACIÓ, ja no el wizard sencer.
            Fins ara aquí s'hi encastava `ModelWizard` obert al pas 4: quatre passos navegables,
            capçalera de wizard i botons de desar el MODEL, per a un gest que és triar un joc de
            regles. `GraduacioPanel` ja existia extret precisament per a això (`6af2f6f2`, i la
            seva pròpia capçalera ho diu: «el mateix pas per als DOS llocs que l'ensenyen»);
            el que faltava era que aquest costat el cridés.

            El que NO canvia: l'escriptura segueix sent `onUsarJoc` (`update-step2`), amb el seu
            409 de client aliè i la represa de la propagació en cua. Cap mecànica nova.

            L'ATZUCAC TÉ SORTIDA IGUALMENT. L'argument del wizard era «si falta la construcció,
            l'usuari va al pas 2». El panell ja diu QUIN eix falta (`grading_missing_axes`) i
            aquí s'hi posa la porta que hi porta: «editar el model». Es diu el problema i s'ofereix
            el camí, en comptes d'obligar a travessar tres passos que no es volien tocar.

            LATERAL i sense enfosquir: la taula de Mesures ha de quedar VISIBLE i llegible a
            sota mentre es decideix. Qui vulgui entrar la graduació a mà tanca el calaix i es
            troba les columnes de Regla buides, allà mateix, per treballar-les. */}
        {/* P0.5a — EL CONTENIDOR CENTRAL. Era un calaix lateral amb el pas 4 del wizard
            (`GraduacioPanel`), i aquell pas porta les portes del wizard: sense `size_system` no
            ensenya res, demana un FIT abans d'obrir el picker, i el picker corre en mode
            ESTRICTE. Amb un model real al davant això acabava en «falta la construcció» i una
            llista buida — el tècnic veia que li faltava alguna cosa i no podia triar RES.
            Ara la pertinença ORDENA i no exclou, i el gest central és el que és: triar un joc.
            El `GraduacioPanel` NO es toca: segueix sent el pas 4 del wizard. */}
        {graduacioObert && model && (
          <div
            role="dialog" aria-modal="true" aria-label={t('graduacio.button')}
            onMouseDown={(e) => { if (e.target === e.currentTarget) cancelaGraduacio() }}
            style={{ position: 'fixed', inset: 0, zIndex: 60, display: 'flex',
                     alignItems: 'flex-start', justifyContent: 'center',
                     background: 'rgba(0,0,0,0.28)', padding: '4vh 16px', overflowY: 'auto' }}>
            <div style={{ width: 'min(720px, 100%)', background: 'var(--white)',
                          borderRadius: 12, padding: '1.25rem 1.5rem 1.5rem',
                          boxShadow: '0 12px 40px rgba(0,0,0,0.2)',
                          border: '0.5px solid var(--border)' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between',
                            gap: 12, marginBottom: 14 }}>
                <h2 style={{ margin: 0, fontSize: 'var(--fs-h2)', fontWeight: 500 }}>
                  {t('graduacio.button')}
                </h2>
                <button type="button" onClick={() => navigate(`/models/${id}/editar`)}
                  style={{ ...btnSecondary, fontSize: 'var(--fs-body)' }}>
                  <i className="ti ti-edit" style={{ fontSize: 14 }} aria-hidden="true" />
                  {t('graduacio.editar_model')}
                </button>
              </div>
              {propagarEnCua && (
                <p style={{ margin: '0 0 12px', padding: '8px 12px', borderRadius: 6,
                            border: '0.5px solid var(--gold)', background: 'var(--gold-pale)',
                            fontSize: 'var(--fs-body)' }}>
                  {t('graduacio.cua_propagar')}
                </p>
              )}
              <GraduacioContenidor
                model={model}
                gradingRuleSetId={jocVist ?? model.grading_rule_set ?? null}
                onUsar={(rs) => { setJocVist(rs.id); onUsarJoc(rs) }}
                onManual={onGraduacioManual}
                onTanca={cancelaGraduacio}
              />
            </div>
          </div>
        )}
        {propStatus && propStep === 1 && (
          <Modal
            title={t('grading_propagate.warn_title')}
            /* G6-B2: si la versió segellada ja ha quedat ENRERE (la base ha canviat sota el
               segell), l'avís ho diu aquí — que és on es decideix propagar. Superar un segell que
               ja no diu la veritat no és el mateix acte que superar-ne un de fresc, i qui ho
               decideix ho ha de saber ABANS. No canvia què es pot fer: canvia què se sap. */
            subtitle={propStatus.segellada
              ? (propStatus.estalitud?.avisa
                ? t('grading_propagate.warn_sealed_stale', {
                  version: propStatus.version_number,
                  n: propStatus.estalitud.canvis_base,
                })
                : t('grading_propagate.warn_sealed', { version: propStatus.version_number }))
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
        {activeTab === 'Patró' && <PatternTab modelId={parseInt(id)} />}
        {activeTab === 'Fitxers' && <TabFiles modelId={parseInt(id)} onEditFitxa={obreFitxa} />}
        {activeTab === 'Fitxa tècnica' && <TechSheetTab modelId={id} navigate={navigate} onModificar={obreFitxa} />}
        {activeTab === 'Anàlisi IA' && <TabAIAnalysis modelId={parseInt(id)} />}
        {activeTab === "Registre d'activitat" && <RegistreActivitatTab modelId={id} />}
      </div>

      {/* 🔴 EL DIÀLEG DELS AVISOS CONSCIENTS (D1 · client aliè · D-31.4 · esborrat de regles
          residents) ES PINTA AQUÍ, que és on viu el `useConfirmacioRuleset` que el crea.
          Estava escrit al final de `TabAIAnalysis` —un altre component, 1.400 línies més avall—,
          on `dialegRuleset` ni tan sols és a l'abast. O sigui que el guard existia, el backend
          tornava el seu 409 i la confirmació no arribava MAI a la pantalla: assignar un joc que
          havia d'esborrar regles pròpies es quedava en un botó que no responia. Trobat mirant
          per què eslint deia alhora «assignada i no feta servir» (:518) i «no definida» (:2418). */}
      {dialegRuleset}
    </div>
  )
}

// Pestanya "Fitxa tècnica": LA CASA de les fitxes .ftt del model.
//
// U1 — un model pot tenir N fitxes (multi-peça: DRESS + KNICKERS + HEADBAND). Fins ara el tab
// només ensenyava la primera de la llista i les germanes eren invisibles des d'aquí: existien a
// la BD i al selector de /fitxa, però no hi havia cap superfície on veure-les totes. Ara el tab
// les llista totes i cada fila apunta al SEU document (/models/:id/ftt/:fitxerId), no al
// resolver: obrir una fitxa concreta no ha de tornar a passar per una tria.
//
// Consulta des del Model obre sense task_id → mode consulta (l'editor desa igual, però no
// imputa temps). L'edició registrada es fa des del Kanban, que passa ?task_id=...
function TechSheetTab({ modelId, navigate, onModificar }) {
  const { t, i18n } = useTranslation()
  // Cutover .ftt (F8): la fitxa és un ModelFitxer tipus TECHSHEET (no el TechSheet O2O).
  // `null` = encara carregant; `[]` = el model no en té cap.
  const [fitxes, setFitxes] = useState(null)
  const [nova, setNova] = useState(null)      // null = modal tancat | { nom, descripcio }
  const [creant, setCreant] = useState(false)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let cancelled = false
    modelFitxers.fitxesTecniques(modelId)
      .then(({ data }) => { if (!cancelled) setFitxes(data?.results || data || []) })
      .catch(() => { if (!cancelled) setFitxes([]) })
    return () => { cancelled = true }
  }, [modelId])

  // U2 — la fitxa nova neix amb NOM: és l'únic que distingeix les germanes d'un multi-peça.
  // Es crea en blanc i s'entra directament a l'editor; qui vulgui partir d'una plantilla del
  // tenant té aquell camí a "Crear fitxa tècnica" (el resolver), que és qui les ofereix.
  const crear = () => {
    const nom = (nova?.nom || '').trim()
    if (!nom || creant) return
    setCreant(true); setErr(null)
    modelFitxers.crearFitxa(modelId, { nom, descripcio: (nova.descripcio || '').trim() || undefined })
      // F2.2 — crear una fitxa ÉS treballar-hi: s'obre amb sessió, com «Modificar». Si no hi ha
      // porta (el tab s'usés sense el pare), la navegació de consulta és el fallback honest.
      .then(({ data }) => (onModificar
        ? onModificar(data.id)
        : navigate(`/models/${modelId}/ftt/${data.id}?mode=consulta`)))
      .catch(() => { setErr(t('tech_sheet.tab_new_err')); setCreant(false) })
  }

  if (fitxes === null) return (
    <div style={{ padding: '24px', color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
      {t('model_sheet.loading')}
    </div>
  )

  // Estil compartit per botons outline discrets
  const btnOutline = {
    background: 'transparent',
    border: '1px solid var(--border)',
    color: 'var(--text-main)',
    fontSize: 'var(--fs-body)',
    padding: '5px 12px',
    borderRadius: 6,
    cursor: 'pointer',
    display: 'flex', alignItems: 'center', gap: 5,
  }

  const dataDe = (f) => (f.data_pujada
    ? new Date(f.data_pujada).toLocaleDateString(i18n.language || 'ca',
        { day: '2-digit', month: '2-digit', year: 'numeric' })
    : '—')

  const modal = nova && (
    <Modal
      title={t('tech_sheet.tab_new_title')}
      subtitle={t('tech_sheet.tab_new_hint')}
      confirmLabel={creant ? t('model_sheet.loading') : t('app.create')}
      cancelLabel={t('app.cancel')}
      confirmDisabled={creant || !(nova.nom || '').trim()}
      onCancel={() => { setNova(null); setErr(null) }}
      onConfirm={crear}>
      <label style={{ display: 'block', fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 4 }}>
        {t('tech_sheet.tab_new_name')}
      </label>
      <input autoFocus value={nova.nom} onChange={e => setNova({ ...nova, nom: e.target.value })}
        placeholder={t('tech_sheet.new_doc_name_placeholder')}
        style={{ width: '100%', fontSize: 'var(--fs-body)', padding: '8px 10px', marginBottom: 12,
                 border: '1px solid var(--border)', borderRadius: 6, background: 'var(--white)', color: 'var(--text-main)' }} />
      <label style={{ display: 'block', fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 4 }}>
        {t('tech_sheet.tab_new_desc')}
      </label>
      <input value={nova.descripcio} onChange={e => setNova({ ...nova, descripcio: e.target.value })}
        style={{ width: '100%', fontSize: 'var(--fs-body)', padding: '8px 10px',
                 border: '1px solid var(--border)', borderRadius: 6, background: 'var(--white)', color: 'var(--text-main)' }} />
      {err && <p style={{ marginTop: 10, fontSize: 'var(--fs-body)', color: 'var(--err)' }}>{err}</p>}
    </Modal>
  )

  // --- CAP FITXA --- el buit de sempre; "Crear fitxa tècnica" segueix passant pel resolver,
  // que és qui ofereix les plantilles del tenant quan n'hi ha.
  if (!fitxes.length) {
    return (
      <div style={{ padding: '24px' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)', marginBottom: '16px' }}>
          {t('tech_sheet.tab_empty')}
        </p>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => navigate(`/models/${modelId}/fitxa`)}
            style={{ ...btnOutline, borderColor: 'var(--gold)', color: 'var(--gold)' }}>
            <i className="ti ti-file-plus" aria-hidden="true" style={{ fontSize: 14 }} />
            {t('tech_sheet.tab_create')}
          </button>
          <button onClick={() => setNova({ nom: '', descripcio: '' })} style={btnOutline}>
            <i className="ti ti-plus" aria-hidden="true" style={{ fontSize: 14 }} />
            {t('tech_sheet.tab_new')}
          </button>
        </div>
        {modal}
      </div>
    )
  }

  // --- N FITXES (amb 1, la fila única de sempre) ---
  return (
    <div>
      {/* Capçalera del tab: recompte + la porta de la fitxa nova. */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px', borderBottom: '1px solid var(--border)', background: 'var(--bg-muted)',
      }}>
        <span style={{ fontSize: 'var(--fs-label)', fontFamily: FILES_MONO,
                       color: 'var(--text-muted)', textTransform: 'uppercase' }}>
          {t('tech_sheet.tab_count', { n: fitxes.length })}
        </span>
        <button onClick={() => setNova({ nom: '', descripcio: '' })}
          style={{ ...btnOutline, borderColor: 'var(--gold)', color: 'var(--gold)' }}>
          <i className="ti ti-plus" aria-hidden="true" style={{ fontSize: 14 }} />
          {t('tech_sheet.tab_new')}
        </button>
      </div>

      {/* Una fila per fitxa. Els dos botons apunten al document CONCRET. */}
      {fitxes.map(f => (
        <div key={f.id} style={{
          display: 'flex', alignItems: 'center', gap: 16,
          padding: '12px 16px', borderBottom: '1px solid var(--border)',
        }}>
          <i className="ti ti-file-text" aria-hidden="true"
             style={{ fontSize: 16, color: 'var(--text-muted)', flexShrink: 0 }} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)',
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                 title={f.nom_fitxer}>
              {f.nom_fitxer}
            </div>
            {f.descripcio && (
              <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)',
                            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {f.descripcio}
              </div>
            )}
          </div>
          <span style={{ width: 44, flexShrink: 0, textAlign: 'right', fontSize: 'var(--fs-label)',
                         fontFamily: FILES_MONO, color: 'var(--text-muted)' }}>v{f.versio}</span>
          <span style={{ width: 110, flexShrink: 0, fontSize: 'var(--fs-label)',
                         fontFamily: FILES_MONO, color: 'var(--text-muted)' }}
                title={t('tech_sheet.tab_updated')}>{dataDe(f)}</span>
          <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
            {/* F2.2 · D-1 — fins avui aquests dos botons feien EXACTAMENT el mateix `navigate`,
                i cap dels dos comptava temps. Ara diuen coses diferents perquè fan coses
                diferents: PREVISUALITZAR obre en lectura (sense `task_id` l'editor no demana
                lock i l'autosave no dispara, o sigui que no hi ha ni batec ni sessió) i
                MODIFICAR obre sessió sobre la tasca vigent, passant pel modal si cal.
                La consulta és la sortida digna del superior que només ve a mirar: per això és
                visible i no està amagada darrere d'un menú. */}
            <button onClick={() => navigate(`/models/${modelId}/ftt/${f.id}?mode=consulta`)}
                    style={btnOutline} title={t('tech_sheet.tab_preview_nota')}>
              <i className="ti ti-eye" style={{ marginRight: 6 }} />
              {t('tech_sheet.tab_preview')}
            </button>
            <button onClick={() => onModificar?.(f.id)} style={btnOutline}
                    title={t('tech_sheet.tab_edit_nota')}>
              <i className="ti ti-pencil" style={{ marginRight: 6 }} />
              {t('tech_sheet.tab_edit')}
            </button>
          </div>
        </div>
      ))}

      {/* Cos: resum de l'estat */}
      <div style={{ padding: '16px', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
        <p>{t('tech_sheet.tab_hint')}</p>
      </div>

      {modal}
    </div>
  )
}

function ModelSheetHeader({ model, onDelete, onFeedback, onChanged }) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const isBrand = useAuthStore(s => s.tenant?.tipologia === 'marca')
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
        {/* F2.7 — l'avís de lliurable va a la capçalera, al costat de la identitat del model:
            el PM que obre la fitxa ho ha de veure sense buscar-ho. */}
        <BadgeLliurable rondes={model.lliurable_ronda_n} />
        {model.nom_prenda && (
          <>
            <span style={{ color: 'var(--border)' }}>·</span>
            <span style={{ fontSize: 'var(--fs-h3)', fontWeight: 500,
                           color: 'var(--text-main)' }}>
              {model.nom_prenda}
            </span>
          </>
        )}
        {/* SET-1 · A4 — el conjunt a la capçalera: quina peça és, de quantes, i com anar a les
            germanes. Les germanes vénen niuades al serializer del detall (`garment_set.peces`):
            un fetch de menys, i la llista ja s'ha de travessar per pintar el badge. */}
        {model.garment_set && (
          <>
            <span style={{ color: 'var(--border)' }}>·</span>
            <span title={model.garment_set.nom_comercial || ''} style={{
              fontSize: 'var(--fs-caption)', padding: '2px 8px', borderRadius: 5,
              background: 'var(--gold-pale)', color: 'var(--gold)',
              border: '0.5px solid var(--gold)', fontWeight: 600,
            }}>
              {t('model_sheet.set_badge', {
                n: model.piece_number ?? '?', total: model.garment_set.num_pieces,
                codi: model.garment_set.codi_base,
              })}
            </span>
            {(model.garment_set.peces || [])
              .filter(p => p.id !== model.id)
              .map(p => (
                <button key={p.id} type="button" onClick={() => navigate(`/models/${p.id}`)}
                  title={p.codi_intern}
                  style={{ background: 'none', border: '0.5px solid var(--border)',
                           borderRadius: 5, padding: '2px 8px', cursor: 'pointer',
                           fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
                  {p.nom_prenda || `#${p.piece_number}`}
                </button>
              ))}
          </>
        )}
        <span style={{
          fontSize: 'var(--fs-body)', padding: '2px 8px', borderRadius: 20, fontWeight: 600,
          background: 'var(--gold)', color: 'var(--white)',
        }} title={t('model_sheet.phase')}>
          {model.fase_actual ? t(`model_sheet.dashboard.phase.${model.fase_actual}`, model.fase_actual) : '—'}
        </span>
        {/* P7 — el RECURS assignat. Només en una MARCA (és qui assigna) i només si n'hi ha un:
            un model sense recurs no viatja enlloc, i dir-ho amb un '—' aquí seria soroll a la
            capçalera. Qui l'ha de veure buit és la llista, que compara models entre ells. */}
        {isBrand && model.studio_assignat && (
          <span style={{
            fontSize: 'var(--fs-body)', padding: '2px 8px', borderRadius: 20, fontWeight: 600,
            fontFamily: 'IBM Plex Mono, monospace',
            background: 'var(--gold-pale)', color: 'var(--gold)', border: '0.5px solid var(--gold)',
          }} title={t('model_sheet.assign_resource')}>
            <i className="ti ti-affiliate" style={{ marginRight: 4 }} aria-hidden="true" />
            {model.studio_assignat}
          </span>
        )}
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
    // El badge compta NOMÉS els oberts (resoldre'n un l'ha de decrementar). El backend
    // ja filtra per `estat` (filterset_fields), així que demanem només els open.
    watchpoints.list({ model: modelId, estat: 'open' })
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
      <WatchpointDrawer modelId={modelId} open={open} onClose={handleClose} onChanged={fetchCount} />
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
    // RETORN-2 — a l'ESTUDI, la data i la urgència les MANA la marca i les hi sobreescriu.
    // Sense aquesta nota, un tècnic que les canviés a mà no entendria per què tornen soles.
    { label: t('model_sheet.field_deadline'), value: (
        <span style={{ display: 'inline-flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          {deadlineCell}
          <EncarrecDelClient model={model} t={t} />
        </span>
      ) },
    // La maduresa només existeix al bessó de la MARCA (a l'estudi el camp és buit i el
    // component no pinta res), i és on cal: la marca no té tasques per mirar.
    ...(model.federacio_estat
      ? [{ label: t('federacio.maduresa_label'), value: <MaduresaBadge model={model} t={t} /> }]
      : []),
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

function TabFiles({ modelId, onEditFitxa }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  // K2 — aquest tab va per `authFetch` (no per `fetch` cru): un 401 per access token
  // caducat es refresca i es REINTENTA, en comptes d'arribar a la pantalla com a JSON.
  // El Bearer el posa `authFetch`; aquí ja no cal ni token ni capçalera d'autorització.

  const [fitxers, setFitxers] = useState([])
  const [orderBy, setOrderBy] = useState('data')
  const [uploading, setUploading] = useState(false)
  const [popup, setPopup] = useState(null)
  // D-31.9b — obrir un adjunt no donava CAP senyal: entre el clic i el primer píxel hi ha una
  // URL signada, una petició i el pintat del PDF, i la pantalla es quedava amb un rectangle
  // blanc. Es reposa a `true` a cada obertura (i no només al muntatge) perquè el segon fitxer
  // que s'obre sense tancar el modal ha de tornar a avisar.
  const [previewCarregant, setPreviewCarregant] = useState(false)
  const obrirPreview = (fitxer) => {
    setPreviewCarregant(true)
    setPopup({ url: previewUrl(fitxer), nom: fitxer.nom_fitxer })
  }
  // D-31.9c — obrir un arxiu DES DE LA FILA. Què vol dir «obrir» depèn del que és: una fitxa
  // `.ftt` és un ZIP i la seva vista prèvia no ensenyaria res, o sigui que obre l'editor —
  // exactament la mateixa bifurcació que ja fa el panell de detall (`FileDetail`, isTechSheet).
  // Una sola llei d'obertura per a les dues portes.
  const esFitxaTecnica = (f) => f.tipus === 'TECHSHEET' || fileExt(f.nom_fitxer) === 'ftt'
  const obrirFitxer = (f) => {
    // F2.2 — obrir des de la llista és MIRAR. Qui vulgui treballar-hi té «Modificar» al tab de
    // Fitxa tècnica (o el botó Editar del panell de detall), que sí obren sessió.
    if (esFitxaTecnica(f)) navigate(`/models/${modelId}/ftt/${f.id}?mode=consulta`)
    else obrirPreview(f)
  }
  const [history, setHistory] = useState(null)   // { fitxer, chain[], loading }
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)   // Finder: CAP selecció per defecte

  useEffect(() => {
    authFetch(`/api/v1/model-fitxers/?model=${modelId}&is_current=true&ordering=-data_pujada`)
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
      // El FormData es reenvia tal qual si `authFetch` ha de refrescar i reintentar: la
      // pujada sobreviu a l'access token caducat i el fitxer NO es perd (K2).
      const r = await authFetch(`/api/v1/models/${modelId}/upload-fitxer/`, {
        method: 'POST',
        body: formData,
      })
      const d = await r.json()
      if (r.ok) {
        setFitxers(prev => versioAnteriorId
          ? [d, ...prev.filter(f => f.id !== versioAnteriorId)]
          : [d, ...prev])
      } else {
        // K3 — codis coneguts en llenguatge humà; la resta, com abans.
        setError(missatgeError(d, t))
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
      const r = await authFetch(`/api/v1/model-fitxers/${fitxer.id}/versions/`)
      const d = await r.json()
      setHistory({ fitxer, chain: (d.results || d || []), loading: false })
    } catch {
      setHistory({ fitxer, chain: [], loading: false })
    }
  }

  const handleDelete = async (fitxerId) => {
    if (!window.confirm(t('model_sheet.confirm_delete_file'))) return
    await authFetch(`/api/v1/model-fitxers/${fitxerId}/`, { method: 'DELETE' })
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
            {previewCarregant && (
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                padding: '10px 0', fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
              }}>
                <i className="ti ti-loader-2" aria-hidden="true"
                   style={{ fontSize: 16, animation: 'spin 0.8s linear infinite' }} />
                {t('model_sheet.files.loading_preview')}
              </div>
            )}
            {/* `onError` tanca el senyal igual que `onLoad`: si la URL signada ha caducat o el
                fitxer no es pot pintar, la roda no pot quedar-se girant per sempre. */}
            {PREVIEW_IMG_RE.test(popup.nom || '') ? (
              <img src={popup.url} alt={popup.nom}
                onLoad={() => setPreviewCarregant(false)}
                onError={() => setPreviewCarregant(false)}
                style={{ maxWidth: '80vw', maxHeight: '80vh', objectFit: 'contain' }} />
            ) : (
              <iframe src={popup.url} title={popup.nom}
                onLoad={() => setPreviewCarregant(false)}
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
                      onClick={() => obrirPreview(v)}
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

      {/* D-31.9b — LA BARRA DE PUJADA. Fins ara l'únic senyal era que el text del botó canviava
          a «Pujant…»: 12 píxels de text en un cantó, en una pantalla plena de taules, mentre un
          fitxer de 20 MB puja sense dir res. La barra és INDETERMINADA a posta — `authFetch`
          torna una promesa i no exposa `onUploadProgress`, i fabricar un percentatge fals seria
          pitjor que no donar-ne cap. Diu «està passant alguna cosa», que és el que faltava.
          El keyframe local segueix el precedent de la casa (SizeMapSetup.jsx:982); el `spin`
          global d'`index.css:75` no serveix aquí perquè el moviment és de translació. */}
      {uploading && (
        <div role="progressbar" aria-busy="true" aria-label={t('model_sheet.uploading')}
          style={{ height: 3, borderRadius: 2, background: 'var(--bg-muted)',
                   overflow: 'hidden', marginBottom: 12 }}>
          <style>{'@keyframes ftt-upload-bar{from{transform:translateX(-100%)}to{transform:translateX(400%)}}'}</style>
          <div style={{ width: '25%', height: '100%', background: 'var(--gold)',
                        animation: 'ftt-upload-bar 1.1s ease-in-out infinite' }} />
        </div>
      )}

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
              <span style={{ width: 26, flexShrink: 0 }} />
            </div>
            {sorted.map(f => (
              <FileRow key={f.id} fitxer={f} selected={f.id === selectedId}
                onSelect={() => setSelectedId(f.id)}
                onOpen={() => obrirFitxer(f)} />
            ))}
          </div>
          {/* DRETA — detall del fitxer seleccionat; buit discret si cap. */}
          <div style={{ width: 340, flexShrink: 0 }}>
            {selected ? (
              <FileDetail key={selected.id} fitxer={selected}
                onPreview={() => obrirPreview(selected)}
                onHistory={() => openHistory(selected)}
                onNewVersion={file => handleUpload(file, selected.id)}
                onEdit={() => onEditFitxa(selected.id)}
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
function FileRow({ fitxer, selected, onSelect, onOpen }) {
  const { t, i18n } = useTranslation()
  const ext = fileExt(fitxer.nom_fitxer)
  const esFitxa = fitxer.tipus === 'TECHSHEET' || ext === 'ftt'
  const obrirLabel = esFitxa ? t('model_sheet.files.edit') : t('model_sheet.view')
  const date = fitxer.data_pujada
    ? new Date(fitxer.data_pujada).toLocaleDateString(i18n.language || 'ca', { day: '2-digit', month: '2-digit', year: '2-digit' })
    : '—'
  return (
    // D-31.9c — la fila obre l'arxiu, i ho fa per les DUES vies que un Finder ofereix: doble
    // clic sobre la fila sencera (convenció del patró que aquest component ja segueix) i un
    // botó explícit al final. El clic simple segueix SELECCIONANT i no obrint: si obrís,
    // recórrer la llista amb el teclat o mirar el detall de tres fitxers seguits obriria tres
    // modals, i el panell de detall —que és la meitat dreta d'aquesta pantalla— perdria l'única
    // manera d'omplir-se. El botó és el que fa la funció DESCOBRIBLE; el doble clic, ràpida.
    <div onClick={onSelect} onDoubleClick={onOpen} title={fitxer.nom_fitxer}
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
      {/* `stopPropagation`: el botó obre, i no ha de tornar a disparar la selecció de la fila. */}
      <button type="button" onClick={e => { e.stopPropagation(); onOpen() }}
        title={obrirLabel} aria-label={`${obrirLabel} — ${fitxer.nom_fitxer}`}
        style={{ width: 26, flexShrink: 0, background: 'none', border: 'none', padding: 0,
                 cursor: 'pointer', color: 'var(--text-muted)', lineHeight: 1 }}>
        <i className={`ti ${esFitxa ? 'ti-edit' : 'ti-eye'}`} aria-hidden="true"
           style={{ fontSize: 16 }} />
      </button>
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
