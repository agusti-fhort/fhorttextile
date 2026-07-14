from django.urls import path
from rest_framework.routers import DefaultRouter

from fhort.backoffice.views_legal_tenant import legal_accept_tenant_view

from .views import (UserViewSet, me_view, me_change_password,
                    password_reset_validate, password_reset_confirm)


router = DefaultRouter()
router.register('users', UserViewSet, basename='user')

urlpatterns = [
    path('me/', me_view, name='me'),
    path('me/change-password/', me_change_password, name='me_change_password'),
    # F4 P-LEGAL: acceptació legal per l'admin del tenant (única ruta legal al tenant).
    path('legal/accept/', legal_accept_tenant_view, name='legal_accept_tenant'),
    path('password-reset/validate/', password_reset_validate, name='password_reset_validate'),
    path('password-reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
    *router.urls,
]
