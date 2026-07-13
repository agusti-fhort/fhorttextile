import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Stage, Layer, Line, Rect, Group, Arrow, Circle, Text } from 'react-konva'
import { useTranslation } from 'react-i18next'
import {
  bboxDePeces, capesPresents, escalaPerCabre, longitudVora,
  puntMesProper, puntsDelSegment, puntsPerKonva, tramMesProper,
} from './patternGeometry'

/**
 * Visor interactiu del patró (react-konva). READ-ONLY estricte: cap punt es pot arrossegar.
 *
 * Dibuixa des de la GEOMETRIA (endpoint /geometry/), no des de l'SVG del servidor. L'SVG
 * és un render de document —paleta fixa, per imprimir i arxivar— i continua servint per a
 * això; però un <img> no et pot dir que el cursor és a sobre d'un punt de gir, i això és
 * justament el que un visor ha de saber.
 *
 * QUÈ S'HA REUTILITZAT DEL TechSheetEditor I QUÈ NO (T-R5 del pla: el monòlit NO es toca):
 *   · Reutilitzat com a PATRÓ (llegit, no importat): el zoom aplicat com a escala del
 *     Stage i el zoom-al-cursor via getPointerPosition()/zoom.
 *   · NO reutilitzat: MM_TO_PX (=2.4), CANVAS_W/H, clampZoom i fitZoomToViewport. Les tres
 *     primeres són constants d'una pàgina A4 —un patró fa metre i mig i no hi cap—, i les
 *     dues funcions viuen dins del monòlit sense exportar. Duplicar-les netes aquí costa
 *     vint línies; extreure-les del monòlit costaria un refactor que el pla prohibeix.
 */

// El canvas NO resol var(--…): la paleta de canvas és literal, com KONVA_COL al
// TechSheetEditor. I NO és la paleta de l'SVG: allà és un document, aquí és una eina.
export const KONVA_COL = {
  cut: '#1d1d1b',        // contorn de tall — el que es retalla
  sew: '#1f6feb',        // línia de cosit (quan n'hi ha)
  internal: '#868685',   // línies internes
  mirror: '#8250df',
  unknown: '#c9c9c9',
  turn: '#3b6d11',       // punt de GIR: quadrat verd (llei del pla)
  curve: '#bf8700',      // punt de CORBA: x groga (llei del pla)
  notch: '#a32d2d',
  grain: '#3b6d11',
  sel: '#c27a2a',        // peça seleccionada
  selBg: 'rgba(194,122,42,0.07)',
  hover: '#c27a2a',
  bg: '#ffffff',
  pom: '#bf3989',      // la mesura d'un POM ancorat
  sewA: '#1f6feb',     // costat A d'una costura
  sewB: '#8250df',     // costat B
  tram: '#0969da',     // tram DECLARAT (el que una costura pot triar)
  tramSel: '#fb8500',  // el tram assenyalat o triat
}

const ZOOM_MIN = 0.02
const ZOOM_MAX = 8
const ZOOM_STEP = 1.15

const GLIF = 3.2          // mida dels glifs de punt, en px de contingut
const ALCADA = 560

const clampZoom = (v) => Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, v))

export default function PatternViewer({
  pieces, pecaSel, onTriaPeca,
  // ── mode d'anotació (S6). Sense aquestes props, el visor és el de S5: read-only.
  mode = 'view',                 // 'view' | 'pom' | 'sew'
  puntsPom = [],                 // punts ja clicats en mode POM (0, 1 o 2)
  onClicPunt = null,
  // Els trams que la costura en curs ja té a cada costat (per pintar-los del seu color).
  segmentsA = [], segmentsB = [],
  // ── W3/D8. La peça on es COL·LOCA: l'imant només s'ofereix sobre els seus punts i la
  // resta del patró s'atenua. Sense això, l'imant caça el punt més proper del patró SENCER
  // — i dos punts de peces diferents no són una mesura d'una peça, són un PatternPOM
  // impossible (en penja d'UNA). La restricció no és estètica: és la llei del model.
  pecaIman = null,
  // ── W4. La vora on l'imant pot caçar. Un tram és un tros d'UNA vora: posat el punt A, el
  // B no pot sortir d'una altra —el motor ho rebutjaria—, i val més no deixar clicar el que
  // no es pot fer que deixar-ho clicar i després dir que no.
  voraIman = null,
  // Els dos arcs que dos punts d'una vora tancada defineixen: es dibuixen tots dos i es tria.
  arcs = [], arcTriat = 0, onTriaArc = null,
  // Els trams DECLARATS, pintats sobre la geometria. `tramRessaltat` és el que la llista de
  // cosir assenyala en passar-hi per sobre.
  tramsDeclarats = [], tramRessaltat = null, onClicTram = null,
  // ── W2. Al Taller el canvas no té una alçada de maqueta: ocupa el que li deixa el
  // pare. Al tab (la porta) segueix valent ALCADA, que és el que sempre ha valgut.
  omplirAlcada = false,
}) {
  const { t } = useTranslation()
  const viewportRef = useRef(null)
  const stageRef = useRef(null)

  const [mida, setMida] = useState({ w: 800, h: ALCADA })
  const [zoom, setZoom] = useState(1)
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const [hover, setHover] = useState(null)      // { xMm, yMm, tram }
  // La MÀ (D7). El pan no el fa el `draggable` de Konva sinó nosaltres, perquè la regla no
  // és «es pot arrossegar o no»: és «es pot arrossegar SEGONS què s'estigui fent». Amb el
  // draggable de Konva no hi ha manera de dir «arrossega només amb l'espai o el botó del
  // mig», i mentre es col·loca un POM un drag lliure mouria el patró sota el punt que
  // s'està mirant.
  const panRef = useRef(null)          // { x0, y0, px, py, mogut }
  const [espai, setEspai] = useState(false)
  const espaiRef = useRef(false)
  const arrossegatRef = useRef(false)  // el clic que tanca un pan NO és un clic
  const [capes, setCapes] = useState({
    cut: true, sew: true, internal: true, mirror: true,
    notch: true, grain: true, punts: true,
  })

  const bbox = useMemo(() => bboxDePeces(pieces), [pieces])
  const presents = useMemo(() => capesPresents(pieces), [pieces])

  // Els punts que l'imant pot caçar: els de la peça activa (i, definint un tram, els de la
  // seva VORA), o els de tot el patró si encara no s'ha clicat res.
  const pecesIman = useMemo(() => {
    if (!pecaIman) return pieces
    const p = pieces.find(x => x.nom_block === pecaIman)
    if (!p) return []
    if (voraIman == null) return [p]
    return [{ ...p, boundaries: (p.boundaries || []).filter(b => b.index === voraIman) }]
  }, [pieces, pecaIman, voraIman])

  // ── enquadrar ────────────────────────────────────────────────────────────
  const encaixar = useCallback(() => {
    const el = viewportRef.current
    if (!el) return
    const w = el.clientWidth
    const h = omplirAlcada ? el.clientHeight : ALCADA
    if (!w || !h) return
    const z = clampZoom(escalaPerCabre(bbox, w, h))
    setZoom(z)
    // El contingut es dibuixa en mm amb l'eix Y capgirat: el centrem al viewport.
    setPos({
      x: w / 2 - ((bbox.minX + bbox.maxX) / 2) * z,
      y: h / 2 + ((bbox.minY + bbox.maxY) / 2) * z,
    })
    setMida({ w, h })
  }, [bbox, omplirAlcada])

  useEffect(() => { encaixar() }, [encaixar])

  useEffect(() => {
    if (omplirAlcada) return          // omplint l'alçada mana el ResizeObserver, aquí sota
    const onResize = () => encaixar()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [encaixar, omplirAlcada])

  // Omplint l'alçada, la mida del canvas la mana el PARE (un contenidor que creix, una barra
  // de guia que apareix), i això la finestra no ho veu: cal observar el viewport.
  //
  // Re-MESURAR no és re-ENQUADRAR. Al principi això cridava encaixar(), i llavors qualsevol
  // canvi d'alçada del canvas —com la barra de guia que surt en començar a col·locar un
  // POM— reenquadrava el patró i li prenia el zoom i la posició a qui estava treballant.
  // Justament al pitjor moment: quan s'acaba d'apuntar a un punt. Aquí només s'actualitza
  // la mida de l'escenari; el zoom i la posició NO es toquen. Reenquadrar és una ordre
  // explícita (el botó Encaixar), no un efecte secundari de canviar de mida.
  useEffect(() => {
    if (!omplirAlcada) return
    const el = viewportRef.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => {
      const w = el.clientWidth
      const h = el.clientHeight
      if (w && h) setMida({ w, h })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [omplirAlcada])

  // L'espai és la mà de tota la vida. Es mira el target: en un camp de text, un espai és un
  // espai — que escriure el nom d'un tram et paneges el patró seria absurd.
  useEffect(() => {
    const esCamp = (el) => !!el && (
      /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) || el.isContentEditable)
    const down = (e) => {
      if (e.code !== 'Space' || esCamp(e.target)) return
      e.preventDefault()               // l'espai, si no, fa scroll de pàgina
      espaiRef.current = true
      setEspai(true)
    }
    const up = (e) => {
      if (e.code !== 'Space') return
      espaiRef.current = false
      setEspai(false)
    }
    window.addEventListener('keydown', down)
    window.addEventListener('keyup', up)
    return () => {
      window.removeEventListener('keydown', down)
      window.removeEventListener('keyup', up)
    }
  }, [])

  // ── zoom amb la roda, ancorat al cursor ──────────────────────────────────
  const onWheel = (e) => {
    e.evt.preventDefault()
    const stage = stageRef.current
    if (!stage) return
    const punter = stage.getPointerPosition()
    if (!punter) return

    const zAnt = zoom
    const zNou = clampZoom(e.evt.deltaY < 0 ? zAnt * ZOOM_STEP : zAnt / ZOOM_STEP)
    if (zNou === zAnt) return

    // El punt del món sota el cursor s'ha de quedar sota el cursor.
    const mon = { x: (punter.x - pos.x) / zAnt, y: (punter.y - pos.y) / zAnt }
    setZoom(zNou)
    setPos({ x: punter.x - mon.x * zNou, y: punter.y - mon.y * zNou })
  }

  const zoomBoto = (factor) => {
    const zNou = clampZoom(zoom * factor)
    const centre = { x: mida.w / 2, y: mida.h / 2 }
    const mon = { x: (centre.x - pos.x) / zoom, y: (centre.y - pos.y) / zoom }
    setZoom(zNou)
    setPos({ x: centre.x - mon.x * zNou, y: centre.y - mon.y * zNou })
  }

  // Col·locant de debò (ja hi ha un punt A a la pantalla), el drag lliure no paneja: mouria
  // el patró sota el punt que s'està a punt de clicar. Llavors la mà es demana — espai o
  // botó del mig. La resta del temps (mirant, cosint, o abans del punt A) el drag paneja,
  // que és el que tothom espera d'un canvas.
  // POM i SEGMENT es marquen igual: dos punts imantats sobre la geometria. El que canvia és
  // què se'n fa (una mesura recta, o un tros de vora).
  const imantant = mode === 'pom' || mode === 'seg'
  const colocant = imantant && puntsPom.length > 0
  const potPanejar = !colocant
  const maAlta = espai || !!panRef.current

  // ── la mà: pan manual ────────────────────────────────────────────────────
  const onMouseDown = (e) => {
    const evt = e.evt
    const forcat = evt.button === 1 || espaiRef.current    // botó del mig o espai
    if (evt.button !== 0 && evt.button !== 1) return
    if (!forcat && !potPanejar) return

    evt.preventDefault()               // el botó del mig, si no, obre l'autoscroll
    const p = stageRef.current?.getPointerPosition()
    if (!p) return
    panRef.current = { x0: p.x, y0: p.y, px: pos.x, py: pos.y, mogut: false }
  }

  const acabarPan = useCallback(() => {
    if (!panRef.current) return
    // Si el punter s'ha mogut, això ha estat un PAN i el clic que ve al darrere no és un
    // clic de l'usuari: és el final de l'arrossegament. Marcar-lo i menjar-se'l.
    if (panRef.current.mogut) arrossegatRef.current = true
    panRef.current = null
  }, [])

  // El botó es pot deixar anar FORA del canvas: sense això, el pan es quedaria enganxat al
  // cursor i el patró seguiria el ratolí sense cap botó premut.
  useEffect(() => {
    window.addEventListener('mouseup', acabarPan)
    return () => window.removeEventListener('mouseup', acabarPan)
  }, [acabarPan])

  // ── hover: on és el cursor i quin tram de vora hi ha a sota ──────────────
  const onMouseMove = () => {
    const stage = stageRef.current
    if (!stage) return
    const p = stage.getPointerPosition()
    if (!p) { setHover(null); return }

    if (panRef.current) {
      const dx = p.x - panRef.current.x0
      const dy = p.y - panRef.current.y0
      if (Math.abs(dx) + Math.abs(dy) > 3) panRef.current.mogut = true
      setPos({ x: panRef.current.px + dx, y: panRef.current.py + dy })
      return                           // panejant no s'imanta res
    }

    const xMm = (p.x - pos.x) / zoom
    const yMm = -(p.y - pos.y) / zoom      // desfem el capgirat de l'eix Y
    const tram = tramMesProper(pieces, xMm, yMm, 12 / zoom)
    // En mode POM, el cursor s'imanta al punt més proper: marcar una mesura "a ull" no
    // seria una mesura del patró, seria un dibuix a sobre del patró.
    const iman = imantant ? puntMesProper(pecesIman, xMm, yMm, 14 / zoom) : null
    setHover({ xMm, yMm, tram, iman })
  }

  const onClicStage = () => {
    if (arrossegatRef.current) { arrossegatRef.current = false; return }
    if (imantant && hover?.iman && onClicPunt) onClicPunt(hover.iman)
  }

  const visible = (capa) => capes[capa] && presents.has(capa)
  const anotant = mode !== 'view'
  // Qui té el focus: col·locant, la peça de l'imant; mirant, la peça seleccionada. Cosint no
  // s'atenua res — una costura uneix DUES peces i amagar-ne una seria amagar la meitat.
  const pecaFocus = imantant ? pecaIman : (anotant ? null : pecaSel)


  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: '0.5rem',
      ...(omplirAlcada ? { height: '100%', minHeight: 0 } : null),
    }}>
      <Controls
        t={t} zoom={zoom} capes={capes} presents={presents}
        onZoom={zoomBoto} onEncaixa={encaixar}
        onToggle={(c) => setCapes(prev => ({ ...prev, [c]: !prev[c] }))}
      />

      <div
        ref={viewportRef}
        style={{
          border: '1px solid var(--border)', borderRadius: 8,
          background: 'var(--white)', overflow: 'hidden',
          cursor: maAlta ? 'grabbing' : anotant ? 'crosshair' : 'grab',
          ...(omplirAlcada ? { flex: 1, minHeight: 0 } : null),
        }}
      >
        <Stage
          ref={stageRef}
          width={mida.w}
          height={mida.h}
          scaleX={zoom}
          scaleY={zoom}
          x={pos.x}
          y={pos.y}
          onWheel={onWheel}
          onMouseDown={onMouseDown}
          onMouseMove={onMouseMove}
          onMouseUp={acabarPan}
          onMouseLeave={() => setHover(null)}
          onClick={onClicStage}
          onTap={onClicStage}
        >
          <Layer>
            {pieces.map(piece => (
              <PecaKonva
                key={piece.id}
                piece={piece}
                zoom={zoom}
                sel={piece.nom_block === pecaSel}
                atenuada={!!pecaFocus && piece.nom_block !== pecaFocus}
                visible={visible}
                // Els punts es dibuixen on es poden clicar. Ensenyar-los a una peça on
                // l'imant no els caçarà seria oferir un clic que no farà res.
                mostraPunts={capes.punts
                  || (mode === 'pom' && (!pecaIman || piece.nom_block === pecaIman))}
                anotant={anotant}
                onClick={() => !anotant && onTriaPeca(
                  piece.nom_block === pecaSel ? '' : piece.nom_block)}
              />
            ))}

            {/* Els POMs ja ancorats: la mesura, dibuixada sobre la geometria que mesura. */}
            {pieces.flatMap(piece => (piece.poms || []).map(pom => (
              <PomKonva key={`pom-${pom.id}`} piece={piece} pom={pom} zoom={zoom} />
            )))}

            {/* Els trams DECLARATS, sobre la geometria. Es pinten SEMPRE: són el vocabulari
                de costura del patró, i qui cus ha de veure què hi ha declarat sense canviar
                de mode. Els 'auto' del motor NO es pinten — són una proposta de lectura, i
                dibuixar-los seria dir que existeixen. */}
            {tramsDeclarats.map(tr => {
              const piece = pieces.find(p => p.id === tr.piece_id)
              if (!piece) return null
              const pts = puntsDelSegment(piece, tr)
              if (pts.length < 2) return null
              const marcat = tramRessaltat === tr.id
              const enA = segmentsA.includes(tr.id)
              const enB = segmentsB.includes(tr.id)
              const color = enA ? KONVA_COL.sewA : enB ? KONVA_COL.sewB
                : marcat ? KONVA_COL.tramSel : KONVA_COL.tram
              return (
                <Line
                  key={`tram-${tr.id}`}
                  points={pts.flatMap(p => [p.x, -p.y])}
                  stroke={color}
                  strokeWidth={(marcat || enA || enB ? 4.5 : 2.5) / zoom}
                  lineCap="round"
                  listening={mode === 'sew' && !!onClicTram}
                  hitStrokeWidth={Math.max(14 / zoom, 5)}
                  onClick={() => onClicTram && onClicTram(tr)}
                  onTap={() => onClicTram && onClicTram(tr)}
                  perfectDrawEnabled={false}
                />
              )
            })}

            {/* Mode SEGMENT: els DOS arcs que els dos punts defineixen. El triat, gruixut;
                l'altre, discontinu i clicable — triar-lo és clicar-lo. */}
            {mode === 'seg' && arcs.map((arc, i) => {
              const triat = i === arcTriat
              return (
                <Line
                  key={`arc-${i}`}
                  points={arc.punts.flatMap(p => [p.x, -p.y])}
                  stroke={triat ? KONVA_COL.tramSel : KONVA_COL.tram}
                  strokeWidth={(triat ? 5 : 2.5) / zoom}
                  dash={triat ? undefined : [8 / zoom, 5 / zoom]}
                  opacity={triat ? 1 : 0.75}
                  lineCap="round"
                  listening={!!onTriaArc}
                  hitStrokeWidth={Math.max(16 / zoom, 6)}
                  onClick={() => onTriaArc && onTriaArc(i)}
                  onTap={() => onTriaArc && onTriaArc(i)}
                  perfectDrawEnabled={false}
                />
              )
            })}
            {mode === 'seg' && arcs.map((arc, i) => {
              const mig = arc.punts[Math.floor(arc.punts.length / 2)]
              if (!mig) return null
              return (
                <Text
                  key={`arc-txt-${i}`}
                  x={mig.x} y={-mig.y - 14 / zoom}
                  text={`${(arc.longitud / 10).toFixed(1)} cm`}
                  fontSize={12 / zoom}
                  fill={i === arcTriat ? KONVA_COL.tramSel : KONVA_COL.tram}
                  listening={false} perfectDrawEnabled={false}
                />
              )
            })}

            {/* Mode POM: la mesura que s'està marcant, i l'imant sota el cursor. */}
            {mode === 'pom' && puntsPom.length >= 1 && (
              <Line
                points={[
                  ...puntsPom.flatMap(p => [p.x, -p.y]),
                  ...(puntsPom.length === 1 && hover?.iman
                    ? [hover.iman.punt.x, -hover.iman.punt.y] : []),
                ]}
                stroke={KONVA_COL.pom}
                strokeWidth={2 / zoom}
                dash={[5 / zoom, 3 / zoom]}
                listening={false}
                perfectDrawEnabled={false}
              />
            )}
            {imantant && puntsPom.map((p, i) => (
              <Circle
                key={`sel-${i}`} x={p.x} y={-p.y} r={5 / zoom}
                fill={KONVA_COL.pom} listening={false} perfectDrawEnabled={false}
              />
            ))}
            {imantant && hover?.iman && (
              <Circle
                x={hover.iman.punt.x} y={-hover.iman.punt.y} r={6 / zoom}
                stroke={KONVA_COL.pom} strokeWidth={1.5 / zoom}
                listening={false} perfectDrawEnabled={false}
              />
            )}
          </Layer>
        </Stage>
      </div>

      <BarraEstat t={t} hover={hover} pieces={pieces} pecaSel={pecaSel} colocant={colocant} />
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * Un POM ancorat, dibuixat sobre la geometria que mesura.
 *
 * La línia de mesura és la MATEIXA cosa que la capa FTT-POM exportarà al DXF (S2): el que
 * el patronista veurà al seu CAD és això mateix. Aquí i allà, la mesura es dibuixa on és.
 */
function PomKonva({ piece, pom, zoom }) {
  const punts = puntsDeLaMesura(piece, pom)
  if (punts.length < 2) return null
  const mig = {
    x: (punts[0].x + punts[punts.length - 1].x) / 2,
    y: (punts[0].y + punts[punts.length - 1].y) / 2,
  }
  return (
    <Group listening={false}>
      <Line
        points={punts.flatMap(p => [p.x, -p.y])}
        stroke={KONVA_COL.pom} strokeWidth={1.8 / zoom}
        perfectDrawEnabled={false}
      />
      {punts.map((p, i) => (
        <Circle key={i} x={p.x} y={-p.y} r={3 / zoom} fill={KONVA_COL.pom}
                perfectDrawEnabled={false} />
      ))}
      <Text
        x={mig.x} y={-mig.y - 14 / zoom}
        text={`${pom.pom_code}${pom.valor_mesurat_cm != null ? ` ${pom.valor_mesurat_cm} cm` : ''}`}
        fontSize={11 / zoom}
        fill={KONVA_COL.pom}
        perfectDrawEnabled={false}
      />
    </Group>
  )
}

/** Els punts que una recepta de mesura toca (mode `points`; el landmark es resol al servidor). */
function puntsDeLaMesura(piece, pom) {
  const def = pom.definicio_mesura || {}
  const perId = new Map()
  for (const b of piece.boundaries || []) {
    for (const p of b.points || []) perId.set(p.id, p)
  }
  const a = perId.get(def.a) || perId.get(def.landmark)
  const b = perId.get(def.b)
  return a && b ? [a, b] : []
}

function PecaKonva({ piece, zoom, sel, atenuada, visible, mostraPunts, anotant, onClick }) {
  // Els traços es dibuixen amb gruix CONSTANT a pantalla: si el gruix escalés amb el
  // zoom, en allunyar-se el patró es convertiria en una taca negra i en apropar-se
  // desapareixeria.
  const gruix = (base) => base / zoom
  const g = GLIF / zoom

  return (
    <Group opacity={atenuada ? 0.25 : 1} onClick={onClick} onTap={onClick}>
      {piece.boundaries.map(b => {
        if (!visible(b.role)) return null
        const esTall = b.role === 'cut'
        return (
          <Line
            key={`${piece.id}-${b.index}`}
            points={puntsPerKonva(b)}
            closed={b.closed}
            stroke={sel && esTall ? KONVA_COL.sel : (KONVA_COL[b.role] || KONVA_COL.unknown)}
            strokeWidth={gruix(esTall ? 1.6 : 0.9)}
            dash={b.role === 'sew' ? [6 / zoom, 3 / zoom] : undefined}
            fill={sel && esTall ? KONVA_COL.selBg : undefined}
            lineJoin="round"
            hitStrokeWidth={Math.max(12 / zoom, 4)}
            perfectDrawEnabled={false}
          />
        )
      })}

      {/* Glifs de punt: quadrat verd = GIR (es grada) · x groga = CORBA (flueix).
          La distinció no és decorativa: és la llei que governa què es mou a l'escalat. */}
      {mostraPunts && piece.boundaries.flatMap(b =>
        (visible(b.role) ? b.points : []).map((p, i) => (
          p.tipus === 'turn' ? (
            <Rect
              key={`t-${piece.id}-${b.index}-${i}`}
              x={p.x - g / 2} y={-p.y - g / 2} width={g} height={g}
              fill={KONVA_COL.turn} listening={false} perfectDrawEnabled={false}
            />
          ) : p.tipus === 'curve' ? (
            <Group key={`c-${piece.id}-${b.index}-${i}`} listening={false}>
              <Line points={[p.x - g / 2, -p.y - g / 2, p.x + g / 2, -p.y + g / 2]}
                    stroke={KONVA_COL.curve} strokeWidth={gruix(0.9)} perfectDrawEnabled={false} />
              <Line points={[p.x - g / 2, -p.y + g / 2, p.x + g / 2, -p.y - g / 2]}
                    stroke={KONVA_COL.curve} strokeWidth={gruix(0.9)} perfectDrawEnabled={false} />
            </Group>
          ) : null
        ))
      )}

      {visible('notch') && piece.notches.map((n, i) => (
        <Rect
          key={`n-${piece.id}-${i}`}
          x={n.x - g * 0.7} y={-n.y - g * 0.7} width={g * 1.4} height={g * 1.4}
          fill={KONVA_COL.notch} rotation={45} listening={false} perfectDrawEnabled={false}
        />
      ))}

      {visible('grain') && piece.grain && (
        <Arrow
          points={[piece.grain.x1, -piece.grain.y1, piece.grain.x2, -piece.grain.y2]}
          stroke={KONVA_COL.grain} fill={KONVA_COL.grain}
          strokeWidth={gruix(0.9)} pointerLength={6 / zoom} pointerWidth={5 / zoom}
          pointerAtBeginning listening={false} perfectDrawEnabled={false}
        />
      )}
    </Group>
  )
}

function Controls({ t, zoom, capes, presents, onZoom, onEncaixa, onToggle }) {
  // Les capes que el fitxer NO porta no s'ofereixen: un toggle que no fa res és pitjor
  // que no tenir-lo, perquè fa pensar que la capa hi és i està amagada.
  const TOGGLES = [
    ['cut', 'ti-line'], ['sew', 'ti-needle-thread'], ['internal', 'ti-line-dashed'],
    ['mirror', 'ti-flip-horizontal'], ['notch', 'ti-scissors'], ['grain', 'ti-arrow-narrow-up'],
  ]
  const boto = {
    background: 'var(--white)', border: '1px solid var(--border)', borderRadius: 4,
    padding: '0.2rem 0.5rem', cursor: 'pointer', fontSize: 'var(--fs-caption)',
    display: 'flex', alignItems: 'center', gap: '0.25rem',
  }

  return (
    <div style={{
      display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center', flexShrink: 0,
    }}>
      <button onClick={() => onZoom(1 / ZOOM_STEP)} style={boto} aria-label={t('pattern.zoom_out')}>
        <i className="ti ti-zoom-out" />
      </button>
      <button onClick={() => onZoom(ZOOM_STEP)} style={boto} aria-label={t('pattern.zoom_in')}>
        <i className="ti ti-zoom-in" />
      </button>
      <button onClick={onEncaixa} style={boto}>
        <i className="ti ti-maximize" />
        {t('pattern.fit')}
      </button>
      <span style={{
        fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
        fontFamily: 'var(--mono)', minWidth: 52,
      }}>
        {(zoom * 100).toFixed(0)}%
      </span>

      <span style={{ width: 1, height: 18, background: 'var(--border)', margin: '0 0.2rem' }} />

      {TOGGLES.filter(([capa]) => presents.has(capa)).map(([capa, icona]) => (
        <button
          key={capa}
          onClick={() => onToggle(capa)}
          aria-pressed={capes[capa]}
          style={{
            ...boto,
            background: capes[capa] ? 'var(--gold-pale)' : 'var(--white)',
            borderColor: capes[capa] ? 'var(--gold)' : 'var(--border)',
            opacity: capes[capa] ? 1 : 0.55,
          }}
        >
          <i className={`ti ${icona}`} />
          {t(`pattern.layer.${capa}`)}
        </button>
      ))}
      <button
        onClick={() => onToggle('punts')}
        aria-pressed={capes.punts}
        style={{
          ...boto,
          background: capes.punts ? 'var(--gold-pale)' : 'var(--white)',
          borderColor: capes.punts ? 'var(--gold)' : 'var(--border)',
          opacity: capes.punts ? 1 : 0.55,
        }}
      >
        <i className="ti ti-point" />
        {t('pattern.layer.points')}
      </button>
    </div>
  )
}

function BarraEstat({ t, hover, pieces, pecaSel, colocant }) {
  const cm = (mm) => (mm / 10).toFixed(1)
  const peca = pecaSel ? pieces.find(p => p.nom_block === pecaSel) : null
  const perimetre = peca
    ? longitudVora((peca.boundaries || []).find(b => b.role === 'cut') || { points: [] })
    : 0

  return (
    <div style={{
      display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center',
      fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
      fontFamily: 'var(--mono)', minHeight: 18, flexShrink: 0,
    }}>
      {/* Col·locant, la pista de la mà NO substitueix les coordenades: mentre es marca un
          punt és quan més falta fan. Van juntes. */}
      {colocant && (
        <span style={{ color: 'var(--gold)' }}>
          <i className="ti ti-hand-move" /> {t('pattern.taller.pan_hint')}
        </span>
      )}
      {hover ? (
        <>
          <span>{t('pattern.cursor', { x: cm(hover.xMm), y: cm(hover.yMm) })}</span>
          {hover.tram && (
            <span style={{ color: 'var(--gold)' }}>
              <i className="ti ti-ruler-measure" />{' '}
              {t('pattern.segment', {
                peca: hover.tram.peca,
                capa: t(`pattern.layer.${hover.tram.role}`),
                cm: cm(hover.tram.longitud),
              })}
            </span>
          )}
        </>
      ) : (
        <span>{t('pattern.hover_hint')}</span>
      )}
      <span style={{ flex: 1 }} />
      {peca && (
        <span style={{ color: 'var(--text-main)' }}>
          {t('pattern.selected_piece', { peca: peca.nom_block, cm: cm(perimetre) })}
        </span>
      )}
    </div>
  )
}
