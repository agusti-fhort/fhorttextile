import { useState, useEffect, useMemo } from 'react'
import { IconBulb } from '@tabler/icons-react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import CascadeSelector from '../components/CascadeSelector/CascadeSelector'
import CustomerSelector from '../components/CustomerSelector'
import RuleSetPicker from '../components/grading/RuleSetPicker'
import { availableFitsStrict, matchingRuleSetsStrict, TARGETS, CONSTRUCTIONS } from '../components/grading/gradingAxes'
import useAuthStore from '../store/auth'
import { models, sizeSystems, gradingRuleSets, garmentGroups, garmentTypes, garmentTypeItems } from '../api/endpoints'

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

// Etiquetes de talla d'un SizeSystem (les tres formes que retorna l'API, en ordre de preferència).
const labelsOf = (sys) => (sys?.talles || []).map(s => s.etiqueta || s.size_label || s.label).filter(Boolean)
// Un run és VÀLID dins un sistema si totes les seves talles hi són (subconjunt legítim, forma normal
// i massiva al tenant: 218 models — DIAGNOSI_MODEL_174 §B0.4).
const runCapDins = (run, labels) => run.length > 0 && run.every(l => labels.includes(l))
// S24b — l'ORDRE el mana el SizeSystem, no l'ordre de clic. `labels` ve ja ordenat per
// `SizeDefinition.ordre` (el prefetch de l'API respecta el Meta.ordering), i per tant ordenar
// per la seva posició és ordenar pel sistema. Les talles que no hi són (no hauria de passar-ne
// cap: el guard `runCapDins` ho comprova) queden al final en comptes de desaparèixer.
const ordenaPelSistema = (run, labels) =>
  [...run].sort((a, b) => {
    const ia = labels.indexOf(a), ib = labels.indexOf(b)
    return (ia < 0 ? Infinity : ia) - (ib < 0 ? Infinity : ib)
  })
// TARGETS i CONSTRUCTIONS: vocabulari ÚNIC de gradingAxes (fora la còpia privada — Onada 1). Objectes
// {codi, nom_*}; aquí només en fem servir el `codi` (l'etiqueta la resol t('model_wizard.*')).

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
  // P6 — el ruleset que l'ITEM porta com a estàndard (V1). Només SUGGEREIX: es marca i puja
  // al capdamunt del picker, mai s'assigna sol (això seria arrossegar, i el pas 4 no ho fa).
  const [itemSuggestedRsId, setItemSuggestedRsId] = useState(null)
  const [picking, setPicking] = useState(false)
  // Navegació controlada del picker de peça (CascadeSelector single, grup→ítem). Es sembra des de
  // family/item en reobrir; onConfirm (triar ítem) commita a family/item i tanca.
  const [pickAxes, setPickAxes] = useState({})
  const [construction, setConstruction] = useState(null)
  // Bloc 3 — talles (LLEI 5 CAPES: ESCALA PURA — SizeSystem, sense fit ni graduació)
  const [systems, setSystems] = useState([])
  const [selSystem, setSelSystem] = useState(null)
  const [sizeDefs, setSizeDefs] = useState([])
  const [selectedSizes, setSelectedSizes] = useState([])
  const [baseSize, setBaseSize] = useState(null)
  // Peça 4 — sistema/run/base que ja té el model (edició). NO és només memòria: és la FONT de la
  // rehidratació del pas 3 (F1.1). Sense ella el pas 4 neix cec en edició (DIAGNOSI_MODEL_174, risc #1).
  const [modelSizeSystemId, setModelSizeSystemId] = useState(null)
  const [modelSizeRun, setModelSizeRun] = useState('')
  const [modelBaseSize, setModelBaseSize] = useState(null)
  const [modelSizeSystemNom, setModelSizeSystemNom] = useState('')
  const [sizingHydrated, setSizingHydrated] = useState(false)
  const [runPerdut, setRunPerdut] = useState([])   // talles del run desat que ja no són al sistema
  // Bloc 4 — GRADUACIÓ (sprint WIZARD-COMPLET). Eixos target/construction/grup + size_system venen
  // fixats dels passos 2-3 (arbre únic: el grup el mana l'item, no es re-tria); l'usuari només tria FIT.
  const [gradingRuleSets_, setGradingRuleSets_] = useState([])
  const [ggCodiById, setGgCodiById] = useState({})
  const [fit, setFit] = useState(null)               // codi de fit triat (eix del matching)
  const [gradingRuleSetId, setGradingRuleSetId] = useState(null)  // ruleset triat (null = cap)
  const [noGrading, setNoGrading] = useState(false)  // «Sense graduació» explícit
  const [autoProposed, setAutoProposed] = useState(false)  // B1: ruleset preseleccionat per única coincidència
  const [gradingDropped, setGradingDropped] = useState(false)  // F1.5: el ruleset previ ja no casa amb els eixos
  const [modelGarmentGrup, setModelGarmentGrup] = useState(null)  // grup del model en edició (prefill)

  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const resetGrading = () => { setFit(null); setGradingRuleSetId(null); setNoGrading(false); setAutoProposed(false); setGradingDropped(false) }

  // LLEI 5 CAPES: el pas Talles retorna NOMÉS escala (sistema/run/base). La graduació (capa 4) es
  // tria per separat a la fitxa (RuleSetCard→update-step2). Aquí NO s'arrossega grading_rule_set_id.
  const sizingResult = useMemo(() => (
    // F1.3 — la base ha de ser DINS el run: una base fora del run no és una escala vàlida
    // (abans passava el filtre i el pas 4 s'obria amb un Guardar gris i cap motiu visible).
    (selSystem && selectedSizes.length > 0 && baseSize && selectedSizes.includes(baseSize)) ? {
      size_system_id: selSystem.id,
      size_run: selectedSizes.join('·'),
      base_size: baseSize,
      size_system_nom: selSystem.nom,
    } : null
  ), [selSystem, selectedSizes, baseSize])

  const resetSizing = () => { setSelSystem(null); setSelectedSizes([]); setBaseSize(null); setSizeDefs([]) }

  // F1.3 — quina de les tres peces del pas 3 falta (l'ordre és el del flux: sistema → run → base).
  const sizingMissing = !selSystem ? 'system'
    : (selectedSizes.length === 0 ? 'run'
      : ((!baseSize || !selectedSizes.includes(baseSize)) ? 'base' : null))

  // Coherència Onada 1+2: en CANVIAR el target, si la família seleccionada ja no és al catàleg filtrat
  // pel nou target, es neteja família+item (+graduació, que en depèn del garment). Si SÍ hi és, es
  // conserva (no molestar l'usuari). Comprovació amb el MATEIX endpoint que la cascada compartida
  // (garment-types/?target=) i NOMÉS en acció d'usuari — el prefill d'edició no passa per aquí.
  const onPickTarget = (codi) => {
    if (codi === target) return
    setTarget(codi)
    if (!family) return
    garmentTypes.list({ target: codi, actiu: 'true', page_size: 500 })
      .then(r => {
        const fams = r.data?.results ?? r.data ?? []
        if (!fams.some(f => f.id === family.id)) { setFamily(null); setItem(null); resetGrading() }
      })
      .catch(() => {})
  }

  // Un cop hi ha sistema i run, la talla base és obligatòria i ha de ser DINS el run. Abans això
  // només es demanava quan el sistema canviava respecte al model (`systemChanged`), i el pas 4 podia
  // quedar cec sense dir-ho. Ara la condició és la real, valgui per a creació o edició.
  const baseSizeInvalid = !!(selSystem && selectedSizes.length > 0 && (!baseSize || !selectedSizes.includes(baseSize)))

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
      setModelBaseSize(d.base_size_label || null)
      setModelSizeSystemNom(d.size_system_nom || '')
      // Bloc 4 — graduació vigent (edició): grup canònic (sempre present via garment_type.grup) i
      // ruleset actual, perquè el pas 4 mostri la selecció i permeti canviar-la (cas Regular→Slim).
      setModelGarmentGrup(d.garment_type_grup || null)
      if (d.grading_rule_set) setGradingRuleSetId(d.grading_rule_set)
      if (d.garment_type) setFamily({ id: d.garment_type, nom_en: d.garment_type_nom, grup: d.garment_type_grup })
      if (d.garment_type_item) setItem({ id: d.garment_type_item, name: d.garment_type_item_nom })
    }).catch(() => setError(t('model_wizard.conn_error')))
    return () => { alive = false }
  }, [id, isEditMode])

  // Bloc 3 (LLEI 5 CAPES) — carrega SizeSystems PURS quan hi ha target i estem al bloc 3.
  // Filtra pel target de la peça (target_codis, buit = universal) i descarta systems sense talles.
  // Escala pura: SENSE fit, SENSE construcció, SENSE graduació. Pre-selecciona el primer en creació.
  // F1.1 — també al pas 4: entrant per «Canviar graduació» (?block=4) els sistemes no es carregaven
  // mai i la rehidratació no tenia de què estirar (DIAGNOSI_MODEL_174, risc #7).
  useEffect(() => {
    if (!target || (block !== 3 && block !== 4)) return
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

  // F1.1 — REHIDRATACIÓ del pas 3 en edició: el que el model ja té desat (size_system + run + base)
  // torna a ser la selecció viva. Sense això `sizingResult` era null i tot el pas 4 naixia cec.
  // Corre un sol cop (`sizingHydrated`) perquè no trepitgi mai una tria posterior de la tècnica.
  useEffect(() => {
    if (!isEditMode || sizingHydrated) return
    if (!systems.length || modelSizeSystemId == null) return
    const sys = systems.find(s => s.id === modelSizeSystemId)
    if (!sys) return   // el sistema del model no és a l'oferta (inactiu o d'un altre target): no forcem res
    const labels = labelsOf(sys)
    // El run es desa amb '·' (skeletonPayload); tolerem ','/';' d'imports antics.
    const desat = modelSizeRun.split(/[·,;]/).map(x => x.trim()).filter(Boolean)
    const run = desat.filter(l => labels.includes(l))
    const vius = run.length ? run : labels
    setSelSystem(sys)
    setSizeDefs(sys.talles || [])
    setSelectedSizes(vius)
    setBaseSize(modelBaseSize && vius.includes(modelBaseSize) ? modelBaseSize : null)
    // El run desat pot portar talles que ja no són al sistema (talles retirades, deriva de dades).
    // No es poden rehidratar, però tampoc es descarten en silenci: desar amb el run escurçat
    // reescriuria size_run_model, i això s'ha de veure abans de prémer Guardar.
    setRunPerdut(desat.filter(l => !labels.includes(l)))
    setSizingHydrated(true)
  }, [systems, isEditMode, sizingHydrated, modelSizeSystemId, modelSizeRun, modelBaseSize])

  // Bloc 3 — talles del sistema triat (venen amb el propi SizeSystem, sense crida extra).
  // F1.2 — aquest efecte JA NO substitueix el run: si el que hi ha cap dins el sistema, es conserva.
  // Substituir un run és un acte conscient i viu a `pickSystem` (confirmació explícita), mai aquí.
  useEffect(() => {
    if (!selSystem) return
    const defs = selSystem.talles || []
    setSizeDefs(defs)
    const labels = labelsOf(selSystem)
    if (runCapDins(selectedSizes, labels)) return
    setSelectedSizes(labels)
    setBaseSize(labels[Math.floor(labels.length / 2)] || labels[0] || null)
  }, [selSystem])  // eslint-disable-line react-hooks/exhaustive-deps

  // F1.2 — GUARD DEL RUN. Triar un sistema no substitueix mai el run en silenci:
  //  · el run existent cap dins el sistema nou → es CONSERVA (amb la seva talla base);
  //  · no hi cap (canvi real de sistema) → avís conscient amb el cost exacte (D1: mai en silenci).
  const pickSystem = (s) => {
    if (selSystem?.id === s.id) return
    const labels = labelsOf(s)
    if (selectedSizes.length > 0 && !runCapDins(selectedSizes, labels)
      && !window.confirm(t('model_wizard.size_run_replace_confirm', { from: selectedSizes.length, to: labels.length, sistema: s.nom || s.codi }))) return
    setSelSystem(s)
  }

  // Bloc 4 — el grup canònic de la peça (eix fix del matching). Prové de l'ITEM (arbre únic):
  // family.grup en creació; garment_type.grup del model en edició. Mai es re-tria a mà.
  const garmentGroupCodi = family?.grup ?? modelGarmentGrup ?? null

  // Bloc 4 — carrega rulesets + mapa grup id→codi quan s'entra al pas. En edició, deriva el fit
  // vigent del ruleset del model perquè el picker el mostri seleccionat.
  useEffect(() => {
    if (block !== 4) return
    let alive = true
    Promise.all([gradingRuleSets.list({ page_size: 200, amb_regles: 1 }), garmentGroups.list({ page_size: 200 })])
      .then(([rsRes, ggRes]) => {
        if (!alive) return
        const rs = rsRes.data?.results ?? (Array.isArray(rsRes.data) ? rsRes.data : [])
        const gg = ggRes.data?.results ?? (Array.isArray(ggRes.data) ? ggRes.data : [])
        const map = {}; gg.forEach(g => { map[g.id] = g.codi })
        setGradingRuleSets_(rs); setGgCodiById(map)
      })
      .catch(() => { if (alive) setGradingRuleSets_([]) })
    return () => { alive = false }
  }, [block])  // eslint-disable-line react-hooks/exhaustive-deps

  // El fit vigent es deriva del ruleset del model. Viu en un efecte PROPI perquè al camí
  // «Canviar graduació» (?block=4) el bloc s'obre al mount: l'efecte de càrrega corria amb
  // gradingRuleSetId encara null (el prefill no havia resolt) i el fit no es derivava mai —
  // el picker quedava amagat justament al camí que F1.1 volia rescatar.
  useEffect(() => {
    if (fit || !gradingRuleSetId || !gradingRuleSets_.length) return
    const cur = gradingRuleSets_.find(r => r.id === gradingRuleSetId)
    if (cur?.fit_type_codi) setFit(cur.fit_type_codi)
  }, [gradingRuleSets_, gradingRuleSetId, fit])

  // P6 — l'estàndard de graduació de l'item (V1) es llegeix per SUGGERIR-LO al pas 4. És el primer
  // lector real d'aquesta FK: fins ara ningú la consumia i només feia de semàfor al catàleg d'items.
  // Si l'item no en porta, o la lectura falla, el picker es comporta exactament com abans.
  useEffect(() => {
    if (!item?.id) { setItemSuggestedRsId(null); return }
    let viu = true
    garmentTypeItems.get(item.id)
      .then(({ data }) => { if (viu) setItemSuggestedRsId(data?.grading_rule_set ?? null) })
      .catch(() => { if (viu) setItemSuggestedRsId(null) })
    return () => { viu = false }
  }, [item?.id])

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

  // F1.3 — eixos del matching estricte que encara no estan resolts. Sense això, qualsevol eix a null
  // buidava la llista i la UI ho reportava com «no hi ha cap joc de regles» (motiu fals).
  const eixosGradingMancants = [
    !target && t('grading.axis_target'),
    !construction && t('grading.axis_construction'),
    !garmentGroupCodi && t('grading.axis_group'),
  ].filter(Boolean)

  // B1 — coincidències estrictes per als eixos FIXATS (incloent el fit triat). Consumeix el matcher
  // canònic de gradingAxes.js (no es duplica cap lògica aquí).
  const strictMatches = useMemo(
    () => matchingRuleSetsStrict(
      gradingRuleSets_, gradingAxes, ggCodiById, sizingResult?.size_system_id ?? null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [gradingRuleSets_, target, construction, garmentGroupCodi, family?.id, item?.id, fit, ggCodiById, sizingResult],
  )

  // B1 — autoselecció quan la coincidència és ÚNICA: preselecciona l'únic ruleset possible. Visible
  // (bàner «proposat automàticament») i REVOCABLE (canviar de card, «Sense graduació» o canviar fit).
  // No dispara si ja hi ha tria (manual o hidratada en edició) ni amb 0/>1 candidats.
  useEffect(() => {
    if (noGrading || !fit || !sizingResult) return
    if (gradingRuleSetId != null) return
    if (strictMatches.length === 1) {
      setGradingRuleSetId(strictMatches[0].id)
      setAutoProposed(true)
    }
  }, [strictMatches, fit, noGrading, sizingResult, gradingRuleSetId])

  // F1.5 — el ruleset hidratat en edició no es netejava mai encara que deixés de casar amb els eixos
  // triats, i skeletonPayload seguia enviant l'id antic (risc #8). Es neteja, i es DIU (mai en silenci).
  useEffect(() => {
    if (noGrading || gradingRuleSetId == null) return
    if (!gradingRuleSets_.length || !fit || !sizingResult) return
    // Només si el ruleset és a la llista carregada: si no hi és (p.ex. sense regles actives, filtrat
    // per amb_regles=1) no l'hem de jutjar aquí — D1 el bloqueja a la porta del backend.
    if (!gradingRuleSets_.some(rs => rs.id === gradingRuleSetId)) return
    if (strictMatches.some(rs => rs.id === gradingRuleSetId)) return
    setGradingRuleSetId(null)
    setAutoProposed(false)
    setGradingDropped(true)
  }, [strictMatches, gradingRuleSets_, fit, sizingResult, gradingRuleSetId, noGrading])

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

  // D1 — el backend valida el grading ABANS d'assignar-lo i parla en clar: `message` és per a
  // la tècnica, no per al log. Abans es feia JSON.stringify(data) i el motiu quedava enterrat.
  // S24b — la porta única del run rebutja les talles que el SizeSystem no coneix i envia la
  // llista al payload (`codi`:'talles_desconegudes'). Es tradueix aquí: les etiquetes són
  // dades de domini i no es tradueixen, el text que les envolta sí.
  const errMsg = (e) => {
    const d = e.response?.data
    if (d?.codi === 'talles_desconegudes') {
      return t('model_wizard.unknown_sizes', { sizes: (d.etiquetes_desconegudes || []).join(', ') })
    }
    return d?.message || d?.error || (d ? JSON.stringify(d) : t('model_wizard.conn_error'))
  }

  // D1 — grading d'un ALTRE client: 409 que NO bloqueja. És un flux de taller legítim (aplicar
  // la forma d'un altre client), però ha de ser un acte conscient → es confirma i es reintenta.
  const confirmaAltreClient = (e) => {
    const d = e.response?.data
    if (e.response?.status !== 409 || d?.tipus !== 'ruleset_altre_client') return false
    return window.confirm(`${d.message}\n\n${t('model_wizard.grading_other_customer_confirm')}`)
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
      const payload = {
        year, season, customer_id: customerId, ref_client: refClient,
        nom_prenda: nomPrenda, descripcio, collection,
        data_objectiu: dataObjectiu || null,
        ...skeletonPayload(),
      }
      let r
      try {
        r = await models.createWizard(payload)
      } catch (e) {
        if (!confirmaAltreClient(e)) throw e
        r = await models.createWizard({ ...payload, confirmar_altre_client: true })
      }
      navigate(`/models/${r.data.id}`)
    } catch (e) {
      setError(errMsg(e))
    } finally { setSaving(false) }
  }

  const handleSaveEdit = async () => {
    if (!customerId) { setError(t('model_wizard.customer_required')); setBlock(1); return }
    setSaving(true); setError('')
    try {
      // Edit: el camp FK del serializer és `customer` (rep l'id); codi_client = el camp de text.
      await models.update(id, { customer: customerId, codi_client: refClient, nom_prenda: nomPrenda, descripcio, collection, data_objectiu: dataObjectiu || null })
      const payload = skeletonPayload()
      try {
        await models.updateStep2(id, payload)
      } catch (e) {
        if (!confirmaAltreClient(e)) throw e
        await models.updateStep2(id, { ...payload, confirmar_altre_client: true })
      }
      navigate(`/models/${id}`)
    } catch (e) {
      setError(errMsg(e))
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

      {/* El run desat portava talles que ja no són al sistema del model: no s'han pogut rehidratar
          i desar les reescriuria. Es diu SEMPRE (a qualsevol pas), abans de prémer Guardar. */}
      {runPerdut.length > 0 && (
        <div style={{ ...errBox, background: 'var(--warn-bg)', color: 'var(--warn)', border: '0.5px solid var(--warn)' }}>
          {t('model_wizard.run_lost_sizes', { talles: runPerdut.join(' · ') })}
        </div>
      )}

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
                  <Chip key={tg.codi} active={target === tg.codi} onClick={() => onPickTarget(tg.codi)}>{t(`model_wizard.target_${tg.codi}`)}</Chip>
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
                    <button type="button" onClick={() => {
                      setPickAxes({ target, garmentGroup: family?.grup ?? null, garmentTypeId: family?.id ?? null, garmentTypeItemId: item?.id ?? null })
                      setPicking(true)
                    }} style={ghostBtn}>{t('model_wizard.change')}</button>
                  </div>
                ) : (
                  <div style={{ maxHeight: 460, border: '0.5px solid var(--gray-l)', borderRadius: 8, overflowY: 'auto', padding: 14 }}>
                    <CascadeSelector
                      mode="single"
                      minLevel="group"
                      maxLevel="item"
                      stopPolicy="require-item"
                      target={target}
                      value={pickAxes}
                      onChange={setPickAxes}
                      onConfirm={({ family: fam, item: it }) => { setFamily(fam); setItem(it); setPicking(false); resetGrading() }}
                    />
                  </div>
                )}
              </Field>
            )}

            {target && (
              <Field label={t('model_wizard.construction')}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {CONSTRUCTIONS.map(c => (
                    <Chip key={c.codi} active={construction === c.codi} onClick={() => { if (construction !== c.codi) { resetSizing(); resetGrading() } setConstruction(c.codi) }}>{t(`model_wizard.construction_${c.codi}`)}</Chip>
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
                    <div key={s.id} onClick={() => pickSystem(s)} style={{
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
                        {/* F1.4 — quin d'aquests sistemes és EL DEL MODEL. No es filtra per client
                            (D1: les eines del tècnic s'ofereixen senceres i s'acoten amb informació,
                            no amb ocultació); es marca, que és el que evitava el parany del 174. */}
                        {isEditMode && modelSizeSystemId === s.id && (
                          <span style={{ fontSize: 'var(--fs-caption)', fontWeight: 600, padding: '1px 6px', borderRadius: 999,
                                         background: 'var(--white)', color: 'var(--warn)', border: '0.5px solid var(--warn)' }}>
                            {t('model_wizard.model_size_system')}
                          </span>
                        )}
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
                        // S24b — el toggle APENDIA (`[...prev, label]`) i l'ordre de clic acabava
                        // persistit tal qual: és l'origen del run `XS·S·L·XXS·M` del model 166.
                        // Ara s'ordena pel sistema en marcar, de manera que la tira de talla base
                        // de sota (que pinta `selectedSizes`) també es veu en ordre.
                        return <Chip key={label} active={active} onClick={() => setSelectedSizes(prev => active ? prev.filter(x => x !== label) : ordenaPelSistema([...prev, label], labelsOf(selSystem)))}>{label}</Chip>
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
              {/* F1.3 — fallback al sistema DEL MODEL (com fa la fitxa, ModelSheet): un model que en té
                  un no pot pintar '—'. El guió queda per als models que de debò no en tenen. */}
              <ReadChip label={t('model_wizard.grading_system')} value={sizingResult?.size_system_nom || modelSizeSystemNom || '—'} />
            </div>

            <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: MONO, fontSize: 'var(--fs-body)', cursor: 'pointer', color: 'var(--text-main)' }}>
              <input type="checkbox" checked={noGrading}
                onChange={e => { setNoGrading(e.target.checked); setAutoProposed(false); if (e.target.checked) { setFit(null); setGradingRuleSetId(null) } }} />
              {t('model_wizard.no_grading')}
            </label>

            {/* F1.3 — el missatge diu QUÈ falta de veritat. Abans deia sempre «defineix les talles»
                encara que el que faltés fos només la talla base (risc #2 de la diagnosi 174). */}
            {!noGrading && !sizingResult && (
              <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, margin: 0 }}>
                {t(`model_wizard.grading_needs_${sizingMissing}`)}
              </p>
            )}

            {!noGrading && sizingResult && (
              <>
                <Field label={t('model_wizard.pick_fit')}>
                  {fitOptions.length === 0 ? (
                    <p style={{ fontSize: 'var(--fs-body)', color: 'var(--gray)', fontFamily: MONO, margin: 0 }}>
                      {/* F1.3 — «cap graduació disponible» era el motiu FALS quan el que faltava era un
                          eix (matchers que tornen [] en silenci, risc #4). Es diu quin eix falta. */}
                      {eixosGradingMancants.length > 0
                        ? t('model_wizard.grading_missing_axes', { eixos: eixosGradingMancants.join(' · ') })
                        : t('model_wizard.no_grading_available')}
                    </p>
                  ) : (
                    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                      {fitOptions.map(f => (
                        <Chip key={f.codi} active={fit === f.codi} onClick={() => { setFit(f.codi); setGradingRuleSetId(null); setAutoProposed(false) }}>{t(`model_wizard.fit_${f.codi}`, f.nom_en)}</Chip>
                      ))}
                    </div>
                  )}
                </Field>
                {gradingDropped && (
                  <div style={{ fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--warn)', background: 'var(--warn-bg)',
                                border: '0.5px solid var(--warn)', borderRadius: 6, padding: '8px 12px' }}>
                    {t(gradingRuleSetId != null ? 'model_wizard.grading_dropped_replaced' : 'model_wizard.grading_dropped')}
                  </div>
                )}
                {fit && autoProposed && gradingRuleSetId != null && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontFamily: MONO, fontSize: 'var(--fs-body)', color: 'var(--gold)', background: 'var(--gold-pale)', border: '0.5px solid var(--gold)', borderRadius: 6, padding: '8px 12px' }}>
                    <IconBulb size={16} stroke={1.5} />
                    {t('model_wizard.grading_auto_proposed')}
                  </div>
                )}
                {fit && (
                  <RuleSetPicker
                    ruleSets={gradingRuleSets_}
                    garmentGroupCodiById={ggCodiById}
                    axes={gradingAxes}
                    strict
                    sizeSystemId={sizingResult?.size_system_id ?? null}
                    selectedId={gradingRuleSetId}
                    suggestedId={itemSuggestedRsId}
                    actionLabel={t('model_sheet.use_ruleset')}
                    onPick={(rs) => { setGradingRuleSetId(rs.id); setNoGrading(false); setAutoProposed(false) }}
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
