from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import company_calendar_view, user_jornada_view, AbsenciaViewSet


router = DefaultRouter()
router.register('absencies', AbsenciaViewSet, basename='absencia')

urlpatterns = [
    path('company-calendar/', company_calendar_view, name='company-calendar'),
    path('users/<int:user_id>/jornada/', user_jornada_view, name='user-jornada'),
    *router.urls,
]
