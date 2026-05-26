import { useState, useEffect, useMemo } from 'react'
import client from '../api/client'
import SizeSetCard from '../components/SizeSetCard'
import SizeSetDetail from '../components/SizeSetDetail'

// ─────────────────────────────────────────────────────────────
// Mock data — estructura preparada per substituir per API real
// (GET /api/v1/targets/  ·  GET /api/v1/sizing-profiles/)
// ─────────────────────────────────────────────────────────────
const MOCK_TARGETS = [
  { code: 'woman',        en: 'Woman',        ca: 'Dona',           icon: 'ti-user' },
  { code: 'man',          en: 'Man',          ca: 'Home',           icon: 'ti-user' },
  { code: 'baby_girl',    en: 'Baby Girl',    ca: 'Nadó nena',      icon: 'ti-baby-carriage' },
  { code: 'baby_boy',     en: 'Baby Boy',     ca: 'Nadó nen',       icon: 'ti-baby-carriage' },
  { code: 'baby_unisex',  en: 'Baby Unisex',  ca: 'Nadó unisex',    icon: 'ti-baby-carriage' },
  { code: 'toddler_girl', en: 'Toddler Girl', ca: 'Nena petita',    icon: 'ti-mood-kid' },
  { code: 'toddler_boy',  en: 'Toddler Boy',  ca: 'Nen petit',      icon: 'ti-mood-kid' },
  { code: 'girl',         en: 'Girl',         ca: 'Nena',           icon: 'ti-mood-smile' },
  { code: 'boy',          en: 'Boy',          ca: 'Nen',            icon: 'ti-mood-smile' },
  { code: 'teen_girl',    en: 'Teen Girl',    ca: 'Adolescent noia', icon: 'ti-friends' },
  { code: 'teen_boy',     en: 'Teen Boy',     ca: 'Adolescent noi', icon: 'ti-friends' },
  { code: 'unisex',       en: 'Unisex',       ca: 'Unisex',         icon: 'ti-users' },
  { code: 'maternity',    en: 'Maternity',    ca: 'Maternitat',     icon: 'ti-heart' },
]

const CONSTRUCTIONS = [
  { code: 'woven',        label: 'Woven' },
  { code: 'knit',         label: 'Knit' },
  { code: 'stretch_knit', label: 'Stretch Knit' },
  { code: 'technical',    label: 'Technical' },
]

// Mock profiles — variats segons target/construction
const MOCK_PROFILES = [
  {
    id: 'p-alpha-eu',
    name: 'Alpha EU',
    targets: ['woman', 'man', 'teen_girl', 'teen_boy', 'unisex', 'maternity'],
    constructions: ['woven', 'knit', 'stretch_knit'],
    sizes: ['XS', 'S', 'M', 'L', 'XL'],
    base: 'M',
    grading: 'Chest +2cm · Hip +2cm · Length +1cm',
    standard: 'ISO',
    customClient: null,
  },
  {
    id: 'p-numeric-eu',
    name: 'Numeric EU',
    targets: ['woman', 'man', 'maternity'],
    constructions: ['woven', 'knit', 'stretch_knit', 'technical'],
    sizes: ['34', '36', '38', '40', '42', '44'],
    base: '38',
    grading: 'Chest +2cm · Waist +2cm · Hip +2cm',
    standard: 'ISO',
    customClient: null,
  },
  {
    id: 'p-baby-months',
    name: 'Baby months',
    targets: ['baby_girl', 'baby_boy', 'baby_unisex'],
    constructions: ['woven', 'knit', 'stretch_knit'],
    sizes: ['0-3m', '3-6m', '6-9m', '9-12m', '12-18m', '18-24m'],
    base: '6-9m',
    grading: 'Length +3cm · Chest +1cm',
    standard: 'ISO',
    customClient: null,
  },
  {
    id: 'p-kids-eu',
    name: 'Kids EU (height)',
    targets: ['toddler_girl', 'toddler_boy', 'girl', 'boy'],
    constructions: ['woven', 'knit', 'stretch_knit'],
    sizes: ['92', '98', '104', '110', '116', '122', '128'],
    base: '110',
    grading: 'Length +6cm · Chest +2cm',
    standard: 'ISO',
    customClient: null,
  },
  {
    id: 'p-custom-zara',
    name: 'Alpha Custom Zara',
    targets: ['woman', 'man'],
    constructions: ['woven', 'knit'],
    sizes: ['XXS', 'XS', 'S', 'M', 'L', 'XL'],
    base: 'S',
    grading: 'Chest +1.5cm · Hip +1.5cm · Length +1cm',
    standard: null,
    customClient: 'Zara',
  },
  {
    id: 'p-technical-uniform',
    name: 'Technical Uniform',
    targets: ['man', 'woman', 'unisex'],
    constructions: ['technical'],
    sizes: ['S', 'M', 'L', 'XL', 'XXL'],
    base: 'L',
    grading: 'Chest +3cm · Sleeve +1.5cm · Length +1cm',
    standard: 'ISO',
    customClient: null,
  },
]

async function fetchTargets() {
  try {
    const res = await client.get('/api/v1/targets/')
    const list = res.data.results || res.data
    if (Array.isArray(list) && list.length) return list
  } catch (_) {}
  return MOCK_TARGETS
}

async function fetchProfiles(target, construction) {
  try {
    const res = await client.get('/api/v1/sizing-profiles/', {
      params: { target, construction },
    })
    const list = res.data.results || res.data
    if (Array.isArray(list) && list.length) return list
  } catch (_) {}
  return MOCK_PROFILES.filter(p =>
    p.targets.includes(target) && p.constructions.includes(construction)
  )
}

export default function SizeLibrary() {
  const [targets, setTargets] = useState([])
  const [target, setTarget] = useState(null)
  const [construction, setConstruction] = useState(null)
  const [profiles, setProfiles] = useState([])
  const [loadingTargets, setLoadingTargets] = useState(true)
  const [loadingProfiles, setLoadingProfiles] = useState(false)
  const [detailId, setDetailId] = useState(null)

  useEffect(() => {
    fetchTargets()
      .then(setTargets)
      .finally(() => setLoadingTargets(false))
  }, [])

  useEffect(() => {
    if (!target || !construction) {
      setProfiles([])
      return
    }
    setLoadingProfiles(true)
    setDetailId(null)
    fetchProfiles(target.code, construction.code)
      .then(setProfiles)
      .finally(() => setLoadingProfiles(false))
  }, [target, construction])

  const onSelectTarget = (t) => {
    setTarget(t)
    setConstruction(null)
    setProfiles([])
    setDetailId(null)
  }

  const onSelectConstruction = (c) => {
    setConstruction(c)
    setDetailId(null)
  }

  const breadcrumb = useMemo(() => {
    const parts = ['Size Library']
    if (target) parts.push(target.en)
    if (construction) parts.push(construction.label)
    return parts
  }, [target, construction])

  return (
    <div>
      <div style={{marginBottom: '1.5rem'}}>
        <h1 style={{fontSize: 20, fontWeight: 500, marginBottom: 4}}>Size Library</h1>
        <p style={{fontSize: 12, color: 'var(--gray)', fontWeight: 300}}>
          {breadcrumb.map((p, i) => (
            <span key={i}>
              {i > 0 && <span style={{margin: '0 6px', color: 'var(--gray-l2, #d4d4d2)'}}>›</span>}
              <span style={i === breadcrumb.length - 1 ? {color: 'var(--gold)', fontWeight: 500} : {}}>
                {p}
              </span>
            </span>
          ))}
        </p>
      </div>

      {/* Step 1 — Target */}
      <Section
        step={1}
        title="Target"
        subtitle="Selecciona la població objectiu"
        active={!target}
      >
        {loadingTargets ? (
          <div style={loadingStyle}>Carregant...</div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))',
            gap: '0.8rem',
          }}>
            {targets.map(t => (
              <TargetCard
                key={t.code}
                target={t}
                selected={target?.code === t.code}
                onClick={() => onSelectTarget(t)}
              />
            ))}
          </div>
        )}
      </Section>

      {/* Step 2 — Construction */}
      {target && (
        <Section
          step={2}
          title="Construction"
          subtitle="Tipus de teixit"
          active={!construction}
        >
          <div style={{display: 'flex', flexWrap: 'wrap', gap: 8}}>
            {CONSTRUCTIONS.map(c => (
              <ConstructionPill
                key={c.code}
                label={c.label}
                selected={construction?.code === c.code}
                onClick={() => onSelectConstruction(c)}
              />
            ))}
          </div>
        </Section>
      )}

      {/* Step 3 — Size Sets */}
      {target && construction && (
        <Section
          step={3}
          title="Size Sets"
          subtitle={`Sistemes de talles disponibles per ${target.en} · ${construction.label}`}
          active
        >
          {loadingProfiles ? (
            <div style={loadingStyle}>Carregant...</div>
          ) : profiles.length === 0 ? (
            <div style={loadingStyle}>
              No hi ha sistemes definits per aquesta combinació encara.
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
              gap: '1.2rem',
            }}>
              {profiles.map(p => (
                <div key={p.id}>
                  <SizeSetCard
                    profile={p}
                    onUse={() => alert(`Usar: ${p.name}`)}
                    onDetail={() => setDetailId(detailId === p.id ? null : p.id)}
                    onClone={() => alert(`Clonar: ${p.name}`)}
                    detailOpen={detailId === p.id}
                  />
                  {detailId === p.id && (
                    <div style={{marginTop: 12}}>
                      <SizeSetDetail profile={p} />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Section>
      )}
    </div>
  )
}

// ─── Building blocks ────────────────────────────────────────────

function Section({ step, title, subtitle, active, children }) {
  return (
    <div style={{
      marginBottom: '1.8rem',
      opacity: active ? 1 : 0.55,
      transition: 'opacity 0.2s',
    }}>
      <div style={{
        display: 'flex', alignItems: 'baseline', gap: 10,
        marginBottom: '0.8rem',
      }}>
        <span style={{
          width: 22, height: 22, borderRadius: '50%',
          background: 'var(--gold-pale)', color: 'var(--gold)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 11, fontWeight: 600, flexShrink: 0,
        }}>{step}</span>
        <h2 style={{fontSize: 15, fontWeight: 500, margin: 0}}>{title}</h2>
        <span style={{fontSize: 11, color: 'var(--gray)', fontWeight: 300}}>
          {subtitle}
        </span>
      </div>
      {children}
    </div>
  )
}

function TargetCard({ target, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: selected ? 'var(--gold-pale)' : 'var(--white)',
        border: `0.5px solid ${selected ? 'var(--gold)' : '#e4e4e2'}`,
        borderRadius: 12,
        padding: '1.1rem 1rem',
        cursor: 'pointer',
        textAlign: 'center',
        fontFamily: 'inherit',
        transition: 'all 0.15s',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 8,
      }}
    >
      <i
        className={`ti ${target.icon}`}
        style={{
          fontSize: 28,
          color: selected ? 'var(--gold)' : 'var(--gray)',
          strokeWidth: 1,
        }}
      />
      <div>
        <div style={{
          fontSize: 13, fontWeight: 500,
          color: selected ? 'var(--gold)' : 'var(--ink, #1d1d1b)',
        }}>
          {target.en}
        </div>
        <div style={{fontSize: 10, color: 'var(--gray)', fontWeight: 300, marginTop: 2}}>
          {target.ca}
        </div>
      </div>
    </button>
  )
}

function ConstructionPill({ label, selected, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: selected ? 'var(--gold)' : 'var(--white)',
        color: selected ? 'white' : 'var(--ink, #1d1d1b)',
        border: `0.5px solid ${selected ? 'var(--gold)' : '#e4e4e2'}`,
        borderRadius: 999,
        padding: '7px 16px',
        fontSize: 12,
        fontWeight: selected ? 500 : 400,
        cursor: 'pointer',
        fontFamily: 'inherit',
        transition: 'all 0.15s',
      }}
    >
      {label}
    </button>
  )
}

const loadingStyle = {
  padding: '2rem',
  textAlign: 'center',
  color: 'var(--gray)',
  fontSize: 13,
  background: 'var(--white)',
  border: '0.5px solid #e4e4e2',
  borderRadius: 12,
}
