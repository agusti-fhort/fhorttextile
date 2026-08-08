from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CustomerPOMAliasViewSet,
    GarmentGroupViewSet,
    GarmentGroupPOMMapViewSet,
    GarmentPOMMapViewSet,
    GarmentTypePOMMapViewSet,
    GarmentTypeViewSet,
    GradingRuleSetViewSet,
    GradingRuleViewSet,
    ItemBaseMeasurementViewSet,
    ItemBaseSetViewSet,
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
# U2 — les dues germanes de l'acumulació. Mateix contracte que la de l'item; el que canvia és
# l'àncora (`?garment_type=` · `?garment_group=`). L'acumulació de les tres és un endpoint a part.
router.register('garment-type-pom-maps', GarmentTypePOMMapViewSet, basename='garment-type-pom-map')
router.register('garment-group-pom-maps', GarmentGroupPOMMapViewSet, basename='garment-group-pom-map')
router.register('item-base-measurements', ItemBaseMeasurementViewSet, basename='item-base-measurement')
router.register('item-base-sets', ItemBaseSetViewSet, basename='item-base-set')
router.register('customer-pom-aliases', CustomerPOMAliasViewSet, basename='customer-pom-alias')

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

# Size Map Setup wizard — function views (no router).
try:
    from .size_map_views import (
        size_map_lookups_view,
        size_map_match_view,
        size_map_preview_view,
        size_map_grading_preview_view,
        size_map_grading_preview_file_view,
        size_map_create_view,
        size_map_systems_view,
    )
    _size_map_paths = [
        path('size-map/lookups/',              size_map_lookups_view),
        path('size-map/match/',                size_map_match_view),
        path('size-map/preview/',              size_map_preview_view),
        path('size-map/grading-preview/',      size_map_grading_preview_view),
        path('size-map/grading-preview-file/', size_map_grading_preview_file_view),
        path('size-map/create/',               size_map_create_view),
        path('size-map/systems/',              size_map_systems_view),
    ]
except Exception:
    _size_map_paths = []

# Diccionari de nomenclatura del client (setup): plantilla + preview + commit.
try:
    from .dictionary_views import (
        dictionary_template_view,
        dictionary_preview_view,
        dictionary_commit_view,
    )
    _dictionary_paths = [
        path('pom/customers/<int:customer_id>/dictionary/template/', dictionary_template_view),
        path('pom/customers/<int:customer_id>/dictionary/preview/',  dictionary_preview_view),
        path('pom/customers/<int:customer_id>/dictionary/commit/',   dictionary_commit_view),
    ]
except Exception:
    _dictionary_paths = []

# U1/U2 — les dues preguntes del catàleg. Abans del router pel mateix motiu que el wizard:
# `poms/<id>/us/` xocaria amb el detall de POMMasterViewSet.
try:
    from .cataleg_views import item_acumulacio_view, pom_us_view
    # A2 — la mateixa pregunta per a un RUN. Abans del router pel mateix motiu que la de POMs:
    # `size-systems/<id>/us/` xocaria amb el detall de `SizeSystemViewSet`.
    from .size_library_views import size_system_us_view
    _cataleg_paths = [
        path('poms/<int:pom_id>/us/', pom_us_view),
        path('garment-type-items/<int:item_id>/acumulacio/', item_acumulacio_view),
        path('size-systems/<int:size_system_id>/us/', size_system_us_view),
    ]
except Exception:
    _cataleg_paths = []

# El VOCABULARI D'IDENTITAT d'una mesura (capes + instàncies). Un sol GET perquè les dues
# taules es miren sempre juntes. NO és el diccionari de nomenclatura del client (a sobre).
try:
    from .identity_views import measurement_identity_vocabulary_view
    _identity_paths = [
        path('mesures/diccionari/', measurement_identity_vocabulary_view),
    ]
except Exception:
    _identity_paths = []

urlpatterns = (_sprint7_pom_paths + _size_map_paths + _dictionary_paths
               + _cataleg_paths + _identity_paths + router.urls)
