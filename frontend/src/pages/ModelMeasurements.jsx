import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import EditableTable from '../components/EditableTable/EditableTable'
import ImportWizard from '../components/ImportWizard/ImportWizard'

const API = import.meta.env.VITE_API_URL || ''

const thStyle = {
  padding: '8px 12px', textAlign: 'left', fontSize: 12,
  fontWeight: 500, borderBottom: '1px solid var(--color-border-tertiary, #e0d5c5)',
}
const tdStyle = { padding: '6px 12px', verticalAlign: 'middle' }

export default function ModelMeasurements() {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const [model, setModel] = useState(null)
  const [mode, setMode] = useState('loading') // 'loading' | 'selector' | 'manual' | 'import' | 'resultat'

  // Manual
  const [pomsSuggerits, setPomsSuggerits] = useState([])
  const [selectedPomIds, setSelectedPomIds] = useState([])

  // Taula final
  const [taulaRows, setTaulaRows] = useState([])
  const [sizesAmbDades, setSizesAmbDades] = useState(null)
  const [deltes, setDeltes] = useState(null)
  const [saving, setSaving] = useState(false)
  const [generatingGrading, setGeneratingGrading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    if (!id) return
    Promise.all([
      fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders }).then(r => r.json()),
      fetch(`${API}/api/v1/models/${id}/poms-suggerits/`, { headers: authHeaders }).then(r => r.json()),
    ]).then(([modelData, pomsData]) => {
      setModel(modelData)
      const poms = pomsData.poms || []
      setPomsSuggerits(poms)
      setSelectedPomIds(prev => prev.length > 0 ? prev : poms.filter(p => p.is_key).map(p => p.pom_id))
    }).catch(() => setError('Error carregant les dades'))
  }, [id])

  const togglePom = (pom) => {
    setSelectedPomIds(prev =>
      prev.includes(pom.pom_id)
        ? prev.filter(id => id !== pom.pom_id)
        : [...prev, pom.pom_id]
    )
  }

  const handleGenerateGrading = async () => {
    setGeneratingGrading(true); setError('')
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/generar-grading/`, {
        method: 'POST', headers: authHeaders,
      })
      const d = await r.json()
      if (r.ok) {
        setTaulaRows(d.rows || [])
        // Grading fills graded for all sizes → we refresh columns/delta.
        fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
          .then(r => r.json()).then(refreshTableMeta).catch(() => {})
      } else {
        setError(d.error || 'Error generant grading')
      }
    } catch {
      setError('Error de connexió')
    } finally {
      setGeneratingGrading(false)
    }
  }

  // Refresh column/delta metadata from taula-mesures (single source).
  const refreshTableMeta = (d) => {
    setSizesAmbDades(d.sizes_amb_dades || null)
    setDeltes(d.deltes || null)
  }

  // Materialització família→item: en tenir el model, si té garment_type_item, instanciem la
  // pertinença de POMs de l'item (idempotent) ABANS de carregar la taula. Sense item → avís.
  useEffect(() => {
    if (!id || !model) return
    const loadTable = () =>
      fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
        .then(r => r.json())
        .then(d => {
          refreshTableMeta(d)
          if (d.rows && d.rows.length > 0) {
            setTaulaRows(d.rows)
          }
          // La pantalla d'opcions SEMPRE espera que l'usuari triï (manual/import).
          // Única excepció: si la taula ja està TANCADA → directe a la vista de lectura.
          setMode(d.tancat ? 'resultat' : 'selector')
        })
        .catch(() => setMode('selector'))
    if (model.garment_type_item) {
      fetch(`${API}/api/v1/models/${id}/materialitzar-poms/`, { method: 'POST', headers: authHeaders })
        .then(() => loadTable())
        .catch(() => loadTable())
    } else {
      setNotice("Aquest model no té tipus d'ítem (garment_type_item) definit: no es materialitzen els POMs de la plantilla.")
      loadTable()
    }
  }, [id, model])

  return (
    <>
      {error && (
        <div style={{
          maxWidth: 1000, margin: '1rem auto 0',
          background: '#fee', border: '1px solid #fcc', borderRadius: 8,
          padding: '0.75rem 1rem', fontSize: 13, color: '#c00',
          fontFamily: 'IBM Plex Mono, monospace',
        }}>{error}</div>
      )}

      {notice && (
        <div style={{
          maxWidth: 1000, margin: '1rem auto 0',
          background: '#fff9e6', border: '1px solid #f0c040', borderRadius: 8,
          padding: '0.75rem 1rem', fontSize: 13, color: '#7a5a00',
          fontFamily: 'IBM Plex Mono, monospace',
        }}>{notice}</div>
      )}

      {mode === 'loading' && !error && (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
          Carregant…
        </div>
      )}

      {mode === 'selector' && (
        <div style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1rem' }}>
          <ModelSummaryBar model={model} />

          <h2 style={{ fontSize: 18, fontWeight: 500, margin: '1.5rem 0 0.5rem' }}>
            Mesures i grading
          </h2>
          <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)', marginBottom: '1.5rem' }}>
            Introdueix les mesures de la talla base. El sistema calcularà el grading per a totes les talles.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div onClick={() => setMode('manual')}
              style={{
                background: 'var(--color-background-primary, #fff)',
                border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                borderRadius: 12, padding: '1.5rem', cursor: 'pointer',
              }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>
                <i className="ti ti-pencil" style={{ color: 'var(--gold)' }} />
              </div>
              <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 6 }}>Introduir manualment</div>
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)' }}>
                El sistema proposa els POMs estàndard per a {model?.garment_type_nom || 'aquest tipus de peça'}.
                Introdueix els valors de la talla base.
              </div>
              {pomsSuggerits.length > 0 && (
                <div style={{ marginTop: 12, fontSize: 12, color: 'var(--gold)' }}>
                  {pomsSuggerits.length} POMs disponibles · {pomsSuggerits.filter(p => p.is_key).length} KEY
                </div>
              )}
            </div>

            <div onClick={() => setMode('import')}
              style={{
                background: 'var(--color-background-primary, #fff)',
                border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                borderRadius: 12, padding: '1.5rem', cursor: 'pointer',
              }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>
                <i className="ti ti-bolt" style={{ color: 'var(--gold)' }} />
              </div>
              <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 6 }}>Importar de fitxa tècnica</div>
              <div style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)' }}>
                Puja un PDF o imatge de la fitxa tècnica del client.
                La IA extraurà les mesures, talles i grading automàticament.
              </div>
            </div>
          </div>
        </div>
      )}

      {mode === 'manual' && (
        <div style={{ maxWidth: 1000, margin: '0 auto', padding: '2rem 1rem' }}>
          <ModelSummaryBar model={model} />

          {taulaRows.length === 0 && pomsSuggerits.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)', marginBottom: 8 }}>
                POMs suggerits per a aquest tipus de peça — clica per afegir a la taula:
              </div>
              {pomsSuggerits.filter(p => p.is_key).length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <span style={{ fontSize: 11, color: 'var(--gold)', marginRight: 6,
                                 fontWeight: 500 }}>KEY</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                    {pomsSuggerits.filter(p => p.is_key).map(p => (
                      <POMChipSuggerit key={p.pom_id} pom={p}
                        selected={selectedPomIds.includes(p.pom_id)}
                        onToggle={() => togglePom(p)} />
                    ))}
                  </div>
                </div>
              )}
              {pomsSuggerits.filter(p => !p.is_key).length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {pomsSuggerits.filter(p => !p.is_key).map(p => (
                    <POMChipSuggerit key={p.pom_id} pom={p}
                      selected={selectedPomIds.includes(p.pom_id)}
                      onToggle={() => togglePom(p)} />
                  ))}
                </div>
              )}
            </div>
          )}

          <EditableTable
            rows={taulaRows.length > 0 ? taulaRows : pomsSuggerits
              .filter(p => selectedPomIds.includes(p.pom_id))
              .map((p, i) => ({
                id: `tmp-${p.pom_id}`,
                pom_id: p.pom_id, pom_code: p.pom_code,
                nom_ca: p.nom_ca, nom_en: p.nom_en, nom_fitxa: '',
                base_value_cm: null, graded: {}, ordre: i,
              }))}
            sizeRun={(sizesAmbDades && sizesAmbDades.length
              ? sizesAmbDades
              : model?.size_run_model?.split('·').map(s => s.trim())) || []}
            baseSize={model?.base_size_label}
            deltes={deltes}
            modelId={parseInt(id)}
            isImport={false}
            onSaved={(newRows) => setTaulaRows(newRows)}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginTop: 24 }}>
            <button type="button" onClick={() => setMode('selector')}
              style={{ padding: '8px 16px', border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                       borderRadius: 6, background: 'transparent', cursor: 'pointer', fontSize: 13 }}>
              ← Enrere
            </button>
            {taulaRows.length > 0 && (
              <div style={{ display: 'flex', gap: 8 }}>
                {model?.grading_rule_set && (
                  <button type="button" onClick={handleGenerateGrading} disabled={generatingGrading}
                    style={{
                      padding: '8px 16px', border: '0.5px solid var(--gold)',
                      borderRadius: 6, background: 'transparent',
                      color: 'var(--gold)', fontSize: 13, cursor: 'pointer',
                    }}>
                    {generatingGrading ? '⏳ Generant...' : '⚡ Generar grading automàtic'}
                  </button>
                )}
                <button type="button" onClick={() => navigate(`/models/${id}/teixit`)}
                  style={{
                    padding: '8px 20px', background: 'var(--gold)', color: '#fff',
                    border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 500,
                    cursor: 'pointer',
                  }}>
                  Continuar → Teixit
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {mode === 'import' && (
        <div style={{ maxWidth: 1100, margin: '0 auto', padding: '2rem 1rem' }}>
          <ModelSummaryBar model={model} />
          {/* Import Wizard de 5 passos (substitueix el flux inline antic). */}
          <ImportWizard
            model={model}
            onCancel={() => setMode('selector')}
            onComplete={() => {
              fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders })
                .then(r => r.json())
                .then(d => { setTaulaRows(d.rows || []); refreshTableMeta(d); setMode('resultat') })
                .catch(() => setMode('selector'))
            }}
          />
        </div>
      )}

      {mode === 'resultat' && (
        <div style={{ width: '100%', padding: '1rem' }}>
          <ModelSummaryBar model={model} />

          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ fontSize: 16, fontWeight: 500, margin: 0 }}>
              Taula de mesures i grading
            </h2>
            <button type="button" onClick={() => setMode('manual')}
              style={{ padding: '6px 14px', border: '0.5px solid var(--color-border-tertiary)',
                       borderRadius: 6, background: 'transparent', cursor: 'pointer', fontSize: 13 }}>
              ✏ Editar mesures
            </button>
          </div>

          <EditableTable
            rows={taulaRows}
            sizeRun={(sizesAmbDades && sizesAmbDades.length
              ? sizesAmbDades
              : model?.size_run_model?.split('·').map(s => s.trim())) || []}
            baseSize={model?.base_size_label}
            deltes={deltes}
            modelId={parseInt(id)}
            isImport={false}
            onSaved={(newRows) => setTaulaRows(newRows)}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'center', marginTop: 16 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              {model?.grading_rule_set && (
                <button type="button" onClick={handleGenerateGrading} disabled={generatingGrading}
                  style={{
                    padding: '8px 16px', border: '0.5px solid var(--gold)',
                    borderRadius: 6, background: 'transparent',
                    color: 'var(--gold)', fontSize: 13, cursor: 'pointer',
                    fontFamily: 'IBM Plex Mono, monospace',
                  }}>
                  {generatingGrading ? '⏳ Generant...' : '⚡ Generar grading automàtic'}
                </button>
              )}
            </div>
            <button type="button" onClick={() => navigate(`/models/${id}/teixit`)}
              style={{
                padding: '8px 20px', borderRadius: 6, border: 'none',
                fontSize: 14, fontWeight: 500,
                background: 'var(--gold)', color: '#fff', cursor: 'pointer',
                fontFamily: 'IBM Plex Mono, monospace',
              }}>
              Continuar → Teixit
            </button>
          </div>
        </div>
      )}
    </>
  )
}

function POMChipSuggerit({ pom, selected, onToggle }) {
  return (
    <button type="button" onClick={onToggle}
      style={{
        padding: '3px 10px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
        border: selected
          ? '1.5px solid var(--gold)' : '0.5px solid var(--color-border-tertiary, #e0d5c5)',
        background: selected ? '#fdf6ee' : 'transparent',
        color: selected ? '#7a4a10' : 'var(--color-text-secondary, #868685)',
        fontFamily: 'IBM Plex Mono, monospace',
      }}>
      <span style={{ fontFamily: 'monospace', marginRight: 4 }}>{pom.pom_code}</span>
      {pom.nom_ca || pom.nom_en}
    </button>
  )
}

function ModelSummaryBar({ model }) {
  if (!model) return null
  return (
    <div style={{
      display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap',
      background: 'var(--color-background-secondary, #f5f0ea)',
      border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
      borderRadius: 8, padding: '10px 16px', marginBottom: 16, fontSize: 13,
      fontFamily: 'IBM Plex Mono, monospace',
    }}>
      <span><strong>{model.codi_intern}</strong></span>
      {model.nom_prenda && <span>{model.nom_prenda}</span>}
      {model.target && <span style={{ color: 'var(--color-text-secondary, #868685)' }}>{model.target}</span>}
      {model.construction && <span style={{ color: 'var(--color-text-secondary, #868685)' }}>{model.construction}</span>}
      {model.base_size_label && (
        <span style={{ color: 'var(--gold)' }}>Base: {model.base_size_label}</span>
      )}
      {model.size_run_model && (
        <span style={{ color: 'var(--color-text-secondary, #868685)', fontFamily: 'monospace' }}>
          {model.size_run_model}
        </span>
      )}
    </div>
  )
}
