"""Rutes del motor de patrons.

Convenció de `commerce/` (S0-B9): el prefix del mòdul viu DINS del register, no a
l'`include` de `fhort/urls.py`, que sempre és `api/v1/`.
"""
from rest_framework.routers import DefaultRouter

from .annotation_views import (
    PatternPOMViewSet, PatternSegmentViewSet, SewProposalRejectionViewSet, SewRelationViewSet,
    SewToleranceAcceptanceViewSet,
)
from .views import PatternFileViewSet

router = DefaultRouter()
router.register(r'patterns/pattern-files', PatternFileViewSet, basename='patterns-pattern-files')
router.register(r'patterns/pattern-poms', PatternPOMViewSet, basename='patterns-pattern-poms')
router.register(r'patterns/pattern-segments', PatternSegmentViewSet,
                basename='patterns-pattern-segments')
router.register(r'patterns/sew-relations', SewRelationViewSet, basename='patterns-sew-relations')
# Els rebuigs de proposta: llegir-los i desfer-los. Crear-los és `sew-relations/
# rebutjar-proposta/` — la llei del rebuig té una sola porta d'entrada.
router.register(r'patterns/sew-proposal-rejections', SewProposalRejectionViewSet,
                basename='patterns-sew-proposal-rejections')
# Auditoria de tolerància (H/T2): acceptar/desacceptar desajustos, append-only. Primera baula
# del mòdul d'auditoria de model — es llegeix per model (transversal) o per costura (històric).
router.register(r'patterns/sew-tolerance-acceptances', SewToleranceAcceptanceViewSet,
                basename='patterns-sew-tolerance-acceptances')

urlpatterns = router.urls
