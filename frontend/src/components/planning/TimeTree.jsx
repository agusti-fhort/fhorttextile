import { useState, useEffect, useMemo, useCallback } from 'react'
import { timeAnalysis } from '../../api/endpoints'
import { taskTypeLabel } from '../../utils/taskType'
import Center from '../ui/Center'
import Feedback from '../ui/Feedback'

// Arbre consultiu de temps (GET time-analysis/tree/): root (fase | tipus de peça) → task_type → item.
// Cada fulla: estimat (seed) vs real (mean) vs n vs desviació vs maduresa. CONSULTIU per defecte;
// només les cel·les None són editables (captura-PM: POST time-analysis/set-estimate/, graó 4 cascada).
const MONO = 'IBM Plex Mono, monospace'
const FASE_KEY = {
  'Disseny': 'disseny', 'Dev. tècnic': 'dev_tecnic', 'Prototip': 'prototip',
  'Mostres': 'mostres', 'Preproducció': 'preproduccio', 'Producció': 'produccio',
}
const MAT_DOT = { empiric: 'var(--ok)', seed: 'var(--gold)', none: 'var(--gray-l)', empty: 'var(--gray-l)' }

function fmtMins(m) {
  if (m == null) return '—'
  const h = Math.floor(m / 60), mm = m % 60
  return h ? (mm ? `${h}h ${mm}m` : `${h}h`) : `${mm}m`
}

// Mètriques de node a partir de les fulles (mirall del rollup ponderat del backend: pes n|1).
function nodeMetrics(items) {
  let wsum = 0, w = 0, emp = 0, seed = 0
  for (const it of items) {
    if (it.maturity === 'empiric') emp++
    else if (it.maturity === 'seed') seed++
    if (it.effective_minutes != null) {
      const ww = it.maturity === 'empiric' ? (it.n || 1) : 1
      wsum += it.effective_minutes * ww; w += ww
    }
  }
  return { minutes: w > 0 ? Math.round(wsum / w) : null,
           maturity: emp > 0 ? 'empiric' : (seed > 0 ? 'seed' : 'empty'),
           count: items.length }
}

const thS = {
  fontFamily: MONO, fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-muted)', textAlign: 'left',
  padding: '6px 10px', textTransform: 'uppercase', letterSpacing: '.04em', whiteSpace: 'nowrap',
}
const tdS = { padding: '6px 10px', fontSize: 'var(--fs-body)', verticalAlign: 'middle' }
const ghostBtn = {
  background: 'none', border: '0.5px solid var(--gray-l)', borderRadius: 6, cursor: 'pointer',
  padding: '3px 10px', fontSize: 'var(--fs-label)', fontFamily: MONO, color: 'var(--text-main)',
}

function MatDot({ m }) {
  return <span style={{ width: 7, height: 7, borderRadius: '50%', background: MAT_DOT[m] || 'var(--gray-l)', display: 'inline-block', flexShrink: 0 }} />
}

export default function TimeTree({ t }) {
  const [axis, setAxis] = useState('fase')   // 'fase' | 'garment_type' | 'model'
  const [phases, setPhases] = useState([])
  const [modelTree, setModelTree] = useState([])   // eix MODEL: [{label,nom,est,real,n,fases:[...]}]
  const [loading, setLoading] = useState(true)
  const [loadingModels, setLoadingModels] = useState(false)
  const [modelsLoaded, setModelsLoaded] = useState(false)
  const [expanded, setExpanded] = useState(() => new Set())
  const [editing, setEditing] = useState(null)   // `${gti}:${code}`
  const [editVal, setEditVal] = useState('')
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    return timeAnalysis.tree({})
      .then(res => setPhases(res.data?.phases || []))
      .catch(() => setFeedback({ type: 'err', text: t('planning.time.tree.error') }))
      .finally(() => setLoading(false))
  }, [t])
  useEffect(() => { load() }, [load])

  // Eix MODEL — substrat propi (ModelTask→fase→task_type; TaskTimeEstimate no té model). Es carrega
  // mandrós: només el primer cop que l'usuari selecciona l'eix "Model" (evita el cost si no s'usa).
  useEffect(() => {
    if (axis !== 'model' || modelsLoaded) return
    setLoadingModels(true)
    timeAnalysis.byModel({})
      .then(res => { setModelTree(res.data?.models || []); setModelsLoaded(true) })
      .catch(() => setFeedback({ type: 'err', text: t('planning.time.tree.error') }))
      .finally(() => setLoadingModels(false))
  }, [axis, modelsLoaded, t])

  // Aplana totes les fulles, conservant fase + task_type d'origen.
  const allItems = useMemo(() => {
    const out = []
    for (const ph of phases)
      for (const tt of (ph.task_types || []))
        for (const it of (tt.items || []))
          out.push({ ...it, fase: ph.fase, tt_code: tt.code, tt_name: tt.name })
    return out
  }, [phases])

  // Construeix l'arbre segons l'eix: root → task_type → items.
  const groups = useMemo(() => {
    const roots = new Map()
    for (const it of allItems) {
      const [rk, rlabel] = axis === 'garment_type'
        ? [it.garment_type_id ?? '∅', it.garment_type_nom || '—']
        : [it.fase, t(`planning.time.phase.${FASE_KEY[it.fase] || 'other'}`, { defaultValue: it.fase })]
      let root = roots.get(rk)
      if (!root) { root = { key: String(rk), label: rlabel, tts: new Map() }; roots.set(rk, root) }
      let tt = root.tts.get(it.tt_code)
      if (!tt) { tt = { code: it.tt_code, name: it.tt_name, items: [] }; root.tts.set(it.tt_code, tt) }
      tt.items.push(it)
    }
    return [...roots.values()].map(r => ({
      key: r.key, label: r.label,
      metrics: nodeMetrics([...r.tts.values()].flatMap(x => x.items)),
      taskTypes: [...r.tts.values()]
        .map(tt => ({ ...tt, metrics: nodeMetrics(tt.items) }))
        .sort((a, b) => a.code.localeCompare(b.code)),
    })).sort((a, b) => a.label.localeCompare(b.label))
  }, [allItems, axis, t])

  const toggle = (k) => setExpanded(s => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n })

  const startEdit = (it) => { setEditing(`${it.garment_type_item_id}:${it.tt_code}`); setEditVal('') }
  const saveEdit = (it) => {
    const minutes = parseInt(editVal, 10)
    if (!minutes || minutes <= 0) { setFeedback({ type: 'err', text: t('planning.time.tree.invalid') }); return }
    setSaving(true); setFeedback(null)
    timeAnalysis.setEstimate({ garment_type_item: it.garment_type_item_id, task_type: it.tt_code, minutes })
      .then(() => { setEditing(null); setFeedback({ type: 'ok', text: t('planning.time.tree.saved_ok') }); return load() })
      .catch(e => setFeedback({ type: 'err', text: e?.response?.data?.error || t('planning.time.tree.error') }))
      .finally(() => setSaving(false))
  }

  if (loading) return <Center>{t('planning.loading')}</Center>

  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', fontFamily: MONO, textTransform: 'uppercase', letterSpacing: '.04em' }}>
          {t('planning.time.tree.group_by')}
        </span>
        {[['fase', 'by_phase'], ['garment_type', 'by_garment'], ['model', 'by_model']].map(([val, key]) => (
          <button key={val} type="button" onClick={() => setAxis(val)} style={{
            ...ghostBtn, background: axis === val ? 'var(--gold)' : 'none',
            color: axis === val ? 'var(--text-main)' : 'var(--text-main)',
            borderColor: axis === val ? 'var(--gold)' : 'var(--gray-l)',
            fontWeight: axis === val ? 600 : 400,
          }}>{t(`planning.time.tree.${key}`)}</button>
        ))}
      </div>

      <Feedback feedback={feedback} />

      {axis === 'model'
        ? <ModelAxisTree tree={modelTree} loading={loadingModels} expanded={expanded} toggle={toggle} t={t} />
        : groups.length === 0
        ? <div style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)', border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)' }}>{t('planning.time.tree.empty')}</div>
        : (
          <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflow: 'hidden' }}>
            {groups.map(root => {
              const rk = `r:${axis}:${root.key}`
              const rOpen = expanded.has(rk)
              return (
                <div key={rk} style={{ borderBottom: '0.5px solid var(--gray-l)' }}>
                  <Row onClick={() => toggle(rk)} open={rOpen} depth={0}
                       label={root.label} m={root.metrics.maturity} t={t}
                       minutes={root.metrics.minutes} count={root.metrics.count} />
                  {rOpen && root.taskTypes.map(tt => {
                    const tk = `${rk}/${tt.code}`
                    const tOpen = expanded.has(tk)
                    return (
                      <div key={tk}>
                        <Row onClick={() => toggle(tk)} open={tOpen} depth={1}
                             label={taskTypeLabel(t, tt.code, tt.name)} m={tt.metrics.maturity} t={t}
                             minutes={tt.metrics.minutes} count={tt.metrics.count} />
                        {tOpen && (
                          <div style={{ background: 'var(--bg-muted)', padding: '4px 0' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                              <thead><tr>
                                <th style={{ ...thS, paddingLeft: 48 }}>{t('planning.time.tree.col_item')}</th>
                                <th style={thS}>{t('planning.time.tree.col_estimate')}</th>
                                <th style={thS}>{t('planning.time.tree.col_real')}</th>
                                <th style={thS}>{t('planning.time.tree.col_n')}</th>
                                <th style={thS}>{t('planning.time.tree.col_deviation')}</th>
                                <th style={thS}></th>
                              </tr></thead>
                              <tbody>
                                {tt.items.map(it => {
                                  const ek = `${it.garment_type_item_id}:${it.tt_code}`
                                  return (
                                    <tr key={ek} style={{ borderTop: '0.5px solid var(--gray-l)' }}>
                                      <td style={{ ...tdS, paddingLeft: 48, fontFamily: MONO }}>
                                        <MatDot m={it.maturity} />{' '}{it.item_nom || `#${it.garment_type_item_id}`}
                                        {axis === 'fase' && it.garment_type_nom &&
                                          <span style={{ color: 'var(--text-muted)' }}> · {it.garment_type_nom}</span>}
                                      </td>
                                      <td style={tdS}>{it.estimated_minutes != null ? fmtMins(it.estimated_minutes) : '—'}</td>
                                      <td style={tdS}>{it.mean_minutes != null ? fmtMins(it.mean_minutes) : '—'}</td>
                                      <td style={tdS}>{it.n || 0}</td>
                                      <td style={{ ...tdS, color: it.desviacio_min > 0 ? 'var(--err)' : (it.desviacio_min < 0 ? 'var(--ok)' : 'inherit') }}>
                                        {it.desviacio_min != null
                                          ? `${it.desviacio_min > 0 ? '+' : ''}${fmtMins(Math.abs(it.desviacio_min))}${it.desviacio_pct != null ? ` (${it.desviacio_pct > 0 ? '+' : ''}${it.desviacio_pct}%)` : ''}`
                                          : '—'}
                                      </td>
                                      <td style={tdS}>
                                        {it.maturity === 'none' && (
                                          editing === ek ? (
                                            <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
                                              <input type="number" min="1" value={editVal} autoFocus
                                                     onChange={e => setEditVal(e.target.value)}
                                                     placeholder={t('planning.time.tree.minutes_ph')}
                                                     style={{ width: 70, padding: '2px 6px', fontFamily: MONO, fontSize: 'var(--fs-label)', border: '0.5px solid var(--gray-l)', borderRadius: 6 }} />
                                              <button onClick={() => saveEdit(it)} disabled={saving} style={{ ...ghostBtn, borderColor: 'var(--gold)' }}>{t('planning.time.tree.save')}</button>
                                              <button onClick={() => setEditing(null)} disabled={saving} style={ghostBtn}>{t('planning.time.tree.cancel')}</button>
                                            </span>
                                          ) : (
                                            <button onClick={() => startEdit(it)} style={ghostBtn}>
                                              <i className="ti ti-plus" style={{ fontSize: 12, marginRight: 3 }} />{t('planning.time.tree.set_estimate')}
                                            </button>
                                          )
                                        )}
                                      </td>
                                    </tr>
                                  )
                                })}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        )}
    </div>
  )
}

// Maduresa d'un node de l'eix MODEL: empíric si hi ha real consolidat, seed si només estimació.
const modelMaturity = (real, est) => (real > 0 ? 'empiric' : (est > 0 ? 'seed' : 'empty'))

// Eix MODEL — arbre model → fase → task_type. A diferència dels eixos fase/tipus-de-peça (que
// reagrupen les MATEIXES cel·les de TaskTimeEstimate), aquí la font és ModelTask: estimat = snapshot
// per tasca, real = Sum(timers). Per tant les fulles són task_types (un per model+fase), sense edició
// de seed (la captura-PM viu a l'eix tècnic). Reusa Row/MatDot/fmtMins.
function ModelAxisTree({ tree, loading, expanded, toggle, t }) {
  if (loading) return <Center>{t('planning.loading')}</Center>
  if (!tree.length) return (
    <div style={{ padding: '1.25rem', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--fs-body)', border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)' }}>
      {t('planning.time.tree.empty')}
    </div>
  )
  return (
    <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflow: 'hidden' }}>
      {tree.map(mod => {
        const mk = `m:${mod.model_id}`
        const mOpen = expanded.has(mk)
        return (
          <div key={mk} style={{ borderBottom: '0.5px solid var(--gray-l)' }}>
            <Row onClick={() => toggle(mk)} open={mOpen} depth={0} t={t}
                 label={`${mod.label}${mod.nom ? ` · ${mod.nom}` : ''}`}
                 m={modelMaturity(mod.real, mod.est)} minutes={mod.real || mod.est} count={mod.n} />
            {mOpen && (mod.fases || []).map(ph => {
              const fk = `${mk}/${ph.fase}`
              const fOpen = expanded.has(fk)
              return (
                <div key={fk}>
                  <Row onClick={() => toggle(fk)} open={fOpen} depth={1} t={t}
                       label={t(`planning.time.phase.${FASE_KEY[ph.fase] || 'other'}`, { defaultValue: ph.fase })}
                       m={modelMaturity(ph.real, ph.est)} minutes={ph.real || ph.est} count={ph.n} />
                  {fOpen && (
                    <div style={{ background: 'var(--bg-muted)', padding: '4px 0' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                        <thead><tr>
                          <th style={{ ...thS, paddingLeft: 48 }}>{t('planning.time.tree.col_task')}</th>
                          <th style={thS}>{t('planning.time.tree.col_estimate')}</th>
                          <th style={thS}>{t('planning.time.tree.col_real')}</th>
                          <th style={thS}>{t('planning.time.tree.col_deviation')}</th>
                        </tr></thead>
                        <tbody>
                          {(ph.tasks || []).map(tk => (
                            <tr key={tk.task_type_code} style={{ borderTop: '0.5px solid var(--gray-l)' }}>
                              <td style={{ ...tdS, paddingLeft: 48, fontFamily: MONO }}>
                                <MatDot m={tk.maturity} />{' '}{taskTypeLabel(t, tk.task_type_code, tk.task_type_name)}
                              </td>
                              <td style={tdS}>{tk.estimated_minutes != null ? fmtMins(tk.estimated_minutes) : '—'}</td>
                              <td style={tdS}>{tk.real_minutes != null ? fmtMins(tk.real_minutes) : '—'}</td>
                              <td style={{ ...tdS, color: tk.desviacio_min > 0 ? 'var(--err)' : (tk.desviacio_min < 0 ? 'var(--ok)' : 'inherit') }}>
                                {tk.desviacio_min != null
                                  ? `${tk.desviacio_min > 0 ? '+' : ''}${fmtMins(Math.abs(tk.desviacio_min))}${tk.desviacio_pct != null ? ` (${tk.desviacio_pct > 0 ? '+' : ''}${tk.desviacio_pct}%)` : ''}`
                                  : '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

// Fila d'un node expandible (root o task_type): chevron + etiqueta + temps + maduresa + recompte.
function Row({ onClick, open, depth, label, minutes, m, count, t }) {
  return (
    <div onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer',
      padding: '8px 12px', paddingLeft: 12 + depth * 24,
      background: depth === 0 ? 'var(--white)' : 'var(--bg-muted)',
    }}>
      <i className={`ti ti-chevron-${open ? 'down' : 'right'}`} style={{ fontSize: 14, color: 'var(--text-muted)' }} />
      <MatDot m={m} />
      <span style={{ fontFamily: MONO, fontWeight: depth === 0 ? 600 : 500, fontSize: 'var(--fs-body)' }}>{label}</span>
      <span style={{ marginLeft: 'auto', fontFamily: MONO, fontWeight: 600, fontSize: 'var(--fs-body)', color: minutes != null ? 'var(--text-main)' : 'var(--text-muted)' }}>
        {fmtMins(minutes)}
      </span>
      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>
        {t('planning.time.tree.cells_n', { n: count })}
      </span>
    </div>
  )
}
