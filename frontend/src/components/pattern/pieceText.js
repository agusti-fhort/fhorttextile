/**
 * Com es diu una peça de patró, en un sol lloc.
 *
 * Fins ara cada superfície ho resolia pel seu compte i totes deien el mateix: `nom_block`,
 * que és el que el CAD hi va escriure. Al Tuka això vol dir que el Taller ensenya `1`, `2`,
 * … `16` mentre el nom llegible (`BACK`, `NK PIPING`, `MID SLEEVE`) dorm a la BD. Aquest
 * fitxer és la resposta única a «com es diu això».
 *
 * PRECEDÈNCIA — del que una persona ha decidit al que el fitxer portava:
 *   1. `nom`  — el bateig del model. Mana perquè algú l'ha triat.
 *   2. `metadata.piece_name` — el nom que el CAD va escriure als TEXT de la peça.
 *   3. `nom_block` — el nom del BLOCK. L'últim recurs, i mai desapareix: és l'evidència
 *      del fitxer d'origen i sempre s'ha de poder consultar (v. `nomOriginal`).
 *
 * ⚠️ Això és l'ETIQUETA, no l'IDENTIFICADOR. La selecció, la imantació i el render SVG
 * segueixen anant per `nom_block`, que és el que el servidor espera a `?piece=`
 * (`patterns/svg.py:58`). Barrejar les dues coses trencaria el canvas.
 */

/** El nom que s'ha d'ensenyar. Mai buit: sempre queda el nom del bloc. */
export function etiquetaPeca(p) {
  if (!p) return ''
  return (p.nom || '').trim()
    || (p.metadata?.piece_name || '').trim()
    || p.nom_block
    || ''
}

/**
 * El nom del BLOCK, per al tooltip. L'evidència del fitxer no s'amaga mai: quan
 * l'etiqueta ja no és el nom del bloc, qui mira la pantalla ha de poder saber d'on surt.
 * Torna buit quan l'etiqueta JA és el nom del bloc — repetir-lo al títol no informa de res.
 */
export function nomOriginal(p) {
  if (!p) return ''
  return etiquetaPeca(p) === p.nom_block ? '' : (p.nom_block || '')
}

/**
 * El nom del ROL en la llengua de l'usuari, o buit si la peça encara no en té.
 * El servidor envia els tres idiomes en cru a posta; triar-ne un és feina d'aquí.
 */
export function nomDelRol(p, idioma) {
  const noms = p?.piece_role?.nom
  if (!noms) return ''
  return noms[idioma] || noms.ca || noms.en || ''
}
