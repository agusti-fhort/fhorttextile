// PER QUÈ «MESURAR PRENDA» I «MESURAR SET» ESTAN APAGATS — S42/F2 · S45/B.
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
// ══ S45/B — I LES DUES PORTES ES PARTEIXEN, perquè NO demanen el mateix ═══════════════
// Fins ara «Mesurar prenda» (pas ③ de Mesures) i «Mesurar set» (tab Escalat) compartien
// predicat: `te_taula`, la taula PROPAGADA. Amb la regla d'Agus (Patró C) això és fals per a
// una de les dues:
//
//   · **MESURAR PRENDA no exigeix propagat.** Un PROTOTIP pot arribar a la sala sense
//     graduació definida, i la modista l'ha de poder anotar. El backend ja ho permet: sense
//     versió, `create_piece_fitting` en materialitza una de BUIDA i `reconcilia_linies` treu
//     les línies de la TALLA BASE del model (`fitting/services.py:503`, `:640-660`). L'únic
//     que aquesta porta necessita, doncs, és que hi hagi ALGUNA COSA A PRENDRE: `te_mesures`.
//
//   · **MESURAR SET SÍ que exigeix propagat**, i no per un `if` que es pugui afluixar: el
//     full de presa del set ÉS la corba propagada convertida en fulls. `desa_presa_escalat`
//     busca la línia de (POM, talla) i, si no hi és, alça `PresaSenseLiniaError`
//     (`fitting/services.py:135-138`). Sense `GradedSpec` només hi ha la talla base: no hi ha
//     set. Aquesta porta es queda amb la cascada de sempre.
//
// EL GUARD ES PARTEIX PER CAMP/CAMÍ, NO PER ENDPOINT (llei S43). Per això són dues funcions
// i no un booleà de més: dues portes amb dues preguntes diferents no poden compartir el
// predicat només perquè comparteixin el mateix `estatPas`.
//
// ── PER QUÈ VIU AQUÍ I NO DINS DEL JSX ────────────────────────────────────────────────
// La llei del contenidor de peça ja es va perdre una vegada per existir només com un `&&`
// enmig d'un JSX (v. `pecaDefinicio.calFilaDePeca`). Aquestes són cadenes d'estats i un
// ordre; en una funció pura tenen banc, i el banc és el que dirà si algun dia l'ordre canvia.
//
//     node --test frontend/src/utils/motiuPasPresa.test.js

/**
 * La clau i18n del motiu pel qual el pas «Mesurar prenda» està bloquejat, o `null` si no ho està.
 *
 * ⚠️ `null` NO vol dir «tot fet»: vol dir «aquest pas no té res que l'aturi». Amb `estatPas`
 * encara sense resposta també és `null`, i és deliberat — el botó no es bloqueja per una cosa
 * que no sabem, exactament com feia el predicat que substitueix (`estatPas != null && …`).
 *
 * S45/B — L'ÚNICA CONDICIÓ ÉS `te_mesures`: hi ha una mesura base amb valor, o sigui que hi ha
 * alguna cosa a prendre. NI `te_regles` NI `te_taula`: graduar i propagar són la feina d'una
 * ALTRA porta (④), i exigir-les aquí era exigir-li al proto que fos un model acabat.
 *
 * @param {{te_taula?: boolean, te_mesures?: boolean, te_regles?: boolean}|null} estatPas
 *        el payload de `GET /api/v1/models/<id>/grading-status/`
 * @returns {string|null} clau de `t()`, o `null` si el pas és accessible
 */
export function motiuPasPresa(estatPas) {
  if (estatPas == null) return null        // encara no ho sabem: no es bloqueja pel dubte
  if (!estatPas.te_mesures) return 'model_sheet.pas_sense_mesures'
  return null
}

/**
 * El mateix, per a «Mesurar set» (tab Escalat) — que SÍ que exigeix la taula propagada.
 *
 * L'ORDRE ÉS EL DEL FLUX DE TREBALL (① POM → ② Graduació → ④ Propagar) i mana el PRIMER que
 * falta: dir «cal propagar» a qui encara no ha gravat cap mesura seria el mateix error al
 * revés. Es diu un sol pas, el següent, perquè és l'únic que la persona pot fer ara.
 *
 * @param {{te_taula?: boolean, te_mesures?: boolean, te_regles?: boolean}|null} estatPas
 * @returns {string|null} clau de `t()`, o `null` si el pas és accessible
 */
export function motiuPasMesurarSet(estatPas) {
  if (estatPas == null) return null        // encara no ho sabem: no es bloqueja pel dubte
  if (estatPas.te_taula) return null       // la taula hi és: res a dir
  if (!estatPas.te_mesures) return 'model_sheet.pas_sense_mesures'
  if (!estatPas.te_regles) return 'model_sheet.pas_sense_regles'
  return 'model_sheet.pas_sense_propagacio'
}
