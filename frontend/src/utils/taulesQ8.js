// Q8/B4 — LES FILES DE LES TRES TAULES DE LA FITXA: fitting · grading · size set.
//
// Això és el CONSTRUCTOR DE DADES i prou —el mateix repartiment de feina que `taulaPresaPerTalla`
// declara al seu capçal—. Aquí no hi ha cap `type: 'table'`, cap amplada en mm, cap idioma de
// document i cap color: la PÀGINA (columnes, tipografia, vermells, snapshot, col·locació) viu a
// `TechSheetEditor`, que és qui sap de quin document parlem i en quina unitat.
//
// ── LES FONTS, I CAP CONTRACTE PARAL·LEL ────────────────────────────────────────────────────
//   Q8a fitting  ·  Q8c size set → `PieceFittingLine` via el `grid` de `pieceFittings.get(id)`,
//                   passat per `construeixTaulaPresaPerTalla` (B2). NO es reimplementa: el
//                   predicat de «algú ha tocat aquesta línia» és d'aquell mòdul i és el bessó del
//                   backend; una segona còpia aquí faria que la fitxa i el Repàs comptessin
//                   fittings diferents.
//   Q8b grading  → `GET /models/<id>/taula-mesures/`, que porta EN UN SOL PAYLOAD el règim
//                   (`logica`/`increment_base`/`increment_break`/`talla_break_label`), els valors
//                   per talla (`graded` + `base_value_cm`) i l'eix de la prenda (`garment`).
//                   `graded-table/` NO serveix `garment` i faria caure totes les files a la mare.
//
// Les files que en surten porten `garment`, o sigui que `agrupaPerGarment`/`grupsDelFull` les
// saben repartir per peça sense cap adaptador pel mig.

import { identitatMesura } from './identitatMesura.js'
import { construeixTaulaPresaPerTalla } from './taulaPresaPerTalla.js'

/** Resta de dues mesures amb la precisió del domini. `null` si no hi ha les dues xifres: un 0
 *  quan una banda no existeix diria «coincideixen», que és justament el contrari. */
export function diferencia(actual, referencia) {
  if (actual == null || referencia == null) return null
  return Number((Number(actual) - Number(referencia)).toFixed(2))
}

/** La nota que la modista ha escrit a la cel·la, per identitat de mesura i per talla. Surt del
 *  MATEIX `grid` —no és cap font nova—; només és un camp que el constructor de B2 no arrossega
 *  perquè la seva taula no en té columna. */
function notesPerIdentitat(grid, talla) {
  const out = new Map()
  for (const l of grid?.lines || []) {
    if ((l.size_label || '').trim() !== talla) continue
    const nota = (l.nota || '').trim()
    if (nota) out.set(identitatMesura(l), nota)
  }
  return out
}

/**
 * Q8a · LA TAULA DE FITTING — una fila per mesura, a la TALLA BASE.
 *
 * 🔑 D'ON SURT LA COLUMNA DE LA TALLA BASE, que és la decisió que sosté tota la taula:
 * `valor_teoric` de la línia és l'estat de l'spec **a l'obertura de la sessió**, o sigui l'última
 * mesura vàlida aprovada per precedència temporal. Amb dos fittings tancats, el teòric del segon
 * JA és la consolidació del primer (`consolidate_base_from_fitting`), de manera que llegir-lo dona
 * «la de l'últim aprovat» sense haver de recórrer cap històric. Anar-la a buscar a una altra banda
 * seria una segona veritat per a la mateixa cel·la.
 *
 * `actual` és `null` quan ningú no ha mesurat: una `PieceFittingLine` neix amb `valor_real` copiat
 * del teòric i llegir-lo a pèl ompliria la fitxa de preses que no s'han fet (v. `liniaTeContingut`).
 *
 * @param {object} grid  payload de `pieceFittings.get(id)`
 * @returns {{base: string, files: Array}}
 */
export function filesFitting(grid) {
  const { base, files } = construeixTaulaPresaPerTalla(grid)
  const notes = notesPerIdentitat(grid, base)
  return {
    base,
    files: files.map(f => {
      const v = f.valors?.[base] || { teorica: null, arribada: null, estat: '' }
      return {
        ...f,
        aprovada: v.teorica,
        actual: v.arribada,
        dif: diferencia(v.arribada, v.teorica),
        veredicte: v.estat,
        nota: notes.get(f.identitat) || '',
      }
    }),
  }
}

/**
 * Q8c · LA TAULA DE SIZE SET — una fila per mesura, amb TOTES les talles a dins.
 *
 * Mateix patró que Q8a però per cada talla del run. **Veredicte només a la talla base** (R2): una
 * talla no-base no arriba mai a `BaseMeasurement` —el `close` la descarta— i posar-hi un veredicte
 * diria que el model l'ha adoptada quan no ho ha fet.
 */
export function filesSizeSet(grid) {
  const { base, talles, files } = construeixTaulaPresaPerTalla(grid)
  return {
    base,
    talles,
    files: files.map(f => ({
      ...f,
      celles: Object.fromEntries(talles.map(s => {
        const v = f.valors?.[s] || { teorica: null, arribada: null, estat: '' }
        return [s, {
          teorica: v.teorica,
          actual: v.arribada,
          dif: diferencia(v.arribada, v.teorica),
          // R2 — el veredicte NOMÉS a la base; a la resta, cadena buida i no `null`, perquè la
          // cel·la existeix i el que no hi ha és decisió.
          veredicte: s === base ? v.estat : '',
        }]
      })),
    })),
  }
}

/** Les notes de la talla base, en taula PRÒPIA (l'espec de Q8c les treu de la graella: amb una
 *  columna per talla no hi cap ni una frase). Només les files que en tenen: una taula de notes
 *  buides seria una columna de guions. */
export function filesNotes(grid) {
  const { base, files } = construeixTaulaPresaPerTalla(grid)
  const notes = notesPerIdentitat(grid, base)
  return {
    base,
    files: files
      .map(f => ({ ...f, nota: notes.get(f.identitat) || '' }))
      .filter(f => f.nota),
  }
}

/**
 * Q8b · LA TAULA DE GRADING — règim + corba, per mesura i per talla.
 *
 * El VALOR d'una talla es resol amb el mateix criteri que la pantalla d'Escalat
 * (`fittingGridAdapter.jsx:381`): la base viu a `base_value_cm` i la resta a `graded`. Es replica
 * el CRITERI, no el codi — aquell mòdul és de la superfície de Mesures i no es toca.
 *
 * `talla_break_label` surt CRU: la traducció a convenció de DOCUMENT (±1 posició dins del run) és
 * de `utils/breakConvention` i es fa just abans de pintar, mai aquí. Un constructor que la
 * desplacés tornaria una etiqueta que ja no casa amb la BD.
 *
 * @param {Array} rows      `rows` de `taula-mesures`
 * @param {string[]} talles el run del model, en ordre
 * @param {string} base     etiqueta de la talla base
 */
export function filesGrading(rows, talles, base) {
  return (rows || []).map(r => ({
    identitat: identitatMesura(r),
    pom_id: r.pom_id,
    capa: r.capa || '', instancia: r.instancia || '', garment: r.garment || '',
    codi: r.pom_code || r.abbreviation || '',
    nom_en: r.nom_en || '', nom_local: r.nom_ca || '',
    nom_fitxa: r.nom_fitxa || null,
    nom_canonic_model: r.nom_canonic_model || '', nom_traduit_model: r.nom_traduit_model || '',
    is_key: !!r.is_key,
    regla: r.logica || '',
    delta: r.increment_base ?? null,
    delta_break: r.increment_break ?? null,
    talla_break: r.talla_break_label || null,
    valors: Object.fromEntries((talles || []).map(s => [
      s, s === base ? (r.base_value_cm ?? null) : (r.graded?.[s] ?? null),
    ])),
  }))
}
