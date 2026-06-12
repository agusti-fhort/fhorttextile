import uuid as _uuid

from django.urls import path, register_converter
from rest_framework.routers import DefaultRouter

from .graded_spec_views import GradedSpecTableView


class CaseInsensitiveUUIDConverter:
    """Com el converter 'uuid' de Django però accepta hex en MAJÚSCULA i minúscula.
    El built-in només casa [0-9a-f] (minúscula) → una convocatòria amb hex en majúscula
    provocava 404 a totes les rutes de grup. Retorna un uuid.UUID (filtre ORM case-insensitive)."""
    regex = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'

    def to_python(self, value):
        return _uuid.UUID(value)

    def to_url(self, value):
        return str(value)


register_converter(CaseInsensitiveUUIDConverter, 'ciuuid')
from .views import (
    GradingVersionViewSet,
    POMAlertViewSet,
    SizeFittingViewSet,
    FittingSessionViewSet,
    PieceFittingViewSet,
    PieceFittingLineViewSet,
    FittingPhotoViewSet,
    group_reschedule,
    group_add_model,
    group_remove_model,
    group_attendees,
    group_remove,
)

router = DefaultRouter()
router.register('size-fittings', SizeFittingViewSet, basename='size-fitting')
router.register('grading-versions', GradingVersionViewSet, basename='grading-version')
router.register('pom-alerts', POMAlertViewSet, basename='pom-alert')
# Sprint 5B.6 — fitting REST API
router.register('fitting-sessions', FittingSessionViewSet, basename='fitting-session')
router.register('piece-fittings', PieceFittingViewSet, basename='piece-fitting')
router.register('piece-fitting-lines', PieceFittingLineViewSet, basename='piece-fitting-line')
router.register('fitting-photos', FittingPhotoViewSet, basename='fitting-photo')

# Peça 2 — gestió de convocatòria (per UUID). Abans del router perquè els paths
# de grup són específics (no col·lisionen amb les rutes <pk> del ViewSet).
group_urls = [
    path('fitting-sessions/group/<ciuuid:conv_uuid>/reschedule/', group_reschedule,
         name='fitting-group-reschedule'),
    path('fitting-sessions/group/<ciuuid:conv_uuid>/add-model/', group_add_model,
         name='fitting-group-add-model'),
    path('fitting-sessions/group/<ciuuid:conv_uuid>/remove-model/<int:model_id>/', group_remove_model,
         name='fitting-group-remove-model'),
    path('fitting-sessions/group/<ciuuid:conv_uuid>/attendees/', group_attendees,
         name='fitting-group-attendees'),
    # Ajust 1 — eliminar la convocatòria en bloc (path sense sufix → cal després dels específics).
    path('fitting-sessions/group/<ciuuid:conv_uuid>/', group_remove,
         name='fitting-group-remove'),
]

urlpatterns = group_urls + router.urls + [
    # F3 — taula de specs graduades (GradingVersion activa) per a la fitxa tècnica.
    path('fitting/<int:sf_id>/graded-table/', GradedSpecTableView.as_view(), name='graded-spec-table'),
]
