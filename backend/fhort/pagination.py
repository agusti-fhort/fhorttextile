"""Paginació per defecte del projecte. Pas 5C — mida configurable via ?page_size=N."""
from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 200
