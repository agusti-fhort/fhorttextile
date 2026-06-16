
import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import useAuthStore from "../store/auth"

const API = import.meta.env.VITE_API_URL || ""

const STEPS = ["Benvinguda", "Configuració", "Dades", "Verificació"]

export default function OnboardingWizard() {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [status, setStatus] = useState(null)
  const [config, setConfig] = useState({ nom_empresa: '', unitat_mesura: 'CM', norma_referencia: 'ISO_8559' })
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [msg, setMsg] = useState(null)

  useEffect(() => {
    fetch(`${API}/api/v1/onboarding/status/`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(r => r.json()).then(setStatus).catch(() => {})
  }, [token])

  const saveConfig = async () => {
    const r = await fetch(`${API}/api/v1/onboarding/config/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
    const d = await r.json()
    if (r.ok) { setMsg({ type: 'ok', text: d.missatge }); setStep(2) }
    else setMsg({ type: 'error', text: d.error })
  }

  const uploadExcel = async () => {
    if (!file) return
    setUploading(true)
    const fd = new FormData()
    fd.append('file', file)
    const r = await fetch(`${API}/api/v1/onboarding/setup-from-excel/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: fd,
    })
    const d = await r.json()
    if (r.ok) { setUploadResult(d); setStep(3) }
    else setMsg({ type: 'error', text: d.error })
    setUploading(false)
  }

  return (
    <div style={{ padding: '40px', maxWidth: 600, margin: '0 auto' }}>
      <div style={{ marginBottom: 8, fontSize: 10, color: 'var(--text-muted)', letterSpacing: '.08em', textTransform: 'uppercase' }}>
        FHORT Textile Tech · Onboarding
      </div>
      <h1 style={{ fontSize: 22, fontWeight: 500, color: 'var(--gold)', margin: '0 0 24px' }}>
        Configuració inicial
      </h1>

      {msg && (
        <div style={{ padding: '8px 12px', marginBottom: 16, borderRadius: 4, fontSize: 11,
          background: msg.type === 'ok' ? '#f0f9f0' : '#fff0f0',
          border: `1px solid ${msg.type === 'ok' ? '#c0dd97' : '#f09595'}`,
          color: msg.type === 'ok' ? '#3b6d11' : '#a32d2d' }}>
          {msg.text}
        </div>
      )}

      {/* Step 0 */}
      {step === 0 && (
        <div>
          <p style={{ fontSize: 13, color: 'var(--text-main)', lineHeight: 1.7, marginBottom: 20 }}>
            Benvingut a FHORT Textile Tech. Configurem el teu entorn en 3 passos:
          </p>
          {status && (
            <div style={{ padding: '12px 16px', border: '1px solid var(--border)', borderRadius: 6, marginBottom: 20 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
                Estat actual: <strong style={{ color: 'var(--gold)' }}>{status.percentatge}% completat</strong>
              </div>
              {Object.entries(status.steps || {}).map(([k, s]) => (
                <div key={k} style={{ display: 'flex', gap: 8, padding: '3px 0', fontSize: 11 }}>
                  <span style={{ color: s.ok ? '#3b6d11' : 'var(--text-muted)' }}>{s.ok ? '✓' : '○'}</span>
                  <span style={{ color: s.ok ? 'var(--text-main)' : 'var(--text-muted)' }}>{s.label}</span>
                  <span style={{ marginLeft: 'auto', color: 'var(--text-muted)', fontSize: 10 }}>{s.descripcio}</span>
                </div>
              ))}
            </div>
          )}
          <button onClick={() => setStep(1)} style={{
            padding: '9px 20px', borderRadius: 4, fontSize: 12, cursor: 'pointer',
            background: '#f5e6d0', color: 'var(--gold)', border: '1px solid var(--gold)',
          }}>Començar →</button>
        </div>
      )}

      {/* Step 1 — Configuration */}
      {step === 1 && (
        <div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Nom de l\'empresa *</label>
            <input value={config.nom_empresa} onChange={e => setConfig(c => ({...c, nom_empresa: e.target.value}))}
              placeholder="Ex: Textiles Brownie SL"
              style={{ width: '100%', padding: '7px 10px', border: '1px solid var(--border)', borderRadius: 4, fontSize: 12, boxSizing: 'border-box' }} />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>Unitats de mesura</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {['CM', 'INCH'].map(u => (
                <button key={u} onClick={() => setConfig(c => ({...c, unitat_mesura: u}))} style={{
                  padding: '6px 16px', borderRadius: 4, fontSize: 11, cursor: 'pointer',
                  background: config.unitat_mesura === u ? '#f5e6d0' : 'var(--white)',
                  color: config.unitat_mesura === u ? 'var(--gold)' : 'var(--text-muted)',
                  border: `1px solid ${config.unitat_mesura === u ? 'var(--gold)' : 'var(--border)'}`,
                }}>{u}</button>
              ))}
            </div>
          </div>
          <button onClick={saveConfig} disabled={!config.nom_empresa} style={{
            padding: '9px 20px', borderRadius: 4, fontSize: 12, cursor: 'pointer',
            background: '#f5e6d0', color: 'var(--gold)', border: '1px solid var(--gold)',
          }}>Guardar i continuar →</button>
        </div>
      )}

      {/* Step 2 — Carregar dades */}
      {step === 2 && (
        <div>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>
            Carrega el fitxer <strong>FHORT_Master_Data_Reference_v2.xlsx</strong> per
            inicialitzar el catàleg de POMs, grading rules i size systems.
          </p>
          <input type="file" accept=".xlsx" onChange={e => setFile(e.target.files[0])}
            style={{ marginBottom: 12, fontSize: 11 }} />
          {file && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12 }}>
              {file.name} · {(file.size/1024).toFixed(0)} KB
            </div>
          )}
          <button onClick={uploadExcel} disabled={!file || uploading} style={{
            padding: '9px 20px', borderRadius: 4, fontSize: 12, cursor: 'pointer',
            background: file ? '#f5e6d0' : '#f5f0ea',
            color: file ? 'var(--gold)' : '#c8b89a',
            border: `1px solid ${file ? 'var(--gold)' : 'var(--border)'}`,
          }}>{uploading ? 'Carregant...' : '⬆ Carregar Excel'}</button>
        </div>
      )}

      {/* Step 3 — Verification */}
      {step === 3 && (
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#3b6d11', marginBottom: 16 }}>
            ✓ Configuració completada!
          </div>
          {uploadResult && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>Dades carregades:</div>
              {Object.entries(uploadResult.resultats || {}).map(([k, v]) => (
                <div key={k} style={{ display: 'flex', gap: 8, fontSize: 11, padding: '3px 0' }}>
                  <span style={{ color: v.ok ? '#3b6d11' : '#a32d2d' }}>{v.ok ? '✓' : '✗'}</span>
                  <span style={{ color: 'var(--text-main)' }}>{k.replace(/_/g, ' ')}</span>
                  {v.count !== undefined && <span style={{ marginLeft: 'auto', color: 'var(--text-muted)' }}>{v.count}</span>}
                </div>
              ))}
            </div>
          )}
          <button onClick={() => navigate('/')} style={{
            padding: '9px 20px', borderRadius: 4, fontSize: 12, cursor: 'pointer',
            background: '#f5e6d0', color: 'var(--gold)', border: '1px solid var(--gold)',
          }}>Anar al Dashboard →</button>
        </div>
      )}
    </div>
  )
}
