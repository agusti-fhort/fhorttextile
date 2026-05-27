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

# Sprint 7A — wizard de POMs. Els paths 'poms/suggerits/', 'poms/cerca/' i
# 'poms/crear-tenant/' col·lisionarien amb POMMasterViewSet detail (poms/<pk>/);
# els posem ABANS del router perquè Django els resolgui primer.
try:
    from .wizard_views import (
        poms_suggerits_view,
        cerca_poms_view,
        crear_pom_tenant_view,
        editar_nomenclatura_pom_view,
    )
    _sprint7_pom_paths = [
        path('poms/suggerits/',    poms_suggerits_view),
        path('poms/cerca/',        cerca_poms_view),
        path('poms/crear-tenant/', crear_pom_tenant_view),
        path('poms/<int:pom_id>/nomenclatura/', editar_nomenclatura_pom_view),
    ]
except Exception:
    _sprint7_pom_paths = []

urlpatterns = _sprint7_pom_paths + router.urls
