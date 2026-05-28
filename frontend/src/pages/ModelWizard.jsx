import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import useAuthStore from '../store/auth'
import { SizingProfileWizard } from '../components/SizingProfileWizard'
import GarmentTypeSelector from '../components/GarmentTypeSelector/GarmentTypeSelector'

const API = import.meta.env.VITE_API_URL || ''

const SEASONS = [
  { codi: 'SS',  label: 'SS',  sub: 'Spring/Summer' },
  { codi: 'FW',  label: 'FW',  sub: 'Fall/Winter' },
  { codi: 'RE',  label: 'RE',  sub: 'Resort' },
  { codi: 'PRE', label: 'PRE', sub: 'Pre-collection' },
]

const anyActual = new Date().getFullYear()
const YEARS = [anyActual, anyActual + 1, anyActual + 2, anyActual + 3]

// Mateixa llista que SizingProfileWizard.
const TARGET_ORDER = [
  'WOMAN', 'MAN', 'UNISEX_ADULT',
  'BABY_GIRL', 'BABY_BOY', 'BABY_UNISEX',
  'TODDLER_GIRL', 'TODDLER_BOY',
  'GIRL', 'BOY', 'TEEN_GIRL', 'TEEN_BOY', 'MATERNITY',
]

const TARGET_LABELS = {
  WOMAN: 'Woman', MAN: 'Man', UNISEX_ADULT: 'Unisex Adult',
  BABY_GIRL: 'Baby Girl', BABY_BOY: 'Baby Boy', BABY_UNISEX: 'Baby Unisex',
  TODDLER_GIRL: 'Toddler Girl', TODDLER_BOY: 'Toddler Boy',
  GIRL: 'Girl', BOY: 'Boy', TEEN_GIRL: 'Teen Girl', TEEN_BOY: 'Teen Boy',
  MATERNITY: 'Maternity',
}

const CONSTRUCTIONS = [
  { codi: 'WOVEN',        label: 'Woven',        sub: 'Teixit pla' },
  { codi: 'KNIT',         label: 'Knit',         sub: 'Punt jersey' },
  { codi: 'STRETCH_KNIT', label: 'Stretch Knit', sub: 'Punt elàstic' },
  { codi: 'TECHNICAL',    label: 'Technical',    sub: 'Tècnic' },
]

const BORDER_INACTIVE = '0.5px solid var(--color-border-tertiary, var(--border))'

const chipStyle = (active) => ({
  padding: '10px 16px',
  borderRadius: 6,
  cursor: 'pointer',
  background: active ? 'var(--gold)' : '#fff',
  color: active ? '#fff' : 'var(--text-main)',
  border: active ? '0.5px solid var(--gold)' : BORDER_INACTIVE,
  fontFamily: 'IBM Plex Mono, monospace',
  fontSize: 12,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: 2,
  minWidth: 72,
  fontWeight: active ? 600 : 400,
})

const inputStyle = {
  width: '100%',
  padding: '8px 10px',
  borderRadius: 4,
  border: BORDER_INACTIVE,
  fontFamily: 'IBM Plex Mono, monospace',
  fontSize: 12,
  background: '#fff',
  color: 'var(--text-main)',
}

const labelStyle = {
  display: 'block',
  fontSize: 10,
  color: 'var(--text-muted)',
  marginBottom: 4,
  textTransform: 'uppercase',
  letterSpacing: '.04em',
}

const sectionLabel = {
  fontSize: 11, color: 'var(--text-muted)',
  textTransform: 'uppercase', letterSpacing: '.06em',
  marginBottom: 10,
}

const primaryBtn = (disabled = false) => ({
  padding: '10px 20px',
  borderRadius: 6,
  background: disabled ? 'var(--bg-muted)' : 'var(--gold)',
  color: disabled ? 'var(--text-muted)' : '#fff',
  border: `0.5px solid ${disabled ? 'var(--border)' : 'var(--gold)'}`,
  fontFamily: 'IBM Plex Mono, monospace',
  fontSize: 12,
  fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer',
})

export default function ModelWizard() {
  const navigate = useNavigate()
  const { id: modelIdParam } = useParams()
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const authHeaders = { Authorization: `Bearer ${token}` }

  const isEditMode = !!modelIdParam
  const [showStep1, setShowStep1] = useState(!isEditMode)

  // --- Pas 1 state ---
  const [year, setYear] = useState(null)
  const [season, setSeason] = useState(null)
  const [refClient, setRefClient] = useState('')
  const [nomPrenda, setNomPrenda] = useState('')
  const [descripcio, setDescripcio] = useState('')
  const [previewRef, setPreviewRef] = useState('—')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  // --- Resum Pas 1 (carregat en mode edit) ---
  const [summary, setSummary] = useState(null)

  // --- Pas 2 state ---
  const [subStep, setSubStep] = useState('A')
  const [target, setTarget] = useState(null)             // codi (string)
  const [garmentType, setGarmentType] = useState(null)   // { id, nom_en, ... }
  const [construction, setConstruction] = useState(null) // codi (string)
  const [sizingResult, setSizingResult] = useState(null) // de SizingProfileWizard
  const [savingStep2, setSavingStep2] = useState(false)

  // Preview ref intern (Pas 1)
  useEffect(() => {
    if (!year || !season) { setPreviewRef('—'); return }
    let aborted = false
    fetch(`${API}/api/v1/models/next-ref/?year=${year}&season=${season}`, { headers: authHeaders })
      .then(r => r.json())
      .then(d => { if (!aborted) setPreviewRef(d.codi_intern || '—') })
      .catch(() => { if (!aborted) setPreviewRef('—') })
    return () => { aborted = true }
  }, [year, season])

  // Carrega el model en mode edit (per al resum + prefill si l'usuari obre Pas 1)
  useEffect(() => {
    if (!isEditMode) return
    fetch(`${API}/api/v1/models/${modelIdParam}/`, { headers: authHeaders })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(d => {
        setSummary({
          any: d.any,
          temporada: d.temporada,
          codi_intern: d.codi_intern,
          codi_client: d.codi_client,
          nom_prenda: d.nom_prenda,
          descripcio: d.descripcio,
        })
        // Prefill per si l'usuari clica "editar"
        setYear(d.any)
        setSeason(d.temporada)
        setRefClient(d.codi_client || '')
        setNomPrenda(d.nom_prenda || '')
        setDescripcio(d.descripcio || '')
        setPreviewRef(d.codi_intern || '—')
      })
      .catch(() => setError('No s\'ha pogut carregar el model'))
  }, [isEditMode, modelIdParam])

  // --- Handlers ---
  const handleCreate = async () => {
    setSubmitting(true)
    setError('')
    try {
      const payload = {
        year, season,
        codi_client: refClient || null,
        nom_prenda: nomPrenda || null,
        descripcio: descripcio || null,
      }
      const r = await fetch(`${API}/api/v1/models/create-wizard/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || JSON.stringify(data))
      navigate(`/models/${data.id}/editar`)
    } catch (e) {
      setError(e.message)
      setSubmitting(false)
    }
  }

  const handlePatchStep1 = async () => {
    setSubmitting(true)
    setError('')
    try {
      const payload = {
        codi_client: refClient || null,
        nom_prenda: nomPrenda || null,
        descripcio: descripcio || null,
      }
      const r = await fetch(`${API}/api/v1/models/${modelIdParam}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || JSON.stringify(data))
      setSummary(s => ({ ...s, ...payload }))
      setShowStep1(false)
      setSubmitting(false)
    } catch (e) {
      setError(e.message)
      setSubmitting(false)
    }
  }

  const handleSaveStep2 = async () => {
    if (!sizingResult) return
    setSavingStep2(true)
    setError('')
    try {
      const payload = {
        target,
        garment_type_id: garmentType?.id,
        construction,
        size_system_id: sizingResult.size_system_id,
        size_run: sizingResult.size_run_model,
        base_size: sizingResult.base_size_label,
        grading_rule_set_id: sizingResult.grading_rule_set_id,
      }
      const r = await fetch(`${API}/api/v1/models/${modelIdParam}/update-step2/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(payload),
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || JSON.stringify(data))
      navigate(`/models/${modelIdParam}/mesures`)
    } catch (e) {
      setError(e.message)
      setSavingStep2(false)
    }
  }

  // --- RENDER ---
  if (isEditMode) {
    return (
      <div style={{ fontFamily: 'IBM Plex Mono, monospace', maxWidth: 820, padding: 24 }}>
        <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 20 }}>Editar model</h1>

        {/* Bloc superior: resum o Pas 1 expandit */}
        {showStep1
          ? renderStep1Form({
              year, setYear, season, setSeason, refClient, setRefClient,
              nomPrenda, setNomPrenda, descripcio, setDescripcio, previewRef,
              error, submitting,
              primaryLabel: 'Guardar canvis',
              onPrimary: handlePatchStep1,
              onCancel: () => { setShowStep1(false); setError('') },
            })
          : renderSummaryCard({ summary, onEdit: () => setShowStep1(true) })
        }

        {/* Bloc Pas 2 */}
        {!showStep1 && (
          <div style={{
            marginTop: 16, padding: 20, borderRadius: 8,
            border: BORDER_INACTIVE, background: '#fff',
          }}>
            <Step2Header
              target={target} garmentType={garmentType}
              construction={construction} sizingResult={sizingResult}
              onJump={setSubStep}
            />

            {subStep === 'A' && (
              <Section title="Target — Per a qui és la peça?">
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {TARGET_ORDER.map(codi => (
                    <button
                      key={codi}
                      onClick={() => { setTarget(codi); setSubStep('B') }}
                      style={chipStyle(target === codi)}
                    >
                      <span>{TARGET_LABELS[codi]}</span>
                    </button>
                  ))}
                </div>
              </Section>
            )}

            {subStep === 'B' && (
              <Section title="Tipus de prenda">
                <div style={{
                  height: 480, border: BORDER_INACTIVE, borderRadius: 6, overflow: 'hidden',
                }}>
                  <GarmentTypeSelector
                    selectedId={garmentType?.id}
                    onSelect={(t) => { setGarmentType(t); setSubStep('C') }}
                  />
                </div>
              </Section>
            )}

            {subStep === 'C' && (
              <Section title="Teixit — Com és la construcció?">
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {CONSTRUCTIONS.map(c => (
                    <button
                      key={c.codi}
                      onClick={() => { setConstruction(c.codi); setSubStep('D') }}
                      style={chipStyle(construction === c.codi)}
                    >
                      <span>{c.label}</span>
                      <span style={{ fontSize: 9, opacity: 0.85 }}>{c.sub}</span>
                    </button>
                  ))}
                </div>
              </Section>
            )}

            {subStep === 'D' && (
              <Section title="Sistema de talles">
                {!sizingResult ? (
                  <SizingProfileWizard
                    initialValues={{ target, construction }}
                    onComplete={(res) => setSizingResult(res)}
                    onCancel={() => setSubStep('C')}
                  />
                ) : (
                  <div style={{ padding: '8px 0', fontSize: 12, color: 'var(--text-muted)' }}>
                    ✓ Configuració de talles confirmada.
                    <button
                      onClick={() => setSizingResult(null)}
                      style={{
                        marginLeft: 12, padding: '4px 10px', borderRadius: 4,
                        background: '#fff', color: 'var(--gold)',
                        border: '0.5px solid var(--gold)', cursor: 'pointer',
                        fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
                      }}
                    >Modificar</button>
                  </div>
                )}
              </Section>
            )}

            {error && (
              <div style={{
                marginTop: 16, padding: '8px 12px', borderRadius: 4,
                background: 'var(--err-bg)', color: 'var(--err)', fontSize: 11,
              }}>{error}</div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 20 }}>
              <button
                onClick={handleSaveStep2}
                disabled={!sizingResult || savingStep2}
                style={primaryBtn(!sizingResult || savingStep2)}
              >
                {savingStep2 ? 'Guardant...' : 'Guardar i continuar →'}
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  // --- Mode create (Pas 1 únic) ---
  return (
    <div style={{ fontFamily: 'IBM Plex Mono, monospace', maxWidth: 680, padding: 24 }}>
      <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 24 }}>Nou model</h1>
      {renderStep1Form({
        year, setYear, season, setSeason, refClient, setRefClient,
        nomPrenda, setNomPrenda, descripcio, setDescripcio, previewRef,
        error, submitting,
        primaryLabel: 'Crear model →',
        onPrimary: handleCreate,
      })}
    </div>
  )
}

// --- Subcomponents ---

function renderSummaryCard({ summary, onEdit }) {
  if (!summary) {
    return (
      <div style={{
        padding: '12px 14px', borderRadius: 6, border: BORDER_INACTIVE,
        background: 'var(--bg-muted)', fontSize: 11, color: 'var(--text-muted)',
      }}>Carregant…</div>
    )
  }
  const rows = [
    ['Any', summary.any],
    ['Temporada', summary.temporada],
    ['Ref interna', summary.codi_intern],
    ['Ref client', summary.codi_client || '—'],
    ['Nom peça', summary.nom_prenda || '—'],
  ]
  return (
    <div style={{
      padding: '14px 16px', borderRadius: 8, border: BORDER_INACTIVE,
      background: 'var(--bg-muted)',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      gap: 16, flexWrap: 'wrap',
    }}>
      <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
        {rows.map(([k, v]) => (
          <div key={k}>
            <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.04em' }}>{k}</div>
            <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-main)' }}>{v}</div>
          </div>
        ))}
      </div>
      <button
        onClick={onEdit}
        style={{
          padding: '6px 12px', borderRadius: 4, cursor: 'pointer',
          background: '#fff', color: 'var(--gold)',
          border: '0.5px solid var(--gold)',
          fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
        }}
      >Editar</button>
    </div>
  )
}

function renderStep1Form({
  year, setYear, season, setSeason, refClient, setRefClient,
  nomPrenda, setNomPrenda, descripcio, setDescripcio, previewRef,
  error, submitting, primaryLabel, onPrimary, onCancel,
}) {
  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <label style={{ ...labelStyle, marginBottom: 0, fontSize: 13, color: 'var(--text-muted)', minWidth: 100 }}>Any</label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {YEARS.map(y => (
              <button key={y} onClick={() => setYear(y)} style={chipStyle(year === y)}>
                <span>{y}</span>
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <label style={{ ...labelStyle, marginBottom: 0, fontSize: 13, color: 'var(--text-muted)', minWidth: 100 }}>Temporada</label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {SEASONS.map(s => (
              <button key={s.codi} onClick={() => setSeason(s.codi)} style={chipStyle(season === s.codi)}>
                <span>{s.label}</span>
                <span style={{ fontSize: 9, opacity: 0.85 }}>{s.sub}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{
        marginBottom: 24, padding: '12px 14px', borderRadius: 6,
        background: 'var(--bg-muted)', border: BORDER_INACTIVE,
      }}>
        <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>Referència interna</div>
        <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--gold)' }}>{previewRef}</div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Referència client (opcional)</label>
        <input type="text" value={refClient} onChange={e => setRefClient(e.target.value)} style={inputStyle} placeholder="ex: AB-1234" />
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={labelStyle}>Nom de la peça (opcional)</label>
        <input type="text" value={nomPrenda} onChange={e => setNomPrenda(e.target.value)} style={inputStyle} placeholder="ex: Brusa màniga llarga" />
      </div>

      <div style={{ marginBottom: 24 }}>
        <label style={labelStyle}>Descripció (opcional)</label>
        <textarea value={descripcio} onChange={e => setDescripcio(e.target.value)} style={{ ...inputStyle, minHeight: 80, resize: 'vertical' }} />
      </div>

      {error && (
        <div style={{
          marginBottom: 16, padding: '8px 12px', borderRadius: 4,
          background: 'var(--err-bg)', color: 'var(--err)', fontSize: 11,
        }}>{error}</div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
        {onCancel && (
          <button
            onClick={onCancel}
            style={{
              padding: '10px 16px', borderRadius: 6, cursor: 'pointer',
              background: '#fff', color: 'var(--text-muted)',
              border: BORDER_INACTIVE,
              fontFamily: 'IBM Plex Mono, monospace', fontSize: 12,
            }}
          >Cancel·lar</button>
        )}
        <button onClick={onPrimary} disabled={submitting} style={primaryBtn(submitting)}>
          {submitting ? 'Guardant...' : primaryLabel}
        </button>
      </div>
    </>
  )
}

function Section({ title, children }) {
  return (
    <div>
      <div style={sectionLabel}>{title}</div>
      {children}
    </div>
  )
}

function Step2Header({ target, garmentType, construction, sizingResult, onJump }) {
  const parts = [
    target && { key: 'A', label: TARGET_LABELS[target] || target },
    garmentType && { key: 'B', label: garmentType.nom_en || garmentType.nom_ca || garmentType.codi_client },
    construction && { key: 'C', label: (CONSTRUCTIONS.find(c => c.codi === construction)?.label) || construction },
    sizingResult && {
      key: 'D',
      label: `${sizingResult.size_system_nom || 'Sistema'} ${sizingResult.size_run_model ? '· ' + sizingResult.size_run_model : ''}`,
    },
  ].filter(Boolean)

  if (parts.length === 0) return null

  return (
    <div style={{
      display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 18,
      paddingBottom: 14, borderBottom: BORDER_INACTIVE,
    }}>
      {parts.map(p => (
        <button
          key={p.key}
          onClick={() => onJump(p.key)}
          style={{
            padding: '4px 10px', borderRadius: 4, cursor: 'pointer',
            background: 'var(--gold-pale)', color: 'var(--gold)',
            border: '0.5px solid var(--gold)',
            fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
          }}
          title="Tornar a aquest pas"
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}
