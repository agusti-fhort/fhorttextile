// ¿HI HA RES PER DESAR? — SET-2/T7-B5c.
//
// La pregunta de tancament d'aquest bloc, i és la bona: **amb quin criteri es decideix «brut»?**
// Si el detector dona falsos positius, el guarda de sortida salta sempre i es converteix en
// soroll que la gent aprèn a ignorar — i el dia que hi hagi canvis de debò, també l'ignorarà.
//
// ── EL QUE HI HAVIA, I PER QUÈ NO SERVIA ─────────────────────────────────────────────────
// `EditableTable` porta un `dirty` que és un flag de TACTE: nou handlers de mutació el posen a
// `true` i només es baixa en desar, en descartar o en rebre files noves. O sigui que **editar
// una cel·la i tornar-la al seu valor original deixava «brut»**, i el botó de desar quedava viu
// per fer un POST que no canviava res. Exactament el fals positiu que la pregunta anticipa.
//
// ── EL CRITERI D'AQUÍ ────────────────────────────────────────────────────────────────────
// Brut = **el que es desaria ara és diferent del que ja hi ha desat**. No «l'usuari ha tocat
// res». Es compara la PROJECCIÓ DEL PAYLOAD i no els camps de la fila, i la diferència no és
// teòrica: `buildPayload` filtra les files sense valor de `measurements` i les files sense
// `pom_id` de `keep_*`, o sigui que esborrar una fila suggerida buida NO canvia res del que
// s'envia. Comparant camps de fila, allò diria «brut» i el guarda saltaria per no res.
//
// ⚠️ ACOBLAMENT DECLARAT: aquest mòdul reprodueix les regles de `EditableTable.buildPayload`.
// Si el payload guanya un camp, aquí n'ha de guanyar un altre, o el botó dirà «net» amb canvis
// pendents — que és el fals NEGATIU, i és pitjor que el positiu: perd feina en silenci. El banc
// hi té un test que fixa la llista de camps justament per fer sorollós aquest oblit.
//
// Mòdul pur i sense dependències: es prova amb `node --test` (vegeu taulaBruta.test.js).

/** Els camps d'una mesura que el desat ENVIA. Fixat al banc: veure l'acoblament de dalt. */
export const CAMPS_DE_MESURA = ['pom_id', 'capa', 'instancia', 'base_value_cm', 'notes', 'nom_fitxa']

/**
 * El valor d'una cel·la, comparable.
 *
 * Un `input` torna SEMPRE text: després d'escriure-hi, un 50 desat es converteix en `'50'`. Si
 * es comparessin crus, teclejar el mateix número que ja hi havia deixaria la taula «bruta» per
 * sempre. `''` i `null` són el mateix estat —sense valor— pel mateix motiu.
 */
function valorComparable(v) {
  if (v === null || v === undefined || v === '') return null
  const n = Number(v)
  // Un text que no és número es compara tal com és: no és feina d'aquest mòdul jutjar-lo.
  return Number.isNaN(n) ? String(v) : n
}

const text = (v) => (v === null || v === undefined ? '' : String(v))

/**
 * El que el desat ENVIARIA a partir d'aquestes files. Mirall de `EditableTable.buildPayload`.
 *
 * `keep` cobreix els dos camps germans del payload (`keep_pom_ids` i `keep_mesures`): tots dos
 * surten de la MATEIXA llista filtrada, o sigui que comparar-la un cop els compara tots dos.
 * L'ORDRE hi compta a posta — `keep_pom_ids` és una llista i reordenar la taula és un canvi.
 */
export function projeccioDesable(files) {
  const f = files || []
  return {
    mesures: f
      .filter(r => r.base_value_cm !== null && r.base_value_cm !== undefined && r.base_value_cm !== '')
      .map(r => ({
        pom_id: r.pom_id ?? null,
        capa: text(r.capa),
        instancia: text(r.instancia),
        base_value_cm: valorComparable(r.base_value_cm),
        notes: text(r.notes),
        nom_fitxa: text(r.nom_fitxa),
      })),
    keep: f
      .filter(r => r.pom_id)
      .map(r => ({ pom_id: r.pom_id, capa: text(r.capa), instancia: text(r.instancia) })),
  }
}

/**
 * ¿El que hi ha a la taula desaria alguna cosa diferent del que ja hi ha desat?
 *
 * `desades` són les files tal com van arribar del servidor; `locals`, les de la pantalla.
 */
export function esBruta(desades, locals) {
  return JSON.stringify(projeccioDesable(desades)) !== JSON.stringify(projeccioDesable(locals))
}
