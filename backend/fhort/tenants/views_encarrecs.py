"""Els ENCÀRRECS d'un Studio — la safata de la federació vista des de qui treballa (P8).

    GET  /api/v1/encarrecs/              → què m'han assignat, per Brand, amb estat
    POST /api/v1/encarrecs/traspassar/   → me'ls porto a casa (crea els Model EXTERN)

MIRALL EXACTE DE `views_recursos.py`, i a posta. El Brand hi veu RECURSOS (amb qui pot
comptar); el Studio hi veu ENCÀRRECS (què li han encomanat). Cap dels dos veu l'altra
meitat: el Brand no veu ni temps ni tècnics, i el Studio no veu el catàleg del Brand — només
els models que li han assignat explícitament.

EL TRASPÀS ÉS DEL STUDIO PERQUÈ LA FEINA ÉS SEVA. El Brand assigna i governa el token; qui
decideix quan es porta l'encàrrec a casa (i paga el cost d'instanciar-lo al seu schema) és
qui hi ha de treballar. Per això aquest endpoint viu al costat del Studio i el `studio_codi`
mai viatja al payload: és sempre `request.tenant`, com el `brand_codi` a P7.

L'ESTAT NO ÉS UN CAMP. `estat_local` (PENDENT/TRASPASSAT) es calcula comparant el
`codi_intern` del Brand amb el que ja tinc al meu schema. No hi ha cap booleà "traspassat"
enlloc que es pugui desincronitzar amb la realitat: si algú esborra el model local, l'estat
torna a PENDENT tot sol i el traspàs el tornarà a crear.
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.accounts.capabilities import CONFIGURE, HasCapability

from .federation_service import (FederacioError, envia_a_la_marca, safata_del_studio,
                                 traspassa)
from .models import Client

#: Els errors de domini que són un CONFLICTE amb l'estat del món (409) i no una petició mal
#: formada (400). El pont tancat és el cas de manual: la petició és perfecta, el món diu que no.
#: `besso_missing` hi entra pel mateix motiu: demanar d'enviar una peça que la marca encara no
#: té no és una petició mal escrita, és un món que encara no hi és.
CODIS_409 = frozenset({'link_not_active', 'customer_missing', 'besso_missing'})


class EsEstudi(IsAuthenticated):
    """El tenant del request ha de ser un Estudi. Una Marca no rep encàrrecs: els emet.

    403 i no 404, pel mateix motiu que `EsMarca` a P7: el recurs existeix conceptualment i
    l'usuari està autenticat; el que no té és la naturalesa per operar-hi.
    """

    message = 'Només un Estudi pot treballar encàrrecs.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        tenant = getattr(request, 'tenant', None)
        return tenant is not None and tenant.tipologia == Client.TIPOLOGIA_ESTUDI


class EncarrecViewSet(viewsets.ViewSet):
    """La safata i el seu únic acte. ViewSet pla: no hi ha cap model 'Encàrrec' a la BD —
    un encàrrec és una VISTA sobre dos schemes (l'assignació al Brand + la meva còpia local),
    i inventar-ne una taula seria fabricar un tercer estat que caldria mantenir sincronitzat."""

    def get_permissions(self):
        if self.action == 'list':
            return [EsEstudi()]
        perm = HasCapability()
        self.required_capability = CONFIGURE
        return [EsEstudi(), perm]

    @property
    def _studio_codi(self):
        return self.request.tenant.codi_tenant

    def list(self, request):
        """La safata agrupada per Brand. Només vincles ACTIUS (vegeu el servei)."""
        try:
            grups = safata_del_studio(self._studio_codi)
        except FederacioError as e:
            return Response({'error': str(e), 'code': e.codi}, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            'studio_codi': self._studio_codi,
            'grups': grups,
            'n_pendents': sum(g['n_pendents'] for g in grups),
        })

    @action(detail=False, methods=['post'])
    def traspassar(self, request):
        """POST /api/v1/encarrecs/traspassar/ — {brand_codi, codis: [...] | 'tots_pendents'}.

        Crida el MATEIX servei que `instantiate_external_models --commit`. La paritat no és
        una casualitat que calgui vigilar: literalment no hi ha una segona implementació.

        `codis='tots_pendents'` no és un mode a part: es tradueix a `codis=None`, que al servei
        vol dir "tots els assignats". Els que ja hi són es SALTEN igualment (idempotència per
        `codi_intern`), així que "tots els assignats" i "tots els pendents" acaben al mateix
        lloc — el segon nom és el que l'usuari entén des de la safata.
        """
        brand_codi = (request.data.get('brand_codi') or '').strip().upper()
        if not brand_codi:
            return Response({'error': 'Cal el codi del Brand.', 'code': 'brand_codi_required'},
                            status=status.HTTP_400_BAD_REQUEST)

        codis = request.data.get('codis')
        if codis == 'tots_pendents' or codis is None:
            codis = None
        elif isinstance(codis, list):
            codis = [str(c).strip() for c in codis if str(c).strip()]
            if not codis:
                return Response({'error': 'La llista de codis és buida.', 'code': 'codis_empty'},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': "codis ha de ser una llista o 'tots_pendents'.",
                             'code': 'codis_invalid'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            report = traspassa(brand_codi=brand_codi, studio_codi=self._studio_codi,
                               commit=True, codis=codis)
        except FederacioError as e:
            codi_http = (status.HTTP_409_CONFLICT if e.codi in CODIS_409
                         else status.HTTP_400_BAD_REQUEST)
            return Response({'error': str(e), 'code': e.codi}, status=codi_http)

        # L'informe sencer, en JSON. Els mateixos números que el terminal, sense adjectius.
        return Response({
            'brand_codi': report['brand_codi'],
            'creats': report['creats'],
            'saltats': report['saltats'],
            'unmatched': report['unmatched'],
            'n_creats': len(report['creats']),
            'n_saltats': len(report['saltats']),
            'n_llegits': report['n_llegits'],
        })

    @action(detail=False, methods=['post'], url_path='enviar')
    def enviar(self, request):
        """POST /api/v1/encarrecs/enviar/ — {model_id} — la feina feta, cap a la marca.

        EL RETORN DE `traspassar/`, I VIU AL MATEIX LLOC PER LA MATEIXA RAÓ. El traspàs és de
        l'estudi perquè la feina és seva; l'enviament també, i pel mateix motiu: qui decideix
        que la peça està prou madura per ensenyar-la és qui l'ha fet. El `brand_codi` no viatja
        al payload —es dedueix del model, que ja diu de quina casa ve— exactament com el
        `studio_codi` no viatja mai en aquest fitxer.

        UN MODEL PER CRIDA, A POSTA. El bulk de la UI itera aquesta crida i n'agrega el resum,
        com fa `runBulk` amb la resta d'accions per-model. Un endpoint en bloc hauria de decidir
        què fer quan la peça 7 de 20 no té bessó, i la resposta honesta —«digues-ho per aquella
        i continua»— és precisament el que la iteració ja fa sense inventar-se cap semàntica.
        """
        model_id = request.data.get('model_id')
        if not model_id:
            return Response({'error': "Cal l'id del model.", 'code': 'model_id_required'},
                            status=status.HTTP_400_BAD_REQUEST)

        from fhort.models_app.models import Model
        model = Model.objects.filter(pk=model_id).first()
        if model is None:
            return Response({'error': 'Model no trobat.', 'code': 'model_missing'},
                            status=status.HTTP_404_NOT_FOUND)

        try:
            informe = envia_a_la_marca(model)
        except FederacioError as e:
            codi_http = (status.HTTP_409_CONFLICT if e.codi in CODIS_409
                         else status.HTTP_400_BAD_REQUEST)
            return Response({'error': str(e), 'code': e.codi}, status=codi_http)
        return Response(informe)
