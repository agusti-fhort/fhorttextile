import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { Stage, Layer, Line, Rect, Group, Arrow, Circle, Text } from 'react-konva'
import { useTranslation } from 'react-i18next'

import { etiquetaPeca } from './pieceText'
import {
  arcDirigit, arcsEntrePunts, bboxDePeces, capesPresents, desplacaPolilinia, escalaPerCabre,
  longitudVora, normalDe, peuPerpendicular, puntMesProper, puntsDeLaCotaProjeccio,
  puntsDelSegment, puntsPerKonva, situaPunt, tramMesProper,
} from './patternGeometry'
import { formatLen, formatLenNum } from '../../utils/format'

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
  // Miralls dels tokens `--tram` / `--tram-sel` (index.css): el tram es pinta IGUAL mentre
  // es declara i un cop desat —és el mateix objecte—, i l'estat només en canvia l'èmfasi.
  tram: '#0969da',     // = var(--tram) · identitat del tram, declarant-lo i declarat
  tramSel: '#fb8500',  // = var(--tram-sel) · el tram que s'assenyala: èmfasi, no identitat
  pinca: '#1b7c83',    // una PINÇA declarada: els seus dos costats i el seu vèrtex
}

// El rang de zoom no és una preferència estètica: és el que decideix si un vèrtex es pot
// triar còmodament. Els punts de gir d'una pinça viuen a 6 mm l'un de l'altre, i amb el
// sostre vell (×8) apuntar-hi era una pràctica de punteria. Per baix, un patró de niada fa
// metres i ha de cabre sencer.
const ZOOM_MIN = 0.005
const ZOOM_MAX = 40
const ZOOM_STEP = 1.15

const ALCADA = 560

// Mètrica del botó d'eina, en un sol lloc. La barra del Taller i els controls del visor són
// UNA fila: dues mides de botó a la mateixa fila es llegeixen com dues barres, que és
// exactament el que s'ha vingut a treure. La compacta és la del visor dins el tab del model,
// on els controls són de vora i no han de pesar com una barra d'eines.
export const METRICA_EINA = {
  borderRadius: 4, padding: '0.35rem 0.8rem', fontSize: 'var(--fs-body)', gap: '0.35rem',
}
export const METRICA_EINA_COMPACTA = {
  borderRadius: 4, padding: '0.2rem 0.5rem', fontSize: 'var(--fs-caption)', gap: '0.25rem',
}

const clampZoom = (v) => Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, v))

/**
 * La mida d'un glif, en px de CONTINGUT (es divideix pel zoom perquè a pantalla sigui la que
 * es demana). Creix amb el zoom però amb sordina i amb sostre: els glifs han de ser més
 * fàcils d'encertar quan t'hi apropes, no convertir-se en taques quan hi ets a sobre.
 */
const midaGlif = (base, max, zoom) =>
  Math.min(max, base * Math.sqrt(Math.max(zoom, 0.05))) / zoom

export default function PatternViewer({
  pieces, pecaSel, onTriaPeca,
  // ── mode d'anotació (S6). Sense aquestes props, el visor és el de S5: read-only.
  mode = 'view',                 // 'view' | 'pom' | 'seg' | 'pinca' | 'sew'
  puntsPom = [],                 // punts ja clicats (2 per a POM i tram; 3 per a una pinça)
  // Els noms de les àncores que el gest de POM demana, EN ORDRE, tal com el backend els
  // serveix ('a','b' · 'ref_a','ref_b','p'). El visor n'havia de deduir el recompte amb una
  // regla pròpia («pinça 3, la resta 2»), que era una segona còpia de la del taller i es va
  // quedar enrere el dia que un mètode en va voler tres. Ara la rep.
  ancoresPom = ['a', 'b'],
  // ── La COTA seleccionada al canvas, i què se'n pot fer. Sense `onSeleccionaPom` les
  // cotes no escolten el ratolí (és el visor read-only del tab del model); sense `onMouPom`
  // no s'arrosseguen.
  pomSel = null,
  onSeleccionaPom = null,
  onMouPom = null,
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
  // ── W4b/T3c. La PREVISUALITZACIÓ DIRECCIONAL substitueix la tria d'arcs com a pas a part:
  // posat el punt A, l'arc segueix el cursor en temps real i el clic B el fixa. `arcInvertit`
  // és el camí llarg (la tecla d'invertir), i `invertits` és el que es va triar a cada arc JA
  // fixat — sense això, invertir el segon costat d'una pinça giraria també el primer.
  arcInvertit = false, invertits = [],
  // ── W4b/T5. L'OMBRA: el que s'està reobrint, dibuixat de fons. Recol·locar sense veure d'on
  // véns és recol·locar a cegues — i el que es corregeix, gairebé sempre, és un punt sol.
  ombra = null,
  // Els trams DECLARATS, pintats sobre la geometria. `tramRessaltat` és el que la llista de
  // cosir assenyala en passar-hi per sobre.
  tramsDeclarats = [], tramRessaltat = null, onClicTram = null,
  // ── W4b/T1. Les pinces declarades: els seus dos costats i el seu vèrtex, amb glif propi.
  // Una pinça no és una costura més: és el forat que explica per què la vora fa 32 i en cus 30.
  pinces = [],
  // ── A2. La proposta que el cursor assenyala: `{a, b}`, els dos trams que el motor diu que es
  // cusen. Es pinten a ratlles i només mentre s'hi passa per sobre — una proposta no forma part
  // del patró fins que algú la confirma, i dibuixar-la fixa la faria passar per una decisió.
  propostaRessaltada = null,
  // ── A1. Les pinces que el motor veu: un glif DISCRET al vèrtex, sempre visible (és el mapa del
  // que hi ha per decidir), i els dos costats encesos només quan el cursor és a la seva fila. El
  // glif és petit i buit a posta: una pinça proposada no és una pinça, i si es pintés com la
  // declarada ningú sabria quines ha marcat ell.
  pincesProposades = [], pincaProposadaRessaltada = null,
  // La unitat del tenant (CM|INCH): el canvas també és taller, i hi val la mateixa llei.
  unit = 'CM',
  // ── W2. Al Taller el canvas no té una alçada de maqueta: ocupa el que li deixa el
  // pare. Al tab (la porta) segueix valent ALCADA, que és el que sempre ha valgut.
  omplirAlcada = false,
  // ── El node DOM on el pare vol els controls (zoom/encaixar/capes). Sense això es pinten
  // aquí mateix, com sempre. Amb això viatgen per PORTAL a la barra del pare i les eines del
  // Taller i les del visor formen UNA sola fila.
  //
  // Per què un portal i no pujar els botons al pare: l'estat que mouen (zoom, pos, capes) viu
  // aquí i està lligat al viewport i a la roda del ratolí; pujar-lo seria moure el motor de
  // pan/zoom fora del component que el fa servir. I al revés tampoc: la barra del Taller es
  // pinta encara que el fitxer no carregui (el visor, no) — baixar-la aquí la faria
  // desaparèixer en el moment que més fa falta, el de l'error.
  contenidorEines = null,
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
  // 🚨 Les dependències són les QUATRE XIFRES de la capsa, no l'objecte.
  //
  // `bboxDePeces` en torna un de nou a cada crida, i `pieces` canvia d'identitat cada cop
  // que el Taller reescriu la geometria —cosa que ara passa a cada arrossegada d'una cota,
  // per l'actualització optimista. Amb l'objecte a les dependències, `encaixar` canviava
  // d'identitat, l'efecte de sota tornava a disparar-se i **el llenç es reenquadrava sol**:
  // fer zoom sobre un escot per separar tres cotes, moure'n una, i que el patró saltés a
  // «encaixar-ho tot».
  //
  // Amb les xifres, l'enquadrat es refà quan canvia el que ha de fer-lo canviar —una versió
  // nova del patró, una peça que entra o surt— i no quan es mou una línia de lloc.
  const { minX, maxX, minY, maxY } = bbox
  const encaixar = useCallback(() => {
    const el = viewportRef.current
    if (!el) return
    const w = el.clientWidth
    const h = omplirAlcada ? el.clientHeight : ALCADA
    if (!w || !h) return
    const z = clampZoom(escalaPerCabre({ minX, maxX, minY, maxY }, w, h))
    setZoom(z)
    // El contingut es dibuixa en mm amb l'eix Y capgirat: el centrem al viewport.
    setPos({
      x: w / 2 - ((minX + maxX) / 2) * z,
      y: h / 2 + ((minY + maxY) / 2) * z,
    })
    setMida({ w, h })
  }, [minX, maxX, minY, maxY, omplirAlcada])

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
  // POM, TRAM i PINÇA es marquen igual: punts imantats sobre la geometria. El que canvia és
  // quants (dos, dos, tres) i què se'n fa (una mesura recta, un tros de vora, o una pinça).
  const imantant = mode === 'pom' || mode === 'seg' || mode === 'pinca'
  const segueixVora = mode === 'seg' || mode === 'pinca'
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

  /** L'arc entre dos punts d'una vora, si de debò comparteixen vora. */
  const arcEntre = useCallback((pa, pb, invertit) => {
    const a = situaPunt(pieces, pa)
    const b = situaPunt(pieces, pb)
    if (!a || !b || a.index !== b.index || a.ordre === b.ordre) return null
    return arcDirigit(a.vora, a.ordre, b.ordre, invertit)
  }, [pieces])

  // Els arcs JA FIXATS (el primer costat d'una pinça, un cop clicat el vèrtex). Cadascun es
  // dibuixa amb el `invertit` que es va triar EN AQUELL clic, no amb el d'ara: si compartissin
  // la bandera viva, invertir el segon costat giraria també el primer, que ja estava decidit.
  const arcsFixats = useMemo(() => {
    if (!segueixVora) return []
    const out = []
    for (let i = 0; i + 1 < puntsPom.length; i++) {
      const arc = arcEntre(puntsPom[i], puntsPom[i + 1], !!invertits[i])
      if (arc) out.push(arc)
    }
    return out
  }, [segueixVora, puntsPom, invertits, arcEntre])

  // La PRÈVIA: de l'últim punt fixat fins on és el cursor ara mateix. És el que substitueix
  // la tria d'arcs com a pas separat — es veu abans de clicar, i la tecla d'invertir el gira.
  const maxPunts = mode === 'pinca' ? 3 : mode === 'pom' ? ancoresPom.length : 2
  const previa = useMemo(() => {
    if (!segueixVora || !hover?.iman) return null
    if (puntsPom.length === 0 || puntsPom.length >= maxPunts) return null
    return arcEntre(puntsPom[puntsPom.length - 1], hover.iman.punt, arcInvertit)
  }, [segueixVora, hover, puntsPom, maxPunts, arcInvertit, arcEntre])

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
      {(() => {
        // `gran` va lligat al portal a posta: si els controls van a la barra del pare, són
        // part d'aquella barra i han de pesar com els seus botons. Dins del visor, en canvi,
        // són controls de vora i es queden compactes (és el que veu el tab del model).
        const controls = (
          <Controls
            t={t} zoom={zoom} capes={capes} presents={presents} gran={!!contenidorEines}
            onZoom={zoomBoto} onEncaixa={encaixar}
            onToggle={(c) => setCapes(prev => ({ ...prev, [c]: !prev[c] }))}
          />
        )
        return contenidorEines ? createPortal(controls, contenidorEines) : controls
      })()}

      <div
        ref={viewportRef}
        style={{
          border: '1px solid var(--line)', borderRadius: 8,
          background: 'var(--panel)', overflow: 'hidden',
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
                  || (imantant && (!pecaIman || piece.nom_block === pecaIman))}
                anotant={anotant}
                onClick={() => !anotant && onTriaPeca(
                  piece.nom_block === pecaSel ? '' : piece.nom_block)}
              />
            ))}

            {/* Els POMs ja ancorats, dibuixats com a COTES sobre la geometria que mesuren. */}
            {pieces.flatMap(piece => (piece.poms || []).map(pom => (
              <PomKonva
                key={`pom-${pom.id}`} piece={piece} pom={pom} zoom={zoom} unit={unit}
                sel={pomSel === pom.id}
                onSelecciona={onSeleccionaPom}
                onMou={onMouPom}
                anotant={anotant}
                maAlta={maAlta}
              />
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

            {/* Les PINÇES declarades: els dos costats i el vèrtex, amb glif propi. Es pinten
                sempre, com els trams: una pinça és el que explica per què una vora fa 32 cm i
                només en cus 30, i qui cus l'ha de veure sense haver de canviar de mode. */}
            {pinces.map(pinca => (
              <PincaKonva key={`pinca-${pinca.id}`} pinca={pinca} zoom={zoom} unit={unit} />
            ))}

            {/* A1 — LES PINCES PROPOSADES: un glif discret al vèrtex.
                Un cercle buit, petit, del color de la pinça: assenyala sense afirmar. Quan el
                cursor és a la seva fila, els dos costats s'encenen a ratlles — la mateixa gramàtica
                que les costures proposades (A2): ratlles = encara no és del patró. */}
            {pincesProposades.map(p => {
              const marcat = pincaProposadaRessaltada === p.clau
              return (
                <Group key={`pinca-prop-${p.clau}`} listening={false}>
                  {marcat && p.costats.map((pts, i) => (
                    pts.length >= 2 && (
                      <Line
                        key={i}
                        points={pts.flatMap(q => [q.x, -q.y])}
                        stroke={KONVA_COL.pinca}
                        strokeWidth={4.5 / zoom}
                        dash={[9 / zoom, 5 / zoom]}
                        lineCap="round"
                        perfectDrawEnabled={false}
                      />
                    )
                  ))}
                  {p.apex && (
                    <Circle
                      x={p.apex.x} y={-p.apex.y}
                      radius={(marcat ? 6 : 4) / zoom}
                      stroke={KONVA_COL.pinca}
                      strokeWidth={1.6 / zoom}
                      perfectDrawEnabled={false}
                    />
                  )}
                </Group>
              )
            })}

            {/* A2 — LA PROPOSTA SOTA EL CURSOR: els dos trams, encesos alhora.
                Amb els colors dels DOS COSTATS d'una costura (A i B), que és exactament el que
                la proposta diu que són. Es pinta només mentre el cursor és a la fila: una
                proposta no és res del patró —no s'ha decidit—, i deixar-la pintada l'ensenyaria
                com si ho fos. Es dibuixa a sobre de tot i no escolta el ratolí: és una resposta a
                la pregunta «quins dos trams?», no un objecte del taller. */}
            {propostaRessaltada && (
              <Group listening={false}>
                {['a', 'b'].map(costat => {
                  const tr = propostaRessaltada[costat]
                  const piece = tr && pieces.find(p => p.id === tr.piece_id)
                  if (!piece) return null
                  const pts = puntsDelSegment(piece, tr)
                  if (pts.length < 2) return null
                  return (
                    <Line
                      key={`prop-${costat}`}
                      points={pts.flatMap(p => [p.x, -p.y])}
                      stroke={costat === 'a' ? KONVA_COL.sewA : KONVA_COL.sewB}
                      strokeWidth={5 / zoom}
                      lineCap="round"
                      dash={[9 / zoom, 5 / zoom]}
                      perfectDrawEnabled={false}
                    />
                  )
                })}
              </Group>
            )}

            {/* L'OMBRA del que s'està reobrint: on era, mentre es diu on ha d'anar. */}
            {ombra && (ombra.punts || []).length >= 2 && (
              <Group listening={false} opacity={0.45}>
                <Line
                  points={ombra.punts.flatMap(p => [p.x, -p.y])}
                  stroke={KONVA_COL.tramSel}
                  strokeWidth={3 / zoom}
                  dash={[4 / zoom, 4 / zoom]}
                  lineCap="round" perfectDrawEnabled={false}
                />
                {[ombra.punts[0], ombra.punts[ombra.punts.length - 1]].map((p, i) => (
                  <Circle key={i} x={p.x} y={-p.y} r={midaGlif(5, 9, zoom)}
                          stroke={KONVA_COL.tramSel} strokeWidth={1.6 / zoom}
                          dash={[3 / zoom, 3 / zoom]} perfectDrawEnabled={false} />
                ))}
              </Group>
            )}

            {/* Els arcs JA FIXATS del gest en curs (el primer costat d'una pinça). Ja tenen el
                color del que seran: el clic que ve no els canviarà de naturalesa, només els
                assentarà. */}
            {arcsFixats.map((arc, i) => (
              <Line
                key={`fix-${i}`}
                points={arc.punts.flatMap(p => [p.x, -p.y])}
                stroke={mode === 'pinca' ? KONVA_COL.pinca : KONVA_COL.tram}
                strokeWidth={5 / zoom}
                lineCap="round" listening={false} perfectDrawEnabled={false}
              />
            ))}

            {/* La PRÈVIA DIRECCIONAL: l'arc que el cursor està assenyalant ara mateix. Es veu
                ABANS de clicar —amb la seva longitud— i la tecla d'invertir el gira.

                Es pinta del color del tram, no d'un altre: el que s'ensenya és el que es
                desarà, i canviar-li el to en desar el feia llegir com un objecte diferent. El
                que diu "això encara no és del patró" és el traç discontinu i translúcid —
                l'èmfasi—, i en desar-se només es solidifica. */}
            {previa && (
              <>
                <Line
                  points={previa.punts.flatMap(p => [p.x, -p.y])}
                  stroke={mode === 'pinca' ? KONVA_COL.pinca : KONVA_COL.tram}
                  strokeWidth={4 / zoom}
                  opacity={0.85}
                  dash={[9 / zoom, 5 / zoom]}
                  lineCap="round" listening={false} perfectDrawEnabled={false}
                />
                {(() => {
                  const mig = previa.punts[Math.floor(previa.punts.length / 2)]
                  if (!mig) return null
                  return (
                    <Text
                      x={mig.x} y={-mig.y - 16 / zoom}
                      text={formatLen(previa.longitud / 10, unit)}
                      fontSize={13 / zoom}
                      fill={mode === 'pinca' ? KONVA_COL.pinca : KONVA_COL.tram}
                      listening={false} perfectDrawEnabled={false}
                    />
                  )
                })()}
              </>
            )}

            {/* Mode POM: la mesura que s'està marcant, i l'imant sota el cursor.

                Amb DUES àncores la mesura és la línia entre els punts, i unir-los tots és
                dir la veritat. Amb TRES no ho és: `ref_a → ref_b → p` dibuixa una ela que
                no és cap caiguda. La forma honesta són dues línies —la de REFERÈNCIA entre
                les dues primeres àncores, i la perpendicular des del punt que hi cau— i
                això és el que es pinta. */}
            {mode === 'pom' && puntsPom.length >= 1 && (() => {
              const cursor = hover?.iman?.punt
              if (ancoresPom.length <= 2) {
                return (
                  <Line
                    points={[
                      ...puntsPom.flatMap(p => [p.x, -p.y]),
                      ...(puntsPom.length === 1 && cursor ? [cursor.x, -cursor.y] : []),
                    ]}
                    stroke={KONVA_COL.pom}
                    strokeWidth={2 / zoom}
                    dash={[5 / zoom, 3 / zoom]}
                    listening={false}
                    perfectDrawEnabled={false}
                  />
                )
              }
              // Amb tres àncores: la referència es tanca amb el cursor mentre es marca la
              // segona; després, el cursor (o el punt ja fixat) penja de la línia.
              const refA = puntsPom[0]
              const refB = puntsPom[1] || (puntsPom.length === 1 ? cursor : null)
              const cau = puntsPom[2] || (puntsPom.length === 2 ? cursor : null)
              const peu = peuPerpendicular(refA, refB, cau)
              return (
                <>
                  {refB && (
                    <Line
                      points={[refA.x, -refA.y, refB.x, -refB.y]}
                      stroke={KONVA_COL.pom}
                      strokeWidth={1 / zoom}
                      dash={[2 / zoom, 4 / zoom]}
                      listening={false}
                      perfectDrawEnabled={false}
                    />
                  )}
                  {peu && cau && (
                    <Line
                      points={[peu.x, -peu.y, cau.x, -cau.y]}
                      stroke={KONVA_COL.pom}
                      strokeWidth={2 / zoom}
                      dash={[5 / zoom, 3 / zoom]}
                      listening={false}
                      perfectDrawEnabled={false}
                    />
                  )}
                </>
              )
            })()}

            {/* EL PUNT FIXAT (T3a): marcador gran, halo, i l'etiqueta que no marxa fins que
                el gest s'acaba. Abans era un cercle de 5 px que es perdia entre els vèrtexs
                del patró, i a mig gest ja no se sabia quin punt s'havia clicat. Un punt que
                l'usuari ha decidit ha de ser el més visible de la pantalla. */}
            {imantant && puntsPom.map((p, i) => {
              const r = midaGlif(7, 13, zoom)
              const col = mode === 'pinca' ? KONVA_COL.pinca : KONVA_COL.pom
              return (
                <Group key={`sel-${i}`} listening={false}>
                  <Circle x={p.x} y={-p.y} r={r * 2.1} fill={col} opacity={0.16}
                          perfectDrawEnabled={false} />
                  <Circle x={p.x} y={-p.y} r={r} fill={col} stroke={KONVA_COL.bg}
                          strokeWidth={1.6 / zoom} perfectDrawEnabled={false} />
                  <Text
                    x={p.x + r * 1.6} y={-p.y - r * 2.4}
                    text={etiquetaPunt(t, mode, i, ancoresPom)}
                    fontSize={13 / zoom} fontStyle="bold" fill={col}
                    perfectDrawEnabled={false}
                  />
                </Group>
              )
            })}

            {/* L'imant sota el cursor: halo, perquè es vegi QUÈ es clicarà abans de clicar. */}
            {imantant && hover?.iman && (
              <Group listening={false}>
                <Circle
                  x={hover.iman.punt.x} y={-hover.iman.punt.y}
                  r={midaGlif(8, 15, zoom)}
                  fill={mode === 'pinca' ? KONVA_COL.pinca : KONVA_COL.pom}
                  opacity={0.18} perfectDrawEnabled={false}
                />
                <Circle
                  x={hover.iman.punt.x} y={-hover.iman.punt.y}
                  r={midaGlif(6, 11, zoom)}
                  stroke={mode === 'pinca' ? KONVA_COL.pinca : KONVA_COL.pom}
                  strokeWidth={2 / zoom} perfectDrawEnabled={false}
                />
              </Group>
            )}
          </Layer>
        </Stage>
      </div>

      <BarraEstat
        t={t} hover={hover} pieces={pieces} pecaSel={pecaSel} colocant={colocant}
        unit={unit} potInvertir={!!previa && !previa.unic}
      />
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

/**
 * Un POM ancorat, dibuixat com el que és: una COTA.
 *
 * Fins ara es dibuixava la línia de la mesura, damunt de la geometria i prou. Una cota de
 * CAD no és això: és una línia paral·lela, separada de la peça, amb dos TESTIMONIS
 * puntejats que la lliguen als punts que acota. La diferència no és estètica — amb tres
 * mesures que comparteixen un extrem, les línies s'apilen sobre el mateix vèrtex i ja no
 * es pot llegir cap.
 *
 * · recta i cota d'eix → la cota va paral·lela a l'eix de la mesura.
 * · caiguda → paral·lela a la caiguda, i el testimoni de baix surt de la línia de referència
 *   (el peu de la perpendicular hi seu).
 * · longitud per vora → la cota és la VORA desplaçada, no la corda: acotar amb una recta una
 *   magnitud que ressegueix una corba seria dibuixar una altra xifra.
 *
 * **Es pot arrossegar**, i el desplaçament es desa (`cota_offset_mm`). El drag va CONSTRET a
 * la normal: una cota de CAD s'allunya i s'apropa, no llisca — i així el que es desa és un
 * sol número amb sentit geomètric, no una posició absoluta que caducaria el dia que algú
 * recol·loqui una àncora.
 */
function PomKonva({
  piece, pom, zoom, unit, sel = false, onSelecciona, onMou,
  anotant = false, maAlta = false,
}) {
  const boto = useRef(0)
  const g = geometriaDeLaCota(piece, pom)
  if (!g) return null

  const { origens, cota, normal } = g
  const cap = cota[0]
  const cua = cota[cota.length - 1]
  const mig = cota[Math.floor(cota.length / 2)]

  // 🚨 **MENTRE S'ANOTA, LA COTA NO ESCOLTA RES**, i és la llei del fitxer: el tram declarat
  // fa `listening={mode === 'sew' && ...}` i `PecaKonva` fa `!anotant && onTriaPeca(...)`.
  // Sense això, el clic de l'IMANT —que és del `Stage`, no d'aquest shape— quedava mort a
  // menys de 12 px de qualsevol cota: el patronista veia el marcador d'imant encès i el clic
  // no ancorava res. I a offset 0, que és on neixen totes, la cota seu DAMUNT de les seves
  // pròpies àncores; amb `metode='vora'`, damunt de tot un tros de contorn.
  //
  // `maAlta` (espai premut o pan en curs) hi entra pel mateix motiu: la sortida d'emergència
  // del pan no pot ser justament el que es queda enganxat a una cota.
  const viva = !anotant && !maAlta
  const arrossegable = !!onMou && viva
  // La tinta del TEXT no canvia amb la selecció: `tramSel` (#fb8500) sobre blanc mesura
  // 2,48:1 i no arriba ni al llindar de component. L'èmfasi el porten la línia i els punts,
  // que són traç i no lletra.
  const col = sel ? KONVA_COL.tramSel : KONVA_COL.pom

  // El drag es projecta sobre la normal: el que arriba al servidor és quant s'ha separat la
  // cota de la mesura, no on ha anat a parar el ratolí.
  const nomesNormal = (posa) => {
    const d = posa.x * normal.x + (-posa.y) * normal.y
    return { x: normal.x * d, y: -(normal.y * d) }
  }

  return (
    <Group
      draggable={arrossegable}
      onDragMove={arrossegable ? (e) => {
        const p = nomesNormal({ x: e.target.x(), y: e.target.y() })
        e.target.position(p)
      } : undefined}
      onDragEnd={arrossegable ? (e) => {
        const d = e.target.x() * normal.x + (-e.target.y()) * normal.y
        // El grup torna a l'origen: la posició nova arriba per `cota_offset_mm` quan el
        // servidor confirma. Deixar-l'hi la sumaria dues vegades al render següent.
        e.target.position({ x: 0, y: 0 })
        if (Math.abs(d) > 1e-6) onMou(pom, (pom.cota_offset_mm || 0) + d)
      } : undefined}
      onDragStart={arrossegable ? (e) => {
        // Konva arrossega amb el botó del mig també (`dragButtons` per defecte és [0, 1]).
        // El del mig és el pan del Taller: si comença damunt d'una cota, ha de panejar.
        if (boto.current !== 0) e.target.stopDrag()
      } : undefined}
      onMouseDown={onSelecciona ? (e) => {
        boto.current = e.evt?.button ?? 0
        if (boto.current !== 0) return    // el pan del botó del mig ha d'arribar al Stage
        e.cancelBubble = true
      } : undefined}
      onClick={onSelecciona ? (e) => {
        if ((e.evt?.button ?? 0) !== 0) return
        e.cancelBubble = true
        onSelecciona(pom)
      } : undefined}
      onTap={onSelecciona ? (e) => { e.cancelBubble = true; onSelecciona(pom) } : undefined}
      onMouseEnter={arrossegable ? (e) => {
        const c = e.target.getStage()?.container()
        if (c) c.style.cursor = 'move'      // res no deia que això s'arrossegués
      } : undefined}
      onMouseLeave={arrossegable ? (e) => {
        const c = e.target.getStage()?.container()
        if (c) c.style.cursor = ''
      } : undefined}
      listening={viva && !!(onSelecciona || onMou)}
    >
      {/* TESTIMONIS: del punt acotat fins una mica més enllà de la línia de cota, puntejats
          i fins, com al CAD. Només quan la cota s'ha separat: a offset zero seria una línia
          de longitud zero sobre ella mateixa. */}
      {origens.map((o, i) => {
        const fi = i === 0 ? cap : cua
        if (Math.hypot(fi.x - o.x, fi.y - o.y) < 1e-6) return null
        return (
          <Line
            key={`t${i}`}
            points={[o.x, -o.y, fi.x, -fi.y]}
            stroke={col} strokeWidth={0.8 / zoom}
            dash={[1.5 / zoom, 2.5 / zoom]}
            listening={false} perfectDrawEnabled={false}
          />
        )
      })}

      {/* La LÍNIA DE COTA. Amb `hitStrokeWidth` generós: una línia d'1,8 px no es pot
          agafar amb el ratolí, i una cota que s'ha d'encertar al píxel no és arrossegable. */}
      <Line
        points={cota.flatMap(p => [p.x, -p.y])}
        stroke={col} strokeWidth={(sel ? 2.6 : 1.8) / zoom}
        hitStrokeWidth={Math.max(12 / zoom, 4)}
        perfectDrawEnabled={false}
      />
      {[cap, cua].map((p, i) => (
        <Circle key={i} x={p.x} y={-p.y} r={3 / zoom} fill={col}
                listening={false} perfectDrawEnabled={false} />
      ))}
      <Text
        x={mig.x} y={-mig.y - 14 / zoom}
        text={`${pom.pom_code}${pom.valor_mesurat_cm != null
          ? ` ${formatLen(pom.valor_mesurat_cm, unit)}` : ''}`}
        fontSize={11 / zoom}
        fill={col}
        listening={false}
        perfectDrawEnabled={false}
      />
    </Group>
  )
}

/** L'etiqueta d'un punt fixat: la de la seva ÀNCORA, o A → Vèrtex → B si és una pinça.
 *
 * Deia «A» i «B» per a tot el que no fos una pinça, i amb tres àncores el tercer clic
 * quedava etiquetat «B» com el segon: dos punts diferents amb el mateix rètol, mentre els
 * xips del selector, tres pams més amunt, els anomenaven correctament.
 */
function etiquetaPunt(t, mode, i, ancores) {
  if (mode === 'pinca') {
    return t(['pattern.taller.pt_a', 'pattern.taller.pt_vertex', 'pattern.taller.pt_b'][i]
      || 'pattern.taller.pt_b')
  }
  return t(`pattern.taller.pt_${ancores[i] || 'b'}`)
}

/**
 * Una PINÇA declarada, sobre la geometria.
 *
 * Els dos costats es pinten com el que són —dos trams de la mateixa vora— i el VÈRTEX porta
 * glif propi: un triangle. No és decoració. Un vèrtex de pinça és el punt que explica per què
 * la vora fa 32.1 cm i només n'aporta 29.8 a la costura, i qui miri la peça l'ha de poder
 * trobar sense obrir cap panell.
 */
function PincaKonva({ pinca, zoom, unit }) {
  const g = midaGlif(6, 12, zoom)
  const apex = pinca.apex
  return (
    <Group listening={false}>
      {pinca.costats.map((punts, i) => (
        <Line
          key={i}
          points={punts.flatMap(p => [p.x, -p.y])}
          stroke={KONVA_COL.pinca} strokeWidth={3.4 / zoom}
          lineCap="round" perfectDrawEnabled={false}
        />
      ))}
      {apex && (
        <>
          {/* El triangle del vèrtex, apuntant amunt. Tancat i ple: es veu de lluny. */}
          <Line
            points={[
              apex.x, -apex.y - g * 1.25,
              apex.x - g, -apex.y + g * 0.75,
              apex.x + g, -apex.y + g * 0.75,
            ]}
            closed
            fill={KONVA_COL.pinca}
            stroke={KONVA_COL.bg} strokeWidth={1.2 / zoom}
            perfectDrawEnabled={false}
          />
          <Text
            x={apex.x + g * 1.5} y={-apex.y - g * 2}
            text={`${pinca.nom} · ${formatLen(pinca.cm, unit)}`}
            fontSize={12 / zoom} fill={KONVA_COL.pinca}
            perfectDrawEnabled={false}
          />
        </>
      )}
    </Group>
  )
}

/** La polilínia que una recepta de mesura RECORRE. La longitud d'això ÉS el valor.
 *
 * Una recepta ORTOGONAL no porta `a`/`b` sinó `ref_a`/`ref_b`/`p`, i una de PROJECCIÓ acota
 * sobre un eix: llegint-hi només les dues primeres claus el POM sortia amb la llista buida i
 * **no es dibuixava gens**. La lectura natural d'això és «no s'ha desat».
 *
 * ⚠️ Per a la caiguda i per a la cota, aquesta línia NO és el que la capa FTT-POM exportarà
 * —cap dels dos modes entra encara a la niada (`adapters.pom_specs`)—, a diferència de la
 * recta i la longitud per vora.
 */
function puntsDeLaMesura(piece, pom) {
  const def = pom.definicio_mesura || {}
  const perId = new Map()
  for (const b of piece.boundaries || []) {
    for (const p of b.points || []) perId.set(p.id, p)
  }

  if (def.mode === 'ortogonal') {
    const p = perId.get(def.p)
    const peu = peuPerpendicular(perId.get(def.ref_a), perId.get(def.ref_b), p)
    return peu && p ? [peu, p] : []
  }

  const a = perId.get(def.a) || perId.get(def.landmark)
  const b = perId.get(def.b)
  if (!a || !b) return []

  if (def.mode === 'projeccio') return puntsDeLaCotaProjeccio(a, b, def.eix || '')

  // LONGITUD PER VORA: la mesura ressegueix la vora, i dibuixar-hi la CORDA seria dibuixar
  // una altra magnitud. S'agafa l'arc CURT entre els dos punts, que és el que el motor
  // mesura (`engine/measure._cami_per_vora`).
  if (pom.metode === 'vora') {
    for (const boundary of piece.boundaries || []) {
      const pts = boundary.points || []
      const ia = pts.findIndex(q => q.id === a.id)
      const ib = pts.findIndex(q => q.id === b.id)
      if (ia < 0 || ib < 0) continue
      const arc = arcsEntrePunts(boundary, ia, ib)[0]
      if (arc?.punts?.length >= 2) return arc.punts
    }
    // Cap vora no passa pels dos punts. El servidor tampoc no ho pot mesurar i deixa el
    // valor a null (`engine/measure._cami_per_vora`): dibuixar-hi la corda seria pintar una
    // magnitud que ningú no ha demanat i que no és la que la fila diu.
    return []
  }

  return [a, b]
}

/**
 * La COTA d'un POM: què es dibuixa i on.
 *
 * Una cota de CAD no és la línia de la mesura: és una línia PARAL·LELA, separada, amb dos
 * testimonis que la lliguen als punts que acota. Per això aquí surten tres coses i no una:
 * els ORÍGENS (d'on surten els testimonis), la línia de COTA (ja desplaçada) i la NORMAL
 * (la direcció en què el desplaçament es compta, que és la que el drag ha de respectar).
 *
 * El desplaçament és `cota_offset_mm` i és PRESENTACIÓ: no toca ni pot tocar el valor.
 * A zero, la cota seu sobre la mesura —exactament on es dibuixava abans que això existís.
 */
function geometriaDeLaCota(piece, pom) {
  const base = puntsDeLaMesura(piece, pom)
  if (base.length < 2) return null
  const normal = normalDe(base[0], base[base.length - 1])
  if (!normal) return null
  const off = pom.cota_offset_mm || 0
  return {
    origens: [base[0], base[base.length - 1]],
    cota: desplacaPolilinia(base, off),
    normal,
  }
}

function PecaKonva({ piece, zoom, sel, atenuada, visible, mostraPunts, anotant, onClick }) {
  // Els traços es dibuixen amb gruix CONSTANT a pantalla: si el gruix escalés amb el
  // zoom, en allunyar-se el patró es convertiria en una taca negra i en apropar-se
  // desapareixeria.
  const gruix = (base) => base / zoom

  // Els GIRS manen i les CORBES flueixen (W4b/T3b). La jerarquia no és estètica: un punt de
  // gir és una cantonada que el patronista reconeix, que es grada, i que és l'únic que es pot
  // triar com a extrem d'un tram o com a vèrtex d'una pinça. Un punt de corba no és frontera
  // de res. Pintar-los igual —com es feia— era fer buscar l'agulla al paller cada cop que
  // calia apuntar a un vèrtex. Ara el gir creix quan t'hi apropes i la corba es queda petita.
  const g = midaGlif(4.6, 9, zoom)        // GIR: es pot encertar
  const gc = midaGlif(2.4, 4, zoom)       // CORBA: hi és, i no fa nosa

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

      {/* Glifs de punt: quadrat verd = GIR (es grada, i és el que es pot triar) · x groga =
          CORBA (flueix). La distinció no és decorativa: és la llei que governa què es mou a
          l'escalat, i qui es pot clicar. El gir porta contorn blanc perquè no es fongui amb
          la línia quan hi cau just a sobre. */}
      {mostraPunts && piece.boundaries.flatMap(b =>
        (visible(b.role) ? b.points : []).map((p, i) => (
          p.tipus === 'turn' ? (
            <Rect
              key={`t-${piece.id}-${b.index}-${i}`}
              x={p.x - g / 2} y={-p.y - g / 2} width={g} height={g}
              fill={KONVA_COL.turn}
              stroke={KONVA_COL.bg} strokeWidth={1 / zoom}
              listening={false} perfectDrawEnabled={false}
            />
          ) : p.tipus === 'curve' ? (
            <Group key={`c-${piece.id}-${b.index}-${i}`} listening={false} opacity={0.7}>
              <Line points={[p.x - gc / 2, -p.y - gc / 2, p.x + gc / 2, -p.y + gc / 2]}
                    stroke={KONVA_COL.curve} strokeWidth={gruix(0.8)} perfectDrawEnabled={false} />
              <Line points={[p.x - gc / 2, -p.y + gc / 2, p.x + gc / 2, -p.y - gc / 2]}
                    stroke={KONVA_COL.curve} strokeWidth={gruix(0.8)} perfectDrawEnabled={false} />
            </Group>
          ) : null
        ))
      )}

      {visible('notch') && piece.notches.map((n, i) => (
        <Rect
          key={`n-${piece.id}-${i}`}
          x={n.x - g * 0.6} y={-n.y - g * 0.6} width={g * 1.2} height={g * 1.2}
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

function Controls({ t, zoom, capes, presents, gran = false, onZoom, onEncaixa, onToggle }) {
  // Les capes que el fitxer NO porta no s'ofereixen: un toggle que no fa res és pitjor
  // que no tenir-lo, perquè fa pensar que la capa hi és i està amagada.
  const TOGGLES = [
    ['cut', 'ti-line'], ['sew', 'ti-needle-thread'], ['internal', 'ti-line-dashed'],
    ['mirror', 'ti-flip-horizontal'], ['notch', 'ti-scissors'], ['grain', 'ti-arrow-narrow-up'],
  ]
  const boto = {
    background: 'var(--panel)', border: '1px solid var(--line)',
    cursor: 'pointer', display: 'flex', alignItems: 'center',
    ...(gran ? METRICA_EINA : METRICA_EINA_COMPACTA),
  }
  const encesa = (on) => ({
    ...boto,
    background: on ? 'var(--sel)' : 'var(--panel)',
    borderColor: on ? 'var(--gold)' : 'var(--line)',
    opacity: on ? 1 : 0.55,
  })

  const contingut = (
    <>
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
        fontSize: gran ? 'var(--fs-body)' : 'var(--fs-caption)', color: 'var(--text-soft)',
        fontFamily: 'var(--mono)', minWidth: 52,
      }}>
        {(zoom * 100).toFixed(0)}%
      </span>

      <span style={{
        width: 1, height: gran ? 22 : 18, background: 'var(--line)', margin: '0 0.2rem',
      }} />

      {TOGGLES.filter(([capa]) => presents.has(capa)).map(([capa, icona]) => (
        <button
          key={capa}
          onClick={() => onToggle(capa)}
          aria-pressed={capes[capa]}
          style={encesa(capes[capa])}
        >
          <i className={`ti ${icona}`} />
          {t(`pattern.layer.${capa}`)}
        </button>
      ))}
      <button
        onClick={() => onToggle('punts')}
        aria-pressed={capes.punts}
        style={encesa(capes.punts)}
      >
        <i className="ti ti-point" />
        {t('pattern.layer.points')}
      </button>
    </>
  )

  // Portalat a la barra del pare: SENSE contenidor propi, perquè els botons siguin fills
  // directes d'aquella fila flex i hi facin `wrap` un a un com els del pare. Un div enmig
  // els convertiria en un sol bloc que salta de línia tot junt.
  if (gran) return contingut

  return (
    <div style={{
      display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center', flexShrink: 0,
    }}>
      {contingut}
    </div>
  )
}

function BarraEstat({ t, hover, pieces, pecaSel, colocant, unit, potInvertir }) {
  const cm = (mm) => formatLenNum(mm / 10, unit)
  const peca = pecaSel ? pieces.find(p => p.nom_block === pecaSel) : null
  const perimetre = peca
    ? longitudVora((peca.boundaries || []).find(b => b.role === 'cut') || { points: [] })
    : 0

  return (
    <div style={{
      display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center',
      fontSize: 'var(--fs-caption)', color: 'var(--text-soft)',
      fontFamily: 'var(--mono)', minHeight: 18, flexShrink: 0,
    }}>
      {/* Col·locant, la pista de la mà NO substitueix les coordenades: mentre es marca un
          punt és quan més falta fan. Van juntes. */}
      {colocant && (
        <span style={{ color: 'var(--gold)' }}>
          <i className="ti ti-hand-move" /> {t('pattern.taller.pan_hint')}
        </span>
      )}
      {/* La tecla d'invertir es diu quan serveix, que és mentre l'arc es previsualitza. */}
      {potInvertir && (
        <span style={{ color: 'var(--gold)' }}>
          <i className="ti ti-switch-horizontal" /> {t('pattern.taller.arc_flip_hint')}
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
          {t('pattern.selected_piece', { peca: etiquetaPeca(peca), cm: cm(perimetre) })}
        </span>
      )}
    </div>
  )
}
