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
// J · R3 — una tasca FETA que no és lliurable. Fins ara queia a CARA_CAP i s'obria directament,
// o sigui que **entrar-hi a mirar la REOBRIA**: tram nou, rellotge reiniciat i una fila al log
// que deia que algú havia pres la decisió de rectificar. Ningú no l'havia presa.
export const CARA_FETA = 'feta'

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
  // lliurable no mereix el diàleg de RONDA —no hi ha volta que obrir— i per això té cara pròpia.
  if (tasca.status === 'Done' && tasca.es_lliurable) return CARA_LLIURADA

  // J · R3 — I LA RESTA DE FETES TAMBÉ PREGUNTEN, encara que la pregunta sigui una altra.
  //
  // ⚠️ AQUÍ HI DEIA «es reobre i prou (rectificació de sempre)», i era el forat: `ALLOWED` permet
  // `Done → InProgress` perquè la rectificació existeix com a ACTE, i aquesta línia se'n servia
  // sense voler. Entrar a mirar què s'havia fet la tornava a obrir. És exactament el mateix
  // defecte que `batec_escriptura` va tancar el 06/08 per l'altra banda —*reobrir és un acte
  // humà, no l'efecte d'un PATCH*— i que aquí quedava viu per la porta del davant.
  //
  // La cara no ofereix ronda (no és lliurable: no hi ha volta) sinó REOBRIR, que és el que de
  // debò passaria. El defecte segueix sent consultar.
  if (tasca.status === 'Done') return CARA_FETA

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

  // J · R3 — I EL CAS QUE `obert_per` NO VEU: EN CURS D'UN ALTRE, SENSE TRAM OBERT.
  //
  // `obert_per` surt del TRAM, i un tram es pot haver tancat amb la tasca encara `InProgress`
  // (el guard de tasca oblidada, una fuita, un relleu a mitges). Llavors aquesta funció deia
  // CARA_CAP, s'obria directe, i el backend queia a la branca de handoff: `traspassa_tram` +
  // `assignee = jo`. **Una mirada s'enduia la tasca**, i «pausada conserva la mà» no hi
  // arribava — això no és pausar, és prendre.
  //
  // ⚠️ I NO ÉS DESFER S-19, que va treure la condició «assignada a un altre» perquè mirava la
  // PLANIFICACIÓ i en deia conflicte: una tasca assignada a algú que **no l'ha començada** és
  // feina prevista i agafar-la és el gest normal del taller. Aquesta condició no és aquella:
  // demana `InProgress`, o sigui feina COMENÇADA. Pending i Paused d'un altre segueixen obrint
  // sense fricció, exactament com S-19 va decidir.
  //
  // 🔒 I NOMÉS QUAN NO HI HA TRAM (`obert_per == null`). Amb tram, ja ha decidit la condició de
  // sobre, i **el tram mana sobre l'assignee** (F1.5): si el rellotge és MEU, la tasca és meva
  // encara que la planificació digui una altra cosa, i preguntar-hi seria tornar a confondre les
  // dues coses que aquella lliçó va separar. Ho guarda el test dels timers 116/117.
  if (tasca.status === 'InProgress' && tasca.obert_per == null
      && tasca.assignee != null && tasca.assignee !== jo) {
    return CARA_CONFLICTE
  }

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
  // J · R3 — els dos codis nous de `open-task`. Hi són perquè l'estat precalculat pot anar ranci
  // (un altre tècnic ha tancat o ha obert la tasca mentre aquesta pantalla la tenia a la foto), i
  // llavors el 409 és l'ÚNIC que sap la veritat. Van davant del 409 genèric: sense això, una
  // tasca feta hauria obert la cara de conflicte i hauria dit que hi ha algú altre treballant-hi.
  if (codi === 'tasca_feta') return CARA_FETA
  if (codi === 'tasca_dun_altre') return CARA_CONFLICTE
  if (err?.response?.status === 409) return CARA_CONFLICTE
  return null
}
