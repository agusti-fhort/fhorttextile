// Adapter de l'eix FITTING (talles × versions) cap al contracte de MeasureGrid (editor únic).
// Reusa l'esquelet de MeasureGrid; aquí NOMÉS es projecta la dada del fitting als seus `groups`/`rows`.
// Cap motor tocat: la propagació/STEP es despatxa per l'API existent (P5c, makeFittingOnSave).
//
// Eix: un GROUP per talla; history = versions read-only (Base, Fit 1…); columna activa = "Fit actual".

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
      logica: row.logica, increment_base: row.increment_base,
      increment_break: row.increment_break, talla_break_label: row.talla_break_label,
      cells,
    }
  })
}
