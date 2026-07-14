"""Comparador round-trip: dos documents són el mateix patró?

**Eina permanent, no bastida de test.** És la validació barata de tota exportació que
farem d'ara endavant (S7 la crida abans de deixar sortir un fitxer per la porta) i és
l'instrument de la prova Montse: exportem un DXF amb la capa FTT-POM, ella el fa passar
pel seu CAD, ens el torna, i això diu **exactament** què li ha fet pel camí.

La comparació és SEMÀNTICA, no de bytes. Un DXF pot canviar de mida, d'ordre d'entitats
i de handles sense que el patró hagi canviat gens; i pot conservar la mida mentre un
punt ha marxat dos mil·límetres. El que compara és el que un patronista consideraria el
mateix patró:

  · les mateixes peces, amb els mateixos noms;
  · els mateixos punts, cadascun al seu lloc **dins d'una tolerància en micres**;
  · les mateixes capes, i les mateixes que no enteníem;
  · les mateixes metadades i els mateixos POMs ancorats;
  · la mateixa taula de grading.

La tolerància per defecte (1 µm) és deliberadament dura: la reproducció pura ha de ser
exacta. Per a un round-trip que ha passat per un CAD de tercers, la Montse dirà quina
tolerància és raonable — i per això és un paràmetre i no una constant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .geometry import GradeTable, LayerRole, PatternDocument, PieceData

#: Tolerància per defecte: 1 µm. Per a reproducció pura, qualsevol cosa més laxa
#: amagaria errors de veritat.
DEFAULT_TOL_UM = 1.0

MM_PER_UM = 0.001


@dataclass(frozen=True)
class Difference:
    """Una diferència concreta, amb prou detall per anar-la a buscar."""
    tipus: str                       # 'piece_missing', 'point_moved', 'layer_missing'…
    missatge: str
    peca: Optional[str] = None
    detall: dict = field(default_factory=dict)

    def __str__(self) -> str:
        on = f' [{self.peca}]' if self.peca else ''
        return f'{self.tipus}{on}: {self.missatge}'


@dataclass(frozen=True)
class RoundtripReport:
    """El veredicte. `ok` només si no hi ha ni una diferència."""
    diferencies: tuple[Difference, ...] = ()
    desviacio_maxima_um: float = 0.0
    punts_comparats: int = 0
    tolerancia_um: float = DEFAULT_TOL_UM

    @property
    def ok(self) -> bool:
        return not self.diferencies

    def resum(self) -> str:
        if self.ok:
            return (
                f'✅ Round-trip idèntic: {self.punts_comparats} punts comparats, '
                f'desviació màxima {self.desviacio_maxima_um:.3f} µm '
                f'(tolerància {self.tolerancia_um:.1f} µm).'
            )
        linies = [
            f'❌ {len(self.diferencies)} diferències '
            f'({self.punts_comparats} punts comparats, desviació màxima '
            f'{self.desviacio_maxima_um:.3f} µm, tolerància {self.tolerancia_um:.1f} µm):'
        ]
        linies += [f'  · {d}' for d in self.diferencies[:20]]
        if len(self.diferencies) > 20:
            linies.append(f'  … i {len(self.diferencies) - 20} més.')
        return '\n'.join(linies)


def compare(
    a: PatternDocument,
    b: PatternDocument,
    tol_um: float = DEFAULT_TOL_UM,
    comparar_empremta: bool = True,
    comparar_grading: bool = True,
) -> RoundtripReport:
    """Compara dos documents. `a` és la referència; `b`, el que ha tornat del viatge.

    `comparar_grading=False` quan l'altra banda és un **DXF tot sol**: un DXF no porta
    taula de regles —la porta el RUL, que és un fitxer germà i un artefacte a part— i
    trobar-hi a faltar una cosa que aquell format no pot contenir no és detectar un
    defecte, és comparar peres amb pomes. La taula es compara amb `compare_grade_tables`
    sobre el RUL, que és on viu.
    """
    tol_mm = tol_um * MM_PER_UM
    diffs: list[Difference] = []
    max_dev = 0.0
    punts = 0

    noms_a, noms_b = a.noms_peces, b.noms_peces
    for nom in noms_a:
        if nom not in noms_b:
            diffs.append(Difference('piece_missing', 'La peça ha desaparegut.', peca=nom))
    for nom in noms_b:
        if nom not in noms_a:
            diffs.append(Difference('piece_added', 'Ha aparegut una peça que no hi era.', peca=nom))

    for nom in noms_a:
        if nom not in noms_b:
            continue
        d, dev, n = _compare_piece(a.piece(nom), b.piece(nom), tol_mm)
        diffs += d
        max_dev = max(max_dev, dev)
        punts += n

    if comparar_empremta:
        diffs += _compare_fingerprint(a, b)

    if comparar_grading:
        diffs += _compare_grading(a.grade_table, b.grade_table)

    return RoundtripReport(
        diferencies=tuple(diffs),
        desviacio_maxima_um=max_dev / MM_PER_UM,
        punts_comparats=punts,
        tolerancia_um=tol_um,
    )


def compare_grade_tables(
    a: Optional[GradeTable],
    b: Optional[GradeTable],
    tol_deltes: float = 0.0,
) -> RoundtripReport:
    """Compara només les taules de grading (per al round-trip del RUL tot sol).

    `tol_deltes` (en les unitats dels deltes, mm) existeix perquè **el RUL és un canal amb
    resolució pròpia**: el format real de PolyPattern escriu els deltes amb DOS decimals, i
    el writer el reprodueix byte a byte perquè aquesta fidelitat és el que fa que el fitxer
    torni a ser seu. La conseqüència és que un delta de 3.439 mm surt escrit com a 3.44:
    el fitxer quantitza a 0.01 mm i no hi ha manera d'evitar-ho sense emetre un RUL que el
    seu CAD ja no reconeixeria.

    Per això, exigir igualtat EXACTA de floats a un round-trip de RUL és demanar-li al
    format una precisió que no té. Amb `tol_deltes=0` (per defecte) la comparació continua
    sent exacta —que és el que volen els tests de reproducció pura, on els deltes ja venen
    del fitxer i hi tornen sense passar per cap càlcul—; qui hi escrigui deltes calculats
    hi ha de passar la resolució del format.
    """
    return RoundtripReport(diferencies=tuple(_compare_grading(a, b, tol_deltes)))


# ─────────────────────────────────────────────────────────────────────────────

def _compare_piece(
    pa: PieceData, pb: PieceData, tol_mm: float
) -> tuple[list[Difference], float, int]:
    diffs: list[Difference] = []
    max_dev = 0.0
    punts = 0
    nom = pa.nom_block

    # Vores, per rol: comparar capa a capa és el que localitza el problema.
    for role in LayerRole:
        ba = pa.boundaries_of(role)
        bb = pb.boundaries_of(role)
        if len(ba) != len(bb):
            diffs.append(Difference(
                'boundary_count',
                f'{len(ba)} vores de tipus {role.value} a l\'original i {len(bb)} a la còpia.',
                peca=nom, detall={'role': role.value, 'a': len(ba), 'b': len(bb)},
            ))
            continue

        for i, (va, vb) in enumerate(zip(ba, bb)):
            if len(va.points) != len(vb.points):
                diffs.append(Difference(
                    'point_count',
                    f'La vora {role.value}#{i} tenia {len(va.points)} punts i ara en té '
                    f'{len(vb.points)}.',
                    peca=nom, detall={'role': role.value, 'a': len(va.points), 'b': len(vb.points)},
                ))
                continue
            if va.closed != vb.closed:
                diffs.append(Difference(
                    'boundary_closed',
                    f'La vora {role.value}#{i} ha canviat de tancada a oberta (o al revés).',
                    peca=nom,
                ))

            for j, (qa, qb) in enumerate(zip(va.points, vb.points)):
                punts += 1
                dev = max(abs(qa.x - qb.x), abs(qa.y - qb.y))
                max_dev = max(max_dev, dev)
                if dev > tol_mm:
                    diffs.append(Difference(
                        'point_moved',
                        f'El punt {j} de la vora {role.value}#{i} s\'ha mogut '
                        f'{dev / MM_PER_UM:.1f} µm.',
                        peca=nom,
                        detall={
                            'role': role.value, 'index': j,
                            'a': (qa.x, qa.y), 'b': (qb.x, qb.y),
                            'desviacio_um': dev / MM_PER_UM,
                        },
                    ))
                if qa.kind is not qb.kind:
                    diffs.append(Difference(
                        'point_kind',
                        f'El punt {j} de la vora {role.value}#{i} era {qa.kind.value} '
                        f'i ara és {qb.kind.value}.',
                        peca=nom, detall={'index': j},
                    ))
                if qa.grade_rule != qb.grade_rule:
                    diffs.append(Difference(
                        'point_grade_rule',
                        f'El punt {j} de la vora {role.value}#{i} tenia la regla '
                        f'{qa.grade_rule} i ara té {qb.grade_rule}.',
                        peca=nom, detall={'index': j},
                    ))

    if len(pa.notches) != len(pb.notches):
        diffs.append(Difference(
            'notch_count',
            f'{len(pa.notches)} piquets a l\'original, {len(pb.notches)} a la còpia.',
            peca=nom,
        ))
    else:
        for j, (na, nb) in enumerate(zip(pa.notches, pb.notches)):
            dev = max(abs(na.x - nb.x), abs(na.y - nb.y))
            max_dev = max(max_dev, dev)
            punts += 1
            if dev > tol_mm:
                diffs.append(Difference(
                    'notch_moved',
                    f'El piquet {j} s\'ha mogut {dev / MM_PER_UM:.1f} µm.',
                    peca=nom, detall={'index': j, 'desviacio_um': dev / MM_PER_UM},
                ))

    if (pa.grain is None) != (pb.grain is None):
        diffs.append(Difference('grain_missing', 'El fil de la roba ha aparegut o desaparegut.',
                                peca=nom))

    if pa.metadata != pb.metadata:
        diffs.append(Difference(
            'metadata',
            f'Les metadades de la peça han canviat: {pa.metadata} → {pb.metadata}.',
            peca=nom,
        ))

    if pa.unknown_layers != pb.unknown_layers:
        diffs.append(Difference(
            'unknown_layers',
            f'Les capes no catalogades han canviat: {pa.unknown_layers} → '
            f'{pb.unknown_layers}. (El CAD del mig se n\'ha menjat alguna.)',
            peca=nom,
        ))

    if pa.has_sew != pb.has_sew or pa.has_fold != pb.has_fold:
        diffs.append(Difference(
            'capabilities',
            f'Els flags de capacitat han canviat: has_sew {pa.has_sew}→{pb.has_sew}, '
            f'has_fold {pa.has_fold}→{pb.has_fold}.',
            peca=nom,
        ))

    diffs += _compare_poms(pa, pb, tol_mm)
    return diffs, max_dev, punts


def _compare_poms(pa: PieceData, pb: PieceData, tol_mm: float) -> list[Difference]:
    """Els POMs de la capa FTT-POM: el que la prova Montse vol saber de debò."""
    diffs: list[Difference] = []
    codis_a = {p.pom_code for p in pa.poms}
    codis_b = {p.pom_code for p in pb.poms}

    for codi in sorted(codis_a - codis_b):
        diffs.append(Difference(
            'pom_lost',
            f'El POM {codi} no ha sobreviscut al viatge.',
            peca=pa.nom_block, detall={'pom': codi},
        ))
    for codi in sorted(codis_b - codis_a):
        diffs.append(Difference(
            'pom_added', f'Ha aparegut un POM que no hi era: {codi}.',
            peca=pa.nom_block, detall={'pom': codi},
        ))

    per_codi = {p.pom_code: p for p in pb.poms}
    for pom in pa.poms:
        altre = per_codi.get(pom.pom_code)
        if altre is None:
            continue
        va, vb = pom.valor_mesurat_mm, altre.valor_mesurat_mm
        if va is not None and vb is not None and abs(va - vb) > tol_mm:
            diffs.append(Difference(
                'pom_value',
                f'El POM {pom.pom_code} valia {va:.2f} mm i ara val {vb:.2f} mm.',
                peca=pa.nom_block, detall={'pom': pom.pom_code, 'a': va, 'b': vb},
            ))
        if len(pom.punts_ancora) != len(altre.punts_ancora):
            diffs.append(Difference(
                'pom_anchor',
                f'El POM {pom.pom_code} tenia {len(pom.punts_ancora)} punts d\'ancoratge '
                f'i ara en té {len(altre.punts_ancora)}.',
                peca=pa.nom_block, detall={'pom': pom.pom_code},
            ))
    return diffs


def _compare_fingerprint(a: PatternDocument, b: PatternDocument) -> list[Difference]:
    diffs: list[Difference] = []
    fa, fb = a.fingerprint, b.fingerprint

    if set(fa.capes_presents) != set(fb.capes_presents):
        perdudes = set(fa.capes_presents) - set(fb.capes_presents)
        noves = set(fb.capes_presents) - set(fa.capes_presents)
        diffs.append(Difference(
            'layers',
            f'Les capes del fitxer han canviat. Perdudes: {sorted(perdudes) or "cap"}; '
            f'noves: {sorted(noves) or "cap"}.',
            detall={'perdudes': sorted(perdudes), 'noves': sorted(noves)},
        ))

    if set(fa.textos_document) != set(fb.textos_document):
        diffs.append(Difference(
            'document_texts',
            f'Els TEXT de metadades del document han canviat: '
            f'{sorted(set(fa.textos_document) ^ set(fb.textos_document))}.',
        ))

    ua, ub = fa.unitats, fb.unitats
    if ua and ub and ua.factor_to_mm != ub.factor_to_mm:
        diffs.append(Difference(
            'units',
            f'El factor d\'unitats ha canviat: {ua.factor_to_mm} → {ub.factor_to_mm}. '
            f'(El fitxer ha canviat d\'escala.)',
        ))

    if fa.separador_decimal != fb.separador_decimal:
        diffs.append(Difference(
            'decimal_separator',
            f'El separador decimal ha canviat: {fa.separador_decimal} → {fb.separador_decimal}.',
        ))

    return diffs


def _compare_grading(
    a: Optional[GradeTable],
    b: Optional[GradeTable],
    tol_deltes: float = 0.0,
) -> list[Difference]:
    if a is None and b is None:
        return []
    if a is None or b is None:
        return [Difference('grade_table', 'La taula de grading hi és a un document i a l\'altre no.')]

    diffs: list[Difference] = []
    if a.talles != b.talles:
        diffs.append(Difference(
            'sizes', f'Les talles han canviat: {a.talles} → {b.talles}.'))
    if a.talla_base != b.talla_base:
        diffs.append(Difference(
            'base_size', f'La talla base ha canviat: {a.talla_base} → {b.talla_base}.'))
    if set(a.regles) != set(b.regles):
        diffs.append(Difference(
            'rules', f'Les regles han canviat: {sorted(a.regles)} → {sorted(b.regles)}.'))
    else:
        for numero, regla in a.regles.items():
            altres = b.regles[numero].deltes
            if _deltes_iguals(regla.deltes, altres, tol_deltes):
                continue
            diffs.append(Difference(
                'rule_deltas',
                f'Els deltes de la regla {numero} han canviat.',
                detall={'regla': numero, 'a': regla.deltes, 'b': altres},
            ))
    return diffs


def _deltes_iguals(a: dict, b: dict, tol: float) -> bool:
    if set(a) != set(b):
        return False
    if tol <= 0:
        return a == b
    for talla, (ax, ay) in a.items():
        bx, by = b[talla]
        if abs(ax - bx) > tol or abs(ay - by) > tol:
            return False
    return True
