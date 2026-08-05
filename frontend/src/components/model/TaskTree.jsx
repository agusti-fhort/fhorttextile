import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Badge from '../ui/Badge'
import { models, taskTypes } from '../../api/endpoints'
import { taskTypeLabel } from '../../utils/taskType'
import { formatMinutes } from '../../utils/format'
import {
  GEST_DECLARAT, GEST_EINA, GEST_SENSE_EINA, GEST_SENSE_PANTALLA,
  destiDeTasca, esOferible, gestDeTasca,
} from '../../utils/destiTasca'

// B2/TL1 — Arbre per INICIAR tasques des del Model Sheet (fase → TaskType → targeta + "Iniciar").
// Targetes amb el MATEIX llenguatge visual que el WorkPlan del Dashboard. Tres estats:
//   1) NORMAL  → meva o sense ModelTask però iniciable: nítida, botó gold actiu.
//   2) FADE+NOM → assignada a un altre tècnic: esvaïda + "Assignada a: nom" (es pot reclamar).
//   3) FADE+"No assignada" → cap ModelTask encara: esvaïda, invitació a agafar-la.
// El backend (open-task) és idempotent: crea-si-falta + InProgress. Referència per `code` (G9).

const API = import.meta.env.VITE_API_URL || ''

// Ordre canònic de fases — mirall de TaskType.FASE_CHOICES (backend tasks/models.py).
const PHASE_ORDER = ['Disseny', 'Dev. tècnic', 'Prototip', 'Mostres', 'Preproducció', 'Producció']
const PHASE_I18N = {
  'Disseny': 'model_sheet.tasks.tree_phase_design',
  'Dev. tècnic': 'model_sheet.tasks.tree_phase_dev',
  'Prototip': 'model_sheet.tasks.tree_phase_prototype',
  'Mostres': 'model_sheet.tasks.tree_phase_samples',
  'Preproducció': 'model_sheet.tasks.tree_phase_preprod',
  'Producció': 'model_sheet.tasks.tree_phase_prod',
}

// code → icona (mirall de WorkPlan TASK_ICON; duplicació mínima conscient).
const TASK_ICON = {
  pattern_digit: 'ti-vector', pattern_cad: 'ti-vector-bezier', pattern_hand: 'ti-pencil',
  pattern_review: 'ti-eye-check', pom: 'ti-ruler-2', size_check: 'ti-ruler-measure',
  tech_sheet: 'ti-file-text', bom: 'ti-list-details', scaling: 'ti-resize',
  marking: 'ti-layout-grid', Audit: 'ti-checklist',
}
const STATUS_VARIANT = { Done: 'ok', InProgress: 'gold', Paused: 'warn', Pending: 'gray' }

// T2 — el destí ja no es cableja aquí: el diu el CATÀLEG (`tipus`/`eina`/`mode`), traduït pel
// resolutor únic `utils/destiTasca`. El `switch (code)` que hi havia (sis casos i un default
// null) era la causa que «Revisió de patró CAD» no fes res: el catàleg tenia la resposta i
// ningú l'hi preguntava.

const sectionTitle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 500,
  textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 10,
}
const phaseTitle = {
  fontSize: 'var(--fs-caption)', color: 'var(--gold)', fontWeight: 700,
  textTransform: 'uppercase', letterSpacing: '0.05em', margin: '16px 0 8px',
}
const cardsGrid = { display: 'flex', flexWrap: 'wrap', gap: 12 }

export default function TaskTree({ modelId, modelTaskRows = [], tasks = [], onTaskStarted, onOpenTab }) {  // eslint-disable-line no-unused-vars
  const { t } = useTranslation()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const [types, setTypes] = useState([])
  const [myProfileId, setMyProfileId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(null)   // code en curs d'iniciar

  useEffect(() => {
    let alive = true
    setLoading(true)
    taskTypes.list({ active: true, page_size: 200 })
      .then(res => {
        const d = res?.data
        const list = Array.isArray(d?.results) ? d.results : (Array.isArray(d) ? d : [])
        if (alive) setTypes(list)
      })
      .catch(() => { if (alive) setError(t('model_sheet.tasks.tree_start_error')) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId])

  // "meva" = assignee_id === me.profile_id (UserProfile.id) — mateix criteri que WorkPlan (P1.5).
  useEffect(() => {
    let alive = true
    fetch(`${API}/api/v1/me/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (alive && d) setMyProfileId(d.profile_id ?? null) })
      .catch(() => {})
    return () => { alive = false }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // L'auditoria de B1 escrivia a la consola els tipus amb `eina` i sense ruta, i ningú no la
  // llegia mai (T0 §S-3). Ara el forat no es denuncia per consola: es diu a la targeta, que és
  // on el tècnic el troba.

  const start = (tt) => {
    const gest = gestDeTasca(tt)
    // EXTERNA-LLIURE — el temps es DECLARA, no es cronometra: aquí no s'obre cap tasca. Fins
    // avui aquest botó cridava `open-task`, que posa la tasca En curs i obre un TimerEntrada
    // real; com que no hi ha cap pantalla on treballar ni cap batec que el sostingui, el que
    // quedava era un rellotge corrent sol. El gest de declarar arriba a T3, amb la seva maqueta.
    if (gest === GEST_DECLARAT) return

    setError(''); setStarting(tt.code)
    models.openTask(modelId, tt.code)
      .then(res => {
        onTaskStarted?.()
        // Sense superfície no es navega. Iniciar-la segueix sent útil —declara la intenció i
        // engega el compte— però el transport encara és manual, i portar el tècnic a una
        // pantalla que no fa el que la targeta promet seria pitjor que no moure'l.
        const desti = gest === GEST_EINA
          ? destiDeTasca(tt, { modelId, taskId: res?.data?.task_id })
          : null
        if (desti) {
          if (desti.tab) onOpenTab?.(desti.tab)
          navigate(desti.route)
        }
      })
      .catch(err => {
        if (err?.response?.status === 403) setError(t('model_sheet.tasks.tree_no_permission'))
        else setError(t('model_sheet.tasks.tree_start_error'))
      })
      .finally(() => setStarting(null))
  }

  // Agrupa per fase respectant l'ordre canònic; les fases sense tipus no es mostren.
  // `esOferible` filtra pel CATÀLEG (`visible`), no per cap llista de codis d'aquí: qui decideix
  // què s'ofereix és el catàleg, i amagar-ne un és una fila de BD, no un desplegament.
  const byPhase = {}
  for (const tt of types) {
    if (!esOferible(tt)) continue
    ;(byPhase[tt.fase] = byPhase[tt.fase] || []).push(tt)
  }
  const ordered = [...PHASE_ORDER, ...Object.keys(byPhase).filter(p => !PHASE_ORDER.includes(p))]
    .filter(p => byPhase[p] && byPhase[p].length)
  // Creuament TaskType.code → ModelTask existent (status + assignee) via el compositor del dashboard.
  const taskByCode = {}
  for (const tk of tasks) { if (tk && tk.task_type_code) taskByCode[tk.task_type_code] = tk }

  const renderCard = (tt) => {
    const mt = taskByCode[tt.code]
    const exists = !!mt
    const mine = exists && mt.assignee_id != null && mt.assignee_id === myProfileId
    const otherTech = exists && mt.assignee_id != null && !mine
    const faded = otherTech || !exists            // estats 2 i 3
    const icon = TASK_ICON[tt.code] || 'ti-checkbox'
    const busy = starting === tt.code
    // El gest de la targeta surt del catàleg. Cada un que no navega porta la seva nota: el
    // tècnic ha de saber PER QUÈ el botó no el mou, no quedar-se mirant una targeta muda.
    const gest = gestDeTasca(tt)
    const NOTA = {
      [GEST_DECLARAT]: 'model_sheet.tasks.gest_declarat_nota',
      [GEST_SENSE_PANTALLA]: 'model_sheet.tasks.gest_sense_pantalla_nota',
      [GEST_SENSE_EINA]: 'model_sheet.tasks.gest_sense_eina_nota',
    }[gest]
    return (
      <div key={tt.code} style={{
        flex: '1 1 220px', maxWidth: 320, minWidth: 0,
        border: '0.5px solid var(--border)', borderRadius: 8, padding: '0.7rem 0.8rem',
        background: 'var(--white)', opacity: faded ? 0.55 : 1,
      }}>
        {/* Capçalera: icona + nom */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <i className={`ti ${icon}`} style={{ fontSize: 16, color: 'var(--gold)', flexShrink: 0 }} />
          <span style={{ fontWeight: 500, color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {taskTypeLabel(t, tt.code, tt.name)}
          </span>
        </div>

        {/* Cos: temps consumit (si la tasca existeix) */}
        {exists && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 8, fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
            <span><i className="ti ti-clock" style={{ fontSize: 13, marginRight: 3 }} />{formatMinutes(mt.temps_consumit_min ?? 0)}</span>
          </div>
        )}

        {/* Assignee / no assignada */}
        <div style={{ marginTop: 4, fontSize: 'var(--fs-label)', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {otherTech && mt.assignee_nom
            ? t('model_sheet.tasks.tree_assigned_to', { name: mt.assignee_nom })
            : t('model_sheet.tasks.tree_unassigned')}
        </div>

        {/* Peu: botó Iniciar + badge d'estat (si existeix) */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
          <button type="button" disabled={!!starting || gest === GEST_DECLARAT}
            onClick={() => start(tt)}
            title={t(NOTA || 'model_sheet.tasks.tree_start_task')}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              border: (otherTech || gest === GEST_DECLARAT) ? '1px solid var(--border)' : '1px solid var(--gold)',
              borderRadius: 6, background: 'transparent',
              color: (otherTech || gest === GEST_DECLARAT) ? 'var(--text-muted)' : 'var(--gold)',
              fontFamily: 'inherit', fontSize: 'var(--fs-body)', fontWeight: 600,
              padding: '5px 12px',
              cursor: (starting || gest === GEST_DECLARAT) ? 'default' : 'pointer',
              opacity: busy ? 0.5 : 1,
            }}>
            <i className={`ti ${gest === GEST_DECLARAT ? 'ti-clock-edit' : 'ti-player-play'}`}
              style={{ fontSize: 14 }} />
            {gest === GEST_DECLARAT
              ? t('model_sheet.tasks.gest_declarat')
              : t('model_sheet.tasks.tree_start_task')}
          </button>
          {exists && (
            <Badge variant={STATUS_VARIANT[mt.status] || 'gray'} style={{ maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {t(`model_sheet.dashboard.task_status.${mt.status}`, { defaultValue: mt.status })}
            </Badge>
          )}
        </div>
        {NOTA && (
          <div style={{ marginTop: 6, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', whiteSpace: 'normal' }}>
            {t(NOTA)}
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ width: '100%' }}>
      <div style={sectionTitle}>{t('model_sheet.tasks.tree_title')}</div>
      {error && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10,
          border: '0.5px solid var(--err)', background: 'var(--err-bg)', color: 'var(--err)',
          borderRadius: 8, padding: '0.5rem 0.8rem', fontSize: 'var(--fs-body)' }}>
          <i className="ti ti-alert-triangle" style={{ fontSize: 15 }} />{error}
        </div>
      )}
      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>{t('model_sheet.loading')}</div>
      ) : ordered.map(phase => (
        <div key={phase}>
          <div style={phaseTitle}>{t(PHASE_I18N[phase], { defaultValue: phase })}</div>
          <div style={cardsGrid}>
            {byPhase[phase].slice().sort((a, b) => (a.default_order - b.default_order)).map(renderCard)}
          </div>
        </div>
      ))}
    </div>
  )
}
