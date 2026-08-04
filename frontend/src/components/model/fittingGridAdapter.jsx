// Adapter de l'eix FITTING cap al contracte de MeasureGrid (editor únic).
// Reusa l'esquelet de MeasureGrid; aquí NOMÉS es projecta la dada del fitting als seus `groups`/`rows`.
// Cap motor tocat: la propagació/STEP es despatxa per l'API existent (makeFittingOnSave).
//
// Eix (P1): UN sol GROUP, la TALLA BASE. history = versions read-only (Base, Fit 1…); columna
// activa = "Fit actual". El fitting és un ESTADI de la taula base (DECISIONS.md §2): el treball
// multi-talla viu a Escalat (vegeu `buildEscalatGroups`, més avall, que sí és per talla).
// Mateix patró d'un sol group que CheckMeasureEditor.

import { pieceFittingLines } from '../../api/endpoints'
import { effectiveRegime } from '../../utils/gradingRegime'
import { formatDelta } from '../../utils/format'

// Etiqueta d'una versió: la primera (v1) és Base; les següents són Fit N amb N = version_number - 1.
const versionLabel = (vn, idx, t) =>
  idx === 0 ? t('fitting.grid.base') : t('fitting.grid.fit', { n: vn - 1 })

// Un sol group: la talla base, marcada amb ★ outline. `historyCols` = versions.
// Sense `baseLabel` (model sense base_size_label; avui: cap) no hi ha eix → cap group.
export function buildFittingGroups(baseLabel, versionNumbers, t) {
  if (!baseLabel) return []
  return [{
    key: baseLabel,
    label: <span>{baseLabel}<i className="ti ti-star" style={{ fontSize: 10, marginLeft: 4, color: 'var(--gold)' }} /></span>,
    historyCols: versionNumbers.map((vn, idx) => ({ key: `v${vn}`, label: versionLabel(vn, idx, t) })),
    activeLabel: t('fitting.grid.fit_current'),
    trailCols: [],
  }]
}

// rows = files POM amb nomenclatura 2 línies + règim (per al leadCol) + la cel·la de la talla base.
// cell.history[`v${vn}`] = valor de la versió; cell.active = la cel·la editable "Fit actual"
// (lineId + valor_real + baseValue = Base, per al marcatge vermell difereix-de-base).
// Sense pomRows (font no carregada / resposta incompleta) → cap fila, no una excepció: la graella
// té un estat buit i és el que ha de sortir. Mirall de buildEscalatRows, que ja ho fa des de sempre.
export function buildFittingRows(pomRows, baseLabel, versionNumbers) {
  return (pomRows || []).map(row => {
    const cells = {}
    if (baseLabel) {
      const line = row.cells[baseLabel]
      const evoMap = new Map((line?.evolucio || []).map(e => [e.version_number, e.valor_cm]))
      const history = {}
      for (const vn of versionNumbers) history[`v${vn}`] = evoMap.has(vn) ? evoMap.get(vn) : null
      const baseValue = line?.evolucio?.[0]?.valor_cm ?? null
      cells[baseLabel] = {
        history,
        active: line ? { lineId: line.id, value: line.valor_real ?? '', baseValue } : null,
      }
    }
    return {
      pom_id: row.pom_id, codi: row.codi, is_key: row.is_key,
      // C4/BLOC 3 — clau de fila per a MeasureGrid. Aquí la més forta disponible és el
      // `bm_id`; 🚩 les germanes ja s'han perdut abans (`deriveFitting`/`FittingDetail`
      // agrupen per `pom_id` perquè el payload de línies de fitting no porta els eixos).
      rowKey: row.bm_id || row.pom_id,
      nom_en: row.nom_en, nom_local: row.nom_local,
      nom_fitxa: row.nom_fitxa, bm_id: row.bm_id,   // P4 — autoria de nom a nivell model
      logica: row.logica, increment_base: row.increment_base,
      increment_break: row.increment_break, talla_break_label: row.talla_break_label,
      cells,
    }
  })
}

// Etiqueta compacta de regla (delta · trencament). Còpia local (igual a MeasureTable/CheckMeasureEditor;
// triplicació anotada per a una unificació futura — extreure-la tocaria el check, fora de l'abast P5).
function regleLabel(row, t) {
  if (row.logica == null) return ''
  if (row.logica === 'STEP') return t('fitting.grid.rule_free')
  // LINEAR+0 sense break = FIXED: no té delta a ensenyar (§LLEI a utils/gradingRegime).
  if (effectiveRegime(row) === 'FIXED') return ''
  if (row.increment_base == null) return ''
  if (row.increment_break != null && row.talla_break_label)
    return `+${row.increment_base} · ${t('fitting.grid.break')} ${row.talla_break_label} +${row.increment_break}`
  return `+${row.increment_base}`
}

// leadCol Règim del fitting (sticky): a diferència del check (lectura), aquí el règim és EDITABLE
// (select LINEAR/STEP) perquè d'ell depèn la propagació. Sota, l'etiqueta de regla a 2 línies.
// LINEAR/STEP són valors de DADA (row.logica) → no es tradueixen.
// `compacte` (FIX-4): amaga la llegenda de regla de sota el desplegable. La fa servir Escalat,
// on el delta i el break ja tenen COLUMNA pròpia — repetir-los aquí seria la mateixa dada dues
// vegades, i és precisament la lletra petita el que ningú llegia.
export function regimeLeadCol(t, onRegimChange, readOnly = false, { compacte = false } = {}) {
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
              border: '1px solid var(--border)', borderRadius: 4,
              background: 'var(--white)', color: 'var(--text-main)', boxSizing: 'border-box',
            }}
          >
            {row.logica == null && <option value="">—</option>}
            <option value="LINEAR">LINEAR</option>
            <option value="STEP">STEP</option>
            {regim === 'FIXED' && <option value="FIXED">FIXED</option>}
          </select>
        )}
        {!compacte && regleLabel(row, t) && (
          <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', whiteSpace: 'nowrap', marginTop: 1 }}>
            {regleLabel(row, t)}
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
export function escalatRuleLeadCols(t, onRegimChange, readOnly = false, unit = 'CM') {
  const cap = { fontSize: 'var(--fs-body)', color: 'var(--text-main)', fontVariantNumeric: 'tabular-nums' }
  const buit = { fontSize: 'var(--fs-body)', color: 'var(--text-muted)' }
  // Un règim sense delta (FIXED, o STEP amb valors lliures) no té Δ que ensenyar: guió, no zero.
  const mostraDelta = (row) => effectiveRegime(row) === 'LINEAR'
  return [
    regimeLeadCol(t, onRegimChange, readOnly, { compacte: true }),
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
      // Etiqueta de talla: DADA de domini (XS, 3XL) — no es tradueix ni porta signe.
      render: (row) => (mostraDelta(row) && row.talla_break_label
        ? <span style={{ fontSize: 'var(--fs-body)', color: 'var(--text-main)' }}>{row.talla_break_label}</span>
        : <span style={buit}>—</span>),
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
