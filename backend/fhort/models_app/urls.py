from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BaseMeasurementViewSet,
    ModelFitxerViewSet,
    ModelViewSet,
    WatchpointViewSet,
    ai_analysis_view,
    consumption_delivery_view,
    model_dashboard_view,
    model_timeline_view,
    create_model_wizard,
    generate_grading_view,
    set_size_override_view,
    escalat_ajustar_talla_view,
    grading_status_view,
    base_measurements_reorder_view,
    base_stages_view,
    iso_shrinkage_view,
    next_model_ref,
    registre_activitat_view,
    suggested_poms_view,
    materialize_poms_view,
    gravar_pom_view,
    close_table_view,
    reorder_measurements_view,
    set_measurements_view,
    measurements_table_view,
    update_fabric_view,
    update_model_step2,
    upload_file_view,
    measurements_chat_view,
    set_pom_regim_view,
)

from .views_size_check import SizeCheckViewSet, SizeCheckLineViewSet
from .ftt_template_views import DocumentTemplateViewSet
from .item_fitxer_views import ItemFitxerViewSet

router = DefaultRouter()
router.register('models', ModelViewSet, basename='model')
router.register('model-fitxers', ModelFitxerViewSet, basename='model-fitxer')
router.register('item-fitxers', ItemFitxerViewSet, basename='item-fitxer')
router.register('base-measurements', BaseMeasurementViewSet, basename='base-measurement')
router.register('size-checks', SizeCheckViewSet, basename='size-check')
router.register('size-check-lines', SizeCheckLineViewSet, basename='size-check-line')
router.register('watchpoints', WatchpointViewSet, basename='watchpoint')
router.register('document-templates', DocumentTemplateViewSet, basename='document-template')

# Sprint 6 — AI extraction. Paths before the router so 'models/extract-from-file/'
# is not captured by 'models/<pk>/' of the ModelViewSet detail.
try:
    from .extraction_views import (
        delete_model_view,
        import_session_cribratge_view,
        import_session_talles_view,
        import_session_extraccio_view,
        import_session_poms_view,
        import_session_grading_preview_view,
        import_session_mesures_view,
        import_session_library_prefill_view,
        import_session_teixit_view,
        import_session_confirmar_view,
    )
    _sprint6_paths = [
        # P6 — camí d'import VELL retirat (0 consumidors al frontend; el wizard nou és l'únic camí).
        # `extraction_service`/`EXTRACTION_PROMPT` es MANTENEN: són VIUS (els usa el wizard nou + size-map).
        path('models/<int:model_id>/delete/', delete_model_view, name='delete-model'),
        path('import-sessions/cribratge/', import_session_cribratge_view,
             name='import-session-cribratge'),
        path('import-sessions/<uuid:token>/talles/', import_session_talles_view,
             name='import-session-talles'),
        path('import-sessions/<uuid:token>/extraccio/', import_session_extraccio_view,
             name='import-session-extraccio'),
        path('import-sessions/<uuid:token>/poms/', import_session_poms_view,
             name='import-session-poms'),
        path('import-sessions/<uuid:token>/grading-preview/', import_session_grading_preview_view,
             name='import-session-grading-preview'),
        path('import-sessions/<uuid:token>/mesures/', import_session_mesures_view,
             name='import-session-mesures'),
        path('import-sessions/<uuid:token>/library-prefill/', import_session_library_prefill_view,
             name='import-session-library-prefill'),
        path('import-sessions/<uuid:token>/teixit/', import_session_teixit_view,
             name='import-session-teixit'),
        path('import-sessions/<uuid:token>/confirmar/', import_session_confirmar_view,
             name='import-session-confirmar'),
    ]
except Exception:
    _sprint6_paths = []

# Sprint 7A — Design Freeze + Base Size. Paths with 3+ segments
# (they do not collide with ModelViewSet detail), but prepended for consistency.
try:
    from fhort.pom.wizard_views import (
        approve_design_freeze_view,
        save_base_size_view,
        confirm_base_size_view,
        base_measurements_view,
    )
    _sprint7_model_paths = [
        path('models/<int:model_id>/aprovar-design-freeze/', approve_design_freeze_view),
        path('models/<int:model_id>/guardar-talla-base/',    save_base_size_view),
        # D5 — `confirmar-talla-base/` JUBILADA (cap consumidor a frontend/src; resta del
        # wizard vell). La vista es conserva importable per a test_g6_segell (camí 6 del segell).
        path('models/<int:model_id>/base-measurements/',     base_measurements_view),
    ]
except Exception:
    _sprint7_model_paths = []

# Sprint 8 — AI extraction chat. Paths before the router to avoid
# collision with 'models/<pk>/' of the ModelViewSet detail.
try:
    from .chat_views import extraction_chat_view, start_extraction_chat_view
    _sprint8_paths = [
        path('models/chat-extraccio/',          extraction_chat_view),
        path('models/iniciar-chat-extraccio/',  start_extraction_chat_view),
    ]
except Exception:
    _sprint8_paths = []

# Sprint S17 — Technical-sheet import via the Anthropic API.
try:
    from .tech_sheet_views import TechSheetExtractView, TechSheetCreateModelView
    _sprint17_paths = [
        path('models/extract-sheet/',     TechSheetExtractView.as_view(),     name='extract-sheet'),
        path('models/create-from-sheet/', TechSheetCreateModelView.as_view(), name='create-from-sheet'),
    ]
except Exception:
    _sprint17_paths = []

# Sprint Bulk — import massiu de models per Excel (col·lecció).
try:
    from .bulk_import_views import (
        template_view as bulk_template_view,
        upload_view as bulk_upload_view,
        commit_view as bulk_commit_view,
        errors_report_view as bulk_errors_report_view,
        reconciliation_view as bulk_reconciliation_view,
    )
    _bulk_paths = [
        path('bulk-import/template/', bulk_template_view, name='bulk-import-template'),
        path('bulk-import/upload/', bulk_upload_view, name='bulk-import-upload'),
        path('bulk-import/<int:import_id>/reconciliation/', bulk_reconciliation_view, name='bulk-import-reconciliation'),
        path('bulk-import/<int:import_id>/commit/', bulk_commit_view, name='bulk-import-commit'),
        path('bulk-import/<int:import_id>/errors-report/', bulk_errors_report_view, name='bulk-import-errors-report'),
    ]
except Exception:
    _bulk_paths = []

# Editor de fitxa tècnica (estat + lock col·laboratiu). Paths de 3 segments → no col·lisionen
# amb el detall del router (models/<pk>/), però es prepended per consistència amb la resta.
try:
    from .tech_sheet_editor_views import (
        get_or_create_template,
        update_template,
    )
    _techsheet_editor_paths = [
        # Fitxa per-model jubilada (Fase 2 .ftt) → els endpoints viuen a ftt-documents/.
        # Es mantenen només les plantilles de fitxa per Customer (TS-3).
        path('customers/<int:customer_id>/tech-sheet-template/',        get_or_create_template, name='tech-sheet-template-detail'),
        path('customers/<int:customer_id>/tech-sheet-template/update/', update_template,        name='tech-sheet-template-update'),
    ]
except Exception:
    _techsheet_editor_paths = []

# Documents .ftt sobre el Finder (ModelFitxer tipus TECHSHEET). Crear/carregar/desar.
try:
    from .ftt_document_views import (
        FttDocumentAssetView,
        FttDocumentCreateView,
        FttDocumentDetailView,
        FttDocumentExportView,
        FttDocumentLockView,
        FttDocumentUnlockView,
        FttSaveAsTemplateView,
    )
    _ftt_document_paths = [
        path('models/<int:model_id>/ftt-document/', FttDocumentCreateView.as_view(), name='ftt-document-create'),
        path('ftt-documents/<int:fitxer_id>/', FttDocumentDetailView.as_view(), name='ftt-document-detail'),
        path('ftt-documents/<int:fitxer_id>/lock/', FttDocumentLockView.as_view(), name='ftt-document-lock'),
        path('ftt-documents/<int:fitxer_id>/unlock/', FttDocumentUnlockView.as_view(), name='ftt-document-unlock'),
        path('ftt-documents/<int:fitxer_id>/export/', FttDocumentExportView.as_view(), name='ftt-document-export'),
        path('ftt-documents/<int:fitxer_id>/save-as-template/', FttSaveAsTemplateView.as_view(), name='ftt-save-as-template'),
        path('ftt-documents/<int:fitxer_id>/asset/<str:asset_name>/', FttDocumentAssetView.as_view(), name='ftt-document-asset'),
    ]
except Exception:
    _ftt_document_paths = []

urlpatterns = (
    [
        path('models/next-ref/', next_model_ref),
        path('models/create-wizard/', create_model_wizard),
        path('models/<int:model_id>/update-step2/', update_model_step2),
        path('models/<int:model_id>/poms-suggerits/', suggested_poms_view),
        path('models/<int:model_id>/materialitzar-poms/', materialize_poms_view),
        path('models/<int:model_id>/gravar-pom/', gravar_pom_view),
        path('models/<int:model_id>/tancar-taula/', close_table_view),
        path('models/<int:model_id>/taula-mesures/', measurements_table_view),
        path('models/<int:model_id>/set-measurements/', set_measurements_view),
        path('models/<int:model_id>/reorder-measurements/', reorder_measurements_view),
        path('models/<int:model_id>/upload-fitxer/', upload_file_view),
        path('models/<int:model_id>/analisi-ia/', ai_analysis_view),
        path('models/<int:model_id>/xat-mesures/', measurements_chat_view),
        path('models/<int:model_id>/generar-grading/', generate_grading_view),
        # D5 — `set-size-override/` JUBILADA: el wrapper JS existia i cap component el cridava;
        # l'editor real fa servir escalat/ajustar-talla. Vista conservada per a test_g6_segell.
        path('models/<int:model_id>/escalat/ajustar-talla/', escalat_ajustar_talla_view),
        path('models/<int:model_id>/grading-status/', grading_status_view),
        path('models/<int:model_id>/base-measurements/reorder/', base_measurements_reorder_view),
        path('models/<int:model_id>/base-stages/', base_stages_view),
        path('models/<int:model_id>/pom/<int:pom_id>/regim/', set_pom_regim_view),
        path('models/iso-shrinkage/', iso_shrinkage_view),
        path('models/<int:model_id>/update-fabric/', update_fabric_view),
        path('models/<int:model_id>/albara/', consumption_delivery_view),
        path('models/<int:model_id>/dashboard/', model_dashboard_view),
        path('models/<int:model_id>/timeline/', model_timeline_view),
        path('registre-activitat/', registre_activitat_view),
    ]
    + _sprint6_paths
    + _sprint7_model_paths
    + _sprint8_paths
    + _sprint17_paths
    + _bulk_paths
    + _techsheet_editor_paths
    + _ftt_document_paths
    + router.urls
)
