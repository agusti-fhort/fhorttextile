from django.urls import path
from rest_framework.routers import DefaultRouter

from .graded_spec_views import GradedSpecTableView
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
    path('fitting-sessions/group/<uuid:conv_uuid>/reschedule/', group_reschedule,
         name='fitting-group-reschedule'),
    path('fitting-sessions/group/<uuid:conv_uuid>/add-model/', group_add_model,
         name='fitting-group-add-model'),
    path('fitting-sessions/group/<uuid:conv_uuid>/remove-model/<int:model_id>/', group_remove_model,
         name='fitting-group-remove-model'),
    path('fitting-sessions/group/<uuid:conv_uuid>/attendees/', group_attendees,
         name='fitting-group-attendees'),
    # Ajust 1 — eliminar la convocatòria en bloc (path sense sufix → cal després dels específics).
    path('fitting-sessions/group/<uuid:conv_uuid>/', group_remove,
         name='fitting-group-remove'),
]

urlpatterns = group_urls + router.urls + [
    # F3 — taula de specs graduades (GradingVersion activa) per a la fitxa tècnica.
    path('fitting/<int:sf_id>/graded-table/', GradedSpecTableView.as_view(), name='graded-spec-table'),
]
