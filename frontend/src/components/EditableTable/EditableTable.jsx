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
  padding: '6px 10px', textAlign: 'left', fontSize: 11,
  fontWeight: 500, whiteSpace: 'nowrap',
  borderBottom: '1px solid var(--color-border-tertiary, #e0d5c5)',
}
const tdS = { padding: '4px 10px', verticalAlign: 'middle', fontSize: 12 }
const btnPrimary = (disabled) => ({
  background: disabled ? '#ccc' : 'var(--gold)', color: 'var(--white)',
  border: 'none', borderRadius: 6, padding: '7px 18px',
  fontSize: 13, fontWeight: 500, cursor: disabled ? 'not-allowed' : 'pointer',
})
const btnSecondary = {
  background: 'transparent', color: 'var(--color-text-secondary, #868685)',
  border: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
  borderRadius: 6, padding: '7px 14px', fontSize: 13, cursor: 'pointer',
}

export default function EditableTable({
  rows,
  sizeRun,
  baseSize,
  deltes,
  modelId,
  isImport = false,
  readOnly = false,
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

  const handleSave = async () => {
    setSaving(true)
    const token = localStorage.getItem('access_token')
    const API = import.meta.env.VITE_API_URL || ''
    const authHeaders = { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }

    try {
      const measurements = localRows
        .filter(r => r.base_value_cm != null)
        .map(r => ({
          pom_id: r.pom_id,
          base_value_cm: r.base_value_cm,
          notes: r.notes || '',
          nom_fitxa: r.nom_fitxa || '',
        }))

      // keep_pom_ids = TOTS els POMs que segueixen a la taula (amb valor o buits/TEMPLATE). El
      // backend desactiva (is_active=False) els que NO hi siguin → persisteix la X d'eliminar fila.
      const keep_pom_ids = localRows.map(r => r.pom_id).filter(Boolean)

      await fetch(`${API}/api/v1/models/${modelId}/set-measurements/`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ measurements, keep_pom_ids }),
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

  const colCount = (readOnly ? 0 : 2) + 4 + sizeRun.length + 1

  return (
    <div>
      {isImport && (
        <div style={{
          background: '#fff9e6', border: '1px solid #f0c040',
          borderRadius: 8, padding: '10px 16px', marginBottom: 12,
          fontSize: 13, display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <i className="ti ti-alert-triangle" style={{ color: '#c8900a', fontSize: 16 }} />
          <span>
            <strong>{t('editable_table.import_title')}</strong>{' '}
            {t('editable_table.import_hint')}
          </span>
        </div>
      )}

      <div style={{ overflowX: 'auto', width: '100%' }}>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <table style={{
            width: '100%', borderCollapse: 'collapse',
            fontSize: 12, 
          }}>
            <thead>
              <tr style={{
                background: 'var(--color-background-secondary, #f5f0ea)',
                borderBottom: '1px solid var(--color-border-tertiary, #e0d5c5)',
              }}>
                {!readOnly && <th style={thS}></th>}
                <th style={thS}>#</th>
                <th style={thS}>{t('editable_table.col.sheet_name')}</th>
                <th style={thS}>POM</th>
                <th style={{ ...thS, minWidth: 200 }}>{t('editable_table.col.description')}</th>
                {sizeRun.map(s => (
                  <th key={s} style={{
                    ...thS, textAlign: 'right', minWidth: 60,
                    background: s === baseSize ? '#fdf6ee' : undefined,
                    color: s === baseSize ? '#7a4a10' : undefined,
                  }}>
                    {s}{s === baseSize ? ' ★' : ''}
                  </th>
                ))}
                <th style={{ ...thS, textAlign: 'right', color: 'var(--color-text-secondary, #868685)' }}>Δ</th>
                {!readOnly && <th style={thS}></th>}
              </tr>
            </thead>
            <SortableContext items={localRows.map(r => r.id)} strategy={verticalListSortingStrategy}>
              <tbody>
                {localRows.map(row => (
                  <SortableRow
                    key={row.id}
                    row={row}
                    sizeRun={sizeRun}
                    baseSize={baseSize}
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

      {!readOnly && dirty && (
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 12 }}>
          <button type="button" onClick={() => { setLocalRows(rows); setDirty(false) }}
            style={btnSecondary}>
            ↩ {t('editable_table.discard')}
          </button>
          <button type="button" onClick={handleSave} disabled={saving}
            style={btnPrimary(saving)}>
            {saving ? t('common.saving') : `✓ ${t('editable_table.confirm_table')}`}
          </button>
        </div>
      )}
    </div>
  )
}

function SortableRow({ row, sizeRun, baseSize, readOnly, onCellChange, onDelete, delta }) {
  const { t } = useTranslation()
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: row.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    background: isDragging ? 'var(--color-background-secondary, #f5f0ea)' : undefined,
    borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
  }

  return (
    <tr ref={setNodeRef} style={style}>
      {!readOnly && (
        <td style={tdS}>
          <span {...attributes} {...listeners}
            style={{ cursor: 'grab', color: 'var(--color-text-secondary, #868685)', fontSize: 16 }}>
            ⠿
          </span>
        </td>
      )}
      <td style={{ ...tdS, color: 'var(--color-text-secondary, #868685)' }}>{(row.ordre ?? 0) + 1}</td>
      <td style={tdS}>
        <EditableCell value={row.nom_fitxa}
          onChange={v => onCellChange(row.id, 'nom_fitxa', v)}
          mono gold readOnly={readOnly} />
      </td>
      <td style={{ ...tdS, fontSize: 11,
                   color: 'var(--color-text-secondary, #868685)' }}>
        {row.pom_code}
        {row.is_key && (
          <span style={{
            marginLeft: 5, fontSize: 8, padding: '1px 4px', borderRadius: 3,
            background: '#fdf6ee', color: 'var(--gold)', border: '0.5px solid #e0c8a0',
            fontWeight: 600, letterSpacing: '.06em', verticalAlign: 'middle',
          }}>KEY</span>
        )}
      </td>
      <td style={tdS}>
        <EditableCell value={row.nom_ca || row.nom_en}
          onChange={v => onCellChange(row.id, 'nom_ca', v)} readOnly={readOnly} />
      </td>
      {sizeRun.map(s => (
        <td key={s} style={{
          ...tdS, textAlign: 'right',
          background: s === baseSize ? '#fefaf5' : undefined,
        }}>
          <EditableCell
            value={s === baseSize ? row.base_value_cm : row.graded?.[s]}
            onChange={v => onCellChange(row.id, s === baseSize ? 'base_value_cm' : `graded.${s}`, v)}
            mono right readOnly={readOnly} />
        </td>
      ))}
      <td style={{ ...tdS, textAlign: 'right', 
                   color: 'var(--color-text-secondary, #868685)', fontSize: 11 }}>
        {delta}
      </td>
      {!readOnly && (
        <td style={tdS}>
          <button type="button" onClick={() => onDelete(row.id)}
            style={{ background: 'none', border: 'none', cursor: 'pointer',
                     color: 'var(--color-text-secondary, #868685)', fontSize: 14, padding: '2px 4px' }}
            title={t('editable_table.delete_row')}>
            ✕
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
      : <span style={{ color: 'var(--color-text-secondary, #868685)' }}>—</span>
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
        onMouseEnter={e => { if (!readOnly) e.currentTarget.style.borderBottomColor = 'var(--color-border-tertiary, #e0d5c5)' }}
        onMouseLeave={e => { e.currentTarget.style.borderBottomColor = 'transparent' }}>
        {display}
      </span>
    )
  }

  return (
    <input
      autoFocus
      type={typeof value === 'number' ? 'number' : 'text'}
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
        fontSize: 12, fontFamily: mono ? 'monospace' : undefined,
        textAlign: right ? 'right' : undefined,
        background: '#fdf6ee',
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
                 fontSize: 12, color: 'var(--gold)', padding: '4px 0',
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
        style={{ padding: '4px 8px', border: '1px solid var(--color-border-tertiary, #e0d5c5)',
                 borderRadius: 4, fontSize: 12, width: 220,
                 }}
      />
      {(results.length > 0 || query.length >= 2) && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4,
          background: 'var(--color-background-primary, #fff)',
          border: '0.5px solid var(--color-border-tertiary, #e0d5c5)', borderRadius: 6,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)', zIndex: 100, minWidth: 280,
        }}>
          {results.map(p => (
            <div key={p.id}
              onClick={() => { onAdd(p); setQuery(''); setResults([]); setOpen(false) }}
              style={{ padding: '6px 12px', cursor: 'pointer', fontSize: 12,
                       borderBottom: '0.5px solid var(--color-border-tertiary, #e0d5c5)',
                       }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--color-background-secondary, #f5f0ea)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <span style={{ color: 'var(--gold)', marginRight: 8 }}>
                {p.codi_client}
              </span>
              {p.nom_client || p.nom_ca || p.nom_en}
            </div>
          ))}
          {query.length >= 2 && results.length === 0 && (
            <div style={{
              padding: '8px 12px', fontSize: 12,
              color: 'var(--color-text-secondary, #868685)',
            }}>
              {t('editable_table.no_pom_found', { query })}{' '}
              <button type="button"
                onClick={() => handleCreatePOM(query)}
                style={{ background: 'none', border: 'none', cursor: 'pointer',
                         color: 'var(--gold)', fontSize: 12, padding: 0,
                         }}>
                + {t('editable_table.create_pom', { query })}
              </button>
            </div>
          )}
        </div>
      )}
      <button type="button" onClick={() => { setOpen(false); setQuery('') }}
        style={{ background: 'none', border: 'none', cursor: 'pointer',
                 fontSize: 12, color: 'var(--color-text-secondary, #868685)' }}>
        ✕
      </button>
    </div>
  )
}
