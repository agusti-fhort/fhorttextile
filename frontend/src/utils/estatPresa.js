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

/** Cap presa, ni oberta ni tancada: el model no n'ha tingut mai. El gest és «Mesurar set». */
export const SENSE_PRESA = 'sense_presa'
/**
 * E3a — LA PRESA ESTÀ SEGELLADA: hi ha dades i es llegeixen, però no s'hi escriu.
 *
 * 🚨 EL CINQUÈ ESTAT VA NÉIXER D'UN EMPAT. Fins a E3a això queia a `SENSE_PRESA`, perquè el
 * servidor servia el mateix payload per a «segellada» i per a «cap». La pantalla, doncs, oferia
 * obrir una presa sobre una acta que s'acabava de tancar, deixava teclejar en una graella que el
 * servidor rebutjava cel·la a cel·la amb 409, i no sabia dir de quina presa parlava. Un estat
 * que no es pot nomenar acaba pintat com el seu contrari.
 * (`docs/diagnosis/DIAGNOSI_QA_2054_REGRESSIO_O_FORAT.md`.)
 */
export const TANCADA = 'tancada'
/** Presa oberta i encara sense cap mesura: el tècnic acaba d'arribar. */
export const BUIDA = 'buida'
/** S'hi ha mesurat i encara queda alguna talla base per decidir. */
export const MESURANT = 'mesurant'
/** S'hi ha mesurat i totes les bases estan decidides: la feina d'aquí està feta. */
export const DECIDIDA = 'decidida'

/**
 * ⚠️ `escrivible` NO és `estat !== TANCADA`: hi ha DOS estats sense on escriure (TANCADA i
 * SENSE_PRESA) i qui els hagi de tractar igual —la graella— no ha de tornar a enumerar-los. És
 * l'únic predicat que decideix si la cel·la accepta una tecla, i per tant l'únic lloc on pot
 * néixer un 409 des de la UI. Deriva de `presa_oberta`, que és el MATEIX booleà que el guard del
 * servidor fa servir: si divergissin, la pantalla oferiria escriure on la porta diu que no.
 *
 * @param {null|{presa_oberta:boolean, presa_tancada?:boolean, session?:object,
 *               resum?:object}} presa
 * @returns {{estat: string, escrivible: boolean, n_preses: number, n_linies: number,
 *            talles: string[], pendents_base: number, decidides_base: number,
 *            session: object|null}}
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
    escrivible: !!presa?.presa_oberta,
  }
  // L'ORDRE MANA: TANCADA es mira ABANS que el buit, perquè una acta té `presa_oberta: false`
  // igual que el no-res i el que la distingeix és NOMÉS `presa_tancada`. Al revés, el cinquè
  // estat no sortiria mai i tornaríem a l'empat que això arregla.
  if (presa?.presa_tancada) return { ...base, estat: TANCADA }
  if (!presa?.presa_oberta) return { ...base, estat: SENSE_PRESA }
  if (!base.n_preses) return { ...base, estat: BUIDA }
  // ⚠️ DECIDIDA vol dir «cap base pendent», i es mira `pendents_base` i no `decidides_base > 0`:
  // amb dues prendes hi ha dues bases, i donar la feina per closa amb una de decidida seria
  // dir que està fet quan la meitat no ho està. El buit NO és una decisió (llei de
  // `PieceFittingLine.decisio`: `''` no és ACCEPTED).
  return { ...base, estat: base.pendents_base > 0 ? MESURANT : DECIDIDA }
}
