// EL TARGET QUE ES POT DERIVAR D'UNA FAMÍLIA, i el que no.
//
// El wizard deriva el target de la peça quan l'usuari no n'ha filtrat cap: la família el sap
// —els seus `SizingProfile` el diuen— i fer-l'hi repetir seria demanar-li el que el catàleg ja
// declara. Però només val si la família el declara SENSE AMBIGÜITAT.
//
// 🔴 EL DEFECTE QUE TANCA (V2, 06/08). Abans es prenia «el primer que el catàleg declara»
// (`perfils.map(p => p.target?.codi).find(Boolean)`), i l'ordre d'aquella llista no té res a
// veure amb aquest model: la consulta va sense `customer_codi` i l'ordre acaba sortint del nom
// del sistema de talles. Amb les dades vives de `fhort` això donava `KID_BOY` a `JERSEY_TOPS` i
// a `TAILORED_PANTS` —famílies que també serveixen MAN i WOMAN—, i el pas 3 hi preseleccionava
// un run de nen amb talla base 6 o 7. És l'origen del model 1307.
//
// La lògica viu aquí i no dins del component perquè es pugui provar amb `node --test`, com
// `destiTasca.js`: el component es queda amb la petició i el `setState`.

/**
 * Els codis de target DIFERENTS que declaren els perfils d'una família, sense repetits ni buits.
 * @param {Array<{target?: {codi?: string}}>} perfils
 * @returns {string[]}
 */
export function targetsDeLaFamilia(perfils) {
  return [...new Set((perfils || []).map(p => p?.target?.codi).filter(Boolean))]
}

/**
 * El target derivable d'una família: el seu, si en declara UN i prou; `null` si en declara
 * diversos (llavors qui el sap és la persona, i té el filtre del pas 2 per dir-ho) o cap.
 * @param {Array} perfils
 * @returns {string|null}
 */
export function targetDerivable(perfils) {
  const codis = targetsDeLaFamilia(perfils)
  return codis.length === 1 ? codis[0] : null
}
