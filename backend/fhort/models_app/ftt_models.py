"""Models del sistema de documents .ftt (tenant).

DocumentTemplate és el magatzem de plantilles de document .ftt del tenant: moltes
plantilles reutilitzables (a diferència de TechSheetTemplate, O2O amb Customer, 1 per
client). Substitueix TechSheetTemplate, que queda deprecat i es retirarà a la neteja final.
"""
from django.conf import settings
from django.db import models


class FttDocumentLock(models.Model):
    """Lock cooperatiu sobre un document .ftt lògic.

    La identitat del document és l'ARREL de la cadena versio_anterior (la v1), que no
    canvia encara que el cap avanci de versió → el lock sobreviu als 'desa'. És cooperatiu
    (porta UX, no transaccional fort) amb caducitat (TTL) perquè una pestanya tancada sense
    unlock no bloquegi per sempre. NO toca ModelFitxer: taula dedicada.
    """

    document_root = models.OneToOneField(
        'models_app.ModelFitxer',
        on_delete=models.CASCADE,
        related_name='ftt_lock',
    )
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ftt_documents_locked',
    )
    locked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return 'lock(doc=%s, by=%s)' % (self.document_root_id, self.locked_by_id)


class DocumentTemplate(models.Model):
    """Plantilla de document .ftt reutilitzable, emmagatzemada al tenant."""

    ORIGEN_CHOICES = [
        ('sistema', 'Mostra del sistema'),
        ('tenant', 'Creada al tenant'),
    ]

    nom = models.CharField(max_length=120)
    descripcio = models.TextField(blank=True, default='')
    # El .ftt plantilla (contenidor zip). Opcional fins que se'n puja el contingut.
    fitxer_template = models.FileField(
        upload_to='document_templates/%Y/%m/', null=True, blank=True
    )
    # Esquema dels camps de metadata que la plantilla espera (reference, supplier, ...).
    metadata_schema = models.JSONField(default=dict, blank=True)
    # Mostra precarregada del sistema vs plantilla pròpia del tenant.
    is_sample = models.BooleanField(default=False)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default='tenant')
    actiu = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nom']

    def __str__(self):
        return self.nom
