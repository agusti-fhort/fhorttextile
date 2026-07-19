import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import GarmentTypeSelector from '../components/GarmentTypeSelector/GarmentTypeSelector'
import CustomerSelector from '../components/CustomerSelector'
import RuleSetPicker from '../components/grading/RuleSetPicker'
import { availableFitsStrict } from '../components/grading/gradingAxes'
import useAuthStore from '../store/auth'
import { models, sizeSystems, customers, gradingRuleSets, garmentGroups } from '../api/endpoints'

// Wizard d'ESQUELET unificat. Un sol flux de creació (4 blocs) + mode edició.
// Crea el Model amb identificació + garment def (família→ITEM = baula del motor) + talles + GRADUACIÓ.
// Sprint WIZARD-COMPLET: la graduació (pas 4) torna al wizard, amb matching ESTRICTE (size_system
// obligatori, cap comodí NULL) i opció explícita «Sense graduació». POM detallat NO aquí.

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
  const [searchParams] = useSearchParams()
  const me = useAuthStore(s => s.user)
  const canConfigure = !!me?.capabilities?.includes('configure')

  // WIZARD-COMPLET C.3 — «Canviar graduació» des de la fitxa obre el wizard directament al pas 4.
  const [block, setBlock] = useState(isEditMode && searchParams.get('block') === '4' ? 4 : 1)
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
  // Bloc 3 — talles (LLEI 5 CAPES: ESCALA PURA — SizeSystem, sense fit ni graduació)
  const [systems, setSystems] = useState([])
  const [selSystem, setSelSystem] = useState(null)
  const [sizeDefs, setSizeDefs] = useState([])
  const [selectedSizes, setSelectedSizes] = useState([])
  const [baseSize, setBaseSize] = useState(null)
  // Peça 4 — sistema/run que ja tenia el model (edició), per detectar canvi de sistema de talles.
  const [modelSizeSystemId, setModelSizeSystemId] = useState(null)
  const [modelSizeRun, setModelSizeRun] = useState('')
  // Bloc 4 — GRADUACIÓ (sprint WIZARD-COMPLET). Eixos target/construction/grup + size_system venen
  // fixats dels passos 2-3 (arbre únic: el grup el mana l'item, no es re-tria); l'usuari només tria FIT.
  const [gradingRuleSets_, setGradingRuleSets_] = useState([])
  const [ggCodiById, setGgCodiById] = useState({})
  const [fit, setFit] = useState(null)               // codi de fit triat (eix del matching)
  const [gradingRuleSetId, setGradingRuleSetId] = useState(null)  // ruleset triat (null = cap)
  const [noGrading, setNoGrading] = useState(false)  // «Sense graduació» explícit
  const [modelGarmentGrup, setModelGarmentGrup] = useState(null)  // grup del model en edició (prefill)

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const resetGrading = () => { setFit(null); setGradingRuleSetId(null); setNoGrading(false) }

  // LLEI 5 CAPES: el pas Talles retorna NOMÉS escala (sistema/run/base). La graduació (capa 4) es
  // tria per separat a la fitxa (RuleSetCard→update-step2). Aquí NO s'arrossega grading_rule_set_id.
  const sizingResult = useMemo(() => (
    (selSystem && selectedSizes.length > 0 && baseSize) ? {
      size_system_id: selSystem.id,
      size_run: selectedSizes.join('·'),
      base_size: baseSize,
      size_system_nom: selSystem.nom,
    } : null
  ), [selSystem, selectedSizes, baseSize])

  const resetSizing = () => { setSelSystem(null); setSelectedSizes([]); setBaseSize(null); setSizeDefs([]) }

  // Peça 4 — en edició, si el model ja tenia run i el sistema de talles del perfil triat
  // és DIFERENT del que té el model, la talla base no s'autoassigna i és obligatòria.
  const systemChanged = !!(
    isEditMode && modelSizeRun && selSystem &&
    modelSizeSystemId != null && modelSizeSystemId !== selSystem.id
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
      // Bloc 4 — graduació vigent (edició): grup canònic (sempre present via garment_type.grup) i
      // ruleset actual, perquè el pas 4 mostri la selecció i permeti canviar-la (cas Regular→Slim).
      setModelGarmentGrup(d.garment_type_grup || null)
      if (d.grading_rule_set) setGradingRuleSetId(d.grading_rule_set)
      if (d.garment_type) setFamily({ id: d.garment_type, nom_en: d.garment_type_nom, grup: d.garment_type_grup })
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

  // Bloc 3 (LLEI 5 CAPES) — carrega SizeSystems PURS quan hi ha target i estem al bloc 3.
  // Filtra pel target de la peça (target_codis, buit = universal) i descarta systems sense talles.
  // Escala pura: SENSE fit, SENSE construcció, SENSE graduació. Pre-selecciona el primer en creació.
  useEffect(() => {
    if (!target || block !== 3) return
    let alive = true
    sizeSystems.list({ actiu: true, page_size: 100 })
      .then(r => {
        if (!alive) return
        const rows = (r.data?.results ?? r.data ?? []).filter(s =>
          (s.talles || []).length > 0 &&
          (!s.target_codis || s.target_codis.length === 0 || s.target_codis.includes(target)))
        setSystems(rows)
        if (rows.length && !selSystem && !isEditMode) setSelSystem(rows[0])
      })
      .catch(() => { if (alive) setSystems([]) })
    return () => { alive = false }
  }, [target, block])  // eslint-disable-line react-hooks/exhaustive-deps

  // Bloc 3 — carrega talles del sistema triat (venen amb el propi SizeSystem, sense crida extra).
  useEffect(() => {
    if (!selSystem) return
    const defs = selSystem.talles || []
    setSizeDefs(defs)
    const labels = defs.map(s => s.etiqueta || s.size_label || s.label).filter(Boolean)
    setSelectedSizes(labels)
    // Peça 4 — si en edició el sistema canvia respecte al model, NO autoassignis la base.
    const changed = isEditMode && modelSizeRun && modelSizeSystemId != null && modelSizeSystemId !== selSystem.id
    setBaseSize(changed ? null : (labels[Math.floor(labels.length / 2)] || labels[0] || null))
  }, [selSystem])  // eslint-disable-line react-hooks/exhaustive-deps

  // Bloc 4 — el grup canònic de la peça (eix fix del matching). Prové de l'ITEM (arbre únic):
  // family.grup en creació; garment_type.grup del model en edició. Mai es re-tria a mà.
  const garmentGroupCodi = family?.grup ?? modelGarmentGrup ?? null

  // Bloc 4 — carrega rulesets + mapa grup id→codi quan s'entra al pas. En edició, deriva el fit
  // vigent del ruleset del model perquè el picker el mostri seleccionat.
  useEffect(() => {
    if (block !== 4) return
    let alive = true
    Promise.all([gradingRuleSets.list({ page_size: 200 }), garmentGroups.list({ page_size: 200 })])
      .then(([rsRes, ggRes]) => {
        if (!alive) return
        const rs = rsRes.data?.results ?? (Array.isArray(rsRes.data) ? rsRes.data : [])
        const gg = ggRes.data?.results ?? (Array.isArray(ggRes.data) ? ggRes.data : [])
        const map = {}; gg.forEach(g => { map[g.id] = g.codi })
        setGradingRuleSets_(rs); setGgCodiById(map)
        if (gradingRuleSetId && !fit) {
          const cur = rs.find(r => r.id === gradingRuleSetId)
          if (cur?.fit_type_codi) setFit(cur.fit_type_codi)
        }
      })
      .catch(() => { if (alive) setGradingRuleSets_([]) })
    return () => { alive = false }
  }, [block])  // eslint-disable-line react-hooks/exhaustive-deps

  // Sprint ÀMBIT — el node de la peça (item → família → grup) viatja als eixos: un contenidor amb
  // àmbit aplica si el conté a ell o a un ancestre seu. Sense àmbit → fallback al garment_group.
  const nodeAxes = {
    target, construction, garmentGroup: garmentGroupCodi,
    garmentTypeId: family?.id ?? null,
    garmentTypeItemId: item?.id ?? null,
  }

  // Fits que porten a una graduació REAL per a la combinació fixada (matching estricte).
  const fitOptions = useMemo(
    () => availableFitsStrict(
      gradingRuleSets_, nodeAxes, ggCodiById, sizingResult?.size_system_id ?? null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [gradingRuleSets_, target, construction, garmentGroupCodi, family?.id, item?.id, ggCodiById, sizingResult],
  )

  const gradingAxes = { ...nodeAxes, fit }

  const skeletonPayload = () => {
    // Sprint WIZARD-COMPLET: la graduació torna al payload. `undefined` = no tocar (creació sense
    // grading / no triat); `null` = «Sense graduació» EXPLÍCIT (buida en edició). El fit NO s'escriu
    // a Model.fit_type (mapatge codi→choice lossy); viu al ruleset triat, que és qui el porta.
    const grs = noGrading ? null : (gradingRuleSetId || undefined)
    return {
      target: target || undefined,
      garment_type_id: family?.id || undefined,
      garment_type_item_id: item?.id || undefined,
      construction: construction || undefined,
      size_system_id: sizingResult?.size_system_id || undefined,
      size_run: sizingResult?.size_run || undefined,
      base_size: sizingResult?.base_size || undefined,
      grading_rule_set_id: grs,
    }
  }

  const handleCreate = async () => {
    if (!season) { setError(t('model_wizard.season_required')); setBlock(1); return }
    if (!customerId) { setError(t('model_wizard.customer_required')); setBlock(1); return }
    // B4b — GTI obligatori: és la baula del motor de temps (matriu item×task_type); sense ell
    // no es poden estimar tasques ni valorar la recepta d'un encàrrec.
    if (!item) { setError(t('model_wizard.gti_required')); setBlock(2); return }
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

  const BLOCKS = [t('model_wizard.block1'), t('model_wizard.block2'), t('model_wizard.block3'), t('model_wizard.block4')]

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
                      target={target}
                      selectedItemId={item?.id}
                      onSelect={({ family: fam, item: it }) => { setFamily(fam); setItem(it); setPicking(false); resetGrading() }}
                    />
                  </div>
                )}
              </Field>
            )}

            {target && (
              <Field label={t('model_wizard.construction')}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {CONSTRUCTIONS.map(c => (
                    <Chip key={c} active={construction === c} onClick={() => { if (construction !== c) { resetSizing(); resetGrading() } setConstruction(c) }}>{t(`model_wizard.construction_${c}`)}</Chip>
                  ))}
                </div>
              </Field>
            )}
          </div>
        )}

        {block === 3 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {(!target) ? (
              <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO }}>{t('model_wizard.no_sizes')}</p>
            ) : (
              <>
                <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, margin: 0 }}>
                  {t('model_wizard.sizes_for')} {t(`model_wizard.target_${target}`)}
                </p>
                {systems.length === 0 && <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO }}>{t('model_wizard.no_sizes')}</p>}
                {systems.map(s => {
                  const active = selSystem?.id === s.id
                  // Rang d'edat (mesos) derivat de les talles del sistema (per a systems Baby/Kids).
                  const ageMins = (s.talles || []).map(d => d.age_months_min).filter(v => v != null)
                  const ageMaxs = (s.talles || []).map(d => d.age_months_max).filter(v => v != null)
                  const ageMin = ageMins.length ? Math.min(...ageMins) : null
                  const ageMax = ageMaxs.length ? Math.max(...ageMaxs) : null
                  return (
                    <div key={s.id} onClick={() => setSelSystem(s)} style={{
                      padding: '10px 14px', borderRadius: 8, cursor: 'pointer', fontFamily: MONO,
                      border: `0.5px solid ${active ? 'var(--warn)' : 'var(--gray-l)'}`,
                      background: active ? 'var(--warn-bg)' : 'var(--white)',
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                        <span style={{ fontWeight: 500, fontSize: 'var(--fs-h3)' }}>{s.nom || s.codi}</span>
                        {s.customer_codi
                          ? <span style={{ fontSize: 'var(--fs-caption)', fontWeight: 600, padding: '1px 6px', borderRadius: 999,
                                           background: 'var(--gold-pale)', color: 'var(--gold)' }}>
                              {t('model_wizard.client_run')}: {s.customer_codi}
                            </span>
                          : <span style={{ fontSize: 'var(--fs-caption)', fontWeight: 600, padding: '1px 6px', borderRadius: 999,
                                           background: 'var(--gray-l)', color: 'var(--gray)' }}>
                              {t('model_wizard.canonical')}
                            </span>}
                      </div>
                      <div style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)' }}>{s.codi}</div>
                      {ageMin != null && ageMax != null && ageMax > 0 && (
                        <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-muted)', marginTop: 2 }}>
                          {t('model_wizard.age_months_range', { min: ageMin, max: ageMax })}
                        </div>
                      )}
                    </div>
                  )
                })}
                {selSystem && (
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

        {block === 4 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Context FIX de la peça+talles (arbre únic: no es re-tria aquí; el grup el mana l'item) */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <ReadChip label={t('model_wizard.target')} value={target ? t(`model_wizard.target_${target}`) : '—'} />
              <ReadChip label={t('model_wizard.construction')} value={construction ? t(`model_wizard.construction_${construction}`) : '—'} />
              <ReadChip label={t('model_wizard.grading_group')} value={garmentGroupCodi || '—'} />
              <ReadChip label={t('model_wizard.grading_system')} value={sizingResult?.size_system_nom || '—'} />
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: MONO, fontSize: 'var(--fs-body)', cursor: 'pointer', color: 'var(--text-main)' }}>
              <input type="checkbox" checked={noGrading}
                onChange={e => { setNoGrading(e.target.checked); if (e.target.checked) { setFit(null); setGradingRuleSetId(null) } }} />
              {t('model_wizard.no_grading')}
            </label>

            {!noGrading && !sizingResult && (
              <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, margin: 0 }}>{t('model_wizard.grading_needs_sizes')}</p>
            )}

            {!noGrading && sizingResult && (
              <>
                <Field label={t('model_wizard.pick_fit')}>
                  {fitOptions.length === 0 ? (
                    <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, margin: 0 }}>{t('model_wizard.no_grading_available')}</p>
                  ) : (
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {fitOptions.map(f => (
                        <Chip key={f.codi} active={fit === f.codi} onClick={() => { setFit(f.codi); setGradingRuleSetId(null) }}>{t(`model_wizard.fit_${f.codi}`, f.nom_en)}</Chip>
                      ))}
                    </div>
                  )}
                </Field>
                {fit && (
                  <RuleSetPicker
                    ruleSets={gradingRuleSets_}
                    garmentGroupCodiById={ggCodiById}
                    axes={gradingAxes}
                    strict
                    sizeSystemId={sizingResult?.size_system_id ?? null}
                    selectedId={gradingRuleSetId}
                    actionLabel={t('model_sheet.use_ruleset')}
                    onPick={(rs) => { setGradingRuleSetId(rs.id); setNoGrading(false) }}
                  />
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
        {block < 4 ? (
          <button type="button" disabled={block === 1 && !block1Resolved}
            onClick={() => { if (!(block === 1 && !block1Resolved)) setBlock(b => Math.min(4, b + 1)) }}
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
function ReadChip({ label, value }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, padding: '6px 12px', borderRadius: 6, border: '0.5px solid var(--gray-l)', background: 'var(--bg-card)', minWidth: 90 }}>
      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--gray)', textTransform: 'uppercase', letterSpacing: '.04em' }}>{label}</span>
      <span style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--text-main)', fontWeight: 500 }}>{value}</span>
    </div>
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
