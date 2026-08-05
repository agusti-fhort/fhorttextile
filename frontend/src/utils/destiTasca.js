/**
 * T2 · ON PORTA UNA TASCA — RESOLUTOR ÚNIC, LLEGIT DEL CATÀLEG.
 *
 * Fins ara cada superfície duia el seu `switch (task_type_code)` cablejat: un a `TaskTree`
 * (el panell de Tasques del model) i un altre a `WorkPlan` (el Pla de treball del Dashboard),
 * bessons declarats i tots dos amb SIS casos i un `default: null`. El catàleg ja sabia la
 * resposta —`tipus`, `eina` i `mode` hi són poblats i exposats des de B1/F2.0— i ningú l'hi
 * preguntava: per això «Revisió de patró CAD» no feia res i les externes obrien rellotges.
 *
 * Aquí la pregunta es fa UNA vegada. Qui decideix on va una tasca és el catàleg; això
 * només tradueix `eina`+`mode` a la superfície que els sap servir.
 *
 * ⚠️ LA LLISTA NO S'INVENTA RES. `SUPERFICIES` només conté parells que TENEN pantalla viva
 * avui. Un parell que no hi és no vol dir «cap destí possible»: vol dir «encara no hi ha
 * pantalla», i la UI ho ha de DIR, no dissimular-ho portant el tècnic a un lloc que no fa el
 * que la targeta promet. Afegir-hi una superfície nova és una línia.
 */

// Els quatre gestos possibles d'una targeta. El primer és l'únic que navega.
export const GEST_EINA = 'eina'                    // interna amb pantalla → hi anem
export const GEST_SENSE_PANTALLA = 'sense_pantalla'  // interna amb eina, mode sense pantalla encara
export const GEST_SENSE_EINA = 'sense_eina'        // interna sense eina: transport manual
export const GEST_DECLARAT = 'declarat'            // externa-lliure: el temps es declara

export const TIPUS_EXTERN = 'Externa-lliure'

// (eina/mode) → superfície viva. Clau composta: l'eina diu ON i el mode diu EN QUIN CONTEXT.
const SUPERFICIES = {
  // Mesures — dues portes al mateix tab: definir POMs (gènesi) i prendre mesures (treball).
  'mesures/autoria_base': (m) => ({ route: `/models/${m}?tab=Mesures&mode=entry`, tab: 'Mesures' }),
  'mesures/presa': (m, t) => ({ route: `/models/${m}?tab=Mesures&task_id=${t}`, tab: 'Mesures' }),
  // Escalat — l'editor propagat, inline al tab.
  'escalat/propagacio': (m, t) => ({ route: `/models/${m}/escalat?task_id=${t}` }),
  // Fitxa — el resolutor de .ftt obre el document del model.
  'fitxa/document': (m, t) => ({ route: `/models/${m}/fitxa?task_id=${t}` }),
  // Patró — el Taller (W2). Els altres modes de `patro` (revisio, escalat, marcada) NO hi són:
  // el Taller no els sap i no en tenen maqueta aprovada. Quan n'hi hagi, una línia aquí.
  'patro/digitalitzar': (m, t) => ({ route: `/models/${m}/patro/taller?task_id=${t}` }),
  'patro/disseny_base': (m, t) => ({ route: `/models/${m}/patro/taller?task_id=${t}` }),
}

/** Clau de superfície d'un tipus de tasca. Sense eina o sense mode no hi ha clau. */
export function clauSuperficie(tt) {
  if (!tt?.eina || !tt?.mode) return null
  return `${tt.eina}/${tt.mode}`
}

/**
 * El catàleg l'ofereix per iniciar? `visible` i `active` són DUES decisions:
 * inactiu = retirat del catàleg · invisible = vàlid però encara no oferible.
 * Un catàleg antic sense `visible` (o un payload que no el porti) es llegeix com a oferible.
 */
export function esOferible(tt) {
  return !!tt && tt.active !== false && tt.visible !== false
}

/**
 * Quin gest fa la targeta d'aquest tipus. NO mira l'estat de la tasca: mira el CATÀLEG.
 * L'ordre importa — `tipus` mana sobre `eina`: una externa-lliure no té eina per definició,
 * i si algun dia en tingués una, seguiria sent temps declarat.
 */
export function gestDeTasca(tt) {
  if (tt?.tipus === TIPUS_EXTERN) return GEST_DECLARAT
  if (!tt?.eina) return GEST_SENSE_EINA
  const clau = clauSuperficie(tt)
  return (clau && SUPERFICIES[clau]) ? GEST_EINA : GEST_SENSE_PANTALLA
}

/**
 * On va aquesta tasca. `null` quan no hi ha superfície — que és una resposta legítima i
 * la UI l'ha d'explicar, no amagar.
 * @returns {{route: string, tab?: string}|null}
 */
export function destiDeTasca(tt, { modelId, taskId } = {}) {
  if (gestDeTasca(tt) !== GEST_EINA) return null
  return SUPERFICIES[clauSuperficie(tt)](modelId, taskId)
}

/** Els parells amb pantalla viva, per a l'auditoria i els tests. */
export function superficiesVives() {
  return Object.keys(SUPERFICIES)
}
