from rest_framework.routers import DefaultRouter

from .views import (
    UnitViewSet, ProductViewSet, ProductRecipeViewSet, ProductSupplierViewSet,
    ProductComponentViewSet, ProductPriceGTIViewSet,
    QuoteViewSet, QuoteLineViewSet,
)

# Mòdul Comercial Studio — mestre d'articles (B1). Escriptura gated CONFIGURE.
router = DefaultRouter()
router.register(r'commerce/units', UnitViewSet, basename='commerce-unit')
router.register(r'commerce/products', ProductViewSet, basename='commerce-product')
router.register(r'commerce/recipe-lines', ProductRecipeViewSet, basename='commerce-recipe-line')
router.register(r'commerce/product-suppliers', ProductSupplierViewSet, basename='commerce-product-supplier')
router.register(r'commerce/product-components', ProductComponentViewSet, basename='commerce-product-component')
router.register(r'commerce/price-exceptions', ProductPriceGTIViewSet, basename='commerce-price-exception')
# Documents comercials — Quote (B2). send/pdf són @action sota quotes/{pk}/.
router.register(r'commerce/quotes', QuoteViewSet, basename='commerce-quote')
router.register(r'commerce/quote-lines', QuoteLineViewSet, basename='commerce-quote-line')

urlpatterns = router.urls
