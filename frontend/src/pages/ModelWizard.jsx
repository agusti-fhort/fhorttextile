import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import GarmentTypeSelector from '../components/GarmentTypeSelector/GarmentTypeSelector'
import CustomerSelector from '../components/CustomerSelector'
import useAuthStore from '../store/auth'
import { models, sizingProfiles, sizeDefinitions } from '../api/endpoints'

// Pas 5A — Wizard d'ESQUELET unificat. Un sol flux de creació (3 blocs) + mode edició.
// Crea el Model amb identificació + garment def (família→ITEM = baula del motor) + talles.
// POM/sizing detallat/grading NO aquí: s'enriqueix via tasques a posteriori.

const MONO = 'IBM Plex Mono, monospace'
const currentYear = new Date().getFullYear()
const YEARS = [currentYear, currentYear + 1, currentYear + 2, currentYear + 3]

// Temporades ALINEADES amb Model.TEMPORADA_CHOICES (SS/FW/CO/SP). Corregeix el mismatch RE/PRE.
const SEASONS = [
  { codi: 'SS', nom: 'Spring/Summer' },
  { codi: 'FW', nom: 'Fall/Winter' },
  { codi: 'CO', nom: 'Cruise' },
  { codi: 'SP', nom: 'Special' },
]

const TARGETS = [
  { codi: 'WOMAN', nom: 'Woman' }, { codi: 'MAN', nom: 'Man' }, { codi: 'UNISEX_ADULT', nom: 'Unisex Adult' },
  { codi: 'BABY_GIRL', nom: 'Baby Girl' }, { codi: 'BABY_BOY', nom: 'Baby Boy' }, { codi: 'BABY_UNISEX', nom: 'Baby Unisex' },
  { codi: 'TODDLER_GIRL', nom: 'Toddler Girl' }, { codi: 'TODDLER_BOY', nom: 'Toddler Boy' },
  { codi: 'GIRL', nom: 'Girl' }, { codi: 'BOY', nom: 'Boy' },
  { codi: 'TEEN_GIRL', nom: 'Teen Girl' }, { codi: 'TEEN_BOY', nom: 'Teen Boy' }, { codi: 'MATERNITY', nom: 'Maternity' },
]
const CONSTRUCTIONS = [
  { codi: 'WOVEN', nom: 'Woven (Plana)' }, { codi: 'KNIT', nom: 'Knit (Punt)' },
  { codi: 'STRETCH_KNIT', nom: 'Stretch Knit' }, { codi: 'TECHNICAL', nom: 'Technical' },
]

export default function ModelWizard() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()
  const isEditMode = !!id
  const me = useAuthStore(s => s.user)
  const canConfigure = !!me?.capabilities?.includes('configure')

  const [block, setBlock] = useState(1)
  // Bloc 1 — identificació
  const [year, setYear] = useState(currentYear)
  const [season, setSeason] = useState(null)
  // Customer (selector) i referència/SKU del client (camp de text) són DOS camps diferents:
  // el primer mana el prefix del codi; el segon (codi_client) és la referència pròpia del client.
  const [customerId, setCustomerId] = useState(null)
  const [refClient, setRefClient] = useState('')
  const [nomPrenda, setNomPrenda] = useState('')
  const [descripcio, setDescripcio] = useState('')
  const [collection, setCollection] = useState('')
  const [previewRef, setPreviewRef] = useState('—')
  // Bloc 2 — garment
  const [target, setTarget] = useState(null)
  const [family, setFamily] = useState(null)
  const [item, setItem] = useState(null)
  const [picking, setPicking] = useState(false)
  const [construction, setConstruction] = useState(null)
  // Bloc 3 — talles
  const [profiles, setProfiles] = useState([])
  const [selProfile, setSelProfile] = useState(null)
  const [sizeDefs, setSizeDefs] = useState([])
  const [selectedSizes, setSelectedSizes] = useState([])
  const [baseSize, setBaseSize] = useState(null)

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const sizingResult = useMemo(() => (
    (selProfile && selectedSizes.length > 0 && baseSize) ? {
      size_system_id: selProfile.size_system?.id,
      size_run: selectedSizes.join('·'),
      base_size: baseSize,
      grading_rule_set_id: selProfile.grading_rule_set?.id,
      size_system_nom: selProfile.size_system?.nom,
    } : null
  ), [selProfile, selectedSizes, baseSize])

  const resetSizing = () => { setSelProfile(null); setSelectedSizes([]); setBaseSize(null); setSizeDefs([]) }

  // Preview de referència (només create). El prefix surt del customer triat (fallback self-customer).
  useEffect(() => {
    if (isEditMode || !year || !season) return
    let alive = true
    models.nextRef({ year, season, customer_id: customerId || undefined })
      .then(r => { if (alive) setPreviewRef(r.data?.codi_intern || '—') })
      .catch(() => { if (alive) setPreviewRef('—') })
    return () => { alive = false }
  }, [year, season, customerId, isEditMode])

  // Prefill en edició.
  useEffect(() => {
    if (!isEditMode) return
    let alive = true
    models.get(id).then(r => {
      if (!alive) return
      const d = r.data
      setYear(d.any); setSeason(d.temporada); setPreviewRef(d.codi_intern)
      // Prefill: el selector amb el customer (FK), el CAMP DE TEXT amb codi_client (no els creuis).
      setCustomerId(d.customer != null ? String(d.customer) : null)
      setRefClient(d.codi_client && d.codi_client !== d.codi_intern ? d.codi_client : '')
      setNomPrenda(d.nom_prenda || ''); setDescripcio(d.descripcio || ''); setCollection(d.collection || '')
      setTarget(d.target || null); setConstruction(d.construction || null)
      if (d.garment_type) setFamily({ id: d.garment_type, nom_en: d.garment_type_nom })
      if (d.garment_type_item) setItem({ id: d.garment_type_item, name: d.garment_type_item_nom })
    }).catch(() => setError(t('model_wizard.conn_error')))
    return () => { alive = false }
  }, [id, isEditMode])

  // Bloc 3 — carrega perfils quan hi ha target+construction i estem al bloc 3.
  useEffect(() => {
    if (!target || !construction || block !== 3) return
    let alive = true
    sizingProfiles.list({ target, construction, page_size: 50 })
      .then(r => { if (alive) setProfiles(r.data?.results ?? r.data ?? []) })
      .catch(() => { if (alive) setProfiles([]) })
    return () => { alive = false }
  }, [target, construction, block])

  // Bloc 3 — carrega talles quan es tria un perfil.
  useEffect(() => {
    if (!selProfile) return
    const ssId = selProfile.size_system?.id
    if (!ssId) { setSizeDefs([]); return }
    let alive = true
    sizeDefinitions.list({ size_system: ssId, page_size: 50 })
      .then(r => {
        if (!alive) return
        const defs = r.data?.results ?? r.data ?? []
        setSizeDefs(defs)
        const labels = defs.map(s => s.etiqueta || s.size_label || s.label).filter(Boolean)
        setSelectedSizes(labels)
        setBaseSize(labels[Math.floor(labels.length / 2)] || labels[0] || null)
      })
      .catch(() => { if (alive) setSizeDefs([]) })
    return () => { alive = false }
  }, [selProfile])

  const skeletonPayload = () => ({
    target: target || undefined,
    garment_type_id: family?.id || undefined,
    garment_type_item_id: item?.id || undefined,
    construction: construction || undefined,
    size_system_id: sizingResult?.size_system_id || undefined,
    size_run: sizingResult?.size_run || undefined,
    base_size: sizingResult?.base_size || undefined,
    grading_rule_set_id: sizingResult?.grading_rule_set_id || undefined,
  })

  const handleCreate = async () => {
    if (!season) { setError(t('model_wizard.season_required')); setBlock(1); return }
    if (!customerId) { setError(t('model_wizard.customer_required')); setBlock(1); return }
    setSaving(true); setError('')
    try {
      // El selector mana customer_id; ref_client (text) segueix sent codi_client (SKU del client).
      const r = await models.createWizard({
        year, season, customer_id: customerId, ref_client: refClient,
        nom_prenda: nomPrenda, descripcio, collection,
        ...skeletonPayload(),
      })
      navigate(`/models/${r.data.id}`)
    } catch (e) {
      setError(e.response?.data ? JSON.stringify(e.response.data) : t('model_wizard.conn_error'))
    } finally { setSaving(false) }
  }

  const handleSaveEdit = async () => {
    if (!customerId) { setError(t('model_wizard.customer_required')); setBlock(1); return }
    setSaving(true); setError('')
    try {
      // Edit: el camp FK del serializer és `customer` (rep l'id); codi_client = el camp de text.
      await models.update(id, { customer: customerId, codi_client: refClient, nom_prenda: nomPrenda, descripcio, collection })
      await models.updateStep2(id, skeletonPayload())
      navigate(`/models/${id}`)
    } catch (e) {
      setError(e.response?.data ? JSON.stringify(e.response.data) : t('model_wizard.conn_error'))
    } finally { setSaving(false) }
  }

  const BLOCKS = [t('model_wizard.block1'), t('model_wizard.block2'), t('model_wizard.block3')]

  // GATE entre contenidors: el client mana el prefix del codi i l'abast de la seqüència, així que
  // els passos 2 (Peça) i 3 (Talles) queden bloquejats fins que el pas 1 estigui resolt
  // (CLIENT + ANY + TEMPORADA → referència interna generada en conseqüència).
  const block1Resolved = !!(customerId && year && season)

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '2rem 1rem' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
        <h1 style={{ fontFamily: MONO, fontSize: 22, fontWeight: 500, margin: 0 }}>
          {isEditMode ? t('model_wizard.title_edit') : t('model_wizard.title_new')}
        </h1>
        <button type="button" onClick={() => navigate('/models')} style={linkBtn}>✕ {t('model_wizard.cancel')}</button>
      </div>

      {/* Stepper */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 18, flexWrap: 'wrap' }}>
        {BLOCKS.map((label, i) => {
          const n = i + 1, active = block === n
          const locked = n > 1 && !block1Resolved   // gate: 2 i 3 bloquejats fins resoldre el pas 1
          return (
            <button key={n} disabled={locked} onClick={() => { if (!locked) setBlock(n) }} style={{
              flex: 1, minWidth: 120, padding: '8px 12px', borderRadius: 8, cursor: locked ? 'not-allowed' : 'pointer', fontFamily: MONO,
              fontSize: 12, fontWeight: active ? 600 : 400, textAlign: 'left',
              background: active ? 'var(--warn-bg)' : 'var(--white)',
              color: active ? 'var(--warn)' : 'var(--gray)',
              border: `0.5px solid ${active ? 'var(--warn)' : 'var(--gray-l)'}`,
              opacity: locked ? 0.45 : 1,
            }}>
              <span style={{ opacity: 0.7 }}>{n}.</span> {label}{locked && ' 🔒'}
            </button>
          )
        })}
      </div>

      {error && <div style={errBox}>{error}</div>}

      <div style={{ border: '0.5px solid var(--gray-l)', borderRadius: 12, background: 'var(--white)', padding: 20 }}>
        {block === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <Field label={t('model_wizard.customer')}>
              <CustomerSelector value={customerId} onChange={setCustomerId} allowCreate={canConfigure} onError={setError} />
            </Field>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
              <Field label={t('model_wizard.year')}>
                <div style={{ display: 'flex', gap: 6 }}>
                  {YEARS.map(y => <Chip key={y} active={year === y} onClick={() => setYear(y)} disabled={isEditMode}>{y}</Chip>)}
                </div>
              </Field>
              <Field label={t('model_wizard.season')}>
                <div style={{ display: 'flex', gap: 6 }}>
                  {SEASONS.map(s => (
                    <Chip key={s.codi} active={season === s.codi} onClick={() => setSeason(s.codi)} disabled={isEditMode}>
                      <span style={{ fontWeight: 500 }}>{s.codi}</span>
                      <span style={{ fontSize: 9, display: 'block', opacity: 0.8 }}>{s.nom}</span>
                    </Chip>
                  ))}
                </div>
              </Field>
              <Field label={t('model_wizard.internal_ref')}>
                <div style={refBox}>{previewRef}</div>
                <div style={{ ...labelStyle, marginTop: 4, textTransform: 'none' }}>{t('model_wizard.auto_ref')}</div>
              </Field>
            </div>
            <TextInput label={t('model_wizard.ref_client')} value={refClient} onChange={setRefClient} placeholder="ex: AB-1234" />
            <TextInput label={t('model_wizard.collection')} value={collection} onChange={setCollection} placeholder="ex: SS26 Capsule" />
            <TextInput label={t('model_wizard.nom_prenda')} value={nomPrenda} onChange={setNomPrenda} />
            <Field label={t('model_wizard.descripcio')}>
              <textarea value={descripcio} onChange={e => setDescripcio(e.target.value)} style={{ ...inputStyle, minHeight: 70, resize: 'vertical' }} />
            </Field>
          </div>
        )}

        {block === 2 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <Field label={t('model_wizard.target')}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {TARGETS.map(tg => (
                  <Chip key={tg.codi} active={target === tg.codi} onClick={() => setTarget(tg.codi)}>{tg.nom}</Chip>
                ))}
              </div>
            </Field>

            {target && (
              <Field label={t('model_wizard.garment')}>
                {item && !picking ? (
                  <div style={summaryBox}>
                    <div>
                      <div style={{ ...labelStyle, fontSize: 9 }}>{t('model_wizard.selected_item')}</div>
                      <div style={{ fontSize: 13, fontWeight: 600 }}>
                        {(family?.nom_en || '—')} · {item.name}
                      </div>
                    </div>
                    <button type="button" onClick={() => setPicking(true)} style={ghostBtn}>{t('model_wizard.change')}</button>
                  </div>
                ) : (
                  <div style={{ height: 460, border: '0.5px solid var(--gray-l)', borderRadius: 8, overflow: 'hidden' }}>
                    <GarmentTypeSelector
                      selectedItemId={item?.id}
                      onSelect={({ family: fam, item: it }) => { setFamily(fam); setItem(it); setPicking(false) }}
                    />
                  </div>
                )}
              </Field>
            )}

            {target && (
              <Field label={t('model_wizard.construction')}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {CONSTRUCTIONS.map(c => (
                    <Chip key={c.codi} active={construction === c.codi} onClick={() => { if (construction !== c.codi) resetSizing(); setConstruction(c.codi) }}>{c.nom}</Chip>
                  ))}
                </div>
              </Field>
            )}
          </div>
        )}

        {block === 3 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {(!target || !construction) ? (
              <p style={{ fontSize: 12, color: 'var(--gray)', fontFamily: MONO }}>{t('model_wizard.no_sizes')}</p>
            ) : (
              <>
                <p style={{ fontSize: 12, color: 'var(--gray)', fontFamily: MONO, margin: 0 }}>
                  {t('model_wizard.sizes_for')} {target} · {construction}
                </p>
                {profiles.length === 0 && <p style={{ fontSize: 12, color: 'var(--gray)', fontFamily: MONO }}>{t('model_wizard.no_sizes')}</p>}
                {profiles.map(p => {
                  const active = selProfile?.id === p.id
                  const sub = [p.target?.nom_en || p.target?.codi, p.construction?.nom_en || p.construction?.codi, p.fit_type_nom].filter(Boolean).join(' · ')
                  return (
                    <div key={p.id} onClick={() => setSelProfile(p)} style={{
                      padding: '10px 14px', borderRadius: 8, cursor: 'pointer', fontFamily: MONO,
                      border: `0.5px solid ${active ? 'var(--warn)' : 'var(--gray-l)'}`,
                      background: active ? 'var(--warn-bg)' : 'var(--white)',
                    }}>
                      <div style={{ fontWeight: 500, fontSize: 14 }}>{p.size_system?.nom || `Profile #${p.id}`}</div>
                      <div style={{ fontSize: 12, color: 'var(--gray)' }}>{sub}</div>
                    </div>
                  )
                })}
                {selProfile && (
                  <Field label={t('model_wizard.pick_run')}>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {sizeDefs.map(s => {
                        const label = s.etiqueta || s.size_label || s.label
                        const active = selectedSizes.includes(label)
                        return <Chip key={label} active={active} onClick={() => setSelectedSizes(prev => active ? prev.filter(x => x !== label) : [...prev, label])}>{label}</Chip>
                      })}
                    </div>
                  </Field>
                )}
                {selectedSizes.length > 0 && (
                  <Field label={t('model_wizard.base_size')}>
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {selectedSizes.map(s => <Chip key={s} active={baseSize === s} onClick={() => setBaseSize(s)}>{s} {baseSize === s && '★'}</Chip>)}
                    </div>
                  </Field>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Avís si no hi ha ítem */}
      {!item && (
        <div style={{ ...errBox, background: 'var(--warn-bg)', color: 'var(--warn)', border: '0.5px solid var(--warn)' }}>
          {t('model_wizard.no_item_warn')}
        </div>
      )}

      {/* Footer */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 18 }}>
        <button type="button" disabled={block === 1} onClick={() => setBlock(b => Math.max(1, b - 1))}
          style={{ ...ghostBtn, opacity: block === 1 ? 0.4 : 1 }}>← {t('model_wizard.back')}</button>
        {block < 3 ? (
          <button type="button" disabled={block === 1 && !block1Resolved}
            onClick={() => { if (!(block === 1 && !block1Resolved)) setBlock(b => Math.min(3, b + 1)) }}
            style={primaryBtn(block === 1 && !block1Resolved)}>{t('model_wizard.next')} →</button>
        ) : (
          <button type="button" disabled={saving} onClick={isEditMode ? handleSaveEdit : handleCreate} style={primaryBtn(saving)}>
            {saving ? (isEditMode ? t('model_wizard.saving') : t('model_wizard.creating'))
              : (isEditMode ? t('model_wizard.save') : t('model_wizard.create'))}
          </button>
        )}
      </div>

    </div>
  )
}

// ── UI atoms (tokens) ─────────────────────────────────────────────────────────
const labelStyle = { fontSize: 11, color: 'var(--gray)', textTransform: 'uppercase', letterSpacing: '.04em', fontFamily: MONO }
const inputStyle = { width: '100%', padding: '8px 10px', borderRadius: 4, border: '0.5px solid var(--gray-l)', fontFamily: MONO, fontSize: 13, background: 'var(--white)', boxSizing: 'border-box' }
const refBox = { background: 'var(--warn-bg)', border: '0.5px solid var(--warn)', borderRadius: 8, padding: '8px 14px', fontFamily: MONO, fontSize: 15, color: 'var(--warn)', fontWeight: 500, minHeight: 36, display: 'flex', alignItems: 'center' }
const errBox = { background: '#fee', border: '1px solid #fcc', borderRadius: 8, padding: '0.6rem 1rem', margin: '12px 0 0', fontSize: 13, color: '#c00', fontFamily: MONO }
const summaryBox = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, padding: '12px 16px', borderRadius: 8, border: '0.5px solid var(--gray-l)', background: 'var(--warn-bg)' }
const linkBtn = { background: 'none', border: 'none', padding: 0, color: 'var(--gray)', fontSize: 12, cursor: 'pointer', fontFamily: MONO }
const ghostBtn = { background: 'var(--white)', color: 'var(--warn)', border: '0.5px solid var(--warn)', borderRadius: 6, padding: '6px 14px', fontSize: 12, cursor: 'pointer', fontFamily: MONO }
const primaryBtn = (disabled) => ({ background: disabled ? 'var(--gray-l)' : 'var(--warn)', color: '#fff', border: 'none', borderRadius: 6, padding: '8px 20px', fontSize: 14, fontWeight: 500, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.6 : 1, fontFamily: MONO })

function Field({ label, children }) {
  return (
    <div style={{ flex: '1 1 auto' }}>
      <div style={{ ...labelStyle, marginBottom: 6 }}>{label}</div>
      {children}
    </div>
  )
}
function TextInput({ label, value, onChange, placeholder }) {
  return (
    <Field label={label}>
      <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={inputStyle} />
    </Field>
  )
}
function Chip({ active, onClick, disabled, children }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} style={{
      padding: '6px 14px', borderRadius: 6, fontFamily: MONO, fontSize: 13,
      border: active ? '1.5px solid var(--warn)' : '0.5px solid var(--gray-l)',
      background: active ? 'var(--warn)' : 'transparent', color: active ? '#fff' : 'var(--text-main)',
      cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled && !active ? 0.5 : 1, fontWeight: active ? 500 : 400,
    }}>{children}</button>
  )
}
