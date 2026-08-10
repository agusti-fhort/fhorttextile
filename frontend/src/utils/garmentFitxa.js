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
 *  `garment`, com la columna. Un payload que encara no la serveixi = la mare. */
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
