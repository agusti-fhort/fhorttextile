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

# Sprint 7A — Design Freeze + Talla Base. Paths amb 3+ segments
# (no col·lisionen amb ModelViewSet detail), però prepended per coherència.
try:
    from fhort.pom.wizard_views import (
        aprovar_design_freeze_view,
        guardar_talla_base_view,
        confirmar_talla_base_view,
        base_measurements_view,
    )
    _sprint7_model_paths = [
        path('models/<int:model_id>/aprovar-design-freeze/', aprovar_design_freeze_view),
        path('models/<int:model_id>/guardar-talla-base/',    guardar_talla_base_view),
        path('models/<int:model_id>/confirmar-talla-base/',  confirmar_talla_base_view),
        path('models/<int:model_id>/base-measurements/',     base_measurements_view),
    ]
except Exception:
    _sprint7_model_paths = []

urlpatterns = _sprint6_paths + _sprint7_model_paths + router.urls
