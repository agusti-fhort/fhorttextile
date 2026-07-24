"""Rutes de l'app `tenants` servides des de l'URLconf de TENANT (fhort/urls.py).

Sembla una contradicció — `fhort.tenants` és SHARED i les seves taules viuen a `public` —
però no ho és: qui consulta els seus propis vincles és una petició de tenant, des del host
del tenant, amb la sessió del tenant. La taula és a `public` i s'hi arriba pel `search_path`
(diagnosi P7 §A1). Muntar-ho a `urls_public.py` obligaria el Brand a sortir de casa seva per
veure una cosa que és seva.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views_encarrecs import EncarrecViewSet
from .views_recursos import RecursViewSet

router = DefaultRouter()
# Les dues cares de la federació, servides des del mateix lloc perquè són la mateixa taula
# vista des dels dos extrems: `recursos` és el que veu la Marca (amb qui pot comptar) i
# `encarrecs` el que veu l'Estudi (què li han encomanat). Cadascuna té el seu 403.
router.register('recursos', RecursViewSet, basename='recurs')
router.register('encarrecs', EncarrecViewSet, basename='encarrec')

urlpatterns = [
    path('', include(router.urls)),
]
