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

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT
    # La vista és la de la llibreria; el que canvia és el serializer, que segella el token
    # amb `tenant_schema` (fhort/auth_jwt.py). Un token només val a l'schema que l'ha emès.
    path('api/token/', TokenObtainPairView.as_view(
        serializer_class=TenantTokenObtainPairSerializer), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

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
