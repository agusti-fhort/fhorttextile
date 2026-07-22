"""JWT lligat a l'schema que l'ha emès (F0 — claim de tenant).

PER QUÈ EXISTEIX AQUEST MÒDUL
------------------------------
El JWT de SimpleJWT porta `user_id` i res més que digui QUI és l'emissor. Amb
django-tenants, `django.contrib.auth` viu alhora a SHARED_APPS (`settings.py:41`) i a
TENANT_APPS (`settings.py:64`): hi ha una taula `auth_user` per schema, amb PKs
INDEPENDENTS que sempre comencen a l'1. I l'schema no el decideix el token: el fixa
`TenantMainMiddleware` (2n middleware, `settings.py:87`) a partir del **Host**, abans
que DRF miri res.

`JWTAuthentication` acaba fent un `.get(pk=user_id)` pelat sobre aquell schema. Resultat
verificat empíricament a `docs/diagnosis/DIAGNOSI_LOGIN_UNIC_2026-07-22.md` §B3.1: un
token emès al tenant `fhort` per l'usuari id=1 **era acceptat al schema `public` com un
usuari DIFERENT — el superusuari**. La regla real era «col·lisió de PK = suplantació», i
empitjorava amb cada tenant nou.

La cura: el token diu de quin schema és, i l'autenticació ho comprova contra l'schema que
el Host ha fixat. Un token només val a casa seva.

INVALIDACIÓ NETA (decisió d'Agus)
---------------------------------
No hi ha finestra de gràcia ni doble camí de validació. Un token sense el claim
`tenant_schema` (tots els emesos abans d'aquest canvi) no coincideix amb cap schema i
queda rebutjat, exactament igual que un token amb el claim equivocat. Amb el deploy,
tothom torna a fer login un cop.
"""
from django.db import connection
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

#: Nom del claim. Constant perquè emissió, validació i tests no puguin divergir.
TENANT_CLAIM = 'tenant_schema'


class TenantClaimMixin:
    """Segella el token amb l'schema actiu en el moment d'autenticar.

    Va a `get_token()` (no a `validate()`) perquè és el punt que SimpleJWT fa servir per
    construir el REFRESH; l'access en surt via `RefreshToken.access_token`, que copia tots
    els claims llevat de `exp`/`iat`/`jti`/`token_type` (`tokens.py:379-413`). Un sol lloc,
    doncs, i els dos tokens queden segellats.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token[TENANT_CLAIM] = connection.schema_name
        return token


class TenantTokenObtainPairSerializer(TenantClaimMixin, TokenObtainPairSerializer):
    """El serializer de login del producte (tenant i public), amb el claim.

    Els urlconfs l'endollen a la vista de la llibreria amb
    `TokenObtainPairView.as_view(serializer_class=…)`. No hi ha subclasse de vista a posta:
    aquest mòdul l'importa `DEFAULT_AUTHENTICATION_CLASSES`, o sigui que s'avalua MENTRE
    DRF encara s'inicialitza; importar-hi `simplejwt.views` (que arrossega
    `rest_framework.generics` → `rest_framework.views`) hi provoca un import circular real.
    """


class TenantJWTAuthentication(JWTAuthentication):
    """Autenticació JWT que exigeix que el token sigui d'AQUEST schema.

    La comprovació va a `get_validated_token()`, just després que el pare validi signatura
    i caducitat i abans de tocar la BD: un token d'un altre schema no arriba mai a fer el
    `.get(pk=…)`.

    L'error és deliberadament INDISTINGIBLE del d'un token caducat o mal signat (mateixa
    excepció `InvalidToken` → mateix 401, mateix missatge genèric). Dir «aquest token és
    d'un altre schema» convertiria l'endpoint en un oracle d'enumeració d'schemas.
    """

    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        if token.payload.get(TENANT_CLAIM) != connection.schema_name:
            raise InvalidToken('Token no vàlid o caducat')
        return token
