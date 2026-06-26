import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import Badge from '../ui/Badge'
import ModelTimeline from './ModelTimeline'
import WorkPlan from './WorkPlan'
import WatchpointsPanel from './WatchpointsPanel'
import ModelMilestones from './ModelMilestones'
import { formatMinutes } from '../../utils/format'

// Dashboard del model — PEÇA F1 (Q1 "on sóc" + Q4 "què puc fer").
// Consumeix GET /api/v1/models/<id>/dashboard/ (endpoint B1, read-only).
// NO timeline (Q2), NO atenció (Q3), NO esforç — vénen en peces posteriors.
// Criteri: cada artefacte i cada tasca DEU navegar (treballar), mai informar i prou.

const API = import.meta.env.VITE_API_URL || ''
const MONO = 'IBM Plex Mono, monospace'

// Layout de dues columnes: esquerra Q1/artefactes/Q4 (F1), dreta timeline (F2).
// flexWrap fa que en pantalla estreta la dreta caigui SOTA l'esquerra (apilat), no comprimida.
const grid = { display: 'flex', flexWrap: 'wrap', gap: '2rem', alignItems: 'flex-start' }
const wrap = { display: 'flex', flexDirection: 'column', gap: '1.5rem', flex: '1 1 380px', maxWidth: 760 }
// Columna dreta ~50%: Watchpoints (fil 1) + Timeline (fil 2), apilats i BESSONS.
const rightCol = { display: 'flex', flexDirection: 'column', gap: '1.5rem', flex: '1 1 0', minWidth: 0 }
// Marc ÚNIC compartit pels dos fils: el contenidor exterior és l'únic marc (vora + caixa) i porta el
// scroll propi (maxHeight + overflowY). Els components interns (WatchpointsPanel, ModelTimeline) ja no
// aporten ni caixa ni capçalera → cap caixa-dins-de-caixa. El títol va a FORA (sectionTitle).
const filScroll = {
  maxHeight: '40vh', overflowY: 'auto',
  border: '0.5px solid var(--border)', borderRadius: 8, background: 'var(--bg-card)',
  padding: '8px 12px',
}
const sectionTitle = {
  fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontWeight: 500,
  textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8,
}
const card = {
  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12,
  width: '100%', textAlign: 'left',
  border: '0.5px solid var(--border)', borderRadius: 8, padding: '0.7rem 0.9rem',
  background: 'var(--white)', cursor: 'pointer', color: 'var(--text-main)',
}
const cardEmpty = {
  border: '0.5px dashed var(--border)', borderRadius: 8, padding: '0.7rem 0.9rem',
  background: 'var(--bg-muted)', color: 'var(--text-muted)', fontSize: 'var(--fs-body)',
}
const stateBox = {
  border: '0.5px solid var(--border)', borderRadius: 8, padding: '1rem 1.1rem',
  background: 'var(--bg-card)',
}

export default function DashboardTab({ modelId, onOpenTab, navigate, wpVersion = 0 }) {
  const { t } = useTranslation()
  const token = localStorage.getItem('access_token')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showTech, setShowTech] = useState(false)
  const [albaraTime, setAlbaraTime] = useState(null)   // temps total del model (GET /albara/), per al títol "On sóc"

  // Càrrega del compositor. Reutilitzable: el transport del Pla de treball (P3) la torna a
  // cridar (onRefresh) després de cada transició que NO navega, perquè estat/temps/obertures
  // de les targetes reflecteixin el canvi sense recarregar la pàgina.
  const load = useCallback(() => {
    let alive = true
    setLoading(true); setError('')
    fetch(`${API}/api/v1/models/${modelId}/dashboard/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => { if (!r.ok) throw new Error('http'); return r.json() })
      .then(d => { if (alive) setData(d) })
      .catch(() => { if (alive) setError(t('model_sheet.dashboard.err_load')) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId])

  useEffect(() => load(), [load])

  // Temps acumulat del model: mateixa font que la pestanya Registre (GET /albara/), sense recalcular.
  // Només se'n mostra el "temps total" a la línia del títol "On sóc". Degrada net si no hi ha activitat.
  useEffect(() => {
    let alive = true
    fetch(`${API}/api/v1/models/${modelId}/albara/`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (alive) setAlbaraTime(d && d.merited !== false ? formatMinutes(d.totals?.total_minutes) : null) })
      .catch(() => {})
    return () => { alive = false }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId])

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center',
                    color: 'var(--text-muted)', fontSize: 'var(--fs-body)' }}>
        {t('model_sheet.loading')}
      </div>
    )
  }
  if (error) {
    return (
      <div style={{ ...cardEmpty, display: 'flex', alignItems: 'center', gap: 8,
                    borderStyle: 'solid', borderColor: 'var(--err)', color: 'var(--err)',
                    background: 'var(--err-bg)' }}>
        <i className="ti ti-alert-triangle" style={{ fontSize: 16 }} />
        {error}
      </div>
    )
  }
  if (!data) return null

  const onSoc = data.on_soc || {}
  const art = data.artefactes_vigents || {}
  const tasques = Array.isArray(data.tasques) ? data.tasques : []

  const phaseLabel = t(`model_sheet.dashboard.phase.${onSoc.fase}`, { defaultValue: onSoc.fase || '—' })
  const stateLabel = t(`kanban.estats.${onSoc.estat}`, { defaultValue: onSoc.estat || '—' })
  const tasksOpen = onSoc.blockers?.tasks_open ?? 0

  const goKanban = () => navigate('/tasques/kanban')

  const fitxa = art.fitxa
  const grading = art.grading
  const base = art.base || {}
  const baseHasData = !!(base.base_size_label || (base.n_active ?? 0) > 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

      {/* ── Pla de treball (Q4 crescut) — ample total dalt (P2a) ───── */}
      <WorkPlan tasques={tasques} modelId={modelId} onRefresh={load} onOpenTab={onOpenTab} />

      <div style={grid}>
      <div style={wrap}>

      {/* ── Q1 · On sóc / què bloqueja ─────────────────────────────── */}
      <section>
        <div style={sectionTitle}>{t('model_sheet.dashboard.section_status')}</div>
        <div style={stateBox}>
          {/* D — temps acumulat a la DRETA de la línia de la fase (Desenvolupament), MATEIXA MIDA que el
              títol de fase. Reusa total_minutes de /albara/. La resta del bloc queda intacta. */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 'var(--fs-h2)', fontWeight: 500, color: 'var(--text-main)' }}>
              {phaseLabel}
            </span>
            <Badge variant="gray">{stateLabel}</Badge>
            {onSoc.ready_for_gate && (
              <Badge variant="gate" icon="ti-flag-check">
                {t('model_sheet.dashboard.ready_for_gate')}
              </Badge>
            )}
            {albaraTime && (
              <span style={{ marginLeft: 'auto', fontSize: 'var(--fs-h2)', fontWeight: 500, color: 'var(--text-main)' }}>
                {albaraTime}
              </span>
            )}
          </div>
          <div style={{ marginTop: 10 }}>
            {tasksOpen > 0 ? (
              <button type="button" onClick={goKanban}
                style={{ border: 'none', background: 'transparent', padding: 0, cursor: 'pointer' }}>
                <Badge variant="warn" icon="ti-alert-circle">
                  {t('model_sheet.dashboard.blockers_open', { n: tasksOpen })}
                </Badge>
              </button>
            ) : (
              <Badge variant="ok" icon="ti-check">
                {t('model_sheet.dashboard.blockers_none')}
              </Badge>
            )}
          </div>
        </div>
      </section>

      {/* ── Q1 · Artefactes vigents (accessos, no etiquetes) ───────── */}
      <section>
        <div style={sectionTitle}>{t('model_sheet.dashboard.section_done')}</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>

          {/* Fitxa → pestanya Fitxa tècnica */}
          {fitxa ? (
            <button type="button" style={card} onClick={() => onOpenTab('Fitxa tècnica')}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <i className="ti ti-file-text" style={{ fontSize: 16, color: 'var(--gold)' }} />
                {t('model_sheet.dashboard.artefact_fitxa')}
                <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>
                  {t('model_sheet.dashboard.version_short', { n: fitxa.versio })}
                </span>
                {fitxa.estat && (
                  <Badge variant={fitxa.estat === 'tancat' ? 'ok' : 'gray'}>
                    {t(`model_sheet.dashboard.fitxa_estat.${fitxa.estat}`, { defaultValue: fitxa.estat })}
                  </Badge>
                )}
              </span>
              <i className="ti ti-chevron-right" style={{ color: 'var(--text-muted)' }} />
            </button>
          ) : (
            <div style={cardEmpty}>{t('model_sheet.dashboard.empty_fitxa')}</div>
          )}

          {/* Grading → pestanya Escalat (editor propagat de la taula graduada) */}
          {grading ? (
            <button type="button" style={card} onClick={() => onOpenTab('Escalat')}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <i className="ti ti-table" style={{ fontSize: 16, color: 'var(--gold)' }} />
                {t('model_sheet.dashboard.artefact_grading')}
                <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>
                  {t('model_sheet.dashboard.version_short', { n: grading.version_number })}
                </span>
                <Badge variant={grading.aprovada ? 'ok' : 'gold'}>
                  {grading.aprovada
                    ? t('model_sheet.dashboard.grading_approved')
                    : t('model_sheet.dashboard.grading_draft')}
                </Badge>
              </span>
              <i className="ti ti-chevron-right" style={{ color: 'var(--text-muted)' }} />
            </button>
          ) : (
            <div style={cardEmpty}>{t('model_sheet.dashboard.empty_grading')}</div>
          )}

          {/* Base → pestanya Mesures */}
          {baseHasData ? (
            <button type="button" style={card} onClick={() => onOpenTab('Mesures')}>
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <i className="ti ti-ruler-2" style={{ fontSize: 16, color: 'var(--gold)' }} />
                {t('model_sheet.dashboard.artefact_base')}
                {base.base_size_label && (
                  <span style={{ fontFamily: MONO, color: 'var(--text-muted)' }}>{base.base_size_label}</span>
                )}
                <Badge variant="gray">
                  {t('model_sheet.dashboard.base_active', { n: base.n_active ?? 0 })}
                </Badge>
              </span>
              <i className="ti ti-chevron-right" style={{ color: 'var(--text-muted)' }} />
            </button>
          ) : (
            <div style={cardEmpty}>{t('model_sheet.dashboard.empty_base')}</div>
          )}
        </div>
      </section>

      {/* ── Properes fites del MODEL (sota Què tinc fet) ───────────── */}
      <ModelMilestones modelId={modelId} navigate={navigate} sectionTitle={sectionTitle} />

      {/* Q4 (llista plana de F1) ABSORBIT pel contenidor Pla de treball (P2a/P2b). */}

      {/* ── Estat tècnic (plegat: per consultar, no per actuar) ─────── */}
      <section>
        <button type="button" onClick={() => setShowTech(s => !s)}
          style={{ display: 'flex', alignItems: 'center', gap: 6, border: 'none',
                   background: 'transparent', cursor: 'pointer', padding: 0,
                   color: 'var(--text-muted)', fontSize: 'var(--fs-label)', fontWeight: 500 }}>
          <i className={`ti ti-chevron-${showTech ? 'down' : 'right'}`} />
          {t('model_sheet.dashboard.section_technical')}
        </button>
        {showTech && (
          <div style={{ ...stateBox, marginTop: 8, fontFamily: MONO, fontSize: 'var(--fs-label)',
                        color: 'var(--text-muted)', display: 'grid',
                        gridTemplateColumns: 'auto 1fr', gap: '4px 16px' }}>
            <span>{t('model_sheet.dashboard.tech_model_id')}</span><span>{data.model_id}</span>
            <span>{t('model_sheet.dashboard.tech_next_phase')}</span>
            <span>{onSoc.next_phase
              ? t(`model_sheet.dashboard.phase.${onSoc.next_phase}`, { defaultValue: onSoc.next_phase })
              : t('model_sheet.dashboard.tech_next_phase_none')}</span>
            <span>{t('model_sheet.dashboard.tech_tasks_open')}</span><span>{tasksOpen}</span>
            <span>{t('model_sheet.dashboard.tech_base_size')}</span><span>{base.base_size_label || '—'}</span>
            <span>{t('model_sheet.dashboard.tech_base_active')}</span><span>{base.n_active ?? 0}</span>
            <span>{t('model_sheet.dashboard.tech_size_fitting')}</span>
            <span>{grading?.size_fitting_id ?? '—'}</span>
          </div>
        )}
      </section>
      </div>

      {/* ── Columna dreta (~50%): dos fils BESSONS, títol a FORA + un sol marc amb scroll propi ── */}
      <div style={rightCol}>

        {/* Fil 1 — Avisos (Watchpoints, consulta). Títol a fora; el panell va sense caixa ni capçalera. */}
        <section>
          <div style={sectionTitle}>{t('watchpoints.dashboard_title')}</div>
          <div style={filScroll}>
            <WatchpointsPanel key={`wp-${wpVersion}`} modelId={modelId} editable={false} showAllByDefault />
          </div>
        </section>

        {/* Fil 2 — Què ha canviat (timeline). Mateix títol-a-fora + mateix marc → bessó del fil 1. */}
        <section>
          <div style={sectionTitle}>{t('model_sheet.dashboard.timeline.section')}</div>
          <div style={filScroll}>
            <ModelTimeline modelId={modelId} />
          </div>
        </section>
      </div>
      </div>
    </div>
  )
}
