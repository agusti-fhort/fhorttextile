import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../../store/auth'
import i18n from '../../i18n'

const API = import.meta.env.VITE_API_URL || ''

// TODO(backend): Only GET /api/v1/models/{id}/base-measurements/ exists.
// Missing POST/PATCH/DELETE for inline editing and BaseMeasurement CRUD.
// The current BaseMeasurement model does NOT have `nom_fitxa` or `origen` fields;
// the spec mentions them but they are optional — the UI shows them if present.
// An endpoint for the model's GradedSpec is also missing (the Grading view shows '—'
// fins que existeixi). Mentrestant: optimistic update local + fallback a mock.

const ORIGEN_LABELS = {
  STANDARD:   { label: 'Estàndard', fg: 'var(--text-muted)', bg: '#f5f0ea',  border: 'var(--border)' },
  IMPORTED:   { label: 'Importat',  fg: '#2a5a8a', bg: '#eef4fc',  border: '#c5d8ee' },
  MANUAL:     { label: 'Manual',    fg: 'var(--gold)', bg: '#fdf6ee',  border: '#e0c8a0' },
  FITTED:     { label: 'Fitting',   fg: '#6a3a9a', bg: '#f3edfb',  border: '#d8c5ee' },
  CALCULATED: { label: 'Calculat',  fg: '#3b6d11', bg: '#f0f9f0',  border: '#c0dd97' },
}

const MOCK_MEASUREMENTS = [
  { id: 'mock-1', pom_id: 90, pom_code: 'POM-001', pom_name_en: 'Chest width',       pom_nom: 'Ample de pit',    pom_abbreviation: 'CH',    pom_is_key: true,  nom_fitxa: 'A', base_value_cm: 88.0, origen: 'STANDARD', notes: '' },
  { id: 'mock-2', pom_id: 92, pom_code: 'POM-003', pom_name_en: 'Waist width',       pom_nom: 'Ample de cintura',pom_abbreviation: 'WA',    pom_is_key: true,  nom_fitxa: 'B', base_value_cm: 72.0, origen: 'STANDARD', notes: '' },
  { id: 'mock-3', pom_id: 93, pom_code: 'POM-004', pom_name_en: 'Hip width',         pom_nom: 'Ample de maluc',  pom_abbreviation: 'HI',    pom_is_key: true,  nom_fitxa: 'C', base_value_cm: 94.0, origen: 'MANUAL',   notes: '' },
  { id: 'mock-4', pom_id: 109,pom_code: 'POM-009', pom_name_en: 'Body length',       pom_nom: 'Llarg cos',       pom_abbreviation: 'BL',    pom_is_key: true,  nom_fitxa: 'D', base_value_cm: 62.0, origen: 'STANDARD', notes: '' },
  { id: 'mock-5', pom_id: 120,pom_code: 'POM-020', pom_name_en: 'Sleeve length',     pom_nom: 'Llarg màniga',    pom_abbreviation: 'SL',    pom_is_key: false, nom_fitxa: 'E', base_value_cm: 58.0, origen: 'CALCULATED', notes: '' },
]

function normalizeMeasurement(m) {
  return {
    id: m.id,
    pom_id: m.pom_id,
    pom_code: m.pom_code || m.codi_client || '',
    pom_name_en: m.pom_name_en || m.nom_client || '',
    pom_nom: m.pom_nom || m.nom_ca || m.nom_client || '',
    pom_abbreviation: m.pom_abbreviation || '',
    pom_is_key: !!m.pom_is_key,
    pom_category: m.pom_category || m.categoria_nom || '',
    nom_fitxa: m.nom_fitxa || '',
    base_value_cm: m.base_value_cm,
    origen: m.origen || 'STANDARD',
    notes: m.notes || '',
  }
}

// Detect inconsistencies between BaseMeasurements (patternmaking heuristics).
function checkCoherence(measurements) {
  const alerts = []
  const byCode = {}
  measurements.forEach(m => { byCode[m.pom_code] = m.base_value_cm })

  if (byCode['POM-001'] != null && byCode['POM-003'] != null) {
    const diff = byCode['POM-001'] - byCode['POM-003']
    if (diff < 2) {
      alerts.push({
        tipus: 'WARN',
        missatge: i18n.t('measurement_table.coherence.chest_waist', { chest: byCode['POM-001'], waist: byCode['POM-003'], diff: diff.toFixed(1) }),
      })
    }
  }
  if (byCode['POM-055'] != null && byCode['POM-056'] != null) {
    if (byCode['POM-056'] <= byCode['POM-055']) {
      alerts.push({
        tipus: 'ERROR',
        missatge: i18n.t('measurement_table.coherence.back_front_rise', { back: byCode['POM-056'], front: byCode['POM-055'] }),
      })
    }
  }
  if (byCode['POM-020'] != null && byCode['POM-022'] != null) {
    if (byCode['POM-022'] <= byCode['POM-020']) {
      alerts.push({
        tipus: 'WARN',
        missatge: i18n.t('measurement_table.coherence.sleeve_cb', { cb: byCode['POM-022'], base: byCode['POM-020'] }),
      })
    }
  }
  return alerts
}

export default function MeasurementTable({
  modelId,
  sizeRun = [],
  baseSize = '',
  mode: initialMode = 'base',
  readOnly = false,
  onAlert = () => {},
}) {
  const { t } = useTranslation()
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')

  const [mode, setMode] = useState(initialMode)
  const [measurements, setMeasurements] = useState([])
  const [loading, setLoading] = useState(false)
  const [usingMock, setUsingMock] = useState(false)
  const [editingCell, setEditingCell] = useState(null)
  const [msg, setMsg] = useState(null)

  useEffect(() => { setMode(initialMode) }, [initialMode])

  useEffect(() => {
    if (!modelId) { setMeasurements([]); return }
    setLoading(true)
    fetch(`${API}/api/v1/models/${modelId}/base-measurements/`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => {
        const raw = data.results || data || []
        if (Array.isArray(raw) && raw.length > 0) {
          setMeasurements(raw.map(normalizeMeasurement))
          setUsingMock(false)
        } else {
          // Backend retorna llista buida → no usem mock; deixem buit
          setMeasurements([])
          setUsingMock(false)
        }
      })
      .catch(() => {
        setMeasurements(MOCK_MEASUREMENTS.map(normalizeMeasurement))
        setUsingMock(true)
      })
      .finally(() => setLoading(false))
  }, [modelId, token])

  const alerts = useMemo(() => checkCoherence(measurements), [measurements])
  useEffect(() => { alerts.forEach(a => onAlert(a)) }, [alerts])

  // GradedSpec: there is no public endpoint for the Model yet.
  // TODO(backend): exposar GET /api/v1/models/{id}/graded-specs/ (o similar).
  // Mentrestant gradedSpecs queda buit i la vista Grading mostra '—'.
  const gradedSpecs = {}

  const updateLocal = (id, patch) => {
    setMeasurements(prev => prev.map(m => m.id === id ? { ...m, ...patch } : m))
  }

  const handleEdit = async (id, field, rawValue) => {
    const value = field === 'base_value_cm' ? parseFloat(rawValue) : rawValue
    if (field === 'base_value_cm' && Number.isNaN(value)) {
      setEditingCell(null); return
    }

    updateLocal(id, { [field]: value })
    setEditingCell(null)

    // TODO(backend): endpoint PATCH /api/v1/base-measurements/{id}/ no existeix.
    // Try it — if it returns 404/405, we keep only the local edit and warn.
    if (String(id).startsWith('mock-')) return
    try {
      const res = await fetch(`${API}/api/v1/base-measurements/${id}/`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: value }),
      })
      if (!res.ok && (res.status === 404 || res.status === 405)) {
        setMsg({ type: 'warn', text: t('measurement_table.msg.edit_not_persisted') })
      } else if (!res.ok) {
        setMsg({ type: 'error', text: t('measurement_table.msg.save_error', { status: res.status }) })
      }
    } catch {
      setMsg({ type: 'warn', text: t('measurement_table.msg.edit_local') })
    }
  }

  const handleDelete = async (id) => {
    if (readOnly) return
    if (!confirm(t('measurement_table.confirm_delete'))) return
    setMeasurements(prev => prev.filter(m => m.id !== id))

    if (String(id).startsWith('mock-')) return
    try {
      const res = await fetch(`${API}/api/v1/base-measurements/${id}/`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok && (res.status === 404 || res.status === 405)) {
        setMsg({ type: 'warn', text: t('measurement_table.msg.delete_not_persisted') })
      } else if (!res.ok) {
        setMsg({ type: 'error', text: t('measurement_table.msg.delete_error', { status: res.status }) })
      }
    } catch {
      setMsg({ type: 'warn', text: t('measurement_table.msg.delete_local') })
    }
  }

  if (loading) {
    return <div style={{ padding: 16, fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>{t('measurement_table.loading')}</div>
  }

  return (
    <div style={{ }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: 10, padding: '10px 0', flexWrap: 'wrap',
      }}>
        <ViewToggle mode={mode} onChange={setMode} />
        {usingMock && (
          <span style={{
            fontSize: 'var(--fs-label)', color: 'var(--gold)',
            background: '#fdf6ee', border: '0.5px solid #e0c8a0',
            padding: '3px 8px', borderRadius: 4,
          }}>
            {t('measurement_table.mock_badge')}
          </span>
        )}
        {!readOnly && (
          <button
            onClick={() => setMsg({ type: 'info', text: t('measurement_table.todo_add_pom') })}
            style={btnPrimary}
          >{t('measurement_table.add_pom')}</button>
        )}
      </div>

      {/* Banner alertes */}
      {alerts.length > 0 && (
        <div style={{
          margin: '4px 0 12px',
          border: '0.5px solid',
          borderColor: alerts.some(a => a.tipus === 'ERROR') ? '#f09595' : '#e0c8a0',
          borderRadius: 6,
          background: alerts.some(a => a.tipus === 'ERROR') ? '#fff0f0' : '#fdf6ee',
          padding: '8px 12px',
        }}>
          {alerts.map((a, i) => (
            <div key={i} style={{
              fontSize: 'var(--fs-body)',
              color: a.tipus === 'ERROR' ? '#a32d2d' : 'var(--gold)',
              padding: '2px 0',
            }}>
              <span style={{ fontWeight: 600, marginRight: 6 }}>{a.tipus}</span>
              {a.missatge}
            </div>
          ))}
        </div>
      )}

      {/* Missatge transitori */}
      {msg && (
        <div style={{
          margin: '4px 0 12px',
          padding: '6px 10px', borderRadius: 6, fontSize: 'var(--fs-body)',
          background: msg.type === 'info' ? '#fdf6ee' : msg.type === 'warn' ? '#fdf6ee' : '#fff0f0',
          border: `0.5px solid ${msg.type === 'error' ? '#f09595' : '#e0c8a0'}`,
          color: msg.type === 'error' ? '#a32d2d' : 'var(--gold)',
          display: 'flex', justifyContent: 'space-between',
        }}>
          <span>{msg.text}</span>
          <button onClick={() => setMsg(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 'var(--fs-h3)' }}>×</button>
        </div>
      )}

      {/* Taula */}
      <div style={{ overflow: 'auto', border: '0.5px solid var(--border)', borderRadius: 6 }}>
        {mode === 'base' ? (
          <BaseView
            measurements={measurements}
            readOnly={readOnly}
            editingCell={editingCell}
            setEditingCell={setEditingCell}
            onEdit={handleEdit}
            onDelete={handleDelete}
          />
        ) : (
          <GradingView
            measurements={measurements}
            gradedSpecs={gradedSpecs}
            sizeRun={sizeRun}
            baseSize={baseSize}
          />
        )}
      </div>

      {measurements.length === 0 && !loading && (
        <div style={{
          padding: '14px',
          fontSize: 'var(--fs-body)', color: 'var(--text-muted)',
          textAlign: 'center',
        }}>
          {t('measurement_table.empty')}
        </div>
      )}
    </div>
  )
}

// ── Vista BASE ──────────────────────────────────────────────────────────────
function BaseView({ measurements, readOnly, editingCell, setEditingCell, onEdit, onDelete }) {
  const { t } = useTranslation()
  return (
    <table style={tableStyle}>
      <thead>
        <tr>
          <Th width={70}>{t('measurement_table.col.sheet_name')}</Th>
          <Th>POM</Th>
          <Th width={80}>{t('measurement_table.col.code')}</Th>
          <Th width={100} align="right">{t('measurement_table.col.base_value')}</Th>
          <Th width={90}>{t('measurement_table.col.origin')}</Th>
          <Th>{t('measurement_table.col.notes')}</Th>
          {!readOnly && <Th width={28} />}
        </tr>
      </thead>
      <tbody>
        {measurements.map(m => {
          const origen = ORIGEN_LABELS[m.origen] || ORIGEN_LABELS.STANDARD
          return (
            <tr key={m.id}>
              <Td>
                <EditableCell
                  value={m.nom_fitxa || m.pom_abbreviation || ''}
                  editing={editingCell?.id === m.id && editingCell?.field === 'nom_fitxa'}
                  readOnly={readOnly}
                  onStartEdit={() => setEditingCell({ id: m.id, field: 'nom_fitxa' })}
                  onSave={(v) => onEdit(m.id, 'nom_fitxa', v)}
                  onCancel={() => setEditingCell(null)}
                  mono
                />
              </Td>
              <Td>
                <span style={{ fontWeight: 500, color: 'var(--charcoal, #1d1d1b)' }}>
                  {m.pom_name_en || m.pom_nom || '—'}
                </span>
                {m.pom_is_key && (
                  <span style={{
                    marginLeft: 6, fontSize: 'var(--fs-caption)', padding: '1px 5px', borderRadius: 3,
                    background: '#fdf6ee', color: 'var(--gold)',
                    border: '0.5px solid #e0c8a0', fontWeight: 600, letterSpacing: '.05em',
                  }}>KEY</span>
                )}
              </Td>
              <Td mono>{m.pom_code || '—'}</Td>
              <Td align="right">
                <EditableCell
                  value={m.base_value_cm != null ? Number(m.base_value_cm).toFixed(1) : ''}
                  editing={editingCell?.id === m.id && editingCell?.field === 'base_value_cm'}
                  readOnly={readOnly}
                  onStartEdit={() => setEditingCell({ id: m.id, field: 'base_value_cm' })}
                  onSave={(v) => onEdit(m.id, 'base_value_cm', v)}
                  onCancel={() => setEditingCell(null)}
                  suffix=" cm"
                  type="number"
                  align="right"
                />
              </Td>
              <Td>
                <span style={{
                  fontSize: 'var(--fs-caption)', padding: '2px 6px', borderRadius: 3,
                  background: origen.bg, color: origen.fg,
                  border: `0.5px solid ${origen.border}`,
                  fontWeight: 600, letterSpacing: '.05em',
                }}>{t(`measurement_table.origen.${m.origen}`, origen.label)}</span>
              </Td>
              <Td><span style={{ color: 'var(--text-muted)' }}>{m.notes || '—'}</span></Td>
              {!readOnly && (
                <Td align="center">
                  <button
                    onClick={() => onDelete(m.id)}
                    title={t('app.delete')}
                    style={{
                      background: 'none', border: 'none', cursor: 'pointer',
                      color: '#c0c0c0', fontSize: 'var(--fs-h3)', lineHeight: 1, padding: '2px 4px',
                    }}
                    onMouseEnter={e => e.currentTarget.style.color = '#a32d2d'}
                    onMouseLeave={e => e.currentTarget.style.color = '#c0c0c0'}
                  >×</button>
                </Td>
              )}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

// ── Vista GRADING ───────────────────────────────────────────────────────────
function GradingView({ measurements, gradedSpecs, sizeRun, baseSize }) {
  const { t } = useTranslation()
  if (!sizeRun.length) {
    return (
      <div style={{ padding: 16, fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
        {t('measurement_table.grading_empty')}
      </div>
    )
  }

  // Compute the delta between sizes for a POM
  const calcDelta = (pomId) => {
    const vals = sizeRun.map(s => gradedSpecs[pomId]?.[s])
    const deltas = []
    for (let i = 1; i < vals.length; i++) {
      if (vals[i] != null && vals[i - 1] != null) {
        deltas.push((parseFloat(vals[i]) - parseFloat(vals[i - 1])).toFixed(1))
      }
    }
    const unique = [...new Set(deltas)]
    if (unique.length === 0) return '—'
    if (unique.length === 1) return `+${unique[0]}`
    return unique.map(d => `+${d}`).join('/')
  }

  return (
    <table style={tableStyle}>
      <thead>
        <tr>
          <Th width={70}>{t('measurement_table.col.name')}</Th>
          <Th>POM</Th>
          {sizeRun.map(s => {
            const isBase = s === baseSize
            return (
              <Th key={s} align="right" width={64}
                style={{
                  background: isBase ? '#fdf6ee' : undefined,
                  color: isBase ? 'var(--gold)' : undefined,
                }}>
                {s}{isBase ? ' ●' : ''}
              </Th>
            )
          })}
          <Th align="right" width={80}>{t('measurement_table.col.delta_per_size')}</Th>
        </tr>
      </thead>
      <tbody>
        {measurements.map(m => (
          <tr key={m.id}>
            <Td mono>{m.nom_fitxa || m.pom_abbreviation || '—'}</Td>
            <Td>
              <span style={{ fontWeight: 500 }}>{m.pom_name_en || m.pom_nom || '—'}</span>
            </Td>
            {sizeRun.map(s => {
              const val = gradedSpecs[m.pom_id]?.[s]
              const isBase = s === baseSize
              return (
                <Td key={s} align="right" mono
                  style={{
                    background: isBase ? '#fdf6ee' : undefined,
                    color: isBase && val != null ? 'var(--gold)' : undefined,
                    fontWeight: isBase ? 600 : 400,
                  }}>
                  {val != null ? Number(val).toFixed(1) : '—'}
                </Td>
              )
            })}
            <Td align="right" mono>
              <span style={{ color: '#3b6d11' }}>{calcDelta(m.pom_id)}</span>
            </Td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// ── EditableCell ────────────────────────────────────────────────────────────
function EditableCell({ value, editing, readOnly, onStartEdit, onSave, onCancel, suffix = '', type = 'text', align = 'left', mono }) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState(value)
  useEffect(() => { setDraft(value) }, [value])

  if (editing) {
    return (
      <input
        autoFocus
        type={type}
        step={type === 'number' ? '0.1' : undefined}
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={() => onSave(draft)}
        onKeyDown={e => {
          if (e.key === 'Enter') onSave(draft)
          if (e.key === 'Escape') onCancel ? onCancel() : onSave(value)
        }}
        style={{
          width: '100%',
          background: 'var(--white)',
          border: '0.5px solid var(--gold)',
          borderRadius: 3,
          padding: '2px 6px',
          fontSize: 'var(--fs-body)',
          textAlign: align,
          outline: 'none',
        }}
      />
    )
  }

  const display = (value === '' || value == null) ? '—' : `${value}${suffix}`
  return (
    <span
      onClick={readOnly ? undefined : onStartEdit}
      title={readOnly ? '' : t('measurement_table.click_to_edit')}
      style={{
        display: 'inline-block',
        padding: '2px 6px',
        borderRadius: 3,
        cursor: readOnly ? 'default' : 'pointer',
        textAlign: align,
        fontFamily: mono ? 'IBM Plex Mono, monospace' : 'inherit',
        fontSize: mono ? 11 : 12,
        color: value === '' || value == null ? 'var(--text-muted)' : 'inherit',
      }}
      onMouseEnter={e => { if (!readOnly) e.currentTarget.style.background = '#fdf9f5' }}
      onMouseLeave={e => { if (!readOnly) e.currentTarget.style.background = 'transparent' }}
    >
      {display}
    </span>
  )
}

// ── ViewToggle ──────────────────────────────────────────────────────────────
function ViewToggle({ mode, onChange }) {
  const { t } = useTranslation()
  return (
    <div style={{ display: 'inline-flex', border: '0.5px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
      {[
        { v: 'base',    label: t('measurement_table.view.base') },
        { v: 'grading', label: t('measurement_table.view.grading') },
      ].map(({ v, label }) => {
        const active = mode === v
        return (
          <button
            key={v}
            onClick={() => onChange(v)}
            style={{
              padding: '6px 14px',
              background: active ? 'var(--gold)' : 'var(--white)',
              color: active ? 'var(--white)' : 'var(--text-muted)',
              border: 'none', cursor: 'pointer',
              fontSize: 'var(--fs-body)', 
              fontWeight: active ? 600 : 400,
            }}
          >
            {label}
          </button>
        )
      })}
    </div>
  )
}

// ── Components auxiliars de taula ──────────────────────────────────────────
function Th({ children, width, align = 'left', style }) {
  return (
    <th style={{
      padding: '8px 10px',
      fontSize: 'var(--fs-label)', letterSpacing: '0.08em',
      textTransform: 'uppercase',
      color: 'var(--text-muted)',
      fontWeight: 600, 
      borderBottom: '0.5px solid var(--border)',
      background: '#fafaf8',
      textAlign: align, width, whiteSpace: 'nowrap',
      ...style,
    }}>{children}</th>
  )
}

function Td({ children, align = 'left', mono, style }) {
  return (
    <td style={{
      padding: '6px 10px',
      fontSize: mono ? 11 : 12,
      fontFamily: mono ? 'IBM Plex Mono, monospace' : 'inherit',
      borderBottom: '0.5px solid #f0eee9',
      textAlign: align, whiteSpace: 'nowrap',
      ...style,
    }}>{children}</td>
  )
}

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
  background: 'var(--white)',
}

const btnPrimary = {
  padding: '6px 14px',
  borderRadius: 6,
  background: 'var(--gold)',
  color: 'var(--white)',
  border: 'none',
  cursor: 'pointer',
  fontSize: 'var(--fs-body)', 
  fontWeight: 600,
}
