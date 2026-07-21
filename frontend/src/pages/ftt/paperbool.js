// S8 · Pont JSON (objectes de l'editor) <-> Paper.js, per a les operacions
// booleanes del pathfinder (unir/restar/intersecar/excloure). Mòdul pur,
// sense React/JSX i sense dependència dura de TechSheetEditor (per evitar
// cicles d'importació, `makeId` i `style` s'accepten com a paràmetres).

import paper from 'paper'
// X2 — el buscatraços no s'inventa cap color: `style` ja arriba RESOLT del contracte de
// pintura, i si allà no hi havia color aquí tampoc n'hi ha d'haver.
import { TRAC_PER_DEFECTE } from './paint'

/**
 * Executa `fn(scope)` dins d'un PaperScope offscreen (sense adjuntar-lo al
 * DOM) i neteja el projecte en acabar, per no deixar ítems residuals.
 */
export function withPaperScope(fn) {
  const scope = new paper.PaperScope()
  scope.setup(document.createElement('canvas'))
  try {
    return fn(scope)
  } finally {
    if (scope.project && scope.project.remove) {
      scope.project.remove()
    } else if (scope.project && scope.project.clear) {
      scope.project.clear()
    }
  }
}

function segsToPaperPath(segments, closed, scope) {
  const p = new scope.Path()
  ;(segments || []).forEach(s => {
    p.add(new scope.Segment(
      new scope.Point(s.x, s.y),
      new scope.Point(s.inX || 0, s.inY || 0),
      new scope.Point(s.outX || 0, s.outY || 0),
    ))
  })
  p.closed = !!closed
  return p
}

function entryToPaper(entry, scope) {
  if (entry.subpaths) {
    const cp = new scope.CompoundPath({})
    entry.subpaths.forEach(sp => cp.addChild(segsToPaperPath(sp.segments, sp.closed, scope)))
    return cp
  }
  return segsToPaperPath(entry.segments, entry.closed, scope)
}

/**
 * Converteix un objecte de l'editor (rect/rect_round/ellipse/path) en un
 * Path o CompoundPath de Paper.js, en espai mm. Retorna null si el tipus
 * és desconegut.
 */
export function objectToPaperPath(obj, scope) {
  if (!obj) return null

  if (obj.type === 'rect' || obj.type === 'rect_round') {
    const origin = new scope.Point(obj.x, obj.y)
    const r = new scope.Path.Rectangle({
      point: [obj.x, obj.y],
      size: [obj.width || 1, obj.height || 1],
      radius: obj.type === 'rect_round' ? (obj.cornerRadius || 0) : 0,
    })
    if (obj.rotation) r.rotate(obj.rotation, origin)
    if ((obj.scaleX && obj.scaleX !== 1) || (obj.scaleY && obj.scaleY !== 1)) {
      r.scale(obj.scaleX || 1, obj.scaleY || 1, origin)
    }
    return r
  }

  if (obj.type === 'ellipse') {
    const origin = new scope.Point(obj.x, obj.y)
    const e = new scope.Path.Ellipse({
      center: [obj.x, obj.y],
      radius: [obj.rx || 1, obj.ry || 1],
    })
    if (obj.rotation) e.rotate(obj.rotation, origin)
    if ((obj.scaleX && obj.scaleX !== 1) || (obj.scaleY && obj.scaleY !== 1)) {
      e.scale(obj.scaleX || 1, obj.scaleY || 1, origin)
    }
    return e
  }

  if (obj.type === 'path') {
    const paths = obj.paths || []
    if (!paths.length) return null
    const item = paths.length === 1
      ? entryToPaper(paths[0], scope)
      : new scope.CompoundPath({ children: paths.map(entry => entryToPaper(entry, scope)) })

    if (obj.x || obj.y) item.translate(new scope.Point(obj.x || 0, obj.y || 0))
    const origin = new scope.Point(obj.x || 0, obj.y || 0)
    if (obj.rotation) item.rotate(obj.rotation, origin)
    if ((obj.scaleX && obj.scaleX !== 1) || (obj.scaleY && obj.scaleY !== 1)) {
      item.scale(obj.scaleX || 1, obj.scaleY || 1, origin)
    }
    return item
  }

  return null
}

function segsOf(paperPath) {
  return paperPath.segments.map(seg => ({
    x: seg.point.x,
    y: seg.point.y,
    inX: seg.handleIn.x,
    inY: seg.handleIn.y,
    outX: seg.handleOut.x,
    outY: seg.handleOut.y,
  }))
}

/**
 * Converteix un Path/CompoundPath de Paper.js resultant d'una operació
 * booleana en un NOU objecte 'path' de l'editor (model S6: subpaths per a
 * compostos, segments per a simples).
 */
export function paperPathToPathObject(item, style, makeId) {
  let entry
  if (item.className === 'CompoundPath') {
    entry = {
      fill: style?.fill ?? null,
      fillRule: 'evenodd',
      stroke: style?.stroke ?? null,
      strokeWidth: style?.strokeWidth ?? TRAC_PER_DEFECTE,
      subpaths: item.children
        .filter(c => c.className === 'Path' && c.segments?.length)
        .map(c => ({ closed: !!c.closed, segments: segsOf(c) })),
    }
  } else {
    entry = {
      closed: !!item.closed,
      fill: style?.fill ?? null,
      fillRule: 'nonzero',
      stroke: style?.stroke ?? null,
      strokeWidth: style?.strokeWidth ?? TRAC_PER_DEFECTE,
      segments: segsOf(item),
    }
  }

  return {
    id: makeId ? makeId() : (crypto.randomUUID ? crypto.randomUUID() : String(Math.random())),
    type: 'path',
    layer: 'free',
    x: 0,
    y: 0,
    paths: [entry],
  }
}

/**
 * Orquestrador cridat per la comanda 2 (pathfinder): aplica `op` en cadena
 * sobre `objects` (ja convertits) i retorna un únic objecte 'path' nou, o
 * null si no hi ha prou objectes o l'operació no produeix resultat.
 * `op` ∈ {'unite', 'subtract', 'intersect', 'exclude'}.
 * Nota: per a 'subtract', `objects` s'ha de passar ordenat de baix a dalt
 * (bottom.subtract(top)); l'ordenació per z és responsabilitat del cridador.
 */
export function booleanOp(objects, op, style, makeId) {
  return withPaperScope(scope => {
    const items = (objects || []).map(o => objectToPaperPath(o, scope)).filter(Boolean)
    if (items.length < 2) return null
    let result = items[0]
    for (let i = 1; i < items.length; i++) {
      result = result[op](items[i])
    }
    if (!result) return null
    // Llegim els segments (paperPathToPathObject) ABANS de sortir de
    // withPaperScope, mentre el projecte encara existeix.
    return paperPathToPathObject(result, style, makeId)
  })
}
