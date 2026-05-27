import { useState, useEffect } from 'react'
import useAuthStore from '../../store/auth'
import GarmentTypeSelector from '../GarmentTypeSelector/GarmentTypeSelector'

const API = import.meta.env.VITE_API_URL || ''

function gtNom(t, lang = 'ca') {
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

// TODO(backend): endpoint dedicat `GET /api/v1/poms/?garment_type=<id>` que retorni
// POMs filtrats per GarmentType amb tots els camps rics de POMGlobal
// (name_en, name_cat, abbreviation, is_key, applies_woven/knit/swim, tol_*, etc.).
// El POMMasterViewSet actual no exposa aquests camps ni accepta filtre per garment_type.
// Mentrestant, aquest component intenta /api/v1/poms/ i, si la resposta no porta
// els camps rics, recau en MOCK_POMS perquè la UI sigui usable.

const MOCK_POMS = [
  {
    pom_code: 'POM-001', name_en: 'Chest width', name_cat: 'Ample de pit',
    category: 'Upper body', abbreviation: 'CH', is_key: true,
    description_en: 'Half chest measured 2.5 cm below armhole, horizontal seam to seam.',
    start_point: 'Side seam (left)', end_point: 'Side seam (right)',
    reference_point: '2.5 cm below armhole',
    scope: 'GARMENT', orientation: 'HORIZONTAL', state: 'FLAT', body_section: 'TORSO',
    tol_prod_cm: 1.0, tol_samp_cm: 0.5,
    applies_woven: true, applies_knit: true, applies_swim: false,
    iso_ref: 'ISO 8559-2 §4.1',
  },
  {
    pom_code: 'POM-002', name_en: 'Shoulder width', name_cat: 'Ample d\'espatlles',
    category: 'Upper body', abbreviation: 'SH', is_key: true,
    description_en: 'Horizontal distance between shoulder points.',
    start_point: 'Shoulder point left', end_point: 'Shoulder point right',
    scope: 'GARMENT', orientation: 'HORIZONTAL', state: 'FLAT', body_section: 'TORSO',
    tol_prod_cm: 0.5, tol_samp_cm: 0.3,
    applies_woven: true, applies_knit: true, applies_swim: false,
  },
  {
    pom_code: 'POM-003', name_en: 'Waist width', name_cat: 'Ample de cintura',
    category: 'Upper body', abbreviation: 'WA', is_key: true,
    description_en: 'Half waist at narrowest point.',
    scope: 'GARMENT', orientation: 'HORIZONTAL', state: 'FLAT', body_section: 'TORSO',
    tol_prod_cm: 1.0, tol_samp_cm: 0.5,
    applies_woven: true, applies_knit: true, applies_swim: true,
  },
  {
    pom_code: 'POM-004', name_en: 'Hip width', name_cat: 'Ample de maluc',
    category: 'Lower body', abbreviation: 'HP', is_key: true,
    description_en: 'Half hip at fullest part.',
    scope: 'GARMENT', orientation: 'HORIZONTAL', state: 'FLAT', body_section: 'TORSO',
    tol_prod_cm: 1.0, tol_samp_cm: 0.5,
    applies_woven: true, applies_knit: true, applies_swim: true,
  },
  {
    pom_code: 'POM-010', name_en: 'Sleeve length', name_cat: 'Llargada de màniga',
    category: 'Sleeves', abbreviation: 'SL',
    description_en: 'From shoulder point to cuff edge.',
    scope: 'GARMENT', orientation: 'VERTICAL', state: 'FLAT', body_section: 'ARM',
    tol_prod_cm: 1.0, tol_samp_cm: 0.5,
    applies_woven: true, applies_knit: true, applies_swim: false,
  },
  {
    pom_code: 'POM-020', name_en: 'Inseam', name_cat: 'Entrecuixa',
    category: 'Lower body', abbreviation: 'IS', is_key: true,
    description_en: 'Inside leg from crotch to hem.',
    scope: 'GARMENT', orientation: 'VERTICAL', state: 'FLAT', body_section: 'LEG',
    tol_prod_cm: 1.5, tol_samp_cm: 0.5,
    applies_woven: true, applies_knit: true, applies_swim: false,
  },
]

// Normalitza una resposta /api/v1/poms/ (POMMaster) al format esperat per la UI.
// Si la resposta no porta els camps rics (cas actual del backend), usa MOCK_POMS.
function normalizePOMs(raw) {
  if (!Array.isArray(raw) || raw.length === 0) return null
  const first = raw[0]
  // Heurística: si no hi ha name_en/pom_code, no és el format ric — fallback a mock.
  if (!first.name_en && !first.pom_code && !first.nom_en) return null
  return raw.map(p => ({
    pom_code: p.pom_code || p.codi_client || p.codi || '',
    name_en: p.name_en || p.nom_en || p.nom_client || '',
    name_cat: p.name_cat || p.nom_cat || p.nom_ca || '',
    category: p.category || p.categoria || p.categoria_nom || '',
    abbreviation: p.abbreviation || '',
    is_key: !!p.is_key,
    description_en: p.description_en || p.descripcio_en || '',
    start_point: p.start_point || '',
    end_point: p.end_point || '',
    reference_point: p.reference_point || '',
    scope: p.scope || '',
    orientation: p.orientation || '',
    state: p.state || '',
    line: p.line || '',
    body_section: p.body_section || '',
    tol_prod_cm: p.tol_prod_cm,
    tol_samp_cm: p.tol_samp_cm,
    applies_woven: p.applies_woven,
    applies_knit: p.applies_knit,
    applies_swim: p.applies_swim,
    iso_ref: p.iso_ref || '',
    notes: p.notes || '',
  }))
}

export default function POMBrowser({
  mode = 'explore',
  garmentTypeCode = '',
  activePoms = [],
  onTogglePom = () => {},
  lang = 'ca',
}) {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')

  // L'objecte GarmentType complet seleccionat (null = step 'select-type').
  const [selectedGT, setSelectedGT] = useState(null)
  const [poms, setPoms] = useState([])
  const [search, setSearch] = useState('')
  const [selectedPom, setSelectedPom] = useState(null)
  const [loading, setLoading] = useState(false)
  const [usingMock, setUsingMock] = useState(false)

  // Resol l'objecte GarmentType quan només arriba l'ID per prop (cas wizard assign).
  useEffect(() => {
    if (!garmentTypeCode) { setSelectedGT(null); return }
    // Si ja és l'objecte seleccionat, no recarreguem.
    if (selectedGT && String(selectedGT.id) === String(garmentTypeCode)) return

    fetch(`${API}/api/v1/garment-types/${garmentTypeCode}/`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => setSelectedGT(data))
      .catch(() => {
        // Fallback: objecte sintètic amb només l'ID
        setSelectedGT({ id: garmentTypeCode, nom_en: '', nom_ca: '', grup: '' })
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [garmentTypeCode])

  // Carrega POMs quan canvia el GarmentType seleccionat.
  useEffect(() => {
    setSelectedPom(null)
    if (!selectedGT?.id) { setPoms([]); return }
    setLoading(true)
    // TODO(backend): afegir filtre `?garment_type=<id>` a POMMasterViewSet
    // i exposar camps rics de POMGlobal al serializer.
    const params = new URLSearchParams({ garment_type: selectedGT.id, page_size: 500 })
    fetch(`${API}/api/v1/poms/?${params}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        const raw = data.results || data
        const normalized = normalizePOMs(raw)
        if (normalized) {
          setPoms(normalized)
          setUsingMock(false)
        } else {
          setPoms(MOCK_POMS)
          setUsingMock(true)
        }
      })
      .catch(() => {
        setPoms(MOCK_POMS)
        setUsingMock(true)
      })
      .finally(() => setLoading(false))
  }, [selectedGT, token])

  const filtered = poms.filter(p => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return (
      p.name_en?.toLowerCase().includes(q) ||
      p.name_cat?.toLowerCase().includes(q) ||
      p.abbreviation?.toLowerCase().includes(q) ||
      p.pom_code?.toLowerCase().includes(q)
    )
  })

  // ── Step 'select-type' ────────────────────────────────────────────────────
  if (!selectedGT) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <GarmentTypeSelector
          lang={lang}
          onSelect={(gt) => setSelectedGT(gt)}
        />
      </div>
    )
  }

  // ── Step 'view-poms' ──────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', fontFamily: 'IBM Plex Mono, monospace' }}>
      {/* Breadcrumb + Search */}
      <div style={{
        display: 'flex', gap: 12, padding: '12px 16px',
        borderBottom: '0.5px solid #e4e4e2', background: '#fff',
        alignItems: 'center', flexWrap: 'wrap',
      }}>
        {mode === 'explore' && (
          <button
            onClick={() => setSelectedGT(null)}
            title="Canviar tipus de prenda"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '6px 10px', borderRadius: 6, cursor: 'pointer',
              background: '#fff', color: '#868685',
              border: '0.5px solid #e0d5c5',
              fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#c27a2a'; e.currentTarget.style.color = '#c27a2a' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = '#e0d5c5'; e.currentTarget.style.color = '#868685' }}
          >
            ← Canviar tipus
          </button>
        )}

        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
          {selectedGT.grup && (
            <>
              <span style={{ fontSize: 10, color: '#868685', textTransform: 'uppercase', letterSpacing: '.08em' }}>
                {grupLabel(selectedGT.grup, lang)}
              </span>
              <span style={{ fontSize: 12, color: '#868685' }}>›</span>
            </>
          )}
          <span style={{ fontSize: 13, fontWeight: 600, color: '#1d1d1b' }}>
            {gtNom(selectedGT, lang) || selectedGT.codi_client || '—'}
          </span>
        </div>

        <input
          type="text"
          placeholder="Cerca POM (codi, nom, abreviatura)..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ ...selectStyle, width: 280, flex: '0 1 auto', marginLeft: 'auto' }}
        />
        {usingMock && (
          <span style={{
            fontSize: 10, color: '#c27a2a', background: '#fdf6ee',
            border: '0.5px solid #e0c8a0', padding: '3px 8px', borderRadius: 4,
          }}>
            mock data · backend pendent
          </span>
        )}
        {mode === 'assign' && (
          <span style={{ fontSize: 11, color: '#868685' }}>
            {activePoms.length} POMs assignats
          </span>
        )}
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
          {loading && <p style={hintStyle}>Carregant POMs...</p>}
          {!loading && filtered.length === 0 && (
            <p style={{ ...hintStyle, textAlign: 'center', marginTop: 40 }}>
              Cap POM trobat
            </p>
          )}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
            gap: 10,
          }}>
            {filtered.map(pom => (
              <POMCard
                key={pom.pom_code}
                pom={pom}
                mode={mode}
                isActive={activePoms.includes(pom.pom_code)}
                isSelected={selectedPom?.pom_code === pom.pom_code}
                onSelect={() => mode === 'explore'
                  ? setSelectedPom(selectedPom?.pom_code === pom.pom_code ? null : pom)
                  : onTogglePom(pom.pom_code)
                }
              />
            ))}
          </div>
        </div>

        {mode === 'explore' && selectedPom && (
          <POMDetailPanel pom={selectedPom} onClose={() => setSelectedPom(null)} />
        )}
      </div>
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
              style={{ cursor: 'pointer' }}
            />
          )}
        </div>
      </div>
      <p style={{ fontSize: 13, fontWeight: 500, color: '#1d1d1b', margin: 0, lineHeight: 1.3 }}>
        {pom.name_en}
      </p>
      {pom.name_cat && (
        <p style={{ fontSize: 11, color: '#868685', margin: '2px 0 0', lineHeight: 1.3 }}>
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

function POMDetailPanel({ pom, onClose }) {
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

      <dl style={{ margin: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <DetailRow label="Abreviatura" value={pom.abbreviation} />
        <DetailRow label="Categoria" value={pom.category} />
        <DetailRow label="Descripció" value={pom.description_en} multiline />
        <DetailRow label="Start Point" value={pom.start_point} />
        <DetailRow label="End Point" value={pom.end_point} />
        <DetailRow label="Reference Point" value={pom.reference_point} />
        <DetailRow label="Scope" value={pom.scope} />
        <DetailRow label="Orientation" value={pom.orientation} />
        <DetailRow label="State" value={pom.state} />
        <DetailRow label="Line" value={pom.line} />
        <DetailRow label="Body Section" value={pom.body_section} />
        <DetailRow
          label="Tol. Producció"
          value={pom.tol_prod_cm != null ? `±${pom.tol_prod_cm} cm` : null}
        />
        <DetailRow
          label="Tol. Mostra"
          value={pom.tol_samp_cm != null ? `±${pom.tol_samp_cm} cm` : null}
        />
        <DetailRow label="ISO Ref." value={pom.iso_ref} />
        <DetailRow label="Notes" value={pom.notes} multiline />
      </dl>
    </div>
  )
}

function DetailRow({ label, value, multiline = false }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <div>
      <dt style={{
        fontSize: 9, fontWeight: 600, color: '#868685',
        textTransform: 'uppercase', letterSpacing: '.08em', marginBottom: 2,
      }}>{label}</dt>
      <dd style={{
        margin: 0, color: '#1d1d1b',
        fontSize: multiline ? 11 : 12,
        lineHeight: multiline ? 1.5 : 1.3,
      }}>{value}</dd>
    </div>
  )
}

const selectStyle = {
  background: '#fff',
  border: '0.5px solid #e4e4e2',
  borderRadius: 8,
  padding: '8px 12px',
  fontSize: 12,
  fontFamily: 'IBM Plex Mono, monospace',
  outline: 'none',
  minWidth: 220,
}

const hintStyle = {
  fontSize: 12,
  color: '#868685',
  margin: 0,
}
