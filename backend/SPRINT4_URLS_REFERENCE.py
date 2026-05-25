
# Sprint 4 — URLs fitting wizard
# Afegeix al teu fitxer d'URLs API:

from fhort.fitting.fitting_views import (
    crear_fitting_view, tancar_fitting_view,
    anullar_fitting_view, llistat_fittings_view
)
from django.urls import path

urlpatterns_sprint4 = [
    path('v1/size-fittings/<int:sf_id>/crear-fitting/', crear_fitting_view),
    path('v1/size-fittings/<int:sf_id>/fittings/', llistat_fittings_view),
    path('v1/fittings/<int:fitting_id>/tancar/', tancar_fitting_view),
    path('v1/fittings/<int:fitting_id>/anullar/', anullar_fitting_view),
]
# Endpoints PATCH /api/v1/fitting-lines/{id}/ → ja existeix al router
