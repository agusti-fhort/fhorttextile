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

// ── Helpers de matching (idèntics a GradingRuleSets.jsx:133-193, font única) ──

// Un RuleSet (M2M targets) encaixa si no en té cap o si inclou el target triat.
export const matchesTarget = (rs, target) =>
  !rs.targets_codis?.length || rs.targets_codis.includes(target)

// garment_group via map id→codi (FK del RuleSet). Sense grup assignat = compatible amb qualsevol.
export const matchesGarmentGroup = (rs, groupCodi, garmentGroupCodiById) => {
  if (!rs.garment_group) return true
  return garmentGroupCodiById[rs.garment_group] === groupCodi
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
    matchesGarmentGroup(rs, garmentGroup, garmentGroupCodiById)
  )
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
    rs.garment_group != null && garmentGroupCodiById[rs.garment_group] === garmentGroup &&
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
      rs.garment_group != null && garmentGroupCodiById[rs.garment_group] === garmentGroup &&
      rs.size_system === sizeSystemId &&
      rs.fit_type_codi
    ).map(rs => rs.fit_type_codi)
  )
  return FITS.filter(f => set.has(f.codi))
}
