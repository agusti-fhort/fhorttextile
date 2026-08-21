// LLEI (Agus, 2026-07-22) — LINEAR amb increment 0 i SENSE break ÉS FIXED.
//
// Una regla LINEAR amb delta 0 no gradua res: matemàticament és idèntica a FIXED
// («aquesta mesura no canvia entre talles»), però es presenta com si gradués i
// fabrica taules planes que semblen graduades. El backend ja BLOQUEJA l'autoria de
// regles noves així (models_app/views.py, codi LINEAR_INCREMENT_ZERO) i una migració
// de dades ha convertit les preexistents; aquest helper és el punt ÚNIC de
// classificació per a la capa de presentació, perquè cap superfície torni a
// dibuixar LINEAR+0 encara que li arribi de dades velles, d'un import o d'un seed.
//
// Punt únic deliberat: les 4 superfícies (Escalat/PropagatedEditor, editor de regles
// del check, taula de GradingRuleSets, EditableTable) s'alimenten d'endpoints i
// serializers DIFERENTS; el denominador comú on convergeixen és el frontend.
//
// NO s'aplica a `EditableTable` (gènesi): allà el desplegable de règim és un control
// d'AUTORIA en curs — reinterpretar el valor mentre el tècnic encara no ha escrit el
// delta li canviaria la tria sota els dits. Les files ja desades hi arriben ja
// convertides per la migració de dades, així que el forat és teòric.

import { etiquetesDelRun } from './breakConvention.js'

/**
 * Delta base efectiu d'una regla. Des del FIX-A/PAS-3: NOMÉS `increment_base`.
 *
 * 🚨 Aquí hi havia el fallback a `increment`, i era el MIRALL del que feia `_apply_rule`. El dia
 * que el motor va deixar de llegir el camp llegat, aquest mirall va quedar dient una cosa que ja
 * no és certa: hauria pintat «LINEAR amb delta 2.0, correcta» sobre una fila que el motor ja no
 * gradua. Va amb el seu bessó de backend (`pom/grading_regime.py`, `delta_base_efectiu`) i no
 * es poden separar — és literalment el que aquest fitxer declara ser.
 */
function deltaBase(rule) {
  const ib = rule?.increment_base
  if (ib !== null && ib !== undefined && ib !== '') return Number(ib)
  return 0
}

/** true si la regla porta un trencament informat (talla + valor). NO vol dir «gradua». */
function hasBreak(rule) {
  const lbl = rule?.talla_break_label
  const brk = rule?.increment_break
  if (lbl !== null && lbl !== undefined && String(lbl).trim() !== '') return true
  return brk !== null && brk !== undefined && brk !== '' && Number(brk) !== 0
}

// ── TRAM F · ELS INTERVALS ───────────────────────────────────────────────────────────────────
//
// MIRALL EXACTE de `pom/grading_regime.py`: allà hi ha la constant ÚNICA del backend i la
// validació que guarda les quatre portes; aquí hi ha el que la pantalla necessita saber per no
// oferir el que el servidor rebutjarà. Els dos no es poden separar — canviar el sostre en un
// dels dos costats faria que la pantalla i la porta diguessin coses diferents del mateix gest.
export const MAX_BREAKS = 3

/** Els intervals d'una regla, sempre com a llista (mai null). Camp de fila, com `valors_step`. */
export function intervalsDe(rule) {
  const b = rule?.breaks
  return Array.isArray(b) ? b : []
}

/** El delta d'un interval en número (o null): els inputs escriuen text i la coma decimal. */
function deltaInterval(iv) {
  const v = iv?.delta
  if (v === null || v === undefined || v === '') return null
  const n = Number(String(v).replace(',', '.'))
  return Number.isFinite(n) ? n : null
}

/**
 * Règim EFECTIU d'una regla per a presentació.
 * LINEAR sense CAP delta diferent de 0 → 'FIXED'. Qualsevol altre cas → la lògica tal qual.
 * Valors de DADA (LINEAR/STEP/FIXED) — no es tradueixen.
 *
 * 🚨 TRAM F — abans n'hi havia prou amb `hasBreak` per declarar-la LINEAR, i era el mateix
 * forat que el defecte 4 de la diagnosi de PROD: una regla amb `ib=0 · brk=0` i talla de break
 * informada es presentava com a graduada i pintava una taula PLANA. El backend l'ha deixat de
 * deixar escriure (`es_linear_degenerada`) i aquest mirall va amb ell.
 */
export function effectiveRegime(rule) {
  const logica = rule?.logica
  if (logica !== 'LINEAR') return logica
  if (deltaBase(rule) !== 0) return 'LINEAR'
  const brk = rule?.increment_break
  if (brk !== null && brk !== undefined && brk !== '' && Number(brk) !== 0) return 'LINEAR'
  if (intervalsDe(rule).some(iv => (deltaInterval(iv) ?? 0) !== 0)) return 'LINEAR'
  return 'FIXED'
}

/** true si la regla porta relleu: un break d'1 tram o intervals. Per apagar controls, no per
 *  classificar el règim (això és `effectiveRegime`). */
export function teRelleu(rule) {
  return hasBreak(rule) || intervalsDe(rule).length > 0
}

/**
 * true si algun interval està a MITGES (li falta una talla o el Δ).
 *
 * Un interval neix buit de Δ —el gest és «afegeix-me'n un», no «tinc-ho tot decidit»— i el
 * backend el rebutjaria amb 400 `BREAKS_FORMA`. Val més que la pantalla ho digui A LA FILA que
 * no pas que la persona ho descobreixi en un toast després de prémer Gravar: és el mateix
 * criteri que ja regeix per a la LINEAR degenerada.
 */
export function intervalsIncomplets(rule) {
  return intervalsDe(rule).some(iv => !iv || !String(iv.inici || '').trim()
    || !String(iv.final || '').trim() || deltaInterval(iv) === null)
}

/** true si la regla es presenta com a FIXED tot i estar desada com a LINEAR. */
export function isDegenerateLinear(rule) {
  return rule?.logica === 'LINEAR' && effectiveRegime(rule) === 'FIXED'
}

// ── F4-BIS · LA COLUMNA «BREAKS» ─────────────────────────────────────────────────────────────
//
// La columna d'intervals SUBSTITUEIX «Δ break» + «Talla break» a les dues superfícies
// d'autoria. Per fer-ho ha de saber dir DUES coses que fins ara vivien només al backend:
//
//   ① QUINS INTERVALS DIU UNA REGLA, sigui quina sigui la forma en què estan desats
//      (`intervalsVisibles`) — mirall de `grading_utils.intervals_de`.
//   ② QUINES TALLES SÓN LLIURES per a l'interval que s'està editant (`iniciTriables` /
//      `finalTriables`) — el que fa que el SOLAPAMENT sigui impossible de teclejar.
//
// 🔑 ① NO ÉS UNA CONVERSIÓ NI UNA MIGRACIÓ: és LLEGIR. El motor ja llegeix un break d'1 tram
// com l'interval `[talla_break_label .. última talla del run]` des del tram F, i està provat
// cel·la a cel·la contra el banc 1383. Pintar-lo com a xip és dir a la pantalla el que el motor
// ja fa; l'etiqueta NO es desplaça (convenció de MOTOR tal qual) i la BD no es toca fins que un
// gest humà edita aquell xip. És per això que les 21 regles d'1 break del banc canvien de
// DIBUIX i no de VALOR.
//
// 🚨 ② ÉS LA PORTA DE DEBÒ, I LA DEL SERVIDOR ÉS LA XARXA. `valida_breaks` rebutja el
// solapament amb 400 `BREAKS_SOLAPAMENT`; aquí el solapament no es pot ni construir, perquè els
// selectors només ofereixen talles que cap altre interval cobreix i el final només va endavant
// des de l'inici fins al primer tram ocupat. Les dues capes hi són a posta: la de dalt és
// perquè la persona no hagi de descobrir la regla xocant-hi, i la de baix perquè una pantalla
// no és mai l'única guarda d'una dada.

const normEt = (v) => String(v ?? '').trim().toUpperCase()

/** Posició d'una etiqueta dins el run, comparant com ho fa el motor (`_norm`: trim + upper).
 *  El normalitzador del run és el d'`etiquetesDelRun` i s'IMPORTA: dues còpies de «què és una
 *  etiqueta d'un run» és exactament el que ja va passar amb les amplades d'`EditableTable`. */
function posDe(etiqueta, run) {
  if (etiqueta === null || etiqueta === undefined || String(etiqueta).trim() === '') return -1
  return etiquetesDelRun(run).map(normEt).indexOf(normEt(etiqueta))
}

/**
 * MIRALL de `grading_utils.intervals_de`: el relleu d'una regla com a llista d'intervals,
 * vingui de la forma nova (`breaks`) o de la vella (`talla_break_label` + `increment_break`).
 * Amb les dues formes informades mana `breaks`, que és la que algú ha escrit expressament.
 *
 * Els derivats de la forma vella porten `llegat: true` — no per pintar-los diferent (es
 * llegeixen igual: són el mateix interval), sinó perquè qui els EDITI sàpiga que ha d'escriure
 * la forma nova i retirar la vella. Sense aquesta marca, editar-ne un deixaria la regla amb les
 * dues formes i la vella penjada dient una cosa que ja no mana.
 *
 * Sense run no hi ha derivació possible (com `aDocument`): es torna llista buida i la columna
 * dirà que no pot oferir res, que és millor que inventar-se una talla final.
 *
 * ── 🚨 LA REGLA DEL SILENCI (Agus, 21/08, del passi visual del 1383) ────────────────────────
 * **UN XIP NOMÉS ES PINTA SI DIU ALGUNA COSA.** Dos casos, i tots dos són de PINTAT, mai
 * d'esborrat de dades:
 *
 *   ① **Sota un règim que no gradua, cap interval.** Un FIXED no creix i cap tram no li
 *      aplica. Al banc 1383 hi ha VUIT files així —E5, E7, EK, EK1, EK2, G1, SLT, U: `FIXED`
 *      amb `brk=0 · break M` residuals de quan eren LINEAR— i cadascuna pintava un xip amb
 *      un ✕ que convidava a tocar una fila que no té res a dir.
 *   ② **Un tram que repeteix el delta que ja mana no és un trencament.** El break llegat `+0`
 *      sobre un general 0 (o qualsevol `+d` idèntic al general) no trenca res: pintar-lo és
 *      soroll amb forma de dada. És el mateix criteri que `BREAKS_DELTA_REDUNDANT` aplica a
 *      l'autoria, dit a la lectura.
 *
 * ⚠️ **EL SILENCI ÉS DEL LLEGAT, NO DELS INTERVALS EXPLÍCITS.** Un interval que algú ha desat
 * expressament a `breaks` es pinta SEMPRE, encara que sembli redundant: la porta ja el rebutja
 * en néixer si repeteix l'adjacent (`BREAKS_DELTA_REDUNDANT`), i si malgrat això n'hi ha un a
 * la BD, amagar-lo faria invisible una dada que el tècnic no podria ni veure ni esborrar. Una
 * ⓘ muda no vol dir «no hi ha dada».
 *
 * ⚠️ **I NO ES TOCA `grading_utils.intervals_de`.** Aquell és el MOTOR i és el node que el
 * banc mesura; un tram amb el delta del general dona el mateix valor calculat, o sigui que
 * silenciar-lo allà no canviaria cap xifra — però mouria el node del gate per un canvi de
 * DIBUIX. La regla del silenci viu on es dibuixa.
 */
export function intervalsVisibles(rule, run) {
  const propis = intervalsDe(rule)
  // ① Sota un règim que no gradua no hi ha relleu a dir. Els `breaks` residuals hi poden ser
  //    —una regla pot haver passat de LINEAR a FIXED— i es conserven a la BD; el que no fan és
  //    sortir a pantalla. (Sota STEP el relleu és LATENT per llei PG-4b-3a: es conserva i es
  //    calla, i torna a manar si algú refà la regla LINEAR.)
  if ((rule?.logica || 'LINEAR') !== 'LINEAR') return []
  if (propis.length) return propis.map(iv => ({ ...iv, llegat: false }))
  const brk = rule?.increment_break
  if (brk === null || brk === undefined || brk === '') return []
  // ② El break llegat que repeteix el delta general no trenca res.
  if (Number(brk) === deltaBase(rule)) return []
  const et = etiquetesDelRun(run)
  const i = posDe(rule?.talla_break_label, et)
  if (i < 0) return []            // etiqueta forana o sense run: cap trencament (com el motor)
  return [{ inici: et[i], final: et[et.length - 1], delta: Number(brk), llegat: true }]
}

/**
 * true si la regla porta relleu RESIDUAL sota un règim que no el llegeix: la condició que fa
 * que desar-la n'hagi de netejar els camps.
 *
 * 🚨 NOMÉS SOTA FIXED/ZERO, mai sota STEP. Sota STEP el relleu es conserva LATENT (PG-4b-3a,
 * el pas STEP↔LINEAR no-destructiu): netejar-lo en desar li trencaria la llei a una regla que
 * només estava de pas. Un FIXED, en canvi, és una destinació: si algú el torna a LINEAR ha de
 * trobar la fila neta i no un trencament fòssil que no ha escrit ell.
 */
export function relleuResidual(rule) {
  const logica = (rule?.logica || '').toUpperCase()
  if (logica !== 'FIXED' && logica !== 'ZERO') return false
  const brk = rule?.increment_break
  return intervalsDe(rule).length > 0
    || (brk !== null && brk !== undefined && brk !== '')
    || String(rule?.talla_break_label ?? '').trim() !== ''
}

/**
 * true si el relleu que es VEU surt només de la forma vella. Qui escriu sobre aquesta regla ha
 * d'enviar `breaks` I buidar `increment_break`/`talla_break_label`: una regla no pot quedar amb
 * dues formes on una és la que mana i l'altra un fòssil que altres pantalles encara llegeixen.
 */
export function relleuLlegat(rule, run) {
  return intervalsVisibles(rule, run).some(iv => iv.llegat)
}

/** Les posicions del run cobertes per algun interval, tret del d'índex `excepte`. */
function ocupades(intervals, run, excepte = -1) {
  const et = etiquetesDelRun(run)
  const fora = new Set()
  ;(intervals || []).forEach((iv, k) => {
    if (k === excepte) return
    const i = posDe(iv?.inici, et)
    const f = posDe(iv?.final, et)
    if (i < 0 || f < 0) return
    for (let p = Math.min(i, f); p <= Math.max(i, f); p += 1) fora.add(p)
  })
  return fora
}

/** Les talles que pot prendre l'INICI de l'interval `k`: totes les que ningú més cobreix. */
export function iniciTriables(intervals, run, k) {
  const et = etiquetesDelRun(run)
  const fora = ocupades(intervals, run, k)
  return et.filter((_, p) => !fora.has(p))
}

/**
 * Les talles que pot prendre el FINAL de l'interval `k` donat el seu `inici`: des de l'inici cap
 * ENDAVANT i mentre el tram segueixi lliure. Dues coses alhora, i les dues per construcció:
 * `final ≥ inici` (mai a l'inrevés → cap `BREAKS_ORDRE`) i cap talla d'un altre interval pel mig
 * (→ cap `BREAKS_SOLAPAMENT`).
 */
export function finalTriables(intervals, run, k, inici) {
  const et = etiquetesDelRun(run)
  const i = posDe(inici, et)
  if (i < 0) return []
  const fora = ocupades(intervals, run, k)
  const out = []
  for (let p = i; p < et.length && !fora.has(p); p += 1) out.push(et[p])
  return out
}

/**
 * Els intervals ORDENATS per posició d'inici — mirall del `nets.sort(key=lambda d: d['_i'])`
 * de `valida_breaks`. El servidor els desa ordenats sempre, o sigui que una llista en un altre
 * ordre és un estat que només existeix ENTRE el gest i el desat: pintar-la així faria que la
 * pantalla mostrés una cosa i la BD en guardés una altra. Els que no cauen al run van al final
 * i conserven l'ordre relatiu (no es poden situar, i inventar-los una posició seria pitjor).
 */
export function ordenaIntervals(intervals, run) {
  const et = etiquetesDelRun(run)
  return [...(intervals || [])].sort((a, b) => {
    const pa = posDe(a?.inici, et), pb = posDe(b?.inici, et)
    return (pa < 0 ? Number.MAX_SAFE_INTEGER : pa) - (pb < 0 ? Number.MAX_SAFE_INTEGER : pb)
  })
}

/**
 * L'interval que neix quan es prem [+]: el PRIMER tram lliure, cobrint-lo fins allà on arriba.
 * `null` si no queda cap talla lliure — i llavors el [+] no s'ha d'oferir: un control que obre
 * un editor sense cap opció és una porta a una paret.
 *
 * Neix SENSE Δ a posta: el gest és «afegeix-me'n un», no «ja ho tinc decidit», i el Δ és
 * justament la decisió. Mentre no es confirma, l'interval viu a l'esborrany de la columna i no
 * entra a la regla — o sigui que no pot bloquejar el Gravar de la fila.
 */
export function intervalNou(intervals, run) {
  const et = etiquetesDelRun(run)
  const fora = ocupades(intervals, run, -1)
  const i = et.findIndex((_, p) => !fora.has(p))
  if (i < 0) return null
  let f = i
  while (f + 1 < et.length && !fora.has(f + 1)) f += 1
  return { inici: et[i], final: et[f], delta: null }
}

// ── F4-QUATER · LA FRASE D'UN RELLEU ─────────────────────────────────────────────────────────
//
// **PUNT ÚNIC DE PRESENTACIÓ DELS BREAKS A TOTA LA CASA** (ordre d'Agus, 21/08). Fins avui cada
// superfície de LECTURA es pintava el seu relleu a mà i cap dues no deien el mateix de la
// mateixa regla: la consulta tenia dues columnes (`Δ break` + `Talla break`), l'Escalat les
// mateixes dues però amb una tercera veu a dins quan hi havia intervals, i la fitxa Q8b encara
// unes altres dues (`Break` + `B.Size`). Tres transcripcions del mateix concepte, i la lliçó ja
// era coneguda de les amplades d'`EditableTable`: **el que es copia, divergeix.**
//
// Ara totes llegeixen d'aquí. Una superfície nova que hagi de dir un relleu crida `fraseBreaks`
// i no decideix res pel seu compte.
//
// 🔑 LA FRASE ÉS D'INTERVAL, SEMPRE: `M→XL +3`, i els múltiples separats per ` · `. No hi ha
// «el» break ni «la» talla de break — n'hi ha un per tram, i dir-ne un de tres és pitjor que no
// dir-ne cap. Amb rang explícit inclusiu la frase és autoexplicativa.
//
// 🚨 **I PER AIXÒ L'OFF-BY-ONE DE DOCUMENT MOR AQUÍ.** Les etiquetes van en **convenció de
// MOTOR tal qual**: `inici` i `final` són les que la BD desa i les que el picker ofereix. La
// volta d'`aDocument` tenia sentit quan es pintava UNA talla sola —el full del client anomena
// el punt per l'última talla del tram petit i s'havia de poder creuar—, però un RANG amb els
// dos extrems dits no és ambigu i traduir-ne l'inici sense el final (o els dos, que voldria dir
// sortir del run per dalt) donaria una etiqueta que no casa ni amb la BD ni amb la pantalla.
// `breakConvention.aDocument` queda viu NOMÉS on encara es pinti una talla sola.
//
// 🚨 **LA REGLA DEL SILENCI ÉS LA D'`intervalsVisibles`, I NO SE'N FA UNA DE PRÒPIA.** FIXED/
// STEP → cap interval; el llegat `+0` o idèntic al general → cap interval. Aquesta funció torna
// `''` i qui crida pinta el seu propi buit (`—` a les taules, res a les etiquetes compactes).
// Que el silenci visqui en UN sol node és el que fa que les tres captures d'Agus callin alhora.

/** `+2` / `-1.5` — el signe explícit d'un delta de regla (mai una talla). */
export function signeDelta(v) {
  const n = Number(v)
  if (!Number.isFinite(n)) return String(v)
  return n < 0 ? `${n}` : `+${n}`
}

/**
 * LA FRASE D'UN RELLEU: `M→XL +3` · `S→M +3 · L→XL +4`. `''` quan la regla no diu res.
 *
 * @param {object} rule   la fila de regla (forma nova `breaks` o vella `increment_break`)
 * @param {Array}  run    el run de talles (etiquetes o `{etiqueta}`) — sense ell no hi ha
 *                        derivació del llegat possible i el relleu vell es calla
 * @param {object} opts
 * @param {(v:any)=>string} opts.delta  formatador del Δ (per dur la unitat on n'hi ha)
 * @param {number} opts.max   sostre de trams a lletrejar; la resta es diu `+N`. `0` = tots.
 *
 * ⚠️ **`max` NO ÉS UNA OPINIÓ, ÉS UN PRESSUPOST D'AMPLADA.** Només l'han de passar les
 * superfícies on el carril és finit i cada mil·límetre que es prengui el relleu és una TALLA
 * que deixa de cabre (l'Escalat i la fitxa Q8b). Qui el passi ha de portar la frase sencera al
 * `title`/tooltip: una dada retallada sense on anar-la a veure és una dada perduda.
 */
export function fraseBreaks(rule, run, { delta = signeDelta, max = 0 } = {}) {
  // ⚠️ UN INTERVAL A MITGES NO ES LLETREJA, i el sedàs és AQUÍ i no a `intervalsVisibles`: la
  // columna d'AUTORIA l'ha de veure (és el xip que la persona està escrivint, i amagar-l'hi
  // seria fer-li desaparèixer sota els dits el que acaba de teclejar), però una superfície de
  // LECTURA no en pot dir res —«S→L +0» seria inventar-se un Δ que ningú no ha escrit—. A la BD
  // no n'hi pot haver cap: `valida_breaks` els rebutja amb 400 `BREAKS_FORMA`.
  const ivs = intervalsVisibles(rule, run)
    .map(iv => ({ ...iv, _d: deltaInterval(iv) }))
    .filter(iv => iv._d !== null)
  if (!ivs.length) return ''
  const trams = ivs.map(iv => `${iv.inici}→${iv.final} ${delta(iv._d)}`)
  if (max > 0 && trams.length > max) {
    return `${trams.slice(0, max).join(' · ')} +${trams.length - max}`
  }
  return trams.join(' · ')
}

/**
 * L'ETIQUETA COMPACTA D'UNA REGLA — el delta general i el seu relleu: `+2 · M→XL +3`.
 * Torna `''` quan no hi ha res a dir.
 *
 * 🚨 VIVIA A `breakConvention.js` I HA VINGUT AQUÍ, i no és un trasllat de conveniència: des que
 * la frase és d'interval, aquesta etiqueta necessita `intervalsVisibles` —que és qui sap llegir
 * les dues formes i qui porta la regla del silenci— i `breakConvention` no el pot importar sense
 * fer un cicle (aquest mòdul ja li pren `etiquetesDelRun`). El repartiment que en queda és net i
 * és el de l'ordre: **aquí el RELLEU, allà la VOLTA DE CONVENCIÓ** d'una talla sola.
 *
 * Abans deia el llegat en convenció de document (`+2 · trencament XS +3`) i per això demanava el
 * rètol traduït «trencament»; ara no li cal cap paraula, perquè el rang es diu sol.
 */
export function etiquetaRegla(rule, run, opts = {}) {
  const ib = rule?.increment_base
  if (ib === null || ib === undefined) return ''
  const frase = fraseBreaks(rule, run, opts)
  return frase ? `${signeDelta(ib)} · ${frase}` : `${signeDelta(ib)}`
}
