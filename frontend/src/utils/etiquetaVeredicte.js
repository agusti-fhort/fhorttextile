// L'ETIQUETA del veredicte de la modista (D-31.21 + ordre CTO 23/09). El CODI
// (ACCEPTED/ADJUSTED/REJECTED) segueix sent el valor de BD/API i no es toca — el que canvia és
// NOMÉS com es pinta: OK · ADJUSTED · NO OK, FOLLOW SPEC (forma llarga) / OK · ADJUSTED · NO OK
// (forma curta, per a columnes estretes). Mateix text als 3 idiomes —dada de domini, com
// LINEAR/STEP— per això ve del vocabulari (`/api/v1/vocabulari/`, `veredictes_fitting`) i no
// d'una constant local: Llei d'Agus (08/08, `vocabulariDominiFont.js`) — cap enumeració de
// domini es declara al frontend, perquè una constant que la dupliqui és una segona font de
// veritat que ningú actualitza el dia que la primera canvia.
import { useElements } from './vocabulariDominiFont'

/**
 * `(codi, curta=false) => etiqueta`. Mentre el vocabulari no ha arribat (o per a un codi que no
 * hi és, p.ex. `''` = sense decidir) torna el codi cru: és el mateix mode de fallada degradada
 * que ja fan els altres consumidors d'aquest vocabulari (CAP llista de reserva al client).
 */
export function useEtiquetaVeredicte() {
  const { elements } = useElements('veredictes_fitting')
  return (codi, curta = false) => {
    if (!codi) return ''
    const el = (elements || []).find(e => e.codi === codi)
    if (!el) return codi
    return (curta ? el.etiqueta_curta : el.etiqueta_llarga) || codi
  }
}
