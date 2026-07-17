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
from .views_invoices import InvoiceSerieViewSet, InvoiceViewSet, VATRateViewSet
from .views_seeding import SeedProfileViewSet
from .views_legal import (
    LegalActionViewSet, LegalDocumentViewSet, LegalDocumentVersionViewSet,
)

router = DefaultRouter()
router.register('tenants', ClientViewSet, basename='tenant')
router.register('plans', PlanViewSet, basename='plan')
router.register('serveis', ServiceCatalogViewSet, basename='servei')
router.register('contractes', TenantContractViewSet, basename='contracte')
router.register('perfils-sembra', SeedProfileViewSet, basename='perfil-sembra')
router.register('facturacio/series', InvoiceSerieViewSet, basename='invoice-serie')
router.register('facturacio/tipus-iva', VATRateViewSet, basename='vat-rate')
router.register('facturacio/factures', InvoiceViewSet, basename='invoice')
router.register('legal/documents', LegalDocumentViewSet, basename='legal-document')
router.register('legal/versions', LegalDocumentVersionViewSet, basename='legal-version')

urlpatterns = [
    path('auth/login/', BackofficeTokenObtainView.as_view(), name='backoffice-login'),
    path('auth/me/', BackofficeMeView.as_view(), name='backoffice-me'),
    path('health/', health_view, name='backoffice-health'),
    path('pricing/public/', pricing_public_view, name='backoffice-pricing-public'),
    path('pricing/for-client/<str:codi_tenant>/', pricing_for_client_view, name='backoffice-pricing-for-client'),
    path('pricing/', pricing_view, name='backoffice-pricing'),
    path('facturacio/generar/', generate_invoice_view),
    path('legal/pending/', LegalActionViewSet.as_view({'get': 'pending'}), name='legal-pending'),
    path('legal/accept/', LegalActionViewSet.as_view({'post': 'accept'}), name='legal-accept'),
    path('legal/acceptances/', LegalActionViewSet.as_view({'get': 'acceptances'}), name='legal-acceptances'),
    path('', include(router.urls)),
]
