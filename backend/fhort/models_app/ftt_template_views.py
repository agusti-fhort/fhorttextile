"""S4 — CRUD de DocumentTemplate (magatzem de plantilles .ftt del tenant).

fitxer_template és de només lectura aquí: el contingut es puja via el flux
"desar com a plantilla" (commit 3), no per POST/PATCH directe d'aquest CRUD.
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ModelViewSet

from .models import DocumentTemplate


class DocumentTemplateSerializer(ModelSerializer):
    class Meta:
        model = DocumentTemplate
        fields = [
            'id', 'nom', 'descripcio', 'fitxer_template', 'metadata_schema',
            'is_sample', 'origen', 'actiu', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'fitxer_template', 'is_sample', 'origen', 'created_by', 'created_at', 'updated_at',
        ]


class DocumentTemplateViewSet(ModelViewSet):
    queryset = DocumentTemplate.objects.all()
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # El chooser de "nou document des de plantilla" (App.jsx → GET list) només ha de
        # veure plantilles ACTIVES: així una plantilla retirada (actiu=False, p.ex. la
        # "Capçalera LOSAN" substituïda per "Template FTT" a S12) surt de la llista sense
        # esborrar-ne les dades. detail/update segueixen accedint a totes per id (gestió).
        qs = DocumentTemplate.objects.all()
        if self.action == 'list':
            qs = qs.filter(actiu=True)
        return qs

    def perform_create(self, serializer):
        # Plantilla creada des del tenant: created_by = usuari actual, origen = 'tenant'.
        serializer.save(created_by=self.request.user, origen='tenant')
