// EL FORAT DEL CROM · §8b-quater (Agus 09/08) — «top bar + menú de pantalla fixos en scroll,
// com un sol bloc enganxat».
//
// ── PER QUÈ EXISTEIX, I PER QUÈ LA PRIMERA IMPLEMENTACIÓ NO BASTAVA ─────────────────────────
// El menú de pantalla el declara CADA pàgina, sempre dins d'un `<div>` de marge negatiu que el
// treu dels 24px de padding del `<main>`. Un element `position: sticky` només es pot desplaçar
// DINS del seu contenidor, i aquell `<div>` fa exactament l'alçada de la barra: recorregut zero.
// La primera versió ho resolia enganxant el CONTENIDOR des d'`index.css` amb
// `main > *:has(> [data-ftt-pagemenu])`. Mesurat a Chromium: funcionava.
//
// **Però `:has()` no existeix a tots els navegadors** (Chrome 105+ · Safari 15.4+ · **Firefox
// 121+**), i quan no hi és la regla sencera no s'aplica: la top bar es queda enganxada —és un
// `sticky` normal— i el menú se'n va cap amunt. **El símptoma exacte que Agus va veure a
// pantalla.** No es pot fer dependre una peça d'estructura de tot el producte d'un selector que
// una part dels navegadors ignora en silenci: quan falla, no falla res — simplement no passa.
//
// LA SOLUCIÓ SENSE `:has()`: el Shell obre un forat i el menú s'hi TELETRANSPORTA. Així la
// barra deixa d'estar dins del `<main>` i passa a ser, literalment, el segon pis d'un sol bloc
// enganxat amb la top bar. Cap pantalla ha de canviar ni una línia; el seu `<div>` de marge
// negatiu es queda buit i **conserva el marge**, que és el que cancel·la el padding del
// `<main>` i deixa el contingut exactament on era (la barra ja no ocupa lloc a dins, però
// tampoc l'ocupa a fora: se n'ha anat amunt amb la mateixa alçada).
//
// EL NODE ES CREA AL CARREGAR EL MÒDUL, no al muntar el Shell. Un portal cap a un node que
// encara no existeix no pinta res, i el Shell (pare) fa `commit` DESPRÉS que els seus fills
// hagin renderitzat: si el forat es creés al Shell, la barra parpellejaria una passada a cada
// navegació. Amb un node de mòdul, React hi pot pintar de seguida encara que estigui desenganxat
// del document; el Shell només l'hi enganxa.
export const FORAT_CROM = typeof document !== 'undefined' ? document.createElement('div') : null

/** `ref` del Shell: enganxa el forat al seu lloc dins de la barra de crom. */
export function enganxaForat(node) {
  if (node && FORAT_CROM && FORAT_CROM.parentNode !== node) node.appendChild(FORAT_CROM)
}
