import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import EditableTable from '../components/EditableTable/EditableTable'
import Feedback from '../components/ui/Feedback'
import ActionsMenu from '../components/model/ActionsMenu'
import ProductionTab from '../components/model/ProductionTab'
import FittingTab from '../components/model/FittingTab'
import TaskLog from '../components/model/TaskLog'

const API = import.meta.env.VITE_API_URL || ''
const TABS = ['Resum', 'Mesures', 'Producció', 'Fitting', 'Fitxa tècnica', 'Fitxers', 'Anàlisi IA']

const btnSecondary = {
  background: 'transparent',
  border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
  borderRadius: 6, padding: '6px 12px', fontSize: 12,
  cursor: 'pointer', color: 'var(--color-text-primary, #1d1d1b)',
  display: 'flex', alignItems: 'center', gap: 4,
  fontFamily: 'IBM Plex Mono, monospace',
}

export default function ModelSheet({ defaultTab = 'Resum' }) {
  const { id } = useParams()
  const navigate = useNavigate()
  const token = localStorage.getItem('access_token')
  const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

  const { t } = useTranslation()
  const [model, setModel] = useState(null)
  const [activeTab, setActiveTab] = useState(defaultTab)
  const [taulaRows, setTaulaRows] = useState([])
  const [sizesAmbDades, setSizesAmbDades] = useState(null)
  const [deltes, setDeltes] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [feedback, setFeedback] = useState(null)
  const [hasPomTask, setHasPomTask] = useState(false)

  const reloadModel = useCallback(() => {
    fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders })
      .then(r => r.json()).then(setModel).catch(() => {})
  }, [id])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      fetch(`${API}/api/v1/models/${id}/`, { headers: authHeaders }).then(r => r.json()),
      fetch(`${API}/api/v1/models/${id}/taula-mesures/`, { headers: authHeaders }).then(r => r.json()),
      fetch(`${API}/api/v1/model-task-items/?model=${id}`, { headers: authHeaders }).then(r => r.json()),
    ]).then(([modelData, taulaData, tasksData]) => {
      setModel(modelData)
      setTaulaRows(taulaData.rows || [])
      setSizesAmbDades(taulaData.sizes_amb_dades || null)
      setDeltes(taulaData.deltes || null)
      const tasks = tasksData.results || tasksData || []
      setHasPomTask(Array.isArray(tasks) && tasks.some(tk => tk.task_type_code === 'pom'))
    }).catch(() => setError('Error carregant el model'))
    .finally(() => setLoading(false))
  }, [id])

  const handleDelete = async () => {
    if (!window.confirm(`Esborrar ${model?.codi_intern}? Aquesta acció no es pot desfer.`)) return
    try {
      const r = await fetch(`${API}/api/v1/models/${id}/`, {
        method: 'DELETE', headers: authHeaders,
      })
      if (r.ok || r.status === 204) navigate('/models')
      else setError('Error esborrant el model')
    } catch {
      setError('Error de connexió')
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center',
                    color: 'var(--color-text-secondary, #868685)',
                    fontFamily: 'IBM Plex Mono, monospace', fontSize: 13 }}>
        Carregant...
      </div>
    )
  }

  return (
    <div style={{ width: '100%', fontFamily: 'IBM Plex Mono, monospace' }}>
      <ModelSheetHeader model={model} onDelete={handleDelete} onFeedback={setFeedback} onChanged={reloadModel} />

      <div style={{ padding: '0 1.5rem' }}>
        <Feedback feedback={feedback} onDismiss={() => setFeedback(null)} />
      </div>

      <div style={{
        display: 'flex', gap: 8, padding: '0.75rem 1.5rem',
        borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
        background: 'var(--color-background-primary)',
      }}>
        {TABS.map(tab => (
          <button key={tab} type="button"
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '6px 16px', borderRadius: 6, border: 'none',
              background: activeTab === tab ? 'var(--gold)' : 'var(--color-background-secondary, #f5f0ea)',
              color: activeTab === tab ? '#fff' : 'var(--color-text-secondary, #868685)',
              cursor: 'pointer', fontSize: 13,
              fontWeight: activeTab === tab ? 500 : 400,
              fontFamily: 'IBM Plex Mono, monospace',
            }}>
            {tab}
          </button>
        ))}
      </div>

      {error && (
        <div style={{
          margin: '1rem 1.5rem', padding: '0.75rem 1rem',
          background: '#fee', border: '1px solid #fcc', borderRadius: 8,
          fontSize: 13, color: '#c00',
        }}>{error}</div>
      )}

      <div style={{ padding: '1.5rem' }}>
        {activeTab === 'Resum' && (
          <>
            <TabSummary
              model={model}
              modelId={parseInt(id)}
              sizesAmbDades={sizesAmbDades}
              onUpdated={reloadModel}
            />
            <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '0.5px solid var(--gray-l)' }}>
              <TaskLog modelId={parseInt(id)} />
            </div>
          </>
        )}
        {activeTab === 'Mesures' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                          marginBottom: 10, gap: 12 }}>
              <span style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                             fontFamily: 'IBM Plex Mono, monospace' }}>
                Consulta — l'edició de mides es fa a la tasca de POM.
              </span>
              {hasPomTask ? (
                <button type="button" onClick={() => navigate(`/models/${id}/mesures`)}
                  style={{ ...btnSecondary, borderColor: 'var(--gold)', color: 'var(--gold)' }}>
                  <i className="ti ti-ruler-2" style={{ fontSize: 14 }} />
                  Editar a la tasca de POM
                </button>
              ) : (
                <span title="Aquest model no té cap tasca de POM definida"
                  style={{ ...btnSecondary, opacity: 0.5, cursor: 'not-allowed' }}>
                  <i className="ti ti-ruler-2" style={{ fontSize: 14 }} />
                  Sense tasca de POM
                </span>
              )}
            </div>
            <EditableTable
              rows={taulaRows}
              sizeRun={(sizesAmbDades && sizesAmbDades.length
                ? sizesAmbDades
                : (model?.size_run_model || '').split('·').map(s => s.trim()).filter(Boolean))}
              baseSize={model?.base_size_label}
              deltes={deltes}
              modelId={parseInt(id)}
              isImport={false}
              readOnly={true}
              onSaved={setTaulaRows}
            />
          </div>
        )}
        {activeTab === 'Fitting' && <FittingTab model={model} onFeedback={setFeedback} />}
        {activeTab === 'Fitxers' && <TabFiles modelId={parseInt(id)} />}
        {activeTab === 'Fitxa tècnica' && <TechSheetTab modelId={id} navigate={navigate} />}
        {activeTab === 'Anàlisi IA' && <TabAIAnalysis modelId={parseInt(id)} />}
        {activeTab === 'Producció' && <ProductionTab model={model} onFeedback={setFeedback} onChanged={reloadModel} />}
      </div>
    </div>
  )
}

// Pestanya "Fitxa tècnica": resum read-only + accessos a l'editor (/fitxa).
// Consulta des del Model obre sense task_id → mode consulta. L'edició registrada
// es fa des del Kanban (que passa ?task_id=...). Vegeu TechSheetEditor.
function TechSheetTab({ modelId, navigate }) {
  const [sheet, setSheet]   = useState(null)
  const [loading, setLoading] = useState(true)
  const token   = localStorage.getItem('access_token')
  const headers = { Authorization: `Bearer ${token}` }

  useEffect(() => {
    fetch(`${API}/api/v1/models/${modelId}/tech-sheet/`, { headers })
      .then(r => r.ok ? r.json() : null)
      .then(data => { setSheet(data); setLoading(false) })
      .catch(() => setLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelId])

  if (loading) return (
    <div style={{ padding: '24px', color: 'var(--text-muted)',
      fontFamily: 'IBM Plex Mono, monospace', fontSize: '12px' }}>
      Carregant...
    </div>
  )

  // Estil compartit per botons outline discrets
  const btnOutline = {
    background: 'transparent',
    border: '1px solid var(--border)',
    color: 'var(--text-main)',
    fontFamily: 'IBM Plex Mono, monospace',
    fontSize: '11px',
    padding: '5px 12px',
    cursor: 'pointer',
  }

  // --- NO HI HA FITXA ---
  if (!sheet || !sheet.has_content) {
    return (
      <div style={{ padding: '24px',
        fontFamily: 'IBM Plex Mono, monospace' }}>
        <p style={{ color: 'var(--text-muted)', fontSize: '12px',
          marginBottom: '16px' }}>
          Encara no hi ha fitxa tècnica per a aquest model.
        </p>
        <button
          onClick={() => navigate(`/models/${modelId}/fitxa`)}
          style={{ ...btnOutline, borderColor: 'var(--gold)',
            color: 'var(--gold)' }}>
          Crear fitxa tècnica
        </button>
      </div>
    )
  }

  // --- HI HA FITXA ---
  // Nombre de pàgines (calculat al serializer; no enviem template_json sencer).
  const numPages = sheet.num_pages || '—'

  // Format data
  const updatedAt = sheet.updated_at
    ? new Date(sheet.updated_at).toLocaleDateString('ca-ES',
        { day:'2-digit', month:'2-digit', year:'numeric' })
    : '—'

  return (
    <div style={{ fontFamily: 'IBM Plex Mono, monospace' }}>

      {/* Barra superior: info + botons */}
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-muted)',
      }}>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)',
          display: 'flex', gap: '16px' }}>
          <span>v{sheet.versio}</span>
          <span>{sheet.estat}</span>
          <span>{numPages} pàgines</span>
          <span>Actualitzat: {updatedAt}</span>
          {sheet.locked_by_username && (
            <span style={{ color: 'var(--warn)' }}>
              Editant: {sheet.locked_by_username}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => navigate(`/models/${modelId}/fitxa`)}
            style={btnOutline}>
            Previsualitzar
          </button>
          <button
            onClick={() => navigate(`/models/${modelId}/fitxa`)}
            style={btnOutline}>
            Modificar
          </button>
        </div>
      </div>

      {/* Cos: resum de l'estat */}
      <div style={{ padding: '16px', fontSize: '12px',
        color: 'var(--text-muted)' }}>
        <p>
          La fitxa es pot editar des del Kanban (tasca
          <strong style={{ color: 'var(--text-main)' }}>
            {' '}Fitxa tècnica
          </strong>
          ) o des del botó Modificar.
          El PDF definitiu es generarà en congelar la fitxa.
        </p>
      </div>

    </div>
  )
}

function ModelSheetHeader({ model, onDelete, onFeedback, onChanged }) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  if (!model) return null

  return (
    <div style={{ borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)' }}>
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0.75rem 1.5rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button type="button" onClick={() => navigate('/models')}
          style={{ background: 'none', border: 'none', cursor: 'pointer',
                   fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                   fontFamily: 'IBM Plex Mono, monospace' }}>
          ← Models
        </button>
        <span style={{ color: 'var(--color-border-tertiary, #e0d5c5)' }}>›</span>
        <span style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                       fontFamily: 'monospace' }}>
          {model.codi_intern}
        </span>
        {model.codi_client && model.codi_client !== model.codi_intern && (
          <>
            <span style={{ color: 'var(--color-border-tertiary, #e0d5c5)' }}>·</span>
            <span style={{ fontSize: 13, fontFamily: 'monospace',
                           color: 'var(--color-text-primary, #1d1d1b)', fontWeight: 500 }}>
              {model.codi_client}
            </span>
          </>
        )}
        {model.nom_prenda && (
          <>
            <span style={{ color: 'var(--color-border-tertiary, #e0d5c5)' }}>·</span>
            <span style={{ fontSize: 15, fontWeight: 500,
                           color: 'var(--color-text-primary, #1d1d1b)' }}>
              {model.nom_prenda}
            </span>
          </>
        )}
        <span style={{
          fontSize: 11, padding: '2px 8px', borderRadius: 20, fontWeight: 500,
          background: 'var(--color-background-secondary, #f5f0ea)',
          color: 'var(--color-text-secondary, #868685)',
          border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
        }}>
          {model.estat}
        </span>
        <span style={{
          fontSize: 11, padding: '2px 8px', borderRadius: 20, fontWeight: 600,
          background: 'var(--gold)', color: '#fff',
        }} title={t('model_sheet.phase')}>
          {model.fase_actual}
        </span>
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <ActionsMenu model={model} onChanged={onChanged} onFeedback={onFeedback} />
        <button type="button"
          onClick={() => navigate(`/models/${model.id}/editar`)}
          style={btnSecondary}>
          <i className="ti ti-edit" aria-hidden="true" /> Editar
        </button>
        <button type="button" onClick={onDelete}
          style={{ ...btnSecondary, color: '#c5221f', borderColor: '#f5c6c6' }}>
          <i className="ti ti-trash" aria-hidden="true" /> Esborrar
        </button>
      </div>
    </div>
    </div>
  )
}

function TabSummary({ model, modelId, sizesAmbDades, onUpdated }) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    nom_prenda: model?.nom_prenda || '',
    codi_client: (model?.codi_client !== model?.codi_intern ? model?.codi_client : '') || '',
    descripcio: model?.descripcio || '',
  })
  const [saving, setSaving] = useState(false)
  const token = localStorage.getItem('access_token')

  const handleSave = async () => {
    setSaving(true)
    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          nom_prenda: form.nom_prenda,
          codi_client: form.codi_client || model.codi_intern,
          descripcio: form.descripcio,
        }),
      })
      if (r.ok) { setEditing(false); if (onUpdated) onUpdated() }
    } finally { setSaving(false) }
  }

  if (!model) return null

  const fmtDateTime = (v) => v ? new Date(v).toLocaleString('ca-ES', { dateStyle: 'medium', timeStyle: 'short' }) : '—'
  const readOnlyFields = [
    ['Referència interna', model.codi_intern],
    ['Temporada', `${model.temporada} ${model.any}`],
    ['Col·lecció', model.collection || '—'],
    ['Target', model.target || '—'],
    ['Tipus de peça', model.garment_type_nom || '—'],
    ['Model (peça)', model.garment_type_item_nom || '—'],
    ['Construcció', model.construction || '—'],
    ['Fit type', model.fit_type || '—'],
    ['Sistema de talles', model.size_system_nom || '—'],
    ['Talla base', model.base_size_label || '—'],
    ['Run de talles', (sizesAmbDades && sizesAmbDades.length
      ? sizesAmbDades.join('·')
      : model.size_run_model) || '—'],
    ['Grading', model.grading_rule_set ? '✓ Configurat' : '—'],
    ['Estat', model.estat],
    ['Creat per', model.created_by_nom || '—'],
    ['Creat el', fmtDateTime(model.created_at)],
    ...(model.fabric_main ? [
      ['Main Fabric', model.fabric_main],
      ['Composition', model.fabric_composition || '—'],
      ['Shrinkage', model.shrinkage_warp != null
        ? `Warp ${model.shrinkage_warp}% / Weft ${model.shrinkage_weft}% (${model.shrinkage_type})`
        : model.shrinkage_pct != null
          ? `${model.shrinkage_pct}% (${model.shrinkage_type})`
          : '—'],
    ] : []),
  ]

  return (
    <div style={{ maxWidth: 640 }}>
      {editing ? (
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                            display: 'block', marginBottom: 4 }}>
              Nom de la peça
            </label>
            <input value={form.nom_prenda}
              onChange={e => setForm(f => ({...f, nom_prenda: e.target.value}))}
              style={{ width: '100%', padding: '6px 10px', fontSize: 13,
                       border: '1px solid var(--color-border-tertiary, #e0d5c5)', borderRadius: 6 }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                            display: 'block', marginBottom: 4 }}>
              Referència client
            </label>
            <input value={form.codi_client}
              onChange={e => setForm(f => ({...f, codi_client: e.target.value}))}
              style={{ width: '100%', padding: '6px 10px', fontSize: 13,
                       border: '1px solid var(--color-border-tertiary, #e0d5c5)', borderRadius: 6 }} />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                            display: 'block', marginBottom: 4 }}>
              Descripció
            </label>
            <textarea value={form.descripcio}
              onChange={e => setForm(f => ({...f, descripcio: e.target.value}))}
              rows={3}
              style={{ width: '100%', padding: '6px 10px', fontSize: 13,
                       border: '1px solid var(--color-border-tertiary, #e0d5c5)', borderRadius: 6,
                       resize: 'vertical' }} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button type="button" onClick={handleSave} disabled={saving}
              style={{ padding: '6px 16px', background: 'var(--gold)', color: '#fff',
                       border: 'none', borderRadius: 6, fontSize: 13, cursor: 'pointer' }}>
              {saving ? 'Guardant...' : '✓ Guardar'}
            </button>
            <button type="button" onClick={() => setEditing(false)}
              style={{ padding: '6px 14px', background: 'transparent', fontSize: 13,
                       border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                       borderRadius: 6, cursor: 'pointer' }}>
              Cancel·lar
            </button>
          </div>
        </div>
      ) : (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between',
                        alignItems: 'flex-start', marginBottom: 12 }}>
            <div>
              <div style={{ fontSize: 18, fontWeight: 500 }}>
                {model.nom_prenda || <span style={{color:'var(--color-text-secondary, #868685)'}}>Sense nom</span>}
              </div>
              {model.codi_client && model.codi_client !== model.codi_intern && (
                <div style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                              fontFamily: 'monospace', marginTop: 2 }}>
                  {model.codi_client}
                </div>
              )}
              {model.descripcio && (
                <div style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                              marginTop: 6 }}>
                  {model.descripcio}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <tbody>
          {readOnlyFields.map(([label, value]) => (
            <tr key={label}
              style={{ borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)' }}>
              <td style={{ padding: '7px 0', color: 'var(--color-text-secondary, #868685)',
                           width: 180, fontSize: 12 }}>
                {label}
              </td>
              <td style={{ padding: '7px 0',
                           fontFamily: label === 'Referència interna' || label === 'Run de talles'
                             ? 'monospace' : undefined,
                           color: label === 'Referència interna'
                             ? 'var(--color-text-secondary, #868685)' : 'var(--color-text-primary, #1d1d1b)' }}>
                {value}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const TIPUS_CONFIG = {
  SKETCH_FLETXES: { label: 'Sketch amb fletxes', icon: 'ti-pencil',             color: '#c27a2a' },
  SKETCH_NET:     { label: 'Sketch net',         icon: 'ti-eye',                color: '#137333' },
  PATRO:          { label: 'Patró base',         icon: 'ti-vector-triangle',    color: '#185fa5' },
  MARCADA:        { label: 'Marcada',            icon: 'ti-layout',             color: '#7a4a10' },
  ESCALAT:        { label: 'Escalat',            icon: 'ti-arrows-maximize',    color: '#5f3dc4' },
  FITXA:          { label: 'Fitxa tècnica',      icon: 'ti-file-text',          color: '#333' },
  ALTRES:         { label: 'Altres',             icon: 'ti-file',               color: '#888' },
}

function TabFiles({ modelId }) {
  const token = localStorage.getItem('access_token')
  const authHeaders = { Authorization: `Bearer ${token}` }

  const [fitxers, setFitxers] = useState({})
  const [uploading, setUploading] = useState(null)
  const [popup, setPopup] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all(
      Object.keys(TIPUS_CONFIG).map(tipus =>
        fetch(`${API}/api/v1/model-fitxers/?model=${modelId}&tipus=${tipus}`, { headers: authHeaders })
          .then(r => r.json())
          .then(d => [tipus, d.results || d || []])
      )
    ).then(results => {
      const byType = {}
      results.forEach(([tipus, items]) => { byType[tipus] = items })
      setFitxers(byType)
    }).catch(() => setError('Error carregant fitxers'))
  }, [modelId])

  const handleUpload = async (tipus, file) => {
    setUploading(tipus)
    const formData = new FormData()
    formData.append('fitxer', file)
    formData.append('tipus', tipus)
    formData.append('nom', file.name)
    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/upload-fitxer/`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })
      const d = await r.json()
      if (r.ok) {
        setFitxers(prev => ({
          ...prev,
          [tipus]: [d, ...(prev[tipus] || [])],
        }))
      } else {
        setError(JSON.stringify(d))
      }
    } catch {
      setError('Error pujant el fitxer')
    } finally {
      setUploading(null)
    }
  }

  const handleDelete = async (fitxerId, tipus) => {
    if (!window.confirm('Eliminar aquest fitxer?')) return
    await fetch(`${API}/api/v1/model-fitxers/${fitxerId}/`, {
      method: 'DELETE', headers: authHeaders,
    })
    setFitxers(prev => ({
      ...prev,
      [tipus]: (prev[tipus] || []).filter(f => f.id !== fitxerId),
    }))
  }

  return (
    <div style={{ width: '100%', fontFamily: 'IBM Plex Mono, monospace' }}>
      {error && (
        <div style={{
          background: '#fee', border: '1px solid #fcc', borderRadius: 6,
          padding: '8px 12px', marginBottom: 12, fontSize: 13, color: '#c00',
        }}>{error}</div>
      )}

      {popup && (
        <div onClick={() => setPopup(null)}
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
          <div onClick={e => e.stopPropagation()}
            style={{ background: '#fff', borderRadius: 8, padding: 16,
                     maxWidth: '90vw', maxHeight: '90vh' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 500 }}>{popup.nom}</span>
              <button type="button" onClick={() => setPopup(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 18 }}>✕</button>
            </div>
            {popup.url?.match(/\.(jpg|jpeg|png|svg)$/i) ? (
              <img src={popup.url} alt={popup.nom}
                style={{ maxWidth: '80vw', maxHeight: '80vh', objectFit: 'contain' }} />
            ) : (
              <iframe src={popup.url} title={popup.nom}
                style={{ width: '80vw', height: '80vh', border: 'none' }} />
            )}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        {Object.entries(TIPUS_CONFIG).map(([tipus, config]) => (
          <div key={tipus}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
              <i className={`ti ${config.icon}`} aria-hidden="true"
                style={{ fontSize: 18, color: config.color }} />
              <span style={{ fontSize: 14, fontWeight: 500 }}>{config.label}</span>
              <span style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)' }}>
                ({(fitxers[tipus] || []).length})
              </span>
              <label style={{
                marginLeft: 'auto', padding: '4px 12px', fontSize: 12,
                border: '0.5px solid var(--color-border-tertiary, #e0d5c5)', borderRadius: 6,
                cursor: 'pointer', color: 'var(--color-text-secondary, #868685)',
                background: uploading === tipus ? 'var(--color-background-secondary, #f5f0ea)' : 'transparent',
              }}>
                {uploading === tipus ? 'Pujant...' : '+ Pujar'}
                <input type="file" style={{ display: 'none' }}
                  accept=".pdf,.png,.jpg,.jpeg,.svg,.dxf"
                  disabled={uploading === tipus}
                  onChange={e => e.target.files[0] && handleUpload(tipus, e.target.files[0])} />
              </label>
            </div>

            {(fitxers[tipus] || []).length === 0 ? (
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                            padding: '8px 0', fontStyle: 'italic' }}>
                Cap fitxer pujat.
              </div>
            ) : (
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {(fitxers[tipus] || []).map(f => (
                  <FileCard key={f.id} fitxer={f} config={config}
                    onPreview={() => setPopup({ url: f.fitxer || f.url, nom: f.nom_fitxer })}
                    onDelete={() => handleDelete(f.id, tipus)} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function FileCard({ fitxer, config, onPreview, onDelete }) {
  const isImage = fitxer.nom_fitxer?.match(/\.(jpg|jpeg|png|svg)$/i)

  return (
    <div style={{
      width: 140, border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
      borderRadius: 8, overflow: 'hidden', fontSize: 12,
      fontFamily: 'IBM Plex Mono, monospace',
    }}>
      <div onClick={onPreview}
        style={{
          height: 90, background: 'var(--color-background-secondary, #f5f0ea)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', position: 'relative',
        }}>
        {isImage && (fitxer.fitxer || fitxer.url) ? (
          <img src={fitxer.fitxer || fitxer.url} alt={fitxer.nom_fitxer}
            style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        ) : (
          <i className={`ti ${config.icon}`} aria-hidden="true"
            style={{ fontSize: 32, color: config.color }} />
        )}
        {fitxer.versio > 1 && (
          <span style={{
            position: 'absolute', top: 4, right: 4,
            background: 'rgba(0,0,0,0.6)', color: '#fff',
            fontSize: 10, padding: '1px 5px', borderRadius: 10,
          }}>
            v{fitxer.versio}
          </span>
        )}
      </div>

      <div style={{ padding: '6px 8px' }}>
        <div style={{
          fontSize: 11, color: 'var(--color-text-primary, #1d1d1b)',
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          marginBottom: 4,
        }} title={fitxer.nom_fitxer}>
          {fitxer.nom_fitxer}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button type="button" onClick={onPreview}
            style={{ flex: 1, padding: '3px 0', fontSize: 11, border: 'none',
                     background: 'var(--color-background-secondary, #f5f0ea)',
                     borderRadius: 4, cursor: 'pointer',
                     fontFamily: 'IBM Plex Mono, monospace' }}>
            <i className="ti ti-eye" aria-hidden="true" /> Veure
          </button>
          <button type="button" onClick={onDelete}
            style={{ padding: '3px 6px', fontSize: 11, border: 'none',
                     background: 'transparent', borderRadius: 4,
                     cursor: 'pointer', color: '#c5221f' }}>
            <i className="ti ti-trash" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  )
}

const GRAVETAT_STYLE = {
  CRITICA:     { bg: '#fce8e6', color: '#c5221f', border: '#f5c6c6' },
  IMPORTANT:   { bg: '#fff3e0', color: '#c8900a', border: '#f0c040' },
  INFORMATIVA: { bg: '#e6f4ea', color: '#137333', border: '#a8d5b5' },
}

function TabAIAnalysis({ modelId }) {
  const token = localStorage.getItem('access_token')
  const [analisi, setAnalisi] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleAnalyze = async () => {
    setLoading(true); setError(''); setAnalisi(null)
    try {
      const r = await fetch(`${API}/api/v1/models/${modelId}/analisi-ia/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({}),
      })
      const d = await r.json()
      if (r.ok) setAnalisi(d.analisi)
      else setError(d.error || 'Error desconegut')
    } catch {
      setError('Error de connexió')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 800, fontFamily: 'IBM Plex Mono, monospace' }}>
      <div style={{ marginBottom: 16 }}>
        <p style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)', marginBottom: 12 }}>
          Analitza els fitxers pujats (patrons, escalats, sketches) i detecta
          discrepàncies amb les mesures registrades.
          Disponible quan hi ha patrons o escalats pujats.
        </p>
        <button type="button" onClick={handleAnalyze} disabled={loading}
          style={{
            padding: '8px 20px', background: loading ? '#ccc' : 'var(--gold)',
            color: '#fff', border: 'none', borderRadius: 6,
            fontSize: 13, fontWeight: 500, cursor: loading ? 'not-allowed' : 'pointer',
            fontFamily: 'IBM Plex Mono, monospace',
          }}>
          {loading ? (
            <><i className="ti ti-loader" aria-hidden="true" /> Analitzant...</>
          ) : (
            <><i className="ti ti-cpu" aria-hidden="true" /> Llançar anàlisi IA</>
          )}
        </button>
      </div>

      {error && (
        <div style={{ background: '#fee', border: '1px solid #fcc', borderRadius: 6,
                      padding: '8px 12px', fontSize: 13, color: '#c00', marginBottom: 12 }}>
          {error}
        </div>
      )}

      {analisi && (
        <div>
          <div style={{ fontSize: 13, color: 'var(--color-text-secondary, #868685)',
                        marginBottom: 12 }}>
            {analisi.resum}
            {' · '}{analisi.fitxers_analitzats} fitxer(s) analitzat(s)
          </div>

          {(analisi.alertes || []).length === 0 ? (
            <div style={{ fontSize: 13, color: '#137333', padding: '12px 0' }}>
              ✓ Cap discrepància detectada.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {analisi.alertes.map((alerta, i) => {
                const style = GRAVETAT_STYLE[alerta.gravetat] || GRAVETAT_STYLE.INFORMATIVA
                return (
                  <div key={i} style={{
                    background: style.bg, border: `1px solid ${style.border}`,
                    borderRadius: 8, padding: '12px 14px',
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8,
                                  marginBottom: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 500, color: style.color,
                                     padding: '1px 8px', background: 'rgba(255,255,255,0.6)',
                                     borderRadius: 20 }}>
                        {alerta.gravetat}
                      </span>
                      <span style={{ fontSize: 11, color: style.color }}>
                        {alerta.tipus?.replace(/_/g, ' ')}
                      </span>
                      {alerta.pom_afectat && (
                        <span style={{ fontFamily: 'monospace', fontSize: 12,
                                       color: style.color, fontWeight: 500 }}>
                          {alerta.pom_afectat}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--color-text-primary, #1d1d1b)',
                                  marginBottom: 6 }}>
                      {alerta.descripcio}
                    </div>
                    {(alerta.valor_taula || alerta.valor_patro) && (
                      <div style={{ fontSize: 12, color: style.color, marginBottom: 4 }}>
                        Taula: {alerta.valor_taula || '—'} → Patró: {alerta.valor_patro || '—'}
                      </div>
                    )}
                    <div style={{ fontSize: 12, color: 'var(--color-text-secondary, #868685)',
                                  fontStyle: 'italic' }}>
                      → {alerta.accio_suggerida}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

