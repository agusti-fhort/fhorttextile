from rest_framework.routers import DefaultRouter

from .views import (
    GradingVersionViewSet,
    POMAlertViewSet,
    SizeFittingViewSet,
    FittingSessionViewSet,
    PieceFittingViewSet,
    PieceFittingLineViewSet,
    FittingPhotoViewSet,
)

router = DefaultRouter()
router.register('size-fittings', SizeFittingViewSet, basename='size-fitting')
router.register('grading-versions', GradingVersionViewSet, basename='grading-version')
router.register('pom-alerts', POMAlertViewSet, basename='pom-alert')
# Sprint 5B.6 — fitting REST API
router.register('fitting-sessions', FittingSessionViewSet, basename='fitting-session')
router.register('piece-fittings', PieceFittingViewSet, basename='piece-fitting')
router.register('piece-fitting-lines', PieceFittingLineViewSet, basename='piece-fitting-line')
router.register('fitting-photos', FittingPhotoViewSet, basename='fitting-photo')

urlpatterns = router.urls
