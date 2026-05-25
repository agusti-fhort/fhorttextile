# Sprint 1C — SessioFittingViewSet
from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend


class SessioFittingViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['client', 'tipus', 'estat', 'temporada', 'any']
    ordering = ['-data_sessio']

    def get_queryset(self):
        try:
            from .models import SessioFitting
            return SessioFitting.objects.select_related('client', 'responsable').all()
        except Exception:
            from fhort.fitting.models import SessioFitting
            return SessioFitting.objects.all()

    def get_serializer_class(self):
        from .serializers_sprint1c import SessioFittingSerializer
        return SessioFittingSerializer
