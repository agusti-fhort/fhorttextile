"""Serializers del motor de patrons.

Tot **read-only**, i a posta: la creació la governa `services.save_pattern_file`, que és
l'únic lloc que sap mantenir la invariant de cadena. Un serializer amb camps escrivibles
seria una segona porta que se la saltaria — exactament l'error que `ModelFitxerViewSet`
va haver de desfer (S0-B1.2: el ViewSet genèric saltava la invariant).
"""
from rest_framework import serializers

from .models import PatternFile, PatternPiece


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
