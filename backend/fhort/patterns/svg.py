"""Render SVG del patró, fet des del model geomètric intern.

**Per què no matplotlib** (decisió presa amb l'evidència de la diagnosi S0-B6): el DXF
real només conté polilínies, línies i punts — cap arc, cap spline, cap corba
paramètrica. Les "corbes" del patró són polilínies de punts densos. Renderitzar-ho és
traduir punt a punt a un `<path d="M…L…">`, i per fer això matplotlib arrossegaria
numpy, contourpy, kiwisolver i companyia (i l'extra `draw` d'ezdxf, encara pitjor: també
PySide6 i PyMuPDF). Cent línies de codi propi contra cinquanta megues de dependència
per dibuixar rectes.

I hi ha una raó millor que el pes: l'SVG surt del NOSTRE model, no del DXF cru. És el
mateix que S4 ensenyarà i el mateix que S7 escalarà. Si el render llegís el fitxer pel
seu compte, hi hauria dues interpretacions del patró en circulació.

**Això és un DOCUMENT, no una peça d'interfície.** Per això la paleta és una constant
fixa aquí sota i no fa servir tokens CSS: un patró tècnic ha de sortir igual a la
pantalla, a la impressora i d'aquí a cinc anys. Els tokens són per a la UI, que canvia
de tema; això no.
"""
from xml.sax.saxutils import escape

from .engine.geometry import LayerRole, PatternDocument, PieceData

#: PALETA DE DOCUMENT — fixa i documentada. No són tokens i no han de ser-ho.
#: Els colors segueixen la convenció de la indústria: el tall en negre (és el que es
#: retalla), el cosit blau, les internes en gris (informatives), i els piquets en
#: vermell perquè un piquet mal posat és un error car.
PALETA = {
    LayerRole.CUT: '#111111',
    LayerRole.SEW: '#1f6feb',
    LayerRole.INTERNAL: '#8b949e',
    LayerRole.NOTCH: '#d1242f',
    LayerRole.GRAIN: '#1a7f37',
    LayerRole.MIRROR: '#8250df',
    LayerRole.UNKNOWN: '#bbbbbb',
}
COLOR_TURN = '#1a7f37'      # punt de gir: es grada
COLOR_CURVE = '#bf8700'     # punt de corba: flueix
COLOR_FONS = '#ffffff'
COLOR_POM = '#bf3989'       # la nostra capa, quan n'hi ha

GRUIX_CUT = 1.2
GRUIX_ALTRES = 0.6
RADI_PUNT = 1.6
MARGE_MM = 20.0


def render_document(doc: PatternDocument, piece_name: str = '') -> str:
    """SVG del conjunt, o d'una sola peça si es demana.

    Les coordenades van en mil·límetres i l'eix Y es capgira: al DXF creix cap amunt i a
    l'SVG cap avall. Sense això, el patró surt del revés i no ho sembla.
    """
    peces = [p for p in doc.pieces if not piece_name or p.nom_block == piece_name]
    if not peces:
        return _svg_buit('Cap peça per dibuixar.')

    minx, miny, maxx, maxy = _bounding_box(peces)
    ample = (maxx - minx) + 2 * MARGE_MM
    alt = (maxy - miny) + 2 * MARGE_MM

    cos = []
    for piece in peces:
        cos.append(_render_piece(piece))

    return _svg_wrapper(
        contingut='\n'.join(cos),
        # El viewBox es dona en coordenades JA capgirades (v. _y).
        viewbox=f'{minx - MARGE_MM:.2f} {-maxy - MARGE_MM:.2f} {ample:.2f} {alt:.2f}',
        ample=ample,
        alt=alt,
    )


def _render_piece(piece: PieceData) -> str:
    parts = [f'<g id="{escape(piece.nom_block)}">']

    for boundary in piece.boundaries:
        if len(boundary.points) < 2:
            continue
        color = PALETA.get(boundary.role, PALETA[LayerRole.UNKNOWN])
        gruix = GRUIX_CUT if boundary.role is LayerRole.CUT else GRUIX_ALTRES
        d = _path_data(boundary.points, boundary.closed)
        dash = ' stroke-dasharray="4 2"' if boundary.role is LayerRole.SEW else ''
        parts.append(
            f'<path d="{d}" fill="none" stroke="{color}" '
            f'stroke-width="{gruix}" stroke-linejoin="round"{dash}/>'
        )

    # Els punts, amb la seva semàntica: gir (es grada) i corba (flueix).
    for boundary in piece.boundaries:
        for p in boundary.points:
            color = {'turn': COLOR_TURN, 'curve': COLOR_CURVE}.get(p.kind.value)
            if not color:
                continue
            parts.append(
                f'<circle cx="{p.x:.2f}" cy="{_y(p.y):.2f}" r="{RADI_PUNT}" fill="{color}"/>'
            )

    for n in piece.notches:
        c = PALETA[LayerRole.NOTCH]
        parts.append(
            f'<rect x="{n.x - RADI_PUNT:.2f}" y="{_y(n.y) - RADI_PUNT:.2f}" '
            f'width="{RADI_PUNT * 2}" height="{RADI_PUNT * 2}" fill="{c}"/>'
        )

    if piece.grain:
        g = piece.grain
        parts.append(
            f'<line x1="{g.x1:.2f}" y1="{_y(g.y1):.2f}" x2="{g.x2:.2f}" y2="{_y(g.y2):.2f}" '
            f'stroke="{PALETA[LayerRole.GRAIN]}" stroke-width="{GRUIX_ALTRES}"/>'
        )

    for pom in piece.poms:
        if len(pom.punts_ancora) >= 2:
            d = 'M ' + ' L '.join(
                f'{x:.2f},{_y(y):.2f}' for x, y in pom.punts_ancora
            )
            parts.append(
                f'<path d="{d}" fill="none" stroke="{COLOR_POM}" stroke-width="{GRUIX_ALTRES}" '
                f'stroke-dasharray="2 2"/>'
            )

    parts.append('</g>')
    return '\n'.join(parts)


def _path_data(points, closed: bool) -> str:
    d = 'M ' + ' L '.join(f'{p.x:.2f},{_y(p.y):.2f}' for p in points)
    return d + ' Z' if closed else d


def _y(y: float) -> float:
    """DXF creix cap amunt; SVG cap avall."""
    return -y


def _bounding_box(peces) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for p in peces:
        for b in p.boundaries:
            for q in b.points:
                xs.append(q.x)
                ys.append(q.y)
        for n in p.notches:
            xs.append(n.x)
            ys.append(n.y)
    if not xs:
        return (0.0, 0.0, 100.0, 100.0)
    return (min(xs), min(ys), max(xs), max(ys))


def _svg_wrapper(contingut: str, viewbox: str, ample: float, alt: float) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}" '
        f'width="{ample:.0f}mm" height="{alt:.0f}mm">\n'
        f'<rect x="-100000" y="-100000" width="200000" height="200000" fill="{COLOR_FONS}"/>\n'
        f'{contingut}\n'
        f'</svg>\n'
    )


def _svg_buit(missatge: str) -> str:
    return _svg_wrapper(
        f'<text x="10" y="20" font-size="12" fill="#666">{escape(missatge)}</text>',
        viewbox='0 0 200 40', ample=200, alt=40,
    )
