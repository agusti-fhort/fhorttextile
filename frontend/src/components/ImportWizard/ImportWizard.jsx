import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import Modal from '../ui/Modal'
import FileDropCard from '../ui/FileDropCard'

const API = import.meta.env.VITE_API_URL || ''

// base64 unicode-safe (per passar el prefill al Size Map Setup via query param).
const encodePrefill = (obj) => btoa(unescape(encodeURIComponent(JSON.stringify(obj))))

const STEPS = [
  { n: 1, labelKey: 'import_wizard.step.sizes' },
  { n: 2, labelKey: 'import_wizard.step.poms' },
  { n: 3, labelKey: 'import_wizard.step.measures' },
  { n: 4, labelKey: 'import_wizard.step.fabric' },
  { n: 5, labelKey: 'import_wizard.step.save' },
]

const norm = (s) => (s || '').trim().toUpperCase()
const GOLD = 'var(--gold, #c79a3a)'
const BORDER = 'var(--border)'

// ───────────────────────────── Stepper header ─────────────────────────────
function Stepper({ step }) {
  const { t } = useTranslation()
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 0, margin: '0 0 20px' }}>
      {STEPS.map((s, i) => {
        const done = s.n < step
        const active = s.n === step
        return (
          <div key={s.n} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : '0 0 auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                width: 26, height: 26, borderRadius: '50%', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 'var(--fs-body)', fontWeight: 600,
                background: active ? GOLD : done ? '#3b6d11' : 'transparent',
                color: active || done ? 'var(--white)' : 'var(--text-muted)',
                border: active || done ? 'none' : `1px solid ${BORDER}`,
              }}>{done ? '✓' : s.n}</div>
              <span style={{
                fontSize: 'var(--fs-body)', fontWeight: active ? 600 : 400,
                color: active ? 'var(--text-main)' : 'var(--text-muted)', whiteSpace: 'nowrap',
              }}>{t(s.labelKey)}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{ flex: 1, height: 1, background: done ? '#3b6d11' : BORDER, margin: '0 10px' }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ───────────────────────────── Talla chip ─────────────────────────────
function TallaChip({ label, ok, onRemove }) {
  const { t } = useTranslation()
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 8px 4px 10px', borderRadius: 6, fontSize: 'var(--fs-body)', fontWeight: 500,
      background: ok ? '#f0f9f0' : '#fff0f0',
      border: `1px solid ${ok ? '#c0dd97' : '#f0c0c0'}`,
      color: ok ? '#3b6d11' : '#a32d2d',
    }}>
      {ok ? '✓' : '✗'} {label}
      {onRemove && (
        <button onClick={onRemove} title={t('import_wizard.remove_size')}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit',
                   fontSize: 'var(--fs-h3)', lineHeight: 1, padding: 0 }}>×</button>
      )}
    </span>
  )
}

export default function ImportWizard({ model, onCancel, onComplete }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { Authorization: `Bearer ${token}` }

  const [step, setStep] = useState(1)
  const [sessionToken, setSessionToken] = useState(null)
  const [error, setError] = useState('')
  const [confirmSizeMap, setConfirmSizeMap] = useState(false)   // 1C-3b: avís abans de saltar a la Library
  const [sizeMapPrefill, setSizeMapPrefill] = useState(null)   // ve de la resposta talles/ (estat PENDENT)

  // Pas 1 — upload + cribratge + reconciliació de talles
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [cribratge, setCribratge] = useState(null)
  const [tallesSel, setTallesSel] = useState([])      // columnes del document mantingudes (labels doc)
  const [systemLabels, setSystemLabels] = useState([]) // etiquetes REALS del model (SizeDefinition)
  const [mapping, setMapping] = useState({})          // aparellament {label_document: label_model}
  const [baseLabel, setBaseLabel] = useState(model.base_size_label || '')  // B5 · talla base (model)
  const [baseAvisos, setBaseAvisos] = useState([])    // B5 · divergències no bloquejants
  const [savingTalles, setSavingTalles] = useState(false)

  // Pas 2 — extracció POMs + matching
  const [extracting, setExtracting] = useState(false)
  const [pomsExtrets, setPomsExtrets] = useState(null)
  const [extraccioMeta, setExtraccioMeta] = useState(null)
  const [savingPoms, setSavingPoms] = useState(false)
  const [cataleg, setCataleg] = useState(null)        // POMMaster catàleg (per afegir manual)
  const [showAddPom, setShowAddPom] = useState(false)

  // Pas 3 — taula de mesures
  const [taula, setTaula] = useState({})              // {pom_master_id: {talla: valor}}
  const [valorsMode, setValorsMode] = useState('absoluts')   // 1C-2b: mode dels valors de la fitxa
  const [gradingLoading, setGradingLoading] = useState(false)
  const [savingMesures, setSavingMesures] = useState(false)

  // Pas 4 — teixit
  const [teixit, setTeixit] = useState({
    fabric_main: '', fabric_composition: '', shrinkage_type: 'NONE',
    shrinkage_warp: '', shrinkage_weft: '', shrinkage_pct: '', shrinkage_iso_key: '', fabric_notes: '',
  })
  const [isoTable, setIsoTable] = useState([])
  const [biaxial, setBiaxial] = useState(true)
  const [savingTeixit, setSavingTeixit] = useState(false)

  // Pas 5 — guardar
  const [confirming, setConfirming] = useState(false)
  // Llei del contenidor: 409 'grading_conflict' (per-regla) i 409 'container_absent' (crear?).
  const [gradingConflict, setGradingConflict] = useState(null)   // {divergencies:[{pom_id,pom,detall}], options}
  const [containerConflict, setContainerConflict] = useState(null) // {customer_nom, garment_type_item, size_system, fit}
  const [conflictChoices, setConflictChoices] = useState({})     // {pom_id: keep_catalog|update_catalog|model_resident}

  const docLabels = cribratge?.run_talles_document || []
  // Columnes del document sense parella model → avís (no bloqueja, tret de la base).
  const senseParella = useMemo(() => tallesSel.filter(d => !mapping[d]), [tallesSel, mapping])
  // 1↔1: talles del model aparellades més d'un cop.
  const modelDup = useMemo(() => {
    const seen = {}, dup = new Set()
    tallesSel.forEach(d => { const m = mapping[d]; if (m) { if (seen[m]) dup.add(m); seen[m] = true } })
    return dup
  }, [tallesSel, mapping])
  // B5 · talla base: columna del document aparellada a la talla base del model.
  const baseDocLabel = useMemo(
    () => tallesSel.find(d => mapping[d] === baseLabel) || null,
    [tallesSel, mapping, baseLabel],
  )
  const basePaired = !!baseDocLabel

  // ── Upload → cribratge
  const handleUpload = async () => {
    if (!file) return
    setUploading(true); setError('')
    const fd = new FormData()
    fd.append('document', file)
    fd.append('model_id', model.id)
    fd.append('garment_type_item_code', model.garment_type_item_code || '')
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/cribratge/`, {
        method: 'POST', headers: authHeaders, body: fd,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setUploading(false); return }
      setSessionToken(data.token)
      setCribratge(data)
      const docs = data.run_talles_document || []
      setTallesSel(docs)
      await loadProposal(data.token, docs)
    } catch (e) {
      setError(t('import_wizard.err_connection', { detail: String(e) }))
    }
    setUploading(false)
  }

  const removeTalla = (label) => {
    setTallesSel(tallesSel.filter(tt => tt !== label))
    setMapping(prev => { const n = { ...prev }; delete n[label]; return n })
  }
  const setPair = (docLabel, modelLabel) =>
    setMapping(prev => ({ ...prev, [docLabel]: modelLabel }))

  // Carrega l'auto-proposta d'aparellament + etiquetes REALS del model (pas 1).
  const loadProposal = async (token, docs) => {
    const res = await fetch(`${API}/api/v1/import-sessions/${token}/talles/`, {
      method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify({ talles_seleccionades: docs }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); return }
    setSystemLabels(data.system_labels || [])
    const mp = {}
    for (const p of (data.talla_mapping || [])) mp[p.document] = p.model
    setMapping(mp)
    setBaseLabel(data.base_size_label || '')
    setBaseAvisos(data.base_avisos || [])
    setSizeMapPrefill(data.size_map_prefill || null)
  }

  // Desa mapping (+ opcionalment la talla base) i retorna la resposta validada.
  const patchTalles = async (extra = {}) => {
    const talla_mapping = tallesSel.map(d => ({ document: d, model: mapping[d] || '' }))
    const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/talles/`, {
      method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
      body: JSON.stringify({ talles_seleccionades: tallesSel, talla_mapping, ...extra }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); return null }
    if (data.base_size_label !== undefined) setBaseLabel(data.base_size_label || '')
    setBaseAvisos(data.base_avisos || [])
    setSizeMapPrefill(data.size_map_prefill || null)
    return data
  }

  // B5 · canvia la talla base del model (persisteix a base_size_label via /talles/).
  const changeBase = async (modelLabel) => {
    setSavingTalles(true); setError('')
    await patchTalles({ base_size_label: modelLabel })
    setSavingTalles(false)
  }

  // Obre el Size Map Setup pre-omplert. Usa el prefill del backend si el tenim;
  // si no, el construeix a partir del que ja sabem (model + talles seleccionades).
  const goConfigureRun = () => {
    const prefill = sizeMapPrefill || {
      target_codi: model?.target || null,
      labels: tallesSel,
      base_size: model?.base_size_label || null,
      import_session_token: sessionToken,
      model_id: model?.id ?? null,
    }
    // 1C-3b: salta a la Size Library (drawer auto-obert per ?prefill). Decisió (ii):
    // sense represa automàtica — l'usuari es queda a la Library i torna al model manualment.
    // token/model_id es deixen al prefill (inerts al camí Library).
    navigate(`/size-library?prefill=${encodeURIComponent(encodePrefill(prefill))}`)
  }

  const handleContinue = async () => {
    setSavingTalles(true); setError('')
    const data = await patchTalles()
    setSavingTalles(false)
    if (!data) return
    if ((data.errors || []).length) { setError(data.errors.join(' ')); return }
    if (data.ready) { setStep(2); runExtraccio() }
    else setError(t('import_wizard.sizes_unpaired', { sizes: (data.no_aparellades || []).join(', ') }))
  }

  // Bloqueig del pas 1: cada columna doc aparellada, 1↔1, i la talla base aparellada (B5).
  const canContinue = tallesSel.length > 0 && senseParella.length === 0
    && modelDup.size === 0 && basePaired && !savingTalles

  // ── Pas 2 — extracció completa (Crida 2)
  const runExtraccio = async () => {
    setExtracting(true); setError('')
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/extraccio/`, {
        method: 'POST', headers: authHeaders,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setExtracting(false); return }
      setPomsExtrets(data.poms_extrets || [])
      setExtraccioMeta({ header: data.header, base_size: data.base_size, sizes: data.sizes,
                         grading_status: data.grading_status, avisos: data.avisos || [] })
      if (data.suggested_valors_mode === 'absoluts' || data.suggested_valors_mode === 'deltes')
        setValorsMode(data.suggested_valors_mode)
    } catch (e) {
      setError(t('import_wizard.err_connection', { detail: String(e) }))
    }
    setExtracting(false)
  }

  const togglePom = (idx) => setPomsExtrets(pomsExtrets.map((p, i) =>
    i === idx ? { ...p, actiu: !p.actiu } : p))

  // POM sense match → marcar/desmarcar com a tenant-only (s'activa i s'afegirà al catàleg).
  const toggleTenantOnly = (idx) => setPomsExtrets(pomsExtrets.map((p, i) =>
    i === idx ? { ...p, tenant_only: !p.tenant_only, actiu: !p.tenant_only } : p))

  const loadCataleg = async () => {
    if (cataleg) { setShowAddPom(true); return }
    try {
      const res = await fetch(`${API}/api/v1/poms/`, { headers: authHeaders })
      const data = await res.json().catch(() => ({}))
      setCataleg(data.results || data || [])
      setShowAddPom(true)
    } catch (e) { setError(t('import_wizard.err_catalog', { detail: String(e) })) }
  }

  const addPomManual = (pm) => {
    if (pomsExtrets.some(p => p.pom_master_id === pm.id)) { setShowAddPom(false); return }
    setPomsExtrets([...pomsExtrets, {
      codi_fitxa: '', descripcio: pm.nom_client || '', pom_master_id: pm.id,
      pom_codi: pm.codi_client, pom_nom: pm.nom_client, match_type: 'manual',
      confidence: 'HIGH', values: {}, actiu: true, ordre: pomsExtrets.length,
    }])
    setShowAddPom(false)
  }

  const handleContinuePoms = async () => {
    setSavingPoms(true); setError('')
    const ids = pomsExtrets.filter(p => p.actiu && p.pom_master_id).map(p => p.pom_master_id)
    const tenantOnly = pomsExtrets
      .filter(p => p.actiu && !p.pom_master_id && p.tenant_only)
      .map(p => p.ordre)
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/poms/`, {
        method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ poms_confirmats: ids, poms_tenant_only: tenantOnly }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setSavingPoms(false); return }
      // El backend retorna els POMs amb els pom_master_id tenant-only ja assignats.
      const updated = data.poms_extrets || pomsExtrets
      setPomsExtrets(updated)
      buildTaula(updated)
      setStep(3)
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setSavingPoms(false)
  }

  const pomsActius = (pomsExtrets || []).filter(p => p.actiu).length

  // ── Pas 3 — taula de mesures
  const pomsTaula = (pomsExtrets || []).filter(p => p.actiu)  // files = POMs actius
  // La columna base de la taula de mesures és la label DOCUMENT aparellada amb la talla base
  // del model (B5); si no, fallback a l'heurística anterior.
  const baseSize = baseDocLabel
    || ((extraccioMeta?.base_size && tallesSel.includes(extraccioMeta.base_size))
      ? extraccioMeta.base_size : tallesSel[0])

  const buildTaula = (src) => {
    const t = {}
    for (const p of (src || pomsExtrets || []).filter(x => x.actiu)) {
      const row = {}
      for (const talla of tallesSel) {
        const v = (p.values || {})[talla]
        row[talla] = (v === undefined || v === null) ? '' : String(v)
      }
      t[p.pom_master_id] = row
    }
    setTaula(t)
  }

  const setCell = (pid, talla, val) =>
    setTaula(prev => ({ ...prev, [pid]: { ...(prev[pid] || {}), [talla]: val } }))

  // Columnes (talles) completament buides → ofereix generar grading.
  const emptyCols = tallesSel.filter(talla =>
    pomsTaula.every(p => !(taula[p.pom_master_id]?.[talla] ?? '').toString().trim()))
  const baseTeValors = pomsTaula.some(p => (taula[p.pom_master_id]?.[baseSize] ?? '').toString().trim())

  const handleGenerarGrading = async () => {
    setGradingLoading(true); setError('')
    const base_values = {}
    for (const p of pomsTaula) {
      const v = taula[p.pom_master_id]?.[baseSize]
      if (v !== undefined && v !== '') base_values[p.pom_master_id] = v
    }
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/grading-preview/`, {
        method: 'POST', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_values }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setGradingLoading(false); return }
      const grading = data.grading || {}
      // Omple NOMÉS les cel·les buides; preserva els valors extrets del document.
      setTaula(prev => {
        const next = { ...prev }
        for (const p of pomsTaula) {
          const g = grading[String(p.pom_master_id)] || {}
          const row = { ...(next[p.pom_master_id] || {}) }
          for (const talla of tallesSel) {
            if (!(row[talla] ?? '').toString().trim() && g[talla] !== undefined)
              row[talla] = String(g[talla])
          }
          next[p.pom_master_id] = row
        }
        return next
      })
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setGradingLoading(false)
  }

  const handleContinueMesures = async () => {
    setSavingMesures(true); setError('')
    const mesures = []
    for (const p of pomsTaula) {
      for (const talla of tallesSel) {
        const v = taula[p.pom_master_id]?.[talla]
        if (v !== undefined && v !== '')
          mesures.push({ pom_master_id: p.pom_master_id, talla_label: talla, valor: parseFloat(v) })
      }
    }
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/mesures/`, {
        method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ mesures, valors_mode: valorsMode }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setSavingMesures(false); return }
      loadIso()
      setStep(4)
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setSavingMesures(false)
  }

  // 1C-3 — destí Size Library: desa mesures (+valors_mode) i salta al drawer de la Library amb
  // el prefill ENRIQUIT (run+base+target+POMs en absoluts). Reutilitza el camí provat
  // size_map_create_view; aquí només preparem el prefill i naveguem.
  const goCrearLibrary = async () => {
    setSavingMesures(true); setError('')
    const mesures = []
    for (const p of pomsTaula) {
      for (const talla of tallesSel) {
        const v = taula[p.pom_master_id]?.[talla]
        if (v !== undefined && v !== '')
          mesures.push({ pom_master_id: p.pom_master_id, talla_label: talla, valor: parseFloat(v) })
      }
    }
    try {
      await fetch(`${API}/api/v1/import-sessions/${sessionToken}/mesures/`, {
        method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify({ mesures, valors_mode: valorsMode }),
      })
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/library-prefill/`, {
        method: 'POST', headers: authHeaders,
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setSavingMesures(false); return }
      navigate(`/size-library?prefill=${encodeURIComponent(encodePrefill(data))}`)
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setSavingMesures(false)
  }

  // ── Pas 4 — teixit
  const loadIso = async () => {
    if (isoTable.length) return
    try {
      const res = await fetch(`${API}/api/v1/models/iso-shrinkage/`, { headers: authHeaders })
      const data = await res.json().catch(() => [])
      setIsoTable(Array.isArray(data) ? data : [])
    } catch { /* iso opcional */ }
  }

  const selectIso = (entry) => {
    setTeixit(t => ({ ...t, shrinkage_type: 'ISO', shrinkage_iso_key: entry.id,
                      shrinkage_warp: entry.warp, shrinkage_weft: entry.weft, shrinkage_pct: '' }))
    setBiaxial(true)
  }

  const buildTeixitPayload = () => {
    const p = {
      fabric_main: teixit.fabric_main, fabric_composition: teixit.fabric_composition,
      shrinkage_type: teixit.shrinkage_type, fabric_notes: teixit.fabric_notes,
      shrinkage_iso_key: teixit.shrinkage_type === 'ISO' ? teixit.shrinkage_iso_key : '',
    }
    if (biaxial) {
      p.shrinkage_warp = teixit.shrinkage_warp !== '' ? parseFloat(teixit.shrinkage_warp) : null
      p.shrinkage_weft = teixit.shrinkage_weft !== '' ? parseFloat(teixit.shrinkage_weft) : null
      p.shrinkage_pct = null
    } else {
      p.shrinkage_pct = teixit.shrinkage_pct !== '' ? parseFloat(teixit.shrinkage_pct) : null
      p.shrinkage_warp = null; p.shrinkage_weft = null
    }
    return p
  }

  const handleSaveTeixit = async (skip) => {
    setSavingTeixit(true); setError('')
    try {
      if (!skip) {
        const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/teixit/`, {
          method: 'PATCH', headers: { ...authHeaders, 'Content-Type': 'application/json' },
          body: JSON.stringify(buildTeixitPayload()),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setSavingTeixit(false); return }
      }
      setStep(5)
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setSavingTeixit(false)
  }

  // ── Pas 5 — confirmar
  const nValors = pomsTaula.reduce((acc, p) =>
    acc + tallesSel.filter(t => (taula[p.pom_master_id]?.[t] ?? '').toString().trim()).length, 0)
  const teixitInformat = !!(teixit.fabric_main || teixit.fabric_composition ||
    teixit.shrinkage_iso_key || teixit.shrinkage_warp || teixit.shrinkage_pct)

  // Llei del contenidor — avís-i-confirma conscient. El backend torna 409:
  //  · 'container_absent' → el client no té contenidor per la combinació: crear? (container_choice)
  //  · 'grading_conflict' → regles de la fitxa que contradiuen el catàleg: tria per-POM
  //    (conflict_resolutions {pom_id: keep_catalog|update_catalog|model_resident}).
  // `bodyExtra` és el que afegim al POST en re-confirmar amb la decisió del tècnic.
  const handleConfirmar = async (bodyExtra = {}) => {
    setConfirming(true); setError('')
    try {
      const res = await fetch(`${API}/api/v1/import-sessions/${sessionToken}/confirmar/`, {
        method: 'POST', headers: { ...authHeaders, 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyExtra),
      })
      const data = await res.json().catch(() => ({}))
      if (res.status === 409 && data.conflict) {
        if (data.tipus === 'container_absent') { setContainerConflict(data); setGradingConflict(null) }
        else if (data.tipus === 'grading_conflict') {
          setGradingConflict(data); setContainerConflict(null)
          // per defecte: mantenir el catàleg per a cada POM en conflicte.
          const defaults = {}
          for (const d of (data.divergencies || [])) defaults[d.pom_id] = 'keep_catalog'
          setConflictChoices(defaults)
        }
        setConfirming(false); return
      }
      if (res.status === 422 && data.tipus === 'base_size_absent') {
        setError(t('import_wizard.err_base_size_absent', {
          base_size: data.base_size, etiquetes: (data.etiquetes || []).join(', ') || '—' }))
        setConfirming(false); return
      }
      if (!res.ok) { setError(data.error || t('import_wizard.err_status', { status: res.status })); setConfirming(false); return }
      setGradingConflict(null); setContainerConflict(null)
      onComplete && onComplete(data.model_id)
    } catch (e) { setError(t('import_wizard.err_connection', { detail: String(e) })) }
    setConfirming(false)
  }

  // ─────────────────────────── Render ───────────────────────────
  return (
    <div style={{ }}>
      <Stepper step={step} />

      {error && (
        <div style={{ background: '#fff0f0', border: '1px solid #f0c0c0', color: '#a32d2d',
                      borderRadius: 8, padding: '8px 12px', fontSize: 'var(--fs-body)', marginBottom: 12 }}>
          {error}
        </div>
      )}

      {/* ═══════════════ PAS 1 — TALLES ═══════════════ */}
      {step === 1 && !cribratge && (
        <div>
          <div style={{ marginBottom: 16 }}>
            <FileDropCard
              accept={['.xlsx', '.xls', '.pdf', '.png', '.jpg', '.jpeg']}
              icon="ti-file-spreadsheet"
              title={t('import_wizard.drop_file')}
              required
              file={file}
              onFile={setFile}
              disabled={uploading}
              hint={t('import_wizard.file_hint')}
            />
          </div>
          {file && (
            <div style={{ textAlign: 'center' }}>
              <button type="button" onClick={handleUpload} disabled={uploading}
                style={{ padding: '10px 24px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)',
                         fontWeight: 600, background: uploading ? '#ccc' : GOLD, color: 'var(--white)',
                         cursor: uploading ? 'not-allowed' : 'pointer' }}>
                {uploading ? t('import_wizard.analyzing_doc') : t('import_wizard.analyze_sizes')}
              </button>
            </div>
          )}
        </div>
      )}

      {step === 1 && cribratge && (
        <div>
          {/* Avís multi-model (gating de cribratge, no bloqueja el pas de talles) */}
          {cribratge.num_models > 1 && (
            <div style={{ background: '#fdf6ee', border: '1px solid #e0c8a0', color: 'var(--gold)',
                          borderRadius: 8, padding: '8px 12px', fontSize: 'var(--fs-body)', marginBottom: 12 }}>
              ⚠ {t('import_wizard.multimodel_warn', { count: cribratge.num_models, names: (cribratge.model_detectat || []).map(m => m.nom).join(', ') })}
            </div>
          )}

          {/* Aparellament document ⟷ model (LA LLEI de la sessió) */}
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 8 }}>
            {t('import_wizard.pairing_intro')}
          </div>

          {/* B5 · targeta de la TALLA BASE (selector limitat a les SizeDefinition del system) */}
          <div style={{ border: `1px solid ${basePaired ? '#c0dd97' : '#f0c0c0'}`, borderRadius: 8,
                        padding: '10px 12px', marginBottom: 12, background: basePaired ? '#f7fbf2' : '#fff6f6' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 'var(--fs-body)', fontWeight: 600 }}>★ {t('import_wizard.base_size')}:</span>
              <select value={baseLabel} disabled={savingTalles} onChange={e => changeBase(e.target.value)}
                style={{ padding: '4px 8px', borderRadius: 6, border: `1px solid ${BORDER}`, fontSize: 'var(--fs-body)' }}>
                {systemLabels.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <span style={{ color: 'var(--text-muted)' }}>⟷</span>
              <span style={{ fontSize: 'var(--fs-body)', color: basePaired ? '#3b6d11' : '#a32d2d' }}>
                {baseDocLabel || t('import_wizard.base_unpaired')}
              </span>
            </div>
            {baseAvisos.map((a, i) => (
              <div key={i} style={{ marginTop: 6, fontSize: 'var(--fs-small)', color: GOLD }}>⚠ {a}</div>
            ))}
          </div>

          {/* Taula d'aparellament: una fila per etiqueta del document, selector de talla del model */}
          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, padding: 12, marginBottom: 16 }}>
            <div style={{ display: 'flex', gap: 10, fontSize: 'var(--fs-body)', fontWeight: 600,
                          color: 'var(--text-muted)', paddingBottom: 6, borderBottom: `0.5px solid ${BORDER}`, marginBottom: 6 }}>
              <div style={{ width: 110 }}>{t('import_wizard.doc_sizes')} <span style={{ fontWeight: 400 }}>({cribratge.sistema_talles})</span></div>
              <div style={{ width: 20 }} />
              <div>{t('import_wizard.model_sizes')}</div>
            </div>
            {tallesSel.map(d => {
              const m = mapping[d] || ''
              const isBaseRow = !!m && m === baseLabel
              const dup = !!m && modelDup.has(m)
              const state = !m ? 'unpaired' : dup ? 'dup' : 'ok'
              return (
                <div key={d} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 0' }}>
                  <div style={{ width: 110, fontWeight: isBaseRow ? 700 : 400 }}>
                    {isBaseRow ? '★ ' : ''}{d}
                  </div>
                  <span style={{ width: 20, color: 'var(--text-muted)', textAlign: 'center' }}>⟷</span>
                  <select value={m} disabled={savingTalles} onChange={e => setPair(d, e.target.value)}
                    style={{ padding: '4px 8px', borderRadius: 6, fontSize: 'var(--fs-body)', minWidth: 130,
                             border: `1px solid ${state === 'ok' ? '#c0dd97' : '#f0c0c0'}` }}>
                    <option value="">{t('import_wizard.no_pair')}</option>
                    {systemLabels.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                  <span title={t(`import_wizard.pair_${state}`)}
                    style={{ color: state === 'ok' ? '#3b6d11' : '#a32d2d' }}>
                    {state === 'ok' ? '✓' : '⚠'}
                  </span>
                  <button type="button" onClick={() => removeTalla(d)} title={t('import_wizard.remove_size')}
                    style={{ border: 'none', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 'var(--fs-h3)' }}>×</button>
                </div>
              )
            })}
          </div>

          {/* Columnes del document sense parella → avís no bloquejant (la base sí bloqueja) */}
          {senseParella.length > 0 && (
            <div style={{ background: '#fff0f0', border: '1px solid #f0c0c0', borderRadius: 8,
                          padding: '10px 12px', marginBottom: 16 }}>
              <div style={{ fontSize: 'var(--fs-body)', color: '#a32d2d', marginBottom: 8 }}>
                {t('import_wizard.unpaired_warn', { count: senseParella.length, sizes: senseParella.join(', ') })}
              </div>
              <button type="button" onClick={() => setConfirmSizeMap(true)}
                style={{ padding: '6px 14px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer',
                         border: '0.5px solid #c0c0c0', background: 'transparent', color: '#666' }}>
                ⚙ {t('import_wizard.configure_client_run')}
              </button>
            </div>
          )}

          {/* Navegació */}
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
            <button type="button" onClick={onCancel}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
              ← {t('app.cancel')}
            </button>
            <button type="button" onClick={handleContinue} disabled={!canContinue}
              title={canContinue ? '' : t('import_wizard.resolve_mismatch')}
              style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)',
                       fontWeight: 500, color: 'var(--white)', background: canContinue ? GOLD : '#ccc',
                       cursor: canContinue ? 'pointer' : 'not-allowed' }}>
              {t('import_wizard.continue_poms')}
            </button>
          </div>
        </div>
      )}

      {/* ═══════════════ PAS 2 — POMs ═══════════════ */}
      {step === 2 && (
        <div>
          {/* Talles confirmades (Pas 1) sempre visibles */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 6 }}>
              {t('import_wizard.confirmed_sizes')}
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {tallesSel.map(t => (
                <span key={t} style={{ padding: '3px 9px', borderRadius: 6, fontSize: 'var(--fs-body)',
                                       border: `1px solid #c0dd97`, background: '#f0f9f0', color: '#3b6d11' }}>{t}</span>
              ))}
            </div>
          </div>

          {extracting && (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: 28, marginBottom: 12 }}>⏳</div>
              <div style={{ fontSize: 'var(--fs-h3)' }}>{t('import_wizard.extracting_poms')}</div>
              <div style={{ fontSize: 'var(--fs-body)', marginTop: 4 }}>{t('import_wizard.vision_analysis')}</div>
            </div>
          )}

          {!extracting && pomsExtrets && (
            <div>
              {/* Avisos d'extracció */}
              {(extraccioMeta?.avisos || []).length > 0 && (
                <div style={{ background: '#fdf6ee', border: '1px solid #e0c8a0', color: 'var(--gold)',
                              borderRadius: 8, padding: '8px 12px', fontSize: 'var(--fs-body)', marginBottom: 12 }}>
                  {extraccioMeta.avisos.map((a, i) => <div key={i}>⚠ {a}</div>)}
                </div>
              )}

              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 8 }}>
                {t('import_wizard.poms_summary', { count: pomsExtrets.length, active: pomsActius })}
                {extraccioMeta?.base_size && <> · {t('import_wizard.base_size_label')}: <b>{extraccioMeta.base_size}</b></>}
              </div>

              <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, overflow: 'hidden', marginBottom: 16 }}>
                {pomsExtrets.map((p, idx) => {
                  const conf = (p.confidence || '').toUpperCase()
                  const low = conf === 'LOW' || conf === 'NO_MATCH'
                  const med = conf === 'MEDIUM'
                  const noMatch = !p.pom_master_id
                  const tenantOnly = noMatch && !!p.tenant_only
                  // QA-S8 · PENDENT: el backend ha trobat alguna cosa però NO l'ha vinculada
                  // (confiança baixa, o dues files de la fitxa apuntant al mateix POM). No és
                  // un "sense match": és un suggeriment que espera una decisió humana, i s'ha
                  // de veure com a tal — si no, la persona no sap què li estan proposant.
                  const pendent = noMatch && !!p.weak_suggestion && !tenantOnly
                  return (
                    <div key={idx} style={{
                      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
                      borderTop: idx ? `1px solid ${BORDER}` : 'none',
                      background: !p.actiu ? '#f7f7f5' : tenantOnly ? '#f3f0fb' : low ? '#fdf3ee' : 'var(--white)',
                      opacity: p.actiu ? 1 : 0.55,
                    }}>
                      <input type="checkbox" checked={!!p.actiu}
                        onChange={() => noMatch ? toggleTenantOnly(idx) : togglePom(idx)} />
                      <div style={{ flex: '0 0 90px', fontWeight: 600, fontSize: 'var(--fs-body)' }}>
                        {p.codi_fitxa || '—'}
                      </div>
                      <div style={{ fontSize: 'var(--fs-h3)', color: 'var(--text-muted)' }}>→</div>
                      <div style={{ flex: 1, fontSize: 'var(--fs-body)' }}>
                        {noMatch
                          ? (tenantOnly
                              ? <span style={{ color: '#5b3fa3' }}>
                                  {p.descripcio || t('import_wizard.no_description')}
                                  <span style={{ marginLeft: 8, fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
                                    {t('import_wizard.will_add_tenant')}
                                  </span>
                                </span>
                              : <span style={{ color: pendent ? 'var(--gold)' : '#a32d2d' }}>
                                  {pendent
                                    ? t('import_wizard.pending_review')
                                    : t('import_wizard.no_match')} — {p.descripcio || t('import_wizard.no_description')}
                                  {pendent && (
                                    <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 2 }}>
                                      {p.many_to_one
                                        ? t('import_wizard.many_to_one_hint', { codi: p.weak_suggestion_codi })
                                        : t('import_wizard.weak_hint')}
                                      {' '}<b>{p.weak_suggestion_codi}</b> · {p.weak_suggestion}
                                    </div>
                                  )}
                                  <span onClick={() => toggleTenantOnly(idx)}
                                    style={{ marginLeft: 8, fontSize: 'var(--fs-body)', color: GOLD,
                                             cursor: 'pointer', textDecoration: 'underline' }}>
                                    {t('import_wizard.add_as_own')}
                                  </span>
                                </span>)
                          : <><b>{p.pom_codi}</b> · {p.pom_nom || p.descripcio}</>}
                      </div>
                      <span style={{
                        fontSize: 'var(--fs-body)', fontWeight: 600, padding: '2px 8px', borderRadius: 10,
                        background: tenantOnly ? '#ede7fb' : pendent ? '#fdf6ee' : noMatch ? '#fff0f0' : (low || med) ? '#fdf6ee' : '#f0f9f0',
                        color: tenantOnly ? '#5b3fa3' : pendent ? 'var(--gold)' : noMatch ? '#a32d2d' : (low || med) ? 'var(--gold)' : '#3b6d11',
                      }}>{tenantOnly ? 'tenant-only'
                          : pendent ? t('import_wizard.pending_badge')
                          : noMatch ? t('import_wizard.no_match_badge') : conf.toLowerCase()}</span>
                    </div>
                  )
                })}
              </div>

              {/* Afegir POM manual del catàleg */}
              <div style={{ marginBottom: 16 }}>
                {!showAddPom ? (
                  <button type="button" onClick={loadCataleg}
                    style={{ padding: '6px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer',
                             border: `1px dashed ${GOLD}`, background: 'transparent', color: GOLD }}>
                    {t('import_wizard.add_pom_catalog')}
                  </button>
                ) : (
                  <select onChange={e => { const pm = (cataleg || []).find(c => String(c.id) === e.target.value); if (pm) addPomManual(pm) }}
                    defaultValue=""
                    style={{ padding: '8px', borderRadius: 6, fontSize: 'var(--fs-body)', border: `1px solid ${BORDER}`,
                             fontFamily: 'inherit', minWidth: 320 }}>
                    <option value="" disabled>{t('import_wizard.choose_pom')}</option>
                    {(cataleg || []).map(c => (
                      <option key={c.id} value={c.id}>{c.codi_client} · {c.nom_client}</option>
                    ))}
                  </select>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <button type="button" onClick={() => setStep(1)}
                  style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                           background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
                  ← {t('app.back')}
                </button>
                <button type="button" onClick={handleContinuePoms} disabled={pomsActius === 0 || savingPoms}
                  style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)',
                           fontWeight: 500, color: 'var(--white)',
                           background: pomsActius && !savingPoms ? GOLD : '#ccc',
                           cursor: pomsActius && !savingPoms ? 'pointer' : 'not-allowed' }}>
                  {t('import_wizard.continue_measures')}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══════════════ PAS 3 — MESURES ═══════════════ */}
      {step === 3 && (
        <div>
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 10 }}>
            {t('import_wizard.table_intro', { poms: pomsTaula.length, sizes: tallesSel.length, base: baseSize })}
          </div>

          {/* 1C-2b — com estan expressats els valors de la fitxa (default suggerit per l'heurística) */}
          <div style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button type="button" onClick={() => setValorsMode('absoluts')}
                style={{ padding: '4px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer', border: 'none',
                         background: valorsMode === 'absoluts' ? GOLD : '#f5f0ea',
                         color: valorsMode === 'absoluts' ? 'var(--white)' : 'var(--text-muted)' }}>{t('import_wizard.absolute_measures')}</button>
              <button type="button" onClick={() => setValorsMode('deltes')}
                style={{ padding: '4px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer', border: 'none',
                         background: valorsMode === 'deltes' ? GOLD : '#f5f0ea',
                         color: valorsMode === 'deltes' ? 'var(--white)' : 'var(--text-muted)' }}>{t('import_wizard.increments')}</button>
            </div>
            <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginTop: 5 }}>
              {t('import_wizard.values_help')}{valorsMode === 'deltes'
                ? t('import_wizard.values_help_deltes') : ''}
            </div>
          </div>

          {emptyCols.length > 0 && (
            <div style={{ background: '#fdf6ee', border: '1px solid #e0c8a0', color: 'var(--gold)',
                          borderRadius: 8, padding: '8px 12px', fontSize: 'var(--fs-body)', marginBottom: 10,
                          display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
              <span>{t('import_wizard.sizes_no_values')} <b>{emptyCols.join(', ')}</b>.</span>
              <button type="button" onClick={handleGenerarGrading} disabled={gradingLoading || !baseTeValors}
                title={baseTeValors ? '' : t('import_wizard.need_base_values')}
                style={{ padding: '6px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', whiteSpace: 'nowrap',
                         border: `1px solid ${GOLD}`, background: 'transparent', color: GOLD,
                         cursor: baseTeValors && !gradingLoading ? 'pointer' : 'not-allowed' }}>
                {gradingLoading ? t('import_wizard.generating') : t('import_wizard.generate_grading')}
              </button>
            </div>
          )}

          <div style={{ overflowX: 'auto', border: `1px solid ${BORDER}`, borderRadius: 8, marginBottom: 16 }}>
            <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 'var(--fs-body)' }}>
              <thead>
                <tr style={{ background: '#f5f0ea' }}>
                  <th style={{ padding: '8px 10px', textAlign: 'left', position: 'sticky', left: 0,
                               background: '#f5f0ea', minWidth: 160 }}>POM</th>
                  {tallesSel.map(talla => (
                    <th key={talla} style={{ padding: '8px 10px', textAlign: 'center', minWidth: 64,
                          background: talla === baseSize ? '#f0e7cf' : '#f5f0ea',
                          color: talla === baseSize ? '#7a5a00' : 'var(--text-main)' }}>
                      {talla}{talla === baseSize && <div style={{ fontSize: 'var(--fs-caption)' }}>{t('import_wizard.col_base')}</div>}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pomsTaula.map(p => (
                  <tr key={p.pom_master_id} style={{ borderTop: `1px solid ${BORDER}` }}>
                    <td style={{ padding: '6px 10px', position: 'sticky', left: 0, background: 'var(--white)' }}>
                      {/* QA-S8 · El codi del DOCUMENT mana: és el que la persona té al paper
                          davant. El del catàleg queda com a secundari i atenuat, i només si
                          difereix. Abans manava el del catàleg i la fitxa deia 'A' mentre la
                          pantalla deia 'CH': no hi havia manera de relacionar-les.
                          Coherent amb el pas 2 (:681) i amb MeasureGrid (nom_fitxa || pom_code). */}
                      <b>{p.codi_fitxa || p.pom_codi}</b>
                      {p.pom_codi && p.codi_fitxa && p.pom_codi !== p.codi_fitxa && (
                        <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}> → {p.pom_codi}</span>
                      )}
                      <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)' }}>{p.pom_nom || p.descripcio}</div>
                    </td>
                    {tallesSel.map(talla => (
                      <td key={talla} style={{ padding: '2px', textAlign: 'center',
                            background: talla === baseSize ? '#fbf7ec' : 'var(--white)' }}>
                        <input type="number" step="0.1"
                          value={taula[p.pom_master_id]?.[talla] ?? ''}
                          onChange={e => setCell(p.pom_master_id, talla, e.target.value)}
                          style={{ width: 56, padding: '4px', textAlign: 'center', fontSize: 'var(--fs-body)',
                                   border: `1px solid ${BORDER}`, borderRadius: 4,
                                   fontFamily: 'inherit' }} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button type="button" onClick={() => setStep(2)}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>
              ← {t('app.back')}
            </button>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" onClick={goCrearLibrary} disabled={!baseTeValors || savingMesures}
                title={baseTeValors ? t('import_wizard.create_library_title')
                                    : t('import_wizard.base_needs_value')}
                style={{ padding: '8px 16px', borderRadius: 6, border: `1px solid ${GOLD}`,
                         background: 'transparent', color: GOLD, fontSize: 'var(--fs-body)',
                         cursor: baseTeValors && !savingMesures ? 'pointer' : 'not-allowed' }}>
                {t('import_wizard.create_library')}
              </button>
              <button type="button" onClick={handleContinueMesures} disabled={!baseTeValors || savingMesures}
                title={baseTeValors ? '' : t('import_wizard.base_needs_value')}
                style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)',
                         fontWeight: 500, color: 'var(--white)',
                         background: baseTeValors && !savingMesures ? GOLD : '#ccc',
                         cursor: baseTeValors && !savingMesures ? 'pointer' : 'not-allowed' }}>
                {t('import_wizard.continue_fabric')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════ PAS 4 — TEIXIT ═══════════════ */}
      {step === 4 && (
        <div>
          <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginBottom: 12 }}>
            {t('import_wizard.fabric_and_shrinkage')} <b>{t('import_wizard.optional')}</b> {t('import_wizard.skip_step_hint')}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 14 }}>
            <div>
              <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>{t('import_wizard.fabric_main_label')}</label>
              <input value={teixit.fabric_main}
                onChange={e => setTeixit(prev => ({ ...prev, fabric_main: e.target.value }))}
                placeholder={t('import_wizard.fabric_main_ph')}
                style={{ width: '100%', padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6,
                         border: `1px solid ${BORDER}`, boxSizing: 'border-box', fontFamily: 'inherit' }} />
            </div>
            <div>
              <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>{t('import_wizard.composition')}</label>
              <input value={teixit.fabric_composition}
                onChange={e => setTeixit(prev => ({ ...prev, fabric_composition: e.target.value }))}
                placeholder={t('import_wizard.composition_ph')}
                style={{ width: '100%', padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6,
                         border: `1px solid ${BORDER}`, boxSizing: 'border-box', fontFamily: 'inherit' }} />
            </div>
          </div>

          <div style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {t('import_wizard.shrinkage_iso')}
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
              {isoTable.map(entry => {
                const active = teixit.shrinkage_type === 'ISO' && teixit.shrinkage_iso_key === entry.id
                return (
                  <button key={entry.id} type="button" onClick={() => selectIso(entry)}
                    style={{ padding: '4px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer',
                             border: active ? `1.5px solid ${GOLD}` : `0.5px solid ${BORDER}`,
                             background: active ? '#fdf6ee' : 'transparent', color: 'var(--text-muted)' }}>
                    {entry.nom} <span style={{ fontSize: 'var(--fs-body)' }}>{entry.warp}%/{entry.weft}%</span>
                  </button>
                )
              })}
            </div>
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <button type="button" onClick={() => setBiaxial(true)}
                style={{ padding: '4px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer', border: 'none',
                         background: biaxial ? GOLD : '#f5f0ea', color: biaxial ? 'var(--white)' : 'var(--text-muted)' }}>Warp / Weft</button>
              <button type="button" onClick={() => setBiaxial(false)}
                style={{ padding: '4px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', cursor: 'pointer', border: 'none',
                         background: !biaxial ? GOLD : '#f5f0ea', color: !biaxial ? 'var(--white)' : 'var(--text-muted)' }}>Single %</button>
            </div>
            {biaxial ? (
              <div style={{ display: 'flex', gap: 12 }}>
                <input type="number" step="0.5" min="0" max="30" value={teixit.shrinkage_warp}
                  onChange={e => setTeixit(t => ({ ...t, shrinkage_warp: e.target.value, shrinkage_type: 'SUPPLIER', shrinkage_iso_key: '' }))}
                  placeholder="Warp %" style={{ width: 90, padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6, border: `1px solid ${BORDER}`, fontFamily: 'inherit' }} />
                <input type="number" step="0.5" min="0" max="30" value={teixit.shrinkage_weft}
                  onChange={e => setTeixit(t => ({ ...t, shrinkage_weft: e.target.value, shrinkage_type: 'SUPPLIER', shrinkage_iso_key: '' }))}
                  placeholder="Weft %" style={{ width: 90, padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6, border: `1px solid ${BORDER}`, fontFamily: 'inherit' }} />
              </div>
            ) : (
              <input type="number" step="0.5" min="0" max="30" value={teixit.shrinkage_pct}
                onChange={e => setTeixit(t => ({ ...t, shrinkage_pct: e.target.value, shrinkage_type: 'SUPPLIER' }))}
                placeholder="Shrinkage %" style={{ width: 110, padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6, border: `1px solid ${BORDER}`, fontFamily: 'inherit' }} />
            )}
          </div>

          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 'var(--fs-body)', color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>{t('import_wizard.notes')}</label>
            <textarea value={teixit.fabric_notes} rows={2}
              onChange={e => setTeixit(t => ({ ...t, fabric_notes: e.target.value }))}
              style={{ width: '100%', padding: '7px 10px', fontSize: 'var(--fs-body)', borderRadius: 6, resize: 'vertical',
                       border: `1px solid ${BORDER}`, boxSizing: 'border-box', fontFamily: 'inherit' }} />
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button type="button" onClick={() => setStep(3)}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>← {t('app.back')}</button>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" onClick={() => handleSaveTeixit(true)} disabled={savingTeixit}
                style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                         background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>{t('import_wizard.skip')}</button>
              <button type="button" onClick={() => handleSaveTeixit(false)} disabled={savingTeixit}
                style={{ padding: '8px 20px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)', fontWeight: 500,
                         color: 'var(--white)', background: GOLD, cursor: 'pointer' }}>{t('import_wizard.continue_save')}</button>
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════ PAS 5 — GUARDAR ═══════════════ */}
      {step === 5 && (
        <div>
          <div style={{ fontSize: 'var(--fs-h3)', fontWeight: 600, marginBottom: 12 }}>{t('import_wizard.summary_title')}</div>
          <div style={{ border: `1px solid ${BORDER}`, borderRadius: 8, overflow: 'hidden', marginBottom: 16 }}>
            {[
              [t('import_wizard.target_model'), `${model.codi_intern} · ${model.nom_prenda || ''}`],
              [t('import_wizard.step.sizes'), `${tallesSel.length} (${tallesSel.join('·')})`],
              [t('import_wizard.step.poms'), t('import_wizard.confirmed_count', { count: pomsActius })],
              [t('import_wizard.measure_values'), `${nValors}`],
              [t('import_wizard.step.fabric'), teixitInformat ? (teixit.fabric_main || t('import_wizard.fabric_informed')) : t('import_wizard.fabric_not_informed')],
            ].map(([k, v], i) => (
              <div key={k} style={{ display: 'flex', padding: '8px 12px', fontSize: 'var(--fs-body)',
                                    borderTop: i ? `1px solid ${BORDER}` : 'none' }}>
                <div style={{ flex: '0 0 160px', color: 'var(--text-muted)' }}>{k}</div>
                <div style={{ flex: 1, fontWeight: 500 }}>{v}</div>
              </div>
            ))}
          </div>

          <div style={{ background: '#f0f9f0', border: '1px solid #c0dd97', color: '#3b6d11',
                        borderRadius: 8, padding: '8px 12px', fontSize: 'var(--fs-body)', marginBottom: 16 }}>
            {t('import_wizard.mana_doc', { count: pomsActius })}
          </div>

          {/* Llei del contenidor — combinació verge: el client no té contenidor per aquesta
              (peça + sistema de talles + fit). Crear-lo (acte explícit) o deixar el model amb
              residents i prou (sobirania). MAI creació silenciosa. */}
          {containerConflict && (
            <div style={{ background: '#fff9e6', border: '1px solid #f0c040', borderRadius: 8,
                          padding: '12px 14px', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600,
                            fontSize: 'var(--fs-body)', color: '#7a5a00', marginBottom: 6 }}>
                <i className="ti ti-package" aria-hidden="true" />
                {t('import_wizard.container_absent_title')}
              </div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', marginBottom: 10 }}>
                {t('import_wizard.container_absent_help', {
                  customer: containerConflict.customer_nom || '',
                  item: containerConflict.garment_type_item || '',
                  size_system: containerConflict.size_system || '',
                  fit: containerConflict.fit || '',
                })}
              </div>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <button type="button" onClick={() => handleConfirmar({ container_choice: 'create' })} disabled={confirming}
                  style={{ padding: '8px 14px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-body)',
                           fontWeight: 500, color: 'var(--white)', background: GOLD,
                           cursor: confirming ? 'not-allowed' : 'pointer' }}>
                  {t('import_wizard.container_create')}
                </button>
                <button type="button" onClick={() => handleConfirmar({ container_choice: 'no_container' })} disabled={confirming}
                  style={{ padding: '8px 14px', borderRadius: 6, border: `0.5px solid ${BORDER}`,
                           fontSize: 'var(--fs-body)', fontWeight: 500, background: 'var(--white)',
                           color: 'var(--text-main)', cursor: confirming ? 'not-allowed' : 'pointer' }}>
                  {t('import_wizard.container_skip')}
                </button>
              </div>
            </div>
          )}

          {/* Llei del contenidor — conflicte per-regla: la fitxa contradiu el catàleg del client.
              Per a cada POM: mantenir catàleg / actualitzar-lo / deixar-lo resident-només al model. */}
          {gradingConflict && (
            <div style={{ background: '#fff9e6', border: '1px solid #f0c040', borderRadius: 8,
                          padding: '12px 14px', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600,
                            fontSize: 'var(--fs-body)', color: '#7a5a00', marginBottom: 6 }}>
                <i className="ti ti-alert-triangle" aria-hidden="true" />
                {t('import_wizard.grading_conflict_title')}
              </div>
              <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', marginBottom: 8 }}>
                {t('import_wizard.grading_conflict_help')}
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10, alignItems: 'center' }}>
                <span style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
                  {t('import_wizard.conflict_apply_all')}:
                </span>
                {['keep_catalog', 'update_catalog', 'model_resident'].map(opt => (
                  <button key={opt} type="button" disabled={confirming}
                    onClick={() => {
                      const all = {}
                      for (const d of (gradingConflict.divergencies || [])) all[d.pom_id] = opt
                      setConflictChoices(all)
                    }}
                    style={{ padding: '3px 10px', borderRadius: 12, border: `0.5px solid ${BORDER}`,
                             background: 'var(--white)', fontSize: 'var(--fs-caption)',
                             color: 'var(--text-main)', cursor: confirming ? 'not-allowed' : 'pointer' }}>
                    {t(`import_wizard.conflict_${opt}`)}
                  </button>
                ))}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
                {(gradingConflict.divergencies || []).map(d => (
                  <div key={d.pom_id} style={{ borderTop: `0.5px solid ${BORDER}`, paddingTop: 8 }}>
                    <div style={{ fontSize: 'var(--fs-body)', fontWeight: 500, color: 'var(--text-main)' }}>{d.pom}</div>
                    <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', marginBottom: 6 }}>{d.detall}</div>
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {['keep_catalog', 'update_catalog', 'model_resident'].map(opt => {
                        const active = conflictChoices[d.pom_id] === opt
                        return (
                          <button key={opt} type="button" disabled={confirming}
                            onClick={() => setConflictChoices(prev => ({ ...prev, [d.pom_id]: opt }))}
                            style={{ padding: '4px 10px', borderRadius: 6,
                                     border: `${active ? '1px' : '0.5px'} solid ${active ? GOLD : BORDER}`,
                                     background: active ? '#fffdf5' : 'var(--white)',
                                     fontWeight: active ? 600 : 500, fontSize: 'var(--fs-caption)',
                                     color: 'var(--text-main)', cursor: confirming ? 'not-allowed' : 'pointer' }}>
                            {t(`import_wizard.conflict_${opt}`)}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
              <button type="button" disabled={confirming}
                onClick={() => handleConfirmar({ conflict_resolutions: conflictChoices })}
                style={{ padding: '8px 16px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-body)',
                         fontWeight: 600, color: 'var(--white)', background: GOLD,
                         cursor: confirming ? 'not-allowed' : 'pointer' }}>
                {t('import_wizard.conflict_apply')}
              </button>
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <button type="button" onClick={() => setStep(4)}
              style={{ padding: '8px 16px', border: `0.5px solid ${BORDER}`, borderRadius: 6,
                       background: 'transparent', cursor: 'pointer', fontSize: 'var(--fs-body)' }}>← {t('app.back')}</button>
            <button type="button" onClick={() => handleConfirmar()} disabled={confirming || !!gradingConflict || !!containerConflict}
              style={{ padding: '8px 24px', borderRadius: 6, border: 'none', fontSize: 'var(--fs-h3)', fontWeight: 600,
                       color: 'var(--white)', background: (confirming || gradingConflict || containerConflict) ? '#ccc' : GOLD,
                       cursor: (confirming || gradingConflict || containerConflict) ? 'not-allowed' : 'pointer' }}>
              {confirming ? t('import_wizard.confirming') : t('import_wizard.confirm_save')}
            </button>
          </div>
        </div>
      )}

      {confirmSizeMap && (
        <Modal
          title={t('import_wizard.configure_run_title')}
          confirmLabel={t('import_wizard.go_to_library')}
          cancelLabel={t('app.cancel')}
          onCancel={() => setConfirmSizeMap(false)}
          onConfirm={() => { setConfirmSizeMap(false); goConfigureRun() }}
        >
          <p style={{ fontSize: 'var(--fs-body)', color: '#444', lineHeight: 1.5 }}>
            {t('import_wizard.modal_body')}
          </p>
        </Modal>
      )}
    </div>
  )
}
