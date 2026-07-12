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
from .models import PatternPiece, PatternPoint


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
        """Escriu la geometria d'un document sota un `PatternFile` ja existent.

        Reescriu les peces senceres: un `PatternFile` és immutable de facto (una versió
        nova és una fila nova), així que no hi ha cap fusió delicada a fer.
        """
        if pattern_file is None:
            raise ValueError('Cal un PatternFile on penjar la geometria.')

        pattern_file.pieces.all().delete()
        pattern_file.grade_table = grade_table_to_json(doc.grade_table)
        pattern_file.save(update_fields=['grade_table'])

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
        return row

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
