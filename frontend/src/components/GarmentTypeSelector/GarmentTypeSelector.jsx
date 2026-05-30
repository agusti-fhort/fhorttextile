import { useState, useEffect } from 'react'
import useAuthStore from '../../store/auth'

const API = import.meta.env.VITE_API_URL || ''

// Canonical groups. The order sets the button order.
const GRUPS = [
  { codi: 'TOPS',        label_cat: 'Parts superiors', label_en: 'Tops',        label_es: 'Partes superiores' },
  { codi: 'BOTTOMS',     label_cat: 'Parts inferiors', label_en: 'Bottoms',     label_es: 'Partes inferiores' },
  { codi: 'DRESSES',     label_cat: 'Vestits',         label_en: 'Dresses',     label_es: 'Vestidos' },
  { codi: 'OUTERWEAR',   label_cat: 'Abrics',          label_en: 'Outerwear',   label_es: 'Abrigos' },
  { codi: 'UNDERWEAR',   label_cat: 'Interior',        label_en: 'Underwear',   label_es: 'Interior' },
  { codi: 'SWIMWEAR',    label_cat: 'Bany',            label_en: 'Swimwear',    label_es: 'Baño' },
  { codi: 'ACCESSORIES', label_cat: 'Complements',     label_en: 'Accessories', label_es: 'Complementos' },
]

// TODO(backend): GarmentTypeViewSet is a ReadOnlyModelViewSet — POST/PATCH/DELETE
// return 405. It must be converted to a ModelViewSet with proper permissions for
// per-tenant CRUD management. Meanwhile, the UI attempts the operations and shows
// l'error si fallen.

// Mock data for when the backend returns no entries for a group.
// Derived from the canonical GarmentTypeGlobal catalog.
const MOCK_GT_BY_GROUP = {
  TOPS: [
    { id: 'mock-tops-1', codi_client: 'T_SHIRT',   nom_en: 'T-shirt',      nom_ca: 'Samarreta',   nom_es: 'Camiseta',   grup: 'TOPS', is_system: true,  actiu: true },
    { id: 'mock-tops-2', codi_client: 'POLO',      nom_en: 'Polo',         nom_ca: 'Polo',        nom_es: 'Polo',       grup: 'TOPS', is_system: true,  actiu: true },
    { id: 'mock-tops-3', codi_client: 'SHIRT',     nom_en: 'Shirt',        nom_ca: 'Camisa',      nom_es: 'Camisa',     grup: 'TOPS', is_system: true,  actiu: true },
    { id: 'mock-tops-4', codi_client: 'BLOUSE',    nom_en: 'Blouse',       nom_ca: 'Brusa',       nom_es: 'Blusa',      grup: 'TOPS', is_system: true,  actiu: true },
    { id: 'mock-tops-5', codi_client: 'HOODIE',    nom_en: 'Hoodie',       nom_ca: 'Dessuadora',  nom_es: 'Sudadera',   grup: 'TOPS', is_system: true,  actiu: true },
    { id: 'mock-tops-6', codi_client: 'SWEATER',   nom_en: 'Sweater',      nom_ca: 'Jersei',      nom_es: 'Jersey',     grup: 'TOPS', is_system: true,  actiu: true },
  ],
  BOTTOMS: [
    { id: 'mock-bot-1',  codi_client: 'TROUSERS',  nom_en: 'Trousers',     nom_ca: 'Pantalons',   nom_es: 'Pantalones', grup: 'BOTTOMS', is_system: true, actiu: true },
    { id: 'mock-bot-2',  codi_client: 'JEANS',     nom_en: 'Jeans',        nom_ca: 'Texans',      nom_es: 'Vaqueros',   grup: 'BOTTOMS', is_system: true, actiu: true },
    { id: 'mock-bot-3',  codi_client: 'SHORTS',    nom_en: 'Shorts',       nom_ca: 'Pantalons curts', nom_es: 'Pantalones cortos', grup: 'BOTTOMS', is_system: true, actiu: true },
    { id: 'mock-bot-4',  codi_client: 'SKIRT',     nom_en: 'Skirt',        nom_ca: 'Faldilla',    nom_es: 'Falda',      grup: 'BOTTOMS', is_system: true, actiu: true },
  ],
  DRESSES: [
    { id: 'mock-dr-1',   codi_client: 'DRESS',     nom_en: 'Dress',        nom_ca: 'Vestit',      nom_es: 'Vestido',    grup: 'DRESSES', is_system: true, actiu: true },
    { id: 'mock-dr-2',   codi_client: 'JUMPSUIT',  nom_en: 'Jumpsuit',     nom_ca: 'Granota',     nom_es: 'Mono',       grup: 'DRESSES', is_system: true, actiu: true },
  ],
  OUTERWEAR: [
    { id: 'mock-out-1',  codi_client: 'COAT',      nom_en: 'Coat',         nom_ca: 'Abric',       nom_es: 'Abrigo',     grup: 'OUTERWEAR', is_system: true, actiu: true },
    { id: 'mock-out-2',  codi_client: 'JACKET',    nom_en: 'Jacket',       nom_ca: 'Jaqueta',     nom_es: 'Chaqueta',   grup: 'OUTERWEAR', is_system: true, actiu: true },
    { id: 'mock-out-3',  codi_client: 'BLAZER',    nom_en: 'Blazer',       nom_ca: 'Blazer',      nom_es: 'Blazer',     grup: 'OUTERWEAR', is_system: true, actiu: true },
  ],
  UNDERWEAR: [
    { id: 'mock-und-1',  codi_client: 'BRA',       nom_en: 'Bra',          nom_ca: 'Sostenidor',  nom_es: 'Sujetador',  grup: 'UNDERWEAR', is_system: true, actiu: true },
    { id: 'mock-und-2',  codi_client: 'BRIEF',     nom_en: 'Underwear',    nom_ca: 'Roba interior', nom_es: 'Ropa interior', grup: 'UNDERWEAR', is_system: true, actiu: true },
  ],
  SWIMWEAR: [
    { id: 'mock-sw-1',   codi_client: 'SWIMSUIT',  nom_en: 'Swimsuit',     nom_ca: 'Banyador',    nom_es: 'Bañador',    grup: 'SWIMWEAR', is_system: true, actiu: true },
    { id: 'mock-sw-2',   codi_client: 'BIKINI',    nom_en: 'Bikini',       nom_ca: 'Biquini',     nom_es: 'Bikini',     grup: 'SWIMWEAR', is_system: true, actiu: true },
  ],
  ACCESSORIES: [
    { id: 'mock-acc-1',  codi_client: 'SCARF',     nom_en: 'Scarf',        nom_ca: 'Bufanda',     nom_es: 'Bufanda',    grup: 'ACCESSORIES', is_system: true, actiu: true },
    { id: 'mock-acc-2',  codi_client: 'HAT',       nom_en: 'Hat',          nom_ca: 'Barret',      nom_es: 'Sombrero',   grup: 'ACCESSORIES', is_system: true, actiu: true },
  ],
}

function gtName(t, lang) {
  if (lang === 'ca') return t.nom_ca || t.nom_cat || t.nom_en || t.nom_client || t.global_nom || ''
  if (lang === 'es') return t.nom_es || t.nom_en || t.nom_client || t.global_nom || ''
  return t.nom_en || t.nom_client || t.global_nom || ''
}

export default function GarmentTypeSelector({ onSelect, selectedId = null, lang = 'ca' }) {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')

  const [grupActiu, setGrupActiu] = useState('TOPS')
  const [tipus, setTipus] = useState([])
  const [loading, setLoading] = useState(false)
  const [usingMock, setUsingMock] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [msg, setMsg] = useState(null)

  const authHeaders = () => token ? { Authorization: `Bearer ${token}` } : {}

  const loadGroup = (grup) => {
    setLoading(true)
    const params = new URLSearchParams({ grup, page_size: 200, actiu: 'true' })
    fetch(`${API}/api/v1/garment-types/?${params}`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => {
        const list = data.results || data || []
        if (Array.isArray(list) && list.length > 0) {
          setTipus(list)
          setUsingMock(false)
        } else {
          setTipus(MOCK_GT_BY_GROUP[grup] || [])
          setUsingMock(true)
        }
      })
      .catch(() => {
        setTipus(MOCK_GT_BY_GROUP[grup] || [])
        setUsingMock(true)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadGroup(grupActiu) }, [grupActiu])

  const handleDelete = async (t) => {
    if (t.is_system) {
      setMsg({ type: 'error', text: 'No es pot esborrar un tipus de sistema.' })
      return
    }
    if (!confirm(`Esborrar "${gtName(t, lang)}"?`)) return
    try {
      const r = await fetch(`${API}/api/v1/garment-types/${t.id}/`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (r.ok || r.status === 204) {
        setTipus(prev => prev.filter(x => x.id !== t.id))
        setMsg({ type: 'ok', text: 'Tipus esborrat.' })
      } else if (r.status === 405) {
        setMsg({ type: 'error', text: 'Backend encara no suporta esborrar (ReadOnly). TODO pendent.' })
      } else {
        setMsg({ type: 'error', text: `Error ${r.status} esborrant.` })
      }
    } catch (e) {
      setMsg({ type: 'error', text: String(e) })
    }
  }

  const handleClone = (t) => {
    setEditTarget({
      id: null,
      codi_client: (t.codi_client || '') + '_COPY',
      nom_client: t.nom_client || gtName(t, lang),
      nom_en: (t.nom_en || '') + (t.nom_en ? ' (copy)' : ''),
      nom_ca: (t.nom_ca || '') + (t.nom_ca ? ' (còpia)' : ''),
      nom_es: (t.nom_es || '') + (t.nom_es ? ' (copia)' : ''),
      grup: t.grup || grupActiu,
      is_system: false,
      actiu: true,
    })
    setShowModal(true)
  }

  const handleSaved = (saved) => {
    setTipus(prev => {
      const idx = prev.findIndex(t => t.id === saved.id)
      if (idx >= 0) {
        const next = [...prev]
        next[idx] = saved
        return next
      }
      return [...prev, saved]
    })
    setShowModal(false)
    setMsg({ type: 'ok', text: editTarget?.id ? 'Tipus actualitzat.' : 'Tipus creat.' })
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      fontFamily: 'IBM Plex Mono, monospace',
    }}>
      {/* Botons de grup */}
      <div style={{
        display: 'flex', gap: 8, flexWrap: 'wrap',
        padding: '14px 16px', borderBottom: '0.5px solid #e4e4e2',
        background: '#fff',
      }}>
        {GRUPS.map(g => {
          const active = grupActiu === g.codi
          const label = lang === 'ca' ? g.label_cat : lang === 'es' ? g.label_es : g.label_en
          return (
            <button
              key={g.codi}
              onClick={() => setGrupActiu(g.codi)}
              style={{
                padding: '6px 14px', borderRadius: 6, cursor: 'pointer',
                background: active ? '#f5e6d0' : '#fff',
                color: active ? '#c27a2a' : '#1d1d1b',
                border: `1px solid ${active ? '#c27a2a' : '#e0d5c5'}`,
                fontFamily: 'IBM Plex Mono, monospace',
                fontSize: 11, fontWeight: active ? 600 : 400,
              }}
            >
              {label}
            </button>
          )
        })}
      </div>

      {/* Missatge */}
      {msg && (
        <div style={{
          padding: '8px 16px', fontSize: 11,
          background: msg.type === 'ok' ? '#f0f9f0' : '#fff0f0',
          borderBottom: '0.5px solid #e4e4e2',
          color: msg.type === 'ok' ? '#3b6d11' : '#a32d2d',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <span>{msg.text}</span>
          <button onClick={() => setMsg(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 14 }}>×</button>
        </div>
      )}

      {/* Grid */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {loading && <p style={{ fontSize: 12, color: '#868685', margin: 0 }}>Carregant tipus de prenda...</p>}

        {!loading && tipus.length === 0 && (
          <p style={{ fontSize: 12, color: '#868685', margin: 0 }}>
            Cap tipus de prenda en aquest grup.
          </p>
        )}

        {usingMock && !loading && (
          <p style={{
            fontSize: 10, color: '#c27a2a', margin: '0 0 12px',
            padding: '4px 8px', background: '#fdf6ee',
            border: '0.5px solid #e0c8a0', borderRadius: 4,
            display: 'inline-block',
          }}>
            mock data · backend sense entries per a aquest grup
          </p>
        )}

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: 12, marginBottom: 16,
        }}>
          {tipus.map(t => (
            <GarmentTypeCard
              key={t.id}
              tipus={t}
              nom={gtName(t, lang)}
              isSelected={selectedId === t.id}
              onSelect={() => onSelect && onSelect(t)}
              onEdit={() => { setEditTarget(t); setShowModal(true) }}
              onClone={() => handleClone(t)}
              onDelete={() => handleDelete(t)}
            />
          ))}
        </div>

        {/* Nou tipus */}
        <button
          onClick={() => { setEditTarget(null); setShowModal(true) }}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '8px 14px', borderRadius: 6, cursor: 'pointer',
            background: '#fff', color: '#868685',
            border: '1px dashed #e0d5c5',
            fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = '#c27a2a'
            e.currentTarget.style.color = '#c27a2a'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = '#e0d5c5'
            e.currentTarget.style.color = '#868685'
          }}
        >
          + Nou tipus de prenda
        </button>
      </div>

      {showModal && (
        <GarmentTypeModal
          tipus={editTarget}
          grup={grupActiu}
          authHeaders={authHeaders}
          onSave={handleSaved}
          onError={(text) => setMsg({ type: 'error', text })}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}

function GarmentTypeCard({ tipus, nom, isSelected, onSelect, onEdit, onClone, onDelete }) {
  const borderColor = isSelected ? '#c27a2a' : '#e0d5c5'
  const background = isSelected ? '#fdf6ee' : '#fff'
  return (
    <div
      style={{
        border: `1px solid ${borderColor}`,
        borderRadius: 8, padding: '12px 14px',
        background, cursor: 'pointer',
        display: 'flex', flexDirection: 'column', gap: 8,
        transition: 'border-color .15s, background .15s',
      }}
    >
      <div onClick={onSelect} style={{ flex: 1 }}>
        <p style={{ fontSize: 13, fontWeight: 500, color: '#1d1d1b', margin: 0, lineHeight: 1.3 }}>
          {nom}
        </p>
        {tipus.codi_client && (
          <p style={{ fontSize: 10, color: '#868685', margin: '2px 0 0' }}>{tipus.codi_client}</p>
        )}
        <span style={{
          display: 'inline-block', marginTop: 6,
          fontSize: 9, padding: '2px 6px', borderRadius: 3,
          fontWeight: 600, letterSpacing: '.08em',
          background: tipus.is_system ? '#f5f0ea' : '#f0f9f0',
          color: tipus.is_system ? '#868685' : '#3b6d11',
          border: `0.5px solid ${tipus.is_system ? '#e0d5c5' : '#c0dd97'}`,
        }}>
          {tipus.is_system ? 'SYSTEM' : 'USER'}
        </span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
        <ActionBtn onClick={onSelect} label="Veure" primary />
        <ActionBtn onClick={onClone} label="Clonar" />
        {!tipus.is_system && (
          <>
            <ActionBtn onClick={onEdit} label="Editar" />
            <ActionBtn onClick={onDelete} label="Esborrar" danger />
          </>
        )}
      </div>
    </div>
  )
}

function ActionBtn({ onClick, label, danger = false, primary = false }) {
  const palette = danger
    ? { fg: '#a32d2d', bg: '#fff', border: '#f0c0c0', bgHover: '#fff0f0' }
    : primary
      ? { fg: '#c27a2a', bg: '#fdf6ee', border: '#c27a2a', bgHover: '#f5e6d0' }
      : { fg: '#868685', bg: '#fff', border: '#e0d5c5', bgHover: '#fdf9f5' }
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick() }}
      style={{
        fontSize: 10, padding: '3px 8px', borderRadius: 3, cursor: 'pointer',
        background: palette.bg, color: palette.fg,
        border: `0.5px solid ${palette.border}`,
        fontFamily: 'IBM Plex Mono, monospace',
      }}
      onMouseEnter={e => e.currentTarget.style.background = palette.bgHover}
      onMouseLeave={e => e.currentTarget.style.background = palette.bg}
    >
      {label}
    </button>
  )
}

function GarmentTypeModal({ tipus, grup, authHeaders, onSave, onError, onClose }) {
  const isEdit = !!tipus?.id && !String(tipus.id).startsWith('mock-')
  const [form, setForm] = useState({
    codi_client: tipus?.codi_client || '',
    nom_client:  tipus?.nom_client  || tipus?.nom_en || '',
    nom_en:      tipus?.nom_en      || '',
    nom_ca:      tipus?.nom_ca      || tipus?.nom_cat || '',
    nom_es:      tipus?.nom_es      || '',
    grup:        tipus?.grup        || grup,
    actiu:       tipus?.actiu       ?? true,
    is_system:   false,
  })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async () => {
    if (!form.codi_client.trim()) { onError('Codi obligatori'); return }
    if (!form.nom_en.trim() && !form.nom_client.trim()) { onError('Cal almenys un nom (EN o client)'); return }

    setSaving(true)
    const url = isEdit
      ? `${API}/api/v1/garment-types/${tipus.id}/`
      : `${API}/api/v1/garment-types/`
    const method = isEdit ? 'PATCH' : 'POST'

    // Si no s'ha posat nom_client, derivar-lo del nom_en
    const payload = { ...form, nom_client: form.nom_client.trim() || form.nom_en.trim() }

    try {
      const res = await fetch(url, {
        method,
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        const saved = await res.json()
        onSave(saved)
      } else if (res.status === 405) {
        onError('Backend és ReadOnly per a GarmentType — desa local només. TODO: convertir a ModelViewSet.')
        // Fallback: create locally for the demo (synthetic id)
        const localId = 'local-' + Date.now()
        onSave({ ...payload, id: isEdit ? tipus.id : localId })
      } else {
        const detail = await res.json().catch(() => ({}))
        onError(`Error ${res.status}: ${JSON.stringify(detail).slice(0, 120)}`)
      }
    } catch (e) {
      onError(String(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 50,
        background: 'rgba(0,0,0,.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 12, padding: 24,
          width: '100%', maxWidth: 440,
          fontFamily: 'IBM Plex Mono, monospace',
          boxShadow: '0 10px 40px rgba(0,0,0,.18)',
        }}
      >
        <h2 style={{ fontSize: 15, fontWeight: 600, margin: '0 0 16px', color: '#1d1d1b' }}>
          {isEdit ? 'Editar tipus de prenda' : 'Nou tipus de prenda'}
        </h2>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <ModalField label="Codi *" value={form.codi_client} onChange={v => setForm(f => ({ ...f, codi_client: v.toUpperCase() }))} />
          <ModalField label="Nom EN" value={form.nom_en} onChange={v => setForm(f => ({ ...f, nom_en: v }))} />
          <ModalField label="Nom CAT" value={form.nom_ca} onChange={v => setForm(f => ({ ...f, nom_ca: v }))} />
          <ModalField label="Nom ES" value={form.nom_es} onChange={v => setForm(f => ({ ...f, nom_es: v }))} />
          <ModalField label="Grup" value={form.grup} onChange={v => setForm(f => ({ ...f, grup: v }))} />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px', borderRadius: 6, cursor: 'pointer',
              background: '#fff', color: '#868685',
              border: '0.5px solid #e0d5c5',
              fontFamily: 'IBM Plex Mono, monospace', fontSize: 11,
            }}
          >Cancel·lar</button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            style={{
              padding: '8px 16px', borderRadius: 6,
              cursor: saving ? 'not-allowed' : 'pointer',
              background: '#c27a2a', color: '#fff',
              border: 'none', opacity: saving ? 0.6 : 1,
              fontFamily: 'IBM Plex Mono, monospace', fontSize: 11, fontWeight: 600,
            }}
          >{saving ? 'Guardant...' : (isEdit ? 'Guardar' : 'Crear')}</button>
        </div>
      </div>
    </div>
  )
}

function ModalField({ label, value, onChange }) {
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: 10, color: '#868685', fontWeight: 500 }}>{label}</span>
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        style={{
          background: '#fff',
          border: '0.5px solid #e4e4e2',
          borderRadius: 6,
          padding: '8px 10px',
          fontSize: 12,
          fontFamily: 'IBM Plex Mono, monospace',
          outline: 'none',
        }}
        onFocus={e => e.currentTarget.style.borderColor = '#c27a2a'}
        onBlur={e => e.currentTarget.style.borderColor = '#e4e4e2'}
      />
    </label>
  )
}
