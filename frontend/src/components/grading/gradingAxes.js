// gradingAxes.js — Eixos de grading (vocabulari controlat) + helpers de filtre PURS.
// Sprint Llibreria d'Items (B2). Font ÚNICA de la lògica de cascada/filtre que abans vivia
// inline a pages/GradingRuleSets.jsx (:10-193). Els components AxesSelector i RuleSetPicker
// l'usen; GradingRuleSets segueix amb la seva còpia pròpia (vàlvula d'escapament: no es toca
// codi viu). DEUTE: unificar GradingRuleSets perquè consumeixi aquest mòdul + AxesSelector/
// RuleSetPicker quan sigui segur (RuleSetCard de GR té edició inline de regles acoblada).
//
// codi = id (mai traduït); nom_en/nom_ca/nom_es = display bilingüe. Convenció de sector.

export const TARGETS = [
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

export const CONSTRUCTIONS = [
  { codi: 'WOVEN',        nom_en: 'Woven',        nom_ca: 'Teixit pla',   nom_es: 'Tejido plano' },
  { codi: 'KNIT',         nom_en: 'Knit',         nom_ca: 'Punt jersey',  nom_es: 'Punto jersey' },
  { codi: 'STRETCH_KNIT', nom_en: 'Stretch Knit', nom_ca: 'Punt elàstic', nom_es: 'Punto elástico' },
  { codi: 'TECHNICAL',    nom_en: 'Technical',    nom_ca: 'Tècnic',       nom_es: 'Técnico' },
]

export const FITS = [
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

// Construccions disponibles per al target triat.
export function availableConstructions(ruleSets, target) {
  if (!target) return []
  const set = new Set(
    ruleSets.filter(rs => matchesTarget(rs, target)).map(rs => rs.construction_codi).filter(Boolean)
  )
  return CONSTRUCTIONS.filter(c => set.has(c.codi))
}

// Fits disponibles per target + construction.
export function availableFits(ruleSets, target, construction) {
  if (!target || !construction) return []
  const set = new Set(
    ruleSets
      .filter(rs => matchesTarget(rs, target) &&
        (!rs.construction_codi || rs.construction_codi === construction))
      .map(rs => rs.fit_type_codi).filter(Boolean)
  )
  return FITS.filter(f => set.has(f.codi))
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
export function availableFitsStrict(ruleSets, fixed, garmentGroupCodiById, sizeSystemId) {
  const { target, construction, garmentGroup } = fixed || {}
  if (!target || !construction || !garmentGroup || sizeSystemId == null) return []
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
  return FITS.filter(f => set.has(f.codi))
}

// P6 — ordena els candidats posant al davant el SUGGERIT per l'item (V1), sense alterar el
// conjunt: el ventall el decideix el matching d'eixos; això només és ordre de presentació.
// Suggerir ≠ arrossegar — cap crida d'aquesta funció assigna res.
export function orderWithSuggestedFirst(matches, suggestedId) {
  if (suggestedId == null) return matches
  const i = matches.findIndex(rs => rs.id === suggestedId)
  return i <= 0 ? matches : [matches[i], ...matches.slice(0, i), ...matches.slice(i + 1)]
}
