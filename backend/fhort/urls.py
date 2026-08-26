from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from fhort.auth_jwt import TenantTokenObtainPairSerializer
from fhort.tenants.views_auth_central import AuthCentralTriaView, AuthCentralView
from fhort.tenants.views_bescanvi import AuthBescanviView

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT
    # La vista és la de la llibreria; el que canvia és el serializer, que segella el token
    # amb `tenant_schema` (fhort/auth_jwt.py). Un token només val a l'schema que l'ha emès.
    path('api/token/', TokenObtainPairView.as_view(
        serializer_class=TenantTokenObtainPairSerializer), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Login únic (F1): la MATEIXA porta central que a urls_public.py. Aquí no és redundància:
    # a PROD el host neutre (login.*) resol al public, però la pantalla /entrar viu a l'únic
    # build i s'ha de poder validar des d'un host de tenant (staging.*, llei S19). El lookup
    # és cross-schema per construcció: el host des del qual s'entra no altera el resultat.
    path('api/auth/central/', AuthCentralView.as_view(), name='auth-central'),
    path('api/auth/central/tria/', AuthCentralTriaView.as_view(), name='auth-central-tria'),

    # Login únic (F2): bescanvi del codi per una sessió. NOMÉS aquí (mai al public): és el
    # host del tenant qui ha d'emetre el JWT, perquè la sessió neixi al seu propi origen.
    path('api/auth/bescanvi/', AuthBescanviView.as_view(), name='auth-bescanvi'),

    # OpenAPI schema + docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API v1 — apps core del PLM
    path('api/v1/', include('fhort.accounts.urls')),
    path('api/v1/', include('fhort.models_app.urls')),
    path('api/v1/', include('fhort.pom.urls')),
    path('api/v1/', include('fhort.fitting.urls')),
    path('api/v1/', include('fhort.tasks.urls')),
    path('api/v1/', include('fhort.planning.urls')),
    path('api/v1/', include('fhort.commerce.urls')),
    # FASE A — EL MOTOR DE PATRONS, DARRERE L'INTERRUPTOR (`FTT_PATTERNS_ENABLED`, settings.py).
    #
    # EL PANY VIU AQUÍ I NO DINS DE L'APP, per tres raons:
    #   1. És UN sol punt. Tota l'API del motor penja d'aquest únic `include`: les set rutes de
    #      `patterns/urls.py` (pattern-files, piece-roles, pattern-poms, pattern-segments,
    #      sew-relations, sew-proposal-rejections, sew-tolerance-acceptances) i totes les
    #      `@action` que en pengen (render.svg, geometry, download-links, identificar,
    #      export…). Cap altre `urls.py` importa l'app: no hi ha cap ruta de patrons a fora.
    #   2. Dona un 404 DE VERITAT. Un permís de DRF donaria 403, que és una altra frase: diria
    #      «això existeix i no hi pots entrar» quan el que volem dir és «això aquí no hi és».
    #      Amb el flag apagat el resolutor no coneix el prefix i respon el 404 de Django sol.
    #   3. No toca cap vista del motor — que és, a més, on hi ha una altra mà treballant.
    #
    # S'escriu desplegant una llista i no amb un `if` que faci `append` al final del fitxer
    # perquè la POSICIÓ s'ha de conservar: amb el flag encès, aquest `urlpatterns` és element
    # per element el d'abans d'existir el flag, amb `patterns` entre `commerce` i `tenants`.
    *([path('api/v1/', include('fhort.patterns.urls'))] if settings.FTT_PATTERNS_ENABLED else []),
    # P7 — els RECURSOS del Brand (vincles de federació). App SHARED servida des de l'URLconf
    # de tenant a posta: la taula és a `public` però qui la consulta és el tenant (vegeu
    # fhort/tenants/urls.py). Cap ruta al public: un Brand mira els seus vincles des de casa.
    path('api/v1/', include('fhort.tenants.urls')),
]
