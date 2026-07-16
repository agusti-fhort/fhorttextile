# F4 P-LEGAL — endpoints legals (backoffice, ADMIN) sota api/backoffice/v1/legal/.
# CRUD de documents/versions DRAFT + publish + pending/accept/acceptances. La vista
# d'acceptació del TENANT (P3) viu a views_legal_tenant i reusa legal_service.
from django.db.models import Max
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.tenants.models import Client

from .legal_service import pending_versions_for_client, record_acceptance
from .models import BackofficeActionLog, LegalDocument, LegalDocumentVersion, LegalAcceptance
from .serializers_legal import (
    LegalAcceptanceSerializer, LegalDocumentSerializer, LegalDocumentVersionSerializer,
)
from .views import HasBackofficeRole

ADMIN = [IsAuthenticated, HasBackofficeRole(roles=['ADMIN'])]


class LegalDocumentViewSet(viewsets.ModelViewSet):
    """CRUD de documents legals. Només ADMIN."""
    queryset = LegalDocument.objects.prefetch_related('versions').all()
    serializer_class = LegalDocumentSerializer
    permission_classes = ADMIN


class LegalDocumentVersionViewSet(viewsets.ModelViewSet):
    """CRUD de versions DRAFT + publish. Només ADMIN. No hi ha esborrat de PUBLICADES."""
    queryset = LegalDocumentVersion.objects.select_related('document').all()
    serializer_class = LegalDocumentVersionSerializer
    permission_classes = ADMIN
    filterset_fields = ['document', 'estat']

    def perform_create(self, serializer):
        # numero_versio l'assigna el servidor: següent lliure del document.
        doc = serializer.validated_data['document']
        ult = doc.versions.aggregate(m=Max('numero_versio'))['m'] or 0
        serializer.save(numero_versio=ult + 1)

    def destroy(self, request, *args, **kwargs):
        # Cap esborrat sobre PUBLICADES (immutabilitat probatòria).
        obj = self.get_object()
        if obj.estat == LegalDocumentVersion.ESTAT_PUBLICADA:
            return Response({'detail': 'Una versió PUBLICADA no es pot esborrar.'},
                            status=status.HTTP_409_CONFLICT)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Congela la versió: normalitza, calcula sha256, marca PUBLICADA i segella data.
        Determinista i idempotent (re-publicar no recalcula res)."""
        versio = self.get_object()
        ja = versio.estat == LegalDocumentVersion.ESTAT_PUBLICADA
        versio.publica()
        if not ja:
            BackofficeActionLog.objects.create(
                usuari=getattr(request.user, 'backoffice_profile', None),
                accio='legal.publish', objecte_tipus='LegalDocumentVersion',
                objecte_id=str(versio.pk),
                detall={'document': versio.document.tipus, 'versio': versio.numero_versio,
                        'sha256': versio.sha256})
        return Response(LegalDocumentVersionSerializer(versio).data)


def _resol_client(request):
    """Client del query param ?client= (accepta pk o codi_tenant)."""
    ref = request.query_params.get('client') or request.data.get('client')
    if not ref:
        return None
    q = Client.objects.filter(codi_tenant=str(ref))
    if not q.exists() and str(ref).isdigit():
        q = Client.objects.filter(pk=int(ref))
    return q.first()


class LegalActionViewSet(viewsets.ViewSet):
    """pending / accept / acceptances (backoffice, ADMIN). Muntat amb as_view explícit
    a urls.py per donar rutes planes legal/pending|accept|acceptances/."""
    permission_classes = ADMIN

    def pending(self, request):
        client = _resol_client(request)
        if client is None:
            return Response({'detail': 'Paràmetre client (pk o codi_tenant) requerit.'},
                            status=status.HTTP_400_BAD_REQUEST)
        versions = pending_versions_for_client(client)
        return Response(LegalDocumentVersionSerializer(versions, many=True).data)

    def accept(self, request):
        client = _resol_client(request)
        versio_id = request.data.get('versio')
        if client is None or not versio_id:
            return Response({'detail': 'Cal client i versio.'},
                            status=status.HTTP_400_BAD_REQUEST)
        versio = LegalDocumentVersion.objects.filter(pk=versio_id).first()
        if versio is None:
            return Response({'detail': 'Versió no trobada.'}, status=status.HTTP_404_NOT_FOUND)
        accepted_by = request.data.get('accepted_by') or getattr(request.user, 'email', '')
        try:
            acc, created = record_acceptance(
                client, versio, accepted_by, request, LegalAcceptance.METODE_CHECKBOX)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LegalAcceptanceSerializer(acc).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def acceptances(self, request):
        client = _resol_client(request)
        qs = LegalAcceptance.objects.select_related('client', 'versio', 'versio__document')
        if client is not None:
            qs = qs.filter(client=client)
        return Response(LegalAcceptanceSerializer(qs, many=True).data)
