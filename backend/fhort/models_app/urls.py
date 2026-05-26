from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ModelFitxerViewSet, ModelViewSet

router = DefaultRouter()
router.register('models', ModelViewSet, basename='model')
router.register('model-fitxers', ModelFitxerViewSet, basename='model-fitxer')

# Sprint 6 — extracció IA. Paths abans del router perquè 'models/extract-from-file/'
# no quedi capturat per 'models/<pk>/' del ModelViewSet detail.
try:
    from .extraction_views import extract_from_file_view, create_from_extraction_view
    _sprint6_paths = [
        path('models/extract-from-file/', extract_from_file_view),
        path('models/create-from-extraction/', create_from_extraction_view),
    ]
except Exception:
    _sprint6_paths = []

urlpatterns = _sprint6_paths + router.urls
