"""Adaptadors: dataclasses del motor ↔ ORM de Django.

Aquest fitxer és la **frontissa** de la frontera hexagonal, i és l'únic lloc del mòdul
que veu les dues bandes alhora. El motor (`engine/`) no sap que Django existeix; els
models no saben que hi ha un motor. Aquí es tradueix, en les dues direccions.

El viatge d'anada i tornada (`dataclasses → ORM → dataclasses`) ha de tornar el MATEIX
document, i això no és una aspiració: es comprova amb el comparador de S2, que és el
mateix que valida el round-trip dels fitxers. Si una traducció perd un camp, el
comparador ho canta.
"""
from django.db import transaction

from .engine.geometry import (
    BoundaryData,
    Confidence,
    Fingerprint,
    FoldData,
    GradeRuleData,
    GradeTable,
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
from .engine.operations import POMSpec, PointRef, SegRef, SewSpec
from .engine.ports import GradedPOMDelta, GradingSnapshot
from .engine.segments import segmentar_peca
from .models import PatternPiece, PatternPoint, PatternSegment


# ═════════════════════════════════════════════════════════════════════════════
# Empremta ↔ JSON
# ═════════════════════════════════════════════════════════════════════════════

def fingerprint_to_json(fp: Fingerprint) -> dict:
    unitats = None
    if fp.unitats:
        unitats = {
            'factor_to_mm': fp.unitats.factor_to_mm,
            'metode': fp.unitats.metode.value,
            'confianca': fp.unitats.confianca.value,
            'evidencia': fp.unitats.evidencia,
        }
    return {
        'font_cad': fp.font_cad,
        'dxf_version': fp.dxf_version,
        'aama_version': fp.aama_version,
        'autor': fp.autor,
        'ordre_seccions': list(fp.ordre_seccions),
        'capes_presents': list(fp.capes_presents),
        'capes_desconegudes': list(fp.capes_desconegudes),
        'capes_declarades': list(fp.capes_declarades),
        'separador_decimal': dict(fp.separador_decimal),
        'unitats': unitats,
        'cens_entitats': dict(fp.cens_entitats),
        'textos_document': list(fp.textos_document),
        'doc_text_anchor': list(fp.doc_text_anchor),
        'text_height': fp.text_height,
        'header_buida': fp.header_buida,
        'tables_buida': fp.tables_buida,
    }


def fingerprint_from_json(data: dict) -> Fingerprint:
    if not data:
        return Fingerprint()
    u = data.get('unitats')
    unitats = None
    if u:
        unitats = UnitsFingerprint(
            factor_to_mm=u['factor_to_mm'],
            metode=UnitsMethod(u['metode']),
            confianca=Confidence(u['confianca']),
            evidencia=u.get('evidencia', ''),
        )
    return Fingerprint(
        font_cad=data.get('font_cad', ''),
        dxf_version=data.get('dxf_version', ''),
        aama_version=data.get('aama_version', ''),
        autor=data.get('autor', ''),
        ordre_seccions=tuple(data.get('ordre_seccions', [])),
        capes_presents=tuple(data.get('capes_presents', [])),
        capes_desconegudes=tuple(data.get('capes_desconegudes', [])),
        capes_declarades=tuple(data.get('capes_declarades', [])),
        separador_decimal=dict(data.get('separador_decimal', {})),
        unitats=unitats,
        cens_entitats=dict(data.get('cens_entitats', {})),
        textos_document=tuple(data.get('textos_document', [])),
        doc_text_anchor=tuple(data.get('doc_text_anchor', [0.0, 0.0])),
        text_height=data.get('text_height', 0.0),
        header_buida=data.get('header_buida', False),
        tables_buida=data.get('tables_buida', False),
    )


# ═════════════════════════════════════════════════════════════════════════════
# Taula de grading (RUL) ↔ JSON
# ═════════════════════════════════════════════════════════════════════════════

def grade_table_to_json(table) -> dict | None:
    if table is None:
        return None
    return {
        'nom': table.nom,
        'talles': list(table.talles),
        'talla_base': table.talla_base,
        'unitats': table.unitats,
        'unitats_factor_mm': table.unitats_factor_mm,
        'aama_version': table.aama_version,
        'autor': table.autor,
        # Les claus de JSON són strings sempre: el número de regla torna a int en llegir.
        'regles': {
            str(num): {'deltes': {t: list(d) for t, d in regla.deltes.items()}}
            for num, regla in table.regles.items()
        },
    }


def grade_table_from_json(data) -> GradeTable | None:
    if not data:
        return None
    return GradeTable(
        nom=data.get('nom', ''),
        talles=tuple(data.get('talles', [])),
        talla_base=data.get('talla_base', ''),
        unitats=data.get('unitats', ''),
        unitats_factor_mm=data.get('unitats_factor_mm', 1.0),
        aama_version=data.get('aama_version', ''),
        autor=data.get('autor', ''),
        regles={
            int(num): GradeRuleData(
                numero=int(num),
                deltes={t: tuple(d) for t, d in regla['deltes'].items()},
            )
            for num, regla in data.get('regles', {}).items()
        },
    )


# ═════════════════════════════════════════════════════════════════════════════
# El port GeometryStore
# ═════════════════════════════════════════════════════════════════════════════

class DjangoGeometryStore:
    """Implementa el port `GeometryStore` d'`engine/ports.py`.

    El motor només en coneix dos verbs: `save` i `load`. Que a l'altra banda hi hagi
    Postgres, un fitxer o un núvol, no li importa gens ni ha de saber-ho.
    """

    @transaction.atomic
    def save(self, doc: PatternDocument, pattern_file=None, **context) -> int:
        """Escriu el document SENCER sota un `PatternFile` existent.

        Sencer vol dir sencer: geometria, empremta i taula de grading. El port promet que
        `load(save(doc)) ≡ doc`, i una promesa a mitges no és una promesa — un `save` que
        només desés les peces deixaria el fitxer sense empremta i, per tant, impossible de
        reproduir a l'exportació, que és precisament per a què serveix.

        Reescriu les peces senceres: un `PatternFile` és immutable de facto (una versió
        nova és una fila nova), així que no hi ha cap fusió delicada a fer.
        """
        if pattern_file is None:
            raise ValueError('Cal un PatternFile on penjar la geometria.')

        pattern_file.pieces.all().delete()
        pattern_file.empremta = fingerprint_to_json(doc.fingerprint)
        pattern_file.grade_table = grade_table_to_json(doc.grade_table)
        pattern_file.save(update_fields=['empremta', 'grade_table'])

        for piece in doc.pieces:
            self._save_piece(pattern_file, piece)

        return pattern_file.id

    def load(self, pattern_file_id: int) -> PatternDocument:
        from .models import PatternFile

        fp = (
            PatternFile.objects
            .prefetch_related('pieces__points')
            .get(pk=pattern_file_id)
        )
        return self.load_from(fp)

    def load_from(self, fp) -> PatternDocument:
        """Igual que `load`, però amb la fila ja carregada (estalvia una consulta)."""
        return PatternDocument(
            pieces=tuple(self._load_piece(p) for p in fp.pieces.all()),
            fingerprint=fingerprint_from_json(fp.empremta),
            grade_table=grade_table_from_json(fp.grade_table),
        )

    # ── peça ────────────────────────────────────────────────────────────────
    def _save_piece(self, pattern_file, piece: PieceData) -> PatternPiece:
        row = PatternPiece.objects.create(
            pattern_file=pattern_file,
            nom_block=piece.nom_block,
            rol=piece.rol or '',
            contorns=[
                {
                    'index': i,
                    'role': b.role.value,
                    'layer': b.layer,
                    'closed': b.closed,
                }
                for i, b in enumerate(piece.boundaries)
            ],
            grain=(
                {'x1': piece.grain.x1, 'y1': piece.grain.y1,
                 'x2': piece.grain.x2, 'y2': piece.grain.y2}
                if piece.grain else None
            ),
            metadata={
                'piece_name': piece.metadata.piece_name,
                'size': piece.metadata.size,
                'quantity': piece.metadata.quantity,
                'material': piece.metadata.material,
                'extra': dict(piece.metadata.extra),
                'anchor': list(piece.metadata.anchor),
            },
            raw_entities=[
                {
                    'dxftype': r.dxftype,
                    'layer': r.layer,
                    'punts': [list(p) for p in r.punts],
                    'text': r.text,
                    'height': r.height,
                }
                for r in piece.raw_entities
            ],
            doblec_original=(
                {
                    'eix_x1': piece.doblec_original.eix_x1,
                    'eix_y1': piece.doblec_original.eix_y1,
                    'eix_x2': piece.doblec_original.eix_x2,
                    'eix_y2': piece.doblec_original.eix_y2,
                    'materialitzat': piece.doblec_original.materialitzat,
                    'costat': piece.doblec_original.costat,
                }
                if piece.doblec_original else None
            ),
            insert_at=list(piece.insert_at),
            has_sew=piece.has_sew,
            has_fold=piece.has_fold,
            unknown_layers=list(piece.unknown_layers),
        )

        punts = []
        for i, boundary in enumerate(piece.boundaries):
            for ordre, p in enumerate(boundary.points):
                punts.append(PatternPoint(
                    piece=row,
                    mena=PatternPoint.MENA_VERTEX,
                    boundary_index=i,
                    ordre=ordre,
                    x=p.x, y=p.y,
                    tipus=p.kind.value,
                    grade_rule_num=p.grade_rule,
                    rastre=_raw_trace_to_json(p.raw),
                ))
        for ordre, n in enumerate(piece.notches):
            punts.append(PatternPoint(
                piece=row,
                mena=PatternPoint.MENA_NOTCH,
                boundary_index=None,
                ordre=ordre,
                x=n.x, y=n.y,
                tipus=PatternPoint.TIPUS_UNCLASSIFIED,
                grade_rule_num=n.grade_rule,
                rastre=_raw_trace_to_json(n.raw),
            ))
        PatternPoint.objects.bulk_create(punts, batch_size=1000)
        self._save_segments(row, piece)
        return row

    def _save_segments(self, row: PatternPiece, piece: PieceData) -> None:
        """Els trams de gir a gir, derivats en importar.

        Es deriven ARA i no quan algú vulgui cosir, perquè són una propietat de la
        geometria, no una decisió de l'usuari: la peça ja ve amb les seves cantonades
        marcades pel CAD. Qui declari una costura només ha de triar entre trams que ja hi
        són.
        """
        segments = [
            PatternSegment(
                piece=row,
                vora=s.vora,
                t_inici=s.t_inici,
                t_fi=s.t_fi,
                tipus_vora=s.tipus_vora.value,
            )
            for s in segmentar_peca(piece)
        ]
        PatternSegment.objects.bulk_create(segments, batch_size=500)

    def _load_piece(self, row: PatternPiece) -> PieceData:
        vertexs: dict[int, list[PatternPoint]] = {}
        notches: list[PatternPoint] = []
        for p in row.points.all():
            if p.mena == PatternPoint.MENA_NOTCH:
                notches.append(p)
            else:
                vertexs.setdefault(p.boundary_index, []).append(p)

        boundaries = []
        for meta in row.contorns:
            i = meta['index']
            punts = sorted(vertexs.get(i, []), key=lambda p: p.ordre)
            boundaries.append(BoundaryData(
                role=LayerRole(meta['role']),
                layer=meta['layer'],
                closed=meta['closed'],
                points=tuple(
                    PointData(
                        x=p.x, y=p.y,
                        kind=PointKind(p.tipus),
                        grade_rule=p.grade_rule_num,
                        raw=_raw_trace_from_json(p.rastre),
                    )
                    for p in punts
                ),
            ))

        md = row.metadata or {}
        grain = row.grain
        fold = row.doblec_original

        return PieceData(
            nom_block=row.nom_block,
            boundaries=tuple(boundaries),
            notches=tuple(
                NotchData(
                    x=n.x, y=n.y,
                    grade_rule=n.grade_rule_num,
                    raw=_raw_trace_from_json(n.rastre),
                )
                for n in sorted(notches, key=lambda p: p.ordre)
            ),
            grain=(
                GrainLineData(grain['x1'], grain['y1'], grain['x2'], grain['y2'])
                if grain else None
            ),
            metadata=PieceMetadata(
                piece_name=md.get('piece_name', ''),
                size=md.get('size', ''),
                quantity=md.get('quantity'),
                material=md.get('material', ''),
                extra=dict(md.get('extra', {})),
                anchor=tuple(md.get('anchor', (0.0, 0.0))),
            ),
            rol=row.rol or None,
            doblec_original=(
                FoldData(
                    eix_x1=fold['eix_x1'], eix_y1=fold['eix_y1'],
                    eix_x2=fold['eix_x2'], eix_y2=fold['eix_y2'],
                    materialitzat=fold.get('materialitzat', False),
                    costat=fold.get('costat', 0),
                )
                if fold else None
            ),
            has_sew=row.has_sew,
            has_fold=row.has_fold,
            unknown_layers=tuple(row.unknown_layers or ()),
            raw_entities=tuple(
                RawEntity(
                    dxftype=r['dxftype'],
                    layer=r['layer'],
                    punts=tuple(tuple(p) for p in r.get('punts', [])),
                    text=r.get('text', ''),
                    height=r.get('height', 0.0),
                )
                for r in (row.raw_entities or [])
            ),
            insert_at=tuple(row.insert_at or (0.0, 0.0)),
        )


def _raw_trace_to_json(raw: RawTrace | None) -> dict | None:
    if raw is None:
        return None
    return {
        'dxftype': raw.dxftype,
        'layer': raw.layer,
        'handle': raw.handle,
        'extra': [list(e) for e in raw.extra],
    }


def _raw_trace_from_json(data) -> RawTrace | None:
    if not data:
        return None
    return RawTrace(
        dxftype=data.get('dxftype', ''),
        layer=data.get('layer', ''),
        handle=data.get('handle', ''),
        extra=tuple(tuple(e) for e in data.get('extra', [])),
    )


# ═════════════════════════════════════════════════════════════════════════════
# El port GradingSource — l'ÚNICA porta entre el motor i el grading de l'FTT
# ═════════════════════════════════════════════════════════════════════════════

class GradingVersionNotFound(Exception):
    """La versió de grading demanada no existeix."""


class DjangoGradingSource:
    """Implementa el port `GradingSource` (S0-B7.4) llegint `GradedSpec`.

    Les dues condicions que la diagnosi va deixar escrites per a aquest adaptador (B7,
    C1 i C2) no són consells: cadascuna tapa una manera concreta i documentada que el
    grading de l'FTT té d'enganyar qui el llegeixi.

    **C2 — el guard d'aprovació és `filter(pk=…)` + comprovar el flag, MAI
    `get(aprovada=True)`.** Estructuralment poden coexistir diverses `GradingVersion`
    aprovades del mateix `SizeFitting` (cap constraint no ho impedeix, i `seal_model_grading`
    marca l'aprovada sense desmarcar-ne cap d'anterior). El dia que passi, un
    `get(aprovada=True)` petaria amb `MultipleObjectsReturned` **en producció i en el
    moment d'exportar**. Aquí es demana una versió per PK i se li mira el flag; si no el
    té, es diu.

    **C1 — el context ve del MODEL, recorrent `grading_version.size_fitting.model`.**
    `GradingVersion` NO té FK a `Model`, i `GradedSpec` no sap quina és la talla base:
    la fila de la base no porta cap marca i el seu `increment_applied_cm == 0.0` només per
    coincidència aritmètica —un POM amb regla ZERO té l'increment a 0 a TOTES les talles—,
    de manera que **deduir la base pel delta zero és incorrecte**. Es llegeix declarada de
    `Model.base_size_label`, i el size run de `Model.size_run_model`.

    I una tercera cosa que no és una condició sinó un fet: `aprovada` i `is_active` són
    **ortogonals**. La versió aprovada d'un model sovint NO és la que la UI serveix (a
    staging, 3 de les 4 aprovades no són l'activa). Aquí es demana l'APROVADA, i punt: qui
    exporta tria la versió, no se li endevina.
    """

    def snapshot(self, grading_version_id: int) -> GradingSnapshot:
        from fhort.fitting.models import GradedSpec, GradingVersion

        # C2: per PK, i el flag es MIRA (no es filtra).
        gv = (
            GradingVersion.objects
            .filter(pk=grading_version_id)
            .select_related('size_fitting__model')
            .first()
        )
        if gv is None:
            raise GradingVersionNotFound(
                f'La versió de grading {grading_version_id} no existeix.')

        # C1: el context, recorregut explícitament fins al Model.
        model = gv.size_fitting.model
        size_run = _parse_size_run(model.size_run_model)
        base = (model.base_size_label or '').strip()

        specs = (
            GradedSpec.objects
            .filter(grading_version_id=gv.pk, is_active=True)
            .select_related('pom')
            .order_by('pom_id', 'size_label')
        )

        return GradingSnapshot(
            grading_version_id=gv.pk,
            approved=bool(gv.aprovada),
            base_size_label=base,
            size_run=tuple(size_run),
            deltas=tuple(
                GradedPOMDelta(
                    pom_id=s.pom_id,
                    pom_code=s.pom.pom_code,
                    size_label=s.size_label,
                    value_cm=s.graded_value_cm,
                    delta_cm=s.increment_applied_cm,
                    rule_applied=s.grading_type_applied,
                )
                for s in specs
            ),
        )


def _parse_size_run(brut: str) -> list[str]:
    """`Model.size_run_model` → llista ordenada de talles.

    Mateix criteri que el motor de grading (`pom/services.py:52`): el separador és `·`, i
    el `;` s'hi tolera. Una còpia de la regla, no una versió pròpia: si divergissin, el
    patró es graduaria amb unes talles i la fitxa amb unes altres.
    """
    return [s.strip() for s in (brut or '').replace(';', '·').split('·') if s.strip()]


# ═════════════════════════════════════════════════════════════════════════════
# Anotacions de S6 → contractes de l'engine (POMSpec / SewSpec)
# ═════════════════════════════════════════════════════════════════════════════

def point_refs(pattern_file) -> dict[int, PointRef]:
    """`PatternPoint.id` → `PointRef`. L'engine no sap què és un id de BD; això l'hi tradueix."""
    refs: dict[int, PointRef] = {}
    for piece in pattern_file.pieces.all():
        for p in piece.points.all():
            refs[p.id] = PointRef(
                peca=piece.nom_block,
                vora=(None if p.mena == PatternPoint.MENA_NOTCH else p.boundary_index),
                ordre=p.ordre,
            )
    return refs


def pom_specs(pattern_file) -> tuple[tuple[POMSpec, ...], list[str]]:
    """Els `PatternPOM` d'un fitxer → `POMSpec` de l'engine. → (specs, problemes).

    Els POMs amb una recepta que no es pot traduir (mode `landmark`, que la UI encara no
    ofereix, o un punt que ja no hi és) NO es descarten en silenci: surten a la llista de
    problemes perquè qui exporti sàpiga que aquell POM no entrarà a la niada.
    """
    refs = point_refs(pattern_file)
    specs: list[POMSpec] = []
    problemes: list[str] = []

    for piece in pattern_file.pieces.all():
        for pom in piece.poms.all():
            codi = pom.pom_master.pom_code
            definicio = pom.definicio_mesura or {}
            mode = definicio.get('mode', 'points')

            if mode != 'points':
                problemes.append(
                    f'El POM {codi} fa servir el mode de mesura «{mode}», que la projecció '
                    f'v1 encara no sap graduar (només «points»). No entrarà a la niada.'
                )
                continue

            ref_a = refs.get(definicio.get('a'))
            ref_b = refs.get(definicio.get('b'))
            if ref_a is None or ref_b is None:
                problemes.append(
                    f'El POM {codi} apunta a un punt que ja no és a la geometria: la seva '
                    f'recepta ha quedat òrfena. No entrarà a la niada.'
                )
                continue

            specs.append(POMSpec(
                pom_code=codi,
                nom=pom.pom_master.name_en,
                peca=piece.nom_block,
                ref_a=ref_a,
                ref_b=ref_b,
                metode=pom.metode,
                pom_id=pom.pom_master_id,
            ))

    return tuple(specs), problemes


def sew_specs(pattern_file) -> tuple[SewSpec, ...]:
    """Les `SewRelation` del MODEL del fitxer → `SewSpec` de l'engine.

    Les costures pengen del Model (cosir és muntatge: hi intervenen dues peces i cap no
    n'és propietària), així que es busquen pel model i es filtren als segments de les peces
    d'AQUEST fitxer: una costura declarada sobre una versió anterior del patró pot tenir
    trams que aquí ja no existeixen.
    """
    from .models import SewRelation

    if pattern_file.model_id is None:
        return ()

    peces = {p.id: p.nom_block for p in pattern_file.pieces.all()}
    fora: list[SewSpec] = []

    for rel in (SewRelation.objects
                .filter(model_id=pattern_file.model_id)
                .prefetch_related('segments_a__piece', 'segments_b__piece')):
        costat_a = _seg_refs(rel.segments_a.all(), peces)
        costat_b = _seg_refs(rel.segments_b.all(), peces)
        if not costat_a or not costat_b:
            continue  # la costura no és d'aquesta versió del patró
        fora.append(SewSpec(
            sew_id=rel.id,
            tipus=rel.tipus,
            diferencial_cm=rel.diferencial_cm,
            costat_a=costat_a,
            costat_b=costat_b,
        ))

    return tuple(fora)


def _seg_refs(segments, peces: dict[int, str]) -> tuple[SegRef, ...]:
    return tuple(
        SegRef(
            peca=peces[s.piece_id],
            vora=s.vora,
            t_inici=s.t_inici,
            t_fi=s.t_fi,
        )
        for s in segments
        if s.piece_id in peces
    )
