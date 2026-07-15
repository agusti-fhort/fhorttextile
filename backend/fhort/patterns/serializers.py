"""Serializers del motor de patrons.

Tot **read-only**, i a posta: la creació la governa `services.save_pattern_file`, que és
l'únic lloc que sap mantenir la invariant de cadena. Un serializer amb camps escrivibles
seria una segona porta que se la saltaria — exactament l'error que `ModelFitxerViewSet`
va haver de desfer (S0-B1.2: el ViewSet genèric saltava la invariant).
"""
from rest_framework import serializers

from .engine.geometry import BoundaryData, LayerRole, NotchData, PieceData, PointData, PointKind
from .engine.natural_segments import index_de_t, segmentar_vora_natural
from .models import PatternFile, PatternPiece, PatternSegment


def _vora_base_meta(boundaries):
    """La vora d'on es deriven els trams: la de COSIT si n'hi ha, si no la de TALL.

    És la mateixa tria que fa `segmentar_peca` al motor, i a propòsit: si els naturals
    sortissin d'una vora i els AUTO d'una altra, no serien la mateixa lectura de la
    mateixa costura.
    """
    for rol in (LayerRole.SEW.value, LayerRole.CUT.value):
        for b in boundaries:
            if b['role'] == rol:
                return b, b['index']
    return None


def _boundary_del_dict(b):
    """Un `BoundaryData` del motor a partir del dict que el serializer ja ha muntat."""
    return BoundaryData(
        role=LayerRole(b['role']),
        layer=b['layer'],
        points=tuple(
            PointData(x=p['x'], y=p['y'], kind=PointKind(p['tipus']))
            for p in b['points']
        ),
        closed=bool(b['closed']),
    )


def _signed_download_url(obj, request, *, salt, accio='download-signed'):
    """URL absoluta i signada. Mateix patró que `models_app.serializers` (D13).

    `<a href>` i `<img src>` no poden portar capçalera Authorization; el permís viatja al
    token, que només rep qui ja s'ha autenticat per llegir aquesta fila.
    """
    from django.core import signing

    if request is None or not obj.fitxer_dxf:
        return None
    token = signing.dumps(obj.id, salt=salt)
    return request.build_absolute_uri(
        f'/api/v1/patterns/pattern-files/{obj.id}/{accio}/?token={token}'
    )


class PatternPieceSerializer(serializers.ModelSerializer):
    """La peça amb els seus RECOMPTES, no amb els seus milers de punts.

    Una peça pot portar centenars de punts i un fitxer, milers. Escopir-los tots a cada
    llistat seria carregar mig megabyte per ensenyar una llista de quatre noms. El detall
    complet es demana explícitament (`?detall=1`) o es mira al render SVG, que és el que
    de debò vol veure qui obre la fitxa.
    """
    punts_per_capa = serializers.SerializerMethodField()
    bounding_box_mm = serializers.SerializerMethodField()
    total_punts = serializers.SerializerMethodField()

    class Meta:
        model = PatternPiece
        fields = [
            'id', 'nom_block', 'rol', 'contorns', 'grain', 'metadata',
            'doblec_original', 'has_sew', 'has_fold', 'unknown_layers',
            'punts_per_capa', 'bounding_box_mm', 'total_punts',
        ]
        read_only_fields = fields

    def get_punts_per_capa(self, obj):
        recompte: dict[str, int] = {}
        for p in obj.points.all():
            clau = p.tipus if p.mena == 'vertex' else 'notch'
            recompte[clau] = recompte.get(clau, 0) + 1
        return recompte

    def get_total_punts(self, obj):
        return sum(1 for p in obj.points.all() if p.mena == 'vertex')

    def get_bounding_box_mm(self, obj):
        xs = [p.x for p in obj.points.all()]
        ys = [p.y for p in obj.points.all()]
        if not xs:
            return None
        return {
            'min_x': min(xs), 'min_y': min(ys),
            'max_x': max(xs), 'max_y': max(ys),
            'ample': max(xs) - min(xs), 'alt': max(ys) - min(ys),
        }


class PatternGeometrySerializer(serializers.ModelSerializer):
    """La geometria SENCERA, coordenades incloses: el que el visor necessita per dibuixar.

    És una vista a part del detall a posta. El detall serveix per a llistes i fitxes i hi
    van els RECOMPTES; això és el document geomètric i hi van els milers de punts. Barrejar
    els dos faria que cada llistat de patrons arrossegués mig megabyte per ensenyar quatre
    noms.

    **Sense paginació.** Un patró és un document, no una llista: mig contorn no és res.
    L'AMELIA en té 266 punts — servir-los sencers costa menys que la ceremònia de paginar-los.
    """
    pieces = serializers.SerializerMethodField()

    class Meta:
        model = PatternFile
        fields = ['id', 'versio', 'escala_mm', 'font_cad', 'pieces']
        read_only_fields = fields

    def get_pieces(self, obj):
        return [self._piece(p) for p in obj.pieces.all()]

    def _naturals(self, piece, boundaries):
        """Els trams naturals de la vora base, calculats sobre el que ja tenim a la mà.

        Es munten objectes del motor amb les MATEIXES files que el serializer ja ha llegit,
        en comptes de tornar a obrir el DXF: la lectura de la geometria és cara i aquí no
        cal, perquè els naturals només són aritmètica sobre punts i piquets.
        """
        vora_meta = _vora_base_meta(boundaries)
        if vora_meta is None:
            return []
        b_dict, index_vora = vora_meta
        b = _boundary_del_dict(b_dict)
        if len(b.points) < 2:
            return []

        peca = PieceData(
            nom_block=piece.nom_block,
            boundaries=(b,),
            notches=tuple(
                NotchData(x=p.x, y=p.y)
                for p in piece.points.all() if p.mena == 'notch'
            ),
        )

        # Els extrems de PINÇA DE VORA tallen encara que l'angle hi arribi suau: el que hi
        # ha a banda i banda són dues costures diferents. Només la PINÇA parteix — un tram
        # qualsevol que estigui cosit a una altra peça no és cap frontera de la seva vora.
        # (Import diferit, com fa `dart_proposals`: la condició és de domini i es constata
        # de la geometria, no d'un flag; no se'n pot tenir una segona versió aquí.)
        from .annotation_views import es_pinca_de_vora

        talls = []
        for s in piece.segments.all():
            if s.vora != index_vora or s.origen != PatternSegment.ORIGEN_DECLARAT:
                continue
            rels = list(s.sew_relations_a.all()) + list(s.sew_relations_b.all())
            if not any(es_pinca_de_vora(r) for r in rels):
                continue
            for t in (s.t_inici, s.t_fi):
                i = index_de_t(b, t)
                if i is not None:
                    talls.append(i)

        return [
            {
                'vora': s.vora,
                't_inici': s.t_inici, 't_fi': s.t_fi,
                'tipus_vora': s.tipus_vora.value,
                'index_inici': s.index_inici, 'index_fi': s.index_fi,
                'longitud_cm': round(s.longitud_mm / 10.0, 2),
                # De quins girs surt: la fusió ha de ser auditable des de la UI.
                'girs_fusionats': list(s.girs_fusionats),
                # Metadada, no frontera: A2 els llegeix per inferir frunzit.
                'piquets': [{'x': k.x, 'y': k.y} for k in s.piquets],
            }
            for s in segmentar_vora_natural(peca, b, index_vora, talls_extra=tuple(talls))
        ]

    def _piece(self, piece):
        # Els punts arriben ja ordenats pel Meta.ordering de PatternPoint
        # (piece, mena, boundary_index, ordre): l'ordre dins la vora és el del contorn, i
        # perdre'l voldria dir dibuixar un garbuix.
        per_vora: dict[int, list] = {}
        notches = []
        for p in piece.points.all():
            if p.mena == 'notch':
                notches.append({'x': p.x, 'y': p.y, 'grade_rule_num': p.grade_rule_num})
            else:
                per_vora.setdefault(p.boundary_index, []).append({
                    # L'id hi és perquè la recepta d'un POM referencia PUNTS: sense ell, la
                    # UI no podria dir "d'aquest punt a aquell" i el servidor no ho podria
                    # tornar a resoldre.
                    'id': p.id,
                    'x': p.x, 'y': p.y,
                    'tipus': p.tipus,
                    'grade_rule_num': p.grade_rule_num,
                })

        boundaries = [
            {
                'index': meta['index'],
                'role': meta['role'],
                'layer': meta['layer'],
                'closed': meta['closed'],
                'points': per_vora.get(meta['index'], []),
            }
            for meta in (piece.contorns or [])
        ]

        xs = [p.x for p in piece.points.all()]
        ys = [p.y for p in piece.points.all()]
        bbox = None
        if xs:
            bbox = {
                'min_x': min(xs), 'min_y': min(ys),
                'max_x': max(xs), 'max_y': max(ys),
                'ample': max(xs) - min(xs), 'alt': max(ys) - min(ys),
            }

        return {
            'id': piece.id,
            'nom_block': piece.nom_block,
            'rol': piece.rol,
            'metadata': piece.metadata,
            'boundaries': boundaries,
            'notches': notches,
            'grain': piece.grain,
            'has_sew': piece.has_sew,
            'has_fold': piece.has_fold,
            'unknown_layers': piece.unknown_layers,
            'bbox': bbox,
            # Els trams. `origen` distingeix la PROPOSTA del motor (gir→gir, 'auto') del que
            # algú ha DECLARAT ('declarat'), i el nom és com se'n diu al taller. Van aquí i
            # no en una crida a part perquè qui dibuixa el patró els ha de poder pintar amb
            # el que ja té: demanar-los per separat era fer dues peticions per a una sola
            # pregunta ("què hi ha en aquesta peça?").
            'segments': [
                {
                    'id': s.id, 'vora': s.vora,
                    't_inici': s.t_inici, 't_fi': s.t_fi,
                    'tipus_vora': s.tipus_vora,
                    'origen': s.origen, 'nom': s.nom,
                }
                for s in piece.segments.all()
            ],
            # Els trams NATURALS: la mateixa vora llegida com poques costures (v.
            # `engine/natural_segments`). Vista DERIVADA —no és a la BD, es calcula aquí— i
            # per això viatja al costat dels AUTO en comptes de substituir-los: el selector
            # de Cosir vol aquests, i el gest manual de precisió segueix volent els altres.
            'naturals': self._naturals(piece, boundaries),
            # Els POMs ja ancorats, per dibuixar-los sobre la geometria.
            'poms': [
                {
                    'id': p.id,
                    'pom_master': p.pom_master_id,
                    'pom_code': p.pom_master.codi_client,
                    'pom_nom': p.pom_master.nom_client,
                    'definicio_mesura': p.definicio_mesura,
                    'metode': p.metode,
                    'valor_mesurat_cm': p.valor_mesurat_cm,
                }
                for p in piece.poms.all()
            ],
        }


class PatternFileSerializer(serializers.ModelSerializer):
    pieces = PatternPieceSerializer(many=True, read_only=True)
    download_url = serializers.SerializerMethodField()
    download_rul_url = serializers.SerializerMethodField()
    render_url = serializers.SerializerMethodField()
    te_rul = serializers.BooleanField(read_only=True)

    class Meta:
        model = PatternFile
        fields = [
            'id', 'model', 'garment_type_item', 'source_asset',
            'versio', 'is_current', 'versio_anterior',
            'nom_fitxer', 'mida_bytes', 'checksum', 'mimetype',
            'nom_rul', 'mida_rul_bytes', 'te_rul',
            'font_cad', 'escala_mm', 'unitats_metode', 'unitats_confianca',
            'empremta', 'grade_table',
            'pujat_per', 'data_pujada',
            'pieces', 'download_url', 'download_rul_url', 'render_url',
        ]
        read_only_fields = fields

    def get_download_url(self, obj):
        from .views import PATTERN_DOWNLOAD_SALT
        return _signed_download_url(
            obj, self.context.get('request'), salt=PATTERN_DOWNLOAD_SALT)

    def get_download_rul_url(self, obj):
        from .views import PATTERN_RUL_DOWNLOAD_SALT
        if not obj.fitxer_rul:
            return None
        return _signed_download_url(
            obj, self.context.get('request'), salt=PATTERN_RUL_DOWNLOAD_SALT,
            accio='download-rul-signed')

    def get_render_url(self, obj):
        request = self.context.get('request')
        if request is None:
            return None
        # Amb barra final: és la ruta canònica del router. Sense, hi hauria un 301 pel
        # mig i el client hauria de seguir-lo per res.
        return request.build_absolute_uri(
            f'/api/v1/patterns/pattern-files/{obj.id}/render.svg/')


class PatternFileLlistaSerializer(PatternFileSerializer):
    """Per als llistats: sense les peces ni l'empremta sencera."""

    class Meta(PatternFileSerializer.Meta):
        fields = [
            f for f in PatternFileSerializer.Meta.fields
            if f not in ('pieces', 'empremta', 'grade_table')
        ]
        read_only_fields = fields
