from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import BaseMeasurementViewSet, ModelFitxerViewSet, ModelViewSet, create_model_wizard, next_model_ref

router = DefaultRouter()
router.register('models', ModelViewSet, basename='model')
router.register('model-fitxers', ModelFitxerViewSet, basename='model-fitxer')
router.register('base-measurements', BaseMeasurementViewSet, basename='base-measurement')

# Sprint 6 — extracció IA. Paths abans del router perquè 'models/extract-from-file/'
# no quedi capturat per 'models/<pk>/' del ModelViewSet detail.
try:
    from .extraction_views import (
        extract_from_file_view,
        create_from_extraction_view,
        delete_model_view,
    )
    _sprint6_paths = [
        path('models/extract-from-file/', extract_from_file_view),
        path('models/create-from-extraction/', create_from_extraction_view),
        path('models/<int:model_id>/delete/', delete_model_view, name='delete-model'),
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

# Sprint 8 — xat IA d'extracció. Paths abans del router per evitar
# col·lisió amb 'models/<pk>/' del ModelViewSet detail.
try:
    from .chat_views import chat_extraccio_view, iniciar_chat_extraccio_view
    _sprint8_paths = [
        path('models/chat-extraccio/',          chat_extraccio_view),
        path('models/iniciar-chat-extraccio/',  iniciar_chat_extraccio_view),
    ]
except Exception:
    _sprint8_paths = []

# Sprint S17 — Importació de fitxes tècniques via API Anthropic.
try:
    from .tech_sheet_views import TechSheetExtractView, TechSheetCreateModelView
    _sprint17_paths = [
        path('models/extract-sheet/',     TechSheetExtractView.as_view(),     name='extract-sheet'),
        path('models/create-from-sheet/', TechSheetCreateModelView.as_view(), name='create-from-sheet'),
    ]
except Exception:
    _sprint17_paths = []

urlpatterns = (
    [
        path('models/next-ref/', next_model_ref),
        path('models/create-wizard/', create_model_wizard),
    ]
    + _sprint6_paths
    + _sprint7_model_paths
    + _sprint8_paths
    + _sprint17_paths
    + router.urls
)
