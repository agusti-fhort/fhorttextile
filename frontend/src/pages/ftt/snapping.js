// S2 commit 1 — mòdul pur de magnetisme (snapping) per al DRAG d'objectes lliures.
// Sense React/JSX: candidates = vores/centres d'altres objectes + marges/centre de pàgina
// + guies; computeSnap tria l'ancoratge més proper dins el llindar i retorna la correcció.

export const SNAP_PX = 8   // llindar de magnetisme en px de pantalla

// rectsMm: [{x,y,w,h}] bboxes (mm) dels ALTRES objectes. guides: [{axis:'x'|'y', pos}].
// Retorna línies candidates: xs = posicions x (verticals), ys = posicions y (horitzontals), en mm.
export function buildCandidates({ rectsMm, pageWmm, pageHmm, guides }) {
  const xs = [0, pageWmm / 2, pageWmm]
  const ys = [0, pageHmm / 2, pageHmm]
  for (const r of rectsMm) { xs.push(r.x, r.x + r.w / 2, r.x + r.w); ys.push(r.y, r.y + r.h / 2, r.y + r.h) }
  for (const g of (guides || [])) { if (g.axis === 'x') xs.push(g.pos); else if (g.axis === 'y') ys.push(g.pos) }
  return { xs, ys }
}

// draggedRectMm: {x,y,w,h} actual de l'objecte arrossegat. thresholdMm: llindar en mm.
// Retorna {dx,dy,lineX,lineY}: dx/dy = correcció en mm perquè encaixi; lineX/lineY = mm de la
// guia a pintar (o null). Es tria l'ancoratge (vora/centre) més proper dins el llindar.
export function computeSnap(draggedRectMm, candidates, thresholdMm) {
  const ax = [draggedRectMm.x, draggedRectMm.x + draggedRectMm.w / 2, draggedRectMm.x + draggedRectMm.w]
  const ay = [draggedRectMm.y, draggedRectMm.y + draggedRectMm.h / 2, draggedRectMm.y + draggedRectMm.h]
  let dx = 0, lineX = null, bestX = Infinity
  for (const a of ax) for (const c of candidates.xs) { const d = c - a; if (Math.abs(d) <= thresholdMm && Math.abs(d) < bestX) { bestX = Math.abs(d); dx = d; lineX = c } }
  let dy = 0, lineY = null, bestY = Infinity
  for (const a of ay) for (const c of candidates.ys) { const d = c - a; if (Math.abs(d) <= thresholdMm && Math.abs(d) < bestY) { bestY = Math.abs(d); dy = d; lineY = c } }
  return { dx, dy, lineX, lineY }
}
