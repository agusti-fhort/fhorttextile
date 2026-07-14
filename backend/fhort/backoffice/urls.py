# Sprint 1 — Capa 9: rutes del backoffice (muntades sota api/backoffice/v1/).
# Sprint 2 — Capa 1/2: router de tenants i plans.
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BackofficeMeView, BackofficeTokenObtainView, health_view
from .views_tenants import ClientViewSet, PlanViewSet
from .views_contracts import ServiceCatalogViewSet, TenantContractViewSet
from .views_contracts import generate_invoice_view
from .views_pricing import pricing_public_view, pricing_view
from .views_pricing_client import pricing_for_client_view
from .views_seeding import SeedProfileViewSet

router = DefaultRouter()
router.register('tenants', ClientViewSet, basename='tenant')
router.register('plans', PlanViewSet, basename='plan')
router.register('serveis', ServiceCatalogViewSet, basename='servei')
router.register('contractes', TenantContractViewSet, basename='contracte')
router.register('perfils-sembra', SeedProfileViewSet, basename='perfil-sembra')

urlpatterns = [
    path('auth/login/', BackofficeTokenObtainView.as_view(), name='backoffice-login'),
    path('auth/me/', BackofficeMeView.as_view(), name='backoffice-me'),
    path('health/', health_view, name='backoffice-health'),
    path('pricing/public/', pricing_public_view, name='backoffice-pricing-public'),
    path('pricing/for-client/<str:codi_tenant>/', pricing_for_client_view, name='backoffice-pricing-for-client'),
    path('pricing/', pricing_view, name='backoffice-pricing'),
    path('facturacio/generar/', generate_invoice_view),
    path('', include(router.urls)),
]
