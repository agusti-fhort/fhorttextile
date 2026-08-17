// E1/B3 — LA CEL·LA DE L'ESCALAT, i quin és el referent del vermell.
//
// ⚠️ E2a (17/08) — AQUÍ HI DEIA «TRES VALORS», i ja no és cert: la columna PROPAGADA se'n va
// (v. l'acta just abans de `cellaEscalat`). Per talla en queden DOS: **Mesura** (la teòrica de
// contracte) i **Fit actual** (l'arribada). L'explicació dels tres orígens es queda perquè
// segueix sent la que diu d'on ve cada xifra i per què `vigent` no és el referent del vermell:
//
// R3 del brief E1 demanava tres valors visibles per cel·la. Amb la presa separada de la corba
// (E1/B3a) els tres existeixen de debò i cadascun ve d'un lloc diferent:
//
//   · TEÒRICA    — `PieceFittingLine.valor_teoric`: la xifra contra la qual es va mesurar,
//                  congelada quan es va obrir la presa. És el CONTRACTE de la presa.
//   · ARRIBADA   — `valor_real` de la mateixa línia, i NOMÉS si algú l'ha mesurada
//                  (el servidor ja hi aplica `linia_te_contingut`; aquí `null` vol dir
//                  «ningú no ho ha mesurat», que no és el mateix que «coincideix»).
//   · PROPAGADA  — la corba VIGENT del model (`taula-mesures`: `base_value_cm` a la base,
//                  `GradedSpec` a la resta). Mentre no es propagui, és igual que la teòrica;
//                  quan algú decideix a la base i propaga, es MOU, i és llavors que la
//                  columna diu alguna cosa que les altres dues no diuen.
//
// 🔑 EL REFERENT DEL VERMELL (R1) ÉS LA TEÒRICA, NO LA CORBA VIGENT. `MeasureGrid` pinta la
// cel·la activa en vermell quan difereix de `baseValue`; posant-hi la teòrica, el vermell diu
// exactament «la peça que ha arribat no fa el que esperàvem», que és el que R1 demana. Amb la
// vigent hi diria una altra cosa —«la presa no coincideix amb la corba d'ara»—, i després
// d'una propagació totes les cel·les es tornarien vermelles soles.
//
// SENSE PRESA OBERTA no hi ha teòrica de contracte: es cau a la vigent, que és el que la
// pantalla ensenyava abans d'aquesta peça. La columna d'arribada queda buida, que és la
// veritat: no s'ha mesurat res perquè no hi ha on anotar-ho.

// ── E2a (QA d'Agus, 17/08) · LA COLUMNA «PROPAGADA» SE'N VA ─────────────────────────────────
// L'acta de sobre deia que la propagada «es MOU quan algú decideix a la base i propaga, i és
// llavors que diu alguna cosa que les altres dues no diuen». És cert, i era el problema: la
// resta del temps —que és quasi sempre— deia EXACTAMENT el mateix que la teòrica, i dues
// columnes amb la mateixa xifra no informen: fan buscar la diferència que no hi és.
//
// Queden dues columnes per talla: **Mesura** (la teòrica de contracte) i **Fit actual**.
// `vigent` NO desapareix del càlcul: segueix sent el fallback de la teòrica quan no hi ha
// presa oberta. El que desapareix és **emetre-la per separat**.
/**
 * @param {{lineId: string, vigent: number|null, presa?: {teoric:number|null, real:number|null,
 *          desviacio:number|null, estat:string}}} arg
 * @returns {{history: {teorica: number|null},
 *            active: {lineId: string, value: number|string, baseValue: number|null,
 *                     estat: string, desviacio: number|null}}}
 */
export function cellaEscalat({ lineId, vigent = null, presa = null }) {
  const teorica = presa && presa.teoric != null ? presa.teoric : vigent
  const real = presa ? (presa.real ?? null) : null
  return {
    history: { teorica },
    active: {
      lineId,
      // ── E2b (QA d'Agus, 17/08) · LA CEL·LA NO COMENÇA MAI BUIDA ────────────────────────
      // Això era `real == null ? '' : real`, amb l'acta «una cel·la sense mesurar ha de sortir
      // BUIDA i convidar a escriure-hi». A la QA es va veure el preu: la modista havia de
      // reteclejar la xifra que ja hi era per confirmar que la peça arribada hi coincideix, i
      // una taula de vint files vol dir vint números copiats a mà.
      //
      // Ara hi surt la TEÒRICA, però com a **FANTASMA**: es veu, no és una presa, i no compta
      // enlloc fins que algú la toca o la confirma. `fantasma` és el que ho diu a qui la pinta.
      value: real == null ? (teorica ?? '') : real,
      // 🔑 NO ÉS «no hi ha valor»: és «el valor que hi ha no l'ha dit ningú». La distinció és
      // tota la peça — el vermell de R1 no l'agafa (coincideix amb `baseValue` per
      // construcció), el desat no la dispara sola, i `presa_at` només neix amb el gest.
      fantasma: real == null && teorica != null,
      baseValue: teorica,
      // Viatgen a la cel·la perquè qui la pinti pugui dir l'estat sense refer el càlcul: la
      // desviació la calcula el servidor (`escalat_presa_views._cella`) i el veredicte és de
      // la línia. Cap dels dos es recalcula al client.
      estat: presa ? (presa.estat || '') : '',
      desviacio: presa ? (presa.desviacio ?? null) : null,
    },
  }
}
