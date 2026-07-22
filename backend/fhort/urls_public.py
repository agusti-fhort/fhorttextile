"""URLconf del schema PUBLIC (PUBLIC_SCHEMA_URLCONF).

Serveix les rutes accessibles des del tenant 'public': l'admin de public, la
pròpia auth del backoffice (JWT) i les seves rutes d'API. NO inclou les apps de
producte (accounts, models_app, pom, fitting, tasks, planning) — aquelles són
TENANT i viuen a fhort.urls (ROOT_URLCONF).
"""
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
from fhort.tenants.views_discovery import TenantDiscoveryView

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT (auth pròpia del backoffice — usat a partir del Sprint 1)
    # La vista és la de la llibreria; el que canvia és el serializer, que segella el token
    # amb `tenant_schema` (fhort/auth_jwt.py). Un token només val a l'schema que l'ha emès.
    path('api/token/', TokenObtainPairView.as_view(
        serializer_class=TenantTokenObtainPairSerializer), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # Tenant-discovery (porta única): email → correu amb els accessos. Públic, resposta uniforme.
    path('api/discovery/', TenantDiscoveryView.as_view(), name='tenant-discovery'),

    # OpenAPI schema + docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # Backoffice (SHARED, només public)
    path('api/backoffice/v1/', include('fhort.backoffice.urls')),
]
