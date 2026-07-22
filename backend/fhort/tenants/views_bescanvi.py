"""Bescanvi del codi per una sessió, AL HOST DEL TENANT (F2).

    POST /api/auth/bescanvi/  {code}
        → 200 {access, refresh}      exactament el contracte de /api/token/
        → 401 genèric                per qualsevol altre motiu

Muntat NOMÉS a `fhort/urls.py`: aquest endpoint viu al host del tenant a posta. És el que fa
que la sessió neixi SAME-ORIGIN, que és tot el propòsit del disseny — el `localStorage` on
anirà el token és el d'aquest origen (DIAGNOSI_LOGIN_UNIC §B3.3), i el JWT que s'emet porta
el claim `tenant_schema` d'AQUEST schema (F0) perquè s'emet aquí dins.

LA LLIÇÓ DE F0, APLICADA AL CODI: un codi emès per a `los` presentat a `fhort` es rebutja.
Sense aquesta comprovació, el codi seria intercanviable entre schemas exactament com ho era
el JWT abans de F0 — la mateixa família de forat, un pis més amunt.

401 ÚNIC I MUT. Caducat, ja usat, inexistent, d'un altre schema, o d'un usuari que entretant
s'ha desactivat: tot té la mateixa cara. Distingir-los diria a un atacant amb un codi robat
QUÈ ha fallat, i «aquest codi era d'un altre tenant» ja és una pista d'existència d'schemas.

Resposta idèntica a la de `/api/token/` a posta: el frontend ha de poder tractar aquest camí
amb el MATEIX codi que el login de sempre (desar access+refresh i seguir), sense una segona
forma de sessió que mantenir.

Sense throttle, i és deliberat: el codi són 256 bits d'entropia, d'un sol ús i amb 60 s de
vida — no hi ha res a endevinar per força bruta. El fre va on es proven CONTRASENYES
(`/api/auth/central/`). Posar-lo aquí només afegiria una manera de deixar fora la gent que
aterra legítimament des d'una mateixa IP compartida, i just al moment d'entrar.
"""
import logging

from django.contrib.auth import get_user_model
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from fhort.auth_jwt import TenantTokenObtainPairSerializer

from .auth_central_service import consumeix_codi
from .models import CodiAuth

logger = logging.getLogger(__name__)

#: Mateix text que el 401 de la porta central i que el d'un JWT caducat. Cap pista.
CODI_NO_VALID = "Codi no vàlid o caducat."


class AuthBescanviView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []

    def post(self, request):
        codi = request.data.get('code') or ''
        fila = consumeix_codi(codi, CodiAuth.MENA_BESCANVI)   # consum ATÒMIC (un sol ús)

        # El codi ha de ser per a AQUEST schema. `connection.schema_name` el fixa el Host via
        # TenantMainMiddleware, o sigui que la comparació és «el destí que va decidir la porta
        # central» contra «el tenant al qual s'està trucant realment».
        if fila is None or fila.tenant_schema != connection.schema_name:
            return self._mut()

        User = get_user_model()
        user = User.objects.filter(pk=fila.user_id, is_active=True).first()
        if user is None:
            # Desactivat entre l'emissió i el bescanvi. El codi ja ha quedat cremat pel
            # consum atòmic: un compte tancat no reobre una sessió ni al segon intent.
            return self._mut()

        refresh = TenantTokenObtainPairSerializer.get_token(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)

    def _mut(self):
        return Response({'detail': CODI_NO_VALID}, status=status.HTTP_401_UNAUTHORIZED)
