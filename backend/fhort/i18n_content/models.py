"""i18n_content — traduccions genèriques reutilitzables (patró híbrid).

Decisió d'arquitectura (Agus): el camp canònic EN viu a la taula ORIGINAL del model
(columna, sempre present, és el fallback); les traduccions addicionals (ca, es, fr, de…)
viuen en AQUESTA taula genèrica, escalable a N idiomes sense afegir columnes. NO mixin de
columnes fixes (no escala).

Viu en l'esquema de cada tenant (TENANT_APPS): tradueix objectes de tenant (Product,
PaymentTerms i futurs) via GenericForeignKey. El `content_type` apunta al django_content_type
del propi tenant (contenttypes és a TENANT_APPS → replicat per esquema).
"""
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TranslationManager(models.Manager):
    """Helper d'accés: llegir/escriure una traducció puntual sense tocar el GenericFK a mà."""

    def get_translation(self, obj, field, language):
        """Text traduït d'un camp per a un idioma, o None si no n'hi ha. El fallback a
        l'EN canònic de la fila el fa el CALLER (mixin/serializer), no aquest mètode."""
        ct = ContentType.objects.get_for_model(obj.__class__)
        row = (self.filter(content_type=ct, object_id=obj.pk, field=field, language=language)
               .only('text').first())
        return row.text if row else None

    def set_translation(self, obj, field, language, text):
        """Crea o actualitza la traducció d'un camp per a un idioma (update_or_create)."""
        ct = ContentType.objects.get_for_model(obj.__class__)
        return self.update_or_create(
            content_type=ct, object_id=obj.pk, field=field, language=language,
            defaults={'text': text},
        )


class Translation(models.Model):
    """Una traducció d'un camp d'un objecte a un idioma.

    Clau natural (content_type, object_id, field, language) única: com a molt una fila per
    (objecte · camp · idioma). L'EN NO es desa aquí (viu a la columna original); aquí només
    hi ha els idiomes addicionals.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    field = models.CharField(max_length=100, help_text="Nom del camp traduït (p.ex. 'name').")
    language = models.CharField(max_length=5, help_text="Codi ISO 639-1 (ca, es, fr, de…).")
    text = models.TextField(blank=True)

    objects = TranslationManager()

    class Meta:
        unique_together = ('content_type', 'object_id', 'field', 'language')
        indexes = [models.Index(fields=['content_type', 'object_id'])]
        verbose_name = 'Translation'
        verbose_name_plural = 'Translations'

    def __str__(self):
        return f'{self.content_type}#{self.object_id}.{self.field} [{self.language}]'


class TranslatableMixin(models.Model):
    """Barreja per als models amb camps traduïbles. El valor canònic (EN) viu a la columna
    del propi camp; `translated()` retorna la traducció d'un idioma o hi fa fallback.

    Els models concrets declaren `TRANSLATABLE_FIELDS = ('name', …)` perquè els serializers i
    la UI sàpiguen quins camps exposar. Abstracte: no afegeix cap columna nova al model.
    """
    TRANSLATABLE_FIELDS = ()

    class Meta:
        abstract = True

    def translated(self, field, language):
        """Traducció del camp per a l'idioma, o el valor canònic EN del camp si no n'hi ha."""
        canonical = getattr(self, field)
        if not language or language == 'en':
            return canonical
        text = Translation.objects.get_translation(self, field, language)
        return text if text else canonical
