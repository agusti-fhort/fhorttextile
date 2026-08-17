// E1/B2 — LA TAULA DE LA FITXA TÈCNICA: teòrica · arribada · final, per talla i mesura.
//
// R4 del brief E1: la presa de les peces físiques arribades ha de construir una taula per a la
// fitxa tècnica. Això és el CONSTRUCTOR DE DADES i prou. La PÀGINA (l'objecte `table`, les
// columnes en mm, la col·locació, el snapshot) és Q8 i viu a `TechSheetEditor`; aquí no hi ha
// cap `type: 'table'`, cap amplada i cap idioma de document.
//
// Territori: germà de `garmentFitxa.js`. Les seves files porten `garment`, o sigui que
// `partirTaules`/`agrupaPerGarment` les saben partir per prenda sense cap adaptador pel mig —
// la llei de partir viu allà i no es duplica aquí.
//
// ── FONT ÚNICA: `PieceFittingLine` ──────────────────────────────────────────────────────────
// L'entrada és el `grid` de `pieceFittings.get(id)` (`PieceFittingGridSerializer`), que ja
// serveix UNA LÍNIA PER (mesura × talla) amb `valor_teoric`, `valor_real`, `decisio`, `nota` i
// els tres eixos. No es barreja amb `GradedSpec` ni amb `taula-mesures`: dues fonts per a la
// mateixa cel·la són dues veritats, i aquesta taula ha de dir la de la PRESA.
//
// ⚠️ LÍMIT DECLARAT (17/08, i és de DATA, no de disseny): amb E1/B3 congelat, encara no hi ha
// preses reals a talles no-base a cap dada viva. El constructor està exercit amb preses
// sintètiques al banc ([QA-SC] BRW-26-SS-0002). El dia que B3 les produeixi, això no canvia.

import { identitatMesura } from './identitatMesura.js'

/** Veredictes de `PieceFittingLine.DECISIO_CHOICES`. DADA DE DOMINI: no es tradueixen mai
 *  (és el que va imprès cap al fabricant, AC/AD/RJ). `''` = sense decidir, que NO és ACCEPTED. */
export const ACCEPTED = 'ACCEPTED'
export const ADJUSTED = 'ADJUSTED'
export const REJECTED = 'REJECTED'

/**
 * ALGÚ HA TOCAT AQUESTA LÍNIA? — bessó de `fitting/esdeveniments.py::linia_te_contingut`.
 *
 * 🚨 LA RAÓ DE SER D'AQUESTA FUNCIÓ, i sense ella la taula MENTIRIA: una `PieceFittingLine`
 * neix amb `valor_real = valor_teoric` (`fitting/services.py:351`), copiada de l'spec. Si la
 * columna «arribada» llegís `valor_real` a pèl, TOTES les cel·les del full dirien que la peça
 * física s'ha mesurat i que coincideix exactament amb la teòrica — un full ple de preses que
 * ningú no ha fet. Existir no és haver mesurat.
 *
 * El predicat és el de la modista i és el MATEIX que el del backend: hi ha contingut si algú hi
 * ha DIT alguna cosa (un veredicte, una nota) o si el número s'aparta del teòric amb què va
 * néixer. Si divergissin, el Repàs i la fitxa comptarien fittings diferents.
 */
export function liniaTeContingut(linia) {
  if (!linia) return false
  // E2/B1 — LA MARCA EXPLÍCITA MANA, I VA PRIMERA. `presa_at` diu que algú ha ANOTAT la
  // cel·la; és l'única de les quatre condicions que no s'endevina. Les altres tres deriven de
  // valors i per tant no poden distingir una presa que COINCIDEIX amb la teòrica del
  // naixement de la línia — que és exactament l'estat que produeix el pre-omplert d'E2b quan
  // l'usuari el confirma tal qual.
  //
  // La inferència es queda DARRERE per a les files nascudes abans del camp (`presa_at` null),
  // que es llegeixen exactament com abans. Cap fila canvia de veredicte.
  if (linia.presa_at) return true
  if ((linia.decisio || '').trim()) return true
  if ((linia.nota || '').trim()) return true
  if (linia.valor_real == null || linia.valor_teoric == null) return false
  return Number(linia.valor_real) !== Number(linia.valor_teoric)
}

/**
 * EL VALOR QUE AQUESTA CEL·LA APORTA AL MODEL — la llei de `consolidate_base_from_fitting`,
 * dita al client sense inventar-ne cap de nova (`fitting/services.py:506-516`):
 *
 *   · REJECTED → la presa no val i NO sembra res: mana la teòrica.
 *   · talla BASE amb presa → la presa consolida (també sense veredicte: el `close` només
 *     exclou el rebuig, no el silenci).
 *   · qualsevol altra talla → mana la teòrica. **I no és una limitació del constructor**: una
 *     presa no-base no arriba mai a `BaseMeasurement` (el `close` la descarta per talla), o
 *     sigui que dir-hi el valor pres seria dir que el model l'ha adoptat quan no ho ha fet.
 *     El valor final d'una talla no-base surt de la corba re-derivada, i el que la re-deriva
 *     és la propagació —un altre acte, amb una altra porta.
 */
export function valorFinalDeLaCella({ teorica, arribada, esBase, estat }) {
  if (estat === REJECTED) return teorica
  if (esBase && arribada != null) return arribada
  return teorica
}

/** L'ordre de les talles: el run DECLARAT del model, mai l'ordre d'aparició de les línies ni
 *  l'alfabètic. `size_run_model` és el que la resta de la casa parteix per `·` (amb `;` com a
 *  separador tolerat, com fa `escala_del_model`). Sense run declarat es cau a l'ordre en què
 *  les línies apareixen, que almenys és el que el backend ha ordenat. */
export function tallesDelGrid(grid) {
  const declarat = (grid?.model?.size_run_model || '').replace(/;/g, '·')
    .split('·').map(s => s.trim()).filter(Boolean)
  if (declarat.length) return declarat
  const vistes = []
  for (const l of grid?.lines || []) {
    const sl = (l.size_label || '').trim()
    if (sl && !vistes.includes(sl)) vistes.push(sl)
  }
  return vistes
}

/**
 * Construeix les files de la taula: una per MESURA, amb les seves talles a dins.
 *
 * @param {{model?: object, lines?: Array}} grid  payload de `pieceFittings.get(id)`
 * @returns {{
 *   base: string,
 *   talles: string[],
 *   files: Array<{
 *     identitat: string, pom_id: number, capa: string, instancia: string, garment: string,
 *     codi: string, nom_en: string, nom_local: string, nom_fitxa: string|null, bm_id: number|null,
 *     valors: Object<string, {teorica: number|null, arribada: number|null,
 *                             final: number|null, estat: string}>
 *   }>
 * }}
 *
 * AGRUPAR NO ÉS REORDENAR: les files surten en ORDRE D'APARICIÓ de les línies, que és l'ordre
 * que el backend ja ha resolt (`serializers.py:352` ordena per `ordre` de fitxa + codi de
 * client + capa + instància). Reordenar-les aquí faria que la fitxa i la pantalla de presa
 * diguessin la mateixa llista en dos ordres. Mateixa llei que `agrupaPerGarment`.
 *
 * Una mesura que no té línia en una talla surt amb la cel·la BUIDA (`null` a tot i estat `''`),
 * no absent: la taula és rectangular i un forat s'ha de poder veure.
 */
export function construeixTaulaPresaPerTalla(grid) {
  const base = (grid?.model?.base_size_label || '').trim()
  const talles = tallesDelGrid(grid)
  const perMesura = new Map()

  for (const l of grid?.lines || []) {
    const ident = identitatMesura(l)
    if (!perMesura.has(ident)) {
      perMesura.set(ident, {
        identitat: ident,
        pom_id: l.pom_id,
        // Els tres eixos viatgen amb la fila: `garmentFitxa.garmentDeFila` en llegeix el
        // tercer per partir la taula per prenda, i els altres dos distingeixen germanes que
        // d'una altra manera sortirien al full amb el mateix nom i xifres diferents.
        capa: l.capa || '', instancia: l.instancia || '', garment: l.garment || '',
        codi: l.codi || '',
        nom_en: l.nom_en || '', nom_local: l.nom_local || '',
        nom_fitxa: l.nom_fitxa ?? null,
        bm_id: l.bm_id ?? null,
        is_key: !!l.is_key,
        valors: Object.fromEntries(
          talles.map(s => [s, { teorica: null, arribada: null, final: null, estat: '' }])),
      })
    }
    const fila = perMesura.get(ident)
    const sl = (l.size_label || '').trim()
    // Una línia d'una talla que el run declarat no conté NO s'inventa columna: el run mana, i
    // una talla òrfena al full seria una columna que la resta de la fitxa no coneix.
    if (!(sl in fila.valors)) continue

    const teorica = l.valor_teoric ?? null
    const estat = (l.decisio || '').trim()
    const arribada = liniaTeContingut(l) ? (l.valor_real ?? null) : null
    fila.valors[sl] = {
      teorica,
      arribada,
      final: valorFinalDeLaCella({ teorica, arribada, esBase: sl === base, estat }),
      estat,
    }
  }

  return { base, talles, files: [...perMesura.values()] }
}
