"""Fitxa tècnica editable (editor full-screen) — model d'estat + lock col·laboratiu.

Separat de models.py per aïllar el subsistema de l'editor de fitxa. S'importa des de
models_app/models.py (al final) perquè Django el descobreixi dins l'app `models_app`;
l'app_label s'infereix del paquet contenidor, així les migracions van a models_app/.

No confondre amb tech_sheet_views.py (Sprint S17), que és l'extracció IA d'una fitxa
PDF → JSON per CREAR un Model. Això és l'editor persistent de la fitxa d'un Model ja existent.
"""
from django.conf import settings
from django.db import models


class TechSheet(models.Model):
    ESTAT_CHOICES = [
        ('obert', 'Obert'),
        ('tancat', 'Tancat'),
    ]

    model = models.OneToOneField(
        'models_app.Model',
        on_delete=models.CASCADE,
        related_name='tech_sheet',
    )
    estat = models.CharField(max_length=10, choices=ESTAT_CHOICES, default='obert')
    versio = models.PositiveIntegerField(default=1)
    template_json = models.JSONField(default=dict, blank=True)

    # Lock col·laboratiu: qui té la fitxa oberta ara (edició exclusiva).
    locked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tech_sheets_locked',
    )
    locked_at = models.DateTimeField(null=True, blank=True)

    # Últim que va desar (auditoria lleugera).
    last_editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tech_sheets_edited',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Fitxa tècnica'
        verbose_name_plural = 'Fitxes tècniques'

    def __str__(self):
        return f'TechSheet<{self.model_id}> [{self.estat}] v{self.versio}'


class TechSheetTemplate(models.Model):
    """Plantilla de fitxa tècnica per Customer (TS-3). Una per client; la del Customer
    is_self=True actua com a default del tenant. S'aplica en crear la TechSheet d'un model
    (copia template_json). Mateix format v2 (clau `pages`) que TechSheet — opac per al backend."""
    customer = models.OneToOneField(
        'tasks.Customer',
        on_delete=models.CASCADE,
        related_name='tech_sheet_template',
    )
    nom = models.CharField(max_length=120, blank=True, default='')
    template_json = models.JSONField(default=dict, blank=True)
    actiu = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tech sheet template'
        verbose_name_plural = 'Tech sheet templates'

    def __str__(self):
        return f'Template {self.customer.codi}'
