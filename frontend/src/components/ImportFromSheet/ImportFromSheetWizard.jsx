import { useState, useRef } from 'react'
import useAuthStore from '../../store/auth'

const API = import.meta.env.VITE_API_URL || ''

const CONFIDENCE_STYLES = {
  HIGH:   { fg: '#3b6d11', bg: '#f0f9f0', border: '#c0dd97', label: 'Alt' },
  MEDIUM: { fg: '#c27a2a', bg: '#fdf6ee', border: '#e0c8a0', label: 'Mitjà' },
  LOW:    { fg: '#a32d2d', bg: '#fff0f0', border: '#f0c0c0', label: 'Baix' },
  CUSTOM: { fg: '#868685', bg: '#f5f0ea', border: '#e0d5c5', label: 'Personalitzat' },
}

export default function ImportFromSheetWizard({ onModelCreated, onClose }) {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')

  const [step, setStep] = useState('upload') // upload → preview
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [extracted, setExtracted] = useState(null)
  const [error, setError] = useState(null)
  const [pomOverrides, setPomOverrides] = useState({})
  const fileRef = useRef(null)

  const authHeaders = () => token ? { Authorization: `Bearer ${token}` } : {}

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch(`${API}/api/v1/models/extract-sheet/`, {
        method: 'POST',
        headers: authHeaders(), // sense Content-Type — FormData posa el boundary
        body: formData,
      })
      const data = await res.json().catch(() => ({}))

      if (!res.ok) {
        setError(data.error || data.message || `Error ${res.status}`)
        setLoading(false)
        return
      }
      if (data.error) {
        setError(data.message || data.error)
        setLoading(false)
        return
      }

      setExtracted(data)
      setStep('preview')
    } catch (e) {
      setError(`Error de connexió: ${String(e)}`)
    }
    setLoading(false)
  }

  const handleCreate = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/v1/models/create-from-sheet/`, {
        method: 'POST',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          extracted,
          overrides: { pom_mappings: pomOverrides },
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.ok) {
        onModelCreated && onModelCreated(data.model_id)
        onClose && onClose()
      } else {
        setError(data.error || `Error ${res.status} creant el model`)
      }
    } catch (e) {
      setError(`Error de connexió: ${String(e)}`)
    }
    setLoading(false)
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 100,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontFamily: 'IBM Plex Mono, monospace',
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 12,
          width: '100%', maxWidth: 820, maxHeight: '90vh',
          display: 'flex', flexDirection: 'column', overflow: 'hidden',
          boxShadow: '0 25px 50px rgba(0,0,0,0.25)',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 20px', borderBottom: '0.5px solid #e0d5c5',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: 15, fontWeight: 600, color: '#1d1d1b' }}>
              Importar fitxa tècnica
            </h2>
            <p style={{ margin: '2px 0 0', fontSize: 11, color: '#868685' }}>
              {step === 'upload' && 'Puja un PDF o imatge de la fitxa tècnica'}
              {step === 'preview' && 'Revisa les dades extretes i confirma els mappings'}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', fontSize: 22, lineHeight: 1,
              cursor: 'pointer', color: '#868685',
            }}
            aria-label="Tancar"
          >×</button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
          {error && (
            <div style={{
              background: '#fff0f0', border: '0.5px solid #f0c0c0',
              borderRadius: 8, padding: '8px 12px', marginBottom: 14,
              color: '#a32d2d', fontSize: 11,
            }}>
              {error}
            </div>
          )}

          {step === 'upload' && (
            <UploadStep file={file} setFile={setFile} fileRef={fileRef} />
          )}

          {step === 'preview' && extracted && (
            <ExtractionPreview
              extracted={extracted}
              pomOverrides={pomOverrides}
              onOverride={(clientCode, pomCode) =>
                setPomOverrides(prev => ({ ...prev, [clientCode]: pomCode.trim().toUpperCase() }))
              }
            />
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '12px 20px', borderTop: '0.5px solid #e0d5c5',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px', borderRadius: 6, cursor: 'pointer',
              background: '#fff', color: '#868685',
              border: '0.5px solid #e0d5c5',
              fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
            }}
          >Cancel·lar</button>

          <div style={{ display: 'flex', gap: 8 }}>
            {step === 'upload' && (
              <button
                onClick={handleUpload}
                disabled={!file || loading}
                style={{
                  padding: '8px 18px', borderRadius: 6,
                  border: 'none', fontWeight: 600,
                  background: file && !loading ? '#c27a2a' : '#e0d5c5',
                  color: '#fff',
                  cursor: file && !loading ? 'pointer' : 'not-allowed',
                  fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
                }}
              >{loading ? 'Analitzant...' : 'Analitzar fitxa'}</button>
            )}

            {step === 'preview' && (
              <>
                <button
                  onClick={() => { setStep('upload'); setExtracted(null); setPomOverrides({}) }}
                  disabled={loading}
                  style={{
                    padding: '8px 16px', borderRadius: 6, cursor: 'pointer',
                    background: '#fff', color: '#868685',
                    border: '0.5px solid #e0d5c5',
                    fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
                  }}
                >← Tornar</button>
                {extracted?._meta?.can_create_model && (
                  <button
                    onClick={handleCreate}
                    disabled={loading}
                    style={{
                      padding: '8px 18px', borderRadius: 6,
                      border: 'none', fontWeight: 600,
                      background: '#c27a2a', color: '#fff',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      opacity: loading ? 0.6 : 1,
                      fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
                    }}
                  >{loading ? 'Creant model...' : 'Crear model'}</button>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function UploadStep({ file, setFile, fileRef }) {
  const [dragging, setDragging] = useState(false)
  return (
    <div>
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => {
          e.preventDefault()
          setDragging(false)
          const f = e.dataTransfer.files?.[0]
          if (f) setFile(f)
        }}
        style={{
          border: `2px dashed ${file ? '#c27a2a' : dragging ? '#c27a2a' : '#e0d5c5'}`,
          borderRadius: 10, padding: '40px 24px', textAlign: 'center',
          cursor: 'pointer',
          background: file ? '#fdf6ee' : dragging ? '#fdf9f5' : '#fafaf8',
          transition: 'all .15s',
        }}
      >
        <div style={{ fontSize: 11, color: '#868685', marginBottom: 8, letterSpacing: '.06em' }}>
          UPLOAD
        </div>
        {file ? (
          <div>
            <p style={{ fontWeight: 600, color: '#c27a2a', margin: 0, fontSize: 13 }}>
              {file.name}
            </p>
            <p style={{ color: '#868685', fontSize: 11, margin: '4px 0 0' }}>
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
        ) : (
          <div>
            <p style={{ fontWeight: 500, color: '#1d1d1b', margin: 0, fontSize: 12 }}>
              Arrossega un fitxer o clica per seleccionar
            </p>
            <p style={{ color: '#868685', fontSize: 10, margin: '6px 0 0' }}>
              PDF, JPG, PNG o WEBP · Màxim 20 MB
            </p>
          </div>
        )}
      </div>
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp"
        style={{ display: 'none' }}
        onChange={e => setFile(e.target.files?.[0] || null)}
      />

      {/* Handwritten document warning */}
      <div style={{
        marginTop: 14, background: '#fdf6ee', border: '0.5px solid #e0c8a0',
        borderRadius: 8, padding: '10px 12px',
        fontSize: 11, color: '#c27a2a',
      }}>
        <strong>Documents manuscrits o de baixa qualitat:</strong> l'extracció pot ser parcial.
        Calen com a mínim 3 mesures llegibles, talla base i tipus de prenda identificables
        per crear el model.
      </div>
    </div>
  )
}

function ExtractionPreview({ extracted, pomOverrides, onOverride }) {
  const meta = extracted._meta || {}
  const header = extracted.header || {}
  const measurements = extracted.measurements || []
  const usage = meta.usage || {}

  return (
    <div>
      {!meta.can_create_model && (
        <div style={{
          background: '#fff0f0', border: '0.5px solid #f0c0c0',
          borderRadius: 8, padding: '10px 12px', marginBottom: 14,
        }}>
          <strong style={{ color: '#a32d2d', fontSize: 12 }}>
            No es pot crear el model automàticament:
          </strong>
          <ul style={{ margin: '6px 0 0', paddingLeft: 18, color: '#a32d2d', fontSize: 11 }}>
            {(meta.blocking_reasons || []).map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      {extracted.flags?.length > 0 && (
        <div style={{
          background: '#fdf6ee', border: '0.5px solid #e0c8a0',
          borderRadius: 8, padding: '10px 12px', marginBottom: 14,
        }}>
          <strong style={{ color: '#c27a2a', fontSize: 11 }}>Avisos:</strong>
          {extracted.flags.map((f, i) => (
            <p key={i} style={{ margin: '4px 0 0', color: '#c27a2a', fontSize: 11 }}>• {f}</p>
          ))}
        </div>
      )}

      {/* FASE 1 — avís SUAU si el grading no s'ha extret: els POMs es mostren igualment. */}
      {extracted.grading_status && extracted.grading_status.status !== 'ok' && (
        <div style={{
          background: '#fff9e6', border: '0.5px solid #f0c040',
          borderRadius: 8, padding: '10px 12px', marginBottom: 14,
        }}>
          <strong style={{ color: '#7a5a00', fontSize: 11 }}>
            {extracted.grading_status.status === 'skipped'
              ? 'Grading no detectat al document'
              : 'Grading no extret'}
          </strong>
          <p style={{ margin: '4px 0 0', color: '#7a5a00', fontSize: 11 }}>
            Els POMs i la talla base s'han extret correctament. El grading l'entraràs després
            a la taula de mides.
          </p>
        </div>
      )}

      {/* Header del model */}
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6,
        background: '#fafaf8', borderRadius: 8, padding: '10px 14px',
        border: '0.5px solid #e0d5c5', marginBottom: 14,
      }}>
        {[
          ['Marca', header.brand],
          ['Estil', header.style_name],
          ['Referència', header.style_reference],
          ['Temporada', header.season],
          ['Tipus prenda', extracted.garment_type_code],
          ['Talla base', extracted.base_size],
          ['Run de talles', (extracted.sizes || []).join(' · ')],
          ['Confiança', extracted.overall_confidence],
        ].filter(([, v]) => v).map(([label, val]) => (
          <div key={label} style={{ fontSize: 11 }}>
            <span style={{ color: '#868685' }}>{label}: </span>
            <strong style={{ color: '#1d1d1b' }}>{val}</strong>
          </div>
        ))}
      </div>

      {/* Resum + telemetria */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        <Pill bg="#eef4fc" fg="#2a5a8a">{meta.total_measurements_count} mesures</Pill>
        <Pill bg="#f0f9f0" fg="#3b6d11">{meta.high_confidence_count} alta confiança</Pill>
        <Pill bg="#fff0f0" fg="#a32d2d">{meta.needs_review_count} revisió manual</Pill>
        {usage.input_tokens != null && (
          <Pill bg="#f5f0ea" fg="#868685">
            {usage.input_tokens} in / {usage.output_tokens} out tokens
          </Pill>
        )}
        {usage.cache_read_input_tokens > 0 && (
          <Pill bg="#f0f9f0" fg="#3b6d11">cache hit: {usage.cache_read_input_tokens}</Pill>
        )}
      </div>

      {/* Taula de mesures */}
      <div style={{ overflowX: 'auto', border: '0.5px solid #e0d5c5', borderRadius: 8 }}>
        <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse', background: '#fff' }}>
          <thead>
            <tr style={{ background: '#fafaf8' }}>
              {['Codi client', 'Descripció', 'POM suggerit', 'Confiança', 'Valor talla base'].map((h, i) => (
                <th key={h} style={{
                  padding: '8px 10px',
                  textAlign: i === 4 ? 'right' : 'left',
                  fontWeight: 600, color: '#868685', fontSize: 10,
                  textTransform: 'uppercase', letterSpacing: '.06em',
                  borderBottom: '0.5px solid #e0d5c5',
                  fontFamily: 'IBM Plex Mono, monospace',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {measurements.map((m, i) => {
              const overrideCode = pomOverrides[m.client_code]
              const conf = overrideCode ? 'HIGH' : (m.pom_confidence || 'LOW')
              const confStyle = CONFIDENCE_STYLES[conf] || CONFIDENCE_STYLES.LOW
              const pomCode = overrideCode || m.pom_code
              const baseVal = m.values?.[extracted.base_size] ?? Object.values(m.values || {})[0]
              return (
                <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#fafaf8' }}>
                  <td style={tdStyle}>
                    <span style={{ color: '#c27a2a', fontFamily: 'IBM Plex Mono, monospace' }}>
                      {m.client_code || '—'}
                    </span>
                  </td>
                  <td style={{ ...tdStyle, color: '#1d1d1b' }}>{m.description}</td>
                  <td style={tdStyle}>
                    {(m.pom_confidence === 'LOW' || m.pom_confidence === 'CUSTOM' || !m.pom_code) ? (
                      <input
                        type="text"
                        placeholder="POM-001"
                        defaultValue={pomCode || ''}
                        onBlur={e => e.target.value && onOverride(m.client_code, e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') e.target.blur() }}
                        style={{
                          border: '0.5px solid #f0c0c0', borderRadius: 4,
                          padding: '3px 6px', fontSize: 10, width: 88,
                          fontFamily: 'IBM Plex Mono, monospace',
                          textTransform: 'uppercase',
                        }}
                      />
                    ) : (
                      <span style={{
                        fontFamily: 'IBM Plex Mono, monospace', fontSize: 10,
                        color: '#2a5a8a', fontWeight: 600,
                      }}>{pomCode}</span>
                    )}
                  </td>
                  <td style={tdStyle}>
                    <span style={{
                      fontSize: 9, padding: '2px 6px', borderRadius: 3,
                      background: confStyle.bg, color: confStyle.fg,
                      border: `0.5px solid ${confStyle.border}`,
                      fontWeight: 600, letterSpacing: '.04em',
                    }}>{confStyle.label}</span>
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'right', fontFamily: 'IBM Plex Mono, monospace' }}>
                    {baseVal != null ? `${baseVal} cm` : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Imatges detectades */}
      {extracted.images_to_extract?.length > 0 && (
        <div style={{
          marginTop: 12, padding: '10px 12px',
          background: '#fafaf8', border: '0.5px solid #e0d5c5', borderRadius: 8,
        }}>
          <p style={{ margin: '0 0 6px', fontSize: 11, fontWeight: 600, color: '#1d1d1b' }}>
            Imatges detectades ({extracted.images_to_extract.length}):
          </p>
          {extracted.images_to_extract.map((img, i) => (
            <p key={i} style={{ margin: '3px 0', fontSize: 10, color: '#868685' }}>
              • Pàg. {img.page} — {img.type}: {img.description}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}

function Pill({ bg, fg, children }) {
  return (
    <span style={{
      fontSize: 10, padding: '3px 8px', borderRadius: 4,
      background: bg, color: fg,
      fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600,
      whiteSpace: 'nowrap',
    }}>{children}</span>
  )
}

const tdStyle = {
  padding: '6px 10px',
  borderBottom: '0.5px solid #f0eee9',
  verticalAlign: 'middle',
}
