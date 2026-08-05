// Sprint Y — FONTS de la superfície Mesures (CheckMeasureEditor).
// Una "font" encapsula els 4 seams que censava la diagnosi de dissolució (Y7-5): load ·
// buildGroups/buildRows · onSave · buildLeadCols. El component orquestra sempre via la font,
// sense cap `if (mode)` escampat: el camí del check és la font per defecte (viu al propi
// CheckMeasureEditor per reusar-ne els sub-components); el camí del fitting és `fittingSource`,
// aquí. L'eix base únic ja el fa `fittingGridAdapter` (P1b); el règim va read-only en mode
// sessió (lockRules) reusant el 3r argument de `regimeLeadCol`.

import { pieceFittings, fittingSessions, baseMeasurements } from '../../api/endpoints'
import { buildFittingGroups, buildFittingRows, makeFittingOnSave, regimeLeadCol } from './fittingGridAdapter'
import { identitatMesura } from '../../utils/identitatMesura'

// Deriva pomRows + versionNumbers + baseLabel d'un `grid` (pieceFittings.get). Còpia fidel de la
// projecció que feia FittingDetail (base única; l'eix multi-talla viu a Escalat).
function deriveFitting(grid) {
  const lines = grid?.lines || []
  const model = grid?.model || {}
  const baseLabel = (model.base_size_label || '').trim()
  const pomMap = new Map()
  for (const l of lines) {
    // C4/BLOC 1-BIS — s'agrupa per la MESURA, no pel POM: dues germanes són dues files.
    const ident = identitatMesura(l)
    if (!pomMap.has(ident)) pomMap.set(ident, {
      pom_id: l.pom_id, capa: l.capa, instancia: l.instancia,
      codi: l.codi, nom: l.nom, is_key: l.is_key,
      nom_en: l.nom_en, nom_local: l.nom_local, nom_fitxa: l.nom_fitxa, bm_id: l.bm_id,
      // F2 · l'ORIGEN de la mesura base d'aquesta germana. 'DERIVAT' = el sistema l'ha moguda
      // perquè s'ha corregit la seva germana. El serializer l'emet des de C4/F2.
      origen: l.origen,
      logica: l.logica, increment_base: l.increment_base,
      increment_break: l.increment_break, talla_break_label: l.talla_break_label,
      cells: {},
    })
    pomMap.get(ident).cells[l.size_label] = l
  }
  const versionNumbers = [...new Set(
    lines.flatMap(l => (l.evolucio || []).map(e => e.version_number))
  )].sort((a, b) => a - b)
  return { lines, model, baseLabel, pomRows: [...pomMap.values()], versionNumbers }
}

// Resol la PieceFitting d'aquesta sessió per al model. Materialització EN OBRIR (decisió 6): si la
// sessió encara no té peça, la crea (create-piece és idempotent des de XD: 409 si ja existeix).
async function resolvePieceFitting(model, fittingSession) {
  const existing = (fittingSession?.piece_fittings || []).find(p => p.model === model.id || p.model_id === model.id)
    || (fittingSession?.piece_fittings || [])[0]
  if (existing) return existing.id
  try {
    const res = await fittingSessions.createPiece(fittingSession.id, model.id)
    return res.data.id
  } catch (e) {
    // XD — 409 piece_exists: una altra càrrega ja l'ha creada. Rellegim la sessió i agafem la peça.
    if (e?.response?.status === 409) {
      const s = await fittingSessions.get(fittingSession.id)
      const pf = (s.data?.piece_fittings || []).find(p => p.model === model.id || p.model_id === model.id)
        || (s.data?.piece_fittings || [])[0]
      if (pf) return pf.id
    }
    throw e
  }
}

export const fittingSource = {
  kind: 'fitting',
  supportsResolve: false,   // el gravar-i-resoldre del fitting viu a Y5, no aquí

  // Carrega el grid de la peça (resolent-la/materialitzant-la si cal). ctx.fittingSession obligatori.
  async load(model, ctx) {
    const pieceFittingId = await resolvePieceFitting(model, ctx.fittingSession)
    const res = await pieceFittings.get(pieceFittingId)
    return { pieceFittingId, grid: res.data, ...deriveFitting(res.data) }
  },

  // C5-UI/P4 — EL BLOC DE DECISIÓ I L'HISTÒRIC PAGINAT viuen NOMÉS en aquesta font: el fitting és
  // on es pren la mesura i es decideix què se'n fa. El check té la seva pròpia cel·la de
  // decisió·nota (una altra semàntica: acceptar o descartar una PRESA), i Escalat no decideix res.
  //
  // EL VEREDICTE ES DESA, i el camí és el MATEIX que el de la nota: PATCH per línia sobre
  // `piece-fitting-lines/<id>/`. `PieceFittingLine.decisio` existeix des de `fd102c06` (D-31.21)
  // amb els tres choices i `''` = sense decidir —que NO és ACCEPTED—, el serializer de cel·la
  // l'accepta a l'escriptura i l'emet a la lectura, i `views.py` guarda que un REJECTED no sembri
  // res. El serializer de la graella també l'emet a `line.decisio` a cada lectura.
  //
  // El front l'escriu des de C1: `buildFittingRows` el sembra de `line.decisio` i `onVeredicte`
  // en fa PATCH per la mateixa porta que la nota.
  //
  // (Aquí hi va haver un «🚨 PENDENT DE BACKEND — no té camp `decisio`». Era cert abans de
  // `fd102c06` i va sobreviure al commit que el va desmentir: qui llegia el fitxer en concloïa
  // que calia una migració que ja existia, i per això el veredicte es va perdre durant dies.)
  buildGroups(raw, ctx) {
    return buildFittingGroups(raw.baseLabel, raw.versionNumbers, ctx.t, {
      hist: ctx.hist || null,
      decisio: !!ctx.decisio,
    })
  },

  buildRows(raw, ctx) {
    return buildFittingRows(raw.pomRows, raw.baseLabel, raw.versionNumbers, { decisio: ctx.decisio })
  },

  // onSave despatxa per règim (STEP desa; LINEAR propaga), com el fitting històric. Només les línies
  // de la base són editables (guard de vista al backend).
  makeOnSave(raw) {
    const lineRegimeMap = new Map(
      raw.lines.filter(l => l.size_label === raw.baseLabel).map(l => [l.id, l.logica]))
    return makeFittingOnSave(lineRegimeMap)
  },

  // Nomenclatura per model (nom_fitxa de BaseMeasurement). Amb lockRules el component el passa undefined.
  onNomSave(bmId, value) {
    return baseMeasurements.update(bmId, { nom_fitxa: value || null })
  },

  // Règim a la capçalera de fila. En mode sessió (lockRules) va READ-ONLY (3r arg true): els deltes
  // s'editen a Escalat, no en presa. regimeLeadCol ja gestiona la branca de lectura.
  buildLeadCols(raw, ctx) {
    return [regimeLeadCol(ctx.t, () => {}, true)]
  },
}
