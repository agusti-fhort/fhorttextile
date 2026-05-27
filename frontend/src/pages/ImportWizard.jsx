import { useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import useAuthStore from "../store/auth"
import GarmentTypeSelector from "../components/GarmentTypeSelector/GarmentTypeSelector"
import { SizingProfileWizard } from "../components/SizingProfileWizard"
import { DesignFreezeReport } from "../components/DesignFreezeReport"
import { XatExtraccio } from "../components/XatExtraccio"

const API = import.meta.env.VITE_API_URL || ""

const STEPS = [
  { id: 1, label: "Target" },
  { id: 2, label: "Tipus peça" },
  { id: 3, label: "Talles" },
  { id: 4, label: "Anàlisi IA" },
]

// Idèntic a TARGETS de GradingRuleSets.jsx
const TARGETS = [
  { codi: 'WOMAN',         nom_en: 'Woman',         nom_ca: 'Dona' },
  { codi: 'MAN',           nom_en: 'Man',           nom_ca: 'Home' },
  { codi: 'UNISEX_ADULT',  nom_en: 'Unisex Adult',  nom_ca: 'Unisex adult' },
  { codi: 'BABY_GIRL',     nom_en: 'Baby Girl',     nom_ca: 'Nadó nena' },
  { codi: 'BABY_BOY',      nom_en: 'Baby Boy',      nom_ca: 'Nadó nen' },
  { codi: 'BABY_UNISEX',   nom_en: 'Baby Unisex',   nom_ca: 'Nadó unisex' },
  { codi: 'TODDLER_GIRL',  nom_en: 'Toddler Girl',  nom_ca: 'Nena toddler' },
  { codi: 'TODDLER_BOY',   nom_en: 'Toddler Boy',   nom_ca: 'Nen toddler' },
  { codi: 'GIRL',          nom_en: 'Girl',          nom_ca: 'Nena' },
  { codi: 'BOY',           nom_en: 'Boy',           nom_ca: 'Nen' },
  { codi: 'TEEN_GIRL',     nom_en: 'Teen Girl',     nom_ca: 'Adolescent nena' },
  { codi: 'TEEN_BOY',      nom_en: 'Teen Boy',      nom_ca: 'Adolescent nen' },
  { codi: 'MATERNITY',     nom_en: 'Maternity',     nom_ca: 'Maternitat' },
]

function StepIndicator({ current }) {
  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: 28, gap: 0 }}>
      {STEPS.map((s, i) => {
        const done = s.id < current
        const active = s.id === current
        return (
          <div key={s.id} style={{ display: "flex", alignItems: "center" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
              <div style={{
                width: 28, height: 28, borderRadius: "50%",
                background: active ? "#c27a2a" : done ? "#f5e6d0" : "#f0f0f0",
                border: `1px solid ${active ? "#c27a2a" : done ? "#e0c8a0" : "#e0d5c5"}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 11, fontFamily: "IBM Plex Mono, monospace",
                color: active ? "#fff" : done ? "#1d1d1b" : "#868685",
                fontWeight: active ? 600 : 400,
              }}>
                {done ? "✓" : s.id}
              </div>
              <div style={{
                fontSize: 10, whiteSpace: "nowrap",
                fontFamily: "IBM Plex Mono, monospace",
                color: active ? "#c27a2a" : done ? "#1d1d1b" : "#868685",
              }}>
                {s.label}
              </div>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{
                width: 40, height: 1, margin: "0 4px", marginBottom: 18,
                background: done ? "#c27a2a" : "#e0d5c5",
              }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

const navBtnStyle = {
  padding: "7px 16px", borderRadius: 4, fontSize: 11, cursor: "pointer",
  background: "#fff", color: "#868685", border: "1px solid #e0d5c5",
  fontFamily: "IBM Plex Mono, monospace",
}

export default function ImportWizard() {
  const navigate = useNavigate()
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')

  const [step, setStep] = useState(1)

  // Seleccions del wizard
  const [selectedTarget, setSelectedTarget] = useState(null)            // codi string
  const [selectedGarmentType, setSelectedGarmentType] = useState(null)  // gt object
  const [sizingResult, setSizingResult] = useState(null)                // payload SizingProfileWizard

  // Pas 4 — upload + IA
  const [file, setFile] = useState(null)
  const [fileBase64, setFileBase64] = useState(null)
  const [fileType, setFileType] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState("")
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const fileInput = useRef()

  const ACCEPTED = ".pdf,.png,.jpg,.jpeg,.webp"

  // Context complet del wizard — s'envia al backend a analyze i a create.
  const wizardContext = {
    target_codi:         selectedTarget,
    garment_type_id:     selectedGarmentType?.id,
    garment_type_codi:   selectedGarmentType?.codi_client,
    garment_type_nom:    selectedGarmentType?.nom_en,
    garment_type_grup:   selectedGarmentType?.grup,
    sizing_profile_id:   sizingResult?.sizing_profile_id,
    size_system_id:      sizingResult?.size_system_id,
    size_system_nom:     sizingResult?.size_system_nom,
    grading_rule_set_id: sizingResult?.grading_rule_set_id,
    grading_rule_set_nom:sizingResult?.grading_rule_set_nom,
    base_size_label:     sizingResult?.base_size_label,
    // size_run: el backend (create-from-extraction) llegeix aquesta clau.
    // size_run_model: NouModel.jsx la consumeix amb el sufix _model.
    size_run:            sizingResult?.size_run_model || '',
    size_run_model:      sizingResult?.size_run_model || '',
    construction_codi:   sizingResult?.construction_codi,
  }

  // ── Handlers ──────────────────────────────────────────────────────────────

  const handleFile = (f) => {
    if (!f) return
    const ext = f.name.split(".").pop().toLowerCase()
    if (!["pdf", "png", "jpg", "jpeg", "webp"].includes(ext)) {
      setError(`Format no acceptat: .${ext}`)
      return
    }
    setFile(f)
    setError(null)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  const handleAnalyze = async () => {
    if (!file) return
    if (!token) {
      setError("Sessió no autenticada — torna a iniciar sessió.")
      navigate("/login")
      return
    }
    setLoading(true)
    setError(null)
    setLoadingMsg("Analitzant document amb IA...")

    // Llegir fitxer com a base64 en paral·lel — el xat el reutilitza al panell dret.
    const reader = new FileReader()
    reader.onload = (e) => {
      const base64 = String(e.target.result).split(',')[1]
      setFileBase64(base64)
      setFileType(file.type)
    }
    reader.readAsDataURL(file)

    const fd = new FormData()
    fd.append("file", file)
    Object.entries(wizardContext).forEach(([k, v]) => {
      if (v != null && v !== '') fd.append(k, String(v))
    })

    try {
      const r = await fetch(`${API}/api/v1/models/extract-from-file/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`)
      setResult(data)
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
    setLoadingMsg("")
  }

  // Pas 4 → NouModel amb pre-fill via location.state.
  // NouModel ha de llegir state.prefill (i opcionalment state.extracted/wizard_context)
  // per omplir el formulari de creació.
  const handleProceedToNouModel = () => {
    const ext = result?.extracted || {}
    const yearVal = ext.year?.value ?? ext.year
    navigate('/models/nou', {
      state: {
        fromImport: true,
        extracted: ext,
        wizard_context: wizardContext,
        prefill: {
          nom_prenda:       ext.style_name?.value || ext.style_name || '',
          codi_client:      ext.style_reference?.value || ext.style_reference || '',
          temporada:        String(ext.season?.value || ext.season || 'SS').slice(0, 2).toUpperCase(),
          any:              Number(yearVal) || new Date().getFullYear(),
          garment_type:     selectedGarmentType?.id || '',
          fit_type:         ext.fit_type || 'Regular',
          size_system:      sizingResult?.size_system_id || '',
          base_size_label:  sizingResult?.base_size_label || '',
          size_run_model:   sizingResult?.size_run_model || '',
          grading_rule_set: sizingResult?.grading_rule_set_id || '',
        },
      },
    })
  }

  // ── Render ────────────────────────────────────────────────────────────────

  // Pas 4 review (result present) ocupa amplada gran per al split report+xat;
  // la resta usen amplada mitjana.
  const wrapperStyle =
    (step === 4 && result)
      ? { padding: "24px", maxWidth: 1200, margin: "0 auto" }
      : { padding: "24px", maxWidth: 760, margin: "0 auto" }

  return (
    <div style={wrapperStyle}>
      <button onClick={() => navigate(-1)} style={{
        background: "none", border: "none", color: 'var(--text-main)', cursor: "pointer",
        fontSize: 11, fontFamily: "IBM Plex Mono, monospace", marginBottom: 20,
      }}>
        ← Tornar
      </button>

      <h1 style={{ fontSize: 18, fontFamily: "IBM Plex Mono, monospace", color: "#c27a2a", marginBottom: 6 }}>
        Nou model des de fitxer
      </h1>
      <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 24, fontFamily: "IBM Plex Mono, monospace" }}>
        Quatre passos: target, tipus de peça, sistema de talles i anàlisi IA. La confirmació final es fa al formulari de Nou model.
      </p>

      <StepIndicator current={step} />

      {error && (
        <div style={{
          padding: "8px 12px", marginBottom: 16, borderRadius: 4,
          background: 'var(--bg-muted)', border: "1px solid #4a2020",
          color: "#cc6666", fontSize: 11, fontFamily: "IBM Plex Mono, monospace",
        }}>
          ✗ {error}
        </div>
      )}

      {/* PAS 1 — Target ─────────────────────────────────────────────── */}
      {step === 1 && (
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12, fontFamily: "IBM Plex Mono, monospace" }}>
            Per a qui és la peça?
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {TARGETS.map(t => {
              const sel = selectedTarget === t.codi
              return (
                <button key={t.codi}
                  onClick={() => { setSelectedTarget(t.codi); setStep(2) }}
                  style={{
                    padding: "10px 14px", borderRadius: 6, cursor: "pointer",
                    background: sel ? "#f5e6d0" : "#fff",
                    color: sel ? "#c27a2a" : "#1d1d1b",
                    border: `1px solid ${sel ? "#c27a2a" : "#e0d5c5"}`,
                    fontFamily: "IBM Plex Mono, monospace", fontSize: 11,
                    display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
                    minWidth: 90,
                  }}>
                  <span style={{ fontWeight: sel ? 600 : 400 }}>{t.nom_en}</span>
                  <span style={{ fontSize: 9, color: sel ? "#c27a2a" : "#868685" }}>
                    {t.nom_ca}
                  </span>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* PAS 2 — Tipus peça (reutilitza GarmentTypeSelector) ─────────── */}
      {step === 2 && (
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12, fontFamily: "IBM Plex Mono, monospace" }}>
            Quin tipus de peça? Selecciona un grup i tria la peça.
          </div>
          <div style={{ border: "1px solid var(--border)", borderRadius: 8, height: 540, overflow: "hidden" }}>
            <GarmentTypeSelector
              selectedId={selectedGarmentType?.id || null}
              onSelect={(gt) => { setSelectedGarmentType(gt); setStep(3) }}
              lang="ca"
            />
          </div>
          <div style={{ display: "flex", justifyContent: "flex-start", marginTop: 16 }}>
            <button onClick={() => setStep(1)} style={navBtnStyle}>← Enrere</button>
          </div>
        </div>
      )}

      {/* PAS 3 — Talles (reutilitza SizingProfileWizard) ─────────────── */}
      {step === 3 && (
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12, fontFamily: "IBM Plex Mono, monospace" }}>
            Sistema de talles, run i talla base.
          </div>
          <SizingProfileWizard
            initialValues={{ target: selectedTarget }}
            onComplete={(payload) => { setSizingResult(payload); setStep(4) }}
            onCancel={() => setStep(2)}
          />
        </div>
      )}

      {/* PAS 4 — Upload + Anàlisi IA ──────────────────────────────────── */}
      {step === 4 && !result && (
        <div>
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInput.current.click()}
            style={{
              border: `1.5px dashed ${dragging ? "#c27a2a" : file ? "#2a4a2a" : 'var(--border)'}`,
              borderRadius: 8, padding: "40px 24px", textAlign: "center",
              cursor: "pointer", transition: "all .15s",
              background: dragging ? "rgba(194,122,42,0.05)" : "transparent",
              marginBottom: 16,
            }}
          >
            <input
              ref={fileInput} type="file" accept={ACCEPTED} style={{ display: "none" }}
              onChange={(e) => handleFile(e.target.files[0])}
            />
            {file ? (
              <div>
                <div style={{ fontSize: 24, marginBottom: 8 }}>📄</div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', fontFamily: "IBM Plex Mono, monospace" }}>{file.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                  {(file.size / 1024).toFixed(0)} KB — clica per canviar
                </div>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: 28, marginBottom: 8 }}>⬆</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: "IBM Plex Mono, monospace" }}>
                  Arrossega o clica per seleccionar
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-main)', marginTop: 6 }}>
                  PDF · PNG · JPG · WEBP · màx. 20MB
                </div>
              </div>
            )}
          </div>

          {loading && (
            <div style={{ textAlign: "center", padding: "16px 0" }}>
              <style>{`@keyframes iw-spin { to { transform: rotate(360deg); } }`}</style>
              <div style={{
                width: 36, height: 36, borderRadius: '50%',
                border: '3px solid rgba(200,150,62,0.18)',
                borderTopColor: 'var(--gold)',
                animation: 'iw-spin 0.8s linear infinite',
                margin: '0 auto 12px',
              }} />
              <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: "IBM Plex Mono, monospace" }}>
                {loadingMsg}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-main)', marginTop: 8 }}>
                Pot trigar 15-45 segons depenent del document
              </div>
            </div>
          )}

        </div>
      )}

      {/* PAS 4 (review) — DesignFreeze + Xat IA ───────────────────────── */}
      {step === 4 && result && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) minmax(420px, 480px)',
          gap: 20,
          height: 'calc(100vh - 280px)',
          minHeight: 500,
        }}>
          <div style={{ overflowY: 'auto', minWidth: 0 }}>
            <DesignFreezeReport
              result={result}
              onConfirm={handleProceedToNouModel}
              onReject={() => { setResult(null); setFile(null); setFileBase64(null) }}
            />
          </div>
          <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden', minWidth: 420 }}>
            <XatExtraccio
              extraccio={result?.extracted}
              fileBase64={fileBase64}
              fileType={fileType}
              onUpdate={(updates) => {
                setResult(prev => ({
                  ...prev,
                  extracted: { ...prev.extracted, ...updates },
                }))
              }}
            />
          </div>
        </div>
      )}

      {/* PAS 4 footer unificat — sempre visible, "Continuar" disabled
          fins que result existeix i loading sigui false ───────────────── */}
      {step === 4 && (() => {
        const continuarDisabled = !result || loading
        return (
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 16 }}>
            <button onClick={() => setStep(3)} style={navBtnStyle}>← Enrere</button>
            <div style={{ display: "flex", gap: 8 }}>
              {!result && (
                <button
                  onClick={handleAnalyze}
                  disabled={!file || loading}
                  style={{
                    padding: "10px 18px",
                    background: 'var(--gold)',
                    color: '#FFFFFF',
                    border: 'none',
                    borderRadius: 4, fontSize: 12,
                    fontFamily: "IBM Plex Mono, monospace",
                    fontWeight: 600,
                    cursor: file && !loading ? "pointer" : "not-allowed",
                    opacity: file && !loading ? 1 : 0.5,
                  }}
                >
                  ⚡ Analitzar amb IA
                </button>
              )}
              <button
                onClick={handleProceedToNouModel}
                disabled={continuarDisabled}
                style={{
                  padding: "10px 18px",
                  background: 'var(--gold)',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: 4, fontSize: 12,
                  fontFamily: "IBM Plex Mono, monospace",
                  fontWeight: 600,
                  cursor: continuarDisabled ? "not-allowed" : "pointer",
                  opacity: continuarDisabled ? 0.5 : 1,
                }}
              >
                Continuar → Crear model
              </button>
            </div>
          </div>
        )
      })()}

    </div>
  )
}
