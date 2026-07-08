from rest_framework.routers import DefaultRouter

from .views import (
    UnitViewSet, ProductViewSet, ProductRecipeViewSet, ProductSupplierViewSet,
    ProductComponentViewSet, ProductPriceGTIViewSet,
    QuoteViewSet, QuoteLineViewSet, PaymentTermsViewSet,
    SalesOrderViewSet, SalesOrderLineViewSet, WorkOrderViewSet, ExpenseViewSet,
)

# Mòdul Comercial Studio — mestre d'articles (B1). Escriptura gated CONFIGURE.
router = DefaultRouter()
router.register(r'commerce/units', UnitViewSet, basename='commerce-unit')
router.register(r'commerce/products', ProductViewSet, basename='commerce-product')
router.register(r'commerce/recipe-lines', ProductRecipeViewSet, basename='commerce-recipe-line')
router.register(r'commerce/product-suppliers', ProductSupplierViewSet, basename='commerce-product-supplier')
router.register(r'commerce/product-components', ProductComponentViewSet, basename='commerce-product-component')
router.register(r'commerce/price-exceptions', ProductPriceGTIViewSet, basename='commerce-price-exception')
router.register(r'commerce/payment-terms', PaymentTermsViewSet, basename='commerce-payment-terms')
# Documents comercials — Quote (B2). send/pdf/convert són @action sota quotes/{pk}/.
router.register(r'commerce/quotes', QuoteViewSet, basename='commerce-quote')
router.register(r'commerce/quote-lines', QuoteLineViewSet, basename='commerce-quote-line')
# Documents comercials — SalesOrder (comanda, B3b). pdf és @action sota orders/{pk}/.
router.register(r'commerce/orders', SalesOrderViewSet, basename='commerce-order')
router.register(r'commerce/order-lines', SalesOrderLineViewSet, basename='commerce-order-line')
# Encàrrecs / ordres de treball (B4a). close/review són @action sota work-orders/{pk}/.
router.register(r'commerce/work-orders', WorkOrderViewSet, basename='commerce-work-order')
# Despeses d'un encàrrec (B4b), satèl·lit filtrat per ?work_order=.
router.register(r'commerce/expenses', ExpenseViewSet, basename='commerce-expense')

urlpatterns = router.urls
