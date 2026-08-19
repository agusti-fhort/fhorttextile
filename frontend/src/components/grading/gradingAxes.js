// gradingAxes.js — Eixos de grading (vocabulari controlat) + helpers de filtre PURS.
// Sprint Llibreria d'Items (B2). Font ÚNICA de la lògica de cascada/filtre que abans vivia
// inline a pages/GradingRuleSets.jsx (:10-193). Els components AxesSelector i RuleSetPicker
// l'usen; GradingRuleSets segueix amb la seva còpia pròpia (vàlvula d'escapament: no es toca
// codi viu). DEUTE: unificar GradingRuleSets perquè consumeixi aquest mòdul + AxesSelector/
// RuleSetPicker quan sigui segur (RuleSetCard de GR té edició inline de regles acoblada).
//
// codi = id (mai traduït); nom_en/nom_ca/nom_es = display bilingüe. Convenció de sector.

// P0b (2026-07-24) — vocabulari alineat amb el sector: BOY→KID_BOY · GIRL→KID_GIRL ·
// TODDLER_*→BABY_* · BABY_*→NEWBORN_*. Ha d'anar SEMPRE en paral·lel amb
// Target.CODI_CHOICES (backend/fhort/pom/models.py) i amb les files de `pom_target`.
// ⚠️ TARGETS · CONSTRUCTIONS · FITS JA NO SÓN AQUÍ. Són TAULES (`pom.Target`,
// `pom.ConstructionType`, `pom.FitType`) i tenen endpoint des de S2; la còpia que hi havia aquí
// —13 + 4 + 10 files amb els noms en tres idiomes escrits a mà— era la més grossa del projecte i
// ni tan sols era al cens de la Fase 1. Ara es llegeixen amb `useEixos()` de `./eixosFont`.
//
// Les funcions d'aquest fitxer que en depenien (`availableConstructions`, `availableFits`,
// `availableFitsStrict`) reben ara el catàleg per PARÀMETRE. No és cerimònia: eren pures i han de
// seguir sent-ho —hi ha una suite de `node --test` que les exercita sense DOM ni xarxa—, i una
// funció pura no pot anar a buscar dades. Qui les crida ja té el hook.

// 🛑 GARMENT_GROUPS ES QUEDA, I NO ÉS UNA EXCEPCIÓ DE CRITERI: ÉS UN BLOQUEIG (coda F2.2).
//
// El quart eix no es pot llegir de l'endpoint com els altres tres perquè la TAULA no té el que
// aquesta llista dona. `pom.GarmentGroup` té `codi`, `nom`, `descripcio`, `actiu` — i prou: **cap
// `nom_en`/`nom_ca`/`nom_es` i cap `display_order`**. Buidar això deixaria tota la casa pintant
// els grups amb el `nom` anglès de la BD en els tres idiomes, i en un ordre alfabètic per codi
// que no és el que el sector fa servir. Seria matar un duplicat a canvi de trencar la pantalla.
//
// I la còpia ja és CURTA, cosa que confirma el diagnòstic en comptes de desmentir-lo: a `fhort`
// hi ha 12 grups a la BD i aquí n'hi ha 7. Els cinc que hi falten (DRESSES-FULL, KNITWEAR,
// NEWBORN, TOPS-KNIT, TOPS-WOVEN) ja cauen al camí de fallback de `garmentCatalog.js:normGroup`
// —surten amb el `nom` de BD i al final de l'ordre—, o sigui que la meitat del catàleg ja viu
// sense aquesta llista. Aquí no hi ha vocabulari canònic: hi ha SET grups amb traducció i cinc
// sense.
//
// EL QUE CAL PERQUÈ CAIGUI (decisió d'Agus, no d'aquest tram): afegir `nom_en`/`nom_ca`/`nom_es`
// i `display_order` a `GarmentGroup`, amb migració i backfill. ⚠️ I el backfill topa amb C6 pas
// 1: el tenant `los` té la taula `GarmentGroup` BUIDA (v. `pom/models.py`, comentari de
// `GarmentType.grup`), o sigui que allà no hi ha res a backfillar i el pas s'ha de coordinar
// amb aquella peça, que està aturada.
export const GARMENT_GROUPS = [
  { codi: 'TOPS',        nom_en: 'Tops',        nom_ca: 'Parts superiors', nom_es: 'Partes superiores' },
  { codi: 'BOTTOMS',     nom_en: 'Bottoms',     nom_ca: 'Parts inferiors', nom_es: 'Partes inferiores' },
  { codi: 'DRESSES',     nom_en: 'Dresses',     nom_ca: 'Vestits',         nom_es: 'Vestidos' },
  { codi: 'OUTERWEAR',   nom_en: 'Outerwear',   nom_ca: 'Abrics',          nom_es: 'Abrigos' },
  { codi: 'UNDERWEAR',   nom_en: 'Underwear',   nom_ca: 'Interior',        nom_es: 'Interior' },
  { codi: 'SWIMWEAR',    nom_en: 'Swimwear',    nom_ca: 'Bany',            nom_es: 'Baño' },
  { codi: 'ACCESSORIES', nom_en: 'Accessories', nom_ca: 'Complements',     nom_es: 'Complementos' },
]

// Nom localitzat secundari segons idioma (anglès primari es mostra a part).
export function nomLocal(obj, lang) {
  if (!obj) return ''
  return lang === 'es' ? (obj.nom_es || obj.nom_en) : lang === 'ca' ? (obj.nom_ca || obj.nom_en) : obj.nom_en
}

// ── Etiquetes de TARGET (font única — cap superfície resol la clau i18n pel seu compte) ──
// El nom es resol per CODI via i18n (`model_wizard.target_<CODI>`), com `tasktype.<code>`
// (DECISIONS.md §3): el codi és l'identitat, el nom pintat és presentació.
export function targetLabel(t, codi, fallback) {
  return codi ? t(`model_wizard.target_${codi}`, fallback || codi) : (fallback || '')
}

// Franja d'edat: informació SECUNDÀRIA, buida a propòsit per a MAN/WOMAN/UNISEX_ADULT/
// MATERNITY. Qui la pinti ha d'ocultar la línia si torna '' — mai un guió ni un buit reservat.
// Defensiu contra la config d'i18next: si `returnEmptyString` es desactivés algun dia, t()
// tornaria la clau en cru i acabaríem pintant «model_wizard.target_franja_MAN» dins un pill.
export function targetFranja(t, codi) {
  if (!codi) return ''
  const clau = `model_wizard.target_franja_${codi}`
  const val = t(clau, '')
  return !val || val === clau ? '' : val
}

// Etiqueta localitzada d'un GRUP de peça pel seu codi (vocabulari canònic; fallback al codi per a
// grups nous com NEWBORN). Font única per a breadcrumbs/labels — fora còpies privades.
export function groupLabel(codi, lang) {
  const g = GARMENT_GROUPS.find(x => x.codi === codi)
  return g ? nomLocal(g, lang) : (codi || '')
}

// ── Helpers de matching (idèntics a GradingRuleSets.jsx:133-193, font única) ──

// Un RuleSet (M2M targets) encaixa si no en té cap o si inclou el target triat.
export const matchesTarget = (rs, target) =>
  !rs.targets_codis?.length || rs.targets_codis.includes(target)

// garment_group via map id→codi (FK del RuleSet). Sense grup assignat = compatible amb qualsevol.
export const matchesGarmentGroup = (rs, groupCodi, garmentGroupCodiById) => {
  if (!rs.garment_group) return true
  return garmentGroupCodiById[rs.garment_group] === groupCodi
}

// ── ÀMBIT D'APLICABILITAT multi-node (sprint ÀMBIT) ───────────────────────────
// LLEI: «aplica a» = «està disponible per a». Un contenidor amb àmbit aplica a un node si el seu
// àmbit conté AQUELL node o un ANCESTRE seu (item → la seva família → el seu grup). Així, marcar un
// GRUP el fa disponible per a tots els seus garments; baixar a ITEM el limita a aquell item.
// El node del model/selecció viatja als eixos: garmentGroup (codi) · garmentTypeId · garmentTypeItemId.
// FALLBACK: un ruleset SENSE àmbit (applies_to buit — canònics i contenidors encara no backfillats)
// es casa pel seu garment_group, exactament com fins ara → cap regressió.
export function scopeApplies(rs, axes, garmentGroupCodiById, { strict = false } = {}) {
  const scope = rs.applies_to || []
  if (!scope.length) {
    return strict
      ? (rs.garment_group != null && garmentGroupCodiById[rs.garment_group] === axes.garmentGroup)
      : matchesGarmentGroup(rs, axes.garmentGroup, garmentGroupCodiById)
  }
  return scope.some(n => (
    (n.node_type === 'ITEM' && axes.garmentTypeItemId != null
      && n.garment_type_item_id === axes.garmentTypeItemId) ||
    (n.node_type === 'TYPE' && axes.garmentTypeId != null
      && n.garment_type_id === axes.garmentTypeId) ||
    (n.node_type === 'GROUP' && !!axes.garmentGroup && n.group_codi === axes.garmentGroup)
  ))
}

// Targets presents als RuleSets (per il·luminar només els disponibles).
export function availableTargetCodes(ruleSets) {
  const set = new Set()
  for (const rs of ruleSets) for (const tc of (rs.targets_codis || [])) set.add(tc)
  return set
}

// Construccions disponibles per al target triat. `constructions` = el catàleg (`useEixos()`);
// sense catàleg torna `[]`, que aquí vol dir «no puc oferir res», no «no n'hi ha cap».
export function availableConstructions(ruleSets, target, constructions) {
  if (!target || !constructions) return []
  const set = new Set(
    ruleSets.filter(rs => matchesTarget(rs, target)).map(rs => rs.construction_codi).filter(Boolean)
  )
  return constructions.filter(c => set.has(c.codi))
}

// Fits disponibles per target + construction. `fits` = el catàleg (`useEixos()`).
export function availableFits(ruleSets, target, construction, fits) {
  if (!target || !construction || !fits) return []
  const set = new Set(
    ruleSets
      .filter(rs => matchesTarget(rs, target) &&
        (!rs.construction_codi || rs.construction_codi === construction))
      .map(rs => rs.fit_type_codi).filter(Boolean)
  )
  return fits.filter(f => set.has(f.codi))
}

// RuleSets que encaixen amb la selecció completa (4 eixos). Buit fins que els 4 estan triats.
// LENIENT: un eix NULL al ruleset fa de COMODÍ (casa amb qualsevol). Vàlid a les superfícies de
// GESTIÓ (CRUD: GradingRuleSets, ItemAuthoring, RuleSetCard) on es vol veure tot el que podria aplicar.
export function matchingRuleSets(ruleSets, axes, garmentGroupCodiById) {
  const { target, construction, fit, garmentGroup } = axes || {}
  if (!target || !construction || !fit || !garmentGroup) return []
  return ruleSets.filter(rs =>
    matchesTarget(rs, target) &&
    (!rs.construction_codi || rs.construction_codi === construction) &&
    (!rs.fit_type_codi || rs.fit_type_codi === fit) &&
    scopeApplies(rs, axes, garmentGroupCodiById)
  )
}

// ── LLEI DELS WIZARDS ELIMINATIUS (C5, 2026-07-23) ────────────────────────────
// Dins d'una pantalla, seleccionar ATENUA I REORDENA: els compatibles vius i amunt, els
// incompatibles grisos, avall i AMB MOTIU. MAI amaga. Generalitza la F1.4 del model 174: una
// llista que es buida en silenci es llegeix com «el botó no respon», i una entitat mal informada
// ha de ser un problema VISIBLE, no invisible.
//
// `classifyRuleSets` és la versió NO ELIMINATÒRIA de `matchingRuleSets`: mateixa aritmètica
// d'eixos (lenient: un eix NULL al ruleset fa de comodí), però en comptes de filtrar retorna
// TOTS els rulesets amb el veredicte i, si no casen, QUINS eixos els deixen fora. Un eix no
// seleccionat no descarta ningú — el filtre és opcional, no un gate.
//
// Retorna [{ rs, compatible, motius }] amb els compatibles primer, conservant l'ordre d'entrada
// dins de cada grup. `motius` són CODIS d'eix ('target'|'construction'|'fit'|'group'), mai text:
// la traducció és del component.
export function classifyRuleSets(ruleSets, axes, garmentGroupCodiById) {
  const { target, construction, fit, garmentGroup } = axes || {}
  const compatibles = []
  const incompatibles = []
  for (const rs of ruleSets) {
    const motius = []
    if (target && !matchesTarget(rs, target)) motius.push('target')
    if (construction && rs.construction_codi && rs.construction_codi !== construction) motius.push('construction')
    if (fit && rs.fit_type_codi && rs.fit_type_codi !== fit) motius.push('fit')
    if (garmentGroup && !scopeApplies(rs, axes, garmentGroupCodiById)) motius.push('group')
    ;(motius.length ? incompatibles : compatibles).push({ rs, compatible: !motius.length, motius })
  }
  return [...compatibles, ...incompatibles]
}

// ── Matching ESTRICTE (context WIZARD, sprint WIZARD-COMPLET) ──────────────────
// A diferència del lenient: `size_system` és OBLIGATORI i coincident, i cap eix NULL fa de
// comodí — un ruleset s'exclou si no declara explícitament target/construction/fit/grup/system
// que casin amb la combinació completa. Així el wizard només ofereix la graduació que realment
// aplica a la peça+talles triades (cap arrossegament implícit ni fals positiu).
export function matchingRuleSetsStrict(ruleSets, axes, garmentGroupCodiById, sizeSystemId) {
  const { target, construction, fit, garmentGroup } = axes || {}
  if (!target || !construction || !fit || !garmentGroup || sizeSystemId == null) return []
  return ruleSets.filter(rs =>
    rs.actiu !== false &&
    !!rs.targets_codis?.length && rs.targets_codis.includes(target) &&
    rs.construction_codi === construction &&
    rs.fit_type_codi === fit &&
    scopeApplies(rs, axes, garmentGroupCodiById, { strict: true }) &&
    rs.size_system != null && rs.size_system === sizeSystemId
  )
}

// Fits amb almenys un ruleset ESTRICTE per a la combinació fixada (target/construction/grup/system).
// Alimenta el selector de FIT del wizard: només s'ofereixen fits que porten a una graduació real.
export function availableFitsStrict(ruleSets, fixed, garmentGroupCodiById, sizeSystemId, fits) {
  const { target, construction, garmentGroup } = fixed || {}
  if (!target || !construction || !garmentGroup || sizeSystemId == null || !fits) return []
  const set = new Set(
    ruleSets.filter(rs =>
      rs.actiu !== false &&
      !!rs.targets_codis?.length && rs.targets_codis.includes(target) &&
      rs.construction_codi === construction &&
      scopeApplies(rs, fixed, garmentGroupCodiById, { strict: true }) &&
      rs.size_system === sizeSystemId &&
      rs.fit_type_codi
    ).map(rs => rs.fit_type_codi)
  )
  return fits.filter(f => set.has(f.codi))
}

// P6 — ordena els candidats posant al davant el SUGGERIT per l'item (V1), sense alterar el
// conjunt: el ventall el decideix el matching d'eixos; això només és ordre de presentació.
// Suggerir ≠ arrossegar — cap crida d'aquesta funció assigna res.
export function orderWithSuggestedFirst(matches, suggestedId) {
  if (suggestedId == null) return matches
  const i = matches.findIndex(rs => rs.id === suggestedId)
  return i <= 0 ? matches : [matches[i], ...matches.slice(0, i), ...matches.slice(i + 1)]
}
