
import { useState, useRef } from "react"
import { useNavigate } from "react-router-dom"
import useAuthStore from "../store/auth"
import { DesignFreezeReport } from "../components/DesignFreezeReport"
import { XatExtraccio } from "../components/XatExtraccio"

const API = import.meta.env.VITE_API_URL || ""

const STEPS = ["Puja fitxer", "Anàlisi IA", "Design Freeze", "Confirmar"]

function StepIndicator({ current }) {
  return (
    <div style={{ display: "flex", alignItems: "center", marginBottom: 28, gap: 0 }}>
      {STEPS.map((s, i) => {
        const done = i < current
        const active = i === current
        return (
          <div key={s} style={{ display: "flex", alignItems: "center" }}>
            <div style={{
              display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
            }}>
              <div style={{
                width: 28, height: 28, borderRadius: "50%",
                background: active ? "#c27a2a" : done ? "#1a2a1a" : "#111",
                border: `1px solid ${active ? "#c27a2a" : done ? "#2a4a2a" : 'var(--border)'}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 11, fontFamily: "IBM Plex Mono, monospace",
                color: active ? "#1d1d1b" : done ? "#4a9a4a" : "#333",
                fontWeight: active ? 600 : 400,
              }}>
                {done ? "✓" : i + 1}
              </div>
              <div style={{
                fontSize: 10, whiteSpace: "nowrap",
                fontFamily: "IBM Plex Mono, monospace",
                color: active ? "#c27a2a" : done ? "#4a9a4a" : "#333",
              }}>
                {s}
              </div>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{ width: 40, height: 1, background: i < current ? "#2a4a2a" : "#1a1a1a", margin: "0 4px", marginBottom: 18 }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function UploadModelWizard() {
  const navigate = useNavigate()
  // Token via Zustand auth store (clau real: 'access_token' al localStorage).
  // Fallback al localStorage directe per si el store no ha inicialitzat encara.
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const [step, setStep] = useState(0)
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
    setStep(1)
    setLoadingMsg("Analitzant document amb IA...")

    // Llegir fitxer com a base64 en paral·lel — el xat el reutilitza al pas 2.
    const reader = new FileReader()
    reader.onload = (e) => {
      const base64 = String(e.target.result).split(',')[1]
      setFileBase64(base64)
      setFileType(file.type)
    }
    reader.readAsDataURL(file)

    const fd = new FormData()
    fd.append("file", file)

    try {
      const r = await fetch(`${API}/api/v1/models/extract-from-file/`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`)
      setResult(data)
      setStep(2)
    } catch (e) {
      setError(e.message)
      setStep(0)
    }
    setLoading(false)
    setLoadingMsg("")
  }

  const handleConfirm = async (extracted) => {
    if (!token) {
      setError("Sessió no autenticada — torna a iniciar sessió.")
      navigate("/login")
      return
    }
    setLoading(true)
    setStep(3)
    setLoadingMsg("Creant model...")
    try {
      const r = await fetch(`${API}/api/v1/models/create-from-extraction/`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ extracted }),
      })
      const data = await r.json()
      if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`)
      navigate(`/models/${data.model_id}`)
    } catch (e) {
      setError(e.message)
      setStep(2)
    }
    setLoading(false)
    setLoadingMsg("")
  }

  return (
    <div style={{ padding: "24px", maxWidth: 640, margin: "0 auto" }}>
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
        Puja una fitxa tècnica i la IA extraurà les dades automàticament.
      </p>

      <StepIndicator current={step} />

      {/* Error */}
      {error && (
        <div style={{
          padding: "8px 12px", marginBottom: 16, borderRadius: 4,
          background: 'var(--bg-muted)', border: "1px solid #4a2020",
          color: "#cc6666", fontSize: 11, fontFamily: "IBM Plex Mono, monospace",
        }}>
          ✗ {error}
        </div>
      )}

      {/* Step 0 — Puja */}
      {step === 0 && (
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

          <div style={{ fontSize: 11, color: 'var(--text-main)', marginBottom: 20, fontFamily: "IBM Plex Mono, monospace", lineHeight: 1.6 }}>
            Accepta: fitxes tècniques PLM, mesuraments, fit comments, sketches escanejats.
            Si el document no conté mesures de talla base, el grading es generarà automàticament
            des de les Grading Rules configurades al sistema.
          </div>

          <button
            onClick={handleAnalyze}
            disabled={!file || loading}
            style={{
              width: "100%", padding: "10px",
              background: file ? 'var(--bg-muted)' : 'var(--bg-card)',
              color: file ? "#7a7acc" : "#333",
              border: `1px solid ${file ? "#3a3a6a" : "#222"}`,
              borderRadius: 4, fontSize: 12,
              fontFamily: "IBM Plex Mono, monospace",
              cursor: file ? "pointer" : "not-allowed",
            }}
          >
            ⚡ Analitzar amb IA
          </button>
        </div>
      )}

      {/* Step 1 — Loading */}
      {step === 1 && loading && (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <div style={{ fontSize: 32, marginBottom: 16 }}>⏳</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: "IBM Plex Mono, monospace" }}>
            {loadingMsg}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-main)', marginTop: 8 }}>
            Pot trigar 15-45 segons depenent del document
          </div>
        </div>
      )}

      {/* Step 2 — Design Freeze + xat IA */}
      {step === 2 && result && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20, height: 500 }}>
          {/* Columna esquerra: report extracció */}
          <div style={{ overflowY: 'auto' }}>
            <DesignFreezeReport
              result={result}
              onConfirm={handleConfirm}
              onReject={() => { setStep(0); setResult(null) }}
            />
          </div>
          {/* Columna dreta: xat IA */}
          <div style={{ border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
            <XatExtraccio
              extraccio={result?.extracted}
              fileBase64={fileBase64}
              fileType={fileType}
              onUpdate={(updates) => {
                setResult(prev => ({
                  ...prev,
                  extracted: { ...prev.extracted, ...updates }
                }))
              }}
            />
          </div>
        </div>
      )}

      {/* Step 3 — Creant */}
      {step === 3 && loading && (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <div style={{ fontSize: 32, marginBottom: 16 }}>⚙</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: "IBM Plex Mono, monospace" }}>
            {loadingMsg}
          </div>
        </div>
      )}
    </div>
  )
}
