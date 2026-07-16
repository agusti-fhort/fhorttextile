# F3 P-FREE-SEED (B5): endpoints dels perfils de sembra (backoffice, ADMIN).
# CRUD de SeedProfile + metadades de blocs amb comptadors reals de fhort. El
# recompte del catàleg viu a tasks (seed_block_counts); el backoffice hi delega
# sense importar cap model de tenant (frontera SHARED).
from django.db import transaction
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import SeedProfile
from .serializers_seeding import SeedProfileSerializer
from .views import HasBackofficeRole


class SeedProfileViewSet(viewsets.ModelViewSet):
    """CRUD dels perfils de sembra. Només ADMIN.

    `is_default_free` és únic (constraint parcial a la BD): en marcar-ne un, es
    degraden els altres dins la mateixa transacció per no xocar amb la constraint.
    """

    queryset = SeedProfile.objects.all()
    serializer_class = SeedProfileSerializer
    permission_classes = [IsAuthenticated, HasBackofficeRole(roles=['ADMIN'])]

    def _degrada_altres_default(self, instance_pk=None):
        qs = SeedProfile.objects.filter(is_default_free=True)
        if instance_pk is not None:
            qs = qs.exclude(pk=instance_pk)
        qs.update(is_default_free=False)

    def perform_create(self, serializer):
        with transaction.atomic():
            if serializer.validated_data.get('is_default_free'):
                self._degrada_altres_default()
            serializer.save()

    def perform_update(self, serializer):
        with transaction.atomic():
            if serializer.validated_data.get('is_default_free'):
                self._degrada_altres_default(instance_pk=serializer.instance.pk)
            serializer.save()

    @action(detail=False, methods=['get'], url_path='blocs-meta')
    def blocs_meta(self, request):
        """Metadades dels blocs de sembra: etiqueta, dependències i comptadors reals
        de fhort (per pintar l'editor de seleccions amb el cost de cada casella)."""
        from fhort.tasks.management.commands.bootstrap_tenant import seed_block_counts

        counts = seed_block_counts('fhort')
        blocs = [
            {
                'key': key,
                'label': label,
                'deps': counts.get(key, {}).get('deps', []),
                'total': counts.get(key, {}).get('total', 0),
                'models': counts.get(key, {}).get('models', {}),
            }
            for key, label in SeedProfile.Bloc.choices
        ]
        return Response({'blocs': blocs})
