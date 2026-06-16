import { useState, useEffect } from 'react'
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors,
} from '@dnd-kit/core'
import {
  SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy,
  useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import useAuthStore from '../../store/auth'
import GarmentTypeSelector from '../GarmentTypeSelector/GarmentTypeSelector'

const API = import.meta.env.VITE_API_URL || ''

function gtName(t, lang = 'ca') {
  if (!t) return ''
  if (lang === 'ca') return t.nom_ca || t.nom_cat || t.nom_en || t.nom_client || t.global_nom || ''
  if (lang === 'es') return t.nom_es || t.nom_en || t.nom_client || t.global_nom || ''
  return t.nom_en || t.nom_client || t.global_nom || ''
}

function grupLabel(grup, lang = 'ca') {
  const MAP = {
    TOPS: { ca: 'Parts superiors', en: 'Tops', es: 'Partes superiores' },
    BOTTOMS: { ca: 'Parts inferiors', en: 'Bottoms', es: 'Partes inferiores' },
    DRESSES: { ca: 'Vestits', en: 'Dresses', es: 'Vestidos' },
    OUTERWEAR: { ca: 'Abrics', en: 'Outerwear', es: 'Abrigos' },
    UNDERWEAR: { ca: 'Interior', en: 'Underwear', es: 'Interior' },
    SWIMWEAR: { ca: 'Bany', en: 'Swimwear', es: 'Baño' },
    ACCESSORIES: { ca: 'Complements', en: 'Accessories', es: 'Complementos' },
  }
  return MAP[grup]?.[lang] || grup
}

// Normalitza la resposta de /api/v1/garment-pom-maps/?garment_type_item=<id> (GarmentPOMMapSerializer,
// camps flat) al format de la UI. Cada entrada porta el seu map_id (id de GarmentPOMMap) i pom_id per
// poder fer DELETE/POST. Llista buida → [] (estat buit real; SENSE mock).
function normalizePOMs(raw) {
  if (!Array.isArray(raw)) return []

  return raw.map(entry => {
    const isKeyFromMap = typeof entry.is_key === 'boolean' ? entry.is_key : undefined
    const pomSource = (entry.pom && typeof entry.pom === 'object') ? entry.pom : entry
    const pg = pomSource.pom_global || pomSource

    return {
      // Identificadors per a assign (POST/DELETE):
      map_id: entry.id,                                   // id de GarmentPOMMap (per DELETE)
      pom_id: typeof entry.pom === 'number' ? entry.pom : (pomSource.id ?? null),  // per POST
      pendent_revisio: !!entry.pendent_revisio,           // badge "revisar" als clons
      ordre: entry.ordre,
      pom_code: pg.codi || pg.pom_code || pomSource.codi_client || '',
      name_en: pg.nom_en || pg.name_en || pomSource.nom_client || '',
      name_cat: pg.nom_ca || pg.name_cat || pg.nom_cat || '',
      category: pg.categoria || pg.category || pomSource.categoria || '',
      abbreviation: pg.abbreviation || pomSource.codi_client || '',
      // is_key generally comes from the POMGlobal, but the GarmentPOMMap can
      // override it for this garment+POM combination.
      is_key: isKeyFromMap !== undefined ? isKeyFromMap : !!pg.is_key,
      description_en: pg.descripcio_en || pg.description_en || '',
      description_ca: pg.descripcio_ca || pg.description_ca || '',
      unitat: pg.unitat || '',
      body_measure_iso_codi: pg.body_measure_iso_codi || '',
      body_measure_iso_nom: pg.body_measure_iso_nom || '',
      start_point: pg.start_point || '',
      end_point: pg.end_point || '',
      reference_point: pg.reference_point || '',
      scope: pg.scope || '',
      orientation: pg.orientation || '',
      state: pg.state || '',
      line: pg.line || '',
      body_section: pg.body_section || '',
      tol_prod_cm: pg.tol_prod_cm,
      tol_samp_cm: pg.tol_samp_cm,
      applies_woven: pg.applies_woven,
      applies_knit: pg.applies_knit,
      applies_swim: pg.applies_swim,
      iso_ref: pg.iso_ref || '',
      notes: pg.notes || pomSource.notes || '',
    }
  })
}

export default function POMBrowser({
  mode = 'explore',
  garmentTypeCode = '',
  activePoms = [],
  onTogglePom = () => {},
  lang = 'ca',
}) {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')

  // Migració família→item: la pertinença viu a l'ITEM. selectedFamily = només per al breadcrumb;
  // selectedItem = el GarmentTypeItem real sobre el qual es llegeixen/escriuen els mapes.
  const [selectedFamily, setSelectedFamily] = useState(null)
  const [selectedItem, setSelectedItem] = useState(null)
  const [poms, setPoms] = useState([])
  const [orderedPoms, setOrderedPoms] = useState([])   // còpia ordenable local (assign drag)
  const [search, setSearch] = useState('')
  const [selectedPom, setSelectedPom] = useState(null)
  const [loading, setLoading] = useState(false)
  // Mode assign — persistència + cerca al catàleg + avisos.
  const [notice, setNotice] = useState(null)
  const [catalogQuery, setCatalogQuery] = useState('')
  const [catalogResults, setCatalogResults] = useState([])

  // Carrega els POMs mapejats a l'ITEM seleccionat: garment-pom-maps/?garment_type_item=<id>.
  // Sense mock: item sense mapes → llista buida (estat buit real). Recarregable via `reloadKey`.
  const [reloadKey, setReloadKey] = useState(0)
  useEffect(() => {
    setSelectedPom(null)
    if (!selectedItem?.id) { setPoms([]); return }
    setLoading(true)
    const params = new URLSearchParams({ garment_type_item: selectedItem.id, page_size: '500' })
    fetch(`${API}/api/v1/garment-pom-maps/?${params}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => setPoms(normalizePOMs(data.results || data)))
      .catch(() => setPoms([]))
      .finally(() => setLoading(false))
  }, [selectedItem, token, reloadKey])

  const matchSearch = (p) => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return (
      p.name_en?.toLowerCase().includes(q) ||
      p.name_cat?.toLowerCase().includes(q) ||
      p.abbreviation?.toLowerCase().includes(q) ||
      p.pom_code?.toLowerCase().includes(q)
    )
  }
  const filtered = poms.filter(matchSearch)            // explore (graella)
  const assignFiltered = orderedPoms.filter(matchSearch)  // assign (llista, ordre local)

  // ── Mode ASSIGN: persistència real (POST/DELETE garment-pom-maps) ──────────
  const authHeaders = { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }
  const mappedPomIds = new Set(poms.map(p => p.pom_id))

  // Cerca al catàleg de POMMaster DEL TENANT (poms/cerca/) per afegir-ne de nous a l'ítem.
  useEffect(() => {
    if (mode !== 'assign' || catalogQuery.trim().length < 2) { setCatalogResults([]); return }
    const tmr = setTimeout(() => {
      fetch(`${API}/api/v1/poms/cerca/?q=${encodeURIComponent(catalogQuery)}`, { headers: authHeaders })
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(d => setCatalogResults(d.results || []))
        .catch(() => setCatalogResults([]))
    }, 300)
    return () => clearTimeout(tmr)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalogQuery, mode, token])

  const assignAdd = async (master) => {
    setNotice(null)
    const nextOrdre = poms.reduce((m, p) => Math.max(m, p.ordre || 0), 0) + 1
    try {
      const r = await fetch(`${API}/api/v1/garment-pom-maps/`, {
        method: 'POST', headers: authHeaders,
        body: JSON.stringify({ garment_type_item: selectedItem.id, pom: master.id, is_key: false, ordre: nextOrdre }),
      })
      if (r.status === 403) return setNotice({ type: 'err', text: 'Sense permís per editar la pertinença (cal CONFIGURE).' })
      if (r.status === 400) return setNotice({ type: 'warn', text: `«${master.codi_client}» ja està assignat a aquest ítem.` })
      if (!r.ok) return setNotice({ type: 'err', text: 'No s\'ha pogut afegir el POM.' })
      setCatalogQuery(''); setCatalogResults([]); setReloadKey(k => k + 1)
    } catch { setNotice({ type: 'err', text: 'Error de connexió.' }) }
  }

  const assignRemove = async (pom) => {
    if (!pom.map_id) return
    setNotice(null)
    try {
      const r = await fetch(`${API}/api/v1/garment-pom-maps/${pom.map_id}/`, { method: 'DELETE', headers: authHeaders })
      if (r.status === 403) return setNotice({ type: 'err', text: 'Sense permís per editar la pertinença (cal CONFIGURE).' })
      if (!r.ok && r.status !== 204) return setNotice({ type: 'err', text: 'No s\'ha pogut treure el POM.' })
      setReloadKey(k => k + 1)
    } catch { setNotice({ type: 'err', text: 'Error de connexió.' }) }
  }

  // Toggle KEY (is_key editable) → PATCH; gate CONFIGURE al backend.
  const toggleKey = async (pom) => {
    if (!pom.map_id) return
    setNotice(null)
    try {
      const r = await fetch(`${API}/api/v1/garment-pom-maps/${pom.map_id}/`, {
        method: 'PATCH', headers: authHeaders, body: JSON.stringify({ is_key: !pom.is_key }),
      })
      if (r.status === 403) return setNotice({ type: 'err', text: 'Sense permís per editar (cal CONFIGURE).' })
      if (!r.ok) return setNotice({ type: 'err', text: 'No s\'ha pogut canviar KEY.' })
      setReloadKey(k => k + 1)
    } catch { setNotice({ type: 'err', text: 'Error de connexió.' }) }
  }

  // Reordenar (drag) — ordre que veurà el tècnic a la taula de mides. Persisteix ordre via PATCH.
  useEffect(() => { setOrderedPoms(poms) }, [poms])
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )
  const handleDragEnd = async (event) => {
    const { active, over } = event
    if (!over || active.id === over.id) return
    const oldIdx = orderedPoms.findIndex(p => String(p.map_id) === String(active.id))
    const newIdx = orderedPoms.findIndex(p => String(p.map_id) === String(over.id))
    if (oldIdx < 0 || newIdx < 0) return
    const next = arrayMove(orderedPoms, oldIdx, newIdx)
    setOrderedPoms(next)   // optimista
    setNotice(null)
    try {
      const results = await Promise.all(next.map((p, i) =>
        fetch(`${API}/api/v1/garment-pom-maps/${p.map_id}/`, {
          method: 'PATCH', headers: authHeaders, body: JSON.stringify({ ordre: i + 1 }),
        })))
      if (results.some(r => r.status === 403)) setNotice({ type: 'err', text: 'Sense permís per reordenar (cal CONFIGURE).' })
      else if (results.some(r => !r.ok)) setNotice({ type: 'err', text: 'No s\'ha pogut desar l\'ordre.' })
      setReloadKey(k => k + 1)   // reconcilia amb la BD
    } catch { setNotice({ type: 'err', text: 'Error de connexió.' }); setReloadKey(k => k + 1) }
  }

  // ── Step 'select-type' (família → ITEM, dos nivells) ──────────────────────
  if (!selectedItem) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <GarmentTypeSelector
          lang={lang}
          onSelect={(sel) => { setSelectedFamily(sel.family); setSelectedItem(sel.item) }}
        />
      </div>
    )
  }

  // ── Step 'view-poms' ──────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Breadcrumb + Search */}
      <div style={{
        display: 'flex', gap: 12, padding: '12px 16px',
        borderBottom: '0.5px solid #e4e4e2', background: '#fff',
        alignItems: 'center', flexWrap: 'wrap',
      }}>
        {(
          <button
            onClick={() => { setSelectedItem(null); setSelectedFamily(null); setNotice(null) }}
            title="Canviar tipus de prenda"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '6px 10px', borderRadius: 6, cursor: 'pointer',
              background: '#fff', color: '#868685',
              border: '0.5px solid #e0d5c5',
              fontSize: 11,
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#c27a2a'; e.currentTarget.style.color = '#c27a2a' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#e0d5c5'; e.currentTarget.style.color = '#868685' }}
          >
            ← Canviar tipus
          </button>
        )}

        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
          {selectedFamily?.grup && (
            <>
              <span style={{ fontSize: 10, color: '#868685', textTransform: 'uppercase', letterSpacing: '.08em' }}>
                {grupLabel(selectedFamily.grup, lang)}
              </span>
              <span style={{ fontSize: 12, color: '#868685' }}>›</span>
            </>
          )}
          {selectedFamily && (
            <>
              <span style={{ fontSize: 12, color: '#868685' }}>
                {gtName(selectedFamily, lang) || selectedFamily.codi_client}
              </span>
              <span style={{ fontSize: 12, color: '#868685' }}>›</span>
            </>
          )}
          <span style={{ fontSize: 13, fontWeight: 600, color: '#1d1d1b' }}>
            {selectedItem.name || selectedItem.code || '—'}
          </span>
        </div>

        <input
          type="text"
          placeholder="Cerca POM (codi, nom, abreviatura)..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ ...selectStyle, width: 280, flex: '0 1 auto', marginLeft: 'auto' }}
        />
        {mode === 'assign' && (
          <span style={{ fontSize: 11, color: '#868685' }}>
            {poms.length} POMs assignats
          </span>
        )}
      </div>

      {/* Assign — afegir POM del catàleg + avisos */}
      {mode === 'assign' && (
        <div style={{ padding: '10px 16px', borderBottom: '0.5px solid #e4e4e2', background: '#fdfbf8' }}>
          <div style={{ position: 'relative', maxWidth: 480 }}>
            <input
              type="text"
              placeholder="+ Afegir POM del catàleg (codi, nom)…"
              value={catalogQuery}
              onChange={e => setCatalogQuery(e.target.value)}
              style={{ ...selectStyle, width: '100%', boxSizing: 'border-box' }}
            />
            {catalogResults.length > 0 && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
                background: '#fff', border: '0.5px solid #e0d5c5', borderTop: 'none',
                borderRadius: '0 0 6px 6px', maxHeight: 240, overflowY: 'auto',
              }}>
                {catalogResults.map(res => {
                  const already = mappedPomIds.has(res.id)
                  return (
                    <div key={res.id}
                      onClick={() => !already && assignAdd(res)}
                      style={{
                        padding: '7px 10px', fontSize: 12, cursor: already ? 'default' : 'pointer',
                        display: 'flex', gap: 8, alignItems: 'center',
                        borderBottom: '0.5px solid #f5ede0', opacity: already ? 0.45 : 1,
                      }}
                      onMouseEnter={e => { if (!already) e.currentTarget.style.background = '#fdf6ee' }}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <span style={{ color: '#c27a2a', fontWeight: 600, minWidth: 70 }}>{res.codi_client}</span>
                      <span style={{ flex: 1, color: '#1d1d1b' }}>{res.nom_ca || res.nom_client || res.nom_en}</span>
                      {already && <span style={{ fontSize: 10, color: '#868685' }}>ja assignat</span>}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
          {notice && (
            <div style={{
              marginTop: 8, fontSize: 11, padding: '5px 10px', borderRadius: 4,
              background: notice.type === 'err' ? '#fff0f0' : '#fff9e6',
              border: `0.5px solid ${notice.type === 'err' ? '#f0a0a0' : '#f0c040'}`,
              color: notice.type === 'err' ? '#a32d2d' : '#7a5a00',
              display: 'flex', justifyContent: 'space-between', gap: 12,
            }}>
              {notice.text}
              <button onClick={() => setNotice(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit' }}>×</button>
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {loading && <p style={hintStyle}>Carregant POMs...</p>}
          {!loading && poms.length === 0 && (
            <p style={{ ...hintStyle, textAlign: 'center', marginTop: 40 }}>
              Cap POM assignat a aquest ítem — afegeix-ne del catàleg.
            </p>
          )}
          {!loading && poms.length > 0 && filtered.length === 0 && (
            <p style={{ ...hintStyle, textAlign: 'center', marginTop: 40 }}>
              Cap POM coincideix amb la cerca
            </p>
          )}

          {/* ASSIGN → LLISTA (drag-reorder, checkbox, KEY toggle, detall al clic). */}
          {mode === 'assign' ? (
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
              <SortableContext items={assignFiltered.map(p => String(p.map_id))}
                               strategy={verticalListSortingStrategy}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {assignFiltered.map(pom => (
                    <POMListRow
                      key={pom.map_id}
                      pom={pom}
                      isSelected={selectedPom?.map_id === pom.map_id}
                      onRowClick={() => setSelectedPom(selectedPom?.map_id === pom.map_id ? null : pom)}
                      onRemove={() => assignRemove(pom)}
                      onToggleKey={() => toggleKey(pom)}
                    />
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          ) : (
            /* EXPLORE → graella de targetes (intacte). */
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
              gap: 10,
            }}>
              {filtered.map(pom => (
                <POMCard
                  key={pom.map_id ?? pom.pom_code}
                  pom={pom}
                  mode={mode}
                  isActive={activePoms.includes(pom.pom_code)}
                  isSelected={selectedPom?.pom_code === pom.pom_code}
                  onSelect={() => setSelectedPom(selectedPom?.pom_code === pom.pom_code ? null : pom)}
                />
              ))}
            </div>
          )}
        </div>

        {selectedPom && (
          <POMDetailPanel pom={selectedPom} onClose={() => setSelectedPom(null)} />
        )}
      </div>
    </div>
  )
}

function POMListRow({ pom, isSelected, onRowClick, onRemove, onToggleKey }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: String(pom.map_id) })
  const style = {
    transform: CSS.Transform.toString(transform), transition,
    opacity: isDragging ? 0.6 : 1,
    display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px', borderRadius: 6,
    border: `0.5px solid ${isSelected ? '#c27a2a' : '#e8e8e6'}`,
    background: isSelected ? '#fdf6ee' : '#fff', fontSize: 12,
  }
  return (
    <div ref={setNodeRef} style={style}>
      <span {...attributes} {...listeners} title="Arrossega per reordenar"
        style={{ cursor: 'grab', color: '#b0b0ad', fontSize: 14, userSelect: 'none', lineHeight: 1 }}>⠿</span>
      <input type="checkbox" checked readOnly
        onClick={(e) => { e.stopPropagation(); onRemove() }}
        title="Desmarca per treure el POM de l'ítem" style={{ cursor: 'pointer' }} />
      <div onClick={onRowClick} style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', minWidth: 0 }}>
        <span style={{ color: '#c27a2a', fontWeight: 600, minWidth: 64 }}>{pom.pom_code}</span>
        <span style={{ flex: 1, minWidth: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          <PomNamePair en={pom.name_en} local={pom.name_cat} />
        </span>
        {pom.abbreviation && <Pill bg="#f5f0ea" color="#868685" mono>{pom.abbreviation}</Pill>}
        {pom.applies_woven && <Pill bg="#eef4fc" color="#2a5a8a">W</Pill>}
        {pom.applies_knit && <Pill bg="#f3edfb" color="#6a3a9a">K</Pill>}
        {pom.applies_swim && <Pill bg="#e8f5f5" color="#2a7a7a">S</Pill>}
      </div>
      {pom.pendent_revisio && (
        <span title="Clon de plantilla — cal revisar el delta" style={{
          background: '#fff3e0', color: '#b25a00', fontSize: 9, padding: '2px 6px', borderRadius: 3,
          fontWeight: 600, letterSpacing: '.06em', border: '0.5px solid #f0c040',
        }}>REVISAR</span>
      )}
      <button type="button" onClick={(e) => { e.stopPropagation(); onToggleKey() }}
        title="Marca/desmarca KEY" style={{
          cursor: 'pointer', fontSize: 9, padding: '2px 7px', borderRadius: 3, fontWeight: 600,
          letterSpacing: '.06em', border: `0.5px solid ${pom.is_key ? '#e0c8a0' : '#e0d5c5'}`,
          background: pom.is_key ? '#fdf6ee' : '#fff', color: pom.is_key ? '#c27a2a' : '#b0b0ad',
        }}>KEY</button>
    </div>
  )
}

function POMCard({ pom, mode, isActive, isSelected, onSelect }) {
  const borderColor = mode === 'assign' && isActive
    ? '#3b6d11'
    : isSelected ? '#c27a2a' : '#e0d5c5'
  const background = mode === 'assign' && isActive
    ? '#f0f9f0'
    : isSelected ? '#fdf6ee' : '#fff'

  return (
    <div
      onClick={onSelect}
      style={{
        border: `1px solid ${borderColor}`,
        borderRadius: 8, padding: '12px 14px',
        background, cursor: 'pointer',
        transition: 'border-color .15s, background .15s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
        <span style={{ fontSize: 10, color: '#868685', fontWeight: 500 }}>{pom.pom_code}</span>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {pom.pendent_revisio && (
            <span title="Clon de plantilla — cal revisar el delta" style={{
              background: '#fff3e0', color: '#b25a00',
              fontSize: 9, padding: '2px 6px', borderRadius: 3,
              fontWeight: 600, letterSpacing: '.06em',
              border: '0.5px solid #f0c040',
            }}>REVISAR</span>
          )}
          {pom.is_key && (
            <span style={{
              background: '#fdf6ee', color: '#c27a2a',
              fontSize: 9, padding: '2px 6px', borderRadius: 3,
              fontWeight: 600, letterSpacing: '.08em',
              border: '0.5px solid #e0c8a0',
            }}>KEY</span>
          )}
          {mode === 'assign' && (
            <input
              type="checkbox"
              checked={isActive}
              onChange={onSelect}
              onClick={e => e.stopPropagation()}
              title="Desmarca per treure el POM de l'ítem"
              style={{ cursor: 'pointer' }}
            />
          )}
        </div>
      </div>
      {/* Convenció sector: anglès primari (negre) + nom localitzat (cursiva gris). */}
      <p style={{ fontSize: 13, fontWeight: 500, color: '#1d1d1b', margin: 0, lineHeight: 1.3 }}>
        {pom.name_en || pom.name_cat}
      </p>
      {pom.name_en && pom.name_cat && pom.name_cat !== pom.name_en && (
        <p style={{ fontSize: 11, color: '#868685', fontStyle: 'italic', margin: '2px 0 0', lineHeight: 1.3 }}>
          {pom.name_cat}
        </p>
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
        {pom.abbreviation && (
          <Pill bg="#f5f0ea" color="#868685" mono>{pom.abbreviation}</Pill>
        )}
        {pom.category && (
          <Pill bg="#f5f0ea" color="#868685">{pom.category}</Pill>
        )}
        {pom.applies_woven && <Pill bg="#eef4fc" color="#2a5a8a">WOVEN</Pill>}
        {pom.applies_knit && <Pill bg="#f3edfb" color="#6a3a9a">KNIT</Pill>}
        {pom.applies_swim && <Pill bg="#e8f5f5" color="#2a7a7a">SWIM</Pill>}
      </div>
    </div>
  )
}

// Convenció sector tèxtil: nom anglès primari (negre), nom localitzat al costat en cursiva gris.
// Si no hi ha EN → mostra el que hi hagi. Si EN i local coincideixen → només un.
export function PomNamePair({ en, local }) {
  const primary = en || local || ''
  const secondary = en && local && local !== en ? local : ''
  return (
    <>
      <span style={{ color: '#1d1d1b' }}>{primary}</span>
      {secondary && (
        <span style={{ color: '#868685', fontStyle: 'italic', marginLeft: 8 }}>{secondary}</span>
      )}
    </>
  )
}

function Pill({ bg, color, mono, children }) {
  return (
    <span style={{
      background: bg, color,
      fontSize: 9, padding: '2px 6px', borderRadius: 3,
      fontWeight: 500, letterSpacing: '.04em',
      fontFamily: mono ? 'IBM Plex Mono, monospace' : 'inherit',
    }}>{children}</span>
  )
}

export function POMDetailPanel({ pom, onClose }) {
  return (
    <div style={{
      width: 340, borderLeft: '0.5px solid #e4e4e2',
      padding: '18px 20px', overflowY: 'auto',
      background: '#fdf9f5', fontSize: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
        <div>
          <span style={{ fontSize: 10, color: '#868685' }}>{pom.pom_code}</span>
          <h2 style={{ fontSize: 14, fontWeight: 600, margin: '2px 0 0', color: '#1d1d1b' }}>{pom.name_en}</h2>
          {pom.name_cat && (
            <p style={{ fontSize: 11, color: '#868685', margin: '2px 0 0' }}>{pom.name_cat}</p>
          )}
        </div>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#868685', fontSize: 18, lineHeight: 1 }}
          aria-label="Tancar"
        >×</button>
      </div>

      {/* Bloc complet "com mesurar". Els buits es mostren com "—" perquè es vegi
          què falta definir (típic en POMs tenant-only sense pom_global). */}
      <DetailSection title="Identificació">
        <DetailRow label="Codi" value={pom.pom_code} mono />
        <DetailRow label="Nom EN" value={pom.name_en} />
        <DetailRow label="Nom local" value={pom.name_cat} />
        <DetailRow label="Abreviatura" value={pom.abbreviation} mono />
        <DetailRow label="Categoria" value={pom.category} />
        <DetailRow label="Unitat" value={pom.unitat} />
      </DetailSection>

      <DetailSection title="Com mesurar">
        <DetailRow label="Des d'on (start point)" value={pom.start_point} />
        <DetailRow label="Fins on (end point)" value={pom.end_point} />
        <DetailRow label="Punt de referència" value={pom.reference_point} />
        <DetailRow label="Scope" value={pom.scope} />
        <DetailRow label="Orientation" value={pom.orientation} />
        <DetailRow label="State" value={pom.state} />
        <DetailRow label="Line" value={pom.line} />
        <DetailRow label="Body Section" value={pom.body_section} />
      </DetailSection>

      <DetailSection title="Toleràncies">
        <DetailRow
          label="Tol. Producció"
          value={pom.tol_prod_cm != null && pom.tol_prod_cm !== '' ? `±${pom.tol_prod_cm} cm` : null}
        />
        <DetailRow
          label="Tol. Mostra"
          value={pom.tol_samp_cm != null && pom.tol_samp_cm !== '' ? `±${pom.tol_samp_cm} cm` : null}
        />
      </DetailSection>

      <DetailSection title="Aplica a">
        <DetailRow label="Teixit pla (woven)" value={boolLabel(pom.applies_woven)} />
        <DetailRow label="Punt (knit)" value={boolLabel(pom.applies_knit)} />
        <DetailRow label="Bany (swim)" value={boolLabel(pom.applies_swim)} />
      </DetailSection>

      <DetailSection title="Referències">
        <DetailRow label="ISO Ref." value={pom.iso_ref} />
        <DetailRow
          label="Mesura corporal ISO"
          value={
            pom.body_measure_iso_codi || pom.body_measure_iso_nom
              ? [pom.body_measure_iso_codi, pom.body_measure_iso_nom].filter(Boolean).join(' · ')
              : null
          }
        />
      </DetailSection>

      <DetailSection title="Descripcions">
        <DetailRow label="Descripció EN" value={pom.description_en} multiline />
        <DetailRow label="Descripció local" value={pom.description_ca} multiline />
      </DetailSection>
    </div>
  )
}

function boolLabel(v) {
  if (v === true) return 'Sí'
  if (v === false) return 'No'
  return null   // undefined/null → "—" (camp sense definir)
}

function DetailSection({ title, children }) {
  return (
    <section style={{ marginBottom: 16 }}>
      <h3 style={{
        fontSize: 9, fontWeight: 700, color: '#c27a2a',
        textTransform: 'uppercase', letterSpacing: '.1em',
        margin: '0 0 8px', paddingBottom: 4, borderBottom: '0.5px solid #ece2d4',
      }}>{title}</h3>
      <dl style={{ margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {children}
      </dl>
    </section>
  )
}

function DetailRow({ label, value, multiline = false, mono = false }) {
  const empty = value === null || value === undefined || value === ''
  return (
    <div>
      <dt style={{
        fontSize: 9, fontWeight: 600, color: '#868685',
        textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 2,
      }}>{label}</dt>
      <dd style={{
        margin: 0,
        color: empty ? '#c0bdb8' : '#1d1d1b',
        fontSize: multiline ? 11 : 12,
        lineHeight: multiline ? 1.5 : 1.3,
        fontFamily: mono && !empty ? 'IBM Plex Mono, monospace' : 'inherit',
      }}>{empty ? '—' : value}</dd>
    </div>
  )
}

const selectStyle = {
  background: '#fff',
  border: '0.5px solid #e4e4e2',
  borderRadius: 8,
  padding: '8px 12px',
  fontSize: 12,
  outline: 'none',
  minWidth: 220,
}

const hintStyle = {
  fontSize: 12,
  color: '#868685',
  margin: 0,
}
