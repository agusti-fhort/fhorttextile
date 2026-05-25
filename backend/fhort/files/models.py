from django.db import models


# Els fitxers físics viuen a /var/www/fhort-textile/storage/{schema_tenant}/{model_codi}/{versio}/
class FitxerVersio(models.Model):
    CATEGORIA_CHOICES = [
        ('patro', 'Patró'),
        ('disseny', 'Disseny'),
        ('fitting', 'Fitting'),
        ('document', 'Document'),
        ('ia_output', 'Sortida IA'),
    ]
    ORIGEN_CHOICES = [
        ('upload', 'Pujada manual'),
        ('ia_escalat', 'IA · escalat'),
        ('ia_marcada', 'IA · marcatge'),
        ('ia_ocr', 'IA · OCR'),
    ]

    model = models.ForeignKey(
        'models_app.Model',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='fitxer_versions',
    )
    nom_original = models.CharField(max_length=255)
    nom_intern = models.CharField(max_length=255)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    versio = models.PositiveIntegerField()
    versio_anterior = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='versions_posteriors',
    )

    path_relatiu = models.CharField(max_length=500)
    mida_bytes = models.BigIntegerField()
    mimetype = models.CharField(max_length=100)
    checksum = models.CharField(max_length=64)

    origen = models.CharField(max_length=30, choices=ORIGEN_CHOICES, default='upload')
    prompt_ia = models.TextField(null=True, blank=True)
    model_ia = models.CharField(max_length=100, null=True, blank=True)

    pujat_per = models.ForeignKey(
        'accounts.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fitxer_versions_pujats',
    )
    data_creacio = models.DateTimeField(auto_now_add=True)
    accessible_portal = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = 'Versió de fitxer'
        verbose_name_plural = 'Versions de fitxer'
        ordering = ['-data_creacio']

    def __str__(self):
        return f'{self.nom_original} v{self.versio}'
