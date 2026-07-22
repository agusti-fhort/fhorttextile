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
    path('api/v1/', include('fhort.patterns.urls')),
]
