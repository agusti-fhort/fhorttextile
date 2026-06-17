import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import GarmentTypeSelector from '../components/GarmentTypeSelector/GarmentTypeSelector'
import CustomerSelector from '../components/CustomerSelector'
import useAuthStore from '../store/auth'
import { models, sizingProfiles, sizeDefinitions, customers } from '../api/endpoints'

// Pas 5A — Wizard d'ESQUELET unificat. Un sol flux de creació (3 blocs) + mode edició.
// Crea el Model amb identificació + garment def (família→ITEM = baula del motor) + talles.
// POM/sizing detallat/grading NO aquí: s'enriqueix via tasques a posteriori.

const MONO = 'IBM Plex Mono, monospace'
const currentYear = new Date().getFullYear()
const YEARS = [currentYear, currentYear + 1, currentYear + 2, currentYear + 3]

// Temporades ALINEADES amb Model.TEMPORADA_CHOICES (SS/FW/CO/SP). Corregeix el mismatch RE/PRE.
// Només l'identificador (codi); l'etiqueta visible es resol amb t('model_wizard.<tipus>_<codi>').
const SEASONS = ['SS', 'FW', 'CO', 'SP']
const TARGETS = [
  'WOMAN', 'MAN', 'UNISEX_ADULT',
  'BABY_GIRL', 'BABY_BOY', 'BABY_UNISEX',
  'TODDLER_GIRL', 'TODDLER_BOY',
  'GIRL', 'BOY',
  'TEEN_GIRL', 'TEEN_BOY', 'MATERNITY',
]
const CONSTRUCTIONS = ['WOVEN', 'KNIT', 'STRETCH_KNIT', 'TECHNICAL']

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
  const [customerCodi, setCustomerCodi] = useState('')   // codi (3 chars) per ordenar sizing profiles
  const [refClient, setRefClient] = useState('')
  const [nomPrenda, setNomPrenda] = useState('')
  const [descripcio, setDescripcio] = useState('')
  const [collection, setCollection] = useState('')
  const [dataObjectiu, setDataObjectiu] = useState('')   // deadline (opcional)
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
  // Peça 4 — sistema/run que ja tenia el model (edició), per detectar canvi de sistema de talles.
  const [modelSizeSystemId, setModelSizeSystemId] = useState(null)
  const [modelSizeRun, setModelSizeRun] = useState('')

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

  // Peça 4 — en edició, si el model ja tenia run i el sistema de talles del perfil triat
  // és DIFERENT del que té el model, la talla base no s'autoassigna i és obligatòria.
  const systemChanged = !!(
    isEditMode && modelSizeRun && selProfile &&
    modelSizeSystemId != null && modelSizeSystemId !== selProfile.size_system?.id
  )
  const baseSizeInvalid = systemChanged && (!baseSize || !selectedSizes.includes(baseSize))

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
      setDataObjectiu(d.data_objectiu || '')
      setTarget(d.target || null); setConstruction(d.construction || null)
      setModelSizeSystemId(d.size_system ?? null)
      setModelSizeRun(d.size_run_model || '')
      if (d.garment_type) setFamily({ id: d.garment_type, nom_en: d.garment_type_nom })
      if (d.garment_type_item) setItem({ id: d.garment_type_item, name: d.garment_type_item_nom })
    }).catch(() => setError(t('model_wizard.conn_error')))
    return () => { alive = false }
  }, [id, isEditMode])

  // Resol el codi (3 chars) del customer triat, per ordenar els sizing profiles.
  useEffect(() => {
    if (!customerId) { setCustomerCodi(''); return }
    let alive = true
    customers.get(customerId)
      .then(r => { if (alive) setCustomerCodi(r.data?.codi || '') })
      .catch(() => { if (alive) setCustomerCodi('') })
    return () => { alive = false }
  }, [customerId])

  // Bloc 3 — carrega perfils quan hi ha target+construction i estem al bloc 3.
  // Ordenats al backend: primer els del customer, després canònics. Pre-seleccionem el primer.
  useEffect(() => {
    if (!target || !construction || block !== 3) return
    let alive = true
    sizingProfiles.list({ target, construction, customer_codi: customerCodi || undefined, page_size: 50 })
      .then(r => {
        if (!alive) return
        const rows = r.data?.results ?? r.data ?? []
        setProfiles(rows)
        // Pre-selecció només en CREACIÓ (en edició no toquem la selecció ni el guard de talla base).
        if (rows.length && !selProfile && !isEditMode) setSelProfile(rows[0])
      })
      .catch(() => { if (alive) setProfiles([]) })
    return () => { alive = false }
  }, [target, construction, block, customerCodi])  // eslint-disable-line react-hooks/exhaustive-deps

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
        // Peça 4 — si en edició el sistema canvia respecte al model, NO autoassignis la base.
        const changed = isEditMode && modelSizeRun && modelSizeSystemId != null && modelSizeSystemId !== ssId
        setBaseSize(changed ? null : (labels[Math.floor(labels.length / 2)] || labels[0] || null))
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
        data_objectiu: dataObjectiu || null,
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
      await models.update(id, { customer: customerId, codi_client: refClient, nom_prenda: nomPrenda, descripcio, collection, data_objectiu: dataObjectiu || null })
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
        <h1 style={{ fontFamily: MONO, fontSize: 'var(--fs-h1)', fontWeight: 500, margin: 0 }}>
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
              fontSize: 'var(--fs-body)', fontWeight: active ? 600 : 400, textAlign: 'left',
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
                    <Chip key={s} active={season === s} onClick={() => setSeason(s)} disabled={isEditMode}>
                      <span style={{ fontWeight: 500 }}>{s}</span>
                      <span style={{ fontSize: 'var(--fs-caption)', display: 'block', opacity: 0.8 }}>{t(`model_wizard.season_${s}`)}</span>
                    </Chip>
                  ))}
                </div>
              </Field>
              <Field label={t('model_wizard.internal_ref')}>
                <div style={refBox}>{previewRef}</div>
                <div style={{ ...labelStyle, marginTop: 4, textTransform: 'none' }}>{t('model_wizard.auto_ref')}</div>
              </Field>
            </div>
            <TextInput label={t('model_wizard.ref_client')} value={refClient} onChange={setRefClient} placeholder={t('model_wizard.ph_ref_client')} />
            <TextInput label={t('model_wizard.collection')} value={collection} onChange={setCollection} placeholder={t('model_wizard.ph_collection')} />
            <TextInput label={t('model_wizard.nom_prenda')} value={nomPrenda} onChange={setNomPrenda} />
            <Field label={t('model_wizard.descripcio')}>
              <textarea value={descripcio} onChange={e => setDescripcio(e.target.value)} style={{ ...inputStyle, minHeight: 70, resize: 'vertical' }} />
            </Field>
            <Field label={t('model_wizard.deadline_optional')}>
              <input type="date" value={dataObjectiu} onChange={e => setDataObjectiu(e.target.value)} style={inputStyle} />
            </Field>
          </div>
        )}

        {block === 2 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <Field label={t('model_wizard.target')}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {TARGETS.map(tg => (
                  <Chip key={tg} active={target === tg} onClick={() => setTarget(tg)}>{t(`model_wizard.target_${tg}`)}</Chip>
                ))}
              </div>
            </Field>

            {target && (
              <Field label={t('model_wizard.garment')}>
                {item && !picking ? (
                  <div style={summaryBox}>
                    <div>
                      <div style={{ ...labelStyle, fontSize: 'var(--fs-caption)' }}>{t('model_wizard.selected_item')}</div>
                      <div style={{ fontSize: 'var(--fs-body)', fontWeight: 600 }}>
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
                    <Chip key={c} active={construction === c} onClick={() => { if (construction !== c) resetSizing(); setConstruction(c) }}>{t(`model_wizard.construction_${c}`)}</Chip>
                  ))}
                </div>
              </Field>
            )}
          </div>
        )}

        {block === 3 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {(!target || !construction) ? (
              <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO }}>{t('model_wizard.no_sizes')}</p>
            ) : (
              <>
                <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, margin: 0 }}>
                  {t('model_wizard.sizes_for')} {t(`model_wizard.target_${target}`)} · {t(`model_wizard.construction_${construction}`)}
                </p>
                {profiles.length === 0 && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO }}>{t('model_wizard.no_sizes')}</p>}
                {profiles.map(p => {
                  const active = selProfile?.id === p.id
                  const sub = [
                    p.target?.codi ? t(`model_wizard.target_${p.target.codi}`, p.target.nom_en || p.target.codi) : p.target?.nom_en,
                    p.construction?.codi ? t(`model_wizard.construction_${p.construction.codi}`, p.construction.nom_en || p.construction.codi) : p.construction?.nom_en,
                    p.fit_type_nom,
                  ].filter(Boolean).join(' · ')
                  // Peça 3 — rang d'edat (mesos) derivat de les size_definitions del perfil.
                  const ageMins = (p.size_definitions || []).map(d => d.age_months_min).filter(v => v != null)
                  const ageMaxs = (p.size_definitions || []).map(d => d.age_months_max).filter(v => v != null)
                  const ageMin = ageMins.length ? Math.min(...ageMins) : null
                  const ageMax = ageMaxs.length ? Math.max(...ageMaxs) : null
                  return (
                    <div key={p.id} onClick={() => setSelProfile(p)} style={{
                      padding: '10px 14px', borderRadius: 8, cursor: 'pointer', fontFamily: MONO,
                      border: `0.5px solid ${active ? 'var(--warn)' : 'var(--gray-l)'}`,
                      background: active ? 'var(--warn-bg)' : 'var(--white)',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 500, fontSize: 'var(--fs-h3)' }}>{p.size_system?.nom || t('model_wizard.profile_n', { id: p.id })}</span>
                        {p.size_system_customer_codi
                          ? <span style={{ fontSize: 'var(--fs-caption)', fontWeight: 600, padding: '1px 6px', borderRadius: 999,
                                           background: 'var(--gold-pale)', color: 'var(--gold)' }}>
                              {t('model_wizard.client_run')}: {p.size_system_customer_codi}
                            </span>
                          : <span style={{ fontSize: 'var(--fs-caption)', fontWeight: 600, padding: '1px 6px', borderRadius: 999,
                                           background: 'var(--gray-l)', color: 'var(--gray)' }}>
                              {t('model_wizard.canonical')}
                            </span>}
                      </div>
                      <div style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{sub}</div>
                      {ageMin != null && ageMax != null && ageMax > 0 && (
                        <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 2 }}>
                          {t('model_wizard.age_months_range', { min: ageMin, max: ageMax })}
                        </div>
                      )}
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
                    {baseSizeInvalid && (
                      <div style={{ color: 'var(--warn)', fontSize: 'var(--fs-body)', marginTop: 6 }}>
                        {t('wizard_base_size_required')}
                      </div>
                    )}
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
          <button type="button" disabled={saving || baseSizeInvalid} onClick={isEditMode ? handleSaveEdit : handleCreate} style={primaryBtn(saving || baseSizeInvalid)}>
            {saving ? (isEditMode ? t('model_wizard.saving') : t('model_wizard.creating'))
              : (isEditMode ? t('model_wizard.save') : t('model_wizard.create'))}
          </button>
        )}
      </div>

    </div>
  )
}

// ── UI atoms (tokens) ─────────────────────────────────────────────────────────
const labelStyle = { fontSize: 'var(--fs-body)', color: 'var(--gray)', textTransform: 'uppercase', letterSpacing: '.04em', fontFamily: MONO }
const inputStyle = { width: '100%', padding: '8px 10px', borderRadius: 4, border: '0.5px solid var(--gray-l)', fontFamily: MONO, fontSize: 'var(--fs-body)', background: 'var(--white)', boxSizing: 'border-box' }
const refBox = { background: 'var(--warn-bg)', border: '0.5px solid var(--warn)', borderRadius: 8, padding: '8px 14px', fontFamily: MONO, fontSize: 'var(--fs-h3)', color: 'var(--warn)', fontWeight: 500, minHeight: 36, display: 'flex', alignItems: 'center' }
const errBox = { background: '#fee', border: '1px solid #fcc', borderRadius: 8, padding: '0.6rem 1rem', margin: '12px 0 0', fontSize: 'var(--fs-body)', color: '#c00', fontFamily: MONO }
const summaryBox = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, padding: '12px 16px', borderRadius: 8, border: '0.5px solid var(--gray-l)', background: 'var(--warn-bg)' }
const linkBtn = { background: 'none', border: 'none', padding: 0, color: 'var(--gray)', fontSize: 'var(--fs-body)', cursor: 'pointer', fontFamily: MONO }
const ghostBtn = { background: 'var(--white)', color: 'var(--warn)', border: '0.5px solid var(--warn)', borderRadius: 6, padding: '6px 14px', fontSize: 'var(--fs-body)', cursor: 'pointer', fontFamily: MONO }
const primaryBtn = (disabled) => ({ background: disabled ? 'var(--gray-l)' : 'var(--warn)', color: 'var(--white)', border: 'none', borderRadius: 6, padding: '8px 20px', fontSize: 'var(--fs-h3)', fontWeight: 500, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.6 : 1, fontFamily: MONO })

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
      padding: '6px 14px', borderRadius: 6, fontFamily: MONO, fontSize: 'var(--fs-body)',
      border: active ? '1.5px solid var(--warn)' : '0.5px solid var(--gray-l)',
      background: active ? 'var(--warn)' : 'transparent', color: active ? 'var(--white)' : 'var(--text-main)',
      cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled && !active ? 0.5 : 1, fontWeight: active ? 500 : 400,
    }}>{children}</button>
  )
}
