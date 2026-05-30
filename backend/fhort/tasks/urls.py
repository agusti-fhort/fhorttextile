from rest_framework.routers import DefaultRouter

from .views import (
    ModelTascaViewSet,
    TascaViewSet,
    TimerEntradaViewSet,
)

router = DefaultRouter()
router.register('model-tasques', ModelTascaViewSet, basename='model-tasca')
router.register('timers', TimerEntradaViewSet, basename='timer')

# Sprint 1C — new endpoints (the sprint1c TascaViewSet is richer than the one in views.py).
# If sprint1c does not exist yet, we fall back to the legacy TascaViewSet.
try:
    from fhort.tasks.views_sprint1c import TascaViewSet as _Sprint1CTascaViewSet, PaquetServeiViewSet
    router.register(r'tasques', _Sprint1CTascaViewSet, basename='tasca')
    router.register(r'paquets-servei', PaquetServeiViewSet, basename='paquet-servei')
except Exception:
    router.register('tasques', TascaViewSet, basename='tasca')

try:
    from fhort.fitting.views_sprint1c import SessioFittingViewSet
    router.register(r'sessions-fitting', SessioFittingViewSet, basename='sessio-fitting')
except Exception:
    pass

try:
    from fhort.models_app.views import ModelServeiViewSet
    router.register(r'model-serveis', ModelServeiViewSet, basename='model-servei')
except Exception:
    pass

# model-fitxers already registered in fhort.models_app.urls

urlpatterns = router.urls



# Sprint 2 — action views
try:
    from fhort.tasks.action_views import generate_tasks_view, process_gate_view, tasks_summary_view
    from django.urls import path as _path
    _sprint2_paths = [
        _path('models/<int:model_id>/generar-tasques/', generate_tasks_view),
        _path('models/<int:model_id>/resum-tasques/', tasks_summary_view),
        _path('model-tasques/<int:tasca_id>/processar-gate/', process_gate_view),
    ]
    urlpatterns = _sprint2_paths + urlpatterns
except Exception as _e:
    pass



# Sprint 3 — grading views
try:
    from fhort.pom.grading_views import tancar_base_view, regenerar_talles_view, taula_mesures_view
    from django.urls import path as _path3
    _sprint3_paths = [
        _path3('size-fittings/<int:sf_id>/tancar-base/', tancar_base_view),
        _path3('size-fittings/<int:sf_id>/regenerar-talles/', regenerar_talles_view),
        _path3('size-fittings/<int:sf_id>/taula-mesures/', taula_mesures_view),
    ]
    urlpatterns = _sprint3_paths + urlpatterns
except Exception as _e3:
    pass



# Sprint 4 — fitting wizard
try:
    from fhort.fitting.fitting_views import (
        crear_fitting_view, tancar_fitting_view,
        anullar_fitting_view, llistat_fittings_view,
    )
    from django.urls import path as _path4
    _sprint4_paths = [
        _path4('size-fittings/<int:sf_id>/crear-fitting/', crear_fitting_view),
        _path4('size-fittings/<int:sf_id>/fittings/', llistat_fittings_view),
        _path4('fittings/<int:fitting_id>/tancar/', tancar_fitting_view),
        _path4('fittings/<int:fitting_id>/anullar/', anullar_fitting_view),
    ]
    urlpatterns = _sprint4_paths + urlpatterns
except Exception as _e4:
    pass

# Sprint 6 — AI extraction: lives in fhort.models_app.urls (avoids collision with ModelViewSet detail)

# Sprint 7A — Design Freeze + Base Size wizard: paths relocated to
# models_app/urls.py (models/...) and pom/urls.py (poms/...) to avoid
# collisions with the detail routers and with the duplicated 'v1/' prefix.

# Sprint S2 — Sizing + TenantConfig endpoints
try:
    from fhort.pom.s2_views import (
        targets_list_view,
        construction_types_list_view,
        sizing_profiles_view,
        sizing_profile_detail_view,
        clone_sizing_profile_view,
        update_grading_rule_view,
        tenant_config_view,
        pom_global_cerca_view,
        garment_types_per_target_view,
    )
    from django.urls import path as _p_s2
    _s2_paths = [
        _p_s2('targets/', targets_list_view),
        _p_s2('construction-types/', construction_types_list_view),
        _p_s2('sizing-profiles/', sizing_profiles_view),
        _p_s2('sizing-profiles/<int:pk>/', sizing_profile_detail_view),
        _p_s2('sizing-profiles/<int:pk>/clonar/', clone_sizing_profile_view),
        _p_s2('grading-rule-sets/<int:rule_set_id>/regles/<str:pom_codi>/', update_grading_rule_view),
        _p_s2('tenant-config/', tenant_config_view),
        _p_s2('pom-global/cerca/', pom_global_cerca_view),
        _p_s2('garment-types-by-target/', garment_types_per_target_view),
    ]
    urlpatterns = _s2_paths + urlpatterns
except Exception as _e_s2:
    import logging
    logging.getLogger(__name__).error(f"Sprint S2 URLs: {_e_s2}")

# Sprint S4 — Versioning + CM/INCH + History
try:
    from fhort.pom.s4_views import (
        update_grading_rule_with_history_view,
        grading_rule_history_view,
        sizing_profile_versions_view,
        grading_rules_with_units_view,
        restore_version_view,
    )
    from django.urls import path as _p_s4
    _s4_paths = [
        _p_s4('grading-rule-sets/<int:rule_set_id>/regles/<str:pom_codi>/editar/',
               update_grading_rule_with_history_view),
        _p_s4('grading-rule-sets/<int:rule_set_id>/historial/',
               grading_rule_history_view),
        _p_s4('grading-rule-sets/<int:rule_set_id>/regles/',
               grading_rules_with_units_view),
        _p_s4('sizing-profiles/<int:profile_id>/versions/',
               sizing_profile_versions_view),
        _p_s4('sizing-profiles/<int:profile_id>/restaurar/',
               restore_version_view),
    ]
    urlpatterns = _s4_paths + urlpatterns
except Exception as _e_s4:
    import logging
    logging.getLogger(__name__).error(f"Sprint S4 URLs: {_e_s4}")

# Sprint S6 — HTM + CM/INCH unified
try:
    from fhort.pom.s6_views import (
        pom_htm_view,
        base_measurements_with_units_view,
        graded_specs_with_units_view,
        fitting_lines_with_units_view,
    )
    from django.urls import path as _p_s6
    _s6_paths = [
        _p_s6('poms/<int:pom_id>/htm/', pom_htm_view),
        _p_s6('models/<int:model_id>/base-measurements-units/', base_measurements_with_units_view),
        _p_s6('size-fittings/<int:sf_id>/graded-specs-units/', graded_specs_with_units_view),
        _p_s6('fittings/<int:fitting_id>/lines-units/', fitting_lines_with_units_view),
    ]
    urlpatterns = _s6_paths + urlpatterns
except Exception as _e_s6:
    import logging
    logging.getLogger(__name__).error(f"Sprint S6 URLs: {_e_s6}")

# Sprint S8 — PDF/CSV export
try:
    from fhort.pom.s8_views import (
        export_grading_csv_view,
        export_size_set_csv_view,
        export_fitting_csv_view,
        export_model_spec_pdf_view,
    )
    from django.urls import path as _p_s8
    _s8_paths = [
        _p_s8('grading-rule-sets/<int:rule_set_id>/export/csv/',
               export_grading_csv_view),
        _p_s8('sizing-profiles/<int:profile_id>/export/csv/',
               export_size_set_csv_view),
        _p_s8('fittings/<int:fitting_id>/export/csv/',
               export_fitting_csv_view),
        _p_s8('models/<int:model_id>/export/pdf/',
               export_model_spec_pdf_view),
    ]
    urlpatterns = _s8_paths + urlpatterns
except Exception as _e_s8:
    import logging
    logging.getLogger(__name__).error(f"Sprint S8 URLs: {_e_s8}")

# Sprint S9 — Onboarding
try:
    from fhort.pom.s9_views import (
        onboarding_status_view,
        setup_tenant_from_excel_view,
        setup_client_config_view,
    )
    from django.urls import path as _p_s9
    _s9_paths = [
        _p_s9('onboarding/status/', onboarding_status_view),
        _p_s9('onboarding/setup-from-excel/', setup_tenant_from_excel_view),
        _p_s9('onboarding/config/', setup_client_config_view),
    ]
    urlpatterns = _s9_paths + urlpatterns
except Exception as _e_s9:
    import logging
    logging.getLogger(__name__).error(f"Sprint S9 URLs: {_e_s9}")

# Sprint S10 — Integrated fitting
try:
    from fhort.pom.s10_views import fitting_vs_spec_view, model_fitting_history_view
    from django.urls import path as _p_s10
    _s10_paths = [
        _p_s10('size-fittings/<int:sf_id>/fittings/<int:fitting_id>/vs-spec/',
                fitting_vs_spec_view),
        _p_s10('models/<int:model_id>/fitting-history/',
                model_fitting_history_view),
    ]
    urlpatterns = _s10_paths + urlpatterns
except Exception as _e_s10:
    import logging
    logging.getLogger(__name__).error(f"Sprint S10 URLs: {_e_s10}")

# Sprint S11 — Automatic notifications
try:
    from fhort.pom.s11_views import (
        pom_alerts_summary_view,
        resolve_alert_view,
        model_alerts_view,
        check_tolerances_view,
    )
    from django.urls import path as _p_s11
    _s11_paths = [
        _p_s11('alerts/summary/', pom_alerts_summary_view),
        _p_s11('alerts/<int:alert_id>/resoldre/', resolve_alert_view),
        _p_s11('models/<int:model_id>/alerts/', model_alerts_view),
        _p_s11('models/<int:model_id>/check-tolerances/', check_tolerances_view),
    ]
    urlpatterns = _s11_paths + urlpatterns
except Exception as _e_s11:
    import logging
    logging.getLogger(__name__).error(f"Sprint S11 URLs: {_e_s11}")
