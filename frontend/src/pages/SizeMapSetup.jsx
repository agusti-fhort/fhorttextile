import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'
import { sizeMap, poms, customers } from '../api/endpoints'
import CustomerSelector from '../components/CustomerSelector'
import SizeSystemSelector from '../components/SizeSystem/SizeSystemSelector'
import CascadeSelector from '../components/CascadeSelector/CascadeSelector'
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
// Badge de confiança del matching (patró del W2): verd/groc/taronja/vermell.
const CONF_BADGE = {
  HIGH:     { bg: '#f0f9f0', color: '#3b6d11', label: 'alta' },
  MEDIUM:   { bg: '#fdf6ee', color: 'var(--gold)', label: 'mitjana' },
  LOW:      { bg: '#fdf3ee', color: 'var(--gold)', label: 'baixa' },
  NO_MATCH: { bg: '#fff0f0', color: '#a32d2d', label: 'sense match' },
}

const STEPS = [
  { n: 1, key: 'size_map_screen_config', label: 'Configuració' },
  { n: 2, key: 'size_map_screen_import', label: 'Importació i confirmació' },
]

const card = { border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', padding: 16, marginBottom: 14 }
const ghostBtn = { ...selS, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }

function Field({ label, children, hint }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: 'var(--text-muted)', textTransform: 'uppercase', display: 'block', marginBottom: 6 }}>{label}</label>
      {children}
      {hint && <div style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)', marginTop: 4 }}>{hint}</div>}
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
    return <Center>{t('size_map_no_access')}</Center>
  }

  if (wizardOpen) {
    return (
      <Wizard t={t} prefill={prefill}
        showReturnBanner={!!prefill?.import_session_token}
        onClose={() => setWizardOpen(false)}
        onComplete={(data) => {
          // Branch de tornada: si venim del W1, tornem al model (tab Mesures). J1: ja NO a la pàgina
          // standalone. El param ?session= era un no-op (ModelMeasurements no el llegia mai), per això
          // es deixa caure; el tab mostra la genesi (si verge) o la consulta (si ja té mesures).
          if (prefill?.import_session_token && prefill?.model_id) {
            navigate(`/models/${prefill.model_id}?tab=Mesures`)
            return
          }
          setWizardOpen(false)
          const w = data?.warnings || []
          const base = t('size_map_created') + `: ${data?.codi} — ${data?.nom}`
          loadSystems().then(() => setFeedback({ type: 'ok', text: w.length ? `${base} (${w.length} ${t('size_map_warnings')})` : base }))
        }}
      />
    )
  }

  const columns = [
    { key: 'nom', label: t('size_map_col_nom'),
      render: r => <span style={{ fontWeight: 500 }}>{r.nom}</span> },
    { key: 'codi', label: t('size_map_col_codi'),
      render: r => <span style={{ fontFamily: MONO }}>{r.codi}</span> },
    { key: 'target_nom', label: t('size_map_col_target'), render: r => r.target_nom || '—' },
    { key: 'base_unit', label: t('size_map_col_unit'),
      render: r => <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)' }}>{r.base_unit || '—'}</span> },
    { key: 'customer_codi', label: t('size_map_col_client'),
      render: r => r.customer_codi
        ? <Badge variant="gold">{r.customer_codi}</Badge>
        : <span style={{ color: 'var(--gray)' }}>{t('size_map_canonical')}</span> },
    { key: 'parent_codi', label: t('size_map_col_parent'),
      render: r => r.parent_codi ? <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)' }}>{r.parent_codi}</span> : '—' },
    { key: 'num_talles', label: t('size_map_col_talles'), align: 'right',
      render: r => <span style={{ fontFamily: MONO }}>{r.num_talles}</span> },
    { key: 'num_rule_sets', label: t('size_map_col_rules'), align: 'right',
      render: r => <span style={{ fontFamily: MONO }}>{r.num_rule_sets}</span> },
  ]

  return (
    <div style={{ minWidth: 0, maxWidth: 1100 }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12, marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4, fontFamily: MONO }}>{t('size_map_title')}</h1>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontWeight: 300 }}>{t('size_map_subtitle')}</p>
        </div>
        <button onClick={() => setWizardOpen(true)} style={{ ...primaryBtn, marginLeft: 0 }}>
          <i className="ti ti-plus" style={{ fontSize: 14 }} />{t('size_map_new_run')}
        </button>
      </div>

      <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loading ? <Center>{t('size_map_loading')}</Center>
        : error ? <Center>{t('size_map_error')}</Center>
          : (
            <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', overflowX: 'auto' }}>
              <Table columns={columns} data={systems} loading={false} empty={t('size_map_empty')} />
            </div>
          )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// WIZARD
// ─────────────────────────────────────────────────────────────────────────────
function Stepper({ screen, t }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, marginBottom: 18, overflowX: 'auto' }}>
      {STEPS.map((s, i) => {
        const done = s.n < screen, active = s.n === screen
        return (
          <div key={s.n} style={{ display: 'flex', alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 10px' }}>
              <span style={{
                width: 22, height: 22, borderRadius: 999, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 'var(--fs-body)', fontFamily: MONO, fontWeight: 600,
                background: active ? 'var(--gold)' : done ? 'var(--gold-pale)' : 'var(--gray-l)',
                color: active ? 'var(--white)' : done ? 'var(--gold)' : 'var(--gray)',
              }}>{s.n}</span>
              <span style={{ fontSize: 'var(--fs-body)', fontFamily: MONO, color: active ? 'var(--text-main)' : 'var(--gray)', fontWeight: active ? 600 : 400 }}>
                {t(s.key, s.label)}
              </span>
            </div>
            {i < STEPS.length - 1 && <i className="ti ti-chevron-right" style={{ fontSize: 13, color: 'var(--gray-l)' }} />}
          </div>
        )
      })}
    </div>
  )
}

export function Wizard({ t, prefill = null, onComplete, onClose, showReturnBanner = false }) {
  const [step, setStep] = useState(1)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  // 1C-4b-fe1 — panell d'avís-i-confirma quan el backend retorna 409 {existing, message}.
  const [conflict, setConflict] = useState(null)
  // R2/R5 — resultat del create (nom, regles reals persistides, pendents de vincular): es mostra
  // abans de tancar perquè l'humà vegi què s'ha desat i què ha quedat pendent.
  const [result, setResult] = useState(null)
  const [lookups, setLookups] = useState({ targets: [], constructions: [], fit_types: [], garment_types: [], base_units: [] })

  // Estat global del wizard en un sol objecte.
  const [wiz, setWiz] = useState({
    target_codi: '', base_unit: 'ALPHA', customer_codi: '', customer_id: null, src_system_id: null, applies_to: [], labelsText: '', base_size: '',
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
    const patch = {
      target_codi: prefill.target_codi || '',
      labelsText: (prefill.labels || []).join('\n'),
      base_size: prefill.base_size || '',
    }
    // 1C-3: si el prefill porta POMs+valors (ve de l'ImportWizard), pre-omple la graella de
    // grading com a TSV perquè el grading-preview (detect_grading) derivi i la Montse REVISI.
    if (Array.isArray(prefill.poms) && prefill.poms.length) {
      const labels = prefill.labels || []
      const header = ['POM', ...labels].join('\t')
      const rows = prefill.poms.map(p =>
        [p.pom_codi, ...labels.map(l => {
          const v = (p.valors || {})[l]
          return (v === undefined || v === null) ? '' : v
        })].join('\t'))
      patch.gradingText = [header, ...rows].join('\n')
    }
    // 1C-3 Bug B: pre-omple el pas Perfils amb la classificació del model (per crear el
    // SizingProfile). perfilTargets parteix del target; construction/fit/garment_type per id.
    if (prefill.target_codi) patch.perfilTargets = [prefill.target_codi]
    if (prefill.construction_id != null) patch.construction_id = String(prefill.construction_id)
    if (prefill.fit_type_id != null) patch.fit_type_id = String(prefill.fit_type_id)
    if (prefill.garment_type_id != null) patch.garment_type_id = String(prefill.garment_type_id)
    set(patch)
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    sizeMap.lookups().then(r => {
      setLookups(r.data || {})
    }).catch(() => {})
  }, [])

  // Catàleg de POMs (tenant) per al match manual al pas Grading: si un codi de l'Excel del
  // client no resol (p.ex. 'B'), l'usuari el pot vincular al POM canònic. Una sola crida;
  // si falla, el select queda buit però el flux no peta. max_page_size=200 > catàleg actual.
  const [catalegPoms, setCatalegPoms] = useState([])
  useEffect(() => {
    poms.list({ page_size: 200, actiu: true }).then(r => {
      const arr = r.data?.results || r.data || []
      setCatalegPoms(arr.map(p => ({ pom_id: p.id, codi_client: p.codi_client, nom: p.nom_client })))
    }).catch(() => setCatalegPoms([]))
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
      .catch(e => setErr(e?.response?.data?.error || t('size_map_match_err')))
      .finally(() => setBusy(false))
  }

  // P2 → preview
  // P2 → P3 (definició de talles) NOMÉS quan es construeix un sistema. Amb REUTILITZAR, el run
  // ja existeix i és sobirà: quines talles fabrica un model és pregunta del MODEL, no del joc de
  // regles (llei S24). El pas es salta sencer — abans hi havia una graella editable que convidava
  // a podar el run i la poda ni es desava ni validava res: era estat local que es llençava.
  const goPreview = () => {
    if (wiz.decision === 'REUTILITZAR') { setStep(4); return }
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
      .catch(e => setErr(e?.response?.data?.error || t('size_map_preview_err')))
      .finally(() => setBusy(false))
  }

  // P4 → grading preview. Mapatge comú per a paste i fitxer (mateixa forma de fila).
  const [gradingAvisos, setGradingAvisos] = useState([])
  const applyGradingData = (data) => {
    const results = (data?.results || []).map(x => ({
      ...x, logica: x.logica_detectada || 'LINEAR',
      increment: x.increment ?? 0,
      valors_step_text: x.valors_step ? JSON.stringify(x.valors_step) : '',
    }))
    set({ gradingResults: results, gradingRun: data?.run || [] })
    setGradingAvisos(data?.avisos || [])
  }

  // P4 alternatiu → pujada de fitxer (Excel/PDF/imatge): reusa el motor d'extracció del model.
  const calcGradingFromFile = (fileObj) => {
    if (!fileObj) return
    setErr(null); setGradingAvisos([]); setBusy(true)
    const fd = new FormData()
    fd.append('file', fileObj)
    if (wiz.size_system_id) fd.append('size_system_id', wiz.size_system_id)
    fd.append('base_size', wiz.base_size || '')
    if (wiz.customer_codi) fd.append('customer_codi', wiz.customer_codi)
    sizeMap.gradingPreviewFile(fd)
      .then(r => applyGradingData(r.data))
      .catch(e => setErr(errText(e)))
      .finally(() => setBusy(false))
  }

  // Check (d): el document porta una talla que el sistema triat no coneix. NO és una talla que
  // falti (això és `incompleta`): és un desajust real entre document i sistema, i el backend el
  // torna com a 400 amb la llista. Es rotula aquí perquè el text sigui traduïble; la resta
  // d'errors del backend segueixen mostrant-se tal com arriben.
  const errText = (e, fallback = 'size_map_file_err') => {
    const d = e?.response?.data
    if (d?.etiquetes_desconegudes?.length)
      return t('size_map_unknown_sizes', { sizes: d.etiquetes_desconegudes.join(', ') })
    return d?.error || t(fallback)
  }

  // Col·lisió R1 (pre-check al pas 3): pom_id vinculats per >1 codi de document. Dues files al
  // mateix POM col·lapsarien a una sola regla al backend (update_or_create) → pèrdua silenciosa.
  // Es marquen visualment i el create es bloqueja (backend 400); decisió CTO: bloquejar.
  const dupPomIds = (() => {
    const c = {}
    wiz.gradingResults.forEach(g => { if (g.pom_id) c[g.pom_id] = (c[g.pom_id] || 0) + 1 })
    return new Set(Object.entries(c).filter(([, n]) => n > 1).map(([k]) => Number(k)))
  })()

  // Integritat: files amb talles absents (marcades pel backend). No es pot derivar cap regla d'una
  // taula incompleta; es marquen i el create es bloqueja (backend 400).
  const incompletes = wiz.gradingResults.filter(g => g.incompleta)

  // P5 → create. buildPayload accepta overrides {on_conflict, nom_variant} per re-cridar
  // des del panell de conflicte (avís-i-confirma).
  const buildPayload = (extra = {}) => {
    const grading = wiz.gradingResults
      .filter(g => g.pom_id)
      .map(g => {
        // `codi` = codi de document (nomenclatura del client): NO es persisteix, viatja perquè
        // el backend pugui rotular una col·lisió {codi_document → pom} (R1) si dues files hi cauen.
        const row = { pom_id: g.pom_id, codi: g.pom_codi_client, logica: g.logica,
          incompleta: !!g.incompleta, missing_sizes: g.missing_sizes || [] }
        // valors_step és l'ORIGEN del break: enviar-lo sempre que el preview el va produir
        // (també per LINEAR amb break, p.ex. CHEST) perquè el create en derivi base+break.
        let vs
        try { vs = g.valors_step_text ? JSON.parse(g.valors_step_text) : (g.valors_step || null) } catch { vs = g.valors_step || null }
        if (vs && Object.keys(vs).length) row.valors_step = vs
        if (g.logica !== 'STEP') row.increment = Number(g.increment) || 0
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
      // REFERENT (llei S24): el run del DOCUMENT tal com el va tornar el preview. El create
      // deriva el break sobre AQUESTA escala, no sobre el run del sistema — així preview i
      // persistència parlen del mateix run i el break no es recol·loca en desar.
      doc_run: wiz.gradingRun,
      // Sprint ÀMBIT — «aplica a» = «està disponible per a»: nodes multi-nivell (grup/família/item)
      // + multi-target (el M2M targets ja existia).
      applies_to: wiz.applies_to,
      target_codis: wiz.perfilTargets,
      // IDENTITAT (opció (c) del gate): si l'àmbit és EXACTAMENT un item, el contenidor conserva la
      // identitat fina (garment_type_item) i, amb ella, la guarda d'unicitat de la constraint 0039
      // (+ el 409 avís-i-confirma). Àmbits amples (grup/família o multi-item) → gti null: no els
      // guarda la constraint, a posta (són contenidors amples).
      garment_type_item_id: (() => {
        const items = wiz.applies_to.filter(n => n.node_type === 'ITEM')
        return (items.length === 1 && wiz.applies_to.length === 1)
          ? items[0].garment_type_item_id : undefined
      })(),
      // R2 — codis del document no vinculats a cap POM: viatgen perquè el backend els
      // desi al run com a "pendents de vincular" (no es perden en silenci). El window.confirm
      // de submitCreate segueix sent la primera barrera.
      discarded_codes: wiz.gradingResults.filter(g => !g.pom_id).map(g => g.pom_codi_client).filter(Boolean),
      ...extra,   // on_conflict / nom_variant des del panell sobreescriuen
    }
  }

  const submitCreate = (extra = {}) => {
    // Guard d'integritat: cap regla d'una taula incompleta. Torna a la taula de grading, que és
    // on es veuen les files marcades (abans tornava al pas 3, la graella de talles: amagava
    // justament les files vermelles que calia resoldre). El backend també ho bloqueja amb 400.
    if (incompletes.length > 0) {
      setErr(t('size_map_incompleta_warn', { count: incompletes.length }))
      setStep(4)
      return
    }
    // Guard anti-col·lisió (R1): si dos codis comparteixen POM, tornar a la taula de grading a
    // resoldre-ho (el backend també ho bloqueja amb 400, però evitem la crida inútil).
    if (dupPomIds.size > 0) {
      setErr(t('size_map_dup_warn', { count: dupPomIds.size }))
      setStep(4)
      return
    }
    // Guard anti-descart-silenciós: buildPayload filtra els !pom_id; abans d'enviar, avisa
    // l'usuari de quins codis de client no s'han vinculat (i per tant no es desaran).
    const noResolts = wiz.gradingResults.filter(g => !g.pom_id)
    if (noResolts.length > 0) {
      const codis = noResolts.map(g => g.pom_codi_client).join(', ')
      const msg = `${noResolts.length} POM(s) sense vincular (${codis}) no es desaran.\n`
        + `Vincula'ls al catàleg o continua sense ells?`
      if (!window.confirm(msg)) return
    }
    setErr(null); setConflict(null); setBusy(true)
    sizeMap.create(buildPayload(extra))
      .then(r => { setResult(r.data) })
      .catch(e => {
        // 409 = avís-i-confirma (no és error): obre el panell amb les graduacions existents.
        if (e?.response?.status === 409) { setConflict(e.response.data); return }
        setErr(errText(e, 'size_map_create_err'))
      })
      .finally(() => setBusy(false))
  }

  const doCreate = () => submitCreate()

  const nomById = (arr, id) => arr.find(x => String(x.id) === String(id))?.nom || ''

  // ---- RESULTAT del create (R2 pendents + R5 comptador) ----
  if (result) {
    const pendents = result.discarded_codes || []
    return (
      <div style={{ minWidth: 0, maxWidth: 1100 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <i className="ti ti-circle-check" style={{ fontSize: 20, color: 'var(--gold)' }} />
          <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, fontFamily: MONO, margin: 0 }}>{t('size_map_result_title')}</h1>
        </div>
        <div style={{ background: 'var(--gray-l)', borderRadius: 8, padding: 12, marginBottom: 14, fontSize: 'var(--fs-body)', fontFamily: MONO }}>
          <div>{result.nom}</div>
          {/* R5 — regles reals persistides (BD), font única. */}
          <div>{t('size_map_sum_rules')}: {result.rules_count ?? 0}</div>
        </div>
        {pendents.length > 0 && (
          <div style={{ background: 'var(--warn-bg)', border: '0.5px solid var(--warn)', borderRadius: 8,
                        padding: '10px 12px', marginBottom: 14, fontSize: 'var(--fs-body)', color: 'var(--warn)' }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              <i className="ti ti-link-off" style={{ marginRight: 6 }} />
              {t('size_map_pendents')} ({pendents.length})
            </div>
            <div style={{ fontFamily: MONO }}>{pendents.join(', ')}</div>
            <div style={{ marginTop: 4, fontSize: 'var(--fs-label)' }}>{t('size_map_pendents_hint')}</div>
          </div>
        )}
        <button onClick={() => onComplete(result)} style={primaryBtn}>
          <i className="ti ti-check" />{t('size_map_result_close')}
        </button>
      </div>
    )
  }

  return (
    <div style={{ minWidth: 0, maxWidth: 1100 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
        <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, fontFamily: MONO }}>{t('size_map_new_run')}</h1>
        <button onClick={onClose} style={ghostBtn}><i className="ti ti-x" style={{ fontSize: 13 }} />{t('size_map_cancel')}</button>
      </div>

      {showReturnBanner && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--gold-pale)', color: 'var(--gold)',
                      border: '0.5px solid var(--gold)', borderRadius: 8, padding: '8px 12px', marginBottom: 14, fontSize: 'var(--fs-body)' }}>
          <i className="ti ti-link" style={{ fontSize: 14 }} />
          {t('size_map_from_w1')}
        </div>
      )}

      <Stepper screen={step <= 3 ? 1 : 2} t={t} />
      {err && <Feedback feedback={{ type: 'err', text: err }} onDismiss={() => setErr(null)} />}

      {/* ---- P1 ---- */}
      {step === 1 && (
        <div style={card}>
          <Field label={t('size_map_f_target')}>
            <select value={wiz.target_codi} onChange={e => set({ target_codi: e.target.value })} style={{ ...selS, width: '100%' }}>
              <option value="">—</option>
              {lookups.targets.map(o => <option key={o.codi} value={o.codi}>{t(`model_wizard.target_${o.codi}`, o.nom)} ({o.codi})</option>)}
            </select>
          </Field>
          <Field label={t('size_map_f_unit')}>
            <select value={wiz.base_unit} onChange={e => set({ base_unit: e.target.value })} style={{ ...selS, width: '100%' }}>
              {(lookups.base_units?.length ? lookups.base_units.map(o => o.codi) : BASE_UNITS).map(u =>
                <option key={u} value={u}>{u}</option>)}
            </select>
          </Field>
          {/* HIGIENE (1) — el client es TRIA, no es tecleja. El selector dona l'id; el payload va per
              codi (contracte del backend) → es resol el codi en triar. */}
          <Field label={t('size_map_f_customer')} hint={t('size_map_f_customer_hint')}>
            <CustomerSelector value={wiz.customer_id} onError={setErr}
              onChange={(id) => {
                set({ customer_id: id, customer_codi: '' })
                if (id) customers.get(id).then(r => set({ customer_codi: r.data?.codi || '' })).catch(() => {})
              }} />
          </Field>
          {/* HIGIENE (2) — el run es TRIA d'un SizeSystem, no es tecleja. Les etiquetes segueixen sent
              l'estat de sota (la canonada de match/create no canvia). */}
          <Field label={t('size_map_f_labels')} hint={t('size_map_f_run_hint')}>
            <SizeSystemSelector value={wiz.src_system_id} targetCodi={wiz.target_codi || null}
              onChange={(sys) => {
                if (!sys) { set({ src_system_id: null, labelsText: '', base_size: '' }); return }
                const labs = (sys.talles || []).map(d => d.etiqueta || d.size_label || d.label).filter(Boolean)
                set({ src_system_id: sys.id, labelsText: labs.join('\n'),
                      base_size: labs[Math.floor(labs.length / 2)] || labs[0] || '' })
              }} />
          </Field>
          {wiz.labelsText && (
            <Field label={t('size_map_f_base')}>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {labels().map(l => (
                  <Pill key={l} active={wiz.base_size === l} onClick={() => set({ base_size: l })}>{l}</Pill>
                ))}
              </div>
            </Field>
          )}
          {/* HIGIENE (3) — construcció i fit per BOTONS, no selects. */}
          <Field label={t('size_map_p_construction')}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {lookups.constructions.map(o => (
                <Pill key={o.id} active={String(wiz.construction_id) === String(o.id)}
                  onClick={() => set({ construction_id: String(wiz.construction_id) === String(o.id) ? '' : o.id })}>
                  {t(`model_wizard.construction_${o.codi}`, o.nom)}
                </Pill>
              ))}
            </div>
          </Field>
          <Field label={t('size_map_p_fit')}>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {lookups.fit_types.map(o => (
                <Pill key={o.id} active={String(wiz.fit_type_id) === String(o.id)}
                  onClick={() => set({ fit_type_id: String(wiz.fit_type_id) === String(o.id) ? '' : o.id })}>
                  {t(`model_wizard.fit_${o.codi}`, o.nom)}
                </Pill>
              ))}
            </div>
          </Field>
          {/* ÀMBIT — l'item ja no és «buit»: és l'àmbit d'aplicabilitat, multi-node i obligatori (≥1). */}
          <Field label={t('scope.label')} hint={t('scope.hint')}>
            <CascadeSelector mode="multi" value={wiz.applies_to} onChange={(nodes) => set({ applies_to: nodes })} />
          </Field>
          <button onClick={goMatch}
            disabled={busy || !wiz.target_codi || labels().length === 0 || !wiz.base_size || wiz.applies_to.length === 0}
            style={{ ...primaryBtn }}>{t('size_map_next')}</button>
        </div>
      )}

      {/* ---- P2 ---- */}
      {step === 2 && (
        <div style={card}>
          <div style={{ marginBottom: 12, fontSize: 'var(--fs-body)' }}>
            {t('size_map_reco')}: <Badge variant={REC_VARIANT[wiz.recomanacio] || 'gray'}>{wiz.recomanacio}</Badge>
          </div>
          {wiz.candidates.length === 0 && (
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginBottom: 12 }}>{t('size_map_no_candidates')}</div>
          )}
          {wiz.candidates.map(c => (
            <label key={c.size_system_id} style={{ display: 'block', border: '0.5px solid var(--gray-l)', borderRadius: 8, padding: 12, marginBottom: 8, cursor: 'pointer' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <input type="radio" name="cand" checked={wiz.decision !== 'CREAR' && String(wiz.size_system_id) === String(c.size_system_id)}
                  onChange={() => set({ size_system_id: c.size_system_id, decision: c.recomanacio === 'CREAR' ? 'CLONAR' : c.recomanacio })} />
                <span style={{ fontWeight: 600 }}>{c.nom}</span>
                <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{c.codi}</span>
                <Badge variant={c.score >= 1 ? 'ok' : 'warn'}>{Math.round((c.score || 0) * 100)}%</Badge>
                <Badge variant={REC_VARIANT[c.recomanacio] || 'gray'}>{c.recomanacio}</Badge>
              </div>
              {/* barra de score */}
              <div style={{ height: 6, background: 'var(--gray-l)', borderRadius: 999, marginTop: 8 }}>
                <div style={{ height: 6, width: `${Math.round((c.score || 0) * 100)}%`, background: 'var(--gold)', borderRadius: 999 }} />
              </div>
              {c.unmatched_labels?.length > 0 &&
                <div style={{ fontSize: 'var(--fs-body)', color: 'var(--warn)', marginTop: 6 }}>{t('size_map_unmatched')}: {c.unmatched_labels.join(', ')}</div>}
              {c.warning && <div style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', marginTop: 4 }}>{c.warning}</div>}
            </label>
          ))}
          {/* opció crear nou */}
          <label style={{ display: 'flex', alignItems: 'center', gap: 10, border: '0.5px dashed var(--gray-l)', borderRadius: 8, padding: 12, marginBottom: 14, cursor: 'pointer' }}>
            <input type="radio" name="cand" checked={wiz.decision === 'CREAR'} onChange={() => set({ decision: 'CREAR', size_system_id: null })} />
            <span>{t('size_map_create_new')}</span>
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setStep(1)} style={ghostBtn}>{t('size_map_back')}</button>
            <button onClick={goPreview} disabled={busy || (wiz.decision !== 'CREAR' && !wiz.size_system_id)} style={primaryBtn}>{t('size_map_next')}</button>
          </div>
        </div>
      )}

      {/* ---- P3 · definició del run del sistema NOU (CREAR/CLONAR). Amb REUTILITZAR no s'hi
           arriba mai: el run del sistema triat és sobirà i no s'edita des d'aquí (llei S24). ---- */}
      {step === 3 && wiz.decision !== 'REUTILITZAR' && (
        <div style={card}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
              <thead>
                <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 'var(--fs-label)' }}>
                  <th style={{ padding: 6 }}>{t('size_map_t_label')}</th>
                  <th style={{ padding: 6 }}>{t('size_map_t_order')}</th>
                  <th style={{ padding: 6 }}>{t('size_map_t_numeric')}</th>
                  <th style={{ padding: 6 }}>{t('size_map_t_mmin')}</th>
                  <th style={{ padding: 6 }}>{t('size_map_t_mmax')}</th>
                  <th style={{ padding: 6 }}>{t('size_map_t_height')}</th>
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
              style={ghostBtn}><i className="ti ti-plus" />{t('size_map_add_size')}</button>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setStep(2)} style={ghostBtn}>{t('size_map_back')}</button>
            <button onClick={() => setStep(4)} disabled={wiz.talles.length === 0} style={primaryBtn}>{t('size_map_next')}</button>
          </div>
        </div>
      )}

      {/* ---- PANTALLA 2 (a): pujada de fitxer + taula de grading ---- */}
      {step >= 4 && (
        <div style={card}>
          {/* Pujada de fitxer ric (Excel/PDF/imatge): reusa el motor d'extracció del model
              → match per codi+nom + grading derivat sobre les talles definides a la Pantalla 1. */}
          <Field label={t('size_map_g_file')}
            hint={t('size_map_g_file_hint')}>
            <label htmlFor="size-map-grading-file"
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); calcGradingFromFile(e.dataTransfer.files[0]) }}
              style={{ display: 'block', border: '1px dashed var(--gray-l)', borderRadius: 8,
                       padding: 14, textAlign: 'center', cursor: busy ? 'wait' : 'pointer',
                       color: 'var(--gray)', fontSize: 'var(--fs-body)' }}>
              {/* HIGIENE (5) — rodeta mentre l'extracció processa: la IA triga i abans només hi havia
                  un canvi de cursor, sense cap senyal viu que allò estava treballant. */}
              {busy
                ? <Spinner label={t('size_map_g_file_busy')} />
                : <><i className="ti ti-upload" style={{ fontSize: 18, marginRight: 6 }} aria-hidden="true" />
                    {t('size_map_g_file_drop')}</>}
              <input id="size-map-grading-file" type="file" accept=".xlsx,.xls,.pdf,.png,.jpg,.jpeg,.webp"
                style={{ display: 'none' }} disabled={busy}
                onChange={e => { calcGradingFromFile(e.target.files[0]); e.target.value = '' }} />
            </label>
          </Field>

          {gradingAvisos.length > 0 && (
            <ul style={{ margin: '0 0 14px', padding: '8px 12px 8px 26px', background: 'var(--warn-bg)',
                         borderRadius: 8, fontSize: 'var(--fs-body)', color: 'var(--warn)' }}>
              {gradingAvisos.map((a, k) => <li key={k}>{a}</li>)}
            </ul>
          )}

          {incompletes.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--err-bg)', color: 'var(--err)',
                          border: '0.5px solid var(--err)', borderRadius: 8, padding: '8px 12px', marginBottom: 14, fontSize: 'var(--fs-body)' }}>
              <i className="ti ti-alert-triangle" style={{ fontSize: 14 }} />
              {t('size_map_incompleta_warn', { count: incompletes.length })}
            </div>
          )}

          {dupPomIds.size > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--err-bg)', color: 'var(--err)',
                          border: '0.5px solid var(--err)', borderRadius: 8, padding: '8px 12px', marginBottom: 14, fontSize: 'var(--fs-body)' }}>
              <i className="ti ti-alert-triangle" style={{ fontSize: 14 }} />
              {t('size_map_dup_warn', { count: dupPomIds.size })}
            </div>
          )}

          {wiz.gradingResults.length > 0 && (
            <div style={{ overflowX: 'auto', marginBottom: 14 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
                <thead>
                  <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontFamily: MONO, fontSize: 'var(--fs-label)' }}>
                    <th style={{ padding: 6 }}>POM</th>
                    <th style={{ padding: 6 }}>{t('size_map_g_logica')}</th>
                    <th style={{ padding: 6 }}>{t('size_map_g_value')}</th>
                    <th style={{ padding: 6 }}>{t('size_map_g_doc_values')}</th>
                    <th style={{ padding: 6 }}>{t('size_map_g_warn')}</th>
                  </tr>
                </thead>
                <tbody>
                  {wiz.gradingResults.map((g, i) => {
                    const upd = (k, v) => set({ gradingResults: wiz.gradingResults.map((r, j) => j === i ? { ...r, [k]: v } : r) })
                    return (
                      <tr key={i} style={{ borderTop: '0.5px solid var(--gray-l)',
                        background: g.incompleta ? 'var(--err-bg)'
                          : g.pom_id ? (dupPomIds.has(g.pom_id) ? 'var(--err-bg)' : 'transparent') : 'var(--warn-bg)' }}>
                        <td style={{ padding: 6 }}>
                          {/* codi de client (nomenclatura seva, ex 'B') + descripció del fitxer
                              com a referència; badge de confiança; si no resol, select de catàleg. */}
                          <div style={{ fontFamily: MONO }}>{g.pom_codi_client}</div>
                          {g.pom_descripcio && <div style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>{g.pom_descripcio}</div>}
                          {(() => {
                            const cb = CONF_BADGE[(g.confidence || '').toUpperCase()]
                            return cb ? (
                              <span style={{ display: 'inline-block', marginTop: 2, fontSize: 'var(--fs-label)', fontWeight: 600,
                                             padding: '1px 6px', borderRadius: 8, background: cb.bg, color: cb.color }}>
                                {cb.label}</span>
                            ) : null
                          })()}
                          {g.pom_id && dupPomIds.has(g.pom_id) && (
                            <div style={{ marginTop: 2, fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--err)' }}>
                              <i className="ti ti-alert-triangle" style={{ fontSize: 12, marginRight: 3 }} />
                              {t('size_map_dup_pom')}
                            </div>
                          )}
                          {g.pom_id
                            ? (g.pom_nom && <div style={{ fontSize: 'var(--fs-label)', color: 'var(--gray)' }}>→ {g.pom_nom}</div>)
                            : (<>
                              {/* Match dèbil (LOW) o guard many-to-one (N3-P2): el backend NO ha
                                  auto-vinculat; es mostra el suggeriment perquè l'humà vinculi
                                  conscientment (mai vinculació silenciosa ni col·lisió sobreescrita). */}
                              {g.weak_suggestion && (
                                <div style={{ marginTop: 2, fontSize: 'var(--fs-label)', color: 'var(--warn)' }}>
                                  <i className="ti ti-help-circle" style={{ fontSize: 12, marginRight: 3 }} />
                                  {g.many_to_one
                                    ? t('size_map_many_to_one', { pom: g.weak_suggestion })
                                    : t('size_map_weak_match', { pom: g.weak_suggestion })}
                                </div>
                              )}
                              <select value={g.pom_id || ''} style={{ ...selS, padding: '3px 6px', fontSize: 'var(--fs-body)', marginTop: 2, maxWidth: 260 }}
                                onChange={e => {
                                  const id = Number(e.target.value) || null
                                  const picked = catalegPoms.find(p => p.pom_id === id)
                                  set({ gradingResults: wiz.gradingResults.map((r, j) => j === i ? { ...r, pom_id: id, pom_nom: picked ? picked.nom : null } : r) })
                                }}>
                                <option value="">{t('size_map_link_pom')}</option>
                                {catalegPoms.map(p => <option key={p.pom_id} value={p.pom_id}>{p.codi_client} — {p.nom}</option>)}
                              </select>
                            </>)}
                        </td>
                        <td style={{ padding: 6 }}>
                          <select value={g.logica} onChange={e => upd('logica', e.target.value)} style={{ ...selS, padding: '3px 6px' }}>
                            {LOGICA.map(l => <option key={l} value={l}>{l}</option>)}
                          </select>
                        </td>
                        <td style={{ padding: 6 }}>
                          {g.increment_base == null
                            ? (g.valors_step_text
                                ? <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)' }}>{g.valors_step_text}</span>
                                : <span style={{ color: 'var(--gray)' }}>—</span>)
                            : (g.increment_break != null
                                ? <span>+{g.increment_base} · +{g.increment_break} {t('size_map_g_break_from')} {g.talla_break_label}</span>
                                : <span>+{g.increment_base}</span>)}
                        </td>
                        {/* Paritat R7 (NOMÉS display): valors originals del document per talla + toleràncies
                            extretes, al costat de la regla derivada, perquè l'humà validi la fidelitat
                            (p.ex. detectar 5.6→8.0 rotulat FIXED) ABANS de persistir el secret industrial. */}
                        <td style={{ padding: 6, fontFamily: MONO, fontSize: 'var(--fs-label)' }}>
                          {g.valors_calculats && Object.keys(g.valors_calculats).length > 0
                            ? (<>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2px 8px' }}>
                                  {(wiz.gradingRun.length ? wiz.gradingRun : Object.keys(g.valors_calculats)).map(sz =>
                                    g.valors_calculats[sz] != null
                                      ? <span key={sz} style={{ whiteSpace: 'nowrap' }}>
                                          <span style={{ color: 'var(--gray)' }}>{sz}</span> {g.valors_calculats[sz]}
                                        </span>
                                      : null)}
                                </div>
                                {(g.tolerance_minus != null || g.tolerance_plus != null) && (
                                  <div style={{ color: 'var(--gray)', marginTop: 2 }}>
                                    {t('size_map_g_tol')} −{g.tolerance_minus ?? 0} / +{g.tolerance_plus ?? 0}
                                  </div>
                                )}
                              </>)
                            : <span style={{ color: 'var(--gray)' }}>—</span>}
                        </td>
                        <td style={{ padding: 6, fontSize: 'var(--fs-body)' }}>
                          {g.incompleta && (
                            <div style={{ color: 'var(--err)', fontWeight: 600, marginBottom: g.warning ? 3 : 0 }}>
                              <i className="ti ti-alert-triangle" style={{ fontSize: 12, marginRight: 3 }} />
                              {t('size_map_incompleta', { sizes: (g.missing_sizes || []).join(', ') })}
                            </div>
                          )}
                          {g.warning && <span style={{ color: 'var(--warn)' }}>{g.warning}</span>}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ---- PANTALLA 2 (b): perfils + destí + confirmació ---- */}
      {step >= 4 && (
        <div style={card}>
          {/* Destí (de la decisió resolta a la Pantalla 1). REUTILITZAR no modifica el sistema:
              només crea un GradingRuleSet nou lligat (confirmat al backend, pas 1-2 del create). */}
          <div style={{ background: 'var(--gold-pale)', border: '0.5px solid var(--gold)', borderRadius: 8,
                        padding: '8px 12px', marginBottom: 14, fontSize: 'var(--fs-body)' }}>
            {wiz.decision === 'CREAR'
              ? <span>{t('size_map_dest_new')}</span>
              : <span>{t('size_map_dest_reuse')}
                  {' '}<b>{(wiz.candidates.find(c => String(c.size_system_id) === String(wiz.size_system_id)) || {}).nom || ''}</b>.
                  {' '}{t('size_map_dest_reuse2')}</span>}
          </div>
          <Field label={t('size_map_p_targets')} hint={t('size_map_p_targets_hint')}>
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
          {wiz.decision === 'CREAR' && (
            <Field label={t('size_map_p_nom')}>
              <input value={wiz.nom_custom} onChange={e => set({ nom_custom: e.target.value })} style={{ ...selS, width: '100%' }} />
            </Field>
          )}
          {wiz.decision === 'CREAR' && (
            <Field label={t('size_map_p_nom_variant')}
              hint={t('size_map_p_nom_variant_hint')}>
              <input value={wiz.nom_variant} onChange={e => set({ nom_variant: e.target.value })}
                placeholder="EU Knit Woman Slim" style={{ ...selS, width: '100%' }} />
            </Field>
          )}

          {/* Resum */}
          <div style={{ background: 'var(--gray-l)', borderRadius: 8, padding: 12, marginBottom: 14, fontSize: 'var(--fs-body)', fontFamily: MONO }}>
            <div>{t('size_map_sum_action')}: <b>{wiz.decision}</b></div>
            <div>{t('size_map_sum_target')}: {wiz.target_codi ? t(`model_wizard.target_${wiz.target_codi}`, wiz.target_codi) : '—'} · {t('size_map_sum_unit')}: {wiz.base_unit} · {t('size_map_sum_client')}: {wiz.customer_codi || '—'}</div>
            {/* R5 — comptador de regles = POMs distints vinculats (regles reals que es
                persistiran, font única), no files de document. La col·lisió (R1) es bloqueja
                abans, així que aquest recompte coincideix amb el de la BD després de crear. */}
            {/* El comptador de talles només té sentit quan aquest wizard DEFINEIX el run (sistema
                nou). Amb REUTILITZAR el run no és cosa seva: es diu quin document s'ha llegit. */}
            <div>
              {wiz.decision === 'REUTILITZAR'
                ? <>{t('size_map_sum_doc_run')}: {wiz.gradingRun.length ? wiz.gradingRun.join(' · ') : '—'} · </>
                : <>{t('size_map_sum_talles')}: {wiz.talles.length} · </>}
              {t('size_map_sum_rules')}: {new Set(wiz.gradingResults.filter(g => g.pom_id).map(g => g.pom_id)).size} · {t('size_map_sum_perfils')}: {wiz.perfilTargets.length}
            </div>
            {wiz.construction_id && <div>{t('size_map_sum_constr')}: {nomById(lookups.constructions, wiz.construction_id)}</div>}
          </div>

          {/* Panell d'avís-i-confirma (409): graduacions ja existents per a la combinació. */}
          {conflict && (
            <div style={{ border: '1px solid var(--gold)', background: 'var(--gold-pale)', borderRadius: 8, padding: 12, marginBottom: 14, fontSize: 'var(--fs-body)' }}>
              <div style={{ fontWeight: 600, color: 'var(--gold)', marginBottom: 8 }}>
                <i className="ti ti-alert-triangle" style={{ marginRight: 6 }} />
                {conflict.message || t('size_map_conflict_title')}
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
                    {t('size_map_conflict_update')} «{nom}»
                  </button>
                ))}
              </div>
              {/* (b) Crear-ne una de nova: exigeix nom_variant */}
              <Field label={t('size_map_conflict_new_name')}>
                <input value={wiz.nom_variant} onChange={e => set({ nom_variant: e.target.value })}
                  placeholder="EU Knit Woman Slim" style={{ ...selS, width: '100%' }} />
              </Field>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => {
                    if (!wiz.nom_variant.trim()) { setErr(t('size_map_conflict_need_name')); return }
                    submitCreate({ on_conflict: 'new', nom_variant: wiz.nom_variant.trim() })
                  }} disabled={busy} style={primaryBtn}>
                  <i className="ti ti-plus" />{t('size_map_conflict_new')}
                </button>
                <button onClick={() => setConflict(null)} style={ghostBtn}>{t('size_map_cancel')}</button>
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => { setConflict(null); setStep(wiz.decision === 'REUTILITZAR' ? 2 : 3) }}
              style={ghostBtn}>{t('size_map_back')}</button>
            <button onClick={doCreate} disabled={busy} style={primaryBtn}>
              <i className="ti ti-check" />{t('size_map_create_btn')}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Àtoms d'entrada (sprint ÀMBIT · higiene) ─────────────────────────────────
// Pill: botó de tria (construcció/fit/talla base) amb el mateix llenguatge visual que la resta de
// selectors de peça/grup (tokens, mai hex).
function Pill({ active, onClick, children }) {
  return (
    <button type="button" onClick={onClick} style={{
      padding: '6px 14px', borderRadius: 6, cursor: 'pointer', fontFamily: MONO,
      fontSize: 'var(--fs-body)', fontWeight: active ? 600 : 400,
      background: active ? 'var(--warn-bg)' : 'var(--white)',
      color: active ? 'var(--warn)' : 'var(--text-main)',
      border: `1px solid ${active ? 'var(--warn)' : 'var(--gray-l)'}`,
    }}>{children}</button>
  )
}

// Spinner: rodeta d'espera de l'extracció (icona Tabler outline + rotació CSS inline; sense
// dependències ni fulls d'estil nous).
function Spinner({ label }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: 'var(--warn)' }}>
      <style>{'@keyframes ftt-spin{to{transform:rotate(360deg)}}'}</style>
      <i className="ti ti-loader-2" aria-hidden="true"
         style={{ fontSize: 18, display: 'inline-block', animation: 'ftt-spin 0.9s linear infinite' }} />
      <span role="status" aria-live="polite">{label}</span>
    </span>
  )
}
