// Adapter de l'eix FITTING (talles × versions) cap al contracte de MeasureGrid (editor únic).
// Reusa l'esquelet de MeasureGrid; aquí NOMÉS es projecta la dada del fitting als seus `groups`/`rows`.
// Cap motor tocat: la propagació/STEP es despatxa per l'API existent (makeFittingOnSave).
//
// Eix: un GROUP per talla; history = versions read-only (Base, Fit 1…); columna activa = "Fit actual".

import { pieceFittingLines } from '../../api/endpoints'

// Etiqueta d'una versió: la primera (v1) és Base; les següents són Fit N amb N = version_number - 1.
const versionLabel = (vn, idx, t) =>
  idx === 0 ? t('fitting.grid.base') : t('fitting.grid.fit', { n: vn - 1 })

// groups = una talla per group; historyCols = versions; activeLabel = "Fit actual". La talla base es
// marca amb ★ outline a l'etiqueta del group (color només-activa: el fons daurat el porta l'activa).
export function buildFittingGroups(sizeLabels, baseLabel, versionNumbers, t) {
  return sizeLabels.map(s => ({
    key: s,
    label: s === baseLabel
      ? <span>{s}<i className="ti ti-star" style={{ fontSize: 10, marginLeft: 4, color: 'var(--gold)' }} /></span>
      : s,
    historyCols: versionNumbers.map((vn, idx) => ({ key: `v${vn}`, label: versionLabel(vn, idx, t) })),
    activeLabel: t('fitting.grid.fit_current'),
    trailCols: [],
  }))
}

// rows = files POM amb nomenclatura 2 línies + règim (per al leadCol) + cells per talla.
// cell.history[`v${vn}`] = valor de la versió; cell.active = la cel·la editable "Fit actual"
// (lineId + valor_real + baseValue = Base d'aquella talla, per al marcatge vermell difereix-de-base).
export function buildFittingRows(pomRows, sizeLabels, versionNumbers) {
  return pomRows.map(row => {
    const cells = {}
    for (const s of sizeLabels) {
      const line = row.cells[s]
      const evoMap = new Map((line?.evolucio || []).map(e => [e.version_number, e.valor_cm]))
      const history = {}
      for (const vn of versionNumbers) history[`v${vn}`] = evoMap.has(vn) ? evoMap.get(vn) : null
      const baseValue = line?.evolucio?.[0]?.valor_cm ?? null
      cells[s] = {
        history,
        active: line ? { lineId: line.id, value: line.valor_real ?? '', baseValue } : null,
      }
    }
    return {
      pom_id: row.pom_id, codi: row.codi, is_key: row.is_key,
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
  if (row.increment_base == null) return ''
  if (row.increment_break != null && row.talla_break_label)
    return `+${row.increment_base} · ${t('fitting.grid.break')} ${row.talla_break_label} +${row.increment_break}`
  return `+${row.increment_base}`
}

// leadCol Règim del fitting (sticky): a diferència del check (lectura), aquí el règim és EDITABLE
// (select LINEAR/STEP) perquè d'ell depèn la propagació. Sota, l'etiqueta de regla a 2 línies.
// LINEAR/STEP són valors de DADA (row.logica) → no es tradueixen.
export function regimeLeadCol(t, onRegimChange, readOnly = false) {
  return {
    key: 'regim', label: t('fitting.grid.regime'), width: 118,
    render: (row) => (
      <div>
        {readOnly ? (
          <div style={{ fontSize: 'var(--fs-label)', color: 'var(--text-main)' }}>{row.logica ?? '—'}</div>
        ) : (
          <select
            value={row.logica ?? ''}
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
          </select>
        )}
        {regleLabel(row, t) && (
          <div style={{ fontSize: 'var(--fs-caption)', color: 'var(--text-muted)', whiteSpace: 'nowrap', marginTop: 1 }}>
            {regleLabel(row, t)}
          </div>
        )}
      </div>
    ),
  }
}

// --- ESCALAT (taula propagada del model) ---------------------------------------------------------
// LLEI: propagar = llenç net, NO eix de versions per comparar. Per talla: 1 columna read-only "Base"
// (valor vigent propagat) + columna activa "Fit actual" EDITABLE per a TOTES les talles, BASE inclosa
// (el fitting no la bloqueja). Editar una talla propaga per regla (onSave → escalat/ajustar-talla).
// Reusa regimeLeadCol. lineId = `${pom_id}:${size}`. S'alimenta de taula-mesures (versió vigent).
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
        active: { lineId: `${row.pom_id}:${s}`, value: v == null ? '' : v, baseValue: v },
      }
    }
    return {
      pom_id: row.pom_id, codi: row.pom_code, is_key: row.is_key,
      nom_en: row.nom_en, nom_local: row.nom_ca,
      logica: row.logica, increment_base: row.increment_base,
      increment_break: row.increment_break, talla_break_label: row.talla_break_label,
      cells,
    }
  })
}

// onSave de MeasureGrid per al fitting: despatxa per règim del POM (lineRegimeMap: lineId → 'LINEAR'|'STEP').
// STEP → PATCH valor_real (no propaga). LINEAR → propagar (retorna {linies} → MeasureGrid refresca germanes).
// Motor INTACTE: només es criden els endpoints d'autosave/propagació existents.
export function makeFittingOnSave(lineRegimeMap) {
  return (lineId, value) => {
    const regime = lineRegimeMap.get(lineId)
    if (regime === 'STEP') return pieceFittingLines.update(lineId, { valor_real: value })
    return pieceFittingLines.propagar(lineId, value)
  }
}
