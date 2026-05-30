from rest_framework.routers import DefaultRouter

from .views import (
    GradingVersionViewSet,
    POMAlertViewSet,
    SizeFittingViewSet,
)

router = DefaultRouter()
router.register('size-fittings', SizeFittingViewSet, basename='size-fitting')
router.register('grading-versions', GradingVersionViewSet, basename='grading-version')
router.register('pom-alerts', POMAlertViewSet, basename='pom-alert')

urlpatterns = router.urls
