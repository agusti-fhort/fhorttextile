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
