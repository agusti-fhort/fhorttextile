"""Rutes de l'app `tenants` servides des de l'URLconf de TENANT (fhort/urls.py).

Sembla una contradicció — `fhort.tenants` és SHARED i les seves taules viuen a `public` —
però no ho és: qui consulta els seus propis vincles és una petició de tenant, des del host
del tenant, amb la sessió del tenant. La taula és a `public` i s'hi arriba pel `search_path`
(diagnosi P7 §A1). Muntar-ho a `urls_public.py` obligaria el Brand a sortir de casa seva per
veure una cosa que és seva.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_recursos import RecursViewSet

router = DefaultRouter()
router.register('recursos', RecursViewSet, basename='recurs')

urlpatterns = [
    path('', include(router.urls)),
]
