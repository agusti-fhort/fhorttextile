/**
 * F2.1 · QUINA CARA HA D'ENSENYAR EL MODAL D'OBRIR TASCA.
 *
 * La decisió viu aquí, pura i provable; el JSX (`ObrirTascaDialog`) només la pinta. És el patró
 * de la casa (`tascaActivaCore`, `sessioCore`) i aquí importa especialment, perquè la regla que
 * governa tot això és una regla NEGATIVA i és fàcil de trencar sense adonar-se'n:
 *
 *   ⚠️ REGLA D'OR — el modal NO SURT MAI en el cas normal.
 *   Qui obre és qui la té assignada (o no la té ningú), la tasca no és Done i no és albaranada
 *   → zero fricció, zero clics. Un modal que surt quan no toca és pitjor que no tenir-ne.
 *
 * Les tres cares surten de les tres decisions d'Agus:
 *   · CONFLICTE  (D-7) — algú altre hi és o la té assignada → consultar vs endur-se-la
 *   · LLIURADA   (RONDA) — feina tancada i entregada → volta nova o correcció
 *   · ALBARANADA (D-5) — hi ha albarà emès: no es toca, s'obre un extra
 *
 * L'ORDRE DE PRECEDÈNCIA no és arbitrari: ALBARANADA mana sobre LLIURADA, i LLIURADA sobre
 * CONFLICTE. Una tasca albaranada que a més tingui algú a sobre segueix sent, primer de tot,
 * intocable: oferir «treballar-hi jo» seria oferir una porta que el backend tancarà amb un 409.
 */

export const CARA_CAP = 'cap'
export const CARA_CONFLICTE = 'conflicte'
export const CARA_LLIURADA = 'lliurada'
export const CARA_ALBARANADA = 'albaranada'

/**
 * @param {object|null} tasca  fila de `ModelTaskSerializer` (contracte de F2.0)
 * @param {number|null} jo     `UserProfile.id` de qui obre
 * @returns {string} una de les CARA_*
 */
export function caraObrirTasca(tasca, jo) {
  if (!tasca) return CARA_CAP                       // no n'hi ha: open-task la crearà

  // D-5 · la paret dura mana sobre tota la resta.
  if (tasca.albaranada) return CARA_ALBARANADA

  // RONDA · feina tancada. Només és «lliurada» si de debò ho està: una tasca Done que NO és
  // lliurable no mereix el diàleg de ronda — es reobre i prou (rectificació de sempre).
  if (tasca.status === 'Done' && tasca.es_lliurable) return CARA_LLIURADA

  // D-7 · algú altre HI ÉS. I «hi és» vol dir que hi té el rellotge corrent: `obert_per`, el
  // TRAM. Res més.
  //
  // S-19 (05/08) — abans hi havia una segona condició: assignada a un altre, encara que ningú
  // hi treballés, també obria el diàleg. Era mirar la PLANIFICACIÓ i dir-ne conflicte. Una
  // tasca assignada a algú que no l'ha començada és feina prevista, i agafar-la és el gest
  // normal del taller: fer-hi preguntar equivalia a posar una porta on no hi ha paret. Que
  // l'assignee sigui un altre pot ser una NOTA a la pantalla —el panell de Tasques ja la
  // pinta—, mai un diàleg.
  if (tasca.obert_per != null && tasca.obert_per !== jo) return CARA_CONFLICTE

  return CARA_CAP
}

/** Cert quan es pot obrir directament, sense preguntar res. */
export function obreSenseFriccio(tasca, jo) {
  return caraObrirTasca(tasca, jo) === CARA_CAP
}

/**
 * La cara que correspon a un error del backend, per si l'estat precalculat anava ranci.
 * El 409 amb `code='tasca_albaranada'` és el mateix a les dues portes des de F1.7.
 */
export function caraDeError(err) {
  const codi = err?.response?.data?.code
  if (codi === 'tasca_albaranada') return CARA_ALBARANADA
  if (err?.response?.status === 409) return CARA_CONFLICTE
  return null
}
