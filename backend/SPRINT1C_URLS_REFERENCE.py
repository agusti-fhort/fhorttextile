
# =============================================================================
# REFERÈNCIA MANUAL — si les URLs no s'han afegit automàticament
# Afegeix al teu fitxer urls.py principal on tens el router
# =============================================================================

from fhort.tasks.views_sprint1c import TascaViewSet, PaquetServeiViewSet
from fhort.fitting.views_sprint1c import SessioFittingViewSet
# ModelFitxerViewSet ja registrat a fhort.models_app.urls (model-fitxers)

# Registra als endpoints existents:
router.register(r'tasques', TascaViewSet, basename='tasca')
router.register(r'paquets-servei', PaquetServeiViewSet, basename='paquet-servei')
router.register(r'sessions-fitting', SessioFittingViewSet, basename='sessio-fitting')

# ModelServei (afegir al router de models_app si en tens un):
# router.register(r'model-serveis', ModelServeiViewSet, basename='model-servei')

# Endpoints resultants:
# GET /api/v1/tasques/
# GET /api/v1/paquets-servei/
# GET /api/v1/model-fitxers/
# GET /api/v1/sessions-fitting/
# GET /api/v1/model-serveis/
