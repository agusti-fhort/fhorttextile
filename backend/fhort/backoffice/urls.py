# Sprint 1 — Capa 9: rutes del backoffice (muntades sota api/backoffice/v1/).
from django.urls import path

from .views import BackofficeMeView, BackofficeTokenObtainView, health_view

urlpatterns = [
    path('auth/login/', BackofficeTokenObtainView.as_view(), name='backoffice-login'),
    path('auth/me/', BackofficeMeView.as_view(), name='backoffice-me'),
    path('health/', health_view, name='backoffice-health'),
]
