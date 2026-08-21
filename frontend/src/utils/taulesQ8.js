// Q8/B4 — LES FILES DE LES TAULES DE LA FITXA: base · fitting · grading · size set.
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
//   Q8e base     → `GET /models/<id>/base-measurements/`, que és el payload que l'editor JA té
//                   carregat (`pomRows`) i que porta la base consolidada, la tolerància vigent i
//                   l'eix de la prenda. ⚠️ La frase de dues línies més amunt és de `graded-table/`
//                   i NOMÉS d'ell: `base-measurements/` sí que serveix `garment` (des de SET-2/F1).
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
 * 🚨 Q8-ter/T1 · LA XIFRA AMB QUÈ LA PRENDA VA ARRIBAR, DE TOTES LES MESURES.
 *
 * `construeixTaulaPresaPerTalla` serveix `arribada` filtrada per `liniaTeContingut`, i **per a la
 * seva taula això és el correcte**: allà es documenta una presa VIVA, on una línia intacta encara
 * no s'ha mesurat i pintar-hi el número que va copiar de la teòrica en néixer seria inventar-se
 * una presa (v. l'acta d'aquell mòdul, que és el bessó del backend).
 *
 * Les taules de Q8 llegeixen una altra cosa: una sessió **TANCADA**. Allà el cicle s'ha acabat, la
 * prenda física s'ha mesurat sencera i el `close` ja ha consolidat: una línia amb el real igual al
 * teòric vol dir «va arribar clavada», no «ningú no l'ha mirada». Ometre-la deixava la columna
 * ACTUAL mig buida en un document que ha de dir com van arribar TOTES les mesures (QA d'Agus
 * sobre el PDF del 1379).
 *
 * Per això es llegeix `valor_real` cru del MATEIX grid —cap font nova— i el predicat de contingut
 * NO es toca ni es duplica: és d'E2 i segueix manant a la seva superfície.
 */
function realsPerIdentitat(grid, talla) {
  const out = new Map()
  for (const l of grid?.lines || []) {
    if (talla != null && (l.size_label || '').trim() !== talla) continue
    out.set(`${identitatMesura(l)}@${(l.size_label || '').trim()}`, l.valor_real ?? null)
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
 * ⚠️ AQUEST DOCSTRING DEIA «`actual` és `null` quan ningú no ha mesurat», i des de T1 (18/08) és
 * FALS: la sessió que aquesta taula documenta és TANCADA, i allà `valor_real` és com va arribar la
 * prenda —clavada inclosa—. Es corregeix aquí i no s'hi deixa: un docstring datat i fals és
 * exactament el que fa néixer el brief equivocat de la sessió següent. V. `realsPerIdentitat`.
 *
 * @param {object} grid  payload de `pieceFittings.get(id)`
 * @returns {{base: string, files: Array}}
 */
export function filesFitting(grid) {
  const { base, files } = construeixTaulaPresaPerTalla(grid)
  const notes = notesPerIdentitat(grid, base)
  const reals = realsPerIdentitat(grid, base)
  return {
    base,
    files: files.map(f => {
      const v = f.valors?.[base] || { teorica: null, arribada: null, estat: '' }
      // T1 — TOTES les mesures de la talla de la sessió tancada, no només les que s'han mogut.
      const actual = reals.has(`${f.identitat}@${base}`) ? reals.get(`${f.identitat}@${base}`) : v.arribada
      return {
        ...f,
        aprovada: v.teorica,
        actual,
        dif: diferencia(actual, v.teorica),
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
  // T1 — mateixa llei que la taula de fitting, i per la mateixa raó: la sessió és TANCADA i la
  // columna Actual ha de dir com va arribar CADA talla, no només les que algú va corregir.
  const reals = realsPerIdentitat(grid, null)
  return {
    base,
    talles,
    files: files.map(f => ({
      ...f,
      celles: Object.fromEntries(talles.map(s => {
        const v = f.valors?.[s] || { teorica: null, arribada: null, estat: '' }
        const clau = `${f.identitat}@${s}`
        const actual = reals.has(clau) ? reals.get(clau) : v.arribada
        return [s, {
          teorica: v.teorica,
          actual,
          dif: diferencia(actual, v.teorica),
          // R2 — el veredicte NOMÉS a la base; a la resta, cadena buida i no `null`, perquè la
          // cel·la existeix i el que no hi ha és decisió.
          veredicte: s === base ? v.estat : '',
        }]
      })),
    })),
  }
}

/**
 * Q8c-consolidat · EL SIZE SET QUAN ENCARA NINGÚ NO L'HA MESURAT.
 *
 * 🚨 LA CORRECCIÓ DE B0. El size set **no és una propietat del fitting: és LA CORBA DEL MODEL**.
 * Viu consolidada a `GradedSpec` i la serveix `taula-mesures` sense demanar cap sessió. Lligar
 * aquesta taula a l'existència d'una sessió TANCADA feia que un model amb l'escalat tancat i cap
 * fitting segellat no pogués documentar el seu propi size set — i una fitxa documenta cicles
 * ACABATS, que és exactament el cas.
 *
 * El que aporta una sessió tancada són les PRESES (`Actual`, `Dif`, `Verdict`). Que no n'hi hagi
 * cap no vol dir que no hi hagi size set: vol dir que **encara ningú no l'ha mesurat**, i la
 * columna ha de sortir BUIDA, no absent. Per això la forma de sortida és la MATEIXA que
 * `filesSizeSet` i qui pinta no ha de saber de quina de les dues ve.
 */
export function filesSizeSetConsolidat(rows, talles, base) {
  return {
    base,
    talles: talles || [],
    files: filesGrading(rows, talles, base).map(f => ({
      ...f,
      celles: Object.fromEntries((talles || []).map(s => [s, {
        teorica: f.valors?.[s] ?? null,
        actual: null, dif: null, veredicte: '',
      }])),
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
    // H-bis/4 — ELS CAMPS CRUS DE LA NOMENCLATURA, per al cas en què la fila no tingui
    // resident al model (v. `residentQ8` a la pàgina, que és qui mana). `taula-mesures` els
    // bateja amb noms propis —`client_code` és l'ÀLIES del client i `pom_code` és el codi de
    // la casa—: la traducció es fa aquí, que és la frontera del payload, i mai al resolutor.
    // La lliçó d'H segueix vigent: aquestes claus s'han comprovat al payload d'AQUEST endpoint,
    // no copiades del constructor germà.
    client_alias: r.client_code || null,
    codi_client: r.pom_code || '',
    pom_abbreviation: r.abbreviation || '',
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

/**
 * Q8e · LA TAULA DE MESURES DE TALLA BASE — la base sola, sense graduació.
 *
 * 🔑 QUÈ ÉS «L'ÚLTIM FIT VÀLID», i per què NO és una consulta a part. La llei del domini és que
 * *l'última mesura escrita és la veritat* —temporal, no d'origen—, i està MATERIALITZADA a
 * `BaseMeasurement.base_value_cm`: `consolidate_base_from_fitting` (`fitting/services.py:669`)
 * hi escriu la darrera línia VÀLIDA en tancar el fitting (`close_piece_fitting`) i en propagar
 * (`models_app/views.py:3090`, amb `origen='FITTED'`). Un model sense cap fitting tancat porta
 * la base que la talla base va confirmar. Per tant **la taula només ha de llegir la base**: anar
 * a buscar «l'últim fit» a un històric seria una segona veritat per a la mateixa cel·la, i el dia
 * que les dues no coincidissin no hi hauria manera de dir quina menteix.
 *
 * FONT ÚNICA: `GET /models/<id>/base-measurements/` (`pom/wizard_views.py:572`), que és el
 * MATEIX payload que l'editor ja té carregat a `pomRows` des del muntatge. Cap crida nova.
 *
 * ⚠️ LA DIAGNOSI DEIA QUE AQUESTA FONT NO SERVIA NI L'EIX NI LA TOLERÀNCIA, I SÓN DUES COSES
 * FALSES, cadascuna per un motiu diferent —i totes dues comprovades al COS de la vista, no al
 * seu voltant—:
 *   · `garment` hi és des de SET-2/F1 (`wizard_views.py:674`). La frase «no serveix garment» era
 *     de `graded-table/` (v. el capçal d'aquest fitxer) i es va traslladar d'endpoint.
 *   · `tol_minus`/`tol_plus` hi són i **ja arriben RESOLTS** (`:697-698`, `_tol_vigent`): la de la
 *     mesura mana, la del catàleg és el pla B i el 0.6 de la casa és l'últim recurs. Qui va dir
 *     que no hi eren mirava `BaseMeasurementSerializer` (`models_app/serializers.py:432`), que és
 *     el ViewSet del router —un ALTRE endpoint— i que a més els diu `tolerancia_minus/plus`.
 *     Cap serializer no s'ha hagut de tocar.
 *
 * FILES: TOTES les mesures vives, **inclosos els POM sense xifra**. És la llei de la versió
 * retirada i es conserva sencera: *la cel·la buida en una fitxa impresa és on el tècnic anota a
 * mà; podar les files en silenci seria decidir per ell què no li importa.*
 *
 * @param {Array} bms  `results` de `base-measurements/` (l'estat `pomRows` de l'editor)
 */
export function filesBase(bms) {
  return (bms || []).map(bm => ({
    identitat: identitatMesura(bm),
    pom_id: bm.pom_id,
    capa: bm.capa || '', instancia: bm.instancia || '', garment: bm.garment || '',
    // ELS DOS NOMS LLARGS, amb les mateixes claus que `filesGrading` emet, perquè `nomsDePom`
    // resolgui el bateig del model igual a totes dues taules (regla d'or 31/07).
    //
    // 🚨 I `nom_client` AMB ELLS, que `filesGrading` no arrossega i aquí NO és opcional. Un POM
    // tenant-only —sense `pom_global`— no té ni `nom_en` ni `nom_ca`: el catàleg d'un client
    // importat el bateja NOMÉS a `POMMaster.nom_client`, i és l'últim graó de la cadena de
    // `nomsDePom`. Sense passar-lo, `canonic` sortia CADENA BUIDA i la columna POM naixia muda
    // per a un model sencer —mesurat al banc 1383, on les 21 files són exactament aquest cas—.
    // Que la taula d'escalat no el necessiti no vol dir que no calgui: aquella beu de
    // `taula-mesures`, que resol els noms d'una altra manera.
    nom_en: bm.nom_en || '', nom_local: bm.nom_ca || '', nom_client: bm.nom_client || '',
    nom_canonic_model: bm.nom_canonic_model || '', nom_traduit_model: bm.nom_traduit_model || '',
    // I LA NOMENCLATURA CURTA, que aquesta taula sí que pinta en columna pròpia: es passen els
    // camps CRUS que `nomenclaturaDePom` sap encadenar (nom_fitxa → àlies del client → codi
    // canònic → codi de la casa), mai una cadena ja resolta aquí. El resolutor és d'aquell mòdul.
    nom_fitxa: bm.nom_fitxa || null,
    client_alias: bm.client_alias || null,
    pom_code_global: bm.pom_code_global || '',
    codi_client: bm.codi_client || '',
    pom_abbreviation: bm.pom_abbreviation || '',
    is_key: !!bm.pom_is_key,
    base: bm.base_value_cm ?? null,
    // 🚨 H-bis/1 — LA TOLERÀNCIA NO HI ÉS, i no és un oblit: Agus va REVOCAR la columna el
    // 21/08 sobre la captura del 1383, i amb la columna se'n va la dada. `base-measurements/`
    // la serveix ja resolta (`tol_minus`/`tol_plus`, `_tol_vigent`) i qui la vulgui la té a un
    // camp de distància; el que no ha de quedar és un camp que ningú no pinta fent de promesa
    // que la taula la porta.
    // La data d'escriptura de CADA fila: la de la taula és la més recent del grup, que és
    // exactament el que la llei temporal declara com a veritat vigent. La tria la fa la pàgina.
    updated_at: bm.updated_at || null,
  }))
}
