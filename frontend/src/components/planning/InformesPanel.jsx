import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { models as modelsApi, timeAnalysis } from '../../api/endpoints'
import Center from '../ui/Center'

// Tab "Informes" — reporting de direcció. NO construeix backend nou: reusa el substrat agregat ja
// viu (DIAGNOSI §17.2 / ABAST §C):
//   · Cartera             → modelsApi.list (temporada/col·lecció/fase/risc), agregat al client.
//   · Compliment terminis → predicted_end vs data_objectiu (mateixa regla que RiskBlock), agregat.
//   · Productivitat       → timeAnalysis.byModel (estimat snapshot vs real timers), sumat per fase.
// COSTOS parcats (lligats a billing): NO s'hi inclouen. Exportació PDF/full: diferida (commit propi).
const MONO = 'IBM Plex Mono, monospace'

const PHASES = ['Pending', 'Dev', 'Proto', 'SizeSet', 'PP', 'TOP']   // Model.FASE_CHOICES (eix cartera)
const FASE_KEY = {   // TaskType.FASE_CHOICES → clau i18n planning.time.phase.* (eix productivitat)
  'Disseny': 'disseny', 'Dev. tècnic': 'dev_tecnic', 'Prototip': 'prototip',
  'Mostres': 'mostres', 'Preproducció': 'preproduccio', 'Producció': 'produccio',
}

const thS = {
  fontFamily: MONO, fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-muted)', textAlign: 'left',
  padding: '8px 10px', textTransform: 'uppercase', letterSpacing: '.04em',
  borderBottom: '0.5px solid var(--gray-l)', whiteSpace: 'nowrap',
}
const tdS = { padding: '8px 10px', fontSize: 'var(--fs-body)', borderBottom: '0.5px solid var(--gray-l)', verticalAlign: 'middle' }
const numTh = { ...thS, textAlign: 'right' }
const numTd = { ...tdS, fontFamily: MONO, fontVariantNumeric: 'tabular-nums', textAlign: 'right' }
const ghostBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '3px 10px', fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-main)',
}

function fmtMins(m) {
  if (!m) return '—'
  const h = Math.floor(m / 60), mm = m % 60
  return h ? (mm ? `${h}h ${mm}m` : `${h}h`) : `${mm}m`
}
function todayISO() { return new Date().toISOString().slice(0, 10) }
const phaseLabel = (t, p) => t(`model_sheet.dashboard.phase.${p}`, { defaultValue: p })

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

export default function InformesPanel({ me }) {
  const { t } = useTranslation()
  const canViewTeam = !!me?.capabilities?.includes('view_team_tasks')
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 30 }}>
      <DeadlinesBlock t={t} />
      <CarteraBlock t={t} />
      {/* Productivitat consumeix time-analysis (gated view_team_tasks) → només manager/admin. */}
      {canViewTeam && <ProductivityBlock t={t} />}
    </div>
  )
}

function SectionHead({ icon, color, title, subtitle, extra }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <h2 style={{ fontSize: 'var(--fs-h3)', fontWeight: 500, fontFamily: MONO, margin: 0 }}>
          <i className={`ti ${icon}`} style={{ fontSize: 16, marginRight: 6, color }} />{title}
        </h2>
        {extra}
      </div>
      {subtitle && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300, marginTop: 4, marginBottom: 0 }}>{subtitle}</p>}
    </div>
  )
}

function Kpi({ label, n, tone }) {
  const color = tone === 'err' ? 'var(--err)' : tone === 'warn' ? 'var(--warn)' : tone === 'ok' ? 'var(--ok)' : 'var(--text-main)'
  return (
    <div style={{ flex: '1 1 150px', minWidth: 130, border: `0.5px solid ${tone ? color : 'var(--gray-l)'}`, borderRadius: 12, background: 'var(--white)', padding: '14px 16px' }}>
      <div style={{ fontSize: 'var(--fs-h1)', fontWeight: 600, fontFamily: MONO, color, fontVariantNumeric: 'tabular-nums' }}>{n}</div>
      <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO, marginTop: 2 }}>{label}</div>
    </div>
  )
}

// ── COMPLIMENT DE TERMINIS ────────────────────────────────────────────────
// Classifica cada model (mateixa regla que el semàfor de Planning / RiskBlock):
//   on_time = té data_objectiu i predicted_end ≤ data_objectiu · overdue = en risc i objectiu passat
//   at_risk = en risc però objectiu futur · no_deadline = sense data_objectiu.
function DeadlinesBlock({ t }) {
  const navigate = useNavigate()
  const [models, setModels] = useState(null)
  useEffect(() => {
    let alive = true
    fetchAllPages(modelsApi.list, {}).then(m => { if (alive) setModels(m) }).catch(() => { if (alive) setModels([]) })
    return () => { alive = false }
  }, [])

  const { kpi, late } = useMemo(() => {
    const today = todayISO()
    const acc = { on_time: 0, at_risk: 0, overdue: 0, no_deadline: 0 }
    const lateRows = []
    for (const m of (models || [])) {
      if (!m.data_objectiu) { acc.no_deadline++; continue }
      const risc = m.predicted_end && m.predicted_end > m.data_objectiu
      if (!risc) { acc.on_time++; continue }
      const overdue = m.data_objectiu < today
      acc[overdue ? 'overdue' : 'at_risk']++
      lateRows.push({
        id: m.id, codi: m.codi_intern, nom: m.nom_prenda, fase: m.fase_actual,
        data_objectiu: m.data_objectiu, predicted_end: m.predicted_end, overdue,
        desviacio: Math.round((new Date(m.predicted_end) - new Date(m.data_objectiu)) / 86400000),
      })
    }
    lateRows.sort((a, b) => b.desviacio - a.desviacio)
    return { kpi: acc, late: lateRows }
  }, [models])

  if (models === null) return (
    <section><SectionHead icon="ti-calendar-stats" color="var(--gold)" title={t('planning.informes.deadlines.title')} /><Center>{t('planning.loading')}</Center></section>
  )
  return (
    <section>
      <SectionHead icon="ti-calendar-stats" color="var(--gold)" title={t('planning.informes.deadlines.title')}
        subtitle={t('planning.informes.deadlines.subtitle')} />
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 14 }}>
        <Kpi label={t('planning.informes.deadlines.on_time')} n={kpi.on_time} tone="ok" />
        <Kpi label={t('planning.informes.deadlines.at_risk')} n={kpi.at_risk} tone="warn" />
        <Kpi label={t('planning.informes.deadlines.overdue')} n={kpi.overdue} tone="err" />
        <Kpi label={t('planning.informes.deadlines.no_deadline')} n={kpi.no_deadline} />
      </div>
      {late.length > 0 && (
        <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%' }}>
            <thead><tr>
              <th style={thS}>{t('planning.col_model')}</th>
              <th style={thS}>{t('planning.gates.col_phase')}</th>
              <th style={thS}>{t('planning.col_deadline')}</th>
              <th style={thS}>{t('planning.col_end')}</th>
              <th style={numTh}>{t('planning.risk.col_deviation')}</th>
            </tr></thead>
            <tbody>
              {late.map(r => (
                <tr key={r.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/models/${r.id}`)}>
                  <td style={{ ...tdS, fontFamily: MONO, fontWeight: 600 }}>{r.codi}<div style={{ fontWeight: 400, color: 'var(--gray)' }}>{r.nom}</div></td>
                  <td style={tdS}>{phaseLabel(t, r.fase)}</td>
                  <td style={tdS}>{r.data_objectiu}</td>
                  <td style={{ ...tdS, color: 'var(--err)' }}>{r.predicted_end}</td>
                  <td style={{ ...numTd, color: r.overdue ? 'var(--err)' : 'var(--warn)', fontWeight: 600 }}>{t('planning.risk.deviation_days', { n: r.desviacio })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

// ── CARTERA ───────────────────────────────────────────────────────────────
// Estat global de la cartera agregat per una dimensió (Temporada / Col·lecció): total + distribució
// per fase del model + recompte de models en risc. 100% sobre modelsApi.list (reús, sense backend).
function CarteraBlock({ t }) {
  const [models, setModels] = useState(null)
  const [dim, setDim] = useState('temporada')
  const DIMENSIONS = [
    ['temporada', t('planning.informes.cartera.dim_temporada'),
      m => m.temporada ? `${m.temporada}${m.any ? ` ${m.any}` : ''}` : t('planning.informes.cartera.no_temporada')],
    ['collection', t('planning.informes.cartera.dim_collection'),
      m => m.collection || t('planning.informes.cartera.no_collection')],
  ]
  useEffect(() => {
    let alive = true
    fetchAllPages(modelsApi.list, {}).then(m => { if (alive) setModels(m) }).catch(() => { if (alive) setModels([]) })
    return () => { alive = false }
  }, [])

  const groups = useMemo(() => {
    const keyOf = DIMENSIONS.find(d => d[0] === dim)[2]
    const map = new Map()
    for (const m of (models || [])) {
      const k = keyOf(m)
      let g = map.get(k)
      if (!g) { g = { key: k, total: 0, risc: 0, phases: {} }; map.set(k, g) }
      g.total++
      g.phases[m.fase_actual] = (g.phases[m.fase_actual] || 0) + 1
      if (m.data_objectiu && m.predicted_end && m.predicted_end > m.data_objectiu) g.risc++
    }
    return [...map.values()].sort((a, b) => b.total - a.total)
  }, [models, dim])   // eslint-disable-line react-hooks/exhaustive-deps

  if (models === null) return (
    <section><SectionHead icon="ti-briefcase" color="var(--gold)" title={t('planning.informes.cartera.title')} /><Center>{t('planning.loading')}</Center></section>
  )
  const dimLabel = DIMENSIONS.find(d => d[0] === dim)[1]
  return (
    <section>
      <SectionHead icon="ti-briefcase" color="var(--gold)" title={t('planning.informes.cartera.title')}
        subtitle={t('planning.informes.cartera.subtitle')}
        extra={
          <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center', marginLeft: 'auto' }}>
            {DIMENSIONS.map(([val, label]) => (
              <button key={val} type="button" onClick={() => setDim(val)} style={{
                ...ghostBtn, background: dim === val ? 'var(--gold)' : 'none',
                borderColor: dim === val ? 'var(--gold)' : 'var(--gray-l)', fontWeight: dim === val ? 600 : 400,
              }}>{label}</button>
            ))}
          </span>
        } />
      <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead><tr>
            <th style={thS}>{dimLabel}</th>
            <th style={numTh}>{t('planning.informes.cartera.total')}</th>
            {PHASES.map(p => <th key={p} style={numTh}>{phaseLabel(t, p)}</th>)}
            <th style={numTh}>{t('planning.informes.cartera.en_risc')}</th>
          </tr></thead>
          <tbody>
            {groups.map(g => (
              <tr key={g.key}>
                <td style={{ ...tdS, fontFamily: MONO }}>{g.key}</td>
                <td style={{ ...numTd, fontWeight: 600 }}>{g.total}</td>
                {PHASES.map(p => <td key={p} style={{ ...numTd, color: g.phases[p] ? 'var(--text-main)' : 'var(--gray-l)' }}>{g.phases[p] || '·'}</td>)}
                <td style={{ ...numTd, color: g.risc ? 'var(--err)' : 'var(--gray-l)', fontWeight: g.risc ? 600 : 400 }}>{g.risc || '·'}</td>
              </tr>
            ))}
            {groups.length === 0 && <tr><td colSpan={PHASES.length + 3} style={{ ...tdS, textAlign: 'center', color: 'var(--text-muted)' }}>{t('planning.informes.cartera.empty')}</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  )
}

// ── PRODUCTIVITAT ─────────────────────────────────────────────────────────
// Temps REAL (timers consolidats) vs ESTIMAT (snapshot) per fase, sumat sobre tots els models.
// Reusa time-analysis/by-model/ (P1) — que ja porta est/real per fase de cada model — i l'agrega.
function ProductivityBlock({ t }) {
  const [tree, setTree] = useState(null)
  useEffect(() => {
    let alive = true
    timeAnalysis.byModel({}).then(res => { if (alive) setTree(res.data?.models || []) }).catch(() => { if (alive) setTree([]) })
    return () => { alive = false }
  }, [])

  const rows = useMemo(() => {
    const acc = new Map()
    for (const mod of (tree || []))
      for (const ph of (mod.fases || [])) {
        let a = acc.get(ph.fase)
        if (!a) { a = { fase: ph.fase, est: 0, real: 0, n: 0 }; acc.set(ph.fase, a) }
        a.est += ph.est || 0; a.real += ph.real || 0; a.n += ph.n || 0
      }
    const order = Object.keys(FASE_KEY)
    return [...acc.values()].sort((a, b) => order.indexOf(a.fase) - order.indexOf(b.fase))
  }, [tree])

  const totals = useMemo(() => rows.reduce((s, r) => ({ est: s.est + r.est, real: s.real + r.real, n: s.n + r.n }), { est: 0, real: 0, n: 0 }), [rows])

  if (tree === null) return (
    <section><SectionHead icon="ti-gauge" color="var(--gold)" title={t('planning.informes.productivity.title')} /><Center>{t('planning.loading')}</Center></section>
  )
  const faseLabel = (f) => t(`planning.time.phase.${FASE_KEY[f] || 'other'}`, { defaultValue: f })
  return (
    <section>
      <SectionHead icon="ti-gauge" color="var(--gold)" title={t('planning.informes.productivity.title')}
        subtitle={t('planning.informes.productivity.subtitle')} />
      <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
        <table style={{ borderCollapse: 'collapse', width: '100%' }}>
          <thead><tr>
            <th style={thS}>{t('planning.time.tree.by_phase')}</th>
            <th style={numTh}>{t('planning.informes.productivity.estimate')}</th>
            <th style={numTh}>{t('planning.informes.productivity.real')}</th>
            <th style={numTh}>{t('planning.informes.productivity.deviation')}</th>
            <th style={numTh}>{t('planning.informes.productivity.tasks')}</th>
          </tr></thead>
          <tbody>
            {rows.map(r => {
              const dev = (r.est && r.real) ? r.real - r.est : null
              const pct = (r.est && r.real) ? Math.round((r.real - r.est) / r.est * 100) : null
              return (
                <tr key={r.fase}>
                  <td style={{ ...tdS, fontFamily: MONO }}>{faseLabel(r.fase)}</td>
                  <td style={numTd}>{fmtMins(r.est)}</td>
                  <td style={numTd}>{fmtMins(r.real)}</td>
                  <td style={{ ...numTd, color: dev > 0 ? 'var(--err)' : dev < 0 ? 'var(--ok)' : 'inherit' }}>
                    {dev != null ? `${dev > 0 ? '+' : ''}${fmtMins(Math.abs(dev))}${pct != null ? ` (${pct > 0 ? '+' : ''}${pct}%)` : ''}` : '—'}
                  </td>
                  <td style={numTd}>{r.n}</td>
                </tr>
              )
            })}
            {rows.length === 0
              ? <tr><td colSpan={5} style={{ ...tdS, textAlign: 'center', color: 'var(--text-muted)' }}>{t('planning.informes.productivity.empty')}</td></tr>
              : (
                <tr style={{ background: 'var(--bg-muted)' }}>
                  <td style={{ ...tdS, fontFamily: MONO, fontWeight: 600 }}>{t('planning.informes.productivity.total')}</td>
                  <td style={{ ...numTd, fontWeight: 600 }}>{fmtMins(totals.est)}</td>
                  <td style={{ ...numTd, fontWeight: 600 }}>{fmtMins(totals.real)}</td>
                  <td style={numTd}>{(totals.est && totals.real) ? `${totals.real - totals.est > 0 ? '+' : ''}${fmtMins(Math.abs(totals.real - totals.est))}` : '—'}</td>
                  <td style={{ ...numTd, fontWeight: 600 }}>{totals.n}</td>
                </tr>
              )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
