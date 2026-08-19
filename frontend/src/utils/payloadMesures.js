// EL PAYLOAD DE DESAR MESURES, EN UN SOL LLOC — SET-2/T7-B6.
//
// ── PER QUÈ NEIX AQUEST MÒDUL ────────────────────────────────────────────────────────────
// El construïa `EditableTable.buildPayload` i el REPRODUÏA `utils/taulaBruta` per decidir si hi
// havia res per desar. Dues còpies de la mateixa regla, amb un pin al banc per fer sorollós el
// dia que divergissin. Amb l'eix de peça entrant al payload, aquell dia era avui: valia més
// unificar-les que sincronitzar-les. Ara el detector de brut compara EXACTAMENT el que s'enviarà,
// perquè li ho fabrica la mateixa funció.
//
// ── L'EIX DE PEÇA HI ENTRA, I NO ÉS COSMÈTIC ─────────────────────────────────────────────
// 🛑 Amb les comportes de mesura retirades (#12), una fila pot ser d'una prenda que no és la
// mare. El backend ja ho sap fer: l'upsert de `set_measurements_view` resol per
// `(pom, capa, instancia, garment)` i `_poda_mesures` conserva per una clau de QUATRE camps que
// surt de `_identitat_de_mesura`. El que faltava era que el CLIENT ho digués.
//
// I el que passava si no ho deia NO era «res»: `_identitat_de_mesura` hi posa `''` quan el camp
// falta, o sigui que **la fila de la 02 quedava fora del conjunt a conservar i la poda la
// desactivava**. Mesurat contra dades vives el 12/08: desar la taula de la mare del model 1320
// donava de baixa la fila `garment='02'`. Ningú peta i ningú avisa; la mesura simplement deixa
// de comptar. És la família del «indexar per menys camps dels que la identitat té» que aquest
// sprint ha anat tancant, fabricada des de l'altra banda.
//
// `garmentDefecte` és el de la PRENDA DEL CONTENIDOR. Mana el de la FILA quan hi és —és dada
// factual, la fila sap de qui és— i el del contenidor és el pla B mentre els adaptadors de
// lectura no el propaguin (censat el 12/08: `measureSources`, `fittingGridAdapter`,
// `PropagatedEditor` i `GraduacioSuperficie` el deixen caure; el backend sí que l'emet).
//
// Mòdul pur i sense dependències: es prova amb `node --test` (vegeu payloadMesures.test.js).

/** Els camps d'una mesura que el desat ENVIA. */
export const CAMPS_DE_MESURA = ['pom_id', 'capa', 'instancia', 'garment',
  'base_value_cm', 'notes', 'nom_fitxa']

const text = (v) => (v === null || v === undefined ? '' : String(v))

/** L'eix d'una fila: el seu si el porta, i si no el del contenidor. Mai «endevinat». */
export const garmentDeFila = (fila, garmentDefecte = '') => (
  typeof fila?.garment === 'string' ? fila.garment : (garmentDefecte || '')
)

/**
 * El cos de `POST /models/<id>/set-measurements/` a partir de les files d'una taula.
 *
 * `keep_pom_ids` i `keep_mesures` viatgen junts a posta: el backend fa servir el nou i ignora
 * el vell, i un desplegament a mitges (bundle nou amb backend antic) segueix podant com abans
 * en comptes de deixar de podar.
 *
 * ⚠️ `keep_*` es construeix sobre TOTES les files i no sobre `measurements`: aquesta última
 * només porta les que tenen valor, i una fila buida que en quedés fora deixaria de ser
 * «conservada» — el backend l'esborraria. Seria fabricar un esborrat silenciós.
 */
export function construeixPayload(files, garmentDefecte = '') {
  const f = files || []
  const measurements = f
    .filter(r => r.base_value_cm !== null && r.base_value_cm !== undefined && r.base_value_cm !== '')
    .map(r => ({
      pom_id: r.pom_id,
      capa: r.capa,
      instancia: r.instancia,
      garment: garmentDeFila(r, garmentDefecte),
      base_value_cm: r.base_value_cm,
      notes: r.notes || '',
      nom_fitxa: r.nom_fitxa || '',
    }))
  const ambPom = f.filter(r => r.pom_id)
  const cos = {
    measurements,
    keep_pom_ids: ambPom.map(r => r.pom_id),
    keep_mesures: ambPom.map(r => ({
      pom_id: r.pom_id,
      capa: r.capa,
      instancia: r.instancia,
      garment: garmentDeFila(r, garmentDefecte),
    })),
  }
  // ── L'ABAST EXPLÍCIT, NOMÉS QUAN CAL (SET-2/#12b) ──────────────────────────────────────
  // `_poda_mesures` dedueix quines prendes s'estan podant de les files que el payload ANOMENA.
  // Hi ha un sol gest que no pot resoldre: **el contenidor que es desa BUIT** —cap fila, cap
  // eix, i tanmateix una ordre de buidar-lo—. Per a aquell, i només per a aquell, el client diu
  // qui és.
  //
  // ⚠️ NO S'ENVIA SEMPRE, i la diferència té dany: l'abast explícit SUBSTITUEIX el derivat. En
  // una taula amb files de dues prendes —l'estat d'avui, perquè `taula-mesures` no filtra—
  // enviar `garments: ['']` des de la mare deixaria les files de la 02 fora de l'abast, i
  // esborrar-ne una no faria efecte: un gest que l'usuari fa i que no passa.
  if (!cos.keep_mesures.length) cos.garments = [garmentDefecte || '']
  return cos
}

/**
 * El valor d'una cel·la, COMPARABLE (no és el que s'envia: és el que es compara).
 *
 * Un `input` torna SEMPRE text: després d'escriure-hi, un 50 desat es converteix en `'50'`. Si
 * es comparessin crus, teclejar el mateix número que ja hi havia deixaria la taula «bruta» per
 * sempre. `''` i `null` són el mateix estat —sense valor— pel mateix motiu.
 */
function valorComparable(v) {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  return Number.isNaN(n) ? String(v) : n
}

/**
 * El MATEIX payload, normalitzat per comparar-lo. No s'envia mai: només serveix per decidir si
 * hi ha res per desar (v. `utils/taulaBruta`).
 */
export function payloadComparable(files, garmentDefecte = '') {
  const p = construeixPayload(files, garmentDefecte)
  return {
    measurements: p.measurements.map(m => ({
      ...m,
      pom_id: m.pom_id ?? null,
      capa: text(m.capa),
      instancia: text(m.instancia),
      base_value_cm: valorComparable(m.base_value_cm),
    })),
    keep_mesures: p.keep_mesures.map(k => ({
      ...k, capa: text(k.capa), instancia: text(k.instancia),
    })),
  }
}
