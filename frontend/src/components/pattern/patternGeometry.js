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

/**
 * El PEU de la perpendicular de `p` sobre la recta que passa per `a` i `b`.
 *
 * El mateix càlcul que `engine/measure._ortogonal` fa al servidor, i aquí per la mateixa raó
 * que la resta d'aquest fitxer existeix: el canvas ha de poder DIBUIXAR el que el servidor
 * MESURA sense una anada i tornada per cada moviment del cursor. La xifra que val segueix
 * sent la del servidor —aquí no se'n desa cap—; això només diu on va la línia.
 *
 * Torna `null` si les dues referències són el mateix punt: sense recta no hi ha
 * perpendicular, exactament el mateix límit que el motor.
 */
export function peuPerpendicular(a, b, p) {
  if (!a || !b || !p) return null
  const vx = b.x - a.x
  const vy = b.y - a.y
  const base2 = vx * vx + vy * vy
  if (base2 <= 1e-12) return null
  const t = ((p.x - a.x) * vx + (p.y - a.y) * vy) / base2
  return { x: a.x + t * vx, y: a.y + t * vy }
}

/**
 * Els dos extrems de la COTA d'una projecció sobre un eix.
 *
 * Mirall de `engine/measure._projeccio`, i aquí pel mateix motiu que `peuPerpendicular`: el
 * canvas ha de saber dibuixar el que el servidor mesura sense una anada i tornada. La xifra
 * que val segueix sent la del servidor.
 *
 * `eix` buit = AUTO, l'eix de més recorregut, amb l'empat a l'horitzontal (com el motor).
 */
export function puntsDeLaCotaProjeccio(a, b, eix = '') {
  if (!a || !b) return []
  const quin = eix || (Math.abs(b.x - a.x) >= Math.abs(b.y - a.y) ? 'H' : 'V')
  if (quin === 'H') {
    const y = (a.y + b.y) / 2
    return [{ x: a.x, y }, { x: b.x, y }]
  }
  const x = (a.x + b.x) / 2
  return [{ x, y: a.y }, { x, y: b.y }]
}

/** El vector unitari perpendicular a a→b, girat +90°. `null` si els punts coincideixen. */
export function normalDe(a, b) {
  if (!a || !b) return null
  const dx = b.x - a.x
  const dy = b.y - a.y
  const l = Math.hypot(dx, dy)
  if (l <= 1e-9) return null
  return { x: -dy / l, y: dx / l }
}

/**
 * Una polilínia DESPLAÇADA en paral·lel a ella mateixa, `off` mm cap al costat de la normal.
 *
 * Cada vèrtex es mou per la seva normal LOCAL —la mitjana de les dels dos segments que hi
 * toquen—, que és el que fa que una corba desplaçada segueixi sent paral·lela a l'original
 * i no una còpia inclinada. Amb dos punts es redueix a moure'ls tots dos per la mateixa
 * normal, que és el cas de la recta.
 *
 * No és un offset de corba EXACTE (no resol autointerseccions als colzes tancats), i no cal
 * que ho sigui: això dibuixa una cota, no genera una trajectòria de tall.
 */
export function desplacaPolilinia(punts, off) {
  const n = punts.length
  if (n < 2) return punts
  if (!off) return punts

  const normals = []
  for (let i = 0; i < n - 1; i++) normals.push(normalDe(punts[i], punts[i + 1]))

  return punts.map((p, i) => {
    const abans = normals[i - 1]
    const despres = normals[i]
    const nx = ((abans?.x || 0) + (despres?.x || 0))
    const ny = ((abans?.y || 0) + (despres?.y || 0))
    const l = Math.hypot(nx, ny)
    if (l <= 1e-9) return p
    return { x: p.x + (nx / l) * off, y: p.y + (ny / l) * off }
  })
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

/**
 * La longitud d'un tram, en mm. Mateixa llei que `engine.segments.fraccio_tram`: si el tram
 * travessa l'origen de la polilínia (t_fi < t_inici) la fracció NO és una resta, és el que
 * queda fins al tancament més el que hi ha des del començament.
 */
export function longitudTram(boundary, tInici, tFi) {
  const fraccio = tFi >= tInici ? tFi - tInici : (1 - tInici) + tFi
  return fraccio * longitudVora(boundary)
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

  const rangs = []
  let acumulat = 0
  for (let i = 0; i < trams; i++) {
    rangs.push([acumulat / total, (acumulat + llargs[i]) / total])
    acumulat += llargs[i]
  }

  // Una aresta és del tram si hi comparteix LLARGADA. Tocar-lo per un extrem no és
  // compartir-hi res —i tocar-lo és el cas NORMAL, no el rar: `t_inici` és `cum[i]/total`,
  // exactament la frontera entre dues arestes—, així que l'epsilon ha d'ESTRÈNYER el rang.
  // Eixamplant-lo, el tram es pintava una aresta sencera més llarg per cada punta.
  const solapa = (i, ini, fi) => rangs[i][1] > ini + 1e-9 && rangs[i][0] < fi - 1e-9

  // L'ordre de sortida és el del RECORREGUT, no el dels índexs. Si el tram travessa
  // l'origen de la polilínia (t_fi < t_inici, vegeu `fraccio_tram` al motor), el rang és
  // la UNIÓ [t_inici, 1] ∪ [0, t_fi], i es recorre EN AQUEST ORDRE: primer el que queda
  // fins al tancament, després el que hi ha des del començament. Emetent-lo per índex, la
  // polilínia tornava enrere a mig traç i pintava una diagonal per dins de la peça.
  const ordre = []
  if (segment.t_fi < segment.t_inici) {
    for (let i = 0; i < trams; i++) if (solapa(i, segment.t_inici, 1)) ordre.push(i)
    for (let i = 0; i < trams; i++) if (solapa(i, 0, segment.t_fi)) ordre.push(i)
  } else {
    for (let i = 0; i < trams; i++) if (solapa(i, segment.t_inici, segment.t_fi)) ordre.push(i)
  }

  const out = []
  for (const i of ordre) {
    if (!out.length) out.push(pts[i])
    out.push(pts[(i + 1) % n])
  }
  return out
}

/**
 * Els DOS arcs entre dos vèrtexs d'una vora — la previsualització de «Definir segment».
 *
 * Dos punts d'una vora TANCADA no defineixen un tram: en defineixen dos, l'arc que va de A
 * a B i el que hi torna per l'altre costat. Cap dels dos és «el bo» en abstracte: depèn de
 * quina costura s'estigui declarant. Per això es dibuixen tots dos i es tria.
 *
 * En una vora OBERTA només hi ha un camí, i demanar-hi l'arc llarg és una contradicció (el
 * motor la rebutja). Aquí es retorna un sol arc, i prou.
 *
 * `arcLlarg` és el que el servidor espera a `POST /pattern-segments/`: el curt és el
 * defecte (arc_llarg=false), calcat de `engine.segments.tram_entre_punts`.
 */
export function arcsEntrePunts(boundary, idxA, idxB) {
  const pts = boundary.points || []
  const n = pts.length
  if (n < 2 || idxA === idxB) return []
  if (idxA < 0 || idxB < 0 || idxA >= n || idxB >= n) return []

  const cami = (desde, fins) => {
    const punts = [pts[desde]]
    let i = desde
    let llarg = 0
    // El pas és SEMPRE endavant amb mòdul: així «de B a A» és l'arc complementari, no el
    // mateix arc llegit al revés.
    while (i !== fins) {
      const seg = (i + 1) % n
      llarg += distancia(pts[i].x, pts[i].y, pts[seg].x, pts[seg].y)
      punts.push(pts[seg])
      i = seg
    }
    return { punts, longitud: llarg }
  }

  if (!boundary.closed) {
    const [d, f] = idxA <= idxB ? [idxA, idxB] : [idxB, idxA]
    const punts = pts.slice(d, f + 1)
    let llarg = 0
    for (let i = d; i < f; i++) llarg += distancia(pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y)
    return [{ ...{ punts, longitud: llarg }, arcLlarg: false, unic: true }]
  }

  const endavant = cami(idxA, idxB)
  const enrere = cami(idxB, idxA)
  // Empat exacte (antípodes): l'endavant és el curt, per determinisme — com fa el motor.
  const endavantEsCurt = endavant.longitud <= enrere.longitud
  const curt = endavantEsCurt ? endavant : enrere
  const llarg = endavantEsCurt ? enrere : endavant
  return [
    { ...curt, arcLlarg: false, unic: false },
    { ...llarg, arcLlarg: true, unic: false },
  ]
}

/**
 * On és un punt: de quina peça, de quina vora, i quin lloc hi ocupa.
 *
 * Ho pregunten el taller (per saber on pot caçar l'imant) i el visor (per dibuixar la
 * previsualització). Preguntat de dues maneres, acabaria responent dues coses.
 */
export function situaPunt(pieces, punt) {
  if (!punt) return null
  for (const piece of pieces || []) {
    for (const b of piece.boundaries || []) {
      const ordre = (b.points || []).findIndex(q => q.id === punt.id)
      if (ordre >= 0) return { piece, vora: b, index: b.index, ordre }
    }
  }
  return null
}

/**
 * L'arc que el cursor està assenyalant — la PREVISUALITZACIÓ DIRECCIONAL (W4b · T3c).
 *
 * Dos punts d'una vora tancada defineixen dos arcs, i abans això es preguntava DESPRÉS
 * («quin dels dos volies?»), amb els dos pintats i un pas més al mig. Preguntar-ho després
 * és preguntar-ho quan la mà ja ha marxat: qui declara un tram ja sap, mentre mou el cursor,
 * per quin costat el vol.
 *
 * Així que la regla és la del cursor: **l'arc que va de A fins on ets, pel camí més curt**.
 * Mentre el cursor recorre la vora en un sentit, l'arc el segueix; passat l'antípoda, el
 * camí curt és l'altre i l'arc salta —que és exactament quan cal poder dir «no, per l'altre
 * costat», i per això hi ha la tecla d'invertir. Amb `invertit`, l'arc és el complementari,
 * i es veu ABANS de confirmar.
 *
 * És la MATEIXA funció que fa servir el visor per pintar la prèvia i el taller per crear el
 * tram: si cadascú triés l'arc pel seu compte, un dia pintaria un i crearia l'altre.
 */
export function arcDirigit(boundary, idxA, idxB, invertit = false) {
  const arcs = arcsEntrePunts(boundary, idxA, idxB)
  if (!arcs.length) return null
  // Vora oberta: només hi ha un camí, i invertir-lo no és una preferència, és una
  // contradicció (el motor la rebutja). Es torna l'únic que hi ha.
  if (arcs[0].unic) return arcs[0]
  return arcs[invertit ? 1 : 0]
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

/**
 * Els punts de la vora entre dos VÈRTEXS, seguint el recorregut (A1).
 *
 * Els tres punts d'una pinça proposada són girs consecutius, però entre dos girs hi pot haver
 * punts de corba: el costat de la pinça és el recorregut de la vora, no la recta. Es dona la
 * volta si cal (vora tancada), amb la mateixa convenció que la resta del motor.
 */
export function puntsEntreIndexs(boundary, i, j) {
  const pts = boundary?.points || []
  const n = pts.length
  if (n < 2 || i < 0 || j < 0 || i >= n || j >= n) return []
  if (i === j) return []
  if (i < j) return pts.slice(i, j + 1)
  return boundary.closed ? [...pts.slice(i), ...pts.slice(0, j + 1)] : pts.slice(j, i + 1)
}
