import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import GarmentTypeSelector from '../components/GarmentTypeSelector/GarmentTypeSelector'

const API = import.meta.env.VITE_API_URL || ''
const currentYear = new Date().getFullYear()
const YEARS = [currentYear, currentYear + 1, currentYear + 2, currentYear + 3]

const SEASONS = [
  { codi: 'SS', nom: 'Spring/Summer' },
  { codi: 'FW', nom: 'Fall/Winter' },
  { codi: 'RE', nom: 'Resort' },
  { codi: 'PRE', nom: 'Pre-collection' },
]

const TARGETS = [
  { codi: 'WOMAN', nom_en: 'Woman', nom_ca: 'Dona' },
  { codi: 'MAN', nom_en: 'Man', nom_ca: 'Home' },
  { codi: 'UNISEX_ADULT', nom_en: 'Unisex Adult', nom_ca: 'Unisex adult' },
  { codi: 'BABY_GIRL', nom_en: 'Baby Girl', nom_ca: 'Nadó nena' },
  { codi: 'BABY_BOY', nom_en: 'Baby Boy', nom_ca: 'Nadó nen' },
  { codi: 'BABY_UNISEX', nom_en: 'Baby Unisex', nom_ca: 'Nadó unisex' },
  { codi: 'TODDLER_GIRL', nom_en: 'Toddler Girl', nom_ca: 'Nena toddler' },
  { codi: 'TODDLER_BOY', nom_en: 'Toddler Boy', nom_ca: 'Nen toddler' },
  { codi: 'GIRL', nom_en: 'Girl', nom_ca: 'Nena' },
  { codi: 'BOY', nom_en: 'Boy', nom_ca: 'Nen' },
  { codi: 'TEEN_GIRL', nom_en: 'Teen Girl', nom_ca: 'Adolescent nena' },
  { codi: 'TEEN_BOY', nom_en: 'Teen Boy', nom_ca: 'Adolescent nen' },
  { codi: 'MATERNITY', nom_en: 'Maternity', nom_ca: 'Maternitat' },
]

const CONSTRUCTIONS = [
  { codi: 'WOVEN', nom: 'Woven (Plana)', desc: 'Teixit pla' },
  { codi: 'KNIT', nom: 'Knit (Punt Jersey)', desc: 'Teixit de punt · Spec en HALF (½)' },
  { codi: 'STRETCH_KNIT', nom: 'Stretch Knit (Punt elàstic)', desc: 'Punt elàstic · Spec en HALF (½)' },
  { codi: 'TECHNICAL', nom: 'Technical', desc: 'Tècnic' },
]

const BORDER = '0.5px solid var(--color-border-tertiary, #e0d5c5)'

const chipStyle = (active) => ({
  padding: '6px 14px',
  borderRadius: 6,
  border: active ? '1.5px solid var(--gold)' : BORDER,
  background: active ? 'var(--gold)' : 'transparent',
  color: active ? '#fff' : 'var(--color-text-primary, #1d1d1b)',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: active ? 500 : 400,
  fontFamily: 'IBM Plex Mono, monospace',
})

const primaryBtn = (disabled) => ({
  background: disabled ? '#ccc' : 'var(--gold)',
  color: '#fff',
  border: 'none',
  borderRadius: 6,
  padding: '8px 20px',
  fontSize: 14,
  fontWeight: 500,
  cursor: disabled ? 'not-allowed' : 'pointer',
  opacity: disabled ? 0.6 : 1,
  fontFamily: 'IBM Plex Mono, monospace',
})

const secondaryBtn = {
  background: '#fff',
  color: 'var(--gold)',
  border: '0.5px solid var(--gold)',
  borderRadius: 6,
  padding: '6px 14px',
  fontSize: 12,
  cursor: 'pointer',
  fontFamily: 'IBM Plex Mono, monospace',
}

const labelStyle = {
  fontSize: 11,
  color: 'var(--color-text-secondary, var(--text-muted, #868685))',
  textTransform: 'uppercase',
  letterSpacing: '.04em',
  fontFamily: 'IBM Plex Mono, monospace',
}

const inputStyle = {
  width: '100%',
  padding: '8px 10px',
  borderRadius: 4,
  border: BORDER,
  fontFamily: 'IBM Plex Mono, monospace',
  fontSize: 13,
  background: '#fff',
  boxSizing: 'border-box',
}

export default function ModelWizard() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isEditMode = !!id

  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const [year, setYear] = useState(currentYear)
  const [season, setSeason] = useState(null)
  const [refClient, setRefClient] = useState('')
  const [nomPrenda, setNomPrenda] = useState('')
  const [descripcio, setDescripcio] = useState('')
  const [previewRef, setPreviewRef] = useState('—')

  const [editingStep1, setEditingStep1] = useState(false)

  const [subStep, setSubStep] = useState('A')
  const [target, setTarget] = useState(null)
  const [garmentType, setGarmentType] = useState(null)
  const [construction, setConstruction] = useState(null)

  // Sub-pas D — Sistema de talles natiu (Fix 1)
  const [sizingProfiles, setSizingProfiles] = useState([])
  const [selProfile, setSelProfile] = useState(null)
  const [sizeDefinitions, setSizeDefinitions] = useState([])
  const [selectedSizes, setSelectedSizes] = useState([])
  const [baseSize, setBaseSize] = useState(null)

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // sizingResult ara és derivat (Fix 1) — calculat a partir de selProfile+selectedSizes+baseSize.
  const sizingResult = (selProfile && selectedSizes.length > 0 && baseSize) ? {
    size_system_id: selProfile.size_system?.id,
    size_run_model: selectedSizes.join('·'),
    base_size_label: baseSize,
    grading_rule_set_id: selProfile.grading_rule_set?.id,
    size_system_nom: selProfile.size_system?.nom,
  } : null

  const resetSizing = () => {
    setSelProfile(null)
    setSelectedSizes([])
    setBaseSize(null)
    setSizeDefinitions([])
  }

  useEffect(() => {
    if (!year || !season || isEditMode) return
    fetch(`${API}/api/v1/models/next-ref/?year=${year}&season=${season}`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => setPreviewRef(d.codi_intern || '—'))
      .catch(() => setPreviewRef('—'))
  }, [year, season])

  useEffect(() => {
    if (!isEditMode) return
    fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => {
        setYear(d.any)
        setSeason(d.temporada)
        setPreviewRef(d.codi_intern)
        setRefClient(d.codi_client && d.codi_client !== d.codi_intern ? d.codi_client : '')
        setNomPrenda(d.nom_prenda || '')
        setDescripcio(d.descripcio || '')
        setTarget(d.target || null)
        setConstruction(d.construction || null)
        if (d.garment_type) setGarmentType({ id: d.garment_type })
      })
      .catch(() => setError('Error carregant el model'))
  }, [id])

  // Fix 1 — carregar sizing profiles quan target+construction+subStep='D'
  useEffect(() => {
    if (!target || !construction || subStep !== 'D') return
    fetch(`${API}/api/v1/sizing-profiles/?target=${target}&construction=${construction}&page_size=50`,
      { headers: authHeaders })
      .then(r => r.json())
      .then(d => setSizingProfiles(d.results || d || []))
      .catch(() => setSizingProfiles([]))
  }, [target, construction, subStep])

  // Fix 1 — carregar talles quan es selecciona un profile
  useEffect(() => {
    if (!selProfile) return
    const ssId = selProfile.size_system?.id
    if (!ssId) { setSizeDefinitions([]); return }
    fetch(`${API}/api/v1/size-definitions/?size_system=${ssId}&page_size=50`,
      { headers: authHeaders })
      .then(r => r.json())
      .then(d => {
        const defs = d.results || d || []
        setSizeDefinitions(defs)
        const labels = defs.map(s => s.etiqueta || s.size_label || s.label).filter(Boolean)
        setSelectedSizes(labels)
        setBaseSize(labels[Math.floor(labels.length / 2)] || labels[0] || null)
      })
      .catch(() => setSizeDefinitions([]))
  }, [selProfile])

  const handleCreateModel = async () => {
    if (!season) { setError('Selecciona una temporada'); return }
    setSaving(true); setError('')
    try {
      const r = await fetch(`${API}/api/v1/models/create-wizard/`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ year, season, ref_client: refClient, nom_prenda: nomPrenda, descripcio }),
      })
      const d = await r.json()
      if (!r.ok) { setError(JSON.stringify(d)); return }
      navigate(`/models/${d.id}/editar`)
    } catch {
      setError('Error de connexió')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveStep1 = async () => {
    setSaving(true); setError('')
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({ codi_client: refClient, nom_prenda: nomPrenda, descripcio }),
      })
      if (!r.ok) { const d = await r.json(); setError(JSON.stringify(d)); return }
      setEditingStep1(false)
    } catch {
      setError('Error de connexió')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveStep2 = async () => {
    if (!sizingResult) { setError('Configura el sistema de talles'); return }
    setSaving(true); setError('')
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/update-step2/`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify({
          target,
          garment_type_id: garmentType?.id,
          construction,
          size_system_id: sizingResult.size_system_id,
          size_run: sizingResult.size_run_model,
          base_size: sizingResult.base_size_label,
          grading_rule_set_id: sizingResult.grading_rule_set_id,
        }),
      })
      const d = await r.json()
      if (!r.ok) { setError(JSON.stringify(d)); return }
      navigate(`/models/${id}/mesures`)
    } catch {
      setError('Error de connexió')
    } finally {
      setSaving(false)
    }
  }

  // Fix 3 — banner si el model just s'acaba de crear (sense target)
  const isNewlyCreated = isEditMode && !target

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1rem' }}>
      <h1 style={{ fontFamily: 'IBM Plex Mono, monospace', fontSize: 22, marginBottom: '1.5rem', fontWeight: 500 }}>
        {isEditMode ? 'Editar model' : 'Nou model'}
      </h1>

      {isNewlyCreated && (
        <div style={{
          background: '#EBF8EC', border: '1px solid #A9DFBF', borderRadius: 8,
          padding: '8px 14px', marginBottom: 16, fontSize: 13, color: '#1E8449',
          fontFamily: 'IBM Plex Mono, monospace',
        }}>
          ✓ Model creat. Ara completa la descripció de la peça.
        </div>
      )}

      {error && (
        <div style={{
          background: '#fee', border: '1px solid #fcc', borderRadius: 8,
          padding: '0.75rem 1rem', marginBottom: '1rem', fontSize: 13, color: '#c00',
          fontFamily: 'IBM Plex Mono, monospace',
        }}>{error}</div>
      )}

      {!isEditMode && (
        <Step1Form
          year={year} setYear={setYear}
          season={season} setSeason={setSeason}
          refClient={refClient} setRefClient={setRefClient}
          nomPrenda={nomPrenda} setNomPrenda={setNomPrenda}
          descripcio={descripcio} setDescripcio={setDescripcio}
          previewRef={previewRef}
          saving={saving}
          onCreate={handleCreateModel}
        />
      )}

      {isEditMode && !editingStep1 && (
        <Step1Summary
          year={year} season={season} previewRef={previewRef}
          refClient={refClient} nomPrenda={nomPrenda}
          onEdit={() => setEditingStep1(true)}
        />
      )}

      {isEditMode && editingStep1 && (
        <Step1EditForm
          year={year} season={season} previewRef={previewRef}
          refClient={refClient} setRefClient={setRefClient}
          nomPrenda={nomPrenda} setNomPrenda={setNomPrenda}
          descripcio={descripcio} setDescripcio={setDescripcio}
          saving={saving}
          onSave={handleSaveStep1}
          onCancel={() => { setEditingStep1(false); setError('') }}
        />
      )}

      {isEditMode && (
        <Step2
          subStep={subStep} setSubStep={setSubStep}
          target={target} setTarget={setTarget}
          garmentType={garmentType} setGarmentType={setGarmentType}
          construction={construction} setConstruction={setConstruction}
          sizingResult={sizingResult}
          sizingProfiles={sizingProfiles}
          selProfile={selProfile} setSelProfile={setSelProfile}
          sizeDefinitions={sizeDefinitions}
          selectedSizes={selectedSizes} setSelectedSizes={setSelectedSizes}
          baseSize={baseSize} setBaseSize={setBaseSize}
          resetSizing={resetSizing}
          saving={saving}
          onSave={handleSaveStep2}
        />
      )}
    </div>
  )
}

// Fix 2 — Layout horitzontal (ANY · TEMPORADA · REFERÈNCIA INTERNA en una sola fila)
function Step1Form({
  year, setYear, season, setSeason,
  refClient, setRefClient, nomPrenda, setNomPrenda, descripcio, setDescripcio,
  previewRef, saving, onCreate,
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>

        {/* ANY */}
        <div style={{ flex: '0 0 auto' }}>
          <div style={{ ...labelStyle, marginBottom: 6, letterSpacing: '0.05em' }}>ANY</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {YEARS.map(y => (
              <button key={y} type="button" onClick={() => setYear(y)} style={chipStyle(year === y)}>
                {y}
              </button>
            ))}
          </div>
        </div>

        {/* TEMPORADA */}
        <div style={{ flex: '0 0 auto' }}>
          <div style={{ ...labelStyle, marginBottom: 6, letterSpacing: '0.05em' }}>TEMPORADA</div>
          <div style={{ display: 'flex', gap: 6 }}>
            {SEASONS.map(s => (
              <button key={s.codi} type="button" onClick={() => setSeason(s.codi)} style={chipStyle(season === s.codi)}>
                <div style={{ fontWeight: 500 }}>{s.codi}</div>
                <div style={{ fontSize: 10, opacity: 0.8 }}>{s.nom}</div>
              </button>
            ))}
          </div>
        </div>

        {/* REFERÈNCIA INTERNA */}
        <div style={{ flex: '1 1 200px' }}>
          <div style={{ ...labelStyle, marginBottom: 6, letterSpacing: '0.05em' }}>REFERÈNCIA INTERNA</div>
          <div style={{
            background: '#fdf6ee', border: '1px solid #e8d5b0', borderRadius: 8,
            padding: '8px 14px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 15,
            color: previewRef === '—' ? 'var(--color-text-secondary, #868685)' : 'var(--gold)',
            fontWeight: 500, minHeight: 36, display: 'flex', alignItems: 'center',
          }}>
            {previewRef}
          </div>
          <div style={{ ...labelStyle, marginTop: 4, textTransform: 'none' }}>
            Auto-generada · no editable
          </div>
        </div>

      </div>

      <div>
        <label style={labelStyle}>Referència client (opcional)</label>
        <input type="text" value={refClient} onChange={e => setRefClient(e.target.value)}
          style={{ ...inputStyle, marginTop: 4 }} placeholder="ex: AB-1234" />
      </div>

      <div>
        <label style={labelStyle}>Nom de la peça (opcional)</label>
        <input type="text" value={nomPrenda} onChange={e => setNomPrenda(e.target.value)}
          style={{ ...inputStyle, marginTop: 4 }} placeholder="ex: Brusa màniga llarga" />
      </div>

      <div>
        <label style={labelStyle}>Descripció (opcional)</label>
        <textarea value={descripcio} onChange={e => setDescripcio(e.target.value)}
          style={{ ...inputStyle, marginTop: 4, minHeight: 80, resize: 'vertical' }} />
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button type="button" onClick={onCreate} disabled={saving} style={primaryBtn(saving)}>
          {saving ? 'Creant...' : 'Crear model →'}
        </button>
      </div>
    </div>
  )
}

function Step1Summary({ year, season, previewRef, refClient, nomPrenda, onEdit }) {
  const items = [
    ['ANY', year],
    ['TEMPORADA', season],
    ['REF INTERNA', previewRef],
  ]
  if (refClient) items.push(['REF CLIENT', refClient])
  if (nomPrenda) items.push(['NOM PEÇA', nomPrenda])

  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      gap: 16, flexWrap: 'wrap',
      padding: '12px 16px', borderRadius: 8, border: BORDER,
      background: 'var(--bg-muted, #f5f0ea)',
    }}>
      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
        {items.map(([k, v]) => (
          <div key={k}>
            <div style={{ ...labelStyle, fontSize: 9 }}>{k}</div>
            <div style={{ fontSize: 13, fontWeight: 600, fontFamily: 'IBM Plex Mono, monospace' }}>{v}</div>
          </div>
        ))}
      </div>
      <button type="button" onClick={onEdit} style={secondaryBtn}>Editar</button>
    </div>
  )
}

function Step1EditForm({
  year, season, previewRef,
  refClient, setRefClient, nomPrenda, setNomPrenda, descripcio, setDescripcio,
  saving, onSave, onCancel,
}) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 14,
      padding: 16, borderRadius: 8, border: BORDER, background: '#fff',
    }}>
      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', paddingBottom: 12, borderBottom: BORDER }}>
        {[['ANY', year], ['TEMPORADA', season], ['REF INTERNA', previewRef]].map(([k, v]) => (
          <div key={k}>
            <div style={{ ...labelStyle, fontSize: 9 }}>{k}</div>
            <div style={{ fontSize: 13, fontWeight: 600, fontFamily: 'IBM Plex Mono, monospace' }}>{v}</div>
          </div>
        ))}
      </div>

      <div>
        <label style={labelStyle}>Referència client</label>
        <input type="text" value={refClient} onChange={e => setRefClient(e.target.value)}
          style={{ ...inputStyle, marginTop: 4 }} placeholder="ex: AB-1234" />
      </div>

      <div>
        <label style={labelStyle}>Nom de la peça</label>
        <input type="text" value={nomPrenda} onChange={e => setNomPrenda(e.target.value)}
          style={{ ...inputStyle, marginTop: 4 }} />
      </div>

      <div>
        <label style={labelStyle}>Descripció</label>
        <textarea value={descripcio} onChange={e => setDescripcio(e.target.value)}
          style={{ ...inputStyle, marginTop: 4, minHeight: 70, resize: 'vertical' }} />
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
        <button type="button" onClick={onCancel} disabled={saving} style={secondaryBtn}>Cancel·lar</button>
        <button type="button" onClick={onSave} disabled={saving} style={primaryBtn(saving)}>
          {saving ? 'Guardant...' : 'Guardar'}
        </button>
      </div>
    </div>
  )
}

function Step2({
  subStep, setSubStep,
  target, setTarget, garmentType, setGarmentType,
  construction, setConstruction,
  sizingResult,
  sizingProfiles, selProfile, setSelProfile,
  sizeDefinitions, selectedSizes, setSelectedSizes,
  baseSize, setBaseSize,
  resetSizing,
  saving, onSave,
}) {
  const targetLabel = TARGETS.find(t => t.codi === target)?.nom_en
  const constructionLabel = CONSTRUCTIONS.find(c => c.codi === construction)?.nom
  const garmentLabel = garmentType?.nom_en || garmentType?.nom_ca || (garmentType?.id ? `Garment #${garmentType.id}` : null)
  const sizingLabel = sizingResult
    ? `${sizingResult.size_system_nom || 'Sistema'} · ${sizingResult.size_run_model} · ★${sizingResult.base_size_label}`
    : null

  const breadcrumbs = [
    { key: 'A', label: targetLabel },
    { key: 'B', label: garmentLabel },
    { key: 'C', label: constructionLabel },
    { key: 'D', label: sizingLabel },
  ].filter(b => b.label)

  return (
    <div style={{
      marginTop: 18, padding: 20, borderRadius: 8,
      border: BORDER, background: '#fff',
    }}>
      {breadcrumbs.length > 0 && (
        <div style={{
          display: 'flex', flexWrap: 'wrap', gap: 6,
          paddingBottom: 14, marginBottom: 18, borderBottom: BORDER,
        }}>
          {breadcrumbs.map(b => (
            <button key={b.key} type="button" onClick={() => setSubStep(b.key)}
              style={{
                ...secondaryBtn, padding: '4px 10px', fontSize: 11,
                background: 'var(--gold-pale, #fdf6ee)',
              }}>
              {b.label}
            </button>
          ))}
        </div>
      )}

      {subStep === 'A' && (
        <Section title="Target — Per a qui és la peça?">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {TARGETS.map(t => (
              <button key={t.codi} type="button"
                onClick={() => {
                  if (target !== t.codi) resetSizing()
                  setTarget(t.codi)
                  setSubStep('B')
                }}
                style={chipStyle(target === t.codi)}>
                {t.nom_en}
              </button>
            ))}
          </div>
        </Section>
      )}

      {subStep === 'B' && (
        <Section title="Tipus de peça">
          <div style={{ height: 480, border: BORDER, borderRadius: 6, overflow: 'hidden' }}>
            <GarmentTypeSelector
              selectedId={garmentType?.id}
              onSelect={(gt) => { setGarmentType(gt); setSubStep('C') }}
            />
          </div>
        </Section>
      )}

      {subStep === 'C' && (
        <Section title="Construcció — Com és el teixit?">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {CONSTRUCTIONS.map(c => (
              <button key={c.codi} type="button"
                onClick={() => {
                  if (construction !== c.codi) resetSizing()
                  setConstruction(c.codi)
                  setSubStep('D')
                }}
                style={{ ...chipStyle(construction === c.codi), display: 'flex', flexDirection: 'column', gap: 2 }}>
                <span>{c.nom}</span>
                <span style={{ fontSize: 9, opacity: 0.85 }}>{c.desc}</span>
              </button>
            ))}
          </div>
        </Section>
      )}

      {subStep === 'D' && (
        <Section title="Sistema de talles">
          {/* D1 — selecció de Size Profile */}
          <div>
            <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)', marginBottom: 12, fontFamily: 'IBM Plex Mono, monospace' }}>
              Sistema de talles disponible per {target} · {construction}
            </p>
            {sizingProfiles.length === 0 && (
              <p style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)', fontFamily: 'IBM Plex Mono, monospace' }}>
                Cap sistema disponible per aquesta combinació.
              </p>
            )}
            {sizingProfiles.map(p => {
              const active = selProfile?.id === p.id
              const heading = p.size_system?.nom || `Profile #${p.id}`
              const sub = [p.target?.nom_en || p.target?.codi, p.construction?.nom_en || p.construction?.codi, p.fit_type_nom].filter(Boolean).join(' · ')
              return (
                <div key={p.id}
                  onClick={() => setSelProfile(p)}
                  style={{
                    padding: '10px 14px', marginBottom: 8, borderRadius: 8, cursor: 'pointer',
                    border: active ? '1.5px solid var(--gold)' : BORDER,
                    background: active ? '#fdf6ee' : 'transparent',
                    fontFamily: 'IBM Plex Mono, monospace',
                  }}>
                  <div style={{ fontWeight: 500, fontSize: 14 }}>{heading}</div>
                  <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)' }}>{sub}</div>
                </div>
              )
            })}
          </div>

          {/* D2 — Run de talles */}
          {selProfile && (
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)', marginBottom: 8, fontFamily: 'IBM Plex Mono, monospace' }}>
                Selecciona les talles del run:
              </p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {sizeDefinitions.map(s => {
                  const label = s.etiqueta || s.size_label || s.label
                  const active = selectedSizes.includes(label)
                  return (
                    <button key={label} type="button"
                      onClick={() => setSelectedSizes(prev =>
                        active ? prev.filter(x => x !== label) : [...prev, label]
                      )}
                      style={chipStyle(active)}>
                      {label}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* D3 — Talla base */}
          {selectedSizes.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)', marginBottom: 8, fontFamily: 'IBM Plex Mono, monospace' }}>
                Talla base:
              </p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {selectedSizes.map(s => (
                  <button key={s} type="button"
                    onClick={() => setBaseSize(s)}
                    style={chipStyle(baseSize === s)}>
                    {s} {baseSize === s && '★'}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Resum quan tot confirmat */}
          {sizingResult && (
            <div style={{
              marginTop: 16,
              background: '#f0f9f0', border: '1px solid #a9dfb1', borderRadius: 8,
              padding: '10px 14px', fontFamily: 'IBM Plex Mono, monospace', fontSize: 13,
            }}>
              ✓ {selProfile?.size_system?.nom} · {selectedSizes.join('·')} · Base: {baseSize}
              <button type="button" onClick={resetSizing}
                style={{
                  marginLeft: 12, fontSize: 12, background: 'transparent', border: 'none',
                  color: 'var(--gold)', cursor: 'pointer', fontFamily: 'IBM Plex Mono, monospace',
                }}>
                Modificar
              </button>
            </div>
          )}
        </Section>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 22 }}>
        <button type="button" onClick={onSave}
          disabled={!sizingResult || saving}
          style={primaryBtn(!sizingResult || saving)}>
          {saving ? 'Guardant...' : 'Guardar i continuar →'}
        </button>
      </div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <div style={{ ...labelStyle, marginBottom: 12 }}>{title}</div>
      {children}
    </div>
  )
}
