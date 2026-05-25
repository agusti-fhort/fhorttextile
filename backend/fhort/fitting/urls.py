from rest_framework.routers import DefaultRouter

from .views import (
    FitCommentViewSet,
    FittingLineViewSet,
    FittingViewSet,
    GradedSpecLineViewSet,
    GradingVersionViewSet,
    POMAlertViewSet,
    SizeFittingViewSet,
)

router = DefaultRouter()
router.register('size-fittings', SizeFittingViewSet, basename='size-fitting')
router.register('grading-versions', GradingVersionViewSet, basename='grading-version')
router.register('graded-spec-lines', GradedSpecLineViewSet, basename='graded-spec-line')
router.register('fittings', FittingViewSet, basename='fitting')
router.register('fitting-lines', FittingLineViewSet, basename='fitting-line')
router.register('fit-comments', FitCommentViewSet, basename='fit-comment')
router.register('pom-alerts', POMAlertViewSet, basename='pom-alert')

urlpatterns = router.urls
