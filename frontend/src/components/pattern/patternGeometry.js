/**
 * Helpers geomètrics del visor de patrons. Funcions PURES, sense React ni Konva.
 *
 * Viuen a part perquè el visor només s'hagi de preocupar de dibuixar. Tot el que és
 * "quin és el tram de vora sota el cursor" o "quant fa de llarg" és aritmètica, i
 * l'aritmètica es prova sola.
 *
 * Unitats: el motor serveix MIL·LÍMETRES. La conversió a píxels la fa el visor amb la
 * seva pròpia escala (v. PatternViewer): un patró fa metre i mig i no té res a veure amb
 * la constant MM_TO_PX del TechSheetEditor, que és l'escala d'un A4 a pantalla.
 */

/** Bounding box d'un conjunt de peces (en mm). */
export function bboxDePeces(pieces) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity
  for (const p of pieces) {
    for (const b of p.boundaries || []) {
      for (const q of b.points || []) {
        if (q.x < minX) minX = q.x
        if (q.y < minY) minY = q.y
        if (q.x > maxX) maxX = q.x
        if (q.y > maxY) maxY = q.y
      }
    }
    for (const n of p.notches || []) {
      if (n.x < minX) minX = n.x
      if (n.y < minY) minY = n.y
      if (n.x > maxX) maxX = n.x
      if (n.y > maxY) maxY = n.y
    }
  }
  if (!isFinite(minX)) return { minX: 0, minY: 0, maxX: 100, maxY: 100, ample: 100, alt: 100 }
  return { minX, minY, maxX, maxY, ample: maxX - minX, alt: maxY - minY }
}

/** Escala que fa cabre el bbox dins el viewport, amb un marge. */
export function escalaPerCabre(bbox, ampleViewport, altViewport, marge = 40) {
  const w = Math.max(bbox.ample, 1)
  const h = Math.max(bbox.alt, 1)
  return Math.min((ampleViewport - marge) / w, (altViewport - marge) / h)
}

export function distancia(ax, ay, bx, by) {
  return Math.hypot(bx - ax, by - ay)
}

/**
 * Distància d'un punt al segment AB, i el paràmetre t del peu de la perpendicular.
 * És el nucli del hover: sense això no se sap quin tram de vora hi ha sota el cursor.
 */
export function distanciaASegment(px, py, ax, ay, bx, by) {
  const dx = bx - ax
  const dy = by - ay
  const den = dx * dx + dy * dy
  if (den === 0) return { dist: distancia(px, py, ax, ay), t: 0 }
  let t = ((px - ax) * dx + (py - ay) * dy) / den
  t = Math.max(0, Math.min(1, t))
  const projX = ax + t * dx
  const projY = ay + t * dy
  return { dist: distancia(px, py, projX, projY), t }
}

/**
 * El tram de vora més proper al cursor, entre totes les vores de totes les peces.
 * Torna null si no n'hi ha cap dins de `maxDist` (en mm).
 *
 * Es fa a força bruta: 532 punts són res per a un navegador, i un índex espacial aquí
 * seria complexitat a canvi de cap millora perceptible.
 */
export function tramMesProper(pieces, x, y, maxDist = 12) {
  let millor = null
  for (const piece of pieces) {
    for (const b of piece.boundaries || []) {
      const pts = b.points || []
      const n = pts.length
      if (n < 2) continue
      const total = b.closed ? n : n - 1
      for (let i = 0; i < total; i++) {
        const a = pts[i]
        const c = pts[(i + 1) % n]
        const { dist } = distanciaASegment(x, y, a.x, a.y, c.x, c.y)
        if (dist <= maxDist && (!millor || dist < millor.dist)) {
          millor = {
            dist,
            peca: piece.nom_block,
            role: b.role,
            longitud: distancia(a.x, a.y, c.x, c.y),
            indexTram: i,
          }
        }
      }
    }
  }
  return millor
}

/** Longitud total d'una vora (perímetre si és tancada), en mm. */
export function longitudVora(boundary) {
  const pts = boundary.points || []
  const n = pts.length
  if (n < 2) return 0
  let total = 0
  const trams = boundary.closed ? n : n - 1
  for (let i = 0; i < trams; i++) {
    const a = pts[i]
    const b = pts[(i + 1) % n]
    total += distancia(a.x, a.y, b.x, b.y)
  }
  return total
}

/** Punts d'una vora aplanats per a Konva: [x0,y0,x1,y1,…] amb l'eix Y capgirat. */
export function puntsPerKonva(boundary) {
  const flat = []
  for (const p of boundary.points || []) {
    flat.push(p.x, -p.y)   // el DXF creix cap amunt; el canvas, cap avall
  }
  return flat
}

/**
 * El punt de la geometria més proper al cursor (l'imant del mode d'anotació).
 *
 * Marcar un POM "a ull", entre dos vèrtexs, no seria una mesura del patró: seria un
 * dibuix a sobre del patró. Per això el cursor s'imanta i, si no hi ha cap punt a prop,
 * no s'ancora res.
 */
export function puntMesProper(pieces, x, y, maxDist = 14) {
  let millor = null
  for (const piece of pieces) {
    for (const b of piece.boundaries || []) {
      for (const p of b.points || []) {
        const d = distancia(x, y, p.x, p.y)
        if (d <= maxDist && (!millor || d < millor.dist)) {
          millor = { dist: d, punt: p, peca: piece.nom_block, pieceId: piece.id }
        }
      }
    }
  }
  return millor
}

/**
 * Els punts d'un segment, per dibuixar-lo ressaltat.
 *
 * El segment es guarda en coordenades PARAMÈTRIQUES (t_inici–t_fi sobre la longitud de
 * la vora), no en índexs de vèrtex: així continua sent el mateix tram encara que la
 * geometria es mogui. Aquí es tradueix a punts per pintar-lo.
 */
export function puntsDelSegment(piece, segment) {
  const b = (piece.boundaries || [])[segment.vora]
  if (!b) return []
  const pts = b.points || []
  const n = pts.length
  if (n < 2) return []

  const trams = b.closed ? n : n - 1
  const llargs = []
  let total = 0
  for (let i = 0; i < trams; i++) {
    const a = pts[i], c = pts[(i + 1) % n]
    const d = distancia(a.x, a.y, c.x, c.y)
    llargs.push(d)
    total += d
  }
  if (total === 0) return []

  const out = []
  let acumulat = 0
  for (let i = 0; i < trams; i++) {
    const t0 = acumulat / total
    const t1 = (acumulat + llargs[i]) / total
    // Un tram entra si se solapa amb [t_inici, t_fi] del segment.
    if (t1 > segment.t_inici - 1e-9 && t0 < segment.t_fi + 1e-9) {
      if (!out.length) out.push(pts[i])
      out.push(pts[(i + 1) % n])
    }
    acumulat += llargs[i]
  }
  return out
}

/** Quines capes té de debò aquest patró (per no oferir toggles buits). */
export function capesPresents(pieces) {
  const capes = new Set()
  for (const p of pieces) {
    for (const b of p.boundaries || []) capes.add(b.role)
    if ((p.notches || []).length) capes.add('notch')
    if (p.grain) capes.add('grain')
  }
  return capes
}
