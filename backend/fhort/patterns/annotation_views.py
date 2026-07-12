"""API d'anotació: ancorar POMs i declarar costures.

Separat de `views.py` a posta: allò és el pipeline del fitxer (pujar, llegir, servir) i
això és el treball humà que s'hi diposita a sobre. Són dues vides diferents del mateix
patró.

**El valor de la mesura no s'accepta del client, mai.** Arriba la RECEPTA (quins punts) i
el servidor la resol sobre la geometria. Si el valor vingués del navegador, un POM deixaria
de ser una mesura del patró per ser una xifra que algú hi ha escrit a sobre.
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.pom.models import POMMaster

from .adapters import DjangoGeometryStore
from .engine.measure import MeasureError, resoldre
from .engine.segments import longitud_vora
from .engine.sew import validar
from .models import PatternPiece, PatternPOM, PatternPoint, PatternSegment, SewRelation


class PatternPOMSerializer(serializers.ModelSerializer):
    pom_code = serializers.SerializerMethodField()
    pom_nom = serializers.SerializerMethodField()
    peca = serializers.CharField(source='pattern_piece.nom_block', read_only=True)

    class Meta:
        model = PatternPOM
        fields = [
            'id', 'pattern_piece', 'peca', 'pom_master', 'pom_code', 'pom_nom',
            'definicio_mesura', 'metode', 'valor_mesurat_cm', 'data_creacio',
        ]
        # El valor NO és escrivible: el calcula el servidor des de la geometria.
        read_only_fields = ['valor_mesurat_cm', 'data_creacio', 'peca', 'pom_code', 'pom_nom']

    def get_pom_code(self, obj):
        return obj.pom_master.codi_client

    def get_pom_nom(self, obj):
        return obj.pom_master.nom_client


class SewRelationSerializer(serializers.ModelSerializer):
    estat = serializers.SerializerMethodField()

    class Meta:
        model = SewRelation
        fields = [
            'id', 'model', 'segments_a', 'segments_b', 'tipus', 'diferencial_cm',
            'notes', 'estat', 'data_creacio',
        ]
        read_only_fields = ['estat', 'data_creacio']

    def get_estat(self, obj):
        return comprovar_costura(obj)


def _mesurar(pom: PatternPOM) -> float | None:
    """Resol la recepta d'un POM sobre la geometria de la seva peça.

    Torna None si la recepta no es pot resoldre; el POM es desa igualment, amb el valor
    buit i el motiu a la resposta. Un ancoratge que no es pot mesurar encara és informació
    (algú l'ha intentat), i esborrar-lo en silenci amagaria el problema.
    """
    piece_row = pom.pattern_piece
    doc = DjangoGeometryStore().load_from(piece_row.pattern_file)
    piece = doc.piece(piece_row.nom_block)
    if piece is None:
        return None

    # La recepta desa ids de PatternPoint; l'engine no sap què és un id de BD.
    punts = {p.id: p for p in piece_row.points.all()}
    resultat = resoldre(piece, pom.definicio_mesura, punts, metode=pom.metode)
    return round(resultat.valor_cm, 2)


def comprovar_costura(rel: SewRelation) -> dict:
    """L'estat d'una costura, calculat ara mateix sobre la geometria."""
    llarg_a = _longitud_segments(rel.segments_a.all())
    llarg_b = _longitud_segments(rel.segments_b.all())
    check = validar(llarg_a, llarg_b, tipus=rel.tipus, diferencial_cm=rel.diferencial_cm)
    return {
        'casa': check.casa,
        'longitud_a_cm': round(check.longitud_a_cm, 2),
        'longitud_b_cm': round(check.longitud_b_cm, 2),
        'diferencia_cm': round(check.diferencia_cm, 2),
        'desviament_cm': round(check.desviament_cm, 2),
        'missatge': check.missatge,
    }


def _longitud_segments(segments) -> float:
    """Longitud total (mm) d'un costat de la costura.

    Un costat pot ser la suma de diversos trams: una màniga es cus contra una sisa que és
    davanter + esquena.
    """
    total = 0.0
    store = DjangoGeometryStore()
    cache: dict[int, object] = {}
    for seg in segments:
        piece_row = seg.piece
        if piece_row.pattern_file_id not in cache:
            cache[piece_row.pattern_file_id] = store.load_from(piece_row.pattern_file)
        doc = cache[piece_row.pattern_file_id]
        piece = doc.piece(piece_row.nom_block)
        if piece is None or seg.vora >= len(piece.boundaries):
            continue
        boundary = piece.boundaries[seg.vora]
        # El tram és una fracció paramètrica de la vora: la seva longitud és la fracció
        # de la longitud de la vora. És exactament per això que els trams es guarden en t
        # i no en índexs de vèrtex.
        total += longitud_vora(boundary) * max(0.0, seg.t_fi - seg.t_inici)
    return total


class PatternPOMViewSet(viewsets.ModelViewSet):
    """POMs ancorats a la geometria."""

    queryset = PatternPOM.objects.select_related(
        'pom_master', 'pattern_piece', 'pattern_piece__pattern_file').all()
    serializer_class = PatternPOMSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['pattern_piece', 'pattern_piece__pattern_file', 'pom_master']

    def perform_create(self, serializer):
        pom = serializer.save(creat_per=getattr(self.request.user, 'profile', None))
        self._recalcular(pom)

    def perform_update(self, serializer):
        pom = serializer.save()
        self._recalcular(pom)

    def _recalcular(self, pom: PatternPOM):
        try:
            pom.valor_mesurat_cm = _mesurar(pom)
        except MeasureError as e:
            pom.valor_mesurat_cm = None
            pom._error_mesura = str(e)
        pom.save(update_fields=['valor_mesurat_cm'])

    def create(self, request, *args, **kwargs):
        resposta = super().create(request, *args, **kwargs)
        pom = PatternPOM.objects.get(pk=resposta.data['id'])
        if pom.valor_mesurat_cm is None:
            resposta.data['avis'] = (
                'El POM s\'ha ancorat però la mesura no s\'ha pogut resoldre sobre la '
                'geometria.'
            )
        return resposta


class SewRelationViewSet(viewsets.ModelViewSet):
    """Costures declarades sobre el muntatge d'un model."""

    queryset = SewRelation.objects.prefetch_related(
        'segments_a__piece__pattern_file', 'segments_b__piece__pattern_file').all()
    serializer_class = SewRelationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['model', 'tipus']

    def perform_create(self, serializer):
        serializer.save(creat_per=getattr(self.request.user, 'profile', None))
