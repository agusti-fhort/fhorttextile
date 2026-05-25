from rest_framework.routers import DefaultRouter

from .views import ModelFitxerViewSet, ModelViewSet

router = DefaultRouter()
router.register('models', ModelViewSet, basename='model')
router.register('model-fitxers', ModelFitxerViewSet, basename='model-fitxer')

urlpatterns = router.urls
