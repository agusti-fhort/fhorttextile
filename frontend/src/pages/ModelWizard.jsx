import { useState, useEffect, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import CascadeSelector from '../components/CascadeSelector/CascadeSelector'
import CustomerSelector from '../components/CustomerSelector'
import { matchingRuleSetsStrict, TARGETS, CONSTRUCTIONS, FITS } from '../components/grading/gradingAxes'
// Els àtoms de UI i el PAS DE GRADUACIÓ viuen fora des del 31/07: el pas s'obre també com a
// overlay sobre Mesures, i ha de ser el MATEIX component als dos llocs (mai una còpia).
import GraduacioPanel from '../components/grading/GraduacioPanel'
import { Chip, Field, labelStyle, MONO } from '../components/grading/wizardUI'
import TargetLabel from '../components/grading/TargetLabel'
import useAuthStore from '../store/auth'
import { models, sizeSystems, gradingRuleSets, garmentGroups, garmentTypes, garmentTypeItems, itemBaseMeasurements, sizingProfiles } from '../api/endpoints'

// Wizard d'ESQUELET unificat. Un sol flux de creació (4 blocs) + mode edició.
// Crea el Model amb identificació + garment def (família→ITEM = baula del motor) + talles + GRADUACIÓ.
// Sprint WIZARD-COMPLET: la graduació (pas 4) torna al wizard, amb matching ESTRICTE (size_system
// obligatori, cap comodí NULL) i opció explícita «Sense graduació». POM detallat NO aquí.

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

// EL WIZARD, també ENCASTAT (31/07). El botó «Graduació» de Mesures obre AQUEST wizard —el
// d'editar model, el que ja existeix i funciona— posicionat al pas 4, com a calaix lateral
// sobre la taula. No hi ha cap pantalla nova de graduació: si al pas 4 hi falta la
// construcció, l'usuari fa «← Enrere» fins al pas 2, la posa i torna. Aquell atzucac
// s'acaba aquí.
//
// Encastat vs. ruta és NOMÉS marc i navegació:
//   · `embedModelId` substitueix el `:id` de la ruta (mode edició igualment);
//   · `initialBlock` obre directament al pas que interessa;
//   · `onClose`/`onSaved` substitueixen els `navigate()`, que dins d'un overlay se'n durien
//     l'usuari de la pantalla on està treballant.
// La LÒGICA (hidratació, gates, payload, desat) no es toca: és la mateixa als dos modes.
export default function ModelWizard({ embedModelId = null, initialBlock = null,
                                      onClose = null, onSaved = null, onUsarJoc = null }) {
  const routeParams = useParams()
  const id = embedModelId != null ? String(embedModelId) : routeParams.id
  const encastat = embedModelId != null
  const navigate = useNavigate()
  const { t } = useTranslation()
  const isEditMode = !!id
  const me = useAuthStore(s => s.user)
  const canConfigure = !!me?.capabilities?.includes('configure')

  // WIZARD-COMPLET C.3 — «Canviar graduació» des de la fitxa obre el wizard directament al pas 4.
  const [block, setBlock] = useState(initialBlock || 1)
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
  // SET-1 · A4 — nom OPCIONAL per peça, per id de GarmentTypeItemPart. Buit ⇒ el backend fa
  // servir el `nom_peca` que la composició del catàleg ja declara.
  const [setNoms, setSetNoms] = useState({})
  // El ruleset que el CATÀLEG proposa per a la combinació (SizingProfile). Només SUGGEREIX: es
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
  const [modelFitType, setModelFitType] = useState('')   // `Model.fit_type` desat (edició)
  const [modelSizeRun, setModelSizeRun] = useState('')
  const [modelBaseSize, setModelBaseSize] = useState(null)
  const [sizingHydrated, setSizingHydrated] = useState(false)
  const [runPerdut, setRunPerdut] = useState([])   // talles del run desat que ja no són al sistema
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

  // El fit es pregunta al pas Peça (abans de la peça), i per tant NO es pot esborrar en triar la
  // peça: seria fer caure la resposta que acabes de donar. `resetGrading` neteja la tria de
  // graduació; `resetGradingIFit` afegeix el fit i es reserva per als canvis que el invaliden de
  // debò (canviar de construcció: els fits disponibles en depenen).
  const resetGrading = () => { setGradingRuleSetId(null); setNoGrading(false) }
  const resetGradingIFit = () => { setFit(null); resetGrading() }

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


  // Coherència Onada 1+2: en CANVIAR el target, si la família seleccionada ja no és al catàleg filtrat
  // pel nou target, es neteja família+item (+graduació, que en depèn del garment). Si SÍ hi és, es
  // conserva (no molestar l'usuari). Comprovació amb el MATEIX endpoint que la cascada compartida
  // (garment-types/?target=) i NOMÉS en acció d'usuari — el prefill d'edició no passa per aquí.
  const onPickTarget = (codi) => {
    if (codi === target) return
    // El target ara és un FILTRE i es pot DESMARCAR (P6): sense target, el catàleg surt sencer.
    // Desmarcar no pot invalidar la peça ja triada —no s'ha estret res—, o sigui que no es
    // consulta la compatibilitat ni es neteja res.
    if (!codi) { setTarget(null); return }
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
      setModelFitType(d.fit_type || '')
      setModelBaseSize(d.base_size_label || null)
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

  // F1.3 — quina de les tres peces del pas 3 falta (l'ordre és el del flux: sistema → run → base).
  const sizingMissing = !selSystem ? 'system'
    : (selectedSizes.length === 0 ? 'run'
      : ((!baseSize || !selectedSizes.includes(baseSize)) ? 'base' : null))

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
    if (fit) return
    // El fit del RULESET mana quan n'hi ha (és el que el model gradua de debò)…
    if (gradingRuleSetId && gradingRuleSets_.length) {
      const cur = gradingRuleSets_.find(r => r.id === gradingRuleSetId)
      if (cur?.fit_type_codi) { setFit(cur.fit_type_codi); return }
    }
    // …i si el model encara NO té graduació, se sembra del seu propi `fit_type` (31/07).
    // Sense això, entrar al pas 4 des de Mesures deixava el picker amagat rere un `fit` null
    // en el cas normal —un model sense graduació, que és qui hi ve— i la pantalla es veia
    // completa i buida alhora: tots els eixos informats i cap joc a la vista.
    if (isEditMode && modelFitType) setFit(String(modelFitType).toUpperCase())
  }, [gradingRuleSets_, gradingRuleSetId, fit, isEditMode, modelFitType])


  // Sprint ÀMBIT — el node de la peça (item → família → grup) viatja als eixos: un contenidor amb
  // àmbit aplica si el conté a ell o a un ancestre seu. Sense àmbit → fallback al garment_group.
  const nodeAxes = {
    target, construction, garmentGroup: garmentGroupCodi,
    garmentTypeId: family?.id ?? null,
    garmentTypeItemId: item?.id ?? null,
  }


  const gradingAxes = { ...nodeAxes, fit }


  // B1 — coincidències estrictes per als eixos FIXATS (incloent el fit triat). Consumeix el matcher
  // canònic de gradingAxes.js (no es duplica cap lògica aquí).
  const strictMatches = useMemo(
    () => matchingRuleSetsStrict(
      gradingRuleSets_, gradingAxes, ggCodiById, sizingResult?.size_system_id ?? null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [gradingRuleSets_, target, construction, garmentGroupCodi, family?.id, item?.id, fit, ggCodiById, sizingResult],
  )

  // B1 — autoselecció RETIRADA (31/07). Preseleccionava l'únic ruleset compatible en quant el
  // `fit` quedava resolt, i el `fit` es tria al pas de PEÇA: un model podia NÉIXER graduat sense
  // que ningú hagués passat pel pas de graduació ni l'hagués vist. Amb el pas ja retirat, això
  // hauria estat una assignació invisible — exactament el contrari de la llei: el model neix
  // NET i la graduació s'incorpora pel gest (botó Graduació · Propagar), amb acceptació
  // explícita. La proposta del catàleg no s'ha perdut: viu allà, que és on hi ha un botó
  // d'Acceptar al davant.

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
        // SET-1 — noms per peça (només els omplerts; el backend cau al `nom_peca` del catàleg).
        ...(item?.is_set ? { noms_peces: Object.fromEntries(
          Object.entries(setNoms).filter(([, v]) => (v || '').trim())) } : {}),
        ...skeletonPayload(),
      }
      let r
      try {
        r = await models.createWizard(payload)
      } catch (e) {
        if (!confirmaAltreClient(e)) throw e
        r = await models.createWizard({ ...payload, confirmar_altre_client: true })
      }
      // SET-1 · A4 (forat #5 del dimensionat) — la resposta d'un CONJUNT no porta `id` sinó
      // {garment_set_id, codi_base, num_pieces, pieces[]}. Fins ara `navigate('/models/' +
      // r.data.id)` hauria anat a `/models/undefined` el dia que s'hi creés un conjunt.
      const pieces = r.data?.pieces
      if (Array.isArray(pieces) && pieces.length) {
        navigate(`/models/${pieces[0].id}`)
        return
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
      if (encastat) { onSaved?.(); return }
      navigate(`/models/${id}`)
    } catch (e) {
      setError(errMsg(e))
    } finally { setSaving(false) }
  }

  // C5-UI/P6 — EL PAS DE GRADUACIÓ DESAPAREIX DEL WIZARD (decisió 31/07): el model neix NET i la
  // graduació s'incorpora pel seu gest, amb acceptació explícita al davant. Un pas dins del wizard
  // convidava a assignar-la de passada, sense mirar-se la regla.
  //
  // Sobreviu UNA porta, i és una porta EXPLÍCITA: «Canviar graduació» des de la fitxa obre el
  // wizard directament aquí (`?block=4`). Aquell gest no és néixer, és canviar el que ja hi ha, i
  // treure'l deixaria l'enllaç apuntant al buit.
  const mostraGrading = initialBlock === 4
  const BLOCKS = [t('model_wizard.block1'), t('model_wizard.block2'), t('model_wizard.block3'),
    ...(mostraGrading ? [t('model_wizard.block4')] : [])]

  // GATE entre contenidors: el client mana el prefix del codi i l'abast de la seqüència, així que
  // els passos 2 (Peça) i 3 (Talles) queden bloquejats fins que el pas 1 estigui resolt
  // (CLIENT + ANY + TEMPORADA → referència interna generada en conseqüència).
  const block1Resolved = !!(customerId && year && season)

  return (
    <div style={encastat ? {} : { maxWidth: 820, margin: '0 auto', padding: '2rem 1rem' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 16, marginBottom: 18 }}>
        <h1 style={{ fontFamily: MONO, fontSize: encastat ? 'var(--fs-h3)' : 'var(--fs-h1)', fontWeight: 500, margin: 0 }}>
          {isEditMode ? t('model_wizard.title_edit') : t('model_wizard.title_new')}
        </h1>
        <button type="button" onClick={() => (encastat ? onClose?.() : navigate('/models'))} style={linkBtn}>
          ✕ {t('model_wizard.cancel')}
        </button>
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
            {/* C5-UI/P6 — EL PAS 2 COL·LAPSA A UNA SOLA TRIA: L'ITEM.
                Target, construcció i fit eren PORTES: sense target no hi havia construcció, sense
                construcció no hi havia fit, i sense els tres no es veia el catàleg. Es preguntaven
                dues vegades (aquí i al pas de graduació) i permetien contradir-se. Ara són
                FILTRES: acosten, no delimiten (D-31.3), i el navegador de peces hi és des del
                primer moment. Es deriven de la peça i queden editables si aquest model se'n desvia.

                🔑 LLEI RELAXADA (Agus, 04/08): els eixos filtren NOMÉS si la peça els té
                informats. Brownie no separa punt de plana i el sistema no li ho ha d'exigir. Avui
                el veredicte de compatibilitat el calcula el backend per FAMÍLIA (SizingProfile) i
                «sense perfil» hi compta com a incompatible → v. el PENDENT anotat al commit. El
                que sí que es compleix ja: res queda BLOQUEJAT, tot segueix sent triable. */}
            <div style={{ ...summaryBox, alignItems: 'flex-start', flexDirection: 'column',
                          gap: 12, background: 'var(--white)' }}>
              <div style={{ ...labelStyle, marginBottom: 0 }}>{t('model_wizard.axes_filter')}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {TARGETS.map(tg => (
                  <Chip key={tg.codi} active={target === tg.codi}
                    onClick={() => onPickTarget(target === tg.codi ? '' : tg.codi)}>
                    <TargetLabel
                      codi={tg.codi}
                      nomFallback={tg.nom_en}
                      franjaColor={target === tg.codi ? 'var(--white)' : 'var(--text-muted)'}
                    />
                  </Chip>
                ))}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {CONSTRUCTIONS.map(c => (
                  <Chip key={c.codi} active={construction === c.codi}
                    onClick={() => {
                      const nou = construction === c.codi ? '' : c.codi
                      if (construction !== nou) { resetSizing(); resetGradingIFit() }
                      setConstruction(nou)
                    }}>{t(`model_wizard.construction_${c.codi}`)}</Chip>
                ))}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {FITS.map(f => (
                  <Chip key={f.codi} active={fit === f.codi}
                    onClick={() => {
                      const nou = fit === f.codi ? '' : f.codi
                      if (fit !== nou) setGradingRuleSetId(null)
                      setFit(nou)
                    }}>
                    {t(`model_wizard.fit_${f.codi}`, f.nom_en)}
                  </Chip>
                ))}
              </div>
              <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                {t('model_wizard.axes_filter_hint')}
              </div>
            </div>

            {(
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
                ) : null}
                {/* SET-1 · A4 — si l'item triat és un CONJUNT, la composició es diu AQUÍ, en
                    LECTURA: és el catàleg qui la declara (decisió 3) i el wizard no la
                    negocia. L'únic editable és el nom de cada peça, i és opcional: buit ⇒ el
                    backend fa servir el `nom_peca` de la composició. */}
                {item?.is_set && !picking ? (
                  <div style={{ border: '0.5px solid var(--gold)', borderRadius: 8, padding: 14,
                                background: 'var(--gold-pale)', display: 'flex',
                                flexDirection: 'column', gap: 10 }}>
                    <div style={{ fontSize: 'var(--fs-body)', color: 'var(--gold)', fontWeight: 600 }}>
                      {t('model_wizard.set_title', { total: (item.parts || []).length })}
                    </div>
                    <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>
                      {t('model_wizard.set_hint')}
                    </div>
                    {(item.parts || []).map((p, i) => (
                      <div key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)',
                                       color: 'var(--gold)', minWidth: 28 }}>
                          {String(p.ordre || i + 1).padStart(2, '0')}
                        </span>
                        <span style={{ fontSize: 'var(--fs-body)', minWidth: 160 }}>
                          {p.part_item_name || p.part_item_code}
                        </span>
                        <input
                          value={setNoms[p.id] ?? ''}
                          onChange={e => setSetNoms(prev => ({ ...prev, [p.id]: e.target.value }))}
                          placeholder={p.nom_peca || t('model_wizard.set_piece_name_ph')}
                          style={{ ...inputStyle, flex: 1 }} />
                      </div>
                    ))}
                  </div>
                ) : null}
                {item && !picking ? null : (
                  <div style={{ maxHeight: 460, border: '0.5px solid var(--gray-l)', borderRadius: 8, overflowY: 'auto', padding: 14 }}>
                    <CascadeSelector
                      mode="single"
                      minLevel="group"
                      maxLevel="item"
                      stopPolicy="require-item"
                      target={target}
                      compat={{ construction, fit }}
                      value={pickAxes}
                      onChange={setPickAxes}
                      onConfirm={({ family: fam, item: it }) => { setFamily(fam); setItem(it); setPicking(false); resetGrading() }}
                    />
                  </div>
                )}
              </Field>
            )}

            {/* LA TARGETA DE SEMBRA — què rebrà el model d'aquesta peça, abans de triar-la. Un
                desplegable no ho pot dir: «Blusa» no diu si el model naixerà amb 47 POMs buits o
                amb 47 mesurats. I diu també què NO rebrà: la graduació. */}
            {item?.id && !picking && <TargetaDeSembra itemId={item.id} t={t} />}

            {/* EL TARGET ES DERIVA DE LA PEÇA quan no s'ha filtrat per ell. Amb el target
                convertit en filtre opcional, es podia arribar al pas de Talles sense cap —i
                allà el target NO és opcional: és qui tria el sistema—. La peça el sap: els
                seus SizingProfile el diuen. Es deriva NOMÉS si no n'hi ha cap de triat, i queda
                editable: derivar no és decidir per l'usuari, és no fer-li repetir el que la
                peça ja declara. */}
            {family?.id && !target && <DerivaTarget familyId={family.id} onDeriva={setTarget} />}
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

        {block === 4 && mostraGrading && (
          /* EL PAS DE GRADUACIÓ — el mateix component que el botó «Graduació» de Mesures obre
             com a overlay. Aquí el wizard només hi porta el seu estat; qui decideix segueix
             sent ell (el `grading_rule_set_id` viatja al seu payload i s'escriu en desar). */
          <GraduacioPanel
            axes={{
              target, construction, garmentGroupCodi,
              garmentTypeId: family?.id ?? null, garmentTypeItemId: item?.id ?? null,
            }}
            sizing={sizingResult ? {
              size_system_id: sizingResult.size_system_id,
              size_system_nom: sizingResult.size_system_nom,
            } : null}
            sizingMissing={sizingMissing}
            fit={fit}
            onFit={(codi) => { setFit(codi); setGradingRuleSetId(null) }}
            gradingRuleSetId={gradingRuleSetId}
            onUsar={(rs) => { setGradingRuleSetId(rs.id); setNoGrading(false); onUsarJoc?.(rs) }}
            noGrading={noGrading}
            onNoGrading={(v) => { setNoGrading(v); if (v) { setFit(null); setGradingRuleSetId(null) } }}
          />
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
        {/* «Següent» fins a l'ÚLTIM pas, i allà «Crear model». Deia `block < 4` amb el 4 escrit a
            mà: en retirar el pas de graduació, el pas 3 va passar a ser l'últim i el botó seguia
            dient «Següent» sense portar enlloc — el model no es podia crear. El límit el mana la
            llista de passos, que és qui sap quants n'hi ha. */}
        {block < BLOCKS.length ? (
          <button type="button" disabled={block === 1 && !block1Resolved}
            onClick={() => { if (!(block === 1 && !block1Resolved)) setBlock(b => Math.min(BLOCKS.length, b + 1)) }}
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
const inputStyle = { width: '100%', padding: '8px 10px', borderRadius: 4, border: '0.5px solid var(--gray-l)', fontFamily: MONO, fontSize: 'var(--fs-body)', background: 'var(--white)', boxSizing: 'border-box' }
const refBox = { background: 'var(--warn-bg)', border: '0.5px solid var(--warn)', borderRadius: 8, padding: '8px 14px', fontFamily: MONO, fontSize: 'var(--fs-h3)', color: 'var(--warn)', fontWeight: 500, minHeight: 36, display: 'flex', alignItems: 'center' }
const errBox = { background: '#fee', border: '1px solid #fcc', borderRadius: 8, padding: '0.6rem 1rem', margin: '12px 0 0', fontSize: 'var(--fs-body)', color: '#c00', fontFamily: MONO }
const summaryBox = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, padding: '12px 16px', borderRadius: 8, border: '0.5px solid var(--gray-l)', background: 'var(--warn-bg)' }
const linkBtn = { background: 'none', border: 'none', padding: 0, color: 'var(--gray)', fontSize: 'var(--fs-body)', cursor: 'pointer', fontFamily: MONO }
const ghostBtn = { background: 'var(--white)', color: 'var(--warn)', border: '0.5px solid var(--warn)', borderRadius: 6, padding: '6px 14px', fontSize: 'var(--fs-body)', cursor: 'pointer', fontFamily: MONO }
const primaryBtn = (disabled) => ({ background: disabled ? 'var(--gray-l)' : 'var(--warn)', color: 'var(--white)', border: 'none', borderRadius: 6, padding: '8px 20px', fontSize: 'var(--fs-h3)', fontWeight: 500, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.6 : 1, fontFamily: MONO })

// LA TARGETA DE SEMBRA (C5-UI/P6) — el contracte de la peça, dit abans de triar-la.
//
// Diu QUÈ PUJA al model: els POMs de l'item, quants en porten valor base, a quina talla base i
// —sobretot— que la GRADUACIÓ NO hi puja. Aquesta última línia no és decorativa: fins al 31/07
// el wizard assignava el ruleset de l'item sol, i un model podia néixer graduat sense que ningú
// hagués vist la regla. El model neix NET i la graduació s'incorpora pel seu gest; la regla de
// l'item es mostra aquí com a INFORMACIÓ, i prou.
//
// Un item BUIT ho diu clar en comptes de deixar-ho endevinar pel número: néixer amb 47 POMs sense
// cap valor és una decisió legítima, però ha de ser conscient.
function TargetaDeSembra({ itemId, t }) {
  const [dades, setDades] = useState(null)

  useEffect(() => {
    let viu = true
    setDades(null)
    Promise.all([
      garmentTypeItems.get(itemId).then(r => r.data).catch(() => null),
      // Quants POMs porten VALOR: el recompte de l'item (`poms_count`) diu quantes mesures
      // declara, no quantes en sap el número. Són dues coses diferents i la targeta les separa.
      itemBaseMeasurements.list({ garment_type_item: itemId, page_size: 500 })
        .then(r => (r.data?.results ?? r.data ?? [])).catch(() => []),
    ]).then(([it, bases]) => {
      if (!viu) return
      const ambValor = bases.filter(b => b.base_value_cm != null).length
      setDades({ it, ambValor })
    })
    return () => { viu = false }
  }, [itemId])

  if (!dades?.it) return null
  const { it, ambValor } = dades
  const buit = ambValor === 0
  const kv = (k, v, atenuat) => (
    <div key={k} style={{ minWidth: 120 }}>
      <div style={{ ...labelStyle, marginBottom: 2 }}>{k}</div>
      <div style={{ fontFamily: MONO, fontSize: 'var(--fs-h3)', fontWeight: 500,
                    color: atenuat ? 'var(--text-muted)' : 'var(--text-main)' }}>{v}</div>
    </div>
  )

  return (
    <div style={{ border: `0.5px solid ${buit ? 'var(--warn)' : 'var(--gray-l)'}`, borderRadius: 8,
                  background: buit ? 'var(--warn-bg)' : 'var(--white)', padding: 16,
                  display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <b style={{ fontFamily: MONO, fontSize: 'var(--fs-body)' }}>{it.name}</b>
        <span style={{ fontFamily: MONO, fontSize: 'var(--fs-caption)', color: 'var(--text-muted)' }}>{it.code}</span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 24 }}>
        {kv(t('model_wizard.seed_poms'), it.poms_count ?? '—')}
        {kv(t('model_wizard.seed_with_value'), buit ? t('model_wizard.seed_none') : ambValor, buit)}
        {kv(t('model_wizard.seed_base_size'), it.base_size_label || '—', !it.base_size_label)}
        {kv(t('model_wizard.seed_ruleset'), it.grading_rule_set_nom || t('model_wizard.seed_none'), true)}
      </div>
      <div style={{ fontSize: 'var(--fs-body)', color: buit ? 'var(--warn)' : 'var(--text-muted)' }}>
        {buit
          ? t('model_wizard.seed_empty', { poms: it.poms_count ?? 0 })
          : t('model_wizard.seed_ok', { poms: it.poms_count ?? 0, amb: ambValor, talla: it.base_size_label || '—' })}
      </div>
      {/* LA REGLA NO PUJA. Es diu sempre, també quan l'item no en té: el silenci en aquest punt
          és el que va deixar néixer models graduats sense que ningú ho hagués demanat. */}
      <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', fontStyle: 'italic' }}>
        {t('model_wizard.seed_no_grading')}
      </div>
    </div>
  )
}

// Deriva el TARGET de la peça triada (SizingProfile de la família) quan l'usuari no n'ha filtrat
// cap. No pinta res: només omple el buit que el filtre ha deixat d'omplir per força. Si la família
// en té més d'un, mana el primer que el catàleg declara — i l'usuari el pot canviar als filtres,
// que és on viu la decisió.
function DerivaTarget({ familyId, onDeriva }) {
  useEffect(() => {
    let viu = true
    sizingProfiles.list({ garment_type: familyId, page_size: 50 })
      .then(r => {
        if (!viu) return
        const perfils = r.data?.results ?? r.data ?? []
        const codi = perfils.map(p => p.target?.codi).find(Boolean)
        if (codi) onDeriva(codi)
      })
      .catch(() => {})
    return () => { viu = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [familyId])
  return null
}

function TextInput({ label, value, onChange, placeholder }) {
  return (
    <Field label={label}>
      <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} style={inputStyle} />
    </Field>
  )
}
// `motiu` (C5): l'opció no porta enlloc, però NO s'amaga ni es bloqueja — s'atenua i ho diu.
