// PER QUÈ «MESURAR PRENDA» ESTÀ APAGAT — S42/F2.
//
// El pas ③ del stepper de Mesures exigeix TAULA DE TALLES: `grading-status.te_taula` (versió
// de grading activa amb `GradedSpec` actives) és el mateix predicat que el gate dur de
// `create-piece`, i el botó el respecta a posta. Això no canvia.
//
// ── EL DEFECTE QUE AIXÒ TANCA (QA Agus 16/08, model 1379) ──────────────────────────────
// El rètol era una CONSTANT —«Cal gravar el POM per generar la taula de talles»— i el botó la
// deia sempre que faltava la taula, valgués el que valgués la resta de l'estat. Al 1379 els
// POM estan gravats (`te_mesures: true`, i el pas ① es pinta amb ✓ tres píxels a l'esquerra),
// la graduació hi és (`te_regles: true`) i el que falta és PROPAGAR. La pantalla es contradeia
// a un pam de distància i enviava el tècnic a repetir una feina ja feta.
//
// **Un motiu fals costa més que un silenci.** Un botó apagat que calla obliga a preguntar; un
// que menteix obliga a desfer. És el mateix defecte que `987ca023` va tancar per a «Gravar
// POM» —allà la porta no tenia rètol; aquí en tenia un d'equivocat— i per això la resposta és
// la mateixa: el rètol es DERIVA de l'estat, no es codifica.
//
// ── PER QUÈ VIU AQUÍ I NO DINS DEL JSX ────────────────────────────────────────────────
// La llei del contenidor de peça ja es va perdre una vegada per existir només com un `&&`
// enmig d'un JSX (v. `pecaDefinicio.calFilaDePeca`). Aquesta és una cadena de tres estats i
// un ordre; en una funció pura té banc, i el banc és el que dirà si algun dia l'ordre canvia.
//
//     node --test frontend/src/utils/motiuPasPresa.test.js

/**
 * La clau i18n del motiu pel qual el pas «Mesurar prenda» està bloquejat, o `null` si no ho està.
 *
 * ⚠️ `null` NO vol dir «tot fet»: vol dir «aquest pas no té res que l'aturi». Amb `estatPas`
 * encara sense resposta també és `null`, i és deliberat — el botó no es bloqueja per una cosa
 * que no sabem, exactament com feia el predicat que substitueix (`estatPas != null && …`).
 *
 * L'ORDRE ÉS EL DEL FLUX DE TREBALL (① POM → ② Graduació → ④ Propagar) i mana el PRIMER que
 * falta: dir «cal propagar» a qui encara no ha gravat cap mesura seria el mateix error al
 * revés. Es diu un sol pas, el següent, perquè és l'únic que la persona pot fer ara.
 *
 * @param {{te_taula?: boolean, te_mesures?: boolean, te_regles?: boolean}|null} estatPas
 *        el payload de `GET /api/v1/models/<id>/grading-status/`
 * @returns {string|null} clau de `t()`, o `null` si el pas és accessible
 */
export function motiuPasPresa(estatPas) {
  if (estatPas == null) return null        // encara no ho sabem: no es bloqueja pel dubte
  if (estatPas.te_taula) return null       // la taula hi és: res a dir
  if (!estatPas.te_mesures) return 'model_sheet.pas_sense_mesures'
  if (!estatPas.te_regles) return 'model_sheet.pas_sense_regles'
  return 'model_sheet.pas_sense_propagacio'
}
