"""API d'anotació: ancorar POMs i declarar costures.

Separat de `views.py` a posta: allò és el pipeline del fitxer (pujar, llegir, servir) i
això és el treball humà que s'hi diposita a sobre. Són dues vides diferents del mateix
patró.

**El valor de la mesura no s'accepta del client, mai.** Arriba la RECEPTA (quins punts) i
el servidor la resol sobre la geometria. Si el valor vingués del navegador, un POM deixaria
de ser una mesura del patró per ser una xifra que algú hi ha escrit a sobre.
"""
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.models_app.models import Model
from fhort.pom.models import POMMaster

from .adapters import DjangoGeometryStore
from .engine.measure import MeasureError, resoldre
from .engine.dart_detection import clau_pinca
from .preferences import registra
from .engine.seam_matching import clau_parella
from .engine.segments import (
    SegmentError, longitud_tram, longitud_vora, tram_entre_punts,
)
from .engine.sew import (
    CostatPinca, TramCosit, descomptar_pinces, validar, validar_cobertura,
)
from .dart_proposals import candidats_del_patro
from .models import (
    DartProposalRejection, PatternFile, PatternPiece, PatternPOM, PatternPoint, PatternSegment,
    SewProposalRejection, SewRelation,
)
from .seam_proposals import propostes_del_model


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
    #: És una pinça de vora? Ho decideix la geometria (v. `es_pinca_de_vora`), i el client ho
    #: necessita per pintar-la amb el seu glif i llistar-la com el que és — no com una costura
    #: qualsevol que casualment es diu 'pinca'.
    es_pinca = serializers.SerializerMethodField()

    class Meta:
        model = SewRelation
        fields = [
            'id', 'model', 'segments_a', 'segments_b', 'tipus', 'diferencial_cm',
            'nom', 'notes', 'estat', 'es_pinca', 'data_creacio',
        ]
        read_only_fields = ['estat', 'es_pinca', 'data_creacio']

    def get_estat(self, obj):
        return comprovar_costura(obj)

    def get_es_pinca(self, obj):
        return es_pinca_de_vora(obj)


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


def es_pinca_de_vora(rel: SewRelation) -> bool:
    """Aquesta costura és una PINÇA sobre una sola vora?

    És la pregunta que decideix si una relació descompta tela d'una altra, i la resposta surt
    de la geometria, no d'un flag: una pinça de vora és una `pinca` els DOS costats de la qual
    viuen a la mateixa vora de la mateixa peça. Això és el que la fa una pinça de debò —dos
    trossos de la mateixa vora que es cusen l'un contra l'altre— i és el que la distingeix
    d'una `pinca` declarada entre dues peces, que és una instrucció de muntatge i no es
    descompta de res.

    Per això no calia cap model nou (ni cap flag que algú hagués de recordar de marcar): la
    condició és una propietat de com està feta, i es constata.
    """
    if rel.tipus != SewRelation.TIPUS_PINCA:
        return False
    segments = list(rel.segments_a.all()) + list(rel.segments_b.all())
    if len(segments) < 2:
        return False
    vores = {(s.piece_id, s.vora) for s in segments}
    return len(vores) == 1


def _mapa_pinces(model_id: int, excloent: int | None = None) -> dict:
    """(peça, vora) → els costats de pinça que hi viuen, amb la seva longitud real.

    `excloent` és la costura que s'està validant: una pinça no es descompta a ella mateixa.
    Els seus dos costats SÓN la costura, i restar-los-hi deixaria una pinça de longitud zero
    que casaria sempre — un validador que sempre diu que sí.
    """
    boundaries = _BoundaryCache()
    per_vora: dict[tuple[int, int], list[CostatPinca]] = {}
    relacions = (SewRelation.objects
                 .filter(model_id=model_id, tipus=SewRelation.TIPUS_PINCA)
                 .prefetch_related('segments_a__piece', 'segments_b__piece'))
    for rel in relacions:
        if rel.id == excloent or not es_pinca_de_vora(rel):
            continue
        nom = rel.nom or f'pinça #{rel.id}'
        for seg in list(rel.segments_a.all()) + list(rel.segments_b.all()):
            boundary = boundaries.get(seg.piece, seg.vora)
            if boundary is None:
                continue
            per_vora.setdefault((seg.piece_id, seg.vora), []).append(CostatPinca(
                sew_id=rel.id, segment_id=seg.id, nom=nom,
                t_inici=seg.t_inici, t_fi=seg.t_fi,
                longitud_cm=longitud_tram(boundary, seg.t_inici, seg.t_fi) / 10.0,
            ))
    return per_vora


def _costat_net(segments, boundaries: _BoundaryCache, pinces: dict):
    """Un costat de costura: el contorn (mm) i les pinces que se'n mengen un tros.

    El brut i els descomptes viatgen JUNTS perquè el net sol no és auditable: qui llegeixi
    «29.8» ha de poder veure d'on surt («32.1 − 2.3 (Pinça 1)»), o el motor li demana un acte
    de fe.
    """
    brut_mm = 0.0
    trams_per_vora: dict[tuple[int, int], list[TramCosit]] = {}
    for seg in segments:
        boundary = boundaries.get(seg.piece, seg.vora)
        if boundary is None:
            continue
        brut_mm += longitud_tram(boundary, seg.t_inici, seg.t_fi)
        trams_per_vora.setdefault((seg.piece_id, seg.vora), []).append(TramCosit(
            sew_id=0, segment_id=seg.id, t_inici=seg.t_inici, t_fi=seg.t_fi,
        ))

    descomptes = []
    for clau, trams in trams_per_vora.items():
        descomptes.extend(descomptar_pinces(trams, pinces.get(clau, [])))
    return brut_mm, descomptes


def comprovar_costura(rel: SewRelation) -> dict:
    """L'estat d'una costura, calculat ara mateix sobre la geometria.

    Tres preguntes, no una:
      · **què hi entra?** — el contorn dels seus trams, MENYS les pinces que s'hi tanquen a
        dins (W4b). Una vora amb pinça aporta a la costura menys tela de la que fa: els dos
        costats de la pinça es cusen entre ells i no arriben mai a la costura.
      · **casa?** — els dos costats (nets) fan el que el TIPUS promet (`validar`).
      · **hi cap?** — el que aquesta costura reclama, sumat al que reclamen les ALTRES
        costures del mateix model sobre les mateixes vores, no es trepitja ni passa de la
        vora (`validar_cobertura`). Una costura pot casar perfectament i ser impossible.
    """
    boundaries = _BoundaryCache()
    pinces = _mapa_pinces(rel.model_id, excloent=rel.id)
    brut_a, desc_a = _costat_net(rel.segments_a.all(), boundaries, pinces)
    brut_b, desc_b = _costat_net(rel.segments_b.all(), boundaries, pinces)

    check = validar(
        brut_a, brut_b, tipus=rel.tipus, diferencial_cm=rel.diferencial_cm,
        descomptes_a=desc_a, descomptes_b=desc_b,
    )
    return {
        'casa': check.casa,
        # La longitud és la NETA: és la que es cus, i per tant la que es compara.
        'longitud_a_cm': round(check.longitud_a_cm, 2),
        'longitud_b_cm': round(check.longitud_b_cm, 2),
        # El BRUT no s'amaga: la vora continua fent el que fa, i el descompte s'ha de veure.
        'brut_a_cm': round(check.brut_a_cm, 2),
        'brut_b_cm': round(check.brut_b_cm, 2),
        'descomptes_a': [
            {'sew_id': d.sew_id, 'nom': d.nom, 'cm': round(d.cm, 2)} for d in check.descomptes_a
        ],
        'descomptes_b': [
            {'sew_id': d.sew_id, 'nom': d.nom, 'cm': round(d.cm, 2)} for d in check.descomptes_b
        ],
        'diferencia_cm': round(check.diferencia_cm, 2),
        'desviament_cm': round(check.desviament_cm, 2),
        'missatge': check.missatge,
        'cobertura': _cobertura_de(rel, boundaries),
    }


def punts_de_la_mateixa_vora(data, camps: list[str]) -> list[PatternPoint]:
    """Els punts d'un gest del taller, validats abans de tocar cap geometria.

    Un gest en pot demanar dos (definir un tram) o tres (marcar una pinça), però la llei és
    la mateixa i per això viu en un sol lloc: existeixen, són de la MATEIXA peça, són vèrtexs
    d'una vora (no piquets), són de la MATEIXA vora, i no es repeteixen. Escrita dues vegades,
    acabaria dient dues coses.
    """
    ids = [data.get(camp) for camp in camps]
    if not all(ids):
        raise serializers.ValidationError(
            f'Aquest gest es defineix amb {len(camps)} punts: {", ".join(camps)}.')

    punts = []
    for camp, pk in zip(camps, ids):
        try:
            punts.append(PatternPoint.objects.select_related('piece').get(pk=pk))
        except PatternPoint.DoesNotExist:
            raise serializers.ValidationError({camp: 'Aquest punt no existeix.'})

    if len({p.piece_id for p in punts}) > 1:
        raise serializers.ValidationError(
            'Els punts han de ser de la MATEIXA peça: un tram és un tros d\'una vora, i una '
            'vora no travessa dues peces.')
    if any(p.boundary_index is None for p in punts):
        raise serializers.ValidationError(
            'Un tram es declara sobre vèrtexs d\'una vora. Un piquet no pertany a cap vora i '
            'no en pot ser l\'extrem.')
    vores = {p.boundary_index for p in punts}
    if len(vores) > 1:
        raise serializers.ValidationError(
            f'Els punts són de vores diferents ({", ".join(str(v) for v in sorted(vores))}): '
            f'un tram no salta d\'una vora a una altra.')
    if len({p.id for p in punts}) < len(punts):
        raise serializers.ValidationError(
            'Hi ha un punt repetit: dos extrems que són el mateix punt no delimiten res.')
    return punts


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
        # Un costat de pinça no és un tram que competeixi per la vora: és la pinça. La
        # cobertura ho ha de saber, o denunciarà com a solapament (i com a excés) la tela que
        # la costura ja NO cus, perquè `validar` l'hi ha descomptada.
        pinca = es_pinca_de_vora(altra)
        for seg in list(altra.segments_a.all()) + list(altra.segments_b.all()):
            clau = (seg.piece_id, seg.vora)
            if clau not in vores:
                continue
            peces[seg.piece_id] = seg.piece
            per_vora.setdefault(clau, []).append(TramCosit(
                sew_id=altra.id, segment_id=seg.id,
                t_inici=seg.t_inici, t_fi=seg.t_fi,
                nom=seg.nom or f'tram {seg.id}',
                es_pinca=pinca,
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


def costures_que_retenen(seg: PatternSegment) -> list[int]:
    """Les costures que cusen aquest tram. Si n'hi ha cap, el tram no s'esborra.

    PROTECT a mà: `segments_a`/`segments_b` són M2M i un `on_delete` no hi arriba. Sense
    aquesta porta, esborrar un tram buidaria un costat d'una costura en silenci i la costura
    passaria a mesurar de menys sense que ningú n'hagués tocat res.

    Viu aquí, i no dins de `destroy`, perquè l'esborrat en BLOC ha de fer exactament la
    mateixa pregunta: una segona còpia de la llei del PROTECT és una llei que algun dia
    divergirà, i el dia que divergeixi ho farà en silenci.
    """
    return sorted(
        {r.id for r in seg.sew_relations_a.all()} | {r.id for r in seg.sew_relations_b.all()}
    )


def esborra_costura(rel: SewRelation) -> None:
    """Esborrar una costura. Si és una PINÇA, se'n va amb els seus dos costats.

    Els costats d'una pinça no existeixen sense ella: SÓN la pinça. Deixar-los enrere ompliria
    el patró de trams declarats que ningú no cus i que ningú no sabria d'on venen.

    Un costat que, contra tot pronòstic, el cusi alguna altra costura, es queda: el PROTECT
    dels trams val aquí igual que a `PatternSegmentViewSet`, i esborrar-lo deixaria coixa una
    costura que ningú ha tocat.
    """
    if not es_pinca_de_vora(rel):
        rel.delete()
        return

    costats = list(rel.segments_a.all()) + list(rel.segments_b.all())
    with transaction.atomic():
        rel.delete()
        for seg in costats:
            if not costures_que_retenen(seg):
                seg.delete()


class BulkDeleteMixin:
    """Esborrar en bloc: `{ids: [...]}` → què ha caigut i què s'ha quedat, i per què.

    **Un bloc no és una transacció sola.** Si ho fos, un sol tram retingut per una costura
    faria caure l'esborrat dels altres divuit, i qui ha demanat divuit no ha demanat «tot o
    res»: ha demanat divuit. Per això l'atomicitat és PER ÍTEM —una pinça i els seus costats
    cauen junts o no cau cap— i el bloc n'aixeca un informe.

    I per això no retorna mai 500 per una dependència: que un tram el cusi una costura no és
    una avaria, és la resposta. Un 500 obligaria la pantalla a endevinar què ha passat i què
    ha quedat viu; l'informe li ho diu id per id.
    """

    def _esborra_un(self, obj) -> dict | None:
        """Esborra `obj`. Retorna None si ha caigut, o el motiu pel qual s'ha quedat."""
        raise NotImplementedError

    @action(detail=False, methods=['post'], url_path='bulk-delete')
    def bulk_delete(self, request):
        ids = request.data.get('ids')
        if not isinstance(ids, list) or not ids:
            raise serializers.ValidationError(
                {'ids': 'Cal una llista d\'ids, i no pot ser buida.'})
        try:
            ids = [int(i) for i in ids]
        except (TypeError, ValueError):
            raise serializers.ValidationError({'ids': 'Els ids han de ser enters.'})

        # El MATEIX camí que `get_object()`: `filter_queryset()` sobre el queryset del ViewSet
        # i `check_object_permissions()` per ítem. No n'hi ha prou amb `get_queryset()`: avui
        # dona el mateix resultat, però el dia que algú posi una permission_class amb
        # `has_object_permission` de debò, `destroy` quedaria protegit i el bloc no —i ho faria
        # en silenci, que és exactament el que aquest endpoint existeix per evitar. El que no
        # passa el filtre és «no trobat»: un id d'un altre patró no s'esborra i no es confirma.
        objectes = {o.id: o for o in self.filter_queryset(self.get_queryset())
                    .filter(id__in=set(ids))}

        esborrats, retinguts = [], []
        for i in dict.fromkeys(ids):          # sense repetits, i en l'ordre demanat
            obj = objectes.get(i)
            if obj is None:
                retinguts.append({'id': i, 'motiu': 'no_trobat'})
                continue
            try:
                self.check_object_permissions(request, obj)
            except (exceptions.NotFound, exceptions.PermissionDenied):
                retinguts.append({'id': i, 'motiu': 'no_trobat'})
                continue
            motiu = self._esborra_un(obj)
            if motiu is None:
                esborrats.append(i)
            else:
                retinguts.append({'id': i, **motiu})

        return Response({'esborrats': esborrats, 'retinguts': retinguts})


class PatternPOMViewSet(BulkDeleteMixin, viewsets.ModelViewSet):
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

    def _esborra_un(self, pom: PatternPOM) -> dict | None:
        """Un POM ancorat no reté res: ningú no el referencia. Sempre cau."""
        pom.delete()
        return None


class SewRelationViewSet(BulkDeleteMixin, viewsets.ModelViewSet):
    """Costures declarades sobre el muntatge d'un model."""

    queryset = SewRelation.objects.prefetch_related(
        'segments_a__piece__pattern_file', 'segments_b__piece__pattern_file').all()
    serializer_class = SewRelationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['model', 'tipus']

    def perform_create(self, serializer):
        serializer.save(creat_per=getattr(self.request.user, 'profile', None))

    def destroy(self, request, *args, **kwargs):
        """Esborrar una costura, i —si és pinça— els seus costats. La llei és `esborra_costura`."""
        esborra_costura(self.get_object())
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _esborra_un(self, rel: SewRelation) -> dict | None:
        """Una costura no la reté ningú: cau, i s'emporta els costats que només eren seus."""
        esborra_costura(rel)
        return None

    @action(detail=False, methods=['post'], url_path='pinca')
    def pinca(self, request):
        """Marcar una pinça: tres punts, i el taller en fa dos trams i una costura.

        `{model, point_a, point_vertex, point_b, nom, nom_a, nom_b}`.

        **Cap model nou.** Una pinça ÉS el que ja hi havia: dos trams declarats (els seus dos
        costats) i una `SewRelation` de tipus pinça que els cus l'un contra l'altre. Inventar
        una taula `Pinca` hauria dit que és una cosa diferent d'una costura, i llavors hi
        hauria dos llocs on mirar què es cus amb què.

        **Un sol gest, una sola transacció.** Tres crides des del client (dos trams i una
        costura) podien fallar a la tercera i deixar dos trams orfes al patró, amb nom de
        pinça i sense pinça. Un gest que l'usuari viu com un de sol no pot deixar mitja cosa
        feta.

        Els noms arriben del client perquè és qui té els tres idiomes (i18n-gate); el servidor
        hi posa un recanvi per si vinguessin buits, però la frase és de qui la sap dir.
        """
        pa, vertex, pb = punts_de_la_mateixa_vora(
            request.data, ['point_a', 'point_vertex', 'point_b'])

        # El model es comprova ABANS d'obrir la transacció. Si es deixés a la FK de la BD, un
        # model inexistent petaria amb un IntegrityError (un 500) a mig gest: la transacció
        # faria el seu paper i no quedarien trams orfes, però l'usuari rebria una avaria en
        # comptes d'un «aquest model no existeix». Una petició que no es pot resoldre és un
        # 400, no una avaria.
        model_id = request.data.get('model')
        if not model_id:
            raise serializers.ValidationError({'model': 'Una costura penja d\'un model.'})
        if not Model.objects.filter(pk=model_id).exists():
            raise serializers.ValidationError({'model': 'Aquest model no existeix.'})

        boundary = _BoundaryCache().get(pa.piece, pa.boundary_index)
        if boundary is None:
            raise serializers.ValidationError(
                {'point_a': 'No s\'ha pogut carregar la vora d\'aquests punts.'})

        # Els dos costats: de l'inici al vèrtex, i del vèrtex al final. Sempre l'arc CURT —
        # una pinça és una V local a la vora, no un tram que dona la volta a la peça.
        try:
            tram_a = tram_entre_punts(boundary, pa.boundary_index, pa.ordre, vertex.ordre)
            tram_b = tram_entre_punts(boundary, pa.boundary_index, vertex.ordre, pb.ordre)
        except SegmentError as e:
            raise serializers.ValidationError({'tram': str(e)})

        nom = (request.data.get('nom') or '').strip() or 'Pinça'
        nom_a = (request.data.get('nom_a') or '').strip() or f'{nom} · A'
        nom_b = (request.data.get('nom_b') or '').strip() or f'{nom} · B'

        with transaction.atomic():
            costats = [
                PatternSegment.objects.create(
                    piece=pa.piece, vora=tram.vora, t_inici=tram.t_inici, t_fi=tram.t_fi,
                    tipus_vora=tram.tipus_vora.value,
                    origen=PatternSegment.ORIGEN_DECLARAT, nom=nom_costat,
                )
                for tram, nom_costat in ((tram_a, nom_a), (tram_b, nom_b))
            ]
            rel = SewRelation.objects.create(
                model_id=model_id, tipus=SewRelation.TIPUS_PINCA,
                # Els dos costats d'una pinça han de fer el mateix: si no, no es poden cosir
                # l'un contra l'altre. El diferencial és zero, i el que en digui el motor és el
                # que la geometria digui — no es maquilla declarant com a promès el que passa.
                diferencial_cm=0.0, nom=nom,
                creat_per=getattr(request.user, 'profile', None),
            )
            rel.segments_a.set([costats[0]])
            rel.segments_b.set([costats[1]])

        return Response(self.get_serializer(rel).data, status=status.HTTP_201_CREATED)


    # ── ASSISTIT (A2): proposar, mai escriure ───────────────────────────────

    def _patro(self, request) -> PatternFile:
        """El patró sobre el qual es proposa: el que demani `?file=`, o el vigent del model.

        Les propostes es calculen sobre UNA versió del patró, i s'ha de dir quina: els trams
        derivats es refan a cada versió, i una proposta que barregés els d'una amb els d'una
        altra no seria una costura, seria un disbarat amb dues geometries.
        """
        model_id = request.query_params.get('model') or request.data.get('model')
        if not model_id:
            raise serializers.ValidationError({'model': 'De quin model es proposen costures?'})

        file_id = request.query_params.get('file') or request.data.get('file')
        qs = PatternFile.objects.filter(model_id=model_id)
        fp = qs.filter(pk=file_id).first() if file_id else qs.filter(is_current=True).first()
        if fp is None:
            raise serializers.ValidationError(
                {'file': 'Aquest model no té cap patró vigent sobre el qual proposar res.'})
        return fp

    @action(detail=False, methods=['get'], url_path='propostes')
    def propostes(self, request):
        """Les costures que el motor proposa. **NOMÉS LECTURA.**

        No desa res, no marca res, no reserva res: es recalculen senceres a cada crida. És el que
        les fa fiables quan la geometria canvia sota els peus —confirmar-ne una, esborrar una
        costura, marcar una pinça— i és el que fa que no calgui cap taula de propostes vives que
        algú hauria de mantenir sincronitzada amb la realitat.
        """
        return Response(propostes_del_model(self._patro(request)))

    @action(detail=False, methods=['post'], url_path='confirmar-proposta')
    def confirmar_proposta(self, request):
        """Confirmar-ne una: `{model, segment_a, segment_b, tipus?, diferencial_cm?, nom?…}`.

        **Confirmar és el gest manual, fet en un clic.** No hi ha cap camí curt: en surt
        exactament el mateix que si el patronista hagués declarat els dos trams a mà i els hagués
        cosit —dos `PatternSegment` DECLARATS i una `SewRelation` que els uneix—, perquè una
        costura confirmada no pot ser una entitat de segona categoria que després ningú sàpiga
        editar. Un cop confirmada, ja no es distingeix d'una feta a mà, i això és la prova que el
        motor no s'ha inventat cap drecera.

        **Els trams es PROMOUEN, no es reciclen.** El tram derivat (`auto`) és la hipòtesi de
        lectura del CAD i es queda on és; el que entra a la costura és un tram DECLARAT amb el
        mateix recorregut. Cosir directament l'`auto` trencaria la llei de W4 (una costura és una
        afirmació, i no es fa una afirmació amb una hipòtesi) i, pitjor, deixaria la costura
        penjada d'una fila que la propera importació pot refer.

        **Una transacció.** Tres crides des del client (dos trams i la costura) podien fallar a la
        tercera i deixar dos trams orfes amb nom de costura i sense costura — el mateix motiu pel
        qual `pinca` és una sola crida.
        """
        fp = self._patro(request)
        seg_a, seg_b = self._trams_de_la_proposta(request.data, fp)

        tipus = request.data.get('tipus') or SewRelation.TIPUS_CASAT
        if tipus not in dict(SewRelation.TIPUS_CHOICES):
            raise serializers.ValidationError({'tipus': f"Tipus de costura desconegut: '{tipus}'."})

        # Els noms arriben del client, que és qui té els tres idiomes (i18n-gate). El servidor hi
        # posa un recanvi perquè un tram sense nom és un tram que després ningú sabrà què és.
        nom_a = (request.data.get('nom_a') or '').strip() or f'{seg_a.piece.nom_block} · tram'
        nom_b = (request.data.get('nom_b') or '').strip() or f'{seg_b.piece.nom_block} · tram'

        with transaction.atomic():
            declarats = [
                PatternSegment.objects.create(
                    piece=seg.piece, vora=seg.vora, t_inici=seg.t_inici, t_fi=seg.t_fi,
                    tipus_vora=seg.tipus_vora,
                    origen=PatternSegment.ORIGEN_DECLARAT, nom=nom,
                )
                for seg, nom in ((seg_a, nom_a), (seg_b, nom_b))
            ]
            # El taller aprèn del «sí»: confirmar una proposta és el judici humà sobre la
            # lectura del motor, i és l'únic moment en què n'hi ha un. Només ACUMULA senyal
            # —no canvia res del que passa aquí— i va dins la mateixa transacció perquè un
            # aprenentatge d'una costura que després no existeix seria un record fals.
            for declarat in declarats:
                registra(declarat, getattr(request.user, 'profile', None))
            rel = SewRelation.objects.create(
                model_id=fp.model_id, tipus=tipus,
                diferencial_cm=float(request.data.get('diferencial_cm') or 0),
                # El bateig és de qui el sap dir. Buit vol dir «genera'l dels dos trams», i és el
                # que la UI fa servir: el nom d'una costura es REFERENCIA, no es congela.
                nom=(request.data.get('nom') or '').strip(),
                creat_per=getattr(request.user, 'profile', None),
            )
            rel.segments_a.set([declarats[0]])
            rel.segments_b.set([declarats[1]])

        return Response(self.get_serializer(rel).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='rebutjar-proposta')
    def rebutjar_proposta(self, request):
        """Dir que no: `{model, segment_a, segment_b, motiu?}`. I que no torni a sortir.

        **El rebuig és persistent perquè si no ho fos no seria un rebuig**, seria un «amaga-ho
        fins que recarregui». Una eina que torna a proposar el que ja li han dit que no ensenya a
        no mirar-la, i llavors tant li fa què proposi.

        El que es rebutja és la PARELLA, no els seus trams: dir que no a «màniga ⛓ màniga» ha de
        deixar la màniga lliure perquè el motor la pugui proposar contra la sisa, que és la
        parella bona. Per això aquí no es marca res sobre els segments.
        """
        fp = self._patro(request)
        seg_a, seg_b = self._trams_de_la_proposta(request.data, fp)
        a, b = clau_parella(seg_a.id, seg_b.id)

        rebuig, creat = SewProposalRejection.objects.get_or_create(
            segment_a_id=a, segment_b_id=b,
            defaults={
                'model_id': fp.model_id,
                'motiu': (request.data.get('motiu') or '').strip(),
                'rebutjat_per': getattr(request.user, 'profile', None),
            },
        )
        return Response(
            {'id': rebuig.id, 'clau': [a, b], 'ja_hi_era': not creat},
            status=status.HTTP_201_CREATED if creat else status.HTTP_200_OK,
        )

    # ── ASSISTIT (A1): les pinces que el motor veu ──────────────────────────

    @action(detail=False, methods=['get'], url_path='pinces-proposades')
    def pinces_proposades(self, request):
        """Les pinces que el motor detecta a la vora. **NOMÉS LECTURA.**

        Mateix patró que les propostes de costura (A2): no es desa res, es recalculen a cada
        crida, i el que les identifica és la clau canònica dels seus tres punts —no cap id, perquè
        una proposta no és cap fila.

        **No hi ha endpoint de confirmació.** Confirmar-ne una és cridar `pinca/` amb els tres
        punts que el candidat ja porta: el MATEIX camí de codi que el gest manual de W4b. Un segon
        camí per a la mateixa cosa hauria estat un lloc més on la llei de la pinça podria divergir.
        """
        return Response(candidats_del_patro(self._patro(request)))

    @action(detail=False, methods=['post'], url_path='rebutjar-pinca')
    def rebutjar_pinca(self, request):
        """Dir que no a una pinça: `{model, point_a, point_vertex, point_b, motiu?}`.

        El rebuig és persistent, per la mateixa raó que a A2: si no ho fos, no seria un rebuig.
        """
        fp = self._patro(request)
        punts = punts_de_la_mateixa_vora(
            request.data, ['point_a', 'point_vertex', 'point_b'])
        if punts[0].piece.pattern_file_id != fp.id:
            raise serializers.ValidationError(
                {'point_a': 'Aquests punts no són d\'aquest patró.'})

        a, v, b = clau_pinca(punts[0].id, punts[1].id, punts[2].id)
        rebuig, creat = DartProposalRejection.objects.get_or_create(
            punt_a_id=a, punt_vertex_id=v, punt_b_id=b,
            defaults={
                'model_id': fp.model_id,
                'motiu': (request.data.get('motiu') or '').strip(),
                'rebutjat_per': getattr(request.user, 'profile', None),
            },
        )
        return Response(
            {'id': rebuig.id, 'clau': [a, v, b], 'ja_hi_era': not creat},
            status=status.HTTP_201_CREATED if creat else status.HTTP_200_OK,
        )

    def _trams_de_la_proposta(self, data, fp: PatternFile):
        """Els dos trams d'una proposta, validats abans de tocar res.

        Han d'existir, han de ser d'aquest patró i han de ser DERIVATS: una proposta és sempre
        sobre la hipòtesi del CAD. Si arribés un tram declarat, algú estaria fent passar per
        proposta una cosa que ja s'havia decidit.

        DERIVAT vol dir `auto` **o** `natural`: totes dues són lectures del motor, i cap de les
        dues és una decisió de ningú. Això es comprovava amb `== auto` quan «derivat» i «auto»
        eren sinònims; des que A2 proposa sobre naturals (QA-TALLER-B · T3b) ja no ho són, i la
        condició que sempre havia manat és la que la frase de sobre diu: **no declarat**.
        """
        ids = [data.get('segment_a'), data.get('segment_b')]
        if not all(ids):
            raise serializers.ValidationError(
                'Una proposta són DOS trams: segment_a i segment_b.')
        if ids[0] == ids[1]:
            raise serializers.ValidationError(
                'Els dos costats de la proposta són el mateix tram: això no cus res.')

        trams = []
        for camp, pk in zip(['segment_a', 'segment_b'], ids):
            seg = (PatternSegment.objects
                   .select_related('piece')
                   .filter(pk=pk, piece__pattern_file=fp).first())
            if seg is None:
                raise serializers.ValidationError(
                    {camp: 'Aquest tram no existeix en aquest patró.'})
            if seg.origen == PatternSegment.ORIGEN_DECLARAT:
                raise serializers.ValidationError(
                    {camp: 'Això no és una proposta: aquest tram ja és un tram declarat.'})
            trams.append(seg)
        return trams[0], trams[1]


class PatternSegmentSerializer(serializers.ModelSerializer):
    """Un tram, derivat o declarat.

    La geometria no s'escriu per `t`: es RECOL·LOCA amb el mateix gest amb què es va declarar
    (dos punts, i el servidor resol la vora). Per això `t_inici`/`t_fi` continuen sent de
    només lectura —una `t` teclejada no seria una referència a la vora, seria una xifra que
    algú hi ha escrit a sobre— i qui les mou és el PATCH amb `point_a`/`point_b`.
    """

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


class PatternSegmentViewSet(BulkDeleteMixin, viewsets.ModelViewSet):
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
        # Declarar un tram a mà també és un judici sobre la lectura del motor: confirma un
        # natural, l'allarga o l'escurça. S'acumula igual que quan es confirma una proposta
        # —el gest és un altre, el judici és el mateix— i no canvia res del que passa aquí.
        registra(seg, getattr(request.user, 'profile', None))
        dades = self.get_serializer(seg).data
        return Response(dades, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Reanomenar i/o RECOL·LOCAR (W4b/T5b).

        Recol·locar és moure els extrems del tram, **sobre la mateixa fila**. No és esborrar
        i tornar a crear: la fila la referencien les costures (M2M), i esborrar-la per
        refer-la les deixaria coixes o obligaria a recompondre-les a mà. El PROTECT que hi ha
        a `destroy` és per a ESBORRAR, no per a corregir: un tram mal posat s'ha de poder
        arreglar sense desmuntar la costura que el fa servir.

        Que la costura estigui en ús no bloqueja res: es revalida sola (l'`estat` es calcula
        a cada lectura sobre la geometria viva) i la cobertura es recalcula amb ella.
        """
        seg = self.get_object()
        recolloca = 'point_a' in request.data or 'point_b' in request.data
        if recolloca:
            pa, pb = punts_de_la_mateixa_vora(request.data, ['point_a', 'point_b'])
            if pa.piece_id != seg.piece_id:
                # Un tram que canviés de peça deixaria de ser el mateix tram: les costures que
                # el cusen es trobarien cosint una altra peça sense que ningú els ho hagués dit.
                raise serializers.ValidationError(
                    {'point_a': 'Un tram no pot canviar de peça: recol·locar-lo és moure\'n '
                                'els extrems, no traslladar-lo a una altra peça.'})
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
                raise serializers.ValidationError({'tram': str(e)})

            seg.vora = tram.vora
            seg.t_inici = tram.t_inici
            seg.t_fi = tram.t_fi
            seg.tipus_vora = tram.tipus_vora.value
            seg.save(update_fields=['vora', 't_inici', 't_fi', 'tipus_vora'])

        return super().update(request, *args, **kwargs)

    def _punts(self, data) -> tuple[PatternPoint, PatternPoint]:
        """Els dos extrems, validats abans de tocar cap geometria."""
        pa, pb = punts_de_la_mateixa_vora(data, ['point_a', 'point_b'])
        return pa, pb

    def destroy(self, request, *args, **kwargs):
        """Esborrar un tram, si ningú no el cus. La porta és `costures_que_retenen`."""
        seg = self.get_object()
        sews = costures_que_retenen(seg)
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

    def _esborra_un(self, seg: PatternSegment) -> dict | None:
        """Un tram EN ÚS es queda, i l'informe diu quines costures el retenen.

        És la mateixa porta que el `destroy` (`costures_que_retenen`), dita en informe en
        comptes de 409: en bloc, que un tram es quedi no és l'excepció que atura la feina, és
        una de les respostes possibles.
        """
        sews = costures_que_retenen(seg)
        if sews:
            return {'motiu': 'en_us', 'sew_relations': sews}
        seg.delete()
        return None
