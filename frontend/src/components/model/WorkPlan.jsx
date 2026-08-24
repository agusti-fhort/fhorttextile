import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Badge from '../ui/Badge'
import Modal from '../ui/Modal'
import TempsDeclaratForm from './TempsDeclaratForm'
import RondaPla from './RondaPla'
import EntregaDialog from './EntregaDialog'
import OkClientDialog from './OkClientDialog'
import { models, modelTasks, taskTypes } from '../../api/endpoints'
import { formatMinutes } from '../../utils/format'
import { taskTypeLabel } from '../../utils/taskType'
import { destiDeTasca } from '../../utils/destiTasca'
import { agrupaPerRonda, potObrirVolta, RONDA_ENTREGADA } from '../../utils/rondes'

// Pla de treball — PEÇA P3 + P4a (Q4 crescut): l'encàrrec del model com a procés.
// Consumeix dashboard.tasques (compositor enriquit a P1, JA ordenat canònic) — NO reordena.
// Transport (Play/Pause/Stop) CABLEJAT al backend de tasques (P3). "Play obre l'eina"
// (decisió Agus): Play = anar a treballar → open-task idempotent + navega a l'eina; si la
// tasca no en té (pattern_*, bom, scaling, marking, Audit) → InProgress sense navegar (§4).
// P4a — handoff (§6): Play sobre tasca d'ALTRI obre un diàleg de reassignació; en confirmar fa
// modelTasks.claim (self-only, gated execute_tasks) i després el mateix camí de Play de P3.
// Pause/Stop segueixen apagats a d'altri. Tres rendings (§5): meva / d'altri / fora d'encàrrec.
//
// M2 · LA CARA DE LES RONDES (mockup A v2) — el Pla s'AGRUPA PER VOLTA. El que canvia és
// l'embolcall, no la targeta: `RondaPla` posa la capçalera agregada, la línia d'entrega i el
// col·lapse, i les targetes de sempre hi entren com a `children`. Cap gest de transport, cap
// camí de Play i cap regla de handoff s'han tocat.
//
// 🔑 **UN MODEL SENSE CAP VOLTA ES PINTA COM ABANS D'M2**, pla i sense contenidors. No és una
// branca de conveniència: és la forma de tot model LLEGAT (la prohibició de backfill d'M1-bis
// segueix vigent fins al retroactiu de M5), i embolicar la seva feina en una ronda que no
// existeix seria dibuixar una volta que ningú no ha obert.

const API = import.meta.env.VITE_API_URL || ''

// T2 — la mini-taula local de destins (sis casos i un `default: null`) marxa d'aquí. Emmirallava
// la del Kanban, que ja no existeix (`fc98cab6`), i la seva bessona de `TaskTree`; el que decideix
// on va una tasca és el CATÀLEG (`tipus`/`eina`/`mode`), traduït pel resolutor únic
// `utils/destiTasca`. Aquí només cal creuar la tasca amb el seu tipus per `code` — el compositor
// del dashboard no porta `eina`/`mode`, o sigui que el catàleg es demana a part i es creua.

// task_type.code → icona Tabler (no hi havia mapa compartit; design system).
const TASK_ICON = {
  pattern_digit: 'ti-vector', pattern_cad: 'ti-vector-bezier', pattern_hand: 'ti-pencil',
  pattern_review: 'ti-eye-check', pom: 'ti-ruler-2', size_check: 'ti-ruler-measure',
  tech_sheet: 'ti-file-text', bom: 'ti-list-details', scaling: 'ti-resize',
  marking: 'ti-layout-grid', Audit: 'ti-checklist',
}

// status → variant del Badge del design system (mateix criteri que el dashboard F1).
const STATUS_VARIANT = { Done: 'ok', InProgress: 'gold', Paused: 'warn', Pending: 'gray' }

// Transport actiu per estat. Aquest és avui l'ÚNIC transport de la casa: l'ACTIONS de
// KanbanTasks que aquest mapa emmirallava ja no existeix (la pàgina Kanban global es va jubilar
// a fc98cab6), i cap altra superfície pinta play/pause/stop. No hi ha res amb què sincronitzar.
//
// play = Pending/Paused/Done (start/resume/reopen); en InProgress només es reactiva si hi ha eina
// per navegar-hi. pause = InProgress (només té sentit sobre feina en curs).
// stop = InProgress i PAUSED. A Paused no és una transició nova —`Paused → Done` segueix
// prohibida a la màquina d'estats (decisió Agus: NO es toca)— sinó un GEST: play+stop encadenat
// (`handleStop`). Pending NO en té: tancar una tasca mai començada és «cancel·lar», una altra
// cosa que aquest sprint no decideix.
const TRANSPORT = {
  Pending:    { play: true,  pause: false, stop: false },
  Paused:     { play: true,  pause: false, stop: true  },
  InProgress: { play: false, pause: true,  stop: true  },
  Done:       { play: true,  pause: false, stop: false },
}

// Fora d'encàrrec / fora de recepta: extra marcat al backend amb off_recipe=True (B4a), o
// tasca iniciada fora de l'encàrrec (origen='ad_hoc'). Activa el filet grana. NOMÉS marca.
function isOutOfCharge(task) { return task?.off_recipe === true || task?.origen === 'ad_hoc' }

const containerStyle = { background: 'transparent', width: '100%' }
const cardsGrid = { display: 'flex', flexWrap: 'wrap', gap: 12 }
// A6 · NOMÉS PELL. `.lblc` de la maqueta: 10px MAJÚSCULES amb tracking .08em i pes 600.
const sectionTitle = {
  fontSize: 'var(--fs-label)', lineHeight: '12px', color: 'var(--text-soft)', fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 10,
}
const footerWrap = { width: '100%', marginTop: 14 }

function TransportBtn({ icon, active, title, onClick }) {
  return (
    <button type="button" title={title} disabled={!active}
      onClick={e => {
        e.preventDefault()
        e.stopPropagation()
        if (active) onClick?.(e)
      }}
      style={{
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        // `.tctl button` de la maqueta: 26×26, filet --line, radi de control i fons --panel.
        // §5.7 — deshabilitat: BAIXA EL FONS, no la tinta; l'`opacity: .4` d'abans apagava
        // també la icona i la deixava molt per sota d'AA.
        width: 26, height: 26, borderRadius: 'var(--r-ctrl)',
        borderWidth: 1, borderStyle: 'solid', borderColor: 'var(--line)',
        background: active ? 'var(--panel)' : 'var(--bg-page)',
        color: active ? 'var(--text-soft)' : 'var(--text-faint)',
        cursor: active ? 'pointer' : 'not-allowed',
        fontSize: 14,
      }}>
      <i className={`ti ${icon}`} aria-hidden="true" style={{ fontSize: 'inherit', color: 'currentColor' }} />
    </button>
  )
}

function TaskCard({ task, mine, hasToolRoute, segellada = false, onPlay, onPause, onStop, onDeclarar }) {
  const { t } = useTranslation()
  const out = isOutOfCharge(task)
  const transport = TRANSPORT[task.status] || TRANSPORT.Pending
  const icon = TASK_ICON[task.task_type_code] || 'ti-checkbox'
  const playActive = mine ? (transport.play || (hasToolRoute && task.status === 'InProgress')) : true
  // Renderings §5: meva = nítida + transport operable; d'altri = fade + transport apagat.
  const otherTech = !mine && task.assignee_id != null
  return (
    <div style={{
      flex: '1 1 220px', maxWidth: 320, minWidth: 0,
      // `.tcard`: filet --line i radi 12. El filet gruixut de l'esquerra quan la tasca és
      // FORA D'ENCÀRREC es queda tal com és: és marca de dada (§1), no selecció.
      borderWidth: 1, borderStyle: 'solid',
      borderColor: out ? 'var(--err)' : 'var(--line)',
      borderLeftWidth: out ? 3 : 1,
      borderRadius: 'var(--r-card)', padding: '12px', background: 'var(--panel)',
      opacity: otherTech ? 0.55 : 1,
    }}>
      {/* Capçalera: icona + nom del tipus (truncat, mai desborda) */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
        <i className={`ti ${icon}`} style={{ fontSize: 16, color: 'var(--gold)', flexShrink: 0 }} />
        <span style={{ fontWeight: 500, color: 'var(--text-main)', overflow: 'hidden',
                       textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {taskTypeLabel(t, task.task_type_code, task.task_type_name)}
        </span>
      </div>

      {/* Cos: temps consumit (helper existent) + obertures */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8,
                    fontFamily: 'var(--mono)', fontSize: 'var(--fs-label)', color: 'var(--text-soft)' }}>
        <span><i className="ti ti-clock" style={{ fontSize: 13, marginRight: 3 }} />{formatMinutes(task.temps_consumit_min ?? 0)}</span>
        <span><i className="ti ti-repeat" style={{ fontSize: 13, marginRight: 3 }} />{t('model_sheet.dashboard.workplan.openings', { n: task.obertures ?? 0 })}</span>
      </div>

      {/* d'altri: qui la duu */}
      {otherTech && task.assignee_nom && (
        <div style={{ marginTop: 4, fontSize: 'var(--fs-label)', color: 'var(--text-soft)' }}>
          {t('model_sheet.dashboard.timeline.by', { label: task.assignee_nom })}
        </div>
      )}
      {out && (
        <div style={{ marginTop: 4, fontSize: 'var(--fs-label)', color: 'var(--err)',
                      overflowWrap: 'anywhere' }}>
          {t('model_sheet.dashboard.workplan.out_of_charge')}
        </div>
      )}

      {/* Peu: transport (placeholder) + badge d'estat */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
        {/* M2 · VOLTA ENTREGADA = FEINA SEGELLADA. El transport no s'apaga: se'n VA. Un botó
            deshabilitat convida a prémer-lo i promet que algun dia s'encendrà; el que diu la
            llei és que aquesta feina ja s'ha entregat i que rectificar-la obre volta nova.
            (No és un guard: `Done→InProgress` segueix sent legal —el segell és TOU, FIT-2— i el
            camí per fer-ho és el diàleg de la tasca, que deixa el rastre al log.) */}
        <div style={{ display: 'flex', gap: 4 }}>
          {segellada ? <span /> : (<>
          {/* P4a: Play disponible també a d'altri (obre diàleg de handoff). Pause/Stop només meves. */}
          <TransportBtn icon="ti-player-play"  active={playActive} title={mine ? t('model_sheet.dashboard.workplan.play') : t('model_sheet.dashboard.workplan.handoff_play')} onClick={() => onPlay(task)} />
          <TransportBtn icon="ti-player-pause" active={mine && transport.pause} title={t('model_sheet.dashboard.workplan.pause')} onClick={() => onPause(task)} />
          <TransportBtn icon="ti-player-stop"  active={mine && transport.stop}  title={t('model_sheet.dashboard.workplan.stop')}  onClick={() => onStop(task)} />
          {/* F2.5 · D-2 — les tasques EXTERNES es fan fora de l'eina i el rellotge no hi arriba
              mai: l'única manera que aquell temps entri al sistema és dir-lo. Va aquí, al costat
              del transport, i no dins d'un menú: si estigués amagat ningú no el faria servir i
              les hores del patró a mà seguirien sense existir. Les internes no el veuen mai. */}
          {task.tipus_extern && (
            <TransportBtn icon="ti-clock-plus" active title={t('temps_declarat.boto')}
                          onClick={() => onDeclarar(task)} />
          )}
          </>)}
        </div>
        <Badge variant={STATUS_VARIANT[task.status] || 'gray'} style={{ maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {t(`model_sheet.dashboard.task_status.${task.status}`, { defaultValue: task.status })}
        </Badge>
      </div>
    </div>
  )
}

export default function WorkPlan({ tasques, modelId, onRefresh, onOpenTab }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const [myProfileId, setMyProfileId] = useState(null)
  const [toast, setToast] = useState(null)        // { type, text }
  const [handoff, setHandoff] = useState(null)     // task pendent de reassignar (diàleg §6)
  const [declarant, setDeclarant] = useState(null)  // F2.5: tasca externa a la qual declarar temps
  const [claiming, setClaiming] = useState(false)  // guard anti-doble-clic del claim
  const toastTimer = useRef(null)
  // M2 — les voltes del model (amb l'entrega niuada) i el log, que és d'on surt el rastre FIT-8.
  const [rondes, setRondes] = useState([])
  const [log, setLog] = useState([])
  const [entregant, setEntregant] = useState(null)   // bloc pendent d'informar l'entrega
  const [okClient, setOkClient] = useState(null)     // entrega pendent de l'OK del client
  const [obrintVolta, setObrintVolta] = useState(false)
  // Col·lapse: NOMÉS les excepcions que l'usuari ha fet en aquesta pantalla. El defecte el
  // deriva `agrupaPerRonda` de l'estat de la volta i no es desa enlloc (v. `utils/rondes`).
  const [plegatManual, setPlegatManual] = useState({})

  useEffect(() => {
    let alive = true
    // scope viewer: "meva" = assignee_id === me.profile_id (UserProfile.id), NO me.id (P1.5).
    fetch(`${API}/api/v1/me/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (alive && d) setMyProfileId(d.profile_id ?? null) })
      .catch(() => {})
    return () => { alive = false }
  }, [])

  useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current) }, [])

  // El CATÀLEG, per `code`. El compositor del dashboard no porta `eina`/`mode` (només `code`),
  // o sigui que es demana a part i es creua aquí. Mentre no ha arribat, cap targeta navega —
  // que és millor que navegar a un destí endevinat.
  const [tipusPerCode, setTipusPerCode] = useState({})
  useEffect(() => {
    let alive = true
    taskTypes.list({ page_size: 200 })
      .then(res => {
        const d = res?.data
        const llista = Array.isArray(d?.results) ? d.results : (Array.isArray(d) ? d : [])
        if (!alive) return
        const map = {}
        for (const tt of llista) map[tt.code] = tt
        setTipusPerCode(map)
      })
      .catch(() => {})
    return () => { alive = false }
  }, [])

  const desti = (task) => destiDeTasca(tipusPerCode[task.task_type_code],
    { modelId, taskId: task.id })

  // M2 — LES VOLTES. Porta pròpia i no un camp del model: una ronda entregada és una ronda
  // TANCADA i `Model.ronda_oberta` no en pot ensenyar mai cap. El log hi va de la mà perquè el
  // rastre de FIT-8 (`nota`) viu a les transicions, no a la ronda.
  const [versio, setVersio] = useState(0)
  useEffect(() => {
    let alive = true
    models.rondes(modelId)
      .then(r => { if (alive) setRondes(Array.isArray(r?.data) ? r.data : []) })
      .catch(() => { if (alive) setRondes([]) })
    models.taskLog(modelId)
      .then(r => { if (alive) setLog(r?.data?.log ?? []) })
      .catch(() => { if (alive) setLog([]) })
    return () => { alive = false }
  }, [modelId, versio])

  // Refresc COMPLET: el dashboard (que el pare recarrega) i les voltes, que són nostres. Tot el
  // que escriu una ronda —entregar, OK del client, +Ronda— pot moure les DUES coses alhora:
  // informar una entrega tanca la volta I tanca la seva feina viva (FIT-13 + FIT-6).
  const refrescaTot = () => { setVersio(v => v + 1); onRefresh?.() }

  const list = Array.isArray(tasques) ? tasques : []
  const isMine = (task) => task.assignee_id != null && task.assignee_id === myProfileId

  // Peu (P5, §1): progrés (% Done sobre el total) + temps real acumulat sobre el MODEL. La suma
  // frontend de temps_consumit_min quadra EXACTAMENT amb el rollup de l'albarà (ambdós sumen els
  // minuts de timers consolidats de TOTES les tasques del model; el compositor no scopa) → suma
  // local, zero crides noves (P5 PAS 0.2). Degradació amb gràcia: 0 tasques → 0% / 0h 00m.
  const total = list.length
  const done = list.filter(task => task.status === 'Done').length
  const pct = total ? Math.round((100 * done) / total) : 0
  const totalMin = list.reduce((s, task) => s + (task.temps_consumit_min || 0), 0)

  // M2 — LES VOLTES, ja agregades. La lògica és compartida amb el Registre (`utils/rondes`):
  // les dues superfícies responen les mateixes preguntes sobre una ronda i només les pinten
  // diferent. `agrupaPerRonda` retorna també el bloc de la feina SENSE volta, que no es perd.
  const blocs = agrupaPerRonda(list, rondes, { tipusPerCode, log })
  const perVoltes = rondes.length > 0
  const obert = (bloc) => plegatManual[bloc.clau] ?? bloc.obertPerDefecte
  const commuta = (bloc) => setPlegatManual(p => ({ ...p, [bloc.clau]: !obert(bloc) }))

  function showToast(type, text) {
    setToast({ type, text })
    if (toastTimer.current) clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 3000)
  }

  // Exclusió un-InProgress-per-tècnic: si la resposta porta paused_task_id, el servei n'ha
  // pausat una altra del mateix tècnic → avisem amb el nom (la cerquem a la llista actual).
  function notifyPaused(res) {
    const pausedId = res?.data?.paused_task_id
    if (!pausedId) return
    const p = list.find(x => x.id === pausedId)
    const name = p ? taskTypeLabel(t, p.task_type_code, p.task_type_name) : `#${pausedId}`
    showToast('warn', t('model_sheet.dashboard.workplan.toast_paused', { name }))
  }

  // Missatge d'error REAL del servidor, amb els dos fallbacks de sempre.
  function transitionError(err) {
    return err?.response?.data?.error
      || (err?.response?.status === 403
        ? t('model_sheet.dashboard.workplan.not_allowed')
        : t('model_sheet.dashboard.workplan.transition_error'))
  }

  // Transició que NO navega (Play sense eina §4, Pause, Stop): després refresca el dashboard
  // perquè estat/temps/obertures de la targeta reflecteixin el canvi.
  function doTransition(task, toStatus) {
    modelTasks.transition(task.id, { to_status: toStatus })
      .then(res => { notifyPaused(res); onRefresh?.() })
      .catch(err => {
        showToast('err', transitionError(err))
        onRefresh?.()   // re-sincronitza amb el backend (la targeta local podia ser obsoleta)
      })
  }

  // Camí de Play de P3 (sobre tasca PRÒPIA): anar a treballar (decisió Agus). Amb eina: open-task
  // idempotent al backend + navega (Done = reobertura §3.8). Sense eina: InProgress sense navegar (§4)
  // — la targeta passa a "en curs".
  function playMine(task) {
    const teDesti = !!desti(task)
    // El backend decideix si cal crear/reobrir/claimar o fer no-op. Evita basar-se en l'estat
    // possiblement obsolet de la targeta i no pot demanar InProgress→InProgress.
    models.openTask(modelId, task.task_type_code)
      .then(res => {
        const openedTask = {
          ...task,
          id: res?.data?.task_id ?? task.id,
          status: res?.data?.status ?? task.status,
        }
        // El destí es recalcula amb la tasca JA oberta: el task_id de la resposta és el que
        // ha de viatjar a la URL (pot ser una tasca acabada de crear o la de la ronda viva).
        const d = teDesti ? desti(openedTask) : null
        if (d) {
          if (d.tab) onOpenTab?.(d.tab)
          navigate(d.route)
        } else {
          onRefresh?.()
        }
      })
      .catch(err => {
        const msg = err?.response?.data?.error
          || (err?.response?.status === 403
            ? t('model_sheet.dashboard.workplan.not_allowed')
            : t('model_sheet.dashboard.workplan.transition_error'))
        showToast('err', msg)
        onRefresh?.()
      })
  }

  // P4a — Play segons qui té la tasca. Meva → camí de P3 directe. D'altri → diàleg de handoff (§6).
  function handlePlay(task) {
    if (isMine(task)) { playMine(task); return }
    setHandoff(task)
  }

  // Confirmar handoff: claim (self-only, gated execute_tasks) i, si OK, el camí de Play de P3 amb
  // la tasca JA reassignada. El recompute es dispara sol al backend. 403 = allow-list (tipus que no
  // executo) → toast clar, sense navegar. La tasca ja és meva → playMine aplica net (mine=true).
  function confirmHandoff() {
    if (!handoff || claiming) return
    const task = handoff
    setClaiming(true)
    modelTasks.claim(task.id)
      .then(() => {
        setHandoff(null)
        playMine({ ...task, assignee_id: myProfileId })
      })
      .catch(err => {
        setHandoff(null)
        const denied = err?.response?.status === 403
        showToast('err', denied
          ? t('model_sheet.dashboard.workplan.claim_denied')
          : t('model_sheet.dashboard.workplan.claim_error'))
      })
      .finally(() => setClaiming(false))
  }

  // Pause = pauso, no he acabat. Stop = gest humà explícit "feta, 100%" (MAI automàtic). Cap navega.
  const handlePause = (task) => doTransition(task, 'Paused')

  // Stop sobre tasca EN CURS: una transició. Sobre tasca PAUSADA: el mateix botó, però el gest
  // és play+stop ENCADENAT — la màquina d'estats prohibeix `Paused → Done` i no es toca; el que
  // s'obre és el gest, no la llei. Un sol acte d'usuari, dues transicions legals.
  //
  // El segon pas NOMÉS si el primer torna 200. Si el play falla (403 d'allow-list, tasca ja
  // moguda per un altre), la tasca es queda Paused i el toast diu el motiu del servidor: el
  // gate d'execució no s'esquiva, es respecta de franc. Si falla el TANCAMENT havent reprès, el
  // toast ho diu explícitament — la tasca ha quedat en curs, i callar-ho seria l'estat intermedi
  // silenciós que aquest sprint prohibeix.
  function handleStop(task) {
    if (task.status !== 'Paused') { doTransition(task, 'Done'); return }
    let repres = false
    modelTasks.transition(task.id, { to_status: 'InProgress' })
      .then(res => {
        repres = true
        notifyPaused(res)   // el play pot haver pausat l'altra InProgress del tècnic
        return modelTasks.transition(task.id, { to_status: 'Done' })
      })
      .then(() => onRefresh?.())
      .catch(err => {
        const msg = transitionError(err)
        showToast('err', repres
          ? t('model_sheet.dashboard.workplan.stop_resumed_not_closed', { msg })
          : msg)
        onRefresh?.()
      })
  }

  // ── M2 · ELS TRES GESTOS DE VOLTA ────────────────────────────────────────────────────────

  // «+ Nova ronda». `codes: []` és el cas NORMAL des d'M1-bis: la volta nova neix amb el joc de
  // l'anterior (`codes_a_replicar`) i el que es demana s'hi SUMA. Aquí no es demana res —qui
  // vol una tasca que la volta anterior no tenia l'obre pel seu camí de sempre— i per això la
  // porta no ha d'aplicar cap allow-list: el joc replicat no és una tria de qui obre.
  //
  // El botó només es pinta si NO hi ha cap volta oberta, que és el guard d'`obrir_ronda`
  // (`potObrirVolta`): fer-lo visible i deixar que el backend contesti 400 seria oferir un gest
  // que la pantalla ja sabia que no es podia fer.
  function obreVolta() {
    if (obrintVolta) return
    setObrintVolta(true)
    models.obrirRonda(modelId, { motiu: 'nova_mostra', codes: [] })
      .then(res => {
        const d = res?.data || {}
        // La porta DIU què ha replicat, què ha adoptat del buit entre voltes i què ha quedat
        // pel camí perquè el catàleg l'ha desactivat (M1-bis + CODA). Callar-ho deixaria
        // l'usuari davant d'una volta amb tasques que ell no ha demanat i sense saber d'on surten.
        const parts = []
        if (d.codes_replicats?.length) parts.push(t('rondes.nova_replicats', { count: d.codes_replicats.length }))
        if (d.codes_adoptats?.length) parts.push(t('rondes.nova_adoptats', { count: d.codes_adoptats.length }))
        if (d.codes_omesos?.length) parts.push(t('rondes.nova_omesos', { codes: d.codes_omesos.join(', ') }))
        showToast(d.codes_omesos?.length ? 'warn' : 'ok',
          t('rondes.nova_ok', { n: d.seq }) + (parts.length ? ` · ${parts.join(' · ')}` : ''))
        refrescaTot()
      })
      .catch(e => showToast('err', e?.response?.data?.error || t('rondes.nova_error')))
      .finally(() => setObrintVolta(false))
  }

  return (
    <section style={containerStyle}>
      <div style={sectionTitle}>{t('model_sheet.dashboard.workplan.title')}</div>
      {/* §8c — estat buit: frase en --text-faint CURSIVA, mai caixa buida muda. */}
      {list.length === 0 ? (
        <div style={{ borderWidth: 1, borderStyle: 'dashed', borderColor: 'var(--line)',
                      borderRadius: 'var(--r-card)', padding: '12px 16px',
                      background: 'var(--panel)', color: 'var(--text-faint)',
                      fontStyle: 'italic', fontSize: 'var(--fs-body)' }}>
          {t('model_sheet.dashboard.workplan.empty')}
        </div>
      ) : perVoltes ? (
        /* M2 · MOCKUP A v2 — UN CONTENIDOR PER VOLTA, en ordre cronològic (la R1 a dalt, les
           noves a baix). Les targetes són LES MATEIXES: el que hi ha de nou és l'embolcall. */
        blocs.map(bloc => (
          <RondaPla key={bloc.clau} bloc={bloc}
            obert={obert(bloc)} onToggle={() => commuta(bloc)}
            onEntregar={() => setEntregant(bloc)}
            onOkClient={() => setOkClient(bloc.entrega)}>
            {bloc.tasques.map(task => (
              <TaskCard key={task.id} task={task} mine={isMine(task)}
                hasToolRoute={Boolean(desti(task))}
                segellada={bloc.estat === RONDA_ENTREGADA}
                onPlay={handlePlay} onPause={handlePause} onStop={handleStop}
                onDeclarar={setDeclarant} />
            ))}
          </RondaPla>
        ))
      ) : (
        <div style={cardsGrid}>
          {list.map(task => (
            <TaskCard key={task.id} task={task} mine={isMine(task)} hasToolRoute={Boolean(desti(task))}
              onPlay={handlePlay} onPause={handlePause} onStop={handleStop}
              onDeclarar={setDeclarant} />
          ))}
        </div>
      )}

      {/* «+ NOVA RONDA» · només quan no n'hi ha cap d'oberta (guard d'`obrir_ronda`), i mai en
          un model que encara no ha fet cap gest de treball: la R1 neix sola del primer gest
          (M1-bis · FIT-4) i un botó aquí faria creure que s'ha de declarar. */}
      {perVoltes && potObrirVolta(rondes) && (
        <button type="button" onClick={obreVolta} disabled={obrintVolta}
          style={{
            width: '100%', padding: 10, marginTop: 2, marginBottom: 6,
            borderRadius: 'var(--r-card)', textAlign: 'center', cursor: obrintVolta ? 'not-allowed' : 'pointer',
            border: '1px dashed var(--line)', background: 'transparent',
            color: obrintVolta ? 'var(--text-faint)' : 'var(--text-soft)',
            fontFamily: 'var(--mono)', fontSize: 'var(--fs-body)',
          }}>
          {t('rondes.nova')}
        </button>
      )}

      {/* La frase del peu del mockup: diu la LLEI que la pantalla acaba d'aplicar (per què el
          transport ha desaparegut de les voltes entregades). */}
      {perVoltes && (
        <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', marginBottom: 4 }}>
          {t('rondes.peu_segellades')}
        </div>
      )}

      {/* Peu (§1): barra de progrés (% Done) + temps acumulat sobre el model (ample total) */}
      <div style={footerWrap}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
                      gap: 12, flexWrap: 'wrap', marginBottom: 6, fontSize: 'var(--fs-label)',
                      color: 'var(--text-soft)' }}>
          <span>{t('model_sheet.dashboard.workplan.progress_label', { done, total })} · {pct}%</span>
          <span>{t('model_sheet.dashboard.workplan.time_total')}:{' '}
            <span style={{ fontFamily: 'var(--mono)', color: 'var(--text-main)' }}>{formatMinutes(totalMin)}</span>
          </span>
        </div>
        {/* `.prog` de la maqueta: 6px de canal en --line-soft, sense vora, píndola. El farciment
            és --ok: la barra diu QUANT S'HA FET, i el fet és verd a tot el sistema. */}
        <div style={{ height: 6, borderRadius: 'var(--r-pill)', background: 'var(--line-soft)',
                      overflow: 'hidden' }}>
          <div style={{ width: `${pct}%`, height: '100%', background: 'var(--ok)',
                        transition: 'width 200ms' }} />
        </div>
      </div>
      {declarant && (
        <TempsDeclaratForm
          tasca={declarant}
          onFet={(d) => {
            setDeclarant(null)
            showToast('ok', t('temps_declarat.ok', { minuts: d?.minuts ?? 0 }))
            onRefresh?.()
          }}
          onCancel={() => setDeclarant(null)}
        />
      )}
      {entregant && (
        <EntregaDialog
          ronda={entregant.ronda}
          viues={entregant.total - entregant.fets}
          onFet={() => {
            setEntregant(null)
            showToast('ok', t('rondes.entrega_ok', { n: entregant.ronda.seq }))
            refrescaTot()
          }}
          onCancel={() => setEntregant(null)} />
      )}
      {okClient && (
        <OkClientDialog
          entrega={okClient}
          onFet={() => {
            setOkClient(null)
            showToast('ok', t('rondes.ok_client_ok'))
            refrescaTot()
          }}
          onCancel={() => setOkClient(null)} />
      )}
      {handoff && (
        <Modal
          title={t('model_sheet.dashboard.workplan.handoff_title')}
          subtitle={handoff.assignee_nom
            ? t('model_sheet.dashboard.workplan.handoff_body', { name: handoff.assignee_nom })
            : t('model_sheet.dashboard.workplan.handoff_body_unassigned')}
          confirmLabel={t('model_sheet.dashboard.workplan.handoff_confirm')}
          cancelLabel={t('model_sheet.dashboard.workplan.handoff_cancel')}
          confirmDisabled={claiming}
          onConfirm={confirmHandoff}
          onCancel={() => { if (!claiming) setHandoff(null) }}
        />
      )}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', zIndex: 60,
          fontSize: 'var(--fs-body)', padding: '10px 16px', borderRadius: 8, boxShadow: '0 6px 24px rgba(0,0,0,0.18)',
          background: toast.type === 'err' ? 'var(--err-bg)' : toast.type === 'warn' ? 'var(--warn-bg)' : 'var(--ok-bg)',
          color: toast.type === 'err' ? 'var(--err)' : toast.type === 'warn' ? 'var(--warn)' : 'var(--ok)',
        }}>{toast.text}</div>
      )}
    </section>
  )
}
