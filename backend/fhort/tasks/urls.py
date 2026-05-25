from rest_framework.routers import DefaultRouter

from .views import (
    ModelTascaViewSet,
    TascaViewSet,
    TimerEntradaViewSet,
)

router = DefaultRouter()
router.register('tasques', TascaViewSet, basename='tasca')
router.register('model-tasques', ModelTascaViewSet, basename='model-tasca')
router.register('timers', TimerEntradaViewSet, basename='timer')

urlpatterns = router.urls
