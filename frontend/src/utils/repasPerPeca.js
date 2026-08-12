/**
 * EL REPÀS COMPTA PER PRENDA — SET-2/PRED-1 (12/08).
 *
 * El forat: el Repàs de fittings ja pinta un contenidor per prenda, però el recompte i la
 * capçalera («N sessions fetes · talla S») es calculaven sobre el MODEL i vivien FORA dels
 * contenidors. Una pantalla que parla per prendes amb un rètol que parla pel model: obrir el
 * Pantaló i llegir-hi «3 sessions fetes» quan cap d'aquelles tres el va tocar és la mateixa
 * mentida que el B12 va treure de la taula («aquest model no té mesures» dins d'un contenidor
 * d'un model que en té 28).
 *
 * 🔑 LES SESSIONS SÓN DEL MODEL (D6) i això NO es toca: una sessió de fitting convoca el model
 * sencer. El que es parteix és **QUÈ N'ENSENYA CADA PRENDA**: de les sessions del model, quantes
 * han tocat de debò les files d'aquesta prenda. La pregunta que respon el número deixa de ser
 * «quants fittings té el model» i passa a ser «quants d'aquests fittings parlen d'aquesta
 * prenda», que és la que es fa qui obre el contenidor.
 *
 * Viu aquí i no dins d'un JSX perquè és una LLEI i les lleis han de poder fallar en vermell
 * (v. `calFilaDePeca`, la germana que va aprendre la mateixa lliçó a B2b).
 */

/** L'id de la columna d'ENTRADA DE POMs (`repas_views.COL_ENTRADA`). No és cap fitting. */
export const COL_ENTRADA = 'entrada'

/**
 * Les columnes d'ESDEVENIMENT que tenen contingut a `files`.
 *
 * Contingut = alguna cel·la amb `valor_real` no nul. Una columna que existeix però que en
 * aquestes files no diu res no s'hi compta: per a aquesta prenda, aquell dia no va passar res.
 *
 * ⚠️ L'ENTRADA DE POMs NO HI ENTRA MAI, i és el mateix criteri que ja aplicava el recompte del
 * model: no és un fitting, és d'on es parteix.
 *
 * @param {Array} files    files ja FILTRADES per la prenda (`filesDeLaPeca`)
 * @param {Array} sessions columnes del payload (`[{id, origen, …}]`)
 * @returns {Array<string>} ids de columna, en l'ordre en què arriben
 */
export function columnesAmbContingut(files, sessions) {
  const ids = []
  for (const s of (sessions || [])) {
    if (!s || s.origen === 'ENTRADA') continue
    const cid = String(s.id)
    // `valor_real` és l'únic camp que diu «aquí es va prendre una mesura». Ni la nota ni el
    // veredicte compten: un comentari sense número no és una presa, i comptar-lo faria que una
    // columna que només porta el motiu d'un gate pugés el recompte d'una prenda que ningú va
    // mesurar.
    const tocada = (files || []).some(f => {
      const cel = f?.valors?.[cid]
      return !!cel && cel.valor_real != null
    })
    if (tocada) ids.push(cid)
  }
  return ids
}

/**
 * Quants FITTINGS ensenya aquesta prenda. És `columnesAmbContingut().length`, i existeix com a
 * funció pròpia perquè és el número que es pinta i el que els bancs fixen.
 */
export function recompteFittings(files, sessions) {
  return columnesAmbContingut(files, sessions).length
}

/**
 * LA TALLA DE LA CAPÇALERA, DITA SENSE MENTIR.
 *
 * El segon predicat de model que se cola en aquesta pantalla: el backend resol UNA talla per a
 * tota la vista (`repas_views`: `model.base_size_label` + `model.size_run_model`) i filtra les
 * línies per ella. Però una prenda pot DECLARAR la seva pròpia base (`ModelGarment.
 * CAMPS_HERETABLES` inclou `base_size_label`), o sigui que dins del contenidor d'una peça amb
 * base pròpia, «talla S» és la talla del MODEL presentada com si fos la de la prenda.
 *
 * 🔑 Aquí NO es pot arreglar pintant la base de la prenda: les files que es veuen són les de la
 * talla de la VISTA, i canviar només el rètol faria la mentida més convincent. El que es pot
 * fer —i és el que la casa ja fa a la Comprovació amb `limitacions`— és DIR-HO.
 *
 * @returns {{talla: string, divergeix: boolean, propia: string}}
 *   `divergeix` = la prenda declara una base diferent de la que la vista ensenya.
 */
export function tallaDeLaCapcalera(tallaVista, peca) {
  const vista = (tallaVista || '').trim()
  // Sense peça (mare, o `/peces/` que no ha contestat) no hi ha res a comparar: la talla de la
  // vista és l'única que hi ha, i és la del model — que per a la mare és la seva de debò.
  const propia = (peca?.base_size_label?.etiqueta || '').trim()
  if (!vista || !propia || peca?.es_mare) return { talla: vista, divergeix: false, propia: '' }
  return { talla: vista, divergeix: propia !== vista, propia }
}
