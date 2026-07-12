"""Rutes del motor de patrons.

Buit a S1: el motor encara no té ni models ni endpoints (arriben a S3). El router
es declara ja perquè l'`include` de `fhort/urls.py` tingui destí i l'app quedi
endollada al projecte des del primer sprint.

Convenció (calcada de commerce/): el prefix del mòdul viu DINS del register
—`router.register(r'patterns/<recurs>', ..., basename='patterns-<recurs>')`— no a
l'`include`, que sempre és `api/v1/`.
"""
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = router.urls
