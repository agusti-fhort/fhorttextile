from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    GarmentGroupViewSet,
    GarmentPOMMapViewSet,
    GarmentTypeViewSet,
    GradingRuleSetViewSet,
    GradingRuleViewSet,
    POMCategoryViewSet,
    POMMasterViewSet,
    SizeDefinitionViewSet,
    SizeSystemViewSet,
)

router = DefaultRouter()
router.register('poms', POMMasterViewSet, basename='pom')
router.register('pom-categories', POMCategoryViewSet, basename='pom-category')
router.register('size-systems', SizeSystemViewSet, basename='size-system')
router.register('size-definitions', SizeDefinitionViewSet, basename='size-definition')
router.register('garment-groups', GarmentGroupViewSet, basename='garment-group')
router.register('garment-types', GarmentTypeViewSet, basename='garment-type')
router.register('grading-rule-sets', GradingRuleSetViewSet, basename='grading-rule-set')
router.register('grading-rules', GradingRuleViewSet, basename='grading-rule')
router.register('garment-pom-maps', GarmentPOMMapViewSet, basename='garment-pom-map')

# Sprint 7A — POM wizard. The 'poms/suggerits/', 'poms/cerca/' and
# 'poms/crear-tenant/' paths would collide with POMMasterViewSet detail (poms/<pk>/);
# we put them BEFORE the router so Django resolves them first.
try:
    from .wizard_views import (
        suggested_poms_view,
        search_poms_view,
        create_tenant_pom_view,
        edit_pom_nomenclature_view,
    )
    _sprint7_pom_paths = [
        path('poms/suggerits/',    suggested_poms_view),
        path('poms/cerca/',        search_poms_view),
        path('poms/crear-tenant/', create_tenant_pom_view),
        path('poms/<int:pom_id>/nomenclatura/', edit_pom_nomenclature_view),
    ]
except Exception:
    _sprint7_pom_paths = []

urlpatterns = _sprint7_pom_paths + router.urls
