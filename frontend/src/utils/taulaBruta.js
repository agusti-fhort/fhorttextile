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
// ✅ L'ACOBLAMENT QUE AQUÍ ES DECLARAVA JA NO EXISTEIX. Aquest mòdul REPRODUÏA les regles de
// `EditableTable.buildPayload`, amb un pin al banc per fer sorollós el dia que divergissin. Amb
// l'eix de peça entrant al payload aquell dia va arribar, i en comptes de sincronitzar les dues
// còpies s'han unificat: el que es compara ara el fabrica `utils/payloadMesures`, el MATEIX que
// construeix el que s'envia. Comparar i desar ja no poden dir coses diferents.
import { payloadComparable } from './payloadMesures.js'

export { CAMPS_DE_MESURA } from './payloadMesures.js'

/** El que el desat ENVIARIA, normalitzat per comparar. */
export const projeccioDesable = (files, garment = '') => payloadComparable(files, garment)

/**
 * ¿El que hi ha a la taula desaria alguna cosa diferent del que ja hi ha desat?
 *
 * `desades` són les files tal com van arribar del servidor; `locals`, les de la pantalla.
 * `garment` és la prenda del contenidor: canviar-la també és un canvi per desar.
 */
export function esBruta(desades, locals, garment = '') {
  return JSON.stringify(projeccioDesable(desades, garment))
    !== JSON.stringify(projeccioDesable(locals, garment))
}
