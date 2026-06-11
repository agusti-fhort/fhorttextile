from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (company_calendar_view, user_jornada_view, AbsenciaViewSet,
                    plan_compute_view, plan_preview_view, plan_apply_view,
                    plan_snapshots_view, plan_current_view, calendar_events_view,
                    plan_reorder_view, plan_eligible_technicians_view,
                    plan_assign_batch_view)


router = DefaultRouter()
router.register('absencies', AbsenciaViewSet, basename='absencia')

urlpatterns = [
    path('company-calendar/', company_calendar_view, name='company-calendar'),
    path('users/<int:user_id>/jornada/', user_jornada_view, name='user-jornada'),
    # Sprint B — motor de planificació (substitueix el plan/compute per-model-en-sèrie).
    path('plan/compute/', plan_compute_view, name='plan-compute'),
    path('plan/preview/', plan_preview_view, name='plan-preview'),
    path('plan/apply/', plan_apply_view, name='plan-apply'),
    path('plan/snapshots/', plan_snapshots_view, name='plan-snapshots'),
    path('plan/current/', plan_current_view, name='plan-current'),
    path('calendar/events/', calendar_events_view, name='calendar-events'),
    path('plan/reorder/', plan_reorder_view, name='plan-reorder'),
    # Sprint multi-assign — wizard d'assignació (task_type × persona × data opcional).
    path('plan/eligible-technicians/', plan_eligible_technicians_view, name='plan-eligible-technicians'),
    path('plan/assign-batch/', plan_assign_batch_view, name='plan-assign-batch'),
    *router.urls,
]
