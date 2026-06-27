"""Models del sistema de documents .ftt (tenant).

DocumentTemplate és el magatzem de plantilles de document .ftt del tenant: moltes
plantilles reutilitzables (a diferència de TechSheetTemplate, O2O amb Customer, 1 per
client). Substitueix TechSheetTemplate, que queda deprecat i es retirarà a la neteja final.
"""
from django.db import models


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
