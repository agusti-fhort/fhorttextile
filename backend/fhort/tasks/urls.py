from rest_framework.routers import DefaultRouter

from .views import (
    ModelTascaViewSet,
    TascaCatalegViewSet,
    TimerEntradaViewSet,
)

router = DefaultRouter()
router.register('tasca-catalegs', TascaCatalegViewSet, basename='tasca-cataleg')
router.register('model-tasques', ModelTascaViewSet, basename='model-tasca')
router.register('timers', TimerEntradaViewSet, basename='timer')

urlpatterns = router.urls
