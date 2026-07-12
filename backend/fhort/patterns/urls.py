"""Rutes del motor de patrons.

Convenció de `commerce/` (S0-B9): el prefix del mòdul viu DINS del register, no a
l'`include` de `fhort/urls.py`, que sempre és `api/v1/`.
"""
from rest_framework.routers import DefaultRouter

from .views import PatternFileViewSet

router = DefaultRouter()
router.register(r'patterns/pattern-files', PatternFileViewSet, basename='patterns-pattern-files')

urlpatterns = router.urls
