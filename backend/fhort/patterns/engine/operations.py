"""L'operació atòmica: moure punts. L'ÚNICA manera que té el motor de tocar geometria.

Escalar, a AAMA, no és emetre N geometries. El lliurable és **la mateixa geometria de la
talla mostra + un RUL poblat**, i el CAD del client reconstrueix cada talla fent
`punt_base + delta(regla, talla)`. Aquesta operació existeix per a les altres dues coses
que sí que necessitem: la PREVIEW per talla i la VALIDACIÓ contra les mesures. **Mai muta
la geometria base persistida** — construeix un document nou i el torna.

QUÈ VOL DIR MOURE UN PUNT (i per què no és moure un punt)
---------------------------------------------------------
Desplaçar el vèrtex i prou deixaria el patró trencat. Moure un punt, de debò, és:

  1. **Moure'l.** Ell i els altres que el mateix moviment demani.
  2. **REFLOW dels punts de corba.** Els punts de corba no es graden: FLUEIXEN entre els
     punts de gir que els emmarquen. Si la sisa creix 1 cm, els punts de corba de la sisa
     no es queden quiets ni salten el centímetre sencer: es reparteixen el moviment
     **per ràtio de longitud d'arc**, que és el que manté la forma de la corba. Aquesta és
     la diferència entre una peça graduada i una peça deformada.
  3. **Reposicionar els piquets.** Un piquet no té coordenades pròpies: té una POSICIÓ
     SOBRE LA VORA. Si la vora es mou, el piquet hi va a sobre. Si el traslladéssim per
     delta, quedaria flotant al costat de la peça — i un piquet fora de la vora és un
     piquet que la taula de tall no sap tallar.
  4. **Rellegir els POMs.** El valor d'un POM no s'escriu: es llegeix de la geometria. Si
     la geometria s'ha mogut, el valor d'abans és una opinió caducada.
  5. **Revalidar les costures.** Dues vores que casaven a la talla mostra poden deixar de
     casar tres talles amunt. Això és **exactament** el que un CAD no et diu i el que fa
     que una niada nostra es pugui defensar.

LA FRONTERA (§3.3 del pla, no negociable)
------------------------------------------
Es mouen punts que **JA EXISTEIXEN**. No es crea topologia: ni vèrtexs nous, ni vores
partides, ni pinces noves. Això té una conseqüència que val la pena dir en veu alta,
perquè decideix una discussió: **la re-derivació del tall per OFFSET de la línia de cosit
NO es fa aquí**. Un offset de polilínia canvia el nombre de vèrtexs a les cantonades
—crea topologia—, i a més no és el que fa el grading: quan un CAD gradua, la MATEIXA
regla mou el punt de tall i el seu company de la línia de cosit, de manera que el marge
de costura es conserva. Això és CORRESPONDÈNCIA, no offset, i és el que fa
`_propagar_al_cosit`. (Per això aquest mòdul no necessita shapely: longituds i direccions
són aritmètica de polilínies i prou. Un offset de veritat —canviar el marge de costura—
és una operació de CREACIÓ i és post-traçadora.)

POSTCONDICIONS
--------------
No hi ha `assert` muts. Tot el que ha passat —i tot el que NO ha pogut passar— surt a
`MoveReport`, que el crida qui vulgui ensenyar-lo. Un `assert` que peta en producció no
diu res a ningú; un informe, sí.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from math import hypot
from typing import Optional

from .geometry import (
    BoundaryData,
    LayerRole,
    NotchData,
    PatternDocument,
    PieceData,
    POMAnchorData,
    PointData,
    PointKind,
)
from .measure import MeasureError, resoldre
from .segments import segmentar_vora
from .sew import SewCheck, validar

MM_PER_CM = 10.0

#: Un piquet més lluny d'això de la vora ja no és "un piquet sobre la vora": és un punt
#: que hi ha a prop. Al material real la distància és 0.000 mm, així que mig mil·límetre
#: és folgadíssim i, tot i així, qualsevol cosa que el superi es reporta.
TOL_PIQUET_MM = 0.5

#: Distància màxima per aparellar un punt de la línia de cosit amb el seu company del
#: tall. És el marge de costura típic (1 cm) amb aire: si no en troba cap a menys d'això,
#: no s'inventa la parella — ho diu.
TOL_PARELLA_COSIT_MM = 30.0


# ─────────────────────────────────────────────────────────────────────────────
# Referències: com s'assenyala un punt sense que l'engine sàpiga què és una BD
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PointRef:
    """L'adreça d'un punt dins el document. Hashable: serveix de clau.

    `vora=None` vol dir piquet (els piquets no pertanyen a cap vora: seuen a sobre d'una).
    L'engine no sap què és un `PatternPoint.id`; l'adaptador li dona això.
    """
    peca: str
    vora: Optional[int]
    ordre: int


@dataclass(frozen=True)
class POMSpec:
    """Un POM ancorat, en termes que l'engine entén: dues adreces i un mètode."""
    pom_code: str
    nom: str
    peca: str
    ref_a: PointRef
    ref_b: PointRef
    metode: str = 'recta'
    pom_id: Optional[int] = None


@dataclass(frozen=True)
class SegRef:
    """Un tram d'una vora, tal com el desa `PatternSegment` (paramètric)."""
    peca: str
    vora: int
    t_inici: float
    t_fi: float


@dataclass(frozen=True)
class SewSpec:
    """Una costura declarada: dos costats, un tipus i el diferencial promès."""
    sew_id: int
    tipus: str
    diferencial_cm: float
    costat_a: tuple[SegRef, ...]
    costat_b: tuple[SegRef, ...]


# ─────────────────────────────────────────────────────────────────────────────
# L'informe
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MoveIssue:
    """Una cosa que ha passat i que qui miri el resultat ha de saber."""
    codi: str
    missatge: str
    peca: str = ''
    detall: dict = field(default_factory=dict)

    def __str__(self) -> str:
        on = f' [{self.peca}]' if self.peca else ''
        return f'{self.codi}{on}: {self.missatge}'


@dataclass(frozen=True)
class POMReading:
    """El valor d'un POM llegit de la geometria MOGUDA."""
    pom_code: str
    peca: str
    valor_cm: Optional[float]
    punts: tuple[tuple[float, float], ...] = ()
    error: str = ''


@dataclass(frozen=True)
class SewReading:
    sew_id: int
    check: Optional[SewCheck]
    error: str = ''


@dataclass(frozen=True)
class MoveReport:
    """Les postcondicions, dites. No són asserts: són un informe."""
    punts_moguts: int = 0
    punts_reflow: int = 0
    piquets_reposicionats: int = 0
    punts_cosit_propagats: int = 0
    poms: tuple[POMReading, ...] = ()
    costures: tuple[SewReading, ...] = ()
    avisos: tuple[MoveIssue, ...] = ()

    @property
    def ok(self) -> bool:
        """Cap avís i totes les costures casen."""
        return not self.avisos and all(
            s.check is not None and s.check.casa for s in self.costures
        )

    def resum(self) -> str:
        linies = [
            f'{self.punts_moguts} punts moguts · {self.punts_reflow} de corba reflowats · '
            f'{self.piquets_reposicionats} piquets reposicionats'
        ]
        if self.punts_cosit_propagats:
            linies.append(f'{self.punts_cosit_propagats} punts de cosit propagats')
        for p in self.poms:
            linies.append(
                f'  POM {p.pom_code} = {p.valor_cm:.2f} cm' if p.valor_cm is not None
                else f'  POM {p.pom_code}: {p.error}'
            )
        for s in self.costures:
            linies.append(f'  Costura {s.sew_id}: '
                          + (s.check.missatge if s.check else s.error))
        for a in self.avisos:
            linies.append(f'  ⚠ {a}')
        return '\n'.join(linies)


@dataclass(frozen=True)
class MoveResult:
    """Document NOU + què ha passat per arribar-hi. L'original no s'ha tocat."""
    document: PatternDocument
    informe: MoveReport


# ─────────────────────────────────────────────────────────────────────────────
# L'operació
# ─────────────────────────────────────────────────────────────────────────────

def move_points(
    doc: PatternDocument,
    deltes: dict[PointRef, tuple[float, float]],
    poms: tuple[POMSpec, ...] = (),
    sews: tuple[SewSpec, ...] = (),
) -> MoveResult:
    """Mou els punts indicats i deixa el patró coherent. Document NOU, sempre.

    `deltes` en mm. Els punts que no hi surten no es queden necessàriament quiets: els de
    corba flueixen (reflow) i els piquets segueixen la vora. Això és el que vol dir que
    l'operació sigui atòmica — no és "moure un punt", és "moure el patró per aquest punt".
    """
    avisos: list[MoveIssue] = []
    moguts = reflow = piquets = cosits = 0
    peces_noves: list[PieceData] = []

    for piece in doc.pieces:
        nova, comptes, issues = _move_piece(piece, deltes, avisos_peca=piece.nom_block)
        peces_noves.append(nova)
        moguts += comptes['moguts']
        reflow += comptes['reflow']
        piquets += comptes['piquets']
        cosits += comptes['cosits']
        avisos += issues

    doc_nou = replace(doc, pieces=tuple(peces_noves))

    # Els deltes que apuntaven enlloc són un error de qui crida, i s'ha de veure.
    coneguts = {
        PointRef(p.nom_block, i, j)
        for p in doc.pieces
        for i, b in enumerate(p.boundaries)
        for j in range(len(b.points))
    } | {
        PointRef(p.nom_block, None, j)
        for p in doc.pieces
        for j in range(len(p.notches))
    }
    for ref in deltes:
        if ref not in coneguts:
            avisos.append(MoveIssue(
                'punt_inexistent',
                f'S\'ha demanat moure un punt que no és al document: {ref}.',
                peca=ref.peca, detall={'ref': str(ref)},
            ))

    lectures = _rellegir_poms(doc_nou, poms, avisos)
    costures = _revalidar_costures(doc, doc_nou, sews, avisos)

    return MoveResult(
        document=doc_nou,
        informe=MoveReport(
            punts_moguts=moguts,
            punts_reflow=reflow,
            piquets_reposicionats=piquets,
            punts_cosit_propagats=cosits,
            poms=tuple(lectures),
            costures=tuple(costures),
            avisos=tuple(avisos),
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Peça
# ─────────────────────────────────────────────────────────────────────────────

def _move_piece(
    piece: PieceData, deltes: dict[PointRef, tuple[float, float]], avisos_peca: str
) -> tuple[PieceData, dict, list[MoveIssue]]:
    avisos: list[MoveIssue] = []
    comptes = {'moguts': 0, 'reflow': 0, 'piquets': 0, 'cosits': 0}

    # ── 1+2. Cada vora: moure els seus punts i fer fluir els de corba.
    desplacaments: list[list[tuple[float, float]]] = []
    for i, boundary in enumerate(piece.boundaries):
        d, n_mog, n_ref, issues = _desplacaments_vora(
            boundary, i, piece.nom_block, deltes,
        )
        desplacaments.append(d)
        comptes['moguts'] += n_mog
        comptes['reflow'] += n_ref
        avisos += issues

    # ── 3. La línia de cosit segueix el tall per CORRESPONDÈNCIA (mai per offset).
    if piece.has_sew:
        n_cosit, issues = _propagar_al_cosit(piece, desplacaments)
        comptes['cosits'] += n_cosit
        avisos += issues

    vores_noves = tuple(
        replace(b, points=tuple(
            replace(p, x=p.x + dx, y=p.y + dy)
            for p, (dx, dy) in zip(b.points, desplacaments[i])
        ))
        for i, b in enumerate(piece.boundaries)
    )

    # ── 4. Els piquets van SOBRE la vora, no al costat.
    piquets_nous, n_piq, issues = _reposicionar_piquets(
        piece, vores_noves, desplacaments,
    )
    comptes['piquets'] += n_piq
    avisos += issues

    return replace(piece, boundaries=vores_noves, notches=piquets_nous), comptes, avisos


def _desplacaments_vora(
    boundary: BoundaryData,
    index_vora: int,
    nom_peca: str,
    deltes: dict[PointRef, tuple[float, float]],
) -> tuple[list[tuple[float, float]], int, int, list[MoveIssue]]:
    """El desplaçament de CADA punt de la vora: els ancorats pel seu delta, els de corba
    per interpolació de ràtio d'arc entre els dos ancoratges que els emmarquen."""
    pts = boundary.points
    n = len(pts)
    avisos: list[MoveIssue] = []
    if n == 0:
        return [], 0, 0, avisos

    explicits: dict[int, tuple[float, float]] = {}
    for j in range(n):
        d = deltes.get(PointRef(nom_peca, index_vora, j))
        if d is not None:
            explicits[j] = d

    # Ancoratge = punt de gir (encara que no es mogui: un gir quiet ancora el reflow) o
    # punt amb delta explícit. Un delta sobre un punt de CORBA és legal però estrany:
    # el punt deixa de fluir i passa a manar. Es diu.
    ancores: dict[int, tuple[float, float]] = {}
    for j, p in enumerate(pts):
        if p.kind is PointKind.TURN:
            ancores[j] = explicits.get(j, (0.0, 0.0))
    for j, d in explicits.items():
        if j not in ancores:
            ancores[j] = d
            if pts[j].kind is PointKind.CURVE:
                avisos.append(MoveIssue(
                    'delta_sobre_corba',
                    f'S\'ha mogut un punt de CORBA (vora {index_vora}, ordre {j}): deixa de '
                    f'fluir i passa a ancorar el reflow dels seus veïns.',
                    peca=nom_peca, detall={'vora': index_vora, 'ordre': j},
                ))

    if not ancores:
        if explicits:
            avisos.append(MoveIssue(
                'vora_sense_ancora',
                f'La vora {index_vora} no té cap punt de gir: no hi ha res que ancori el '
                f'reflow i els seus punts no es mouen.',
                peca=nom_peca, detall={'vora': index_vora},
            ))
        return [(0.0, 0.0)] * n, 0, 0, avisos

    n_moguts = sum(1 for d in explicits.values() if d != (0.0, 0.0))

    if len(ancores) == 1:
        # Un sol ancoratge: no hi ha entre què interpolar. La vora es mou sencera i rígida
        # — que és el que un patronista faria amb una peça que penja d'un sol punt.
        (dx, dy), = ancores.values()
        return [(dx, dy)] * n, n_moguts, n - len(ancores), avisos

    segments = _longituds_segments(boundary)
    desp: list[Optional[tuple[float, float]]] = [None] * n
    for j, d in ancores.items():
        desp[j] = d

    ordenades = sorted(ancores)
    n_reflow = 0

    for j in range(n):
        if desp[j] is not None:
            continue
        prev_a, next_a = _ancores_veines(j, ordenades, n, boundary.closed)
        if prev_a is None or next_a is None:
            # Vora oberta, punt fora del rang d'ancoratges: segueix l'ancoratge que té.
            unica = next_a if prev_a is None else prev_a
            desp[j] = ancores[unica]
            n_reflow += 1
            continue

        arc_fins = _arc(segments, prev_a, j, n, boundary.closed)
        arc_total = _arc(segments, prev_a, next_a, n, boundary.closed)
        r = (arc_fins / arc_total) if arc_total > 0 else 0.0

        dax, day = ancores[prev_a]
        dbx, dby = ancores[next_a]
        desp[j] = (dax + (dbx - dax) * r, day + (dby - day) * r)
        n_reflow += 1

    return [d or (0.0, 0.0) for d in desp], n_moguts, n_reflow, avisos


def _longituds_segments(boundary: BoundaryData) -> list[float]:
    """Longitud de cada tram entre vèrtexs consecutius. En una vora tancada, l'últim tram
    torna al primer punt (el model intern no repeteix el vèrtex de tancament)."""
    pts = boundary.points
    n = len(pts)
    llargs = [
        hypot(pts[(i + 1) % n].x - pts[i].x, pts[(i + 1) % n].y - pts[i].y)
        for i in range(n)
    ]
    if not boundary.closed and n:
        llargs[n - 1] = 0.0  # en una vora oberta no hi ha tram de tancament
    return llargs


def _ancores_veines(
    j: int, ordenades: list[int], n: int, closed: bool
) -> tuple[Optional[int], Optional[int]]:
    """Els dos ancoratges que emmarquen el punt j (donant la volta si la vora és tancada)."""
    prev_a = next((a for a in reversed(ordenades) if a < j), None)
    next_a = next((a for a in ordenades if a > j), None)
    if closed:
        if prev_a is None:
            prev_a = ordenades[-1]   # l'últim, per l'altra banda del tancament
        if next_a is None:
            next_a = ordenades[0]
    return prev_a, next_a


def _arc(segments: list[float], desde: int, fins: int, n: int, closed: bool) -> float:
    """Longitud d'arc de `desde` a `fins` seguint la vora endavant."""
    total = 0.0
    i = desde
    voltes = 0
    while i != fins:
        total += segments[i]
        i = (i + 1) % n
        voltes += 1
        if voltes > n:
            return total  # xarxa de seguretat: mai un bucle infinit per un índex dolent
        if not closed and i == 0:
            break
    return total


def _propagar_al_cosit(
    piece: PieceData, desplacaments: list[list[tuple[float, float]]]
) -> tuple[int, list[MoveIssue]]:
    """La línia de cosit segueix el tall per CORRESPONDÈNCIA (v. docstring del mòdul).

    Cada punt de gir del cosit s'aparella amb el punt de gir del tall que té més a prop i
    n'hereta el desplaçament; els punts de corba del cosit ja han fluït entre els seus
    girs a `_desplacaments_vora`. Amb això el marge de costura es conserva a totes les
    talles, que és la invariant que ha d'aguantar. **Muta `desplacaments` in situ** (és
    una llista de treball, no el document).
    """
    avisos: list[MoveIssue] = []
    idx_tall = next(
        (i for i, b in enumerate(piece.boundaries) if b.role is LayerRole.CUT), None
    )
    if idx_tall is None:
        return 0, [MoveIssue(
            'cosit_sense_tall',
            'La peça porta línia de cosit però no en té cap de tall: no hi ha res amb què '
            'fer-la correspondre.',
            peca=piece.nom_block,
        )]

    tall = piece.boundaries[idx_tall]
    girs_tall = [j for j, p in enumerate(tall.points) if p.kind is PointKind.TURN]
    if not girs_tall:
        return 0, [MoveIssue(
            'cosit_sense_girs',
            'El contorn de tall no té punts de gir: la línia de cosit no s\'hi pot '
            'aparellar.',
            peca=piece.nom_block,
        )]

    propagats = 0
    for i, boundary in enumerate(piece.boundaries):
        if boundary.role is not LayerRole.SEW:
            continue

        girs_cosit = [j for j, p in enumerate(boundary.points) if p.kind is PointKind.TURN]
        parelles: dict[int, int] = {}
        for j in girs_cosit:
            q = boundary.points[j]
            k = min(girs_tall, key=lambda t: hypot(
                tall.points[t].x - q.x, tall.points[t].y - q.y))
            d = hypot(tall.points[k].x - q.x, tall.points[k].y - q.y)
            if d > TOL_PARELLA_COSIT_MM:
                avisos.append(MoveIssue(
                    'cosit_sense_parella',
                    f'El punt de gir {j} de la línia de cosit no té cap company al tall a '
                    f'menys de {TOL_PARELLA_COSIT_MM:.0f} mm (el més proper és a '
                    f'{d:.1f} mm): no se li propaga cap moviment.',
                    peca=piece.nom_block, detall={'vora': i, 'ordre': j, 'distancia_mm': d},
                ))
                continue
            parelles[j] = k

        if not parelles:
            continue

        for j, k in parelles.items():
            desplacaments[i][j] = desplacaments[idx_tall][k]
            propagats += 1

        # Els punts de corba del cosit tornen a fluir, ara entre girs que ja s'han mogut.
        refluits, _, _, _ = _desplacaments_vora(
            boundary, i, piece.nom_block,
            {PointRef(piece.nom_block, i, j): desplacaments[i][j] for j in parelles},
        )
        desplacaments[i] = refluits

    return propagats, avisos


def _reposicionar_piquets(
    piece: PieceData,
    vores_noves: tuple[BoundaryData, ...],
    desplacaments: list[list[tuple[float, float]]],
) -> tuple[tuple[NotchData, ...], int, list[MoveIssue]]:
    """Cada piquet torna a la MATEIXA posició paramètrica sobre la seva vora.

    No es trasllada per delta: es projecta. Un piquet és una marca SOBRE una vora, i si la
    vora s'estira, la marca s'estira amb ella.
    """
    avisos: list[MoveIssue] = []
    if not piece.notches:
        return (), 0, avisos

    idx_tall = next(
        (i for i, b in enumerate(piece.boundaries) if b.role is LayerRole.CUT), None
    )
    if idx_tall is None:
        return piece.notches, 0, [MoveIssue(
            'piquets_sense_vora',
            'La peça té piquets però cap contorn de tall: no es poden reposicionar.',
            peca=piece.nom_block,
        )]

    vella = piece.boundaries[idx_tall]
    nova = vores_noves[idx_tall]
    nous: list[NotchData] = []
    reposicionats = 0

    for n_i, notch in enumerate(piece.notches):
        k, t, dist = _projeccio_sobre_vora(vella, notch.x, notch.y)
        if k is None:
            nous.append(notch)
            continue

        if dist > TOL_PIQUET_MM:
            # No seu sobre la vora: no se l'hi enganxa a la força. Se'l trasllada com el
            # vèrtex que té més a prop i es diu que això ha passat.
            j = _vertex_mes_proper(vella, notch.x, notch.y)
            dx, dy = desplacaments[idx_tall][j]
            nous.append(replace(notch, x=notch.x + dx, y=notch.y + dy))
            reposicionats += 1
            avisos.append(MoveIssue(
                'piquet_fora_de_vora',
                f'El piquet {n_i} és a {dist:.2f} mm del contorn de tall (tolerància '
                f'{TOL_PIQUET_MM} mm): no s\'ha pogut reposicionar sobre la vora i s\'ha '
                f'traslladat com el vèrtex més proper.',
                peca=piece.nom_block, detall={'piquet': n_i, 'distancia_mm': dist},
            ))
            continue

        m = len(nova.points)
        a = nova.points[k]
        b = nova.points[(k + 1) % m]
        nous.append(replace(notch, x=a.x + (b.x - a.x) * t, y=a.y + (b.y - a.y) * t))
        reposicionats += 1

    return tuple(nous), reposicionats, avisos


def _projeccio_sobre_vora(
    boundary: BoundaryData, x: float, y: float
) -> tuple[Optional[int], float, float]:
    """Sobre quin tram de la vora seu aquest punt, i a quina fracció → (k, t, distància)."""
    pts = boundary.points
    n = len(pts)
    if n < 2:
        return None, 0.0, 0.0

    ultim = n if boundary.closed else n - 1
    millor_k, millor_t, millor_d = None, 0.0, float('inf')

    for k in range(ultim):
        a, b = pts[k], pts[(k + 1) % n]
        vx, vy = b.x - a.x, b.y - a.y
        l2 = vx * vx + vy * vy
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((x - a.x) * vx + (y - a.y) * vy) / l2))
        d = hypot(x - (a.x + t * vx), y - (a.y + t * vy))
        if d < millor_d:
            millor_k, millor_t, millor_d = k, t, d

    return millor_k, millor_t, millor_d


def _vertex_mes_proper(boundary: BoundaryData, x: float, y: float) -> int:
    return min(
        range(len(boundary.points)),
        key=lambda j: hypot(boundary.points[j].x - x, boundary.points[j].y - y),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Postcondicions: rellegir el que la geometria ara diu
# ─────────────────────────────────────────────────────────────────────────────

def _rellegir_poms(
    doc: PatternDocument, poms: tuple[POMSpec, ...], avisos: list[MoveIssue]
) -> list[POMReading]:
    """El valor d'un POM no es recalcula: es torna a LLEGIR de la geometria moguda."""
    lectures: list[POMReading] = []

    for spec in poms:
        piece = doc.piece(spec.peca)
        if piece is None:
            avisos.append(MoveIssue(
                'pom_sense_peca',
                f'El POM {spec.pom_code} apunta a la peça «{spec.peca}», que no és al '
                f'document.',
                peca=spec.peca, detall={'pom': spec.pom_code},
            ))
            lectures.append(POMReading(spec.pom_code, spec.peca, None,
                                       error=f'La peça «{spec.peca}» no hi és.'))
            continue

        punts_per_ref = {
            PointRef(piece.nom_block, i, j): p
            for i, b in enumerate(piece.boundaries)
            for j, p in enumerate(b.points)
        }
        try:
            res = resoldre(
                piece,
                {'mode': 'points', 'a': spec.ref_a, 'b': spec.ref_b},
                punts_per_ref,
                spec.metode,
            )
        except MeasureError as e:
            avisos.append(MoveIssue(
                'pom_no_mesurable',
                f'El POM {spec.pom_code} no s\'ha pogut rellegir: {e}',
                peca=spec.peca, detall={'pom': spec.pom_code},
            ))
            lectures.append(POMReading(spec.pom_code, spec.peca, None, error=str(e)))
            continue

        lectures.append(POMReading(
            spec.pom_code, spec.peca, res.valor_cm, tuple(res.punts),
        ))

    return lectures


def _revalidar_costures(
    doc_vell: PatternDocument,
    doc_nou: PatternDocument,
    sews: tuple[SewSpec, ...],
    avisos: list[MoveIssue],
) -> list[SewReading]:
    """Les costures que casaven a la talla mostra, ¿casen encara aquí?

    Els trams s'identifiquen per la seva posició paramètrica sobre la vora ORIGINAL (que
    és on es van declarar) i es MESUREN sobre la vora nova. L'operació no crea ni destrueix
    vèrtexs, així que el rang d'índexs val per als dos documents: el mateix tram, mogut.
    """
    lectures: list[SewReading] = []

    for spec in sews:
        try:
            llarg_a = sum(_longitud_tram(doc_vell, doc_nou, s) for s in spec.costat_a)
            llarg_b = sum(_longitud_tram(doc_vell, doc_nou, s) for s in spec.costat_b)
        except MeasureError as e:
            avisos.append(MoveIssue(
                'costura_no_mesurable',
                f'La costura {spec.sew_id} no s\'ha pogut revalidar: {e}',
                detall={'costura': spec.sew_id},
            ))
            lectures.append(SewReading(spec.sew_id, None, error=str(e)))
            continue

        lectures.append(SewReading(
            spec.sew_id,
            validar(llarg_a, llarg_b, spec.tipus, spec.diferencial_cm),
        ))

    return lectures


def _longitud_tram(
    doc_vell: PatternDocument, doc_nou: PatternDocument, seg: SegRef
) -> float:
    """Longitud (mm) del tram, mesurada sobre el document NOU."""
    peca_vella = doc_vell.piece(seg.peca)
    peca_nova = doc_nou.piece(seg.peca)
    if peca_vella is None or peca_nova is None:
        raise MeasureError(f'La peça «{seg.peca}» no és al document.')
    if seg.vora >= len(peca_vella.boundaries):
        raise MeasureError(
            f'La vora {seg.vora} no és a la peça «{seg.peca}».')

    i0, i1 = _indexs_del_rang(peca_vella.boundaries[seg.vora], seg.vora,
                              seg.t_inici, seg.t_fi)
    return _longitud_indexs(peca_nova.boundaries[seg.vora], i0, i1)


def _indexs_del_rang(
    boundary: BoundaryData, index_vora: int, t_inici: float, t_fi: float
) -> tuple[int, int]:
    """(t_inici, t_fi) → els índexs de vèrtex que emmarquen el tram, a la vora ORIGINAL.

    Es tornen a derivar els trams amb `segmentar_vora` —la MATEIXA funció que els va crear
    quan es va importar el patró— i es busca el que té aquests `t`. No es reconstrueixen
    els índexs comptant longitud d'arc des del vèrtex 0, i la raó és fina però mossega:
    **l'origen de `t` no és el vèrtex 0, és el primer punt de GIR** de la vora. Coincideixen
    només quan el vèrtex 0 resulta ser un gir (que és el cas a l'AMELIA, i per això l'error
    passaria desapercebut fins al dia que arribés una peça que comencés per un punt de
    corba). Preguntar-ho a qui ho sap és més barat que tornar-ho a deduir malament.
    """
    for sd in segmentar_vora(boundary, index_vora):
        if abs(sd.t_inici - t_inici) < 1e-6 and abs(sd.t_fi - t_fi) < 1e-6:
            return sd.index_inici, sd.index_fi

    raise MeasureError(
        f'El tram [{t_inici:.4f}–{t_fi:.4f}] de la vora {index_vora} no correspon a cap '
        f'tram de gir a gir de la geometria actual: la costura es va declarar sobre una '
        f'altra versió del patró.'
    )


def _longitud_indexs(boundary: BoundaryData, i0: int, i1: int) -> float:
    """Longitud de la polilínia que va del vèrtex i0 al i1, endavant (donant la volta si cal)."""
    pts = boundary.points
    n = len(pts)
    if n < 2 or i0 == i1:
        return 0.0

    total = 0.0
    i = i0
    voltes = 0
    while i != i1:
        seguent = (i + 1) % n
        total += hypot(pts[seguent].x - pts[i].x, pts[seguent].y - pts[i].y)
        i = seguent
        voltes += 1
        if voltes > n:
            break
    return total


# ─────────────────────────────────────────────────────────────────────────────
# Utilitat per als consumidors (S7-T2/T3): quin delta ha acabat tenint cada punt
# ─────────────────────────────────────────────────────────────────────────────

def deltes_resultants(
    original: PatternDocument, mogut: PatternDocument
) -> dict[PointRef, tuple[float, float]]:
    """El que s'ha mogut CADA punt, de debò: girs, corbes reflowades i piquets.

    És el que la projecció necessita per escriure el RUL: la regla d'un punt no és el que
    li vam demanar, és **on ha acabat**. Els punts de corba, per exemple, no reben cap
    ordre i tot i així es mouen.
    """
    fora: dict[PointRef, tuple[float, float]] = {}

    for pv in original.pieces:
        pn = mogut.piece(pv.nom_block)
        if pn is None:
            continue

        for i, (bv, bn) in enumerate(zip(pv.boundaries, pn.boundaries)):
            for j, (a, b) in enumerate(zip(bv.points, bn.points)):
                fora[PointRef(pv.nom_block, i, j)] = (b.x - a.x, b.y - a.y)

        for j, (a, b) in enumerate(zip(pv.notches, pn.notches)):
            fora[PointRef(pv.nom_block, None, j)] = (b.x - a.x, b.y - a.y)

    return fora
