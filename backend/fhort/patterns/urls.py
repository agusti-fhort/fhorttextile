"""Rutes del motor de patrons.

Convenció de `commerce/` (S0-B9): el prefix del mòdul viu DINS del register, no a
l'`include` de `fhort/urls.py`, que sempre és `api/v1/`.
"""
from rest_framework.routers import DefaultRouter

from .annotation_views import PatternPOMViewSet, PatternSegmentViewSet, SewRelationViewSet
from .views import PatternFileViewSet

router = DefaultRouter()
router.register(r'patterns/pattern-files', PatternFileViewSet, basename='patterns-pattern-files')
router.register(r'patterns/pattern-poms', PatternPOMViewSet, basename='patterns-pattern-poms')
router.register(r'patterns/pattern-segments', PatternSegmentViewSet,
                basename='patterns-pattern-segments')
router.register(r'patterns/sew-relations', SewRelationViewSet, basename='patterns-sew-relations')

urlpatterns = router.urls
