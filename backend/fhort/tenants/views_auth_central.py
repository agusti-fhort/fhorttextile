"""Porta d'entrada ÚNICA: autenticació central cross-schema (F1).

Contracte:

    POST /api/auth/central/       {email, password}
        → 401 genèric                       si les credencials no valen enlloc
        → 200 {mena:'codi',      workspace, code}          si valen a UN sol workspace
        → 200 {mena:'seleccio',  workspaces, seleccio}     si valen a MÉS D'UN

    POST /api/auth/central/tria/  {seleccio, schema}
        → 200 {mena:'codi', workspace, code}
        → 401 genèric

Dos endpoints i no un de sol amb dues formes: són dos actes distints (provar credencials /
triar destí) amb dos permisos distints d'entrada, i barrejar-los faria que un mateix throttle
comptés coses diferents.

LA CONTRASENYA NOMÉS VIATJA UN COP. Amb multi-workspace, la tria NO re-envia les credencials:
la primera crida deixa un tiquet de selecció efímer al servidor amb els schemes ja validats, i
la segona només diu quin d'aquells. Un client que re-enviés la contrasenya per triar la
tindria retinguda en memòria tota l'estona que la persona dubta.

CAP CODI ES REGALA. La resposta multi-workspace NO porta cap codi de bescanvi: si en portés
un per workspace, un sol login deixaria N sessions obertes de les quals la persona només en
volia una.

Muntat a `urls_public.py` I a `fhort/urls.py`: la porta ha de respondre igual des del host
neutre de PROD (`login.*` → public) i des d'un host de tenant, que és l'única manera de
validar-la visualment a staging (llei S19, no hi ha subdomini `staginglogin.*`). El lookup ja
és cross-schema per construcció, així que el host des del qual s'entra no canvia el resultat.
"""
import logging

from rest_framework import status, throttling
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_central_service import (
    autentica_cross_schema,
    consumeix_codi,
    descriu_workspace,
    emet_codi,
    nom_del_tenant,
)
from .models import CodiAuth

logger = logging.getLogger(__name__)

#: L'ÚNIC missatge de fracàs. Mateix text i mateix 401 per a «no existeix» i per a
#: «contrasenya incorrecta»: qualsevol diferència convertiria la porta en un oracle
#: d'existència de comptes. Mateix criteri que la resposta uniforme del discovery.
CREDENCIALS_NO_VALIDES = "Credencials no vàlides."


class AuthCentralRateThrottle(throttling.SimpleRateThrottle):
    """Rate-limit propi (per IP), del mateix ordre que el del discovery.

    Aquesta és la superfície on es proven contrasenyes: sense fre, la porta única seria
    també la porta única del credential stuffing. Rate fix, sense dependre de
    DEFAULT_THROTTLE_RATES (que el projecte no defineix).

    Limitació coneguda i heretada (DIAGNOSI_LOGIN_UNIC §B2.3 / R4): sense `CACHES` a settings
    el comptador és LocMemCache, o sigui per procés de gunicorn. El fre existeix però reté
    menys del que diu. És deute de la casa, comú amb el discovery, i no d'aquesta peça.
    """
    scope = 'auth_central'

    def get_rate(self):
        return '20/hour'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


def _resposta_codi(workspace, request):
    """La resposta d'èxit: un workspace descrit pel servidor + el codi per entrar-hi."""
    codi = emet_codi(
        CodiAuth.MENA_BESCANVI,
        tenant_schema=workspace['schema'],
        user_id=workspace['user_id'],
    )
    return Response({
        'mena': 'codi',
        'workspace': descriu_workspace(workspace['schema'], workspace['nom'], request.get_host()),
        'code': codi,
    }, status=status.HTTP_200_OK)


def _fracas():
    return Response({'detail': CREDENCIALS_NO_VALIDES}, status=status.HTTP_401_UNAUTHORIZED)


class AuthCentralView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthCentralRateThrottle]
    authentication_classes = []   # porta d'entrada: no hi ha sessió encara (patró del discovery)

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        password = request.data.get('password') or ''
        if not email or not password:
            # Camp absent = error de client. No revela res de cap compte concret.
            return Response({'detail': 'Cal indicar correu i contrasenya.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            valids = autentica_cross_schema(email, password)
        except Exception:   # noqa: BLE001 — cap error intern pot parlar més que la resposta genèrica
            logger.exception('auth central: fallada interna (empassada per uniformitat)')
            return _fracas()

        if not valids:
            return _fracas()

        if len(valids) == 1:
            return _resposta_codi(valids[0], request)

        seleccio = emet_codi(
            CodiAuth.MENA_SELECCIO,
            candidats=[{'schema': w['schema'], 'user_id': w['user_id']} for w in valids],
        )
        return Response({
            'mena': 'seleccio',
            'seleccio': seleccio,
            'workspaces': [descriu_workspace(w['schema'], w['nom'], request.get_host())
                           for w in valids],
        }, status=status.HTTP_200_OK)


class AuthCentralTriaView(APIView):
    """Bescanvia un tiquet de selecció + un schema pel codi de bescanvi d'aquell workspace."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthCentralRateThrottle]
    authentication_classes = []

    def post(self, request):
        tiquet = request.data.get('seleccio') or ''
        schema = (request.data.get('schema') or '').strip()
        if not tiquet or not schema:
            return Response({'detail': 'Cal indicar la selecció i l\'espai de treball.'},
                            status=status.HTTP_400_BAD_REQUEST)

        fila = consumeix_codi(tiquet, CodiAuth.MENA_SELECCIO)
        if fila is None:
            return _fracas()

        # El schema demanat ha de ser un dels que van validar les credencials. Sense això,
        # un tiquet legítim seria una clau per entrar a qualsevol tenant del sistema.
        candidat = next((c for c in (fila.candidats or []) if c.get('schema') == schema), None)
        if candidat is None:
            return _fracas()

        return _resposta_codi({
            'schema': schema,
            'nom': nom_del_tenant(schema),
            'user_id': candidat.get('user_id'),
        }, request)
