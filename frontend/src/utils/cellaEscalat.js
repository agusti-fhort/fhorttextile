// E1/B3 — LA CEL·LA DE L'ESCALAT: tres valors, i quin és el referent del vermell.
//
// R3 del brief: tres valors visibles per cel·la. Amb la presa separada de la corba (E1/B3a)
// els tres existeixen de debò i cadascun ve d'un lloc diferent:
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

/**
 * @param {{lineId: string, vigent: number|null, presa?: {teoric:number|null, real:number|null,
 *          desviacio:number|null, estat:string}}} arg
 * @returns {{history: {teorica: number|null, propagada: number|null},
 *            active: {lineId: string, value: number|string, baseValue: number|null,
 *                     estat: string, desviacio: number|null}}}
 */
export function cellaEscalat({ lineId, vigent = null, presa = null }) {
  const teorica = presa && presa.teoric != null ? presa.teoric : vigent
  const real = presa ? (presa.real ?? null) : null
  return {
    history: { teorica, propagada: vigent },
    active: {
      lineId,
      // Buit i no `0`: una cel·la sense mesurar ha de sortir BUIDA i convidar a escriure-hi.
      value: real == null ? '' : real,
      baseValue: teorica,
      // Viatgen a la cel·la perquè qui la pinti pugui dir l'estat sense refer el càlcul: la
      // desviació la calcula el servidor (`escalat_presa_views._cella`) i el veredicte és de
      // la línia. Cap dels dos es recalcula al client.
      estat: presa ? (presa.estat || '') : '',
      desviacio: presa ? (presa.desviacio ?? null) : null,
    },
  }
}
