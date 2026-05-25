
# Sprint 2 — URLs per a action views
# Afegeix al teu fitxer d'URLs API (on tens el router):

from fhort.tasks.action_views import generar_tasques_view, processar_gate_view, resum_tasques_view
from django.urls import path

# Dins de urlpatterns, ABANS del router.urls:
urlpatterns_sprint2 = [
    path('v1/models/<int:model_id>/generar-tasques/', generar_tasques_view, name='generar-tasques'),
    path('v1/models/<int:model_id>/resum-tasques/', resum_tasques_view, name='resum-tasques'),
    path('v1/model-tasques/<int:tasca_id>/processar-gate/', processar_gate_view, name='processar-gate'),
]

# Integra com:
# urlpatterns = urlpatterns_sprint2 + [path('', include(router.urls))]
