from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (UserViewSet, me_view,
                    password_reset_validate, password_reset_confirm)


router = DefaultRouter()
router.register('users', UserViewSet, basename='user')

urlpatterns = [
    path('me/', me_view, name='me'),
    path('password-reset/validate/', password_reset_validate, name='password_reset_validate'),
    path('password-reset/confirm/', password_reset_confirm, name='password_reset_confirm'),
    *router.urls,
]
