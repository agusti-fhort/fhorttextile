"""Reader DXF-AAMA → model geomètric intern.

Llegeix els fitxers que els CAD de patronatge escupen de debò, no els que l'estàndard
descriu. Les diferències, totes verificades contra material real (AMELIA, PolyPattern
11.0.1):

  · **Les capes no es declaren.** La taula LAYERS només porta '0' i 'Defpoints'; els
    codis AAMA (1, 2, 3, 4, 7, 8, 15…) apareixen només com a atribut de les entitats.
  · **La `HEADER` pot ser buida** → sense `$INSUNITS` ni `$MEASUREMENT`. Les unitats
    s'han de deduir, i ha de constar que s'han deduït (`UnitsFingerprint`).
  · **Els punts de gir i de corba no són vèrtexs**: són POINT de les capes 2 i 3 que
    **seuen damunt** dels vèrtexs i els classifiquen (100% de coincidència al material
    real). Sense aquest creuament, un contorn és una llista de números sense semàntica.
  · **Els contorns no fan servir el flag de tancament**: repeteixen el primer vèrtex al
    final. El tancament es decideix per geometria.
  · **La regla de grading viatja com a TEXT** ('# 1') assegut sobre el punt que
    governa. És el lligam entre la geometria i el RUL (`RULE: DELTA 1`).
  · **Hi ha capes que no són a l'estàndard** (la 15 d'AMELIA porta l'autoria). No són
    un error: es preserven a l'empremta i el fitxer es llegeix igual.

Res del que no hi és s'assumeix: si no hi ha línia de cosit (capa 14), `has_sew` és
False i qui vulgui derivar-ne el tall a S7 sabrà que no té d'on.
"""
from __future__ import annotations

import io
from collections import Counter
from typing import Iterable, Optional

import ezdxf
from ezdxf import recover
from ezdxf.document import Drawing

from .errors import ParseIssue, PatternParseError
from .ftt_pom_layer import FTT_POM_LAYER, build_poms, collect_ftt_entities
from .geometry import (
    AAMA_LAYER_ROLES,
    BoundaryData,
    Confidence,
    Fingerprint,
    FoldData,
    GrainLineData,
    LayerRole,
    NotchData,
    PatternDocument,
    PieceData,
    PieceMetadata,
    PointData,
    PointKind,
    RawEntity,
    RawTrace,
    UnitsFingerprint,
    UnitsMethod,
)

# Dos punts es consideren el mateix punt per sota d'aquesta distància (en unitats
# natives del fitxer, abans d'escalar). El material real coincideix a la mil·lèsima.
COINCIDENCE_TOL = 0.01

#: Factors candidats a la deducció d'unitats: nom → mm per unitat nativa.
UNIT_CANDIDATES: dict[str, float] = {
    'mm': 1.0,
    'cm': 10.0,
    'in': 25.4,
    '1/10mm': 0.1,
}

#: Una peça de patró plausible fa entre 10 cm i 2,5 m. Fora d'aquí, el factor no és aquest.
PLAUSIBLE_MIN_MM = 100.0
PLAUSIBLE_MAX_MM = 2500.0

#: $INSUNITS → mm per unitat (els que tenen sentit en patronatge).
INSUNITS_TO_MM: dict[int, float] = {1: 25.4, 2: 304.8, 4: 1.0, 5: 10.0, 6: 1000.0}

#: Doblec: un tram recte ha de valer com a mínim aquesta fracció del costat del
#: bounding box per ser candidat a eix de simetria.
FOLD_MIN_RATIO = 0.40


class AAMAReader:
    """Implementa la meitat `read` del port `FormatCodec` (el `write` arriba a S2)."""

    def read(self, data: bytes) -> PatternDocument:
        doc = self._open(data)
        separadors = _detect_decimal_separators(data)
        textos_doc = _modelspace_texts(doc)
        meta_doc = _parse_key_values(textos_doc)

        unitats = _resolve_units(doc, meta_doc, textos_doc)
        factor = unitats.factor_to_mm

        blocks = [b for b in doc.blocks if not b.name.startswith('*')]
        if not blocks:
            raise PatternParseError(
                'El fitxer no conté cap peça (cap BLOCK).',
                [ParseIssue('no_blocks', 'Un DXF de patró ha de portar les peces com a BLOCKS.')],
            )

        inserts = _insert_points(doc)
        issues: list[ParseIssue] = []
        pieces = []
        capes_totals: set[str] = set()
        desconegudes: set[str] = set()

        for block in blocks:
            piece, capes, unknown, piece_issues = _read_piece(
                block, factor, inserts.get(block.name, (0.0, 0.0))
            )
            pieces.append(piece)
            capes_totals |= capes
            desconegudes |= unknown
            issues += piece_issues

        buides = _empty_sections(data)
        fingerprint = Fingerprint(
            font_cad=_guess_source_cad(meta_doc),
            dxf_version=doc.dxfversion,
            autor=meta_doc.get('author', ''),
            ordre_seccions=_section_order(doc),
            capes_presents=tuple(sorted(capes_totals, key=_layer_sort_key)),
            capes_desconegudes=tuple(sorted(desconegudes, key=_layer_sort_key)),
            capes_declarades=tuple(l.dxf.name for l in doc.layers),
            separador_decimal=separadors,
            unitats=unitats,
            cens_entitats=_entity_census(doc),
            textos_document=tuple(textos_doc),
            doc_text_anchor=_doc_text_anchor(doc),
            text_height=_dominant_text_height(doc),
            header_buida='HEADER' in buides,
            tables_buida='TABLES' in buides,
        )

        # Les issues NO tomben la lectura: un fitxer amb rareses s'ha de poder obrir.
        # Només un fitxer del qual no en surt ni una peça és un error dur.
        if not any(p.boundaries for p in pieces):
            raise PatternParseError(
                'Cap peça del fitxer té contorn llegible.',
                issues or [ParseIssue('empty_boundaries', 'Cap BLOCK conté polilínies.')],
            )

        return PatternDocument(pieces=tuple(pieces), fingerprint=fingerprint)

    # ── obertura tolerant ────────────────────────────────────────────────────
    def _open(self, data: bytes) -> Drawing:
        if not data:
            raise PatternParseError(
                'El fitxer és buit.', [ParseIssue('empty_file', 'Zero bytes.')]
            )
        try:
            # `recover` és el camí robust d'ezdxf: repara el que pot i no peta amb
            # fitxers que un readfile() estricte rebutjaria.
            doc, _auditor = recover.read(io.BytesIO(data))
            return doc
        except IOError as exc:
            raise PatternParseError(
                'El fitxer no sembla un DXF.',
                [ParseIssue('not_a_dxf', _short(exc))],
            ) from exc
        except ezdxf.DXFError as exc:
            raise PatternParseError(
                'El DXF està malmès i no s\'ha pogut recuperar.',
                [ParseIssue('corrupt_dxf', _short(exc))],
            ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Unitats
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_units(doc: Drawing, meta_doc: dict, textos: list[str]) -> UnitsFingerprint:
    """Cascada: capçalera → (text del document + geometria) → geometria → assumpció.

    Cap CAD real garanteix la capçalera, i el text ('Units: Metric') diu el sistema
    però no l'escala: 'metric' tant és mm com cm. Per això, quan no hi ha capçalera,
    qui decideix el factor és la geometria, i el text només apuja la confiança.
    """
    insunits = doc.header.get('$INSUNITS', 0)
    if insunits and insunits in INSUNITS_TO_MM:
        return UnitsFingerprint(
            factor_to_mm=INSUNITS_TO_MM[insunits],
            metode=UnitsMethod.HEADER,
            confianca=Confidence.HIGH,
            evidencia=f'$INSUNITS={insunits}',
        )

    candidats = _plausible_unit_candidates(doc)
    text_units = (meta_doc.get('units') or '').strip().lower()

    if len(candidats) == 1:
        nom, factor, dim = candidats[0]
        corrobora = (
            text_units.startswith('metric') and nom in ('mm', 'cm', '1/10mm')
        ) or (text_units.startswith('imperial') and nom == 'in')
        return UnitsFingerprint(
            factor_to_mm=factor,
            metode=UnitsMethod.GEOMETRY,
            confianca=Confidence.HIGH if corrobora else Confidence.MEDIUM,
            evidencia=(
                f'peça més gran = {dim:.1f} unitats natives → {dim * factor:.0f} mm amb {nom}; '
                f'únic factor plausible'
                + (f"; corroborat pel TEXT 'Units: {text_units}'" if corrobora else '')
            ),
        )

    if candidats:
        # Més d'un factor deixa la peça dins d'un rang plausible: no s'endevina, es
        # tria mm (el més freqüent) i es diu clarament que la confiança és baixa.
        noms = ', '.join(c[0] for c in candidats)
        return UnitsFingerprint(
            factor_to_mm=1.0,
            metode=UnitsMethod.GEOMETRY,
            confianca=Confidence.LOW,
            evidencia=f'factors plausibles alhora ({noms}); s\'assumeix mm',
        )

    return UnitsFingerprint(
        factor_to_mm=1.0,
        metode=UnitsMethod.ASSUMED,
        confianca=Confidence.LOW,
        evidencia='cap evidència d\'unitats (ni capçalera, ni text, ni dimensions plausibles)',
    )


def _plausible_unit_candidates(doc: Drawing) -> list[tuple[str, float, float]]:
    """Quins factors deixarien la peça més gran dins d'una mida de roba creïble."""
    dim = _max_piece_dimension(doc)
    if dim <= 0:
        return []
    return [
        (nom, factor, dim)
        for nom, factor in UNIT_CANDIDATES.items()
        if PLAUSIBLE_MIN_MM <= dim * factor <= PLAUSIBLE_MAX_MM
    ]


def _max_piece_dimension(doc: Drawing) -> float:
    """Costat més llarg del bounding box de la peça més gran, en unitats natives."""
    millor = 0.0
    for block in doc.blocks:
        if block.name.startswith('*'):
            continue
        xs, ys = [], []
        for e in block:
            if e.dxftype() == 'POLYLINE':
                for v in e.vertices:
                    xs.append(v.dxf.location.x)
                    ys.append(v.dxf.location.y)
        if xs:
            millor = max(millor, max(xs) - min(xs), max(ys) - min(ys))
    return millor


# ─────────────────────────────────────────────────────────────────────────────
# Peça
# ─────────────────────────────────────────────────────────────────────────────

def _read_piece(
    block, factor: float, insert_at: tuple[float, float]
) -> tuple[PieceData, set[str], set[str], list[ParseIssue]]:
    issues: list[ParseIssue] = []
    capes: set[str] = set()
    desconegudes: set[str] = set()

    polylines: list = []
    classificadors: dict[str, list[tuple[float, float]]] = {'2': [], '3': []}
    notch_pts: list[tuple[float, float]] = []
    grain: Optional[GrainLineData] = None
    textos_capa1: list[str] = []
    meta_anchor: tuple[float, float] = (0.0, 0.0)
    rule_texts: list[tuple[float, float, int]] = []
    raw_entities: list[RawEntity] = []

    ftt_entities: list = []

    for e in block:
        layer = e.dxf.layer
        capes.add(layer)
        kind = e.dxftype()

        if layer == FTT_POM_LAYER:
            # La nostra pròpia capa: ni és desconeguda ni és opaca. Es llegeix com a
            # taula de POMs (esmena E3) i NO va a raw_entities — si hi anés, una
            # reexportació l'escriuria dos cops: com a rastre i com a projecció.
            ftt_entities.append(e)
            continue

        if layer not in AAMA_LAYER_ROLES:
            desconegudes.add(layer)
            # No l'entenem, però la tornarem a escriure exactament on era.
            raw_entities.append(_as_raw_entity(e, factor))
            continue

        if kind == 'POLYLINE':
            polylines.append(e)
        elif kind == 'POINT':
            p = (e.dxf.location.x, e.dxf.location.y)
            if layer in classificadors:
                classificadors[layer].append(p)
            elif layer == '4':
                notch_pts.append(p)
        elif kind == 'LINE' and layer == '7':
            s, t = e.dxf.start, e.dxf.end
            grain = GrainLineData(s.x * factor, s.y * factor, t.x * factor, t.y * factor)
        elif kind == 'TEXT':
            text = e.dxf.text
            num = _parse_rule_number(text)
            if num is not None:
                rule_texts.append((e.dxf.insert.x, e.dxf.insert.y, num))
            elif layer == '1':
                textos_capa1.append(text)
                meta_anchor = (e.dxf.insert.x * factor, e.dxf.insert.y * factor)

    boundaries: list[BoundaryData] = []
    for pl in polylines:
        layer = pl.dxf.layer
        role = AAMA_LAYER_ROLES.get(layer, LayerRole.UNKNOWN)
        pts_natius = [(v.dxf.location.x, v.dxf.location.y) for v in pl.vertices]
        if len(pts_natius) < 2:
            issues.append(ParseIssue(
                'degenerate_polyline',
                f'Polilínia de la capa {layer} amb {len(pts_natius)} vèrtex(s); s\'ignora.',
                peca=block.name,
            ))
            continue

        # Tancament PER GEOMETRIA: els CAD reals repeteixen el primer vèrtex en lloc
        # d'activar el flag. Si és així, el vèrtex duplicat sobra al model intern.
        closed = _same_point(pts_natius[0], pts_natius[-1])
        if closed:
            pts_natius = pts_natius[:-1]

        punts = tuple(
            PointData(
                x=x * factor,
                y=y * factor,
                kind=_classify(x, y, classificadors),
                grade_rule=_rule_at(x, y, rule_texts),
                raw=RawTrace(dxftype='VERTEX', layer=layer, handle=str(pl.dxf.handle or '')),
            )
            for x, y in pts_natius
        )
        boundaries.append(BoundaryData(role=role, layer=layer, points=punts, closed=closed))

    notches = tuple(
        NotchData(
            x=x * factor,
            y=y * factor,
            grade_rule=_rule_at(x, y, rule_texts),
            raw=RawTrace(dxftype='POINT', layer='4'),
        )
        for x, y in notch_pts
    )

    metadata = _piece_metadata(textos_capa1, meta_anchor)
    has_sew = any(b.role is LayerRole.SEW for b in boundaries)
    fold = _detect_fold(boundaries)

    poms, _meta = build_poms(*collect_ftt_entities(ftt_entities, factor))

    piece = PieceData(
        nom_block=block.name,
        boundaries=tuple(boundaries),
        notches=notches,
        grain=grain,
        metadata=metadata,
        rol=metadata.piece_name or block.name,
        doblec_original=fold,
        has_sew=has_sew,
        has_fold=fold is not None,
        unknown_layers=tuple(sorted(desconegudes, key=_layer_sort_key)),
        raw_entities=tuple(raw_entities),
        insert_at=insert_at,
        poms=poms,
    )
    return piece, capes, desconegudes, issues


def _as_raw_entity(e, factor: float) -> RawEntity:
    """Una entitat de capa no catalogada, capturada literalment."""
    kind = e.dxftype()
    punts: tuple[tuple[float, float], ...] = ()
    text = ''
    height = 0.0

    if kind == 'TEXT':
        ins = e.dxf.insert
        punts = ((ins.x * factor, ins.y * factor),)
        text = e.dxf.text
        height = e.dxf.height * factor
    elif kind == 'POINT':
        loc = e.dxf.location
        punts = ((loc.x * factor, loc.y * factor),)
    elif kind == 'LINE':
        s, t = e.dxf.start, e.dxf.end
        punts = ((s.x * factor, s.y * factor), (t.x * factor, t.y * factor))
    elif kind == 'POLYLINE':
        punts = tuple(
            (v.dxf.location.x * factor, v.dxf.location.y * factor) for v in e.vertices
        )

    return RawEntity(dxftype=kind, layer=e.dxf.layer, punts=punts, text=text, height=height)


def _classify(x: float, y: float, classificadors: dict[str, list]) -> PointKind:
    """Un vèrtex és turn o curve segons quin POINT hi seu damunt."""
    if _near_any(x, y, classificadors['2']):
        return PointKind.TURN
    if _near_any(x, y, classificadors['3']):
        return PointKind.CURVE
    return PointKind.UNCLASSIFIED


def _rule_at(x: float, y: float, rule_texts: list[tuple[float, float, int]]) -> Optional[int]:
    """El número de regla de grading que el CAD ha assegut sobre aquest punt."""
    for tx, ty, num in rule_texts:
        if _same_point((x, y), (tx, ty)):
            return num
    return None


def _piece_metadata(textos: Iterable[str], anchor: tuple[float, float]) -> PieceMetadata:
    kv = _parse_key_values(textos)
    return PieceMetadata(
        piece_name=kv.get('piece name', ''),
        size=kv.get('size', ''),
        quantity=_parse_number(kv.get('quantity', '')),
        material=kv.get('material', ''),
        extra={k: v for k, v in kv.items()
               if k not in ('piece name', 'size', 'quantity', 'material')},
        anchor=anchor,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Doblec — detecció per geometria i materialització de la simetria
# ─────────────────────────────────────────────────────────────────────────────

def _detect_fold(boundaries: list[BoundaryData]) -> Optional[FoldData]:
    """Cerca un eix de doblec al contorn de tall.

    La capa 6 (mirall) existeix a l'estàndard però és inconsistent entre CAD, així que
    no s'hi confia: es busca la signatura geomètrica d'una peça dibuixada a mitges —
    **un tram recte, llarg, vertical o horitzontal, amb TOTA la resta de la peça a un
    sol costat**. És la vora que el patronista posa sobre el doblec de la tela.

    Si el fitxer SÍ declara la capa 6, se'n pren l'eix i s'estalvia l'heurística.
    """
    declarat = next((b for b in boundaries if b.role is LayerRole.MIRROR), None)
    if declarat is not None and len(declarat.points) >= 2:
        a, b = declarat.points[0], declarat.points[-1]
        return FoldData(a.x, a.y, b.x, b.y, materialitzat=False)

    cut = next((b for b in boundaries if b.role is LayerRole.CUT), None)
    if cut is None or len(cut.points) < 3:
        return None

    xs = [p.x for p in cut.points]
    ys = [p.y for p in cut.points]
    ample, alt = max(xs) - min(xs), max(ys) - min(ys)
    if ample <= 0 or alt <= 0:
        return None

    # Una peça pot tenir més d'un tram recte que compleixi les condicions (una base
    # plana i un centre recte, posem per cas). El doblec és el més llarg dels dos: és
    # la vora que de debò es posa sobre el doblec de la tela.
    candidats: list[tuple[float, FoldData]] = []
    n = len(cut.points)
    for i in range(n):
        a = cut.points[i]
        b = cut.points[(i + 1) % n]
        altres = [p for j, p in enumerate(cut.points) if j not in (i, (i + 1) % n)]
        if not altres:
            continue

        # Eix vertical: x constant, prou llarg, i la peça tota a un costat.
        if abs(a.x - b.x) <= COINCIDENCE_TOL and abs(a.y - b.y) >= FOLD_MIN_RATIO * alt:
            eix = a.x
            if all(p.x >= eix - COINCIDENCE_TOL for p in altres) or \
               all(p.x <= eix + COINCIDENCE_TOL for p in altres):
                candidats.append((abs(a.y - b.y), FoldData(a.x, a.y, b.x, b.y)))

        # Eix horitzontal.
        if abs(a.y - b.y) <= COINCIDENCE_TOL and abs(a.x - b.x) >= FOLD_MIN_RATIO * ample:
            eix = a.y
            if all(p.y >= eix - COINCIDENCE_TOL for p in altres) or \
               all(p.y <= eix + COINCIDENCE_TOL for p in altres):
                candidats.append((abs(a.x - b.x), FoldData(a.x, a.y, b.x, b.y)))

    if not candidats:
        return None
    return max(candidats, key=lambda c: c[0])[1]


def unfold_piece(piece: PieceData) -> PieceData:
    """Desplega una peça dibuixada a mitges: la reflecteix sobre el seu eix de doblec.

    El motor treballa **sempre amb la peça sencera** (mesurar mitja màniga no és
    mesurar una màniga). L'eix es conserva a `doblec_original` amb
    `materialitzat=True` perquè S2 la pugui tornar a plegar si el CAD de destí espera
    rebre-la a mitges.

    Sense doblec, torna la peça tal com és.
    """
    fold = piece.doblec_original
    if fold is None or fold.materialitzat:
        return piece

    boundaries = tuple(
        BoundaryData(
            role=b.role,
            layer=b.layer,
            points=_mirror_points(b.points, fold),
            closed=b.closed,
        )
        for b in piece.boundaries
    )
    notches = piece.notches + tuple(
        NotchData(*_mirror_xy(nd.x, nd.y, fold), grade_rule=nd.grade_rule, raw=nd.raw)
        for nd in piece.notches
        if not _on_axis(nd.x, nd.y, fold)
    )
    return PieceData(
        nom_block=piece.nom_block,
        boundaries=boundaries,
        notches=notches,
        grain=piece.grain,
        metadata=piece.metadata,
        rol=piece.rol,
        doblec_original=FoldData(
            fold.eix_x1, fold.eix_y1, fold.eix_x2, fold.eix_y2, materialitzat=True
        ),
        has_sew=piece.has_sew,
        has_fold=True,
        unknown_layers=piece.unknown_layers,
    )


def _mirror_points(points: tuple[PointData, ...], fold: FoldData) -> tuple[PointData, ...]:
    """Punts originals + el seu mirall en ordre invers (el contorn es tanca sol).

    Els punts que seuen sobre l'eix no es dupliquen: són la frontissa.
    """
    reflectits = [
        PointData(
            *_mirror_xy(p.x, p.y, fold),
            kind=p.kind,
            grade_rule=p.grade_rule,
            raw=p.raw,
        )
        for p in reversed(points)
        if not _on_axis(p.x, p.y, fold)
    ]
    return points + tuple(reflectits)


def _mirror_xy(x: float, y: float, fold: FoldData) -> tuple[float, float]:
    """Reflexió d'un punt respecte de la recta de l'eix."""
    ax, ay = fold.eix_x1, fold.eix_y1
    bx, by = fold.eix_x2, fold.eix_y2
    dx, dy = bx - ax, by - ay
    den = dx * dx + dy * dy
    if den == 0:
        return x, y
    # Projecció de (x,y) sobre la recta, i el punt reflectit és 2·projecció − punt.
    t = ((x - ax) * dx + (y - ay) * dy) / den
    px, py = ax + t * dx, ay + t * dy
    return 2 * px - x, 2 * py - y


def _on_axis(x: float, y: float, fold: FoldData) -> bool:
    mx, my = _mirror_xy(x, y, fold)
    return abs(mx - x) <= COINCIDENCE_TOL and abs(my - y) <= COINCIDENCE_TOL


# ─────────────────────────────────────────────────────────────────────────────
# Empremta i utilitats de text
# ─────────────────────────────────────────────────────────────────────────────

def _detect_decimal_separators(data: bytes) -> dict[str, str]:
    """Quin separador decimal fa servir CADA camp.

    No és una floritura: l'AMELIA escriu les coordenades amb punt (`613.500`) i les
    metadades amb coma (`Quantity: 1,0`) **dins el mateix fitxer**. Un writer que
    unifiqués el criteri (S2) tornaria un fitxer que el CAD d'origen ja no reconeix
    com a seu.
    """
    text = data.decode('utf-8', errors='replace')
    linies = text.splitlines()
    coord_sep: Optional[str] = None
    text_sep: Optional[str] = None

    for i in range(0, len(linies) - 1, 2):
        codi = linies[i].strip()
        valor = linies[i + 1]
        if codi in ('10', '20', '30', '11', '21', '40') and coord_sep is None:
            if ',' in valor:
                coord_sep = ','
            elif '.' in valor:
                coord_sep = '.'
        elif codi == '1' and text_sep is None:
            # Un número dins d'un TEXT ('Quantity: 1,0').
            if any(c.isdigit() for c in valor):
                if ',' in valor:
                    text_sep = ','
                elif '.' in valor:
                    text_sep = '.'

    seps: dict[str, str] = {}
    if coord_sep:
        seps['coordenades'] = coord_sep
    if text_sep:
        seps['text'] = text_sep
    return seps


def _empty_sections(data: bytes) -> set[str]:
    """Quines seccions venien BUIDES al fitxer d'origen.

    ezdxf, en llegir, omple la HEADER amb els seus valors per defecte i la taula LAYERS
    amb '0' i 'Defpoints': si li preguntéssim a ell, diria que hi són. Per saber què hi
    havia de debò cal mirar els bytes. I cal saber-ho, perquè el writer ha de tornar a
    deixar-les buides: un fitxer "millorat" ja no és el fitxer del client.
    """
    text = data.decode('utf-8', errors='replace')
    linies = [l.strip() for l in text.splitlines()]
    buides: set[str] = set()
    for i in range(len(linies) - 3):
        if linies[i] == 'SECTION' and linies[i + 1] == '2':
            nom = linies[i + 2]
            # Buida = SECTION / 2 / <nom> / 0 / ENDSEC, sense res al mig.
            if linies[i + 3] == '0' and linies[i + 4:i + 5] == ['ENDSEC']:
                buides.add(nom)
    return buides


def _doc_text_anchor(doc: Drawing) -> tuple[float, float]:
    for e in doc.modelspace():
        if e.dxftype() == 'TEXT' and e.dxf.layer != FTT_POM_LAYER:
            return (e.dxf.insert.x, e.dxf.insert.y)
    return (0.0, 0.0)


def _dominant_text_height(doc: Drawing) -> float:
    altures: Counter = Counter()
    for block in doc.blocks:
        if block.name.startswith('*'):
            continue
        for e in block:
            if e.dxftype() == 'TEXT':
                altures[e.dxf.height] += 1
    return altures.most_common(1)[0][0] if altures else 0.0


def _insert_points(doc: Drawing) -> dict[str, tuple[float, float]]:
    return {
        e.dxf.name: (e.dxf.insert.x, e.dxf.insert.y)
        for e in doc.modelspace()
        if e.dxftype() == 'INSERT'
    }


def _modelspace_texts(doc: Drawing) -> list[str]:
    """Els TEXT de metadades del CAD d'origen.

    La capa FTT-POM queda FORA a posta: el `FTT-META` que hi vam posar nosaltres no és
    una metadada del fitxer d'origen. Si s'hi colés, cada reexportació n'escriuria un
    de nou i el fitxer aniria engreixant una línia per volta.
    """
    return [
        e.dxf.text for e in doc.modelspace()
        if e.dxftype() == 'TEXT' and e.dxf.layer != FTT_POM_LAYER
    ]


def _entity_census(doc: Drawing) -> dict[str, int]:
    cens: Counter = Counter()
    for block in doc.blocks:
        if block.name.startswith('*'):
            continue
        for e in block:
            cens[e.dxftype()] += 1
    for e in doc.modelspace():
        cens[e.dxftype()] += 1
    return dict(cens)


def _section_order(doc: Drawing) -> tuple[str, ...]:
    """Ordre de seccions d'un DXF (fix a l'estàndard; es registra per al writer de S2)."""
    seccions = ['HEADER', 'TABLES', 'BLOCKS', 'ENTITIES']
    if doc.dxfversion > ezdxf.DXF12:
        seccions.insert(2, 'CLASSES')
        seccions.append('OBJECTS')
    return tuple(seccions)


def _guess_source_cad(meta_doc: dict) -> str:
    autor = (meta_doc.get('author') or '').lower()
    if 'polypattern' in autor:
        return 'polypattern'
    if 'tuka' in autor:
        return 'tuka'
    if 'gerber' in autor or 'accumark' in autor:
        return 'gerber'
    return autor.split()[0] if autor else ''


def _parse_key_values(textos: Iterable[str]) -> dict[str, str]:
    """TEXTs del tipus 'Clau: valor' → dict amb la clau en minúscules."""
    kv: dict[str, str] = {}
    for text in textos:
        if ':' not in text:
            continue
        clau, _, valor = text.partition(':')
        clau = clau.strip().lower()
        if clau:
            kv.setdefault(clau, valor.strip())
    return kv


def _parse_rule_number(text: str) -> Optional[int]:
    """'# 1' → 1. És el número de `RULE: DELTA n` del RUL, assegut sobre el punt."""
    t = text.strip()
    if not t.startswith('#'):
        return None
    try:
        return int(t[1:].strip())
    except ValueError:
        return None


def _parse_number(valor: str) -> Optional[float]:
    """Número d'un TEXT, amb coma o punt decimal ('1,0' i '1.0' són el mateix."""
    if not valor:
        return None
    try:
        return float(valor.strip().replace(',', '.'))
    except ValueError:
        return None


def _short(exc: Exception, limit: int = 200) -> str:
    """El detall d'un error va a parar a un 422 i als ulls d'algú: no hi aboquem el
    fitxer sencer. ezdxf, davant d'un binari qualsevol, cita tota la brossa que ha
    llegit."""
    missatge = ' '.join(str(exc).split())
    return missatge if len(missatge) <= limit else missatge[:limit] + '…'


def _layer_sort_key(layer: str) -> tuple[int, object]:
    return (0, int(layer)) if layer.isdigit() else (1, layer)


def _same_point(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return abs(a[0] - b[0]) <= COINCIDENCE_TOL and abs(a[1] - b[1]) <= COINCIDENCE_TOL


def _near_any(x: float, y: float, punts: list[tuple[float, float]]) -> bool:
    return any(_same_point((x, y), p) for p in punts)
