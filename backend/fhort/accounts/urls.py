from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import UserViewSet, me_view


router = DefaultRouter()
router.register('users', UserViewSet, basename='user')

urlpatterns = [
    path('me/', me_view, name='me'),
    *router.urls,
]
