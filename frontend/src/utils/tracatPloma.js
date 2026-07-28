// Màquina de traçat de la ploma / fletxa curva (editor de la fitxa tècnica): la part pura,
// extreta per poder-la provar sense navegador.
//
// EL CAS: el doble clic és el gest de tancar un traç obert, però abans d'arribar-hi el navegador
// ja ha disparat DOS mousedown, i cadascun ha afegit un ancoratge. El segon cau damunt del
// primer i deixa un node fantasma: un tram de llargada 0 al final del traçat. A la fletxa curva
// això es veu — la punta s'orienta amb la tangent de l'últim tram i, si el vector és nul,
// atan2(0,0)=0 i la punta mira a la dreta corbi el traç cap on corbi.

// Distància (px de contingut) per sota de la qual dos ancoratges es consideren el mateix clic.
const EPS_PX = 3

const senseNanses = (p) => !p.inX && !p.inY && !p.outX && !p.outY

// Treu l'ancoratge fantasma del final, si n'hi ha. NO toca res més:
//  - mai baixa de 2 nodes (un traçat de 2 nodes és el cas canònic de la fletxa curva),
//  - només si l'últim node no porta nanses (si s'ha arrossegat, és una corba volguda),
//  - només si cau damunt de l'anterior (< EPS_PX).
export function treuAncoratgeFantasma(points) {
  if (!Array.isArray(points) || points.length <= 2) return points
  const last = points[points.length - 1]
  const prev = points[points.length - 2]
  if (!senseNanses(last)) return points
  if (Math.hypot(last.x - prev.x, last.y - prev.y) > EPS_PX) return points
  return points.slice(0, -1)
}

// Un traçat es pot tancar (Enter / doble clic) a partir de dos ancoratges.
export function potTancar(points) {
  return Array.isArray(points) && points.length >= 2
}
