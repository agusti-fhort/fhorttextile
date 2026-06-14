import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { sizeMap } from '../api/endpoints'
import Center from '../components/ui/Center'
import Feedback from '../components/ui/Feedback'
import Table from '../components/ui/Table'
import Badge from '../components/ui/Badge'
import { selS, primaryBtn } from '../components/ui/buttons'

// Size Map Setup — wizard de 5 passos per derivar un SizeSystem (+GradingRuleSet +SizingProfiles)
// a partir d'una taula de mides de client, i mode llista dels sistemes existents.
// Backend: pom/size_map_views.py (gated CONFIGURE). Patró visual: TaskTypes.jsx (Peça 0).
const MONO = 'IBM Plex Mono, monospace'

const BASE_UNITS = ['ALPHA', 'NUMERIC_EU', 'NUMERIC_US', 'CM_HEIGHT', 'MONTHS', 'AGE_YEARS']
const LOGICA = ['LINEAR', 'STEP', 'FIXED', 'ZERO']
const REC_VARIANT = { REUTILITZAR: 'ok', CLONAR: 'gold', CREAR: 'gate' }

const STEPS = [
  { n: 1, key: 'size_map_step_target' },
  { n: 2, key: 'size_map_step_match' },
  { n: 3, key: 'size_map_step_talles' },
  { n: 4, key: 'size_map_step_grading' },
  { n: 5, key: 'size_map_step_perfils' },
]

const card = { border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', padding: 16, marginBottom: 14 }
const ghostBtn = { ...selS, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }

function Field({ label, children, hint }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ fontSize: 11, fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
      {hint && <div style={{ fontSize: 10, color: 'var(--gray)', marginTop: 4 }}>{hint}</div>}
    </div>
  )
}

// Llegeix ?prefill= de la URL (base64 unicode-safe d'un JSON) → objecte, o null.
function readPrefill() {
  try {
    const p = new URLSearchParams(window.location.search).get('prefill')
    if (!p) return null
    return JSON.parse(decodeURIComponent(escape(atob(p))))
  } catch { return null }
}

// Parse d'una taula enganxada des d'Excel (tab) o CSV: 1a fila = capçalera (POM | talles...).
function parseTable(text) {
  const lines = (text || '').trim().split(/\r?\n/).filter(l => l.trim())
  if (lines.length < 2) return { sizeLabels: [], taula: [] }
  const split = (l) => l.split(/\t|,|;/).map(c => c.trim())
  const header = split(lines[0])
  const sizeLabels = header.slice(1).filter(Boolean)
  const taula = lines.slice(1).map(l => {
    const cells = split(l)
    const valors = {}
    sizeLabels.forEach((lbl, i) => {
      const v = cells[i + 1]
      if (v !== undefined && v !== '') {
        const num = parseFloat(v.replace(',', '.'))
        if (!isNaN(num)) valors[lbl] = num
      }
    })
    return { pom_codi_client: cells[0], valors }
  }).filter(r => r.pom_codi_client)
  return { sizeLabels, taula }
}

export default function SizeMapSetup() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const me = useAuthStore(s => s.user)
  const canConfigure = !!me?.capabilities?.includes('configure')

  // Si venim del W1 amb ?prefill=, obrim el wizard directament pre-omplert.
  const [prefill] = useState(readPrefill)
  const [wizardOpen, setWizardOpen] = useState(!!prefill)
  const [feedback, setFeedback] = useState(null)

  // ---- Mode llista ----
  const [systems, setSystems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const loadSystems = useCallback(() => {
    setError(false)
    return sizeMap.systems()
      .then(r => setSystems(r.data?.results ?? []))
      .catch(() => setError(true))
  }, [])

  useEffect(() => {
    let alive = true
    sizeMap.systems()
      .then(r => { if (alive) setSystems(r.data?.results ?? []) })
      .catch(() => { if (alive) setError(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  if (!canConfigure) {
    return <Center>{t('size_map_no_access', 'No tens permís per configurar sistemes de talles.')}</Center>
  }

  if (wizardOpen) {
    return (
      <Wizard t={t} prefill={prefill}
        onClose={() => setWizardOpen(false)}
        onComplete={(data) => {
          // Branch de tornada preservat IDÈNTIC (ruta vella): si venim del W1, tornem a
          // la fitxa en curs (pas mesures); si no, mode llista + feedback amb warnings.
          if (prefill?.import_session_token && prefill?.model_id) {
            navigate(`/models/${prefill.model_id}/mesures?session=${prefill.import_session_token}`)
            return
          }
          setWizardOpen(false)
          const w = data?.warnings || []
          const base = t('size_map_created', 'Sistema creat') + `: ${data?.codi} — ${data?.nom}`
          loadSystems().then(() => setFeedback({ type: 'ok', text: w.length ? `${base} (${w.length} ${t('size_map_warnings', 'avisos')})` : base }))
        }}
      />
    )
  }

  const columns = [
    { key: 'nom', label: t('size_map_col_nom', 'Nom'),
      render: r => <span style={{ fontWeight: 500 }}>{r.nom}</span> },
    { key: 'codi', label: t('size_map_col_codi', 'Codi'),
      render: r => <span style={{ fontFamily: MONO }}>{r.codi}</span> },
    { key: 'target_nom', label: t('size_map_col_target', 'Target'), render: r => r.target_nom || '—' },
    { key: 'base_unit', label: t('size_map_col_unit', 'Unitat'),
      render: r => <span style={{ fontFamily: MONO, fontSize: 11 }}>{r.base_unit || '—'}</span> },
    { key: 'customer_codi', label: t('size_map_col_client', 'Client'),
      render: r => r.customer_codi
        ? <Badge variant="gold">{r.customer_codi}</Badge>
        : <span style={{ color: 'var(--gray)' }}>{t('size_map_canonical', 'Canònic')}</span> },
    { key: 'parent_codi', label: t('size_map_col_parent', 'Pare'),
      render: r => r.parent_codi ? <span style={{ fontFamily: MONO, fontSize: 11 }}>{r.parent_codi}</span> : '—' },
    { key: 'num_talles', label: t('size_map_col_talles', 'Talles'), align: 'right',
      render: r => <span style={{ fontFamily: MONO }}>{r.num_talles}</span> },
    { key: 'num_rule_sets', label: t('size_map_col_rules', 'Rule sets'), align: 'right',
      render: r => <span style={{ fontFamily: MONO }}>{r.num_rule_sets}</span> },
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1100 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('size_map_title', 'Sistemes de talles')}</h1>
          <p style={{ fontSize: 12, color: 'var(--gray)', fontWeight: 300 }}>{t('size_map_subtitle', 'Runs de client derivats i sistemes canònics')}</p>
        </div>
        <button onClick={() => setWizardOpen(true)} style={{ ...primaryBtn, marginLeft: 0 }}>
          <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('size_map_new_run', 'Nou run de client')}
        </button>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('size_map_loading', 'Carregant…')}</Center>
        : error ? <Center>{t('size_map_error', 'Error en carregar els sistemes.')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={systems} loading={false} empty={t('size_map_empty', 'Cap sistema de talles encara.')} />
            </div>
          )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// WIZARD
// ─────────────────────────────────────────────────────────────────────────────
function Stepper({ step, t }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 18, overflowX: 'auto' }}>
      {STEPS.map((s, i) => {
        const done = s.n < step, active = s.n === step
        return (
          <div key={s.n} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 10px' }}>
              <span style={{
                width: 22, height: 22, borderRadius: 999, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 11, fontFamily: MONO, fontWeight: 600,
                background: active ? 'var(--gold)' : done ? 'var(--gold-pale)' : 'var(--gray-l)',
                color: active ? '#fff' : done ? 'var(--gold)' : 'var(--gray)',
              }}>{s.n}</span>
              <span style={{ fontSize: 11.5, fontFamily: MONO, color: active ? 'var(--text-main)' : 'var(--gray)', fontWeight: active ? 600 : 400 }}>
                {t(s.key)}
              </span>
            </div>
            {i < STEPS.length - 1 && <i className="ti ti-chevron-right" style={{ fontSize: 13, color: 'var(--gray-l)' }} />}
          </div>
        )
      })}
    </div>
  )
}

export function Wizard({ t, prefill = null, onComplete, onClose }) {
  const [step, setStep] = useState(1)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  // 1C-4b-fe1 — panell d'avís-i-confirma quan el backend retorna 409 {existing, message}.
  const [conflict, setConflict] = useState(null)
  const [lookups, setLookups] = useState({ targets: [], constructions: [], fit_types: [], garment_types: [], base_units: [] })

  // Estat global del wizard en un sol objecte.
  const [wiz, setWiz] = useState({
    target_codi: '', base_unit: 'ALPHA', customer_codi: '', labelsText: '', base_size: '',
    candidates: [], recomanacio: '', decision: '', size_system_id: null,
    talles: [],
    gradingText: '', gradingResults: [], gradingRun: [],
    perfilTargets: [], construction_id: '', fit_type_id: '', garment_type_id: '',
    nom_custom: '', nom_variant: '',
  })
  const set = (patch) => setWiz(w => ({ ...w, ...patch }))

  // Pre-omplir des del W1 (gating PENDENT): target, etiquetes i talla base.
  useEffect(() => {
    if (!prefill) return
    set({
      target_codi: prefill.target_codi || '',
      labelsText: (prefill.labels || []).join('\n'),
      base_size: prefill.base_size || '',
    })
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    sizeMap.lookups().then(r => {
      setLookups(r.data || {})
    }).catch(() => {})
  }, [])

  const labels = () => wiz.labelsText.split(/\r?\n/).map(s => s.trim()).filter(Boolean)

  // P1 → match
  const goMatch = () => {
    setErr(null); setBusy(true)
    sizeMap.match({ target_codi: wiz.target_codi, labels: labels(), base_size: wiz.base_size })
      .then(r => {
        const rec = r.data?.recomanacio || 'CREAR'
        const cands = r.data?.candidates || []
        set({
          candidates: cands, recomanacio: rec, decision: rec,
          size_system_id: rec !== 'CREAR' && cands[0] ? cands[0].size_system_id : null,
        })
        setStep(2)
      })
      .catch(e => setErr(e?.response?.data?.error || t('size_map_match_err', 'Error en el matching.')))
      .finally(() => setBusy(false))
  }

  // P2 → preview
  const goPreview = () => {
    setErr(null); setBusy(true)
    const inputLabels = labels().map((et, i) => ({ etiqueta: et, ordre: i + 1 }))
    sizeMap.preview({ accio: wiz.decision, size_system_id: wiz.size_system_id, labels: inputLabels })
      .then(r => {
        const defs = (r.data?.size_definitions || []).map((d, i) => ({
          etiqueta: d.etiqueta, ordre: d.ordre ?? i + 1,
          valor_numeric: d.valor_numeric ?? '', age_months_min: d.age_months_min ?? '',
          age_months_max: d.age_months_max ?? '', body_height_cm: d.body_height_cm ?? '',
        }))
        set({ talles: defs })
        setStep(3)
      })
      .catch(e => setErr(e?.response?.data?.error || t('size_map_preview_err', 'Error en la previsualització.')))
      .finally(() => setBusy(false))
  }

  // P4 → grading preview
  const calcGrading = () => {
    setErr(null); setBusy(true)
    const { taula } = parseTable(wiz.gradingText)
    sizeMap.gradingPreview({ size_system_id: wiz.size_system_id, base_size: wiz.base_size, taula })
      .then(r => {
        const results = (r.data?.results || []).map(x => ({
          ...x, logica: x.logica_detectada || 'LINEAR',
          increment: x.increment ?? 0,
          valors_step_text: x.valors_step ? JSON.stringify(x.valors_step) : '',
        }))
        set({ gradingResults: results, gradingRun: r.data?.run || [] })
      })
      .catch(e => setErr(e?.response?.data?.error || t('size_map_grading_err', 'Error en el càlcul de grading.')))
      .finally(() => setBusy(false))
  }

  // P5 → create. buildPayload accepta overrides {on_conflict, nom_variant} per re-cridar
  // des del panell de conflicte (avís-i-confirma).
  const buildPayload = (extra = {}) => {
    const grading = wiz.gradingResults
      .filter(g => g.pom_id)
      .map(g => {
        const row = { pom_id: g.pom_id, logica: g.logica }
        if (g.logica === 'STEP') {
          try { row.valors_step = g.valors_step_text ? JSON.parse(g.valors_step_text) : (g.valors_step || {}) } catch { row.valors_step = g.valors_step || {} }
        } else {
          row.increment = Number(g.increment) || 0
        }
        return row
      })
    const perfils = wiz.perfilTargets.map(tc => ({
      target_codi: tc,
      construction_id: wiz.construction_id || null,
      fit_type_id: wiz.fit_type_id || null,
      garment_type_id: wiz.garment_type_id || null,
    }))
    return {
      customer_codi: wiz.customer_codi, nom_custom: wiz.nom_custom || undefined,
      nom_variant: wiz.nom_variant || undefined,
      accio: wiz.decision, size_system_id: wiz.size_system_id,
      target_codi: wiz.target_codi, base_unit: wiz.base_unit, base_size: wiz.base_size,
      talles: wiz.talles.map((x, i) => ({
        etiqueta: x.etiqueta, ordre: Number(x.ordre) || i + 1,
        valor_numeric: x.valor_numeric === '' ? null : Number(x.valor_numeric),
        age_months_min: x.age_months_min === '' ? null : Number(x.age_months_min),
        age_months_max: x.age_months_max === '' ? null : Number(x.age_months_max),
        body_height_cm: x.body_height_cm === '' ? null : Number(x.body_height_cm),
      })),
      grading, perfils,
      ...extra,   // on_conflict / nom_variant des del panell sobreescriuen
    }
  }

  const submitCreate = (extra = {}) => {
    setErr(null); setConflict(null); setBusy(true)
    sizeMap.create(buildPayload(extra))
      .then(r => { onComplete(r.data) })
      .catch(e => {
        // 409 = avís-i-confirma (no és error): obre el panell amb les graduacions existents.
        if (e?.response?.status === 409) { setConflict(e.response.data); return }
        setErr(e?.response?.data?.error || t('size_map_create_err', 'Error en crear el sistema.'))
      })
      .finally(() => setBusy(false))
  }

  const doCreate = () => submitCreate()

  const nomById = (arr, id) => arr.find(x => String(x.id) === String(id))?.nom || ''

  return (
    <div style={{ minWidth: 0, maxWidth: 1100 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, fontFamily: MONO }}>{t('size_map_new_run', 'Nou run de client')}</h1>
        <button onClick={onClose} style={ghostBtn}><i className="ti ti-x" style={{ fontSize: 13 }} />{t('size_map_cancel', 'Cancel·lar')}</button>
      </div>

      {prefill && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--gold-pale)', color: 'var(--gold)',
                      border: '0.5px solid var(--gold)', borderRadius: 8, padding: '8px 12px', marginBottom: 14, fontSize: 12 }}>
          <i className="ti ti-link" style={{ fontSize: 14 }} />
          {t('size_map_from_w1', 'Configures un run per a una fitxa en curs. En acabar tornaràs a la importació.')}
        </div>
      )}

      <Stepper step={step} t={t} />
      {err && <Feedback feedback={{ type: 'err', text: err }} onDismiss={() => setErr(null)} />}

      {/* ---- P1 ---- */}
      {step === 1 && (
        <div style={card}>
          <Field label={t('size_map_f_target', 'Target')}>
            <select value={wiz.target_codi} onChange={e => set({ target_codi: e.target.value })} style={{ ...selS, width: '100%' }}>
              <option value="">—</option>
              {lookups.targets.map(o => <option key={o.codi} value={o.codi}>{o.nom} ({o.codi})</option>)}
            </select>
          </Field>
          <Field label={t('size_map_f_unit', 'Unitat base')}>
            <select value={wiz.base_unit} onChange={e => set({ base_unit: e.target.value })} style={{ ...selS, width: '100%' }}>
              {(lookups.base_units?.length ? lookups.base_units.map(o => o.codi) : BASE_UNITS).map(u =>
                <option key={u} value={u}>{u}</option>)}
            </select>
          </Field>
          <Field label={t('size_map_f_customer', 'Codi client')} hint={t('size_map_f_customer_hint', '3 caràcters (Customer.codi)')}>
            <input value={wiz.customer_codi} maxLength={3} onChange={e => set({ customer_codi: e.target.value.toUpperCase() })}
              placeholder="ABC" style={{ ...selS, width: 120 }} />
          </Field>
          <Field label={t('size_map_f_labels', 'Etiquetes del run')} hint={t('size_map_f_labels_hint', 'Una per línia (XS, S, M, L, XL…)')}>
            <textarea value={wiz.labelsText} onChange={e => set({ labelsText: e.target.value })} rows={5}
              style={{ ...selS, width: '100%', resize: 'vertical' }} placeholder={'XS\nS\nM\nL\nXL'} />
          </Field>
          <Field label={t('size_map_f_base', 'Talla base')}>
            <input value={wiz.base_size} onChange={e => set({ base_size: e.target.value })} placeholder="M" style={{ ...selS, width: 120 }} />
          </Field>
          <button onClick={goMatch} disabled={busy || !wiz.target_codi || labels().length === 0 || !wiz.base_size}
            style={{ ...primaryBtn }}>{t('size_map_next', 'Següent')}</button>
        </div>
      )}

      {/* ---- P2 ---- */}
      {step === 2 && (
        <div style={card}>
          <div style={{ marginBottom: 12, fontSize: 12 }}>
            {t('size_map_reco', 'Recomanació')}: <Badge variant={REC_VARIANT[wiz.recomanacio] || 'gray'}>{wiz.recomanacio}</Badge>
          </div>
          {wiz.candidates.length === 0 && (
            <div style={{ fontSize: 12, color: 'var(--gray)', marginBottom: 12 }}>{t('size_map_no_candidates', 'Cap sistema existent encaixa. Es crearà un de nou.')}</div>
          )}
          {wiz.candidates.map(c => (
            <label key={c.size_system_id} style={{ display: 'block', border: '0.5px solid var(--gray-l)', borderRadius: 8, padding: 12, marginBottom: 8, cursor: 'pointer' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <input type="radio" name="cand" checked={wiz.decision !== 'CREAR' && String(wiz.size_system_id) === String(c.size_system_id)}
                  onChange={() => set({ size_system_id: c.size_system_id, decision: c.recomanacio === 'CREAR' ? 'CLONAR' : c.recomanacio })} />
                <span style={{ fontWeight: 600 }}>{c.nom}</span>
                <span style={{ fontFamily: MONO, fontSize: 11, color: 'var(--gray)' }}>{c.codi}</span>
                <Badge variant={c.score >= 1 ? 'ok' : 'warn'}>{Math.round((c.score || 0) * 100)}%</Badge>
                <Badge variant={REC_VARIANT[c.recomanacio] || 'gray'}>{c.recomanacio}</Badge>
              </div>
              {/* barra de score */}
              <div style={{ height: 6, background: 'var(--gray-l)', borderRadius: 999, marginTop: 8 }}>
                <div style={{ height: 6, width: `${Math.round((c.score || 0) * 100)}%`, background: 'var(--gold)', borderRadius: 999 }} />
              </div>
              {c.unmatched_labels?.length > 0 &&
                <div style={{ fontSize: 11, color: 'var(--warn)', marginTop: 6 }}>{t('size_map_unmatched', 'No reconegudes')}: {c.unmatched_labels.join(', ')}</div>}
              {c.warning && <div style={{ fontSize: 11, color: 'var(--gray)', marginTop: 4 }}>{c.warning}</div>}
            </label>
          ))}
          {/* opció crear nou */}
          <label style={{ display: 'flex', alignItems: 'center', gap: 10, border: '0.5px dashed var(--gray-l)', borderRadius: 8, padding: 12, marginBottom: 14, cursor: 'pointer' }}>
            <input type="radio" name="cand" checked={wiz.decision === 'CREAR'} onChange={() => set({ decision: 'CREAR', size_system_id: null })} />
            <span>{t('size_map_create_new', 'Crear sistema nou')}</span>
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setStep(1)} style={ghostBtn}>{t('size_map_back', 'Enrere')}</button>
            <button onClick={goPreview} disabled={busy || (wiz.decision !== 'CREAR' && !wiz.size_system_id)} style={primaryBtn}>{t('size_map_next', 'Següent')}</button>
          </div>
        </div>
      )}

      {/* ---- P3 ---- */}
      {step === 3 && (
        <div style={card}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 10 }}>
                  <th style={{ padding: 6 }}>{t('size_map_t_label', 'Etiqueta')}</th>
                  <th style={{ padding: 6 }}>{t('size_map_t_order', 'Ordre')}</th>
                  <th style={{ padding: 6 }}>{t('size_map_t_numeric', 'Valor num.')}</th>
                  <th style={{ padding: 6 }}>{t('size_map_t_mmin', 'Mesos mín')}</th>
                  <th style={{ padding: 6 }}>{t('size_map_t_mmax', 'Mesos màx')}</th>
                  <th style={{ padding: 6 }}>{t('size_map_t_height', 'Alçada cm')}</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {wiz.talles.map((row, i) => {
                  const isBase = row.etiqueta && wiz.base_size && row.etiqueta.trim().toUpperCase() === wiz.base_size.trim().toUpperCase()
                  const upd = (k, v) => set({ talles: wiz.talles.map((r, j) => j === i ? { ...r, [k]: v } : r) })
                  const cellInput = (k, w = 80, type = 'text') => (
                    <input type={type} value={row[k] ?? ''} onChange={e => upd(k, e.target.value)} style={{ ...selS, width: w, padding: '3px 6px' }} />
                  )
                  return (
                    <tr key={i} style={{ background: isBase ? 'var(--gold-pale)' : 'transparent', borderTop: '0.5px solid var(--gray-l)' }}>
                      <td style={{ padding: 4 }}>{cellInput('etiqueta', 90)}</td>
                      <td style={{ padding: 4 }}>{cellInput('ordre', 56, 'number')}</td>
                      <td style={{ padding: 4 }}>{cellInput('valor_numeric', 80, 'number')}</td>
                      <td style={{ padding: 4 }}>{cellInput('age_months_min', 70, 'number')}</td>
                      <td style={{ padding: 4 }}>{cellInput('age_months_max', 70, 'number')}</td>
                      <td style={{ padding: 4 }}>{cellInput('body_height_cm', 80, 'number')}</td>
                      <td style={{ padding: 4 }}>
                        <button onClick={() => set({ talles: wiz.talles.filter((_, j) => j !== i) })}
                          style={{ ...ghostBtn, color: 'var(--err)', borderColor: 'var(--err)', padding: '3px 7px' }}><i className="ti ti-trash" /></button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 12, marginBottom: 14 }}>
            <button onClick={() => set({ talles: [...wiz.talles, { etiqueta: '', ordre: wiz.talles.length + 1, valor_numeric: '', age_months_min: '', age_months_max: '', body_height_cm: '' }] })}
              style={ghostBtn}><i className="ti ti-plus" />{t('size_map_add_size', 'Afegir talla')}</button>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setStep(2)} style={ghostBtn}>{t('size_map_back', 'Enrere')}</button>
            <button onClick={() => setStep(4)} disabled={wiz.talles.length === 0} style={primaryBtn}>{t('size_map_next', 'Següent')}</button>
          </div>
        </div>
      )}

      {/* ---- P4 ---- */}
      {step === 4 && (
        <div style={card}>
          <Field label={t('size_map_g_paste', 'Taula de mides (enganxa des d\'Excel)')}
            hint={t('size_map_g_hint', 'Primera fila: POM seguit de les etiquetes. Tab / coma / punt i coma.')}>
            <textarea value={wiz.gradingText} onChange={e => set({ gradingText: e.target.value })} rows={6}
              style={{ ...selS, width: '100%', resize: 'vertical', fontFamily: MONO }}
              placeholder={'POM\tS\tM\tL\tXL\nCH\t46\t48\t50\t53'} />
          </Field>
          <button onClick={calcGrading} disabled={busy || !wiz.gradingText.trim()} style={{ ...primaryBtn, marginBottom: 14 }}>
            <i className="ti ti-calculator" />{t('size_map_calc', 'Calcular increments')}
          </button>

          {wiz.gradingResults.length > 0 && (
            <div style={{ overflowX: 'auto', marginBottom: 14 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                <thead>
                  <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 10 }}>
                    <th style={{ padding: 6 }}>POM</th>
                    <th style={{ padding: 6 }}>{t('size_map_g_logica', 'Lògica')}</th>
                    <th style={{ padding: 6 }}>{t('size_map_g_value', 'Increment / deltes')}</th>
                    <th style={{ padding: 6 }}>{t('size_map_g_warn', 'Avís')}</th>
                  </tr>
                </thead>
                <tbody>
                  {wiz.gradingResults.map((g, i) => {
                    const upd = (k, v) => set({ gradingResults: wiz.gradingResults.map((r, j) => j === i ? { ...r, [k]: v } : r) })
                    return (
                      <tr key={i} style={{ borderTop: '0.5px solid var(--gray-l)', background: g.pom_id ? 'transparent' : 'var(--warn-bg)' }}>
                        <td style={{ padding: 6 }}>
                          <div style={{ fontFamily: MONO }}>{g.pom_codi_client}</div>
                          {g.pom_nom && <div style={{ fontSize: 10, color: 'var(--gray)' }}>{g.pom_nom}</div>}
                        </td>
                        <td style={{ padding: 6 }}>
                          <select value={g.logica} onChange={e => upd('logica', e.target.value)} style={{ ...selS, padding: '3px 6px' }}>
                            {LOGICA.map(l => <option key={l} value={l}>{l}</option>)}
                          </select>
                        </td>
                        <td style={{ padding: 6 }}>
                          {g.logica === 'STEP'
                            ? <input value={g.valors_step_text} onChange={e => upd('valors_step_text', e.target.value)}
                                style={{ ...selS, width: 280, padding: '3px 6px', fontFamily: MONO }} placeholder='{"S":2,"L":2}' />
                            : <input type="number" value={g.increment} onChange={e => upd('increment', e.target.value)}
                                style={{ ...selS, width: 90, padding: '3px 6px' }} />}
                        </td>
                        <td style={{ padding: 6, color: 'var(--warn)', fontSize: 11 }}>{g.warning || ''}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setStep(3)} style={ghostBtn}>{t('size_map_back', 'Enrere')}</button>
            <button onClick={() => setStep(5)} style={primaryBtn}>{t('size_map_next', 'Següent')}</button>
          </div>
        </div>
      )}

      {/* ---- P5 ---- */}
      {step === 5 && (
        <div style={card}>
          <Field label={t('size_map_p_targets', 'Targets dels perfils')} hint={t('size_map_p_targets_hint', 'Es crea un perfil per cada target seleccionat')}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {lookups.targets.map(o => {
                const on = wiz.perfilTargets.includes(o.codi)
                return (
                  <button key={o.codi} onClick={() => set({ perfilTargets: on ? wiz.perfilTargets.filter(x => x !== o.codi) : [...wiz.perfilTargets, o.codi] })}
                    style={{ ...ghostBtn, background: on ? 'var(--gold-pale)' : 'var(--white)', color: on ? 'var(--gold)' : 'var(--text-main)', borderColor: on ? 'var(--gold)' : 'var(--gray-l)' }}>
                    {o.nom}
                  </button>
                )
              })}
            </div>
          </Field>
          <Field label={t('size_map_p_construction', 'Construcció')}>
            <select value={wiz.construction_id} onChange={e => set({ construction_id: e.target.value })} style={{ ...selS, width: '100%' }}>
              <option value="">—</option>
              {lookups.constructions.map(o => <option key={o.id} value={o.id}>{o.nom} ({o.codi})</option>)}
            </select>
          </Field>
          <Field label={t('size_map_p_fit', 'Fit type')}>
            <select value={wiz.fit_type_id} onChange={e => set({ fit_type_id: e.target.value })} style={{ ...selS, width: '100%' }}>
              <option value="">—</option>
              {lookups.fit_types.map(o => <option key={o.id} value={o.id}>{o.nom} ({o.codi})</option>)}
            </select>
          </Field>
          <Field label={t('size_map_p_garment', 'Garment type')}>
            <select value={wiz.garment_type_id} onChange={e => set({ garment_type_id: e.target.value })} style={{ ...selS, width: '100%' }}>
              <option value="">—</option>
              {lookups.garment_types.map(o => <option key={o.id} value={o.id}>{o.nom} ({o.codi})</option>)}
            </select>
          </Field>
          {wiz.decision === 'CREAR' && (
            <Field label={t('size_map_p_nom', 'Nom del sistema (opcional)')}>
              <input value={wiz.nom_custom} onChange={e => set({ nom_custom: e.target.value })} style={{ ...selS, width: '100%' }} />
            </Field>
          )}
          {wiz.decision === 'CREAR' && (
            <Field label={t('size_map_p_nom_variant', 'Nom de la graduació')}
              hint={t('size_map_p_nom_variant_hint', 'Ex: EU Knit Woman Slim — el nom que distingirà aquesta graduació')}>
              <input value={wiz.nom_variant} onChange={e => set({ nom_variant: e.target.value })}
                placeholder="EU Knit Woman Slim" style={{ ...selS, width: '100%' }} />
            </Field>
          )}

          {/* Resum */}
          <div style={{ background: 'var(--gray-l)', borderRadius: 8, padding: 12, marginBottom: 14, fontSize: 12, fontFamily: MONO }}>
            <div>{t('size_map_sum_action', 'Acció')}: <b>{wiz.decision}</b></div>
            <div>{t('size_map_sum_target', 'Target')}: {wiz.target_codi} · {t('size_map_sum_unit', 'Unitat')}: {wiz.base_unit} · {t('size_map_sum_client', 'Client')}: {wiz.customer_codi || '—'}</div>
            <div>{t('size_map_sum_talles', 'Talles')}: {wiz.talles.length} · {t('size_map_sum_rules', 'Regles')}: {wiz.gradingResults.filter(g => g.pom_id).length} · {t('size_map_sum_perfils', 'Perfils')}: {wiz.perfilTargets.length}</div>
            {wiz.construction_id && <div>{t('size_map_sum_constr', 'Construcció')}: {nomById(lookups.constructions, wiz.construction_id)}</div>}
          </div>

          {/* Panell d'avís-i-confirma (409): graduacions ja existents per a la combinació. */}
          {conflict && (
            <div style={{ border: '1px solid var(--gold)', background: 'var(--gold-pale)', borderRadius: 8, padding: 12, marginBottom: 14, fontSize: 12 }}>
              <div style={{ fontWeight: 600, color: 'var(--gold)', marginBottom: 8 }}>
                <i className="ti ti-alert-triangle" style={{ marginRight: 6 }} />
                {conflict.message || t('size_map_conflict_title', 'Ja existeix una graduació per a aquesta combinació.')}
              </div>
              <ul style={{ margin: '0 0 10px', paddingLeft: 18 }}>
                {(conflict.existing || []).map((ex, i) => (
                  <li key={i}>«{ex.nom}» — {ex.combinacio}</li>
                ))}
              </ul>
              {/* (a) Actualitzar: un botó per cada nom distint existent */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
                {[...new Set((conflict.existing || []).map(ex => ex.nom))].map(nom => (
                  <button key={nom} onClick={() => submitCreate({ on_conflict: 'update', nom_variant: nom })}
                    disabled={busy} style={ghostBtn}>
                    {t('size_map_conflict_update', 'Actualitzar')} «{nom}»
                  </button>
                ))}
              </div>
              {/* (b) Crear-ne una de nova: exigeix nom_variant */}
              <Field label={t('size_map_conflict_new_name', 'Nom de la nova graduació')}>
                <input value={wiz.nom_variant} onChange={e => set({ nom_variant: e.target.value })}
                  placeholder="EU Knit Woman Slim" style={{ ...selS, width: '100%' }} />
              </Field>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => {
                    if (!wiz.nom_variant.trim()) { setErr(t('size_map_conflict_need_name', 'Posa un nom per a la nova graduació')); return }
                    submitCreate({ on_conflict: 'new', nom_variant: wiz.nom_variant.trim() })
                  }} disabled={busy} style={primaryBtn}>
                  <i className="ti ti-plus" />{t('size_map_conflict_new', 'Crear-ne una de nova')}
                </button>
                <button onClick={() => setConflict(null)} style={ghostBtn}>{t('size_map_cancel', 'Cancel·lar')}</button>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => { setConflict(null); setStep(4) }} style={ghostBtn}>{t('size_map_back', 'Enrere')}</button>
            <button onClick={doCreate} disabled={busy} style={primaryBtn}>
              <i className="ti ti-check" />{t('size_map_create_btn', 'Crear')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
