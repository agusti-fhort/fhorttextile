"""Plantilla de fitxa per Customer (TechSheetTemplate).

NOTA (Fase 2 .ftt): el model TechSheet (fitxa per-model, O2O) s'ha jubilat — el document
editable viu ara com a ModelFitxer tipus TECHSHEET (.ftt). Queda només la plantilla per
Customer, fins al seu cutover propi a DocumentTemplate.

Separat de models.py per aïllar el subsistema; s'importa des de models_app/models.py (al
final) perquè Django el descobreixi dins l'app `models_app`.
"""
from django.db import models


class TechSheetTemplate(models.Model):
    """DEPRECAT (Fase 1 .ftt) — substituït per models_app.ftt_models.DocumentTemplate
    (magatzem de moltes plantilles del tenant). Es manté mentre el flux TechSheet (O2O)
    encara hi llegeix; la retirada neta arriba a la jubilació final (B8). 0 files a BD.

    Plantilla de fitxa tècnica per Customer (TS-3). Una per client; la del Customer
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
