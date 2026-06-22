import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors,
} from '@dnd-kit/core'
import {
  SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy,
  useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { poms, garmentPomMaps, itemBaseMeasurements } from '../../api/endpoints'

// MeasurementBaseGrid — graella de mesures BASE de la plantilla d'un Item (Sprint Llibreria
// d'Items, B1). Component NOU i autònom: reutilitza el PATRÓ d'EditableTable (dnd-kit + cel·la
// editable + alta de POM en línia) però SENSE el bloc de grading (cap sizeRun, cap Δ, cap graded).
// Columnes: [drag · # · nom_fitxa · descripció · valor base · tol− · tol+ · ✕].
// Escriu a la capa Item: GarmentPOMMap (pertinença + ordre) + ItemBaseMeasurement (valor/tol/nom).

const thS = {
  padding: '6px 10px', textAlign: 'left', fontSize: 'var(--fs-body)',
  fontWeight: 500, whiteSpace: 'nowrap', borderBottom: '1px solid var(--border)',
}
const tdS = { padding: '4px 10px', verticalAlign: 'middle', fontSize: 'var(--fs-body)' }
const btnPrimary = (disabled) => ({
  background: disabled ? '#ccc' : 'var(--gold)', color: 'var(--white)',
  border: 'none', borderRadius: 6, padding: '7px 18px',
  fontSize: 'var(--fs-body)', fontWeight: 500, cursor: disabled ? 'not-allowed' : 'pointer',
})
const btnSecondary = {
  background: 'transparent', color: 'var(--text-muted)',
  border: '0.5px solid var(--border)',
  borderRadius: 6, padding: '7px 14px', fontSize: 'var(--fs-body)', cursor: 'pointer',
}

const numOrNull = (v) => {
  if (v === '' || v == null) return null
  const n = parseFloat(v)
  return Number.isNaN(n) ? null : n
}

export default function MeasurementBaseGrid({ garmentTypeItemId, readOnly = false, onSaved }) {
  const { t } = useTranslation()
  const [rows, setRows] = useState([])
  const [removed, setRemoved] = useState([])   // {mapId, ibmId} de files esborrades (pendents de persistir)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    if (!garmentTypeItemId) return
    setLoading(true); setError(null)
    try {
      const [mapsRes, valsRes] = await Promise.all([
        garmentPomMaps.list({ garment_type_item: garmentTypeItemId, ordering: 'ordre', page_size: 500 }),
        itemBaseMeasurements.list({ garment_type_item: garmentTypeItemId, page_size: 500 }),
      ])
      const maps = mapsRes.data.results || mapsRes.data || []
      const vals = valsRes.data.results || valsRes.data || []
      const valByPom = {}
      vals.forEach(v => { valByPom[v.pom] = v })
      const merged = maps
        .slice()
        .sort((a, b) => (a.ordre ?? 0) - (b.ordre ?? 0))
        .map((m, i) => {
          const v = valByPom[m.pom] || {}
          return {
            id: `map-${m.id}`,
            mapId: m.id,
            ibmId: v.id ?? null,
            pom_id: m.pom,
            pom_code: m.pom_code || '',
            descripcio: m.name_cat || m.name_en || '',
            is_key: m.is_key,
            nom_fitxa: v.nom_fitxa ?? '',
            base_value_cm: v.base_value_cm ?? null,
            tol_minus: v.tol_minus ?? null,
            tol_plus: v.tol_plus ?? null,
            ordre: m.ordre ?? i,
          }
        })
      setRows(merged); setRemoved([]); setDirty(false)
    } catch (e) {
      console.error('Error carregant la graella d\'item', e)
      setError(t('measurement_base_grid.load_error'))
    } finally {
      setLoading(false)
    }
  }, [garmentTypeItemId, t])

  useEffect(() => { load() }, [load])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const handleDragEnd = (event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    setRows(prev => {
      const oldIdx = prev.findIndex(r => r.id === active.id)
      const newIdx = prev.findIndex(r => r.id === over.id)
      if (oldIdx < 0 || newIdx < 0) return prev
      return arrayMove(prev, oldIdx, newIdx).map((r, i) => ({ ...r, ordre: i }))
    })
    setDirty(true)
  }

  const handleCellChange = (rowId, col, value) => {
    setRows(prev => prev.map(r => {
      if (r.id !== rowId) return r
      if (col === 'nom_fitxa') return { ...r, nom_fitxa: value }
      return { ...r, [col]: numOrNull(value) }
    }))
    setDirty(true)
  }

  const handleDeleteRow = (rowId) => {
    setRows(prev => {
      const row = prev.find(r => r.id === rowId)
      if (row && (row.mapId || row.ibmId)) {
        setRemoved(rm => [...rm, { mapId: row.mapId, ibmId: row.ibmId }])
      }
      return prev.filter(r => r.id !== rowId).map((r, i) => ({ ...r, ordre: i }))
    })
    setDirty(true)
  }

  const handleAddRow = (pom) => {
    setRows(prev => {
      if (prev.some(r => r.pom_id === pom.id)) return prev   // ja hi és: no duplicar
      return [...prev, {
        id: `tmp-${pom.id}-${prev.length}`,
        mapId: null, ibmId: null,
        pom_id: pom.id,
        pom_code: pom.codi_client || '',
        descripcio: pom.nom_client || pom.nom_ca || pom.nom_en || '',
        is_key: false,
        nom_fitxa: '', base_value_cm: null, tol_minus: null, tol_plus: null,
        ordre: prev.length,
      }]
    })
    setDirty(true)
  }

  const handleSave = async () => {
    setSaving(true); setError(null)
    try {
      // 1) Esborrats: primer el valor (ItemBaseMeasurement), després la pertinença (GarmentPOMMap).
      for (const r of removed) {
        if (r.ibmId) await itemBaseMeasurements.remove(r.ibmId)
        if (r.mapId) await garmentPomMaps.remove(r.mapId)
      }
      // 2) Files actuals: assegurar pertinença + ordre, i upsert del valor.
      for (const r of rows) {
        if (!r.mapId) {
          await garmentPomMaps.create({
            garment_type_item: garmentTypeItemId, pom: r.pom_id, ordre: r.ordre,
          })
        } else {
          await garmentPomMaps.update(r.mapId, { ordre: r.ordre })
        }
        await itemBaseMeasurements.upsert({
          garment_type_item: garmentTypeItemId,
          pom: r.pom_id,
          base_value_cm: r.base_value_cm,
          tol_minus: r.tol_minus,
          tol_plus: r.tol_plus,
          nom_fitxa: r.nom_fitxa || '',
        })
      }
      await load()
      if (onSaved) onSaved()
    } catch (e) {
      console.error('Error desant la graella d\'item', e)
      setError(t('measurement_base_grid.save_error'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div style={{ padding: 16, color: 'var(--text-muted)' }}>{t('common.loading')}</div>
  }

  const colCount = (readOnly ? 0 : 1) + 6 + (readOnly ? 0 : 1)

  return (
    <div>
      {error && (
        <div style={{
          background: '#fdecea', border: '1px solid #f5c6cb', borderRadius: 8,
          padding: '8px 14px', marginBottom: 12, fontSize: 'var(--fs-body)', color: '#a12622',
        }}>
          {error}
        </div>
      )}

      <div style={{ overflowX: 'auto', width: '100%' }}>
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--fs-body)' }}>
            <thead>
              <tr style={{ background: 'var(--bg-muted)', borderBottom: '1px solid var(--border)' }}>
                {!readOnly && <th style={thS}></th>}
                <th style={thS}>#</th>
                <th style={thS}>{t('measurement_base_grid.col.sheet_name')}</th>
                <th style={{ ...thS, minWidth: 200 }}>{t('measurement_base_grid.col.description')}</th>
                <th style={{ ...thS, textAlign: 'right', minWidth: 90 }}>
                  {t('measurement_base_grid.col.base_value')}
                </th>
                <th style={{ ...thS, textAlign: 'right', minWidth: 70 }}>
                  {t('measurement_base_grid.col.tol_minus')}
                </th>
                <th style={{ ...thS, textAlign: 'right', minWidth: 70 }}>
                  {t('measurement_base_grid.col.tol_plus')}
                </th>
                {!readOnly && <th style={thS}></th>}
              </tr>
            </thead>
            <SortableContext items={rows.map(r => r.id)} strategy={verticalListSortingStrategy}>
              <tbody>
                {rows.map(row => (
                  <SortableRow
                    key={row.id}
                    row={row}
                    readOnly={readOnly}
                    onCellChange={handleCellChange}
                    onDelete={handleDeleteRow}
                  />
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={colCount} style={{
                      padding: '18px 12px', textAlign: 'center', color: 'var(--text-muted)',
                    }}>
                      {t('measurement_base_grid.empty')}
                    </td>
                  </tr>
                )}
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
          <button type="button" onClick={load} style={btnSecondary}>
            ↩ {t('measurement_base_grid.discard')}
          </button>
          <button type="button" onClick={handleSave} disabled={saving} style={btnPrimary(saving)}>
            {saving ? t('common.saving') : `✓ ${t('measurement_base_grid.save')}`}
          </button>
        </div>
      )}
    </div>
  )
}

function SortableRow({ row, readOnly, onCellChange, onDelete }) {
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

  return (
    <tr ref={setNodeRef} style={style}>
      {!readOnly && (
        <td style={tdS}>
          <span {...attributes} {...listeners}
            style={{ cursor: 'grab', color: 'var(--text-muted)', fontSize: 'var(--fs-h3)' }}
            aria-label={t('measurement_base_grid.drag_handle')}>
            ⠿
          </span>
        </td>
      )}
      <td style={{ ...tdS, color: 'var(--text-muted)' }}>{(row.ordre ?? 0) + 1}</td>
      <td style={tdS}>
        <EditableCell value={row.nom_fitxa}
          onChange={v => onCellChange(row.id, 'nom_fitxa', v)}
          mono gold readOnly={readOnly} />
      </td>
      <td style={{ ...tdS, color: 'var(--text-muted)' }}>
        <span style={{ color: 'var(--gold)', marginRight: 8 }}>{row.pom_code}</span>
        {row.descripcio}
        {row.is_key && (
          <span style={{
            marginLeft: 5, fontSize: 'var(--fs-caption)', padding: '1px 4px', borderRadius: 3,
            background: '#fdf6ee', color: 'var(--gold)', border: '0.5px solid #e0c8a0',
            fontWeight: 600, letterSpacing: '.06em', verticalAlign: 'middle',
          }}>KEY</span>
        )}
      </td>
      <td style={{ ...tdS, textAlign: 'right' }}>
        <EditableCell value={row.base_value_cm}
          onChange={v => onCellChange(row.id, 'base_value_cm', v)} numeric mono right readOnly={readOnly} />
      </td>
      <td style={{ ...tdS, textAlign: 'right' }}>
        <EditableCell value={row.tol_minus}
          onChange={v => onCellChange(row.id, 'tol_minus', v)} numeric mono right readOnly={readOnly} />
      </td>
      <td style={{ ...tdS, textAlign: 'right' }}>
        <EditableCell value={row.tol_plus}
          onChange={v => onCellChange(row.id, 'tol_plus', v)} numeric mono right readOnly={readOnly} />
      </td>
      {!readOnly && (
        <td style={tdS}>
          <button type="button" onClick={() => onDelete(row.id)}
            style={{ background: 'none', border: 'none', cursor: 'pointer',
                     color: 'var(--text-muted)', fontSize: 'var(--fs-h3)', padding: '2px 4px' }}
            title={t('measurement_base_grid.delete_row')}>
            ✕
          </button>
        </td>
      )}
    </tr>
  )
}

function EditableCell({ value, onChange, mono, gold, right, numeric, readOnly }) {
  const { t } = useTranslation()
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(value ?? '')

  useEffect(() => { setVal(value ?? '') }, [value])

  if (readOnly || !editing) {
    const display = (val !== '' && val != null) ? val
      : <span style={{ color: 'var(--text-muted)' }}>—</span>
    return (
      <span
        onClick={() => !readOnly && setEditing(true)}
        tabIndex={readOnly ? undefined : 0}
        onKeyDown={e => { if (!readOnly && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); setEditing(true) } }}
        role={readOnly ? undefined : 'button'}
        aria-label={readOnly ? undefined : t('measurement_base_grid.edit_cell')}
        style={{
          display: 'block', cursor: readOnly ? 'default' : 'pointer',
          fontFamily: mono ? 'monospace' : undefined,
          color: gold ? 'var(--gold)' : undefined,
          textAlign: right ? 'right' : undefined,
          minWidth: 30, padding: '1px 2px',
          borderBottom: readOnly ? 'none' : '1px dashed transparent',
          outlineOffset: 2,
        }}
        onFocus={e => { if (!readOnly) e.currentTarget.style.borderBottomColor = 'var(--border)' }}
        onBlur={e => { e.currentTarget.style.borderBottomColor = 'transparent' }}
        onMouseEnter={e => { if (!readOnly) e.currentTarget.style.borderBottomColor = 'var(--border)' }}
        onMouseLeave={e => { e.currentTarget.style.borderBottomColor = 'transparent' }}>
        {display}
      </span>
    )
  }

  return (
    <input
      autoFocus
      type={numeric ? 'number' : 'text'}
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
        width: mono ? 70 : '100%', padding: '1px 4px',
        border: '1px solid var(--gold)', borderRadius: 3,
        fontSize: 'var(--fs-body)', fontFamily: mono ? 'monospace' : undefined,
        textAlign: right ? 'right' : undefined, background: '#fdf6ee',
      }}
    />
  )
}

function AddPOMInline({ onAdd }) {
  const { t } = useTranslation()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (query.length < 2) { setResults([]); return }
    const timer = setTimeout(async () => {
      try {
        const r = await poms.cerca({ q: query, page_size: 10 })
        setResults(r.data.results || r.data || [])
      } catch {
        setResults([])
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [query])

  const handleCreatePOM = async (nom) => {
    try {
      const r = await poms.crearTenant({
        nom_client: nom,
        codi_client: nom.toUpperCase().replace(/\s+/g, '_').slice(0, 20),
        actiu: true,
        pendent_revisio: true,
      })
      onAdd({ id: r.data.id, codi_client: r.data.codi_client, nom_client: r.data.nom_client })
      setQuery(''); setResults([]); setOpen(false)
    } catch (e) {
      console.error('Error creant POM', e)
    }
  }

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}
        style={{ background: 'none', border: 'none', cursor: 'pointer',
                 fontSize: 'var(--fs-body)', color: 'var(--gold)', padding: '4px 0' }}>
        <i className="ti ti-plus" /> {t('measurement_base_grid.add_pom')}
      </button>
    )
  }

  return (
    <div style={{ position: 'relative', display: 'flex', gap: 8, alignItems: 'flex-start', flexWrap: 'wrap' }}>
      <input
        autoFocus
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder={t('measurement_base_grid.search_placeholder')}
        style={{ padding: '4px 8px', border: '1px solid var(--border)',
                 borderRadius: 4, fontSize: 'var(--fs-body)', width: 220 }}
      />
      {(results.length > 0 || query.length >= 2) && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4,
          background: 'var(--bg-main)', border: '0.5px solid var(--border)', borderRadius: 6,
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)', zIndex: 100, minWidth: 280,
        }}>
          {results.map(p => (
            <div key={p.id}
              onClick={() => { onAdd(p); setQuery(''); setResults([]); setOpen(false) }}
              style={{ padding: '6px 12px', cursor: 'pointer', fontSize: 'var(--fs-body)',
                       borderBottom: '0.5px solid var(--border)' }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-muted)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <span style={{ color: 'var(--gold)', marginRight: 8 }}>{p.codi_client}</span>
              {p.nom_client || p.nom_ca || p.nom_en}
            </div>
          ))}
          {query.length >= 2 && results.length === 0 && (
            <div style={{ padding: '8px 12px', fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }}>
              {t('measurement_base_grid.no_pom_found', { query })}{' '}
              <button type="button" onClick={() => handleCreatePOM(query)}
                style={{ background: 'none', border: 'none', cursor: 'pointer',
                         color: 'var(--gold)', fontSize: 'var(--fs-body)', padding: 0 }}>
                + {t('measurement_base_grid.create_pom', { query })}
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
