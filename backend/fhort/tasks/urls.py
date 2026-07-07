from rest_framework.routers import DefaultRouter

from .views import TimerEntradaViewSet

router = DefaultRouter()
router.register('timers', TimerEntradaViewSet, basename='timer')

# model-fitxers already registered in fhort.models_app.urls

# Sprint B — new task catalog (TaskType) + task instances (ModelTask). Isolated from the
# legacy Tasca viewset above; both coexist. Registered before router.urls.
try:
    from fhort.tasks.views_b import TaskTypeViewSet, ModelTaskViewSet
    router.register(r'task-types', TaskTypeViewSet, basename='task-type')
    router.register(r'model-task-items', ModelTaskViewSet, basename='model-task-item')
except Exception:
    pass

# Sprint E — confecció: Supplier + Production (read-only). Registered before router.urls.
try:
    from fhort.tasks.views_b import SupplierViewSet, ProductionViewSet
    router.register(r'suppliers', SupplierViewSet, basename='supplier')
    router.register(r'productions', ProductionViewSet, basename='production')
except Exception:
    pass

# Sprint Customer — arxiu de clients (font del prefix de codi-gen). CRUD; escriptura gated CONFIGURE.
try:
    from fhort.tasks.views_b import CustomerViewSet
    router.register(r'customers', CustomerViewSet, basename='customer')
except Exception:
    pass

# Sprint G — taula de temps: GarmentTypeItem + TaskTimeEstimate. Registered before router.urls.
try:
    from fhort.tasks.views_b import GarmentTypeItemViewSet, TaskTimeEstimateViewSet
    router.register(r'garment-type-items', GarmentTypeItemViewSet, basename='garment-type-item')
    router.register(r'task-time-estimates', TaskTimeEstimateViewSet, basename='task-time-estimate')
except Exception:
    pass

urlpatterns = router.urls



# Sprint B — define tasks of a model (bulk/individual). Requires define_tasks capability.
try:
    from fhort.tasks.views_b import (define_model_tasks_view, transition_task_view,
                                     claim_task_view, assign_model_view, unassign_model_view,
                                     model_task_log_view, open_model_task_view)
    from django.urls import path as _path_b
    _sprintb_paths = [
        _path_b('models/<int:model_id>/define-tasks/', define_model_tasks_view),
        _path_b('models/<int:model_id>/task-log/', model_task_log_view),
        _path_b('model-task-items/<int:pk>/transition/', transition_task_view),
        # P4a-back — self-claim entre tècnics (handoff §6). Gated execute_tasks (NO define_tasks).
        _path_b('model-task-items/<int:pk>/claim/', claim_task_view),
        # Porta-menú — obrir una tasca concreta del model (crea-si-falta + En curs). execute_tasks.
        _path_b('models/<int:model_id>/open-task/', open_model_task_view),
        # Tram 2 — assignar/desassignar model a tècnic (compute de cua sencera). define_tasks.
        _path_b('models/<int:model_id>/assign/', assign_model_view),
        _path_b('models/<int:model_id>/unassign/', unassign_model_view),
    ]
    urlpatterns = _sprintb_paths + urlpatterns
except Exception:
    pass

# Sprint M2 — Anàlisi de temps: rollup per fase + arbre drill-down (gated view_team_tasks).
try:
    from fhort.tasks.views_b import (time_by_phase_view, time_tree_view, time_set_estimate_view,
                                     time_by_model_view)
    from django.urls import path as _path_m2
    _sprintm2_paths = [
        _path_m2('time-analysis/by-phase/', time_by_phase_view),
        _path_m2('time-analysis/tree/', time_tree_view),
        _path_m2('time-analysis/set-estimate/', time_set_estimate_view),
        # Planning-complet P1 — eix MODEL (ModelTask→fase→task_type; dimensió que TaskTimeEstimate no té).
        _path_m2('time-analysis/by-model/', time_by_model_view),
    ]
    urlpatterns = _sprintm2_paths + urlpatterns
except Exception:
    pass

# Sprint B (motor) — plan/compute + preview + apply + snapshots viuen ara a
# fhort/planning/urls.py (motor determinista). El plan/compute per-model-en-sèrie de
# l'Sprint H s'ha jubilat (services_h.py).

# Sprint D — gate del responsable (avanç de fase sense sessió). Requires close_gates.
try:
    from fhort.tasks.views_b import (gate_model_view, gate_bulk_view, gate_ready_models_view,
                                     regress_model_view)
    from django.urls import path as _path_d
    _sprintd_paths = [
        _path_d('models/<int:model_id>/gate/', gate_model_view),
        _path_d('models/<int:model_id>/regress/', regress_model_view),
        _path_d('gates/bulk/', gate_bulk_view),
        _path_d('gates/ready/', gate_ready_models_view),
    ]
    urlpatterns = _sprintd_paths + urlpatterns
except Exception:
    pass

# Sprint E — confecció: demanar producció + transicions de cicle. Requires schedule_fittings.
try:
    from fhort.tasks.views_b import request_production_view, production_status_view
    from django.urls import path as _path_e
    _sprinte_paths = [
        _path_e('models/<int:model_id>/request-production/', request_production_view),
        _path_e('productions/<int:pk>/status/', production_status_view),
    ]
    urlpatterns = _sprinte_paths + urlpatterns
except Exception:
    pass



# Sprint 3 — grading views
try:
    from fhort.pom.grading_views import close_base_view, regenerate_sizes_view, measurements_table_view
    from django.urls import path as _path3
    _sprint3_paths = [
        _path3('size-fittings/<int:sf_id>/tancar-base/', close_base_view),
        _path3('size-fittings/<int:sf_id>/regenerar-talles/', regenerate_sizes_view),
        _path3('size-fittings/<int:sf_id>/taula-mesures/', measurements_table_view),
    ]
    urlpatterns = _sprint3_paths + urlpatterns
except Exception as _e3:
    pass



# Sprint 4 — fitting wizard: removed in 5B.5 (SFFitting/SFFittingLinia retired).
# The fitting cycle now lives in fhort.fitting.services (FittingSession/PieceFitting).

# Sprint 6 — AI extraction: lives in fhort.models_app.urls (avoids collision with ModelViewSet detail)

# Sprint 7A — Design Freeze + Base Size wizard: paths relocated to
# models_app/urls.py (models/...) and pom/urls.py (poms/...) to avoid
# collisions with the detail routers and with the duplicated 'v1/' prefix.

# Sprint S2 — Sizing + TenantConfig endpoints
try:
    from fhort.pom.s2_views import (
        targets_list_view,
        construction_types_list_view,
        fit_types_list_view,
        sizing_profiles_view,
        sizing_profile_detail_view,
        clone_sizing_profile_view,
        update_grading_rule_view,
        tenant_config_view,
        pom_global_search_view,
        garment_types_by_target_view,
    )
    from django.urls import path as _p_s2
    _s2_paths = [
        _p_s2('targets/', targets_list_view),
        _p_s2('construction-types/', construction_types_list_view),
        _p_s2('fit-types/', fit_types_list_view),
        _p_s2('sizing-profiles/', sizing_profiles_view),
        _p_s2('sizing-profiles/<int:pk>/', sizing_profile_detail_view),
        _p_s2('sizing-profiles/<int:pk>/clonar/', clone_sizing_profile_view),
        _p_s2('grading-rule-sets/<int:rule_set_id>/regles/<str:pom_codi>/', update_grading_rule_view),
        _p_s2('tenant-config/', tenant_config_view),
        _p_s2('pom-global/cerca/', pom_global_search_view),
        _p_s2('garment-types-by-target/', garment_types_by_target_view),
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
    )
    from django.urls import path as _p_s6
    _s6_paths = [
        _p_s6('poms/<int:pom_id>/htm/', pom_htm_view),
        _p_s6('models/<int:model_id>/base-measurements-units/', base_measurements_with_units_view),
        _p_s6('size-fittings/<int:sf_id>/graded-specs-units/', graded_specs_with_units_view),
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
    )
    from django.urls import path as _p_s8
    _s8_paths = [
        _p_s8('grading-rule-sets/<int:rule_set_id>/export/csv/',
               export_grading_csv_view),
        _p_s8('sizing-profiles/<int:profile_id>/export/csv/',
               export_size_set_csv_view),
        _p_s8('fittings/peca/<int:pf_id>/export/csv/',
               export_fitting_csv_view),
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
    from fhort.pom.s10_views import fitting_vs_spec_view
    from django.urls import path as _p_s10
    _s10_paths = [
        _p_s10('fittings/peca/<int:pf_id>/vs-spec/',
                fitting_vs_spec_view),
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
