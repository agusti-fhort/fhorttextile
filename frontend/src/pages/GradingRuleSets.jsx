import { useState, useEffect, useMemo } from 'react'
import useAuthStore from '../store/auth'

const API = import.meta.env.VITE_API_URL || ''

// ── Constants ────────────────────────────────────────────────────────────────
const TARGETS = [
  { codi: 'WOMAN',         nom_en: 'Woman',         nom_ca: 'Dona' },
  { codi: 'MAN',           nom_en: 'Man',           nom_ca: 'Home' },
  { codi: 'UNISEX_ADULT',  nom_en: 'Unisex Adult',  nom_ca: 'Unisex adult' },
  { codi: 'BABY_GIRL',     nom_en: 'Baby Girl',     nom_ca: 'Nadó nena' },
  { codi: 'BABY_BOY',      nom_en: 'Baby Boy',      nom_ca: 'Nadó nen' },
  { codi: 'BABY_UNISEX',   nom_en: 'Baby Unisex',   nom_ca: 'Nadó unisex' },
  { codi: 'TODDLER_GIRL',  nom_en: 'Toddler Girl',  nom_ca: 'Nena toddler' },
  { codi: 'TODDLER_BOY',   nom_en: 'Toddler Boy',   nom_ca: 'Nen toddler' },
  { codi: 'GIRL',          nom_en: 'Girl',          nom_ca: 'Nena' },
  { codi: 'BOY',           nom_en: 'Boy',           nom_ca: 'Nen' },
  { codi: 'TEEN_GIRL',     nom_en: 'Teen Girl',     nom_ca: 'Adolescent nena' },
  { codi: 'TEEN_BOY',      nom_en: 'Teen Boy',      nom_ca: 'Adolescent nen' },
  { codi: 'MATERNITY',     nom_en: 'Maternity',     nom_ca: 'Maternitat' },
]

const CONSTRUCTIONS = [
  { codi: 'WOVEN',        nom_en: 'Woven',        nom_ca: 'Teixit pla' },
  { codi: 'KNIT',         nom_en: 'Knit',         nom_ca: 'Punt jersey' },
  { codi: 'STRETCH_KNIT', nom_en: 'Stretch Knit', nom_ca: 'Punt elàstic' },
  { codi: 'TECHNICAL',    nom_en: 'Technical',    nom_ca: 'Tècnic' },
]

const FITS = [
  { codi: 'REGULAR',   nom_en: 'Regular',   nom_ca: 'Regular' },
  { codi: 'SLIM',      nom_en: 'Slim',      nom_ca: 'Ajustat' },
  { codi: 'RELAXED',   nom_en: 'Relaxed',   nom_ca: 'Relaxat' },
  { codi: 'OVERSIZED', nom_en: 'Oversized', nom_ca: 'Oversize' },
  { codi: 'FLARED',    nom_en: 'Flared',    nom_ca: 'Evasé' },
  { codi: 'BODYCON',   nom_en: 'Bodycon',   nom_ca: 'Bodycon' },
  { codi: 'ATHLETIC',  nom_en: 'Athletic',  nom_ca: 'Esportiu' },
  { codi: 'STRAIGHT',  nom_en: 'Straight',  nom_ca: 'Recte' },
  { codi: 'TAPERED',   nom_en: 'Tapered',   nom_ca: 'Cònic' },
  { codi: 'CUSTOM',    nom_en: 'Custom',    nom_ca: 'Personalitzat' },
]

const LOGICA_COLORS = {
  LINEAR:  { bg: '#eef4fc', color: '#2a5a8a', label: 'LINEAR' },
  FIXED:   { bg: '#f5f0ea', color: '#868685', label: 'FIXED' },
  STEPPED: { bg: '#fdf6ee', color: '#c27a2a', label: 'STEPPED' },
}

// TODO(backend): GradingRuleSetSerializer retorna target/construction/fit_type
// com a IDs (ForeignKey) i no com a codis. Sense endpoints /api/v1/targets/,
// /api/v1/construction-types/ ni /api/v1/fit-types/, inferim el mapping
// id→codi a partir del camp `codi_sistema` o `nom` del propi RuleSet
// (patró 'EU_WOVEN_WOMAN_REGULAR' conté els codis textuals).
function inferCodeMappings(ruleSets) {
  const targetById = {}, constructionById = {}, fitById = {}
  const targetCodes = TARGETS.map(t => t.codi).sort((a, b) => b.length - a.length)
  const constructionCodes = CONSTRUCTIONS.map(c => c.codi).sort((a, b) => b.length - a.length)
  const fitCodes = FITS.map(f => f.codi).sort((a, b) => b.length - a.length)

  for (const rs of ruleSets) {
    const ref = ((rs.codi_sistema || '') + ' ' + (rs.nom || '')).toUpperCase()
    if (rs.target != null && targetById[rs.target] === undefined) {
      const found = targetCodes.find(c => ref.includes(c) || ref.includes(c.replace(/_/g, ' ')))
      if (found) targetById[rs.target] = found
    }
    if (rs.construction != null && constructionById[rs.construction] === undefined) {
      const found = constructionCodes.find(c => ref.includes(c) || ref.includes(c.replace(/_/g, ' ')))
      if (found) constructionById[rs.construction] = found
    }
    if (rs.fit_type != null && fitById[rs.fit_type] === undefined) {
      const found = fitCodes.find(c => ref.includes(c) || ref.includes(c.replace(/_/g, ' ')))
      if (found) fitById[rs.fit_type] = found
    }
  }
  return { targetById, constructionById, fitById }
}

export default function GradingRuleSets() {
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')

  const [allRuleSets, setAllRuleSets] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedTarget, setSelectedTarget] = useState(null)
  const [selectedConstruction, setSelectedConstruction] = useState(null)
  const [selectedFit, setSelectedFit] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [msg, setMsg] = useState(null)
  const lang = 'ca'

  const authHeaders = () => token ? { Authorization: `Bearer ${token}` } : {}

  const loadRuleSets = () => {
    setLoading(true)
    fetch(`${API}/api/v1/grading-rule-sets/?page_size=200`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => setAllRuleSets(d.results || (Array.isArray(d) ? d : [])))
      .catch(() => setAllRuleSets([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadRuleSets() }, [token])

  // Mapping id → codi inferit
  const { targetById, constructionById, fitById } = useMemo(
    () => inferCodeMappings(allRuleSets),
    [allRuleSets]
  )

  // RuleSets enriquits amb codis textuals
  const enrichedRuleSets = useMemo(() => allRuleSets.map(rs => ({
    ...rs,
    target_codi: rs.target != null ? targetById[rs.target] : null,
    construction_codi: rs.construction != null ? constructionById[rs.construction] : null,
    fit_type_codi: rs.fit_type != null ? fitById[rs.fit_type] : null,
  })), [allRuleSets, targetById, constructionById, fitById])

  // Targets que apareixen als RuleSets (inclou els sense target)
  const availableTargetCodes = useMemo(() => {
    const set = new Set()
    for (const rs of enrichedRuleSets) {
      if (rs.target_codi) set.add(rs.target_codi)
    }
    return set
  }, [enrichedRuleSets])

  // Construccions disponibles per al target seleccionat
  const availableConstructions = useMemo(() => {
    if (!selectedTarget) return []
    const set = new Set(
      enrichedRuleSets
        .filter(rs => !rs.target_codi || rs.target_codi === selectedTarget)
        .map(rs => rs.construction_codi)
        .filter(Boolean)
    )
    return CONSTRUCTIONS.filter(c => set.has(c.codi))
  }, [enrichedRuleSets, selectedTarget])

  // Fits disponibles per target + construction
  const availableFits = useMemo(() => {
    if (!selectedTarget || !selectedConstruction) return []
    const set = new Set(
      enrichedRuleSets
        .filter(rs =>
          (!rs.target_codi || rs.target_codi === selectedTarget) &&
          (!rs.construction_codi || rs.construction_codi === selectedConstruction)
        )
        .map(rs => rs.fit_type_codi)
        .filter(Boolean)
    )
    return FITS.filter(f => set.has(f.codi))
  }, [enrichedRuleSets, selectedTarget, selectedConstruction])

  // RuleSets que coincideixen amb la selecció
  const matchingRuleSets = useMemo(() => {
    if (!selectedTarget) return []
    return enrichedRuleSets.filter(rs => {
      const tMatch = !rs.target_codi || rs.target_codi === selectedTarget
      const cMatch = !selectedConstruction || !rs.construction_codi || rs.construction_codi === selectedConstruction
      const fMatch = !selectedFit || !rs.fit_type_codi || rs.fit_type_codi === selectedFit
      return tMatch && cMatch && fMatch
    })
  }, [enrichedRuleSets, selectedTarget, selectedConstruction, selectedFit])

  const nom = (obj) => lang === 'ca' ? obj.nom_ca : obj.nom_en

  const totalRegles = useMemo(
    () => allRuleSets.reduce((s, rs) => s + (rs.regles_count ?? rs.regles?.length ?? 0), 0),
    [allRuleSets]
  )

  const handleDelete = async (rs) => {
    if (rs.is_system_default) {
      setMsg({ type: 'error', text: 'No es pot esborrar un RuleSet de sistema.' })
      return
    }
    if (!confirm(`Esborrar "${rs.nom}"?`)) return
    try {
      const r = await fetch(`${API}/api/v1/grading-rule-sets/${rs.id}/`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (r.ok || r.status === 204) {
        setAllRuleSets(prev => prev.filter(x => x.id !== rs.id))
        setMsg({ type: 'ok', text: 'RuleSet esborrat.' })
      } else {
        setMsg({ type: 'error', text: `Error ${r.status} esborrant.` })
      }
    } catch (e) {
      setMsg({ type: 'error', text: String(e) })
    }
  }

  const handleSaved = (saved) => {
    setAllRuleSets(prev => {
      const idx = prev.findIndex(r => r.id === saved.id)
      if (idx >= 0) { const n = [...prev]; n[idx] = saved; return n }
      return [...prev, saved]
    })
    setShowModal(false)
    setMsg({ type: 'ok', text: editTarget?.id ? 'RuleSet actualitzat.' : 'RuleSet creat.' })
  }

  if (loading) return (
    <div style={{ padding: '2rem', fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, color: 'var(--text-muted, #868685)' }}>
      Carregant regles de grading...
    </div>
  )

  return (
    <div style={{ padding: '0', fontFamily: 'IBM Plex Sans, sans-serif', maxWidth: 1200 }}>

      {/* Títol */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '1.5rem', gap: 12,
      }}>
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 500, marginBottom: 4 }}>Grading Rules</h1>
          <p style={{ fontSize: 12, color: 'var(--gray, #868685)', fontWeight: 300 }}>
            {allRuleSets.length} conjunts de regles · {totalRegles} regles totals
          </p>
        </div>
        <button
          onClick={() => { setEditTarget(null); setShowModal(true) }}
          style={btnPrimary}
        >
          + Nou RuleSet
        </button>
      </div>

      {/* Missatge */}
      {msg && (
        <div style={{
          padding: '8px 12px', borderRadius: 6, fontSize: 11, marginBottom: 12,
          background: msg.type === 'ok' ? '#f0f9f0' : '#fff0f0',
          border: `0.5px solid ${msg.type === 'ok' ? '#c0dd97' : '#f09595'}`,
          color: msg.type === 'ok' ? '#3b6d11' : '#a32d2d',
          display: 'flex', justifyContent: 'space-between',
        }}>
          <span>{msg.text}</span>
          <button onClick={() => setMsg(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 14 }}>×</button>
        </div>
      )}

      {/* Pas 1: Target */}
      <StepSection number={1} title="TARGET — PER A QUI ÉS LA PEÇA?">
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {TARGETS.map(t => (
            <TargetCard
              key={t.codi}
              target={t}
              selected={selectedTarget === t.codi}
              available={availableTargetCodes.has(t.codi)}
              onClick={() => {
                setSelectedTarget(t.codi)
                setSelectedConstruction(null)
                setSelectedFit(null)
              }}
            />
          ))}
        </div>
      </StepSection>

      {/* Pas 2: Construction */}
      {selectedTarget && availableConstructions.length > 0 && (
        <StepSection number={2} title="TIPUS DE CONSTRUCCIÓ">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {availableConstructions.map(c => (
              <SelectionButton
                key={c.codi}
                item={c}
                selected={selectedConstruction === c.codi}
                onClick={() => { setSelectedConstruction(c.codi); setSelectedFit(null) }}
              />
            ))}
          </div>
        </StepSection>
      )}

      {/* Pas 3: Fit */}
      {selectedConstruction && availableFits.length > 0 && (
        <StepSection number={3} title="FIT TYPE">
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {availableFits.map(f => (
              <SelectionButton
                key={f.codi}
                item={f}
                selected={selectedFit === f.codi}
                onClick={() => setSelectedFit(f.codi)}
              />
            ))}
          </div>
        </StepSection>
      )}

      {/* Fitxes RuleSet */}
      {matchingRuleSets.length > 0 && (
        <div style={{ marginTop: 24 }}>
          {matchingRuleSets.map(rs => (
            <RuleSetCard
              key={rs.id}
              rs={rs}
              onClone={() => {
                setEditTarget({
                  ...rs, id: null,
                  nom: rs.nom + ' (còpia)',
                  codi_sistema: (rs.codi_sistema || '') + '_COPY',
                  is_system_default: false,
                })
                setShowModal(true)
              }}
              onEdit={() => { setEditTarget(rs); setShowModal(true) }}
              onDelete={() => handleDelete(rs)}
            />
          ))}
        </div>
      )}

      {/* Missatge si no hi ha match */}
      {selectedFit && matchingRuleSets.length === 0 && (
        <div style={{
          marginTop: 24, padding: '2rem', border: '1px dashed #e0d5c5',
          borderRadius: 8, textAlign: 'center', color: 'var(--gray, #868685)', fontSize: 12,
        }}>
          No hi ha cap RuleSet per a aquesta combinació.
          <button
            onClick={() => { setEditTarget(null); setShowModal(true) }}
            style={{ ...btnPrimary, display: 'block', margin: '0.75rem auto 0' }}
          >
            + Crear RuleSet per a {selectedTarget} · {selectedConstruction} · {selectedFit}
          </button>
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <RuleSetModal
          rs={editTarget}
          defaultTarget={selectedTarget}
          defaultConstruction={selectedConstruction}
          defaultFit={selectedFit}
          authHeaders={authHeaders}
          onSave={handleSaved}
          onError={(text) => setMsg({ type: 'error', text })}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  )
}

// ── StepSection ─────────────────────────────────────────────────────────────
function StepSection({ number, title, children }) {
  return (
    <div style={{ marginBottom: '1.4rem' }}>
      <p style={{
        fontSize: 10, fontWeight: 700, color: '#c27a2a',
        letterSpacing: '0.08em', textTransform: 'uppercase',
        margin: '0 0 10px',
        fontFamily: 'IBM Plex Mono, monospace',
      }}>
        {number} · {title}
      </p>
      {children}
    </div>
  )
}

// ── TargetCard ──────────────────────────────────────────────────────────────
// Mateix patró que Size Library: nom_en principal (gran), nom_ca secundari (petit gris).
function TargetCard({ target, selected, available, onClick }) {
  return (
    <div
      onClick={available ? onClick : undefined}
      style={{
        border: `1px solid ${selected ? '#c27a2a' : '#e0d5c5'}`,
        borderRadius: 8,
        padding: '8px 14px',
        cursor: available ? 'pointer' : 'not-allowed',
        background: selected ? '#fdf6ee' : available ? '#fff' : '#f8f8f8',
        opacity: available ? 1 : 0.4,
        minWidth: 100, textAlign: 'center',
        transition: 'all .15s',
        fontFamily: 'IBM Plex Mono, monospace',
      }}
    >
      <div style={{
        fontSize: 12,
        fontWeight: selected ? 600 : 400,
        color: selected ? '#c27a2a' : '#1d1d1b',
      }}>
        {target.nom_en}
      </div>
      <div style={{ fontSize: 9, color: '#868685', marginTop: 2 }}>{target.nom_ca}</div>
    </div>
  )
}

// ── SelectionButton ─────────────────────────────────────────────────────────
// Mateix patró que Size Library: nom_en principal, nom_ca petit gris al costat.
function SelectionButton({ item, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        border: `1px solid ${selected ? '#c27a2a' : '#e0d5c5'}`,
        borderRadius: 6,
        padding: '6px 14px',
        background: selected ? '#fdf6ee' : '#fff',
        color: selected ? '#c27a2a' : '#1d1d1b',
        fontWeight: selected ? 600 : 400,
        fontSize: 11,
        cursor: 'pointer',
        fontFamily: 'IBM Plex Mono, monospace',
        transition: 'all .15s',
      }}
    >
      {item.nom_en}
      {item.nom_ca && (
        <span style={{ fontSize: 10, color: '#868685', marginLeft: 6, fontWeight: 400 }}>
          {item.nom_ca}
        </span>
      )}
    </button>
  )
}

// ── RuleSetCard ─────────────────────────────────────────────────────────────
function RuleSetCard({ rs, onClone, onEdit, onDelete }) {
  const [expanded, setExpanded] = useState(true)
  const regles = rs.regles || []
  const reglesCount = rs.regles_count ?? regles.length
  const aboveXlCount = regles.filter(r => r.valors_step?.above_xl != null).length

  return (
    <div style={{
      border: '1px solid #e0d5c5', borderRadius: 10,
      marginBottom: 16, overflow: 'hidden', background: '#fff',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      <div style={{
        padding: '12px 18px', background: '#fafaf8',
        borderBottom: expanded ? '1px solid #e0d5c5' : 'none',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: 14, flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
          <button
            onClick={() => setExpanded(e => !e)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 12, color: '#868685', padding: 0, lineHeight: 1,
            }}
            aria-label={expanded ? 'Replegar' : 'Desplegar'}
          >
            {expanded ? '▾' : '▸'}
          </button>
          <div style={{ minWidth: 0 }}>
            <div style={{
              fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600,
              fontSize: 13, color: '#1d1d1b',
            }}>
              {rs.nom}
            </div>
            <div style={{
              fontSize: 11, color: '#868685', marginTop: 2,
              display: 'flex', gap: 10, flexWrap: 'wrap',
            }}>
              {rs.target_codi && <span>Target: <strong>{rs.target_codi}</strong></span>}
              {rs.construction_codi && <span>Construction: <strong>{rs.construction_codi}</strong></span>}
              {rs.fit_type_codi && <span>Fit: <strong>{rs.fit_type_codi}</strong></span>}
              {rs.size_system_nom && <span>Size System: <strong>{rs.size_system_nom}</strong></span>}
              {rs.codi_sistema && <span style={{ fontFamily: 'IBM Plex Mono, monospace' }}>{rs.codi_sistema}</span>}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Pill bg="#eef4fc" color="#2a5a8a">{reglesCount} regles</Pill>
          {aboveXlCount > 0 && <Pill bg="#fdf6ee" color="#c27a2a">{aboveXlCount} Δ&gt;XL</Pill>}
          <Pill
            bg={rs.is_system_default ? '#f5f0ea' : '#f0f9f0'}
            color={rs.is_system_default ? '#868685' : '#3b6d11'}
          >{rs.is_system_default ? 'Sistema' : 'Personalitzat'}</Pill>
          {rs.actiu && <Pill bg="#f0f9f0" color="#3b6d11">Actiu</Pill>}
          <ActionBtn onClick={onClone} label="Clonar" />
          {!rs.is_system_default && (
            <>
              <ActionBtn onClick={onEdit} label="Editar" />
              <ActionBtn onClick={onDelete} label="Esborrar" danger />
            </>
          )}
        </div>
      </div>

      {/* Taula */}
      {expanded && regles.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#fafaf8' }}>
                {['Codi', 'Nom POM', 'Lògica', 'Δ/talla', 'Δ>XL', 'Talla base', 'Valor base'].map((h, i) => (
                  <th key={h} style={{
                    padding: '8px 12px',
                    textAlign: i >= 3 ? 'right' : 'left',
                    fontWeight: 600, color: '#868685', fontSize: 10,
                    textTransform: 'uppercase', letterSpacing: '0.06em',
                    borderBottom: '0.5px solid #e0d5c5',
                    fontFamily: 'IBM Plex Mono, monospace',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {regles.map((r, i) => {
                const logica = LOGICA_COLORS[r.logica] || LOGICA_COLORS.FIXED
                const aboveXl = r.valors_step?.above_xl
                const isKey = r.increment > 0 && r.logica === 'LINEAR'
                return (
                  <tr key={r.id} style={{ background: i % 2 === 0 ? '#fff' : '#fafaf8' }}>
                    <td style={{
                      padding: '7px 12px',
                      fontFamily: 'IBM Plex Mono, monospace',
                      fontSize: 11, color: '#c27a2a',
                      borderBottom: '0.5px solid #f0eee9',
                    }}>{r.pom_abbreviation || r.pom_codi}</td>
                    <td style={{
                      padding: '7px 12px', color: '#1d1d1b',
                      borderBottom: '0.5px solid #f0eee9',
                    }}>
                      {r.pom_nom}
                      {isKey && (
                        <span style={{
                          marginLeft: 6, fontSize: 9, padding: '2px 5px', borderRadius: 3,
                          background: '#fdf6ee', color: '#c27a2a',
                          border: '0.5px solid #e0c8a0', fontWeight: 600,
                        }}>KEY</span>
                      )}
                    </td>
                    <td style={{ padding: '7px 12px', borderBottom: '0.5px solid #f0eee9' }}>
                      <span style={{
                        fontSize: 10, padding: '2px 6px', borderRadius: 3,
                        background: logica.bg, color: logica.color,
                        fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600,
                      }}>{r.logica}</span>
                    </td>
                    <td style={{
                      padding: '7px 12px', textAlign: 'right',
                      fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600,
                      color: r.increment > 0 ? '#2a5a8a' : '#868685',
                      borderBottom: '0.5px solid #f0eee9',
                    }}>
                      {r.increment > 0 ? `+${r.increment}` : r.increment === 0 ? '—' : r.increment}
                      {r.increment !== 0 ? ' cm' : ''}
                    </td>
                    <td style={{
                      padding: '7px 12px', textAlign: 'right',
                      fontFamily: 'IBM Plex Mono, monospace',
                      color: aboveXl ? '#c27a2a' : '#c0c0c0',
                      borderBottom: '0.5px solid #f0eee9',
                    }}>
                      {aboveXl != null ? `+${aboveXl} cm` : '—'}
                    </td>
                    <td style={{
                      padding: '7px 12px', textAlign: 'right',
                      fontFamily: 'IBM Plex Mono, monospace',
                      color: '#868685', fontSize: 11,
                      borderBottom: '0.5px solid #f0eee9',
                    }}>{r.talla_base_etiqueta || '—'}</td>
                    <td style={{
                      padding: '7px 12px', textAlign: 'right',
                      fontFamily: 'IBM Plex Mono, monospace',
                      color: '#868685',
                      borderBottom: '0.5px solid #f0eee9',
                    }}>{r.valor_base > 0 ? `${r.valor_base} cm` : '—'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {expanded && regles.length === 0 && (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: '#bbb', fontSize: 12 }}>
          Cap regla definida per a aquest RuleSet.
        </div>
      )}
    </div>
  )
}

function Pill({ bg, color, children }) {
  return (
    <span style={{
      fontSize: 10, padding: '3px 7px', borderRadius: 4,
      background: bg, color,
      fontFamily: 'IBM Plex Mono, monospace', fontWeight: 600,
      letterSpacing: '.04em', whiteSpace: 'nowrap',
    }}>{children}</span>
  )
}

function ActionBtn({ onClick, label, danger = false }) {
  const palette = danger
    ? { fg: '#a32d2d', bg: '#fff', border: '#f0c0c0', bgHover: '#fff0f0' }
    : { fg: '#868685', bg: '#fff', border: '#e0d5c5', bgHover: '#fdf9f5' }
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick() }}
      style={{
        fontSize: 10, padding: '4px 9px', borderRadius: 4, cursor: 'pointer',
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

// ── RuleSetModal ────────────────────────────────────────────────────────────
function RuleSetModal({ rs, defaultTarget, defaultConstruction, defaultFit, authHeaders, onSave, onError, onClose }) {
  const isEdit = !!rs?.id
  const [form, setForm] = useState({
    nom:          rs?.nom          || '',
    codi_sistema: rs?.codi_sistema || '',
    // Target/Construction/Fit no es poden enviar directament com a codi
    // perquè el backend espera IDs. Mantenim els codis al form per a la UI
    // i (TODO) caldria endpoint per resoldre codi→id. De moment, els enviem
    // només si el RuleSet en edició ja en té (passem l'ID original).
    target:       rs?.target       ?? null,
    construction: rs?.construction ?? null,
    fit_type:     rs?.fit_type     ?? null,
    target_codi_form:       rs?.target_codi       || defaultTarget       || '',
    construction_codi_form: rs?.construction_codi || defaultConstruction || '',
    fit_type_codi_form:     rs?.fit_type_codi     || defaultFit          || '',
    actiu: rs?.actiu ?? true,
  })
  const [saving, setSaving] = useState(false)

  const handleSubmit = async () => {
    if (!form.nom.trim()) { onError('Nom obligatori'); return }
    setSaving(true)

    const url = isEdit
      ? `${API}/api/v1/grading-rule-sets/${rs.id}/`
      : `${API}/api/v1/grading-rule-sets/`
    const method = isEdit ? 'PATCH' : 'POST'

    const payload = {
      nom: form.nom.trim(),
      codi_sistema: form.codi_sistema.trim(),
      actiu: form.actiu,
      // TODO(backend): cal endpoint /api/v1/targets/, construction-types/,
      // fit-types/ per poder convertir codi → id des del frontend en cas
      // de creació nova. Mentrestant, només enviem els FKs si vénen de
      // l'objecte original (edit/clone) o si no s'han modificat.
    }
    if (form.target != null) payload.target = form.target
    if (form.construction != null) payload.construction = form.construction
    if (form.fit_type != null) payload.fit_type = form.fit_type

    try {
      const res = await fetch(url, {
        method,
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        const saved = await res.json()
        onSave(saved)
      } else {
        const detail = await res.json().catch(() => ({}))
        onError(`Error ${res.status}: ${JSON.stringify(detail).slice(0, 150)}`)
      }
    } catch (e) {
      onError(String(e))
    } finally {
      setSaving(false)
    }
  }

  const F = ({ label, field, options, disabled }) => (
    <div style={{ marginBottom: 12 }}>
      <label style={{
        fontSize: 10, fontWeight: 600, color: '#868685',
        display: 'block', marginBottom: 4,
        fontFamily: 'IBM Plex Mono, monospace',
      }}>{label}</label>
      {options ? (
        <select
          value={form[field] || ''}
          disabled={disabled}
          onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
          style={modalInput}
        >
          <option value="">— Selecciona —</option>
          {options.map(o => <option key={o.codi} value={o.codi}>{o.nom_en}</option>)}
        </select>
      ) : (
        <input
          type="text"
          value={form[field] || ''}
          onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
          style={modalInput}
        />
      )}
    </div>
  )

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
      }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff', borderRadius: 12, padding: 24,
          width: '100%', maxWidth: 480,
          boxShadow: '0 10px 40px rgba(0,0,0,0.18)',
          fontFamily: 'IBM Plex Mono, monospace',
        }}
      >
        <h2 style={{ margin: '0 0 16px', fontSize: 15, fontWeight: 600, color: '#1d1d1b' }}>
          {isEdit ? 'Editar RuleSet' : 'Nou RuleSet de Grading'}
        </h2>
        <F label="Nom" field="nom" />
        <F label="Codi sistema" field="codi_sistema" />
        <F label="Target (només referència)" field="target_codi_form" options={TARGETS} disabled />
        <F label="Construction (només referència)" field="construction_codi_form" options={CONSTRUCTIONS} disabled />
        <F label="Fit Type (només referència)" field="fit_type_codi_form" options={FITS} disabled />
        <p style={{ fontSize: 10, color: '#c27a2a', margin: '4px 0 12px' }}>
          Nota: Target/Construction/Fit no es poden modificar des d'aquí — backend espera IDs i no hi ha endpoint per resoldre codi→id.
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
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
            style={{ ...btnPrimary, opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
          >
            {saving ? 'Guardant...' : (isEdit ? 'Guardar' : 'Crear')}
          </button>
        </div>
      </div>
    </div>
  )
}

const btnPrimary = {
  background: '#c27a2a', color: '#fff',
  border: 'none', borderRadius: 6,
  padding: '8px 14px', fontSize: 11, fontWeight: 600,
  cursor: 'pointer', fontFamily: 'IBM Plex Mono, monospace',
}

const modalInput = {
  width: '100%',
  border: '0.5px solid #e0d5c5',
  borderRadius: 6,
  padding: '8px 10px',
  fontSize: 12,
  fontFamily: 'IBM Plex Mono, monospace',
  outline: 'none',
  boxSizing: 'border-box',
  background: '#fff',
}
