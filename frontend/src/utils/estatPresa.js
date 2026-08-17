// E1/B3 — L'ESTAT DE LA PRESA, derivat en un sol lloc (i amb banc).
//
// El flux d'E1 és PAUSABLE i ASÍNCRON entre persones: al taller es mesuren les peces que van
// arribant, i al despatx algú decideix a la talla base —potser un altre dia i potser una altra
// persona—. Qui obre la pantalla ha de poder saber, sense preguntar a ningú, **de quina presa
// parla, què s'hi ha fet i què hi falta**. Aquesta funció és aquella frase, resolta.
//
// La font és el `resum` que serveix `fitting/model/<id>/presa/`: els números els compta el
// servidor (que és qui té les línies) i aquí NOMÉS es decideix quin dels quatre estats és,
// que és una decisió de presentació amb conseqüències —de l'estat en penja quin gest s'ofereix.

/** Cap presa oberta: no hi ha on anotar. El gest és obrir-la, i és a una altra pantalla. */
export const SENSE_PRESA = 'sense_presa'
/** Presa oberta i encara sense cap mesura: el tècnic acaba d'arribar. */
export const BUIDA = 'buida'
/** S'hi ha mesurat i encara queda alguna talla base per decidir. */
export const MESURANT = 'mesurant'
/** S'hi ha mesurat i totes les bases estan decidides: la feina d'aquí està feta. */
export const DECIDIDA = 'decidida'

/**
 * @param {null|{presa_oberta:boolean, session?:object, resum?:object}} presa
 * @returns {{estat: string, n_preses: number, n_linies: number, talles: string[],
 *            pendents_base: number, decidides_base: number, session: object|null}}
 */
export function estatDeLaPresa(presa) {
  const r = presa?.resum || {}
  const base = {
    n_preses: r.n_preses || 0,
    n_linies: r.n_linies || 0,
    talles: r.talles_amb_presa || [],
    pendents_base: r.pendents_base || 0,
    decidides_base: r.decidides_base || 0,
    session: presa?.session || null,
  }
  if (!presa?.presa_oberta) return { ...base, estat: SENSE_PRESA }
  if (!base.n_preses) return { ...base, estat: BUIDA }
  // ⚠️ DECIDIDA vol dir «cap base pendent», i es mira `pendents_base` i no `decidides_base > 0`:
  // amb dues prendes hi ha dues bases, i donar la feina per closa amb una de decidida seria
  // dir que està fet quan la meitat no ho està. El buit NO és una decisió (llei de
  // `PieceFittingLine.decisio`: `''` no és ACCEPTED).
  return { ...base, estat: base.pendents_base > 0 ? MESURANT : DECIDIDA }
}
