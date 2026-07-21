// Operacions vectorials PURES de node i topologia sobre el model de l'editor (segments en mm),
// separades de tota UI/JSX perquè siguin reutilitzables tant pel sub-editor PaperFlatEditor (Camí A)
// com per una futura capa in-place a Konva (Camí B). Les que necessiten geometria bezier (afegir node,
// tisores, suavitzar) deleguen a Paper.js dins `withPaperScope` (offscreen); la resta són manipulació
// pura d'arrays. Format de segment: {x,y,inX,inY,outX,outY} (mm; handles relatius al node).
import { withPaperScope } from './paperbool'

// ── Conversió model ⇄ Paper (dins un scope) ─────────────────────────────────────────────
function segsToPath(segments, closed, scope) {
  const p = new scope.Path()
  ;(segments || []).forEach(s => p.add(new scope.Segment(
    new scope.Point(s.x, s.y),
    new scope.Point(s.inX || 0, s.inY || 0),
    new scope.Point(s.outX || 0, s.outY || 0),
  )))
  p.closed = !!closed
  return p
}
function segsOf(p) {
  return p.segments.map(seg => ({
    x: seg.point.x, y: seg.point.y,
    inX: seg.handleIn.x, inY: seg.handleIn.y,
    outX: seg.handleOut.x, outY: seg.handleOut.y,
  }))
}
const clone = (s) => ({ x: s.x, y: s.y, inX: s.inX || 0, inY: s.inY || 0, outX: s.outX || 0, outY: s.outY || 0 })

// ── NODE OPS ─────────────────────────────────────────────────────────────────────────────

// Treu un node; la corba es reconnecta amb els handles dels veïns (splice pur — cap geometria nova).
// Retorna {segments, closed}. Si en quedarien <2, retorna null (el path desapareixeria: el decideix el caller).
export function removeNode(segments, closed, index) {
  const segs = (segments || []).map(clone)
  if (index < 0 || index >= segs.length) return { segments: segs, closed: !!closed }
  segs.splice(index, 1)
  if (segs.length < 2) return null
  return { segments: segs, closed: !!closed }
}

// Converteix un node a CANTONADA (esborra les dues nanses → vèrtex angular). Pur.
export function toCorner(segments, index) {
  const segs = (segments || []).map(clone)
  const s = segs[index]
  if (s) { s.inX = 0; s.inY = 0; s.outX = 0; s.outY = 0 }
  return { segments: segs }
}

// Converteix un node a SUAU (nanses tangents equilibrades a partir dels veïns, via Paper.smooth). Bezier.
export function toSmooth(segments, closed, index) {
  return withPaperScope(scope => {
    const p = segsToPath(segments, closed, scope)
    const seg = p.segments[index]
    if (seg) seg.smooth()
    return { segments: segsOf(p) }
  })
}

// Afegeix un node sobre una corba concreta (curveIndex) al paràmetre time∈(0,1). Bezier (divideAtTime).
// Retorna {segments, closed, index} on index = posició del node nou (per seleccionar-lo).
export function addNodeAt(segments, closed, curveIndex, time = 0.5) {
  return withPaperScope(scope => {
    const p = segsToPath(segments, closed, scope)
    const curve = p.curves[curveIndex]
    if (!curve) return { segments: segsOf(p), closed: !!closed, index: null }
    curve.divideAtTime(time)
    return { segments: segsOf(p), closed: p.closed, index: curveIndex + 1 }
  })
}

// Nansa simètrica: donat el vector d'una nansa, retorna el de l'oposada (reflexió per l'origen del node).
// Pur i trivial; l'usa el drag de nanses en mode suau (per defecte); Alt el salta (independents).
export function mirrorHandle(vx, vy) { return { x: -(vx || 0), y: -(vy || 0) } }

// ── FORMA (subpath sencer) com a entitat de primera classe (G2) ────────────────────────────

// TRANSLADA un subpath sencer (tots els nodes) per (dx,dy). Les nanses són relatives al node → no
// canvien. Pur; l'usa el nudge i el moviment de forma en mode fletxa negra. Retorna {segments}.
export function translateSubpath(segments, dx, dy) {
  const segs = (segments || []).map(clone)
  segs.forEach(s => { s.x += dx; s.y += dy })
  return { segments: segs }
}

// MIRALL d'un subpath sobre el seu centre (cx,cy). axis 'h' = reflexió horitzontal (x); 'v' = vertical (y).
// Reflecteix el punt i el component corresponent de les nanses (relatives). Cas d'ús: simetria de peces.
export function mirrorSubpath(segments, axis, cx, cy) {
  const segs = (segments || []).map(clone)
  segs.forEach(s => {
    if (axis === 'v') { s.y = 2 * cy - s.y; s.inY = -s.inY; s.outY = -s.outY }
    else { s.x = 2 * cx - s.x; s.inX = -s.inX; s.outX = -s.outX }
  })
  return { segments: segs }
}

// ESCALA un subpath per (fx,fy) respecte del centre (cx,cy). Escala punts i nanses (relatives). Pur.
export function scaleSubpath(segments, fx, fy, cx, cy) {
  const segs = (segments || []).map(clone)
  segs.forEach(s => {
    s.x = cx + (s.x - cx) * fx; s.y = cy + (s.y - cy) * fy
    s.inX *= fx; s.inY *= fy; s.outX *= fx; s.outY *= fy
  })
  return { segments: segs }
}

// ROTA un subpath `deg` graus respecte del centre (cx,cy). Rota punts i nanses (vectors). Pur.
export function rotateSubpath(segments, deg, cx, cy) {
  const a = (deg || 0) * Math.PI / 180, cos = Math.cos(a), sin = Math.sin(a)
  const rot = (x, y) => ({ x: x * cos - y * sin, y: x * sin + y * cos })
  const segs = (segments || []).map(clone)
  segs.forEach(s => {
    const p = rot(s.x - cx, s.y - cy); s.x = cx + p.x; s.y = cy + p.y
    const hi = rot(s.inX, s.inY); s.inX = hi.x; s.inY = hi.y
    const ho = rot(s.outX, s.outY); s.outX = ho.x; s.outY = ho.y
  })
  return { segments: segs }
}

// BOOLEANES entre subpaths (G3 · buscatraços dins el path compost). `subpaths` = [{segments,closed}]
// en ordre de z (baix→dalt); `op` ∈ {unite,subtract,intersect,exclude}. Encadena l'operació (subtract:
// la forma inferior resta les superiors — mateix criteri que el buscatraços d'objecte). Retorna
// [{segments,closed}, …] (el resultat pot ser un compost amb diversos subpaths) o null si no aplica.
export function booleanSubpaths(subpaths, op) {
  return withPaperScope(scope => {
    const paths = (subpaths || []).map(sp => segsToPath(sp.segments, sp.closed, scope))
    if (paths.length < 2) return null
    let result = paths[0]
    for (let i = 1; i < paths.length; i++) result = result[op](paths[i])
    if (!result) return null
    const items = result.className === 'CompoundPath'
      ? result.children.filter(c => c.className === 'Path' && c.segments?.length)
      : (result.segments?.length ? [result] : [])
    return items.map(p => ({ segments: segsOf(p), closed: p.closed }))
  })
}

// ── TOPOLOGIA ──────────────────────────────────────────────────────────────────────────────

// Tanca un subpath (uneix primer↔últim). Pur: només marca closed=true (Paper dibuixa la unió).
export function closeSegments(segments) {
  return { segments: (segments || []).map(clone), closed: true }
}

// Obre un path TANCAT tallant per un node: el node es desdobla en dos extrems coincidents i el llaç s'obre.
// Retorna {segments, closed:false}. Si ja era obert, no-op (per obrir un obert cal SEPARAR, no obrir).
export function openAtNode(segments, closed, index) {
  const segs = (segments || []).map(clone)
  if (!closed || index < 0 || index >= segs.length) return { segments: segs, closed: !!closed }
  const rotated = segs.slice(index).concat(segs.slice(0, index))
  rotated.push(clone(rotated[0]))   // extrem final coincident amb el node de tall
  return { segments: rotated, closed: false }
}

// Separa un path en DOS per un node. Obert i node interior → dos oberts que comparteixen el node.
// Tancat → equival a obrir pel node (una sola peça). Retorna [{segments,closed}, ...] (1 o 2 peces).
export function splitAtNode(segments, closed, index) {
  const segs = (segments || []).map(clone)
  if (closed) return [openAtNode(segs, true, index)]
  if (index <= 0 || index >= segs.length - 1) return [{ segments: segs, closed: false }]
  const a = segs.slice(0, index + 1)
  const b = segs.slice(index)
  return [{ segments: a, closed: false }, { segments: b, closed: false }]
}

// ── SEGMENT (tram entre dos nodes) com a entitat de primera classe (F2) ────────────────────

// El segment `curveIndex` és recte si els dos handles que el defineixen (out del node i, in del
// node següent) són nuls. Determina si MOURE'l tradueix (recte) o deforma (corb).
export function isStraightSegment(segments, closed, curveIndex) {
  const n = (segments || []).length
  const i = curveIndex
  const j = closed ? (i + 1) % n : i + 1
  const a = segments[i], b = segments[j]
  if (!a || !b) return true
  return (a.outX || 0) === 0 && (a.outY || 0) === 0 && (b.inX || 0) === 0 && (b.inY || 0) === 0
}

// MOURE un segment (gest Illustrator): recte → translada els dos nodes extrems; corb → desplaça
// proporcionalment les nanses dels dos extrems (out del node i, in del node següent). Pur.
export function moveSegment(segments, closed, curveIndex, dx, dy) {
  const segs = (segments || []).map(clone)
  const n = segs.length
  const i = curveIndex
  const j = closed ? (i + 1) % n : i + 1
  const a = segs[i], b = segs[j]
  if (!a || !b || j >= n) return { segments: segs }
  if (isStraightSegment(segs, closed, curveIndex)) {
    a.x += dx; a.y += dy; b.x += dx; b.y += dy
  } else {
    a.outX = (a.outX || 0) + dx; a.outY = (a.outY || 0) + dy
    b.inX = (b.inX || 0) + dx; b.inY = (b.inY || 0) + dy
  }
  return { segments: segs }
}

// ESBORRAR un segment = OBRIR el path per allà. Tancat → una peça oberta (reordenada perquè el tall
// quedi als extrems). Obert → dues peces (es treu la corba i→i+1). Retorna [{segments,closed}, ...].
export function deleteSegment(segments, closed, curveIndex) {
  const segs = (segments || []).map(clone)
  const n = segs.length
  const i = curveIndex
  if (i < 0 || i >= n) return [{ segments: segs, closed: !!closed }]
  if (closed) {
    const j = (i + 1) % n
    return [{ segments: segs.slice(j).concat(segs.slice(0, j)), closed: false }]
  }
  if (i >= n - 1) return [{ segments: segs, closed: false }]
  return [{ segments: segs.slice(0, i + 1), closed: false }, { segments: segs.slice(i + 1), closed: false }]
}

// TISORES: talla per un punt ARBITRARI (curveIndex + time), no per node. Bezier (splitAt de Paper).
// Obert → dues peces obertes. Tancat → una peça oberta pel tall. Retorna [{segments,closed}, ...].
export function splitAtLocation(segments, closed, curveIndex, time) {
  return withPaperScope(scope => {
    const p = segsToPath(segments, closed, scope)
    const curve = p.curves[curveIndex]
    if (!curve) return [{ segments: segsOf(p), closed: p.closed }]
    const loc = curve.getLocationAtTime(time)
    const other = p.splitAt(loc)
    const out = [{ segments: segsOf(p), closed: p.closed }]
    if (other && other !== p) out.push({ segments: segsOf(other), closed: other.closed })
    return out
  })
}
