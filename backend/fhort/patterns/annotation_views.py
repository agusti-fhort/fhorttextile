"""API d'anotació: ancorar POMs i declarar costures.

Separat de `views.py` a posta: allò és el pipeline del fitxer (pujar, llegir, servir) i
això és el treball humà que s'hi diposita a sobre. Són dues vides diferents del mateix
patró.

**El valor de la mesura no s'accepta del client, mai.** Arriba la RECEPTA (quins punts) i
el servidor la resol sobre la geometria. Si el valor vingués del navegador, un POM deixaria
de ser una mesura del patró per ser una xifra que algú hi ha escrit a sobre.
"""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.pom.models import POMMaster

from .adapters import DjangoGeometryStore
from .engine.measure import MeasureError, resoldre
from .engine.segments import (
    SegmentError, longitud_tram, longitud_vora, tram_entre_punts,
)
from .engine.sew import TramCosit, validar, validar_cobertura
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

    def validate_definicio_mesura(self, valor):
        """Una recepta que uneix un punt amb ell mateix no és una mesura: és un zero.

        Ho impedeix també la UI (el segon clic sobre el mateix punt el destria), però la
        llei és del domini i no de la pantalla: qualsevol client que ho intentés hauria de
        rebotar igual.
        """
        mode = valor.get('mode', 'points')
        if mode == 'points':
            if valor.get('a') is None or valor.get('b') is None:
                raise serializers.ValidationError(
                    'La recepta ha de dir quins dos punts uneix (a i b).')
            if valor['a'] == valor['b']:
                raise serializers.ValidationError(
                    'Els dos extrems de la mesura són el mateix punt: això mesuraria zero.')
        elif mode == 'landmark':
            if valor.get('landmark') is None or valor.get('b') is None:
                raise serializers.ValidationError(
                    'Una mesura per landmark necessita el punt base i el punt final.')
        else:
            raise serializers.ValidationError(f"Mode de mesura desconegut: '{mode}'.")
        return valor


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
    """L'estat d'una costura, calculat ara mateix sobre la geometria.

    Dues preguntes, no una:
      · **casa?** — els dos costats fan el que el TIPUS promet (`validar`).
      · **hi cap?** — el que aquesta costura reclama, sumat al que reclamen les ALTRES
        costures del mateix model sobre les mateixes vores, no es trepitja ni passa de la
        vora (`validar_cobertura`). Una costura pot casar perfectament i ser impossible.
    """
    boundaries = _BoundaryCache()
    llarg_a = _longitud_segments(rel.segments_a.all(), boundaries)
    llarg_b = _longitud_segments(rel.segments_b.all(), boundaries)
    check = validar(llarg_a, llarg_b, tipus=rel.tipus, diferencial_cm=rel.diferencial_cm)
    return {
        'casa': check.casa,
        'longitud_a_cm': round(check.longitud_a_cm, 2),
        'longitud_b_cm': round(check.longitud_b_cm, 2),
        'diferencia_cm': round(check.diferencia_cm, 2),
        'desviament_cm': round(check.desviament_cm, 2),
        'missatge': check.missatge,
        'cobertura': _cobertura_de(rel, boundaries),
    }


class _BoundaryCache:
    """Les vores d'un patró, carregades un sol cop.

    Resoldre una costura toca la mateixa geometria moltes vegades (els dos costats, i
    després la cobertura de cada vora). Rellegir el DXF a cada tram seria absurd.
    """

    def __init__(self):
        self._store = DjangoGeometryStore()
        self._docs: dict[int, object] = {}

    def get(self, piece_row: PatternPiece, vora: int):
        if piece_row.pattern_file_id not in self._docs:
            self._docs[piece_row.pattern_file_id] = self._store.load_from(
                piece_row.pattern_file)
        doc = self._docs[piece_row.pattern_file_id]
        piece = doc.piece(piece_row.nom_block)
        if piece is None or vora >= len(piece.boundaries):
            return None
        return piece.boundaries[vora]


def _longitud_segments(segments, boundaries: _BoundaryCache) -> float:
    """Longitud total (mm) d'un costat de la costura.

    Un costat pot ser la suma de diversos trams: una màniga es cus contra una sisa que és
    davanter + esquena.

    La longitud d'un tram surt de `longitud_tram`, que sap que un tram DECLARAT pot passar
    per l'origen de la vora (`t_fi` < `t_inici`). Abans es feia amb un
    `max(0, t_fi - t_inici)` a mà, que en aquest cas donava **zero**: el tram s'esfumava i
    el costat de la costura sortia més curt del que és, sense dir res. Amb els trams
    derivats no podia passar (van sempre endavant); amb els declarats, sí.
    """
    total = 0.0
    for seg in segments:
        boundary = boundaries.get(seg.piece, seg.vora)
        if boundary is None:
            continue
        total += longitud_tram(boundary, seg.t_inici, seg.t_fi)
    return total


def _cobertura_de(rel: SewRelation, boundaries: _BoundaryCache) -> list[dict]:
    """Avisos de cobertura de les vores que aquesta costura toca.

    Es mira la vora SENCERA, amb tot el que hi cus **qualsevol** costura del model: un
    solapament és, per definició, cosa de dues costures, i mirant-ne una de sola no es veu
    mai. Per això la consulta surt del model i no de `rel`.
    """
    vores = {
        (seg.piece_id, seg.vora)
        for seg in list(rel.segments_a.all()) + list(rel.segments_b.all())
    }
    if not vores:
        return []

    # Tot el que es cus, a tot el model, sobre les vores que ens interessen.
    germanes = (SewRelation.objects
                .filter(model_id=rel.model_id)
                .prefetch_related('segments_a__piece', 'segments_b__piece'))
    per_vora: dict[tuple[int, int], list[TramCosit]] = {}
    peces: dict[int, PatternPiece] = {}
    for altra in germanes:
        for seg in list(altra.segments_a.all()) + list(altra.segments_b.all()):
            clau = (seg.piece_id, seg.vora)
            if clau not in vores:
                continue
            peces[seg.piece_id] = seg.piece
            per_vora.setdefault(clau, []).append(TramCosit(
                sew_id=altra.id, segment_id=seg.id,
                t_inici=seg.t_inici, t_fi=seg.t_fi,
                nom=seg.nom or f'tram {seg.id}',
            ))

    avisos: list[dict] = []
    for (piece_id, vora), trams in sorted(per_vora.items()):
        boundary = boundaries.get(peces[piece_id], vora)
        if boundary is None:
            continue
        for avis in validar_cobertura(vora, longitud_vora(boundary), trams):
            avisos.append({
                'mena': avis.mena,
                'peca': peces[piece_id].nom_block,
                'peca_id': piece_id,
                'vora': avis.vora,
                'longitud_vora_cm': avis.longitud_vora_cm,
                'sews': list(avis.sews),
                'segments': list(avis.segments),
                'solapament_cm': avis.solapament_cm,
                'suma_cosida_cm': avis.suma_cosida_cm,
                'exces_cm': avis.exces_cm,
                'missatge': avis.missatge,
            })
    return avisos


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


class PatternSegmentSerializer(serializers.ModelSerializer):
    """Un tram, derivat o declarat. La geometria és de només lectura: un tram no es
    'mou' editant-li la t, es torna a declarar."""

    peca = serializers.CharField(source='piece.nom_block', read_only=True)
    longitud_cm = serializers.SerializerMethodField()
    en_us = serializers.SerializerMethodField()

    class Meta:
        model = PatternSegment
        fields = [
            'id', 'piece', 'peca', 'vora', 't_inici', 't_fi', 'tipus_vora',
            'origen', 'nom', 'longitud_cm', 'en_us',
        ]
        read_only_fields = [
            'piece', 'peca', 'vora', 't_inici', 't_fi', 'tipus_vora', 'origen',
            'longitud_cm', 'en_us',
        ]

    def get_longitud_cm(self, obj):
        boundary = self.context.setdefault('_vores', _BoundaryCache()).get(obj.piece, obj.vora)
        if boundary is None:
            return None
        return round(longitud_tram(boundary, obj.t_inici, obj.t_fi) / 10.0, 2)

    def get_en_us(self, obj):
        """Si una costura el fa servir. És el que impedeix esborrar-lo."""
        return obj.sew_relations_a.exists() or obj.sew_relations_b.exists()


class PatternSegmentViewSet(viewsets.ModelViewSet):
    """Trams d'una peça: els derivats (gir→gir) i els DECLARATS pel patronista.

    **Primer declarar, després cosir.** La segmentació automàtica és una proposta del CAD;
    la costura de veritat la delimita qui fa el patró, triant dos punts de la vora.
    """

    queryset = PatternSegment.objects.select_related('piece', 'piece__pattern_file').all()
    serializer_class = PatternSegmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['piece', 'piece__pattern_file', 'origen', 'vora']

    def create(self, request, *args, **kwargs):
        """Declarar un tram: {point_a, point_b, nom?, arc_llarg?}.

        No arriba cap `t`, ni cap longitud: arriben dos PUNTS i el servidor resol el tram
        sobre la geometria. Si el client pogués enviar les t directament, un tram deixaria
        de ser una referència a la vora per ser una xifra que algú hi ha escrit a sobre —el
        mateix principi que amb el valor d'un POM.
        """
        punts = self._punts(request.data)
        pa, pb = punts
        boundary = _BoundaryCache().get(pa.piece, pa.boundary_index)
        if boundary is None:
            raise serializers.ValidationError(
                {'point_a': 'No s\'ha pogut carregar la vora d\'aquests punts.'})

        try:
            tram = tram_entre_punts(
                boundary, pa.boundary_index, pa.ordre, pb.ordre,
                arc_llarg=bool(request.data.get('arc_llarg', False)),
            )
        except SegmentError as e:
            # 400 amb el motiu del motor, mai un 500: és una petició que no es pot resoldre,
            # no una avaria.
            raise serializers.ValidationError({'tram': str(e)})

        seg = PatternSegment.objects.create(
            piece=pa.piece, vora=tram.vora, t_inici=tram.t_inici, t_fi=tram.t_fi,
            tipus_vora=tram.tipus_vora.value,
            origen=PatternSegment.ORIGEN_DECLARAT,
            nom=(request.data.get('nom') or '').strip() or None,
        )
        dades = self.get_serializer(seg).data
        return Response(dades, status=status.HTTP_201_CREATED)

    def _punts(self, data) -> tuple[PatternPoint, PatternPoint]:
        """Els dos extrems, validats abans de tocar cap geometria."""
        ids = [data.get('point_a'), data.get('point_b')]
        if not all(ids):
            raise serializers.ValidationError(
                'Un tram declarat es defineix amb dos punts: point_a i point_b.')
        try:
            pa = PatternPoint.objects.select_related('piece').get(pk=ids[0])
            pb = PatternPoint.objects.select_related('piece').get(pk=ids[1])
        except PatternPoint.DoesNotExist:
            raise serializers.ValidationError('Algun dels dos punts no existeix.')

        if pa.piece_id != pb.piece_id:
            raise serializers.ValidationError(
                'Els dos punts han de ser de la MATEIXA peça: un tram és un tros d\'una vora, '
                'i una vora no travessa dues peces.')
        if pa.boundary_index is None or pb.boundary_index is None:
            raise serializers.ValidationError(
                'Un tram es declara sobre vèrtexs d\'una vora. Un piquet no pertany a cap '
                'vora i no en pot ser l\'extrem.')
        if pa.boundary_index != pb.boundary_index:
            raise serializers.ValidationError(
                f'Els dos punts són de vores diferents ({pa.boundary_index} i '
                f'{pb.boundary_index}): un tram no salta d\'una vora a una altra.')
        return pa, pb

    def destroy(self, request, *args, **kwargs):
        """Esborrar un tram, si ningú no el cus.

        PROTECT a mà: `segments_a`/`segments_b` són M2M i un `on_delete` no hi arriba. Sense
        aquesta porta, esborrar un tram buidaria un costat d'una costura en silenci i la
        costura passaria a mesurar de menys sense que ningú n'hagués tocat res.
        """
        seg = self.get_object()
        sews = sorted(
            {r.id for r in seg.sew_relations_a.all()} | {r.id for r in seg.sew_relations_b.all()}
        )
        if sews:
            return Response(
                {
                    'error': (
                        f'Aquest tram el fa servir {len(sews)} costura(es) '
                        f'({", ".join(str(s) for s in sews)}). Treu-lo primer de la costura: '
                        f'esborrar-lo ara la deixaria coixa sense dir-ho.'
                    ),
                    'sew_relations': sews,
                },
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)
