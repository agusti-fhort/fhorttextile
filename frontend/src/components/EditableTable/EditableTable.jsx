import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors,
} from '@dnd-kit/core'
import {
  SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy,
  useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

const thS = {
  padding: '6px 10px', textAlign: 'left', fontSize: 'var(--fs-body)',
  fontWeight: 500, whiteSpace: 'nowrap',
  borderBottom: '1px solid var(--border)',
}
const tdS = { padding: '4px 10px', verticalAlign: 'middle', fontSize: 'var(--fs-body)' }
const btnPrimary = (disabled) => ({
  background: disabled ? 'var(--bg-muted)' : 'var(--gold)', color: disabled ? 'var(--text-muted)' : 'var(--white)',
  border: 'none', borderRadius: 6, padding: '7px 18px',
  fontSize: 'var(--fs-body)', fontWeight: 500, cursor: disabled ? 'not-allowed' : 'pointer',
})
const btnSecondary = {
  background: 'transparent', color: 'var(--text-muted)',
  border: '0.5px solid var(--border)',
  borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', cursor: 'pointer',
}

export default function EditableTable({
  rows,
  sizeRun,
  baseSize,
  deltes,
  modelId,
  isImport = false,
  readOnly = false,
  saveLabel,
  onPomSave,
  onSaved,
}) {
  const { t } = useTranslation()
  const [localRows, setLocalRows] = useState(rows)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  useEffect(() => { setLocalRows(rows); setDirty(false) }, [rows])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleDragEnd = (event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    setLocalRows(prev => {
      const oldIdx = prev.findIndex(r => r.id === active.id)
      const newIdx = prev.findIndex(r => r.id === over.id)
      if (oldIdx < 0 || newIdx < 0) return prev
      return arrayMove(prev, oldIdx, newIdx).map((r, i) => ({ ...r, ordre: i }))
    })
    setDirty(true)
  }

  const handleCellChange = (rowId, col, value) => {
    setLocalRows(prev => prev.map(r => {
      if (r.id !== rowId) return r
      if (col.startsWith('graded.')) {
        const size = col.split('.')[1]
        return { ...r, graded: { ...r.graded, [size]: parseFloat(value) || 0 } }
      }
      if (col.includes('value')) return { ...r, [col]: parseFloat(value) || 0 }
      return { ...r, [col]: value }
    }))
    setDirty(true)
  }

  const handleDeleteRow = (rowId) => {
    setLocalRows(prev => prev.filter(r => r.id !== rowId).map((r, i) => ({ ...r, ordre: i })))
    setDirty(true)
  }

  const handleAddRow = (pom) => {
    const newRow = {
      id: `tmp-${Date.now()}`,
      pom_id: pom.id,
      pom_code: pom.codi_client,
      nom_ca: pom.nom_ca || pom.nom_client || '',
      nom_en: pom.nom_en || pom.nom_client || '',
      nom_fitxa: '',
      base_value_cm: null,
      graded: {},
      ordre: localRows.length,
    }
    setLocalRows(prev => [...prev, newRow])
    setDirty(true)
  }

  const calcDelta = (row) => {
    // Δ computed on the backend (mean of increments between sizes with data).
    if (deltes) {
      const d = deltes[row.pom_id]
      return d == null ? '—' : `±${d}`
    }
    // Local fallback (table without backend deltas, e.g. new unsaved rows).
    if (!sizeRun || sizeRun.length < 2) return '—'
    const valOf = (s) => s === baseSize ? row.base_value_cm : row.graded?.[s]
    const first = valOf(sizeRun[0])
    const last = valOf(sizeRun[sizeRun.length - 1])
    if (first == null || last == null) return '—'
    return (last - first).toFixed(1)
  }

  const buildPayload = () => {
    const measurements = localRows
      .filter(r => r.base_value_cm != null && r.base_value_cm !== '')
      .map(r => ({
        pom_id: r.pom_id,
        base_value_cm: r.base_value_cm,
        notes: r.notes || '',
        nom_fitxa: r.nom_fitxa || '',
      }))
    const keep_pom_ids = localRows.map(r => r.pom_id).filter(Boolean)
    const rules = localRows
      .filter(r => r.pom_id)
      .map(r => ({
        pom_id: r.pom_id,
        logica: r.logica || 'LINEAR',
        increment_base: r.increment_base ?? null,
        increment_break: r.increment_break ?? null,
        talla_break_label: r.talla_break_label || null,
      }))
    return { measurements, keep_pom_ids, rules }
  }

  const handleSave = async () => {
    setSaving(true)
    const token = localStorage.getItem('access_token')
    const API = import.meta.env.VITE_API_URL || ''
    const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

    try {
      const payload = buildPayload()

      if (onPomSave) {
        await onPomSave(payload)
        setDirty(false)
        if (onSaved) onSaved(localRows)
        return
      }

      await fetch(`${API}/api/v1/models/${modelId}/set-measurements/`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify(payload),
      })

      const order = localRows.map(r => r.id).filter(id => id && !String(id).startsWith('tmp-'))
      if (order.length > 0) {
        await fetch(`${API}/api/v1/models/${modelId}/reorder-measurements/`, {
          method: 'POST', headers: authHeaders,
          body: JSON.stringify({ order }),
        })
      }

      setDirty(false)
      if (onSaved) onSaved(localRows)
    } catch (e) {
      console.error('Error guardant', e)
    } finally {
      setSaving(false)
    }
  }

  const displaySize = baseSize || sizeRun?.[0]
  const colCount = (readOnly ? 0 : 2) + 7
  const stickyHd = (left, w) => ({ ...thS, position: 'sticky', left, zIndex: 3, width: w, minWidth: w, background: 'var(--bg-muted)' })

  return (
    <div>
      {isImport && (
        <div style={{
          background: 'var(--warn-bg)', border: '1px solid var(--warn)',
          borderRadius: 8, padding: '10px 16px', marginBottom: 12,
          fontSize: 'var(--fs-body)', display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <i className="ti ti-alert-triangle" style={{ color: 'var(--warn)', fontSize: 16 }} />
          <span>
            <strong>{t('editable_table.import_title')}</strong>{' '}
            {t('editable_table.import_hint')}
          </span>
        </div>
      )}

      <div style={{ overflowX: 'auto', width: '100%' }}>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <table style={{ borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
            <thead>
              <tr style={{
                background: 'var(--bg-muted)',
                borderBottom: '1px solid var(--border)',
              }}>
                {!readOnly && <th style={thS}></th>}
                <th style={thS}>#</th>
                <th style={stickyHd(0, 90)}>{t('measuregrid.col_pom')}</th>
                <th style={stickyHd(90, 190)}>{t('measuregrid.col_nom')}</th>
                <th style={{ ...thS, textAlign: 'right', minWidth: 90, background: 'var(--gold-pale)' }}>
                  {displaySize || t('editable_table.col.base_value')}
                </th>
                <th style={{ ...thS, minWidth: 92 }}>{t('editable_table.col.regime')}</th>
                <th style={{ ...thS, textAlign: 'right', minWidth: 82 }}>{t('editable_table.col.delta')}</th>
                <th style={{ ...thS, textAlign: 'right', minWidth: 82 }}>{t('editable_table.col.break_delta')}</th>
                <th style={{ ...thS, minWidth: 100 }}>{t('editable_table.col.break_size')}</th>
                {!readOnly && <th style={thS}></th>}
              </tr>
            </thead>
            <SortableContext items={localRows.map(r => r.id)} strategy={verticalListSortingStrategy}>
              <tbody>
                {localRows.map(row => (
                  <SortableRow
                    key={row.id}
                    row={row}
                    displaySize={displaySize}
                    readOnly={readOnly}
                    onCellChange={handleCellChange}
                    onDelete={handleDeleteRow}
                    delta={calcDelta(row)}
                  />
                ))}
              </tbody>
            </SortableContext>
            {!readOnly && (
              <tfoot>
                <tr>
                  <td colSpan={colCount} style={{ padding: '8px 12px' }}>
                    <AddPOMInline onAdd={handleAddRow} />
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </DndContext>
      </div>

      {!readOnly && (dirty || onPomSave) && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 12 }}>
          {dirty && (
            <button type="button" onClick={() => { setLocalRows(rows); setDirty(false) }}
              style={btnSecondary}>
              <i className="ti ti-arrow-back-up" /> {t('editable_table.discard')}
            </button>
          )}
          <button type="button" onClick={handleSave} disabled={saving}
            style={btnPrimary(saving)}>
            {saving ? t('common.saving') : saveLabel || t('editable_table.confirm_table')}
          </button>
        </div>
      )}
    </div>
  )
}

function SortableRow({ row, displaySize, readOnly, onCellChange, onDelete, delta }) {
  const { t } = useTranslation()
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: row.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    background: isDragging ? 'var(--bg-muted)' : undefined,
    borderBottom: '0.5px solid var(--border)',
  }

  const rowBg = isDragging ? 'var(--bg-muted)' : 'var(--white)'
  const stickyTd = (left, w) => ({
    ...tdS, position: 'sticky', left, zIndex: 1, width: w, minWidth: w,
    background: rowBg, borderBottom: '0.5px solid var(--border)',
  })

  return (
    <tr ref={setNodeRef} style={style}>
      {!readOnly && (
        <td style={tdS}>
          <span {...attributes} {...listeners}
            style={{ cursor: 'grab', color: 'var(--text-muted)', fontSize: 'var(--fs-h3)' }}>
            ⠿
          </span>
        </td>
      )}
      <td style={{ ...tdS, color: 'var(--text-muted)' }}>{(row.ordre ?? 0) + 1}</td>
      <td style={stickyTd(0, 90)}>
        <EditableCell value={row.nom_fitxa || row.pom_code}
          onChange={v => onCellChange(row.id, 'nom_fitxa', v)}
          mono gold readOnly={readOnly} />
        {row.is_key && (
          <i className="ti ti-star" title="KEY"
            style={{ fontSize: 9, marginLeft: 5, color: 'var(--gold)', verticalAlign: 'middle' }} />
        )}
      </td>
      <td style={stickyTd(90, 190)}>
        <div style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)', whiteSpace: 'normal' }}>
          {row.nom_en || row.nom_ca || row.pom_code}
        </div>
        {(row.nom_ca && row.nom_ca !== row.nom_en) && (
          <div style={{ fontSize: 'var(--fs-caption)', fontStyle: 'italic', color: 'var(--text-muted)', whiteSpace: 'normal' }}>
            {row.nom_ca}
          </div>
        )}
      </td>
      <td style={{ ...tdS, textAlign: 'right', background: 'var(--gold-pale)' }}>
        <EditableCell
          value={row.base_value_cm}
          onChange={v => onCellChange(row.id, 'base_value_cm', v)}
          mono right readOnly={readOnly} />
      </td>
      <td style={tdS}>
        {row.logica && !['LINEAR', 'STEP'].includes(row.logica) ? (
          // FIXED/ZERO/EXCEPTION: règim de regla de catàleg, NO editable a mà aquí → mostra el valor
          // REAL com a etiqueta (mai emmascarat com a LINEAR). El payload el reenvia tal qual.
          <span title={t('editable_table.regime_locked_hint')}
            style={{ fontSize: 'inherit', color: 'var(--text-muted)' }}>
            {row.logica}
          </span>
        ) : (
          <select
            value={row.logica || 'LINEAR'}
            disabled={readOnly}
            onChange={e => onCellChange(row.id, 'logica', e.target.value)}
            style={{
              font: 'inherit', border: '1px solid var(--border)', borderRadius: 4,
              padding: '2px 4px', background: readOnly ? 'transparent' : 'var(--white)',
              color: 'var(--text-main)',
            }}
          >
            <option value="LINEAR">LINEAR</option>
            <option value="STEP">STEP</option>
          </select>
        )}
      </td>
      <td style={{ ...tdS, textAlign: 'right' }}>
        <EditableCell value={row.increment_base ?? ''}
          onChange={v => onCellChange(row.id, 'increment_base', v)}
          mono right readOnly={readOnly} />
      </td>
      <td style={{ ...tdS, textAlign: 'right' }}>
        <EditableCell value={row.increment_break}
          onChange={v => onCellChange(row.id, 'increment_break', v)}
          mono right readOnly={readOnly} />
      </td>
      <td style={tdS}>
        <EditableCell value={row.talla_break_label || ''}
          onChange={v => onCellChange(row.id, 'talla_break_label', v)}
          readOnly={readOnly} />
      </td>
      {!readOnly && (
        <td style={tdS}>
          <button type="button" onClick={() => onDelete(row.id)}
            style={{ background: 'none', border: 'none', cursor: 'pointer',
                     color: 'var(--text-muted)', fontSize: 'var(--fs-h3)', padding: '2px 4px' }}
            title={t('editable_table.delete_row')}>
            <i className="ti ti-x" />
          </button>
        </td>
      )}
    </tr>
  )
}

function EditableCell({ value, onChange, mono, gold, right, readOnly }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value ?? '')

  useEffect(() => { setVal(value ?? '') }, [value])

  if (readOnly || !editing) {
    const display = (val !== '' && val != null) ? val
      : <span style={{ color: 'var(--text-muted)' }}>—</span>
    return (
      <span
        onClick={() => !readOnly && setEditing(true)}
        style={{
          display: 'block', cursor: readOnly ? 'default' : 'pointer',
          fontFamily: mono ? 'monospace' : undefined,
          color: gold ? 'var(--gold)' : undefined,
          textAlign: right ? 'right' : undefined,
          minWidth: 30, padding: '1px 2px',
          borderBottom: readOnly ? 'none' : '1px dashed transparent',
        }}
        onMouseEnter={e => { if (!readOnly) e.currentTarget.style.borderBottomColor = 'var(--border)' }}
        onMouseLeave={e => { e.currentTarget.style.borderBottomColor = 'transparent' }}>
        {display}
      </span>
    )
  }

  return (
    <input
      autoFocus
      type={typeof value === 'number' ? 'number' : 'text'}
      inputMode={typeof value === 'number' ? 'decimal' : undefined}
      step="0.1"
      value={val}
      onChange={e => setVal(e.target.value)}
      onBlur={() => { onChange(val); setEditing(false) }}
      onKeyDown={e => {
        if (e.key === 'Enter') { onChange(val); setEditing(false) }
        if (e.key === 'Escape') { setVal(value ?? ''); setEditing(false) }
        if (e.key === 'Tab') { onChange(val); setEditing(false) }
      }}
      style={{
        width: mono ? 60 : '100%', padding: '1px 4px',
        border: '1px solid var(--gold)', borderRadius: 3,
        fontSize: 'var(--fs-body)', fontFamily: mono ? 'monospace' : undefined,
        textAlign: right ? 'right' : undefined,
        background: 'var(--gold-pale)',
      }}
    />
  )
}

function AddPOMInline({ onAdd }) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const token = localStorage.getItem('access_token')
  const API = import.meta.env.VITE_API_URL || ''

  useEffect(() => {
    if (query.length < 2) { setResults([]); return }
    const timer = setTimeout(async () => {
      try {
        const r = await fetch(
          `${API}/api/v1/poms/cerca/?q=${encodeURIComponent(query)}&page_size=10`,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        const d = await r.json()
        setResults(d.results || d || [])
      } catch {
        setResults([])
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  const handleCreatePOM = async (nom) => {
    try {
      const r = await fetch(`${API}/api/v1/poms/crear-tenant/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          nom_client: nom,
          codi_client: nom.toUpperCase().replace(/\s+/g, '_').slice(0, 20),
          actiu: true,
          pendent_revisio: true,
        }),
      })
      const d = await r.json()
      if (r.ok) {
        onAdd({ id: d.id, codi_client: d.codi_client, nom_client: d.nom_client })
        setQuery(''); setResults([]); setOpen(false)
      }
    } catch (e) {
      console.error('Error creant POM', e)
    }
  }

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}
        style={{ background: 'none', border: 'none', cursor: 'pointer',
                 fontSize: 'var(--fs-body)', color: 'var(--gold)', padding: '4px 0',
                 }}>
        <i className="ti ti-plus" /> {t('editable_table.add_pom')}
      </button>
    )
  }

  return (
    <div style={{ position: 'relative', display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
      <input
        autoFocus
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder={t('editable_table.search_placeholder')}
        style={{ padding: '4px 8px', border: '1px solid var(--border)',
                 borderRadius: 4, fontSize: 'var(--fs-body)', width: 220,
                 }}
      />
      {(results.length > 0 || query.length >= 2) && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4,
          background: 'var(--bg-main)',
          border: '0.5px solid var(--border)', borderRadius: 6,
          zIndex: 100, minWidth: 280,
        }}>
          {results.map(p => (
            <div key={p.id}
              onClick={() => { onAdd(p); setQuery(''); setResults([]); setOpen(false) }}
              style={{ padding: '6px 12px', cursor: 'pointer', fontSize: 'var(--fs-body)',
                       borderBottom: '0.5px solid var(--border)',
                       }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-muted)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <span style={{ color: 'var(--gold)', marginRight: 8 }}>
                {p.codi_client}
              </span>
              {p.nom_client || p.nom_ca || p.nom_en}
            </div>
          ))}
          {query.length >= 2 && results.length === 0 && (
            <div style={{
              padding: '8px 12px', fontSize: 'var(--fs-body)',
              color: 'var(--text-muted)',
            }}>
              {t('editable_table.no_pom_found', { query })}{' '}
              <button type="button"
                onClick={() => handleCreatePOM(query)}
                style={{ background: 'none', border: 'none', cursor: 'pointer',
                         color: 'var(--gold)', fontSize: 'var(--fs-body)', padding: 0,
                         }}>
                + {t('editable_table.create_pom', { query })}
              </button>
            </div>
          )}
        </div>
      )}
      <button type="button" onClick={() => { setOpen(false); setQuery('') }}
        style={{ background: 'none', border: 'none', cursor: 'pointer',
                 fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
        ✕
      </button>
    </div>
  )
}
