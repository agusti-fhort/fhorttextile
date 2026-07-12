import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Stage, Layer, Line, Rect, Group, Arrow } from 'react-konva'
import { useTranslation } from 'react-i18next'
import {
  bboxDePeces, capesPresents, escalaPerCabre, longitudVora,
  puntsPerKonva, tramMesProper,
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
const KONVA_COL = {
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
}

const ZOOM_MIN = 0.02
const ZOOM_MAX = 8
const ZOOM_STEP = 1.15

const GLIF = 3.2          // mida dels glifs de punt, en px de contingut
const ALCADA = 560

const clampZoom = (v) => Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, v))

export default function PatternViewer({ pieces, pecaSel, onTriaPeca }) {
  const { t } = useTranslation()
  const viewportRef = useRef(null)
  const stageRef = useRef(null)

  const [mida, setMida] = useState({ w: 800, h: ALCADA })
  const [zoom, setZoom] = useState(1)
  const [pos, setPos] = useState({ x: 0, y: 0 })
  const [hover, setHover] = useState(null)      // { xMm, yMm, tram }
  const [capes, setCapes] = useState({
    cut: true, sew: true, internal: true, mirror: true,
    notch: true, grain: true, punts: true,
  })

  const bbox = useMemo(() => bboxDePeces(pieces), [pieces])
  const presents = useMemo(() => capesPresents(pieces), [pieces])

  // ── enquadrar ────────────────────────────────────────────────────────────
  const encaixar = useCallback(() => {
    const el = viewportRef.current
    if (!el) return
    const w = el.clientWidth
    const h = ALCADA
    const z = clampZoom(escalaPerCabre(bbox, w, h))
    setZoom(z)
    // El contingut es dibuixa en mm amb l'eix Y capgirat: el centrem al viewport.
    setPos({
      x: w / 2 - ((bbox.minX + bbox.maxX) / 2) * z,
      y: h / 2 + ((bbox.minY + bbox.maxY) / 2) * z,
    })
    setMida({ w, h })
  }, [bbox])

  useEffect(() => { encaixar() }, [encaixar])

  useEffect(() => {
    const onResize = () => encaixar()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [encaixar])

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

  // ── hover: on és el cursor i quin tram de vora hi ha a sota ──────────────
  const onMouseMove = () => {
    const stage = stageRef.current
    if (!stage) return
    const p = stage.getPointerPosition()
    if (!p) { setHover(null); return }
    const xMm = (p.x - pos.x) / zoom
    const yMm = -(p.y - pos.y) / zoom      // desfem el capgirat de l'eix Y
    const tram = tramMesProper(pieces, xMm, yMm, 12 / zoom)
    setHover({ xMm, yMm, tram })
  }

  const visible = (capa) => capes[capa] && presents.has(capa)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <Controls
        t={t} zoom={zoom} capes={capes} presents={presents}
        onZoom={zoomBoto} onEncaixa={encaixar}
        onToggle={(c) => setCapes(prev => ({ ...prev, [c]: !prev[c] }))}
      />

      <div
        ref={viewportRef}
        style={{
          border: '1px solid var(--border)', borderRadius: 8,
          background: 'var(--white)', overflow: 'hidden', cursor: 'grab',
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
          draggable
          onWheel={onWheel}
          onMouseMove={onMouseMove}
          onMouseLeave={() => setHover(null)}
          onDragEnd={(e) => setPos({ x: e.target.x(), y: e.target.y() })}
        >
          <Layer>
            {pieces.map(piece => (
              <PecaKonva
                key={piece.id}
                piece={piece}
                zoom={zoom}
                sel={piece.nom_block === pecaSel}
                hiHaSeleccio={!!pecaSel}
                visible={visible}
                mostraPunts={capes.punts}
                onClick={() => onTriaPeca(piece.nom_block === pecaSel ? '' : piece.nom_block)}
              />
            ))}
          </Layer>
        </Stage>
      </div>

      <BarraEstat t={t} hover={hover} pieces={pieces} pecaSel={pecaSel} />
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

function PecaKonva({ piece, zoom, sel, hiHaSeleccio, visible, mostraPunts, onClick }) {
  // Els traços es dibuixen amb gruix CONSTANT a pantalla: si el gruix escalés amb el
  // zoom, en allunyar-se el patró es convertiria en una taca negra i en apropar-se
  // desapareixeria.
  const gruix = (base) => base / zoom
  const g = GLIF / zoom

  const atenuada = hiHaSeleccio && !sel

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
    <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
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

function BarraEstat({ t, hover, pieces, pecaSel }) {
  const cm = (mm) => (mm / 10).toFixed(1)
  const peca = pecaSel ? pieces.find(p => p.nom_block === pecaSel) : null
  const perimetre = peca
    ? longitudVora((peca.boundaries || []).find(b => b.role === 'cut') || { points: [] })
    : 0

  return (
    <div style={{
      display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center',
      fontSize: 'var(--fs-caption)', color: 'var(--text-muted)',
      fontFamily: 'var(--mono)', minHeight: 18,
    }}>
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
