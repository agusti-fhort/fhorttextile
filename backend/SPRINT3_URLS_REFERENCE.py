
# Sprint 3 — URLs grading
# Afegeix al teu fitxer d'URLs API:

from fhort.pom.grading_views import tancar_base_view, regenerar_talles_view, taula_mesures_view
from django.urls import path

urlpatterns_sprint3 = [
    path('v1/size-fittings/<int:sf_id>/tancar-base/', tancar_base_view),
    path('v1/size-fittings/<int:sf_id>/regenerar-talles/', regenerar_talles_view),
    path('v1/size-fittings/<int:sf_id>/taula-mesures/', taula_mesures_view),
]
