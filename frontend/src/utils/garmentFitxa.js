// SET-2/T9 — L'EIX DE LA PEÇA (`garment`) A LA FITXA TÈCNICA, EN UN SOL LLOC.
//
// SET-2: la peça viu DINS del model i l'eix es diu `garment` (mai «piece», que a aquesta casa
// ja vol dir Model sencer — `PieceFitting`, `Model.piece_number`, `GarmentTypeItemPart`).
//
// LA CONVENCIÓ (la mateixa que la BD, `models_app/models.py:781`): `''` és LA PEÇA MARE, que
// és el Model mateix. Mai `null`, mai `undefined`. La 02, la 03… són codis de `ModelGarment`.
// Per la convenció MANDROSA (D3) la mare no té mai fila pròpia: només es materialitza a
// partir de la 02.
//
// ⚠️ AFIRMACIÓ D'ESTAT DATADA — 2026-08-10. Avui NO existeix cap peça 02 a cap dada real: 13
// comportes CHECK congelen la columna a '' i `ModelGarment` encara no és cap model de Django.
// Re-verificar amb: `grep -rn "class ModelGarment" backend/` (avui: 0 resultats) i
// `SELECT DISTINCT garment FROM <tenant>.models_app_basemeasurement;` (avui: només '').
// Mentre això sigui cert, tot el que hi ha aquí sota ha de donar EXACTAMENT una branca.
//
// A LA FITXA, L'EIX VA A L'OBJECTE I MAI A LA PÀGINA. El round-trip d'objecte del `.ftt` és
// OPAC (`TechSheetEditor.jsx:554`, `base = obj`) i està provat amb test
// (`models_app/test_ftt_peca_grup_roundtrip.py:46-54` i `test_ftt_garment_roundtrip.py`): un
// camp desconegut d'objecte sobreviu el cicle sencer, sense migració ni serialitzador tocat.
// A la pàgina serien quatre reconstruccions camp a camp (`paginesFtt.js:8-10` ho documenta).

/** La peça MARE: el Model mateix. Sentinella no-NULL, igual que a la BD. */
export const GARMENT_MARE = ''

/** L'eix d'un OBJECTE del `.ftt`. Absent (fitxa antiga) = la mare, que és el que era quan es
 *  va escriure: fins avui tot document és d'un model d'una sola peça. No és tolerància, és la
 *  lectura correcta del format vell — el mateix criteri que `identitatDeCota` amb la capa. */
export const garmentIdDe = (obj) => {
  const g = obj?.garmentId
  return typeof g === 'string' ? g : GARMENT_MARE
}

/** L'eix d'una FILA de dades (`base-measurements`, `graded-table`): allà la clau es diu
 *  `garment`, com la columna. Un payload que encara no la serveixi = la mare.
 *
 *  ⚠️ DATAT 2026-08-10 — AVUI CAP PAYLOAD LA SERVEIX, i T9 no l'anticipa: la clau arribarà
 *  quan existeixi `ModelGarment`, perquè la resolució `garment.X or model.X` ha de viure en
 *  un sol punt (D5) i el payload és una de les vores on s'ha de veure. Per això aquest lector
 *  no és una tolerància provisional: és el contracte mentre la vora no la porti. */
export const garmentDeFila = (fila) => {
  const g = fila?.garment
  return typeof g === 'string' ? g : GARMENT_MARE
}

/**
 * Agrupa per peça CONSERVANT L'ORDRE D'APARICIÓ, mai alfabètic: l'ordre de les mesures és
 * de l'usuari (`base_measurements_view` ordena per `ordre`) i agrupar no és reordenar.
 *
 * Torna sempre almenys un grup si hi ha ítems. Amb tot d'una sola peça torna UN grup i prou
 * — que és el que fa que l'arbre no aparegui i no afegeixi cap clic.
 *
 * @param {Array} items
 * @param {(item:any)=>string} llegeix  com se'n treu l'eix (garmentDeFila / garmentIdDe)
 * @returns {Array<{garment: string, items: Array}>}
 */
export function agrupaPerGarment(items, llegeix = garmentDeFila) {
  const perGarment = new Map()
  for (const it of items || []) {
    const g = llegeix(it)
    if (!perGarment.has(g)) perGarment.set(g, [])
    perGarment.get(g).push(it)
  }
  return [...perGarment.entries()].map(([garment, its]) => ({ garment, items: its }))
}

/**
 * ¿Cal ensenyar l'arbre? NOMÉS amb més d'una peça. Amb una sola branca, un capçal de grup
 * seria un rètol que no distingeix res i un nivell de lectura de més: la pantalla ha de
 * degradar a EXACTAMENT el que es veia abans d'aquest tram.
 */
export const calArbrePerGarment = (grups) => (grups || []).length > 1

/** Una taula que abraça diverses prendes és del MODEL, o sigui de la mare: l'ancoratge d'un
 *  objecte és UN codi, mai una llista. */
export const garmentComu = (files) => {
  const grups = agrupaPerGarment(files)
  return grups.length === 1 ? grups[0].garment : GARMENT_MARE
}

/**
 * LA LLEI DE PARTIR UNA TAULA DE MESURES EN DIVERSES, en un sol lloc (T1a i T1b la
 * comparteixen). Dos eixos, i l'ordre importa:
 *
 *   PRENDA (`garment`) — l'eix de DALT. És la peça del model.
 *   SECCIÓ (`seccio`)  — l'eix de DINS. És un rètol de text lliure de l'import, i pot partir
 *                        UNA sola prenda en zones («cos», «caputxa» d'una dessuadora).
 *
 * Cap partició s'aplica sola: totes dues les demana qui compon la fitxa, i totes dues callen
 * si el seu eix no té més d'una branca. Amb tot d'una prenda i sense seccions —el corpus
 * d'avui, 2026-08-10— torna UN sol grup amb totes les files, que és exactament el que hi
 * havia abans d'aquest tram.
 *
 * @param {Array} files
 * @param {{perPeca?: boolean, perSeccio?: boolean, seccionsDe: (files:Array)=>string[]}} opcions
 * @returns {Array<{garment: string, seccio: string|null, files: Array}>}
 */
export function partirTaules(files, { perPeca = false, perSeccio = false, seccionsDe }) {
  const perGarment = agrupaPerGarment(files)
  const prendes = (perPeca && calArbrePerGarment(perGarment))
    ? perGarment.map(g => ({ garment: g.garment, files: g.items }))
    : [{ garment: garmentComu(files), files: files || [] }]
  return prendes.flatMap(p => {
    const seccions = seccionsDe(p.files)
    return (perSeccio && seccions.length > 1)
      ? seccions.map(sec => ({
        garment: p.garment, seccio: sec,
        files: p.files.filter(f => (f?.seccio || '').trim() === sec),
      }))
      : [{ garment: p.garment, seccio: null, files: p.files }]
  })
}
