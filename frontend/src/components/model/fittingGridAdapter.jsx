// Adapter de l'eix FITTING cap al contracte de MeasureGrid (editor únic).
// Reusa l'esquelet de MeasureGrid; aquí NOMÉS es projecta la dada del fitting als seus `groups`/`rows`.
// Cap motor tocat: la propagació/STEP es despatxa per l'API existent (makeFittingOnSave).
//
// Eix (P1): UN sol GROUP, la TALLA BASE. history = versions read-only (Base, Fit 1…); columna
// activa = "Fit actual". El fitting és un ESTADI de la taula base (DECISIONS.md §2): el treball
// multi-talla viu a Escalat (vegeu `buildEscalatGroups`, més avall, que sí és per talla).
// Mateix patró d'un sol group que CheckMeasureEditor.

import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useEnumeracio } from '../../utils/vocabulariDominiFont'

import { pieceFittingLines } from '../../api/endpoints'
import { effectiveRegime } from '../../utils/gradingRegime'
import { formatDelta } from '../../utils/format'
import { aDocument, etiquetaRegla } from '../../utils/breakConvention'
import { identitatMesura } from '../../utils/identitatMesura'

// Etiqueta d'una versió: la primera (v1) és Base; les següents són Fit N amb N = version_number - 1.
const versionLabel = (vn, idx, t) =>
  idx === 0 ? t('fitting.grid.base') : t('fitting.grid.fit', { n: vn - 1 })

// L'HISTÒRIC ES PAGINA (fitting_v3). Una peça amb sis preses eixamplava la taula fins a obligar a
// scroll lateral, i el preu no era l'amplada: era que LA COLUMNA DE TREBALL ES MOVIA DE LLOC cada
// vegada que naixia una versió. Amb el paginador, la columna activa és sempre l'última i sempre al
// mateix lloc; el que es mou és la finestra d'històric, de dues en dues.
const HIST_FINESTRA = 2

function PaginadorHistoric({ from, total, onMove, t }) {
  const potEnrere = from > 0
  const potEndavant = from + HIST_FINESTRA < total
  const btn = (actiu) => ({
    border: '1px solid var(--line)', background: 'var(--white)', borderRadius: 4,
    width: 19, height: 19, font: 'inherit', fontSize: 11, lineHeight: 1, padding: 0,
    color: actiu ? 'var(--gold)' : 'var(--text-soft)', cursor: actiu ? 'pointer' : 'default',
  })
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, textTransform: 'none',
                   letterSpacing: 0, fontSize: 'var(--fs-label)', color: 'var(--text-soft)' }}>
      <button type="button" disabled={!potEnrere} onClick={() => onMove(-1)} style={btn(potEnrere)}
        title={t('fitting.grid.hist_prev')} aria-label={t('fitting.grid.hist_prev')}>‹</button>
      <span>{t('fitting.grid.hist_range', {
        de: Math.min(from + 1, total), a: Math.min(from + HIST_FINESTRA, total), total })}</span>
      <button type="button" disabled={!potEndavant} onClick={() => onMove(1)} style={btn(potEndavant)}
        title={t('fitting.grid.hist_next')} aria-label={t('fitting.grid.hist_next')}>›</button>
    </span>
  )
}

/** Finestra vàlida d'històric: les DUES ÚLTIMES preses per defecte, i mai fora de rang. */
export function finestraHistoric(total, from) {
  const max = Math.max(0, total - HIST_FINESTRA)
  return from == null ? max : Math.min(Math.max(0, from), max)
}

// Un sol group: la talla base, marcada amb ★ outline. `historyCols` = versions (finestra paginada).
// Sense `baseLabel` (model sense base_size_label; avui: cap) no hi ha eix → cap group.
//
// `opts.hist` engega el paginador (fitting) i `opts.decisio`, el bloc de Decisió (Veredicte · Nota).
// Tots dos són OPT-IN: sense ells la graella és exactament la d'abans, que és com la fan servir
// FittingDetail en revisió i el repàs.
export function buildFittingGroups(baseLabel, versionNumbers, t, opts = {}) {
  if (!baseLabel) return []
  const { hist = null, decisio = false } = opts
  const total = versionNumbers.length
  const from = hist ? finestraHistoric(total, hist.from) : 0
  const visibles = hist ? versionNumbers.slice(from, from + HIST_FINESTRA) : versionNumbers
  return [{
    key: baseLabel,
    label: (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
        <span>{baseLabel}<i className="ti ti-star" style={{ fontSize: 10, marginLeft: 4, color: 'var(--gold)' }} /></span>
        {hist && total > HIST_FINESTRA && (
          <PaginadorHistoric from={from} total={total} onMove={hist.onMove} t={t} />
        )}
      </span>
    ),
    // L'etiqueta de la versió és la seva POSICIÓ REAL a la sèrie (v1 = Base), no la posició dins
    // de la finestra: paginar no pot rebatejar les preses.
    historyCols: visibles.map(vn => ({
      key: `v${vn}`, label: versionLabel(vn, versionNumbers.indexOf(vn), t),
    })),
    activeLabel: t('fitting.grid.fit_current'),
    trailCols: decisio
      ? [{ key: 'veredicte', label: t('fitting.grid.col_verdict') },
         { key: 'nota', label: t('fitting.grid.col_note') }]
      : [],
  }]
}

// rows = files POM amb nomenclatura 2 línies + règim (per al leadCol) + la cel·la de la talla base.
// cell.history[`v${vn}`] = valor de la versió; cell.active = la cel·la editable "Fit actual"
// (lineId + valor_real + baseValue = Base, per al marcatge vermell difereix-de-base).
// Sense pomRows (font no carregada / resposta incompleta) → cap fila, no una excepció: la graella
// té un estat buit i és el que ha de sortir. Mirall de buildEscalatRows, que ja ho fa des de sempre.
export function buildFittingRows(pomRows, baseLabel, versionNumbers, opts = {}) {
  // EL VEREDICTE VIU A `line.decisio` (D-31.21) i el serializer l'emet a cada lectura, o sigui que
  // se sembra SEMPRE —també en consulta—: una sessió segellada s'ha de poder rellegir amb els
  // mateixos colors amb què es va decidir, i fins ara els perdia tots en obrir-la.
  //
  // `decisio` (opt-in) només afegeix les dues PORTES que escriuen. El seu `valors` és un buffer
  // OPTIMISTA que es consulta amb `in` i no per veritat: `null` hi és un valor legítim —«s'acaba
  // de treure el veredicte»— i amb `||` es llegiria com «no hi ha res al buffer» i la cel·la
  // tornaria a pintar el que hi havia desat.
  const { decisio = null } = opts
  return (pomRows || []).map(row => {
    const cells = {}
    if (baseLabel) {
      const line = row.cells[baseLabel]
      const evoMap = new Map((line?.evolucio || []).map(e => [e.version_number, e.valor_cm]))
      const history = {}
      for (const vn of versionNumbers) history[`v${vn}`] = evoMap.has(vn) ? evoMap.get(vn) : null
      const baseValue = line?.evolucio?.[0]?.valor_cm ?? null
      const veredicte = !line ? null
        : (decisio && line.id in decisio.valors) ? decisio.valors[line.id]
          : (line.decisio || null)
      cells[baseLabel] = {
        history,
        active: line ? {
          lineId: line.id, value: line.valor_real ?? '', baseValue,
          ...(decisio ? {
            veredicte,
            onVeredicte: (v) => decisio.onVeredicte(line.id, v),
          } : {}),
        } : null,
        ...(decisio ? {
          trail: {
            veredicte: line
              ? <VerdicteCell valor={veredicte} onTria={(v) => decisio.onVeredicte(line.id, v)} />
              : null,
            nota: line
              ? <NotaFittingCell lineId={line.id} valor={line.nota || ''} onDesa={decisio.onNota} />
              : null,
          },
        } : {}),
      }
    }
    return {
      pom_id: row.pom_id, is_key: row.is_key, pom_code: row.pom_code,
      // La NOMENCLATURA CURTA del model mana sobre el codi del catàleg, com a Mesures i a
      // Comprovació (llei de `nomenclaturaPom.js`: `nom_fitxa` primer). Aquí sortia el codi del
      // catàleg i les dues germanes del pit ensenyaven totes dues «CH», quan el tècnic les ha
      // batejades A i A-FOL: la mateixa mesura es deia diferent segons la pantalla.
      codi: row.nom_fitxa || row.codi,
      // C4 — ELS EIXOS VIATGEN AMB LA FILA. El 🚩 que hi havia aquí («les germanes ja s'han
      // perdut abans») ja no és cert: `fitting/serializers.py` emet `capa` i `instancia` a cada
      // línia des de C4/G2, i `deriveFitting` agrupa per la identitat sencera. El que faltava era
      // que la fila ho DIGUÉS: sense aquests dos camps, la graella pintava dues «Chest width»
      // seguides i el nom no deia quina era el folre.
      capa: row.capa, instancia: row.instancia,
      // v3 — LA MARCA D'UNA GERMANA DERIVADA. Una fila que el sistema ha mogut sola (origen
      // 'DERIVAT') no és una presa: ho ha de dir, perquè el número s'assembla a un de mesurat.
      // Sense `origen` al payload no es pinta res — cap superfície canvia de forma.
      marca: row.origen === 'DERIVAT' ? 'derivada' : null,
      // SET-2/T6b — la identitat de fila per CRIDA, no per còpia. Aquí hi havia la fórmula
      // inlined, byte a byte la de `identitatMesura`, i era el punt de més risc del cens: el
      // `rowKey` de `buildEscalatRows` ve del backend (`row.clau`) i T6a l'ha fet créixer a
      // quatre trams, de manera que aquesta còpia s'hauria quedat a tres EN SILENCI i dues
      // germanes de dues prendes haurien compartit clau de fila. Substituïda, no migrada al
      // costat: una còpia que es pot tornar a desincronitzar no és un arranjament.
      rowKey: row.bm_id || identitatMesura(row),
      nom_en: row.nom_en, nom_local: row.nom_local,
      nom_fitxa: row.nom_fitxa, bm_id: row.bm_id,   // P4 — autoria de nom a nivell model
      logica: row.logica, increment_base: row.increment_base,
      increment_break: row.increment_break, talla_break_label: row.talla_break_label,
      cells,
    }
  })
}

// EL BLOC DE DECISIÓ (fitting_v3) — tres botons i una nota sempre oberta.
//
// Els tres veredictes són DADA de domini i van en anglès a totes les llengües, com LINEAR/STEP:
// és el que el full imprès porta cap al fabricant (AC/AD/RJ) i el que la Montse diu en veu alta.
// Traduir-los aquí i no al paper faria que la pantalla i el full parlessin diferent.
// ELS TRES VEREDICTES venen de `/vocabulari/` (`veredictes_fitting` = `PieceFittingLine.
// DECISIO_CHOICES`). L'endpoint NO hi posa el buit, i és a posta: `''` és l'absència de
// veredicte, no un quart membre —v. la capçalera de `vocabulari_views.py`—, i el gest de
// desdir-se (tornar a clicar l'actiu) el continua produint aquesta pantalla, que és on viu.
//
// VERDICTE_TO ES QUEDA: és crom —dos tokens de color per veredicte— indexat pel codi, no una
// segona llista. Un veredicte que l'endpoint dugués i el mapa no tingués sortiria sense color,
// però sortiria; per això la cel·la el llegeix amb `?.` i no amb accés directe.
// A9 · §1b(d) — L'AJUSTAT ES PARTEIX EN DOS TOKENS. `--warn-state` (#ff9942) sobre el seu fons
// dona 1.86:1 com a TEXT: inadmissible, i contrari al vet de C5. La marca (subratllat, vora) va
// en `--warn-state`; la TINTA, en `--warn-ink` (5.32:1, AA). Els altres dos ja complien.
const VERDICTE_TO = {
  ACCEPTED: { col: 'var(--ok)', marca: 'var(--ok)', bg: 'var(--ok-bg)' },
  ADJUSTED: { col: 'var(--warn-ink)', marca: 'var(--warn-state)', bg: 'var(--warn-state-bg)' },
  REJECTED: { col: 'var(--err)', marca: 'var(--err)', bg: 'var(--err-bg)' },
}

export function VerdicteCell({ valor, onTria }) {
  // Sense vocabulari no s'ofereix cap veredicte. La cel·la segueix pintant el que la línia ja
  // porta (això ho fa la graella), però decidir de nou demana saber entre què es decideix.
  const { codis: vocVerdictes } = useEnumeracio('veredictes_fitting')
  const VERDICTES = vocVerdictes || []
  // El CODI no es tradueix (v. la nota de sobre) però el seu SIGNIFICAT sí: qui no sap què
  // vol dir ADJUSTED ho ha de poder llegir en la seva llengua sense sortir de la graella.
  // Va a `title` i a `aria-label`, o sigui que el que viatja al paper segueix sent el codi.
  const { t } = useTranslation()
  return (
    /* §7 · CONTROLS DE VEREDICTE: botons NEUTRES en repòs; el triat, `--sel` + SUBRATLLAT del
       color del veredicte. El color PLE no és seu — és del RESULTAT (el número, que ja el porta
       amb la seva tinta, el seu pes i el ratllat del rebuig). Abans el botó triat s'omplia del
       fons del semàfor i competia amb la xifra que havia de manar. */
    <span style={{ display: 'inline-flex', borderWidth: 1, borderStyle: 'solid',
                   borderColor: 'var(--line)', borderRadius: 'var(--r-ctrl)',
                   overflow: 'hidden', background: 'var(--panel)' }}>
      {VERDICTES.map((v, i) => {
        const on = valor === v
        const to = VERDICTE_TO[v] || {}
        return (
          <button key={v} type="button"
            // Tornar a clicar el veredicte actiu el TREU: decidir i desdir-se han de costar el
            // mateix, i no hi ha cap altre gest per tornar a «sense decidir».
            onClick={() => onTria(on ? null : v)}
            title={t(`fitting.grid.verdicte.${v.toLowerCase()}`)}
            aria-label={t(`fitting.grid.verdicte.${v.toLowerCase()}`)}
            aria-pressed={on}
            style={{
              border: 'none',
              borderRightWidth: i < VERDICTES.length - 1 ? 1 : 0,
              borderRightStyle: 'solid', borderRightColor: 'var(--line)',
              background: on ? 'var(--sel)' : 'transparent',
              color: on ? (to.col || 'var(--text-main)') : 'var(--text-soft)',
              // EL SUBRATLLAT és la marca del triat (§7). `box-shadow` i no `border-bottom`
              // perquè no mogui res: la fila d'una graella no pot saltar 2px en decidir.
              boxShadow: on ? `inset 0 -2px 0 ${to.marca || 'var(--text-main)'}` : undefined,
              fontWeight: on ? 600 : 400, fontFamily: 'inherit', fontSize: 'var(--fs-label)',
              letterSpacing: '0.04em', padding: '4px 9px', cursor: 'pointer',
            }}>{v}</button>
        )
      })}
    </span>
  )
}

// LA NOTA, SEMPRE OBERTA. No és un desplegable ni un icona que s'ha de trobar: en un fitting es
// dicta en veu alta mentre es mesura, i el camp ha de ser-hi abans que ningú el busqui. Desa on
// blur i només si ha canviat (mateix criteri que el bateig).
export function NotaFittingCell({ lineId, valor, onDesa }) {
  const [txt, setTxt] = useState(valor ?? '')
  const [focused, setFocused] = useState(false)
  useEffect(() => { if (!focused) setTxt(valor ?? '') }, [valor, focused])
  const { t } = useTranslation()
  return (
    <input
      value={txt} placeholder={t('fitting.grid.note_ph')}
      onChange={e => setTxt(e.target.value)}
      onFocus={() => setFocused(true)}
      onBlur={() => { setFocused(false); if ((txt ?? '') !== (valor ?? '')) onDesa(lineId, txt) }}
      onKeyDown={e => { if (e.key === 'Enter') e.currentTarget.blur() }}
      style={{
        width: '100%', minWidth: 150, font: 'inherit', fontSize: 'var(--fs-body)',
        color: 'var(--text-main)', border: '1px solid var(--line)', borderRadius: 5,
        padding: '3px 8px', background: 'var(--white)', boxSizing: 'border-box',
      }}
    />
  )
}

// Etiqueta compacta de regla (delta · trencament).
//
// 🔑 EL TRENCAMENT ES DIU EN CONVENCIÓ DE DOCUMENT (Agus, 10/08): la BD desa la primera talla
// del tram gran i aquí es pinta l'ÚLTIMA DEL PETIT, que és com l'anomena el full del client.
// La volta la fa `utils/breakConvention`, que és l'únic lloc de la casa on viu el ±1 — abans
// aquesta funció era una còpia calcada de la de `CheckMeasureEditor` i totes dues pintaven
// `talla_break_label` cru.
function regleLabel(row, t, sizeRun) {
  if (row.logica == null) return ''
  if (row.logica === 'STEP') return t('fitting.grid.rule_free')
  // LINEAR+0 sense break = FIXED: no té delta a ensenyar (§LLEI a utils/gradingRegime).
  if (effectiveRegime(row) === 'FIXED') return ''
  return etiquetaRegla(row, sizeRun, t('fitting.grid.break'))
}

// leadCol Règim del fitting (sticky): a diferència del check (lectura), aquí el règim és EDITABLE
// (select LINEAR/STEP) perquè d'ell depèn la propagació. Sota, l'etiqueta de regla a 2 línies.
// LINEAR/STEP són valors de DADA (row.logica) → no es tradueixen.
// `compacte` (FIX-4): amaga la llegenda de regla de sota el desplegable. La fa servir Escalat,
// on el delta i el break ja tenen COLUMNA pròpia — repetir-los aquí seria la mateixa dada dues
// vegades, i és precisament la lletra petita el que ningú llegia.
export function regimeLeadCol(t, onRegimChange, readOnly = false, { compacte = false, sizeRun = [] } = {}) {
  return {
    key: 'regim', label: t('fitting.grid.regime'), width: compacte ? 100 : 118,
    render: (row) => {
      // Règim EFECTIU, no el desat: LINEAR+0 sense break es presenta com a FIXED. Quan passa,
      // FIXED s'afegeix com a opció del desplegable perquè el valor visible sigui triable i
      // el tècnic pugui segellar-lo (POST regim FIXED) sense que sembli un LINEAR que gradua.
      const regim = effectiveRegime(row)
      return (
      <div>
        {readOnly ? (
          <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-main)' }}>{regim ?? '—'}</div>
        ) : (
          <select
            value={regim ?? ''}
            onChange={e => onRegimChange(row, e.target.value)}
            style={{
              font: 'inherit', fontSize: 'var(--fs-label)', width: '100%', padding: '1px 2px',
              border: '1px solid var(--line)', borderRadius: 4,
              background: 'var(--white)', color: 'var(--text-main)', boxSizing: 'border-box',
            }}
          >
            {row.logica == null && <option value="">—</option>}
            <option value="LINEAR">LINEAR</option>
            <option value="STEP">STEP</option>
            {regim === 'FIXED' && <option value="FIXED">FIXED</option>}
          </select>
        )}
        {!compacte && regleLabel(row, t, sizeRun) && (
          <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-soft)', whiteSpace: 'nowrap', marginTop: 1 }}>
            {regleLabel(row, t, sizeRun)}
          </div>
        )}
      </div>
      )
    },
  }
}

// --- ESCALAT (taula propagada del model) ---------------------------------------------------------
// LLEI: propagar = llenç net, NO eix de versions per comparar. Per talla: 1 columna read-only "Base"
// (valor vigent propagat) + columna activa "Fit actual" EDITABLE per a TOTES les talles, BASE inclosa
// (el fitting no la bloqueja). Editar una talla propaga per regla (onSave → escalat/ajustar-talla).
// Reusa regimeLeadCol. lineId = `${clau}:${size}`. S'alimenta de taula-mesures (versió vigent).
//
// C4/BLOC 3 — la primera meitat del lineId és la CLAU DE LA MESURA, no el `pom_id`. Era
// `${pom_id}:${size}` i, com que `taula-mesures` pinta una fila per germana, l'exterior i el
// folre del mateix pit a la talla M generaven el MATEIX lineId: una sola entrada al `perLinia`
// de `PropagatedEditor` (la guarda de plausibilitat llegia la base de l'altra germana) i una
// sola entrada al buffer de teclejat de `MeasureGrid` (escriure a una cel·la n'omplia dues).
// La fila ja porta la clau sencera des del bloc 1; aquí només s'hi endolla.
//
// El separador segueix sent `:` i el desmuntatge segueix sent per l'ÚLTIM `:`, que és el que
// separa la talla: la clau de mesura fa servir `|` i no n'hi posa cap (v. la capçalera de
// `pom/identitat.py`, que tria el separador precisament per no col·lidir amb aquest).
export function buildEscalatGroups(sizeLabels, baseLabel, t) {
  return sizeLabels.map(s => ({
    key: s,
    label: s === baseLabel
      ? <span>{s}<i className="ti ti-star" style={{ fontSize: 10, marginLeft: 4, color: 'var(--gold)' }} /></span>
      : s,
    historyCols: [{ key: 'vigent', label: t('fitting.grid.base') }],
    activeLabel: t('fitting.grid.fit_current'),
    trailCols: [],
  }))
}

export function buildEscalatRows(rows, sizeLabels, baseLabel) {
  return (rows || []).map(row => {
    const cells = {}
    for (const s of sizeLabels) {
      const v = s === baseLabel ? row.base_value_cm : (row.graded?.[s] ?? null)
      cells[s] = {
        history: { vigent: v },
        // TOTES editables (base inclosa, sense readonly); baseValue per al marcatge difereix-de-base.
        active: { lineId: `${row.clau || row.pom_id}:${s}`, value: v == null ? '' : v, baseValue: v },
      }
    }
    return {
      // Nomenclatura client COHERENT amb Mesures: prevaler nom_fitxa (nom de model editable) sobre
      // pom_code (codi_client). taula-mesures ja retorna nom_fitxa.
      pom_id: row.pom_id, codi: row.nom_fitxa || row.pom_code, is_key: row.is_key,
      // C4/BLOC 3 — els eixos viatgen amb la fila perquè qui hi escrigui no hagi de desmuntar
      // el lineId per saber de quina germana parla. L'escriptura (`escalat/ajustar-talla`)
      // encara és per `pom_id` sol: desancorar-la és feina del bloc 2.
      clau: row.clau, capa: row.capa, instancia: row.instancia,
      // Clau de fila per a MeasureGrid: la identitat sencera de la mesura.
      rowKey: row.clau || row.pom_id,
      nom_en: row.nom_en, nom_local: row.nom_ca,
      logica: row.logica, increment_base: row.increment_base,
      increment_break: row.increment_break, talla_break_label: row.talla_break_label,
      // FIX-4 — la BASE del POM viatja amb la fila: és el referent de la guarda de plausibilitat
      // (una cel·la de talla molt lluny de la base sembla un increment, no una mesura).
      base_value_cm: row.base_value_cm ?? null,
      cells,
    }
  })
}

// FIX-4 (DIAGNOSI_MESURES_TEA_205) — la REGLA surt de la lletra petita i es fa COLUMNES.
//
// Fins ara el delta i el break vivien com una llegenda de dues línies sota el desplegable de
// règim (`+1 · break XS +1.5`), enganxats a les cel·les de mesura. Al 205 això va acabar amb un
// `1` escrit a la cel·la de talla d'un POM amb base 46: mirats de reüll, un increment i una
// llargada són el mateix número. Ara són columnes pròpies, sota la capçalera «Regla de graduació»
// i amb el fons crema de la casa, separades de les mesures per un filet gruixut.
//
// Els deltes es pinten SEMPRE amb signe (`formatDelta`) i les capçaleres porten Δ; les cel·les de
// talla, planes amb la seva unitat. Cap cel·la de talla mostra mai un '+'.
export function escalatRuleLeadCols(t, onRegimChange, readOnly = false, unit = 'CM', sizeRun = []) {
  const cap = { fontSize: 'var(--fs-body)', color: 'var(--text-main)', fontVariantNumeric: 'tabular-nums' }
  const buit = { fontSize: 'var(--fs-body)', color: 'var(--text-soft)' }
  // Un règim sense delta (FIXED, o STEP amb valors lliures) no té Δ que ensenyar: guió, no zero.
  const mostraDelta = (row) => effectiveRegime(row) === 'LINEAR'
  return [
    regimeLeadCol(t, onRegimChange, readOnly, { compacte: true, sizeRun }),
    {
      key: 'delta', label: t('measuregrid.regla_delta'), width: 72,
      render: (row) => (mostraDelta(row) && row.increment_base != null
        ? <span style={cap}>{formatDelta(row.increment_base, unit)}</span>
        : <span style={buit}>—</span>),
    },
    {
      key: 'delta_break', label: t('measuregrid.regla_delta_break'), width: 82,
      render: (row) => (mostraDelta(row) && row.increment_break != null
        ? <span style={cap}>{formatDelta(row.increment_break, unit)}</span>
        : <span style={buit}>—</span>),
    },
    {
      key: 'talla_break', label: t('measuregrid.regla_talla_break'), width: 92,
      // Etiqueta de talla: DADA de domini (XS, 3XL) — no es tradueix ni porta signe. El que sí
      // que se li fa és la volta de CONVENCIÓ: es pinta la del document, no la desada.
      render: (row) => {
        const doc = mostraDelta(row) ? aDocument(row.talla_break_label, sizeRun) : null
        return doc
          ? <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>{doc}</span>
          : <span style={buit}>—</span>
      },
    },
  ]
}

export function makeFittingOnSave(lineRegimeMap) {
  return (lineId, value) => {
    const regime = lineRegimeMap.get(lineId)
    if (regime === 'STEP') return pieceFittingLines.update(lineId, { valor_real: value })
    return pieceFittingLines.propagar(lineId, value)
  }
}
