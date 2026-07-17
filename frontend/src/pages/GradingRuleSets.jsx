import { useState, useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import useAuthStore from '../store/auth'

const API = import.meta.env.VITE_API_URL || ''

// ── Constants ────────────────────────────────────────────────────────────────
// Enums de referència (vocabulari controlat). codi = id (mai traduït); nom_en/nom_ca/nom_es =
// display bilingüe (anglès primari + nom localitzat per i18n.language). Convenció de sector.
const TARGETS = [
  { codi: 'WOMAN',         nom_en: 'Woman',         nom_ca: 'Dona',            nom_es: 'Mujer' },
  { codi: 'MAN',           nom_en: 'Man',           nom_ca: 'Home',            nom_es: 'Hombre' },
  { codi: 'UNISEX_ADULT',  nom_en: 'Unisex Adult',  nom_ca: 'Unisex adult',    nom_es: 'Unisex adulto' },
  { codi: 'BABY_GIRL',     nom_en: 'Baby Girl',     nom_ca: 'Nadó nena',       nom_es: 'Bebé niña' },
  { codi: 'BABY_BOY',      nom_en: 'Baby Boy',      nom_ca: 'Nadó nen',        nom_es: 'Bebé niño' },
  { codi: 'BABY_UNISEX',   nom_en: 'Baby Unisex',   nom_ca: 'Nadó unisex',     nom_es: 'Bebé unisex' },
  { codi: 'TODDLER_GIRL',  nom_en: 'Toddler Girl',  nom_ca: 'Nena toddler',    nom_es: 'Niña toddler' },
  { codi: 'TODDLER_BOY',   nom_en: 'Toddler Boy',   nom_ca: 'Nen toddler',     nom_es: 'Niño toddler' },
  { codi: 'GIRL',          nom_en: 'Girl',          nom_ca: 'Nena',            nom_es: 'Niña' },
  { codi: 'BOY',           nom_en: 'Boy',           nom_ca: 'Nen',             nom_es: 'Niño' },
  { codi: 'TEEN_GIRL',     nom_en: 'Teen Girl',     nom_ca: 'Adolescent nena', nom_es: 'Adolescente niña' },
  { codi: 'TEEN_BOY',      nom_en: 'Teen Boy',      nom_ca: 'Adolescent nen',  nom_es: 'Adolescente niño' },
  { codi: 'MATERNITY',     nom_en: 'Maternity',     nom_ca: 'Maternitat',      nom_es: 'Maternidad' },
]

const CONSTRUCTIONS = [
  { codi: 'WOVEN',        nom_en: 'Woven',        nom_ca: 'Teixit pla',   nom_es: 'Tejido plano' },
  { codi: 'KNIT',         nom_en: 'Knit',         nom_ca: 'Punt jersey',  nom_es: 'Punto jersey' },
  { codi: 'STRETCH_KNIT', nom_en: 'Stretch Knit', nom_ca: 'Punt elàstic', nom_es: 'Punto elástico' },
  { codi: 'TECHNICAL',    nom_en: 'Technical',    nom_ca: 'Tècnic',       nom_es: 'Técnico' },
]

const FITS = [
  { codi: 'REGULAR',   nom_en: 'Regular',   nom_ca: 'Regular',         nom_es: 'Regular' },
  { codi: 'SLIM',      nom_en: 'Slim',      nom_ca: 'Ajustat',         nom_es: 'Ajustado' },
  { codi: 'RELAXED',   nom_en: 'Relaxed',   nom_ca: 'Relaxat',         nom_es: 'Relajado' },
  { codi: 'OVERSIZED', nom_en: 'Oversized', nom_ca: 'Oversize',        nom_es: 'Oversize' },
  { codi: 'FLARED',    nom_en: 'Flared',    nom_ca: 'Evasé',           nom_es: 'Evasé' },
  { codi: 'BODYCON',   nom_en: 'Bodycon',   nom_ca: 'Bodycon',         nom_es: 'Bodycon' },
  { codi: 'ATHLETIC',  nom_en: 'Athletic',  nom_ca: 'Esportiu',        nom_es: 'Deportivo' },
  { codi: 'STRAIGHT',  nom_en: 'Straight',  nom_ca: 'Recte',           nom_es: 'Recto' },
  { codi: 'TAPERED',   nom_en: 'Tapered',   nom_ca: 'Cònic',           nom_es: 'Cónico' },
  { codi: 'CUSTOM',    nom_en: 'Custom',    nom_ca: 'Personalitzat',   nom_es: 'Personalizado' },
]

const GARMENT_GROUPS = [
  { codi: 'TOPS',        nom_en: 'Tops',        nom_ca: 'Parts superiors', nom_es: 'Partes superiores' },
  { codi: 'BOTTOMS',     nom_en: 'Bottoms',     nom_ca: 'Parts inferiors', nom_es: 'Partes inferiores' },
  { codi: 'DRESSES',     nom_en: 'Dresses',     nom_ca: 'Vestits',         nom_es: 'Vestidos' },
  { codi: 'OUTERWEAR',   nom_en: 'Outerwear',   nom_ca: 'Abrics',          nom_es: 'Abrigos' },
  { codi: 'UNDERWEAR',   nom_en: 'Underwear',   nom_ca: 'Interior',        nom_es: 'Interior' },
  { codi: 'SWIMWEAR',    nom_en: 'Swimwear',    nom_ca: 'Bany',            nom_es: 'Baño' },
  { codi: 'ACCESSORIES', nom_en: 'Accessories', nom_ca: 'Complements',     nom_es: 'Complementos' },
]

// Nom localitzat secundari segons i18n.language (anglès es mostra com a primari a part).
function nomLocal(obj, lang) {
  if (!obj) return ''
  return lang === 'es' ? (obj.nom_es || obj.nom_en) : lang === 'ca' ? (obj.nom_ca || obj.nom_en) : obj.nom_en
}

// S16-B fix: mapping grup → categories POM rellevants. La taula de regles
// filters POMs by the selected group, showing only those belonging to
// one of these categories (POMGlobal.categoria is a CharField string).
const GROUP_POM_CATEGORIES = {
  TOPS:        ['Upper body', 'Sleeve', 'Collar / Neckline', 'Hem / Finish', 'Knitwear-specific', 'Closure / Detail'],
  BOTTOMS:     ['Lower body', 'Waistband', 'Rise', 'Hem / Finish', 'Closure / Detail'],
  DRESSES:     ['Upper body', 'Sleeve', 'Collar / Neckline', 'Skirt / Dress', 'Hem / Finish', 'Closure / Detail'],
  OUTERWEAR:   ['Upper body', 'Sleeve', 'Collar / Neckline', 'Jacket / Coat', 'Hem / Finish', 'Closure / Detail'],
  UNDERWEAR:   ['Upper body', 'Swimwear-specific', 'Rise', 'Hem / Finish'],
  SWIMWEAR:    ['Upper body', 'Swimwear-specific', 'Rise', 'Closure / Detail'],
  ACCESSORIES: ['Placement', 'Closure / Detail'],
}

const LOGICA_COLORS = {
  LINEAR:  { bg: '#eef4fc', color: '#2a5a8a', label: 'LINEAR' },
  FIXED:   { bg: '#f5f0ea', color: 'var(--text-muted)', label: 'FIXED' },
  STEPPED: { bg: '#fdf6ee', color: 'var(--gold)', label: 'STEPPED' },
}

export default function GradingRuleSets() {
  const { t, i18n } = useTranslation()
  const token = useAuthStore(s => s.token) || localStorage.getItem('access_token')

  const [allRuleSets, setAllRuleSets] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedTarget, setSelectedTarget] = useState(null)
  const [selectedConstruction, setSelectedConstruction] = useState(null)
  const [selectedFit, setSelectedFit] = useState(null)
  const [selectedGarmentGroup, setSelectedGarmentGroup] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [editTarget, setEditTarget] = useState(null)
  const [msg, setMsg] = useState(null)
  // Mapping id → codi de GarmentGroup, per poder filtrar per codi a partir
  // del FK id que retorna el RuleSet (`rs.garment_group`). El serializer no
  // exposes `garment_group_codi`, only the translated name (not usable as a key).
  const [garmentGroupCodiById, setGarmentGroupCodiById] = useState({})
  const lang = (i18n.language || 'ca').slice(0, 2)

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

  // Load the GarmentGroup catalog to resolve id→codi (once).
  useEffect(() => {
    fetch(`${API}/api/v1/garment-groups/?page_size=200`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => {
        const list = d.results || (Array.isArray(d) ? d : [])
        const map = {}
        for (const g of list) map[g.id] = g.codi
        setGarmentGroupCodiById(map)
      })
      .catch(() => setGarmentGroupCodiById({}))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  // El GradingRuleSetSerializer (S16-A) exposa `targets_codis` (array) +
  // construction_codi + fit_type_codi. Usem-los directament; un RuleSet pot
  // apply to multiple targets (e.g. BABY → 3) thanks to the M2M change.
  const enrichedRuleSets = allRuleSets

  // Helpers per matching M2M targets (un RuleSet apareix sota cada target del array).
  const matchesTarget = (rs, target) =>
    !rs.targets_codis?.length || rs.targets_codis.includes(target)

  // Helper per matching garment_group via id→codi map (FK del RuleSet).
  // RuleSets without an assigned garment_group are considered compatible with any
  // group (passes the condition) — acceptable while the current catalog does not
  // have group-specific RuleSets.
  const matchesGarmentGroup = (rs, groupCodi) => {
    if (!rs.garment_group) return true
    const rsGroupCodi = garmentGroupCodiById[rs.garment_group]
    return rsGroupCodi === groupCodi
  }

  // Targets that appear in the RuleSets (extracted from the targets_codis arrays).
  const availableTargetCodes = useMemo(() => {
    const set = new Set()
    for (const rs of enrichedRuleSets) {
      for (const t of (rs.targets_codis || [])) set.add(t)
    }
    return set
  }, [enrichedRuleSets])

  // Construccions disponibles per al target seleccionat
  const availableConstructions = useMemo(() => {
    if (!selectedTarget) return []
    const set = new Set(
      enrichedRuleSets
        .filter(rs => matchesTarget(rs, selectedTarget))
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
          matchesTarget(rs, selectedTarget) &&
          (!rs.construction_codi || rs.construction_codi === selectedConstruction)
        )
        .map(rs => rs.fit_type_codi)
        .filter(Boolean)
    )
    return FITS.filter(f => set.has(f.codi))
  }, [enrichedRuleSets, selectedTarget, selectedConstruction])

  // RuleSets matching the full selection (4 filters).
  // matchingRuleSets is empty until selectedGarmentGroup has a value.
  const matchingRuleSets = useMemo(() => {
    if (!selectedTarget || !selectedConstruction || !selectedFit || !selectedGarmentGroup) return []
    return enrichedRuleSets.filter(rs => {
      const tMatch = matchesTarget(rs, selectedTarget)
      const cMatch = !rs.construction_codi || rs.construction_codi === selectedConstruction
      const fMatch = !rs.fit_type_codi || rs.fit_type_codi === selectedFit
      const gMatch = matchesGarmentGroup(rs, selectedGarmentGroup)
      return tMatch && cMatch && fMatch && gMatch
    })
  }, [enrichedRuleSets, selectedTarget, selectedConstruction, selectedFit, selectedGarmentGroup, garmentGroupCodiById])


  const totalRegles = useMemo(
    () => allRuleSets.reduce((s, rs) => s + (rs.regles_count ?? rs.regles?.length ?? 0), 0),
    [allRuleSets]
  )

  const handleDelete = async (rs, force = false) => {
    if (rs.is_system_default) {
      setMsg({ type: 'error', text: t('grading.err_system_delete') })
      return
    }
    if (!force && !confirm(t('grading.confirm_delete', { name: rs.nom }))) return
    try {
      const r = await fetch(
        `${API}/api/v1/grading-rule-sets/${rs.id}/${force ? '?force=1' : ''}`,
        { method: 'DELETE', headers: authHeaders() },
      )
      if (r.ok || r.status === 204) {
        setAllRuleSets(prev => prev.filter(x => x.id !== rs.id))
        setMsg({ type: 'ok', text: t('grading.deleted') })
      } else if (r.status === 409) {
        // Té perfils i/o models dependents → avís clar (missatge del backend, font única) +
        // cascada controlada si es confirma.
        const d = await r.json().catch(() => ({}))
        if (confirm(d.message || t('grading.confirm_delete_deps'))) {
          return handleDelete(rs, true)
        }
      } else {
        setMsg({ type: 'error', text: t('grading.delete_error', { status: r.status }) })
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
    setMsg({ type: 'ok', text: editTarget?.id ? t('grading.updated') : t('grading.created') })
  }

  if (loading) return (
    <div style={{ padding: '2rem', fontSize: 'var(--fs-body)', color: 'var(--text-muted, #868685)' }}>
      {t('grading.loading')}
    </div>
  )

  return (
    <div style={{ padding: '0', fontFamily: 'IBM Plex Sans, sans-serif', maxWidth: 1200 }}>

      {/* Title */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: '1.5rem', gap: 12,
      }}>
        <div>
          <h1 style={{ fontSize: 'var(--fs-h1)', fontWeight: 500, marginBottom: 4 }}>{t('nav.grading')}</h1>
          <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray, #868685)', fontWeight: 300 }}>
            {t('grading.summary', { sets: allRuleSets.length, rules: totalRegles })}
          </p>
        </div>
        {/* Creació centralitzada a la Size Library; aquí només consulta/edita/esborra. */}
      </div>

      {/* Missatge */}
      {msg && (
        <div style={{
          padding: '8px 12px', borderRadius: 6, fontSize: 'var(--fs-body)', marginBottom: 12,
          background: msg.type === 'ok' ? '#f0f9f0' : '#fff0f0',
          border: `0.5px solid ${msg.type === 'ok' ? '#c0dd97' : '#f09595'}`,
          color: msg.type === 'ok' ? '#3b6d11' : '#a32d2d',
          display: 'flex', justifyContent: 'space-between',
        }}>
          <span>{msg.text}</span>
          <button onClick={() => setMsg(null)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', fontSize: 'var(--fs-h3)' }}>×</button>
        </div>
      )}

      {/* Pas 1: Target */}
      <StepSection number={1} title={t('grading.step_target')}>
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
                setSelectedGarmentGroup(null)
              }}
            />
          ))}
        </div>
      </StepSection>

      {/* Pas 2: Construction + Fit al mateix nivell */}
      {selectedTarget && (availableConstructions.length > 0 || availableFits.length > 0) && (
        <StepSection number={2} title={t('grading.step_construction_fit')}>
          <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
            <div>
              <p style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 6,
                textTransform: 'uppercase', letterSpacing: '.06em',
                }}>
                {t('grading.construction_type')}
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {availableConstructions.map(c => (
                  <SelectionButton
                    key={c.codi}
                    label={t(`model_wizard.construction_${c.codi}`, c.nom_en)}
                    selected={selectedConstruction === c.codi}
                    onClick={() => {
                      setSelectedConstruction(c.codi)
                      setSelectedFit(null)
                      setSelectedGarmentGroup(null)
                    }}
                  />
                ))}
              </div>
            </div>
            {selectedConstruction && availableFits.length > 0 && (
              <div>
                <p style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginBottom: 6,
                  textTransform: 'uppercase', letterSpacing: '.06em',
                  }}>
                  {t('grading.fit_type_label')}
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {availableFits.map(f => (
                    <SelectionButton
                      key={f.codi}
                      label={t(`model_wizard.fit_${f.codi}`, f.nom_en)}
                      selected={selectedFit === f.codi}
                      onClick={() => {
                        setSelectedFit(f.codi)
                        setSelectedGarmentGroup(null)
                      }}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </StepSection>
      )}

      {/* Pas 3: Garment Group */}
      {selectedFit && (
        <StepSection number={3} title={t('grading.step_group')}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {GARMENT_GROUPS.map(g => (
              <SelectionButton
                key={g.codi}
                label={g.nom_en}
                sublabel={lang !== 'en' ? nomLocal(g, lang) : null}
                selected={selectedGarmentGroup === g.codi}
                onClick={() => setSelectedGarmentGroup(g.codi)}
              />
            ))}
          </div>
        </StepSection>
      )}

      {/* RuleSet cards — only with the 4 filters selected */}
      {selectedGarmentGroup && matchingRuleSets.length > 0 && (
        <div style={{ marginTop: 24 }}>
          {matchingRuleSets.map(rs => (
            <RuleSetCard
              key={rs.id}
              rs={rs}
              lang={lang}
              authHeaders={authHeaders}
              garmentGroup={selectedGarmentGroup}
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

      {/* Message when there is no match (with the 4 filters applied) */}
      {selectedGarmentGroup && matchingRuleSets.length === 0 && (
        <div style={{
          marginTop: 24, padding: '2rem', border: '1px dashed var(--border)',
          borderRadius: 8, textAlign: 'center', color: 'var(--gray, #868685)', fontSize: 'var(--fs-body)',
        }}>
          {t('grading.no_match')}
          <div style={{ marginTop: 8, fontSize: 'var(--fs-body)' }}>
            {t('grading.create_from_library')}
          </div>
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
        fontSize: 'var(--fs-label)', fontWeight: 700, color: 'var(--gold)',
        letterSpacing: '0.08em', textTransform: 'uppercase',
        margin: '0 0 10px',
      }}>
        {number} · {title}
      </p>
      {children}
    </div>
  )
}

// ── TargetCard ──────────────────────────────────────────────────────────────
// Same pattern as Size Library: nom_en primary (large), nom_ca secondary (small grey).
function TargetCard({ target, selected, available, onClick }) {
  const { t } = useTranslation()
  return (
    <div
      onClick={available ? onClick : undefined}
      style={{
        border: `1px solid ${selected ? 'var(--gold)' : 'var(--border)'}`,
        borderRadius: 8,
        padding: '8px 14px',
        cursor: available ? 'pointer' : 'not-allowed',
        background: selected ? '#fdf6ee' : available ? 'var(--white)' : '#f8f8f8',
        opacity: available ? 1 : 0.4,
        minWidth: 100, textAlign: 'center',
        transition: 'all .15s',
      }}
    >
      <div style={{
        fontSize: 'var(--fs-body)',
        fontWeight: selected ? 600 : 400,
        color: selected ? 'var(--gold)' : 'var(--text-main)',
      }}>
        {t(`model_wizard.target_${target.codi}`, target.nom_en)}
      </div>
    </div>
  )
}

// ── SelectionButton ─────────────────────────────────────────────────────────
// API S16-B: label + sublabel (en lloc d'`item={...}`). Sublabel es renderitza
// on a second line, smaller and grey.
function SelectionButton({ label, sublabel, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        border: `1px solid ${selected ? 'var(--gold)' : 'var(--border)'}`,
        borderRadius: 6,
        padding: sublabel ? '5px 12px' : '6px 14px',
        background: selected ? '#fdf6ee' : 'var(--white)',
        color: selected ? 'var(--gold)' : 'var(--text-main)',
        fontWeight: selected ? 600 : 400,
        fontSize: 'var(--fs-body)',
        cursor: 'pointer',
        transition: 'all .15s',
        textAlign: 'left',
        lineHeight: 1.25,
      }}
    >
      {label}
      {sublabel && (
        <span style={{
          display: 'block',
          fontSize: 'var(--fs-caption)',
          color: selected ? '#a06622' : 'var(--text-muted)',
          fontWeight: 400,
          marginTop: 1,
        }}>
          {sublabel}
        </span>
      )}
    </button>
  )
}

// ── RuleSetCard ─────────────────────────────────────────────────────────────
function RuleSetCard({ rs, lang = 'ca', authHeaders, garmentGroup, onClone, onEdit, onDelete }) {
  const { t } = useTranslation()
  // S16-B: collapsed by default (the user already arrives here with 4 filters applied
  // and the card is a focal point, not the previous navigational list).
  const [expanded, setExpanded] = useState(false)
  // Local mutable copy of rules for inline edit / deactivate without waiting
  // refetch complet. Es sincronitza si l'API retorna noves regles (rs.regles).
  const [localRules, setLocalRules] = useState(rs.regles || [])
  useEffect(() => { setLocalRules(rs.regles || []) }, [rs.regles])

  // S16-B fix: filtra regles per categories POM rellevants al grup seleccionat.
  // Si no hi ha grup o no hi ha mapping, mostra totes.
  const relevantCategories = garmentGroup ? GROUP_POM_CATEGORIES[garmentGroup] : null
  const visibleRules = relevantCategories
    ? localRules.filter(r => !r.pom_categoria || relevantCategories.includes(r.pom_categoria))
    : localRules

  const editable = !rs.is_system_default
  const reglesCount = visibleRules.length
  const totalRulesCount = localRules.length
  const breakCount = visibleRules.filter(
    r => r.talla_break_label != null || r.valors_step?.above_xl != null).length

  const updateLocalRule = (id, patch) => {
    setLocalRules(prev => prev.map(r => r.id === id ? { ...r, ...patch } : r))
  }

  const handleSaveRule = async (ruleId, field, value) => {
    const current = localRules.find(r => r.id === ruleId)
    const body = field === 'increment'
      ? { increment: value }
      : { valors_step: { ...(current?.valors_step || {}), above_xl: value } }
    try {
      const res = await fetch(`${API}/api/v1/grading-rules/${ruleId}/`, {
        method: 'PATCH',
        headers: { ...authHeaders(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        const updated = await res.json()
        updateLocalRule(ruleId, updated)
      } else {
        // En cas d'error (p.ex. 403 RuleSet sistema), revertim visualment
        // reloading the rule from the current state of rs.regles.
        const original = (rs.regles || []).find(r => r.id === ruleId)
        if (original) updateLocalRule(ruleId, original)
      }
    } catch {
      // network error: cap canvi local
    }
  }

  const handleDeactivateRule = async (ruleId) => {
    if (!confirm(t('grading.confirm_deactivate'))) return
    try {
      const res = await fetch(`${API}/api/v1/grading-rules/${ruleId}/`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (res.ok) {
        // El backend marca actiu=false (no esborra). La traiem de la llista local.
        setLocalRules(prev => prev.filter(r => r.id !== ruleId))
      }
    } catch {
      // network error: cap canvi
    }
  }

  // Table headers (translation only if lang ≠ en).
  const showTrad = lang !== 'en'
  const headers = [
    { label: t('grading.col.code'),       align: 'left'  },
    { label: t('grading.col.pom_name'),    align: 'left'  },
    ...(showTrad ? [{ label: t('grading.col.translation'), align: 'left' }] : []),
    { label: t('grading.col.logic'),     align: 'left'  },
    { label: t('grading.col.delta_size'),    align: 'right' },
    { label: t('grading.col.delta_break'),    align: 'right' },
    { label: t('grading.col.base_size'), align: 'right' },
    { label: t('grading.col.base_value'), align: 'right' },
    ...(editable ? [{ label: '', align: 'center' }] : []),
  ]

  return (
    <div style={{
      border: '1px solid var(--border)', borderRadius: 10,
      marginBottom: 16, overflow: 'hidden', background: 'var(--white)',
      boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    }}>
      <div style={{
        padding: '12px 18px', background: '#fafaf8',
        borderBottom: expanded ? '1px solid var(--border)' : 'none',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        gap: 14, flexWrap: 'wrap',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, minWidth: 0 }}>
          <button
            onClick={() => setExpanded(e => !e)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontSize: 'var(--fs-body)', color: 'var(--text-muted)', padding: 0, lineHeight: 1,
            }}
            aria-label={expanded ? t('grading.collapse') : t('grading.expand')}
          >
            {expanded ? '▾' : '▸'}
          </button>
          <div style={{ minWidth: 0 }}>
            <div style={{
              fontWeight: 600,
              fontSize: 'var(--fs-body)', color: 'var(--text-main)',
            }}>
              {rs.nom}
            </div>
            <div style={{
              fontSize: 'var(--fs-body)', color: 'var(--text-muted)', marginTop: 2,
              display: 'flex', gap: 10, flexWrap: 'wrap',
            }}>
              {/* S16-B: targets array (M2M) — a RuleSet can apply to multiple targets */}
              {rs.targets_codis?.length > 0 && (
                <span>
                  {rs.targets_codis.length > 1 ? t('grading.targets_label') : t('grading.target_label')}
                  {rs.targets_codis.map((tc, i) => (
                    <span key={tc}>
                      {i > 0 && <span style={{ color: '#bbb' }}> · </span>}
                      <strong>{t(`model_wizard.target_${tc}`, tc)}</strong>
                    </span>
                  ))}
                </span>
              )}
              {rs.construction_codi && <span>{t('grading.construction_label')}<strong>{t(`model_wizard.construction_${rs.construction_codi}`, rs.construction_codi)}</strong></span>}
              {rs.fit_type_codi && <span>{t('grading.fit_label')}<strong>{rs.fit_type_codi}</strong></span>}
              {rs.size_system_nom && <span>{t('grading.size_system_label')}<strong>{rs.size_system_nom}</strong></span>}
              {rs.codi_sistema && <span style={{ }}>{rs.codi_sistema}</span>}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Pill bg="#eef4fc" color="#2a5a8a">
            {relevantCategories && reglesCount !== totalRulesCount
              ? t('grading.rules_count_filtered', { count: reglesCount, total: totalRulesCount })
              : t('grading.rules_count', { count: reglesCount })}
          </Pill>
          {breakCount > 0 && <Pill bg="#fdf6ee" color="var(--gold)">{t('grading.with_break', { count: breakCount })}</Pill>}
          <Pill
            bg={rs.is_system_default ? '#f5f0ea' : '#f0f9f0'}
            color={rs.is_system_default ? 'var(--text-muted)' : '#3b6d11'}
          >{rs.is_system_default ? t('grading.system') : t('grading.custom')}</Pill>
          {rs.actiu && <Pill bg="#f0f9f0" color="#3b6d11">{t('grading.active')}</Pill>}
          <ActionBtn onClick={onClone} label={t('grading.clone')} />
          {!rs.is_system_default && (
            <>
              <ActionBtn onClick={onEdit} label={t('app.edit')} />
              <ActionBtn onClick={onDelete} label={t('app.delete')} danger />
            </>
          )}
        </div>
      </div>

      {/* Taula */}
      {expanded && visibleRules.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', fontSize: 'var(--fs-body)', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#fafaf8' }}>
                {headers.map((h, i) => (
                  <th key={i} style={{
                    padding: '8px 12px',
                    textAlign: h.align,
                    fontWeight: 600, color: 'var(--text-muted)', fontSize: 'var(--fs-label)',
                    textTransform: 'uppercase', letterSpacing: '0.06em',
                    borderBottom: '0.5px solid var(--border)',
                  }}>{h.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleRules.map((r, i) => {
                const logica = LOGICA_COLORS[r.logica] || LOGICA_COLORS.FIXED
                const aboveXl = r.valors_step?.above_xl
                const isKey = r.increment > 0 && r.logica === 'LINEAR'
                return (
                  <tr key={r.id} style={{ background: i % 2 === 0 ? 'var(--white)' : '#fafaf8' }}>
                    {/* CODI: codi global (POM-001) gris petit a sobre,
                        abreviatura (CH) daurada més gran a sota. */}
                    <td style={{
                      padding: '7px 12px',
                      borderBottom: '0.5px solid #f0eee9',
                      whiteSpace: 'nowrap',
                    }}>
                      {r.pom_code_global && (
                        <div style={{
                          fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
                          lineHeight: 1.1, letterSpacing: '.02em',
                        }}>{r.pom_code_global}</div>
                      )}
                      <div style={{
                        fontSize: 'var(--fs-body)', color: 'var(--gold)', fontWeight: 600,
                        lineHeight: 1.15,
                      }}>{r.pom_abbreviation || r.pom_codi}</div>
                    </td>
                    <td style={{
                      padding: '7px 12px', color: 'var(--text-main)',
                      borderBottom: '0.5px solid #f0eee9',
                    }}>
                      {r.pom_nom_en || r.pom_nom}
                      {isKey && (
                        <span style={{
                          marginLeft: 6, fontSize: 'var(--fs-caption)', padding: '2px 5px', borderRadius: 3,
                          background: '#fdf6ee', color: 'var(--gold)',
                          border: '0.5px solid #e0c8a0', fontWeight: 600,
                        }}>KEY</span>
                      )}
                    </td>
                    {showTrad && (
                      <td style={{
                        padding: '7px 12px', color: 'var(--text-muted)', fontStyle: 'italic',
                        borderBottom: '0.5px solid #f0eee9',
                      }}>{r.pom_nom_ca || '—'}</td>
                    )}
                    <td style={{ padding: '7px 12px', borderBottom: '0.5px solid #f0eee9' }}>
                      <span style={{
                        fontSize: 'var(--fs-label)', padding: '2px 6px', borderRadius: 3,
                        background: logica.bg, color: logica.color,
                        fontWeight: 600,
                      }}>{r.logica}</span>
                    </td>
                    {/* Δ/talla — Peça A: forma canònica (increment_base) com a TEXT read-only;
                        regles no backfillades (increment_base null) → escalar editable (compat). */}
                    <td style={{
                      padding: '7px 12px', textAlign: 'right',
                      fontWeight: 600,
                      color: Number(r.increment_base ?? r.increment) > 0 ? '#2a5a8a' : 'var(--text-muted)',
                      borderBottom: '0.5px solid #f0eee9',
                    }}>
                      {r.increment_base != null
                        ? (Number(r.increment_base) > 0 ? `+${Number(r.increment_base)} cm` : '—')
                        : (
                          <EditableIncrement
                            value={Number(r.increment) || 0}
                            ruleId={r.id}
                            field="increment"
                            readOnly={!editable}
                            onSave={handleSaveRule}
                          />
                        )}
                    </td>
                    {/* Δ break — Peça A: increment_break + "des de {talla_break_label}" (text);
                        regles no backfillades → fallback above_xl editable (compat). */}
                    <td style={{
                      padding: '7px 12px', textAlign: 'right',
                      fontSize: 'var(--fs-body)',
                      color: (r.increment_base != null ? r.talla_break_label : aboveXl) ? 'var(--gold)' : '#c0c0c0',
                      borderBottom: '0.5px solid #f0eee9',
                    }}>
                      {r.increment_base != null
                        ? (r.talla_break_label
                            ? t('grading.break_from', { value: Number(r.increment_break), size: r.talla_break_label })
                            : '—')
                        : (
                          <EditableIncrement
                            value={aboveXl != null ? Number(aboveXl) : 0}
                            ruleId={r.id}
                            field="above_xl"
                            readOnly={!editable}
                            onSave={handleSaveRule}
                          />
                        )}
                    </td>
                    <td style={{
                      padding: '7px 12px', textAlign: 'right',
                      color: 'var(--text-muted)', fontSize: 'var(--fs-body)',
                      borderBottom: '0.5px solid #f0eee9',
                    }}>{r.talla_base_etiqueta || '—'}</td>
                    <td style={{
                      padding: '7px 12px', textAlign: 'right',
                      color: 'var(--text-muted)',
                      borderBottom: '0.5px solid #f0eee9',
                    }}>{Number(r.valor_base) > 0 ? `${r.valor_base} cm` : '—'}</td>
                    {editable && (
                      <td style={{
                        padding: '7px 12px', textAlign: 'center',
                        borderBottom: '0.5px solid #f0eee9',
                      }}>
                        <ActionBtn
                          onClick={() => handleDeactivateRule(r.id)}
                          label={t('grading.deactivate')}
                          danger
                        />
                      </td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {expanded && visibleRules.length === 0 && (
        <div style={{ padding: '1.5rem', textAlign: 'center', color: '#bbb', fontSize: 'var(--fs-body)' }}>
          {localRules.length === 0
            ? t('grading.no_rules')
            : t('grading.no_relevant_rules', { group: garmentGroup, count: localRules.length })}
        </div>
      )}
    </div>
  )
}

// ── EditableIncrement ───────────────────────────────────────────────────────
// Show a numeric value. If readOnly, render as static text.
// If editable, click → inline numeric input. Enter saves, Escape cancels.
function EditableIncrement({ value, ruleId, field, readOnly, onSave }) {
  const { t } = useTranslation()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)
  useEffect(() => { setDraft(value) }, [value])

  const display = value > 0 ? `+${value}` : value === 0 ? '—' : `${value}`
  const suffix = value === 0 ? '' : ' cm'

  if (readOnly) {
    return <span>{display}{suffix}</span>
  }

  if (editing) {
    const commit = () => {
      const parsed = parseFloat(draft)
      if (!isNaN(parsed)) onSave(ruleId, field, parsed)
      setEditing(false)
    }
    return (
      <input
        autoFocus
        type="number"
        step="0.25"
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={e => {
          if (e.key === 'Enter') commit()
          if (e.key === 'Escape') { setDraft(value); setEditing(false) }
        }}
        style={{
          width: 64, textAlign: 'right',
          border: '1px solid var(--gold)', borderRadius: 4,
          padding: '1px 4px', fontSize: 'var(--fs-body)',
        }}
      />
    )
  }

  return (
    <span
      onClick={() => setEditing(true)}
      title={t('measurement_table.click_to_edit')}
      style={{
        cursor: 'pointer',
        borderBottom: '1px dashed #c0c0c0',
        paddingBottom: 1,
      }}
    >
      {display}{suffix}
    </span>
  )
}

function Pill({ bg, color, children }) {
  return (
    <span style={{
      fontSize: 'var(--fs-label)', padding: '3px 7px', borderRadius: 4,
      background: bg, color,
      fontWeight: 600,
      letterSpacing: '.04em', whiteSpace: 'nowrap',
    }}>{children}</span>
  )
}

function ActionBtn({ onClick, label, danger = false }) {
  const palette = danger
    ? { fg: '#a32d2d', bg: 'var(--white)', border: '#f0c0c0', bgHover: '#fff0f0' }
    : { fg: 'var(--text-muted)', bg: 'var(--white)', border: 'var(--border)', bgHover: '#fdf9f5' }
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onClick() }}
      style={{
        fontSize: 'var(--fs-label)', padding: '4px 9px', borderRadius: 4, cursor: 'pointer',
        background: palette.bg, color: palette.fg,
        border: `0.5px solid ${palette.border}`,
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
  const { t } = useTranslation()
  const isEdit = !!rs?.id
  const [form, setForm] = useState({
    nom:          rs?.nom          || '',
    codi_sistema: rs?.codi_sistema || '',
    // Target/Construction/Fit cannot be sent directly as a code
    // because the backend expects IDs. We keep the codes in the form for the UI
    // i (TODO) caldria endpoint per resoldre codi→id. De moment, els enviem
    // only if the RuleSet being edited already has them (we pass the original ID).
    target:       rs?.target       ?? null,
    construction: rs?.construction ?? null,
    fit_type:     rs?.fit_type     ?? null,
    target_codi_form:       rs?.target_codi       || defaultTarget       || '',
    construction_codi_form: rs?.construction_codi || defaultConstruction || '',
    fit_type_codi_form:     rs?.fit_type_codi     || defaultFit          || '',
    actiu: rs?.actiu ?? true,
  })
  const [saving, setSaving] = useState(false)

  // F-2 — els seeds ISO (is_system_default) NO són editables als eixos (protecció; el guard dur
  // viu al serializer). Creació nova o ruleset de client → eixos editables. Els lookups S2
  // (targets/construction-types/fit-types) resolen codi→id per desar els FK.
  const axesEditable = !rs?.is_system_default
  const [lookups, setLookups] = useState({ targets: [], constructions: [], fits: [] })
  useEffect(() => {
    if (!axesEditable) return
    let alive = true
    const get = (p) => fetch(`${API}/api/v1/${p}`, { headers: authHeaders() })
      .then(r => r.ok ? r.json() : { results: [] }).then(d => d.results || [])
    Promise.all([get('targets/'), get('construction-types/'), get('fit-types/')])
      .then(([targets, constructions, fits]) => { if (alive) setLookups({ targets, constructions, fits }) })
      .catch(() => {})
    return () => { alive = false }
  }, [axesEditable])
  const codeToId = (list, code) => (list.find(x => x.codi === code) || {}).id ?? null

  const handleSubmit = async () => {
    if (!form.nom.trim()) { onError(t('grading.name_required')); return }
    setSaving(true)

    const url = isEdit
      ? `${API}/api/v1/grading-rule-sets/${rs.id}/`
      : `${API}/api/v1/grading-rule-sets/`
    const method = isEdit ? 'PATCH' : 'POST'

    const payload = {
      nom: form.nom.trim(),
      codi_sistema: form.codi_sistema.trim(),
      actiu: form.actiu,
    }
    if (axesEditable) {
      // F-2 — resol codi→id amb els lookups S2 i desa els FK (target + M2M targets + construction
      // + fit_type). Un eix sense selecció queda sense enviar (PATCH → intacte).
      const tId = codeToId(lookups.targets, form.target_codi_form)
      const cId = codeToId(lookups.constructions, form.construction_codi_form)
      const fId = codeToId(lookups.fits, form.fit_type_codi_form)
      if (tId != null) { payload.target = tId; payload.targets = [tId] }
      if (cId != null) payload.construction = cId
      if (fId != null) payload.fit_type = fId
    }
    // Seed (no editable): s'ometen els eixos → el PATCH els deixa intactes (el guard del serializer
    // els blinda igualment). Un possible canvi de nom/actiu no els toca.

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
        fontSize: 'var(--fs-label)', fontWeight: 600, color: 'var(--text-muted)',
        display: 'block', marginBottom: 4,
      }}>{label}</label>
      {options ? (
        <select
          value={form[field] || ''}
          disabled={disabled}
          onChange={e => setForm(f => ({ ...f, [field]: e.target.value }))}
          style={modalInput}
        >
          <option value="">{t('grading.select_placeholder')}</option>
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
          background: 'var(--white)', borderRadius: 12, padding: 24,
          width: '100%', maxWidth: 480,
          boxShadow: '0 10px 40px rgba(0,0,0,0.18)',
        }}
      >
        <h2 style={{ margin: '0 0 16px', fontSize: 'var(--fs-h3)', fontWeight: 600, color: 'var(--text-main)' }}>
          {isEdit ? t('grading.modal_edit') : t('grading.modal_new')}
        </h2>
        <F label={t('grading.field_name')} field="nom" />
        <F label={t('grading.field_codi')} field="codi_sistema" />
        <F label={t('grading.field_target_ref')} field="target_codi_form" options={TARGETS} disabled={!axesEditable} />
        <F label={t('grading.field_construction_ref')} field="construction_codi_form" options={CONSTRUCTIONS} disabled={!axesEditable} />
        <F label={t('grading.field_fit_ref')} field="fit_type_codi_form" options={FITS} disabled={!axesEditable} />
        {!axesEditable && (
          <p style={{ fontSize: 'var(--fs-label)', color: 'var(--gold)', margin: '4px 0 12px' }}>
            {t('grading.modal_note')}
          </p>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 16 }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 16px', borderRadius: 6, cursor: 'pointer',
              background: 'var(--white)', color: 'var(--text-muted)',
              border: '0.5px solid var(--border)',
              fontSize: 'var(--fs-body)',
            }}
          >{t('app.cancel')}</button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            style={{ ...btnPrimary, opacity: saving ? 0.6 : 1, cursor: saving ? 'not-allowed' : 'pointer' }}
          >
            {saving ? t('common.saving') : (isEdit ? t('app.save') : t('app.create'))}
          </button>
        </div>
      </div>
    </div>
  )
}

const btnPrimary = {
  background: 'var(--gold)', color: 'var(--white)',
  border: 'none', borderRadius: 6,
  padding: '8px 14px', fontSize: 'var(--fs-body)', fontWeight: 600,
  cursor: 'pointer', 
}

const modalInput = {
  width: '100%',
  border: '0.5px solid var(--border)',
  borderRadius: 6,
  padding: '8px 10px',
  fontSize: 'var(--fs-body)',
  outline: 'none',
  boxSizing: 'border-box',
  background: 'var(--white)',
}
