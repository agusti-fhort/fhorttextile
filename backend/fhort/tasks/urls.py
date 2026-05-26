from rest_framework.routers import DefaultRouter

from .views import (
    ModelTascaViewSet,
    TascaViewSet,
    TimerEntradaViewSet,
)

router = DefaultRouter()
router.register('model-tasques', ModelTascaViewSet, basename='model-tasca')
router.register('timers', TimerEntradaViewSet, basename='timer')

# Sprint 1C — endpoints nous (sprint1c TascaViewSet és més ric que el de views.py).
# Si sprint1c no existeix encara, caiem al TascaViewSet legacy.
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

# model-fitxers ja registrat a fhort.models_app.urls

urlpatterns = router.urls



# Sprint 2 — action views
try:
    from fhort.tasks.action_views import generar_tasques_view, processar_gate_view, resum_tasques_view
    from django.urls import path as _path
    _sprint2_paths = [
        _path('models/<int:model_id>/generar-tasques/', generar_tasques_view),
        _path('models/<int:model_id>/resum-tasques/', resum_tasques_view),
        _path('model-tasques/<int:tasca_id>/processar-gate/', processar_gate_view),
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

# Sprint 6 — extracció IA: viu a fhort.models_app.urls (evita col·lisió amb ModelViewSet detail)

# Sprint 7A — Design Freeze + Talla Base wizard: paths reubicats a
# models_app/urls.py (models/...) i pom/urls.py (poms/...) per evitar
# col·lisions amb els routers detail i amb el prefix duplicat 'v1/'.

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
        _p_s2('v1/targets/', targets_list_view),
        _p_s2('v1/construction-types/', construction_types_list_view),
        _p_s2('v1/sizing-profiles/', sizing_profiles_view),
        _p_s2('v1/sizing-profiles/<int:pk>/', sizing_profile_detail_view),
        _p_s2('v1/sizing-profiles/<int:pk>/clonar/', clone_sizing_profile_view),
        _p_s2('v1/grading-rule-sets/<int:rule_set_id>/regles/<str:pom_codi>/', update_grading_rule_view),
        _p_s2('v1/tenant-config/', tenant_config_view),
        _p_s2('v1/pom-global/cerca/', pom_global_cerca_view),
        _p_s2('v1/garment-types/per-target/', garment_types_per_target_view),
    ]
    urlpatterns = _s2_paths + urlpatterns
except Exception as _e_s2:
    import logging
    logging.getLogger(__name__).error(f"Sprint S2 URLs: {_e_s2}")
