from rest_framework.routers import DefaultRouter

from .views import (
    UnitViewSet, ProductViewSet, ProductRecipeViewSet, ProductSupplierViewSet,
    ProductComponentViewSet, ProductPriceGTIViewSet,
)

# Mòdul Comercial Studio — mestre d'articles (B1). Escriptura gated CONFIGURE.
router = DefaultRouter()
router.register(r'commerce/units', UnitViewSet, basename='commerce-unit')
router.register(r'commerce/products', ProductViewSet, basename='commerce-product')
router.register(r'commerce/recipe-lines', ProductRecipeViewSet, basename='commerce-recipe-line')
router.register(r'commerce/product-suppliers', ProductSupplierViewSet, basename='commerce-product-supplier')
router.register(r'commerce/product-components', ProductComponentViewSet, basename='commerce-product-component')
router.register(r'commerce/price-exceptions', ProductPriceGTIViewSet, basename='commerce-price-exception')

urlpatterns = router.urls
