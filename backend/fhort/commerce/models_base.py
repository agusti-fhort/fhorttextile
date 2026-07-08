"""Fonaments dels documents comercials (B2+).

=== ABSTRACTES: primera i única excepció al patró de duplicació del repo ===
Decisió de l'Agus (R3, docs/diagnosis/DIAGNOSI_COMERCIAL_B2_2026-07-07.md): la família de
documents comercials —Quote (B2) · SalesOrder/WorkOrder/DeliveryNote/Settlement (B3-B5)—
comparteix capçalera i línia gairebé idèntiques. És l'ÚNIC lloc del repo on una base
abstracta es paga sola. ÚS EXCLUSIU dins commerce/: no toca cap altra app ni el nucli tècnic.

Lleis heretades (B1): naming BD/codi en ANGLÈS; timestamps `created_at`/`updated_at` (NO la
variant catalana — evita la inconsistència ca/en detectada a R4 del diagnòstic).
"""
from django.db import models


class AbstractDocument(models.Model):
    """Capçalera comuna de tot document comercial tenant→tercer.

    `doc_type` queda preparat perquè B3-B5 (SalesOrder/WorkOrder/DeliveryNote/Settlement)
    l'usin sense migració d'estructura nova; avui Quote és l'únic tipus real.
    `document_number` es genera a save() de la subclasse (reserve_document_number), MAI
    editable per l'usuari. Els imports monetaris (subtotal/tax_amount/total) són calculats
    (recalculate_totals), no s'editen directament excepte tax_amount (camp manual, sense
    motor fiscal a B2).
    """
    DOC_TYPE_CHOICES = [
        ('quote', 'Quote'),
        # TODO B3-B5: ('sales_order','Sales order'), ('work_order','Work order'),
        #             ('delivery_note','Delivery note'), ('settlement','Settlement')
    ]
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('SENT', 'Sent'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('EXPIRED', 'Expired'),
    ]
    document_number = models.CharField(
        max_length=30, unique=True, blank=True,
        help_text="Generat a save() (reserve_document_number). Mai editable per l'usuari.")
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    customer = models.ForeignKey('tasks.Customer', on_delete=models.PROTECT,
                                 related_name='%(class)ss')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    issued_at = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    # Comercial Studio (B3a) — override de condició de pagament per document. Si null, s'usa la
    # del customer; si també null, cap venciment. Entra a cada subclasse concreta per migració.
    payment_terms = models.ForeignKey('commerce.PaymentTerms', on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='%(class)s_documents')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                     help_text="IVA calculat sobre bases agregades (B3a). No editable.")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Comercial Studio (B3a) — desglossament fiscal per tipus: [{rate, base, tax}]. El llegeixen
    # PDF i frontend sense recalcular. Calculat per recalculate_totals(); no editable.
    tax_breakdown = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='%(class)s_created')

    class Meta:
        abstract = True


class AbstractDocumentLine(models.Model):
    """Línia comuna de tot document comercial.

    `unit_price` és una CÒPIA CONGELADA del preu del Product en el moment de crear la línia
    (mai FK viva al preu): si el preu del Product canvia demà, els documents ja emesos no han
    de canviar. `line_total` es guarda (no és property) per coherència amb els totals persistits
    de la capçalera.
    """
    product = models.ForeignKey('commerce.Product', on_delete=models.PROTECT,
                                related_name='%(class)ss')
    description = models.CharField(max_length=300, blank=True,
                                   help_text="Override lliure del name del Product a la línia.")
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                     help_text="Preu congelat en crear la línia (còpia, no FK viva).")
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                     help_text="quantity × unit_price, guardat.")
    position = models.PositiveIntegerField(default=0, help_text="Ordre manual dins el document.")

    class Meta:
        abstract = True


class DocumentSequence(models.Model):
    """Comptador atòmic de número de document per (doc_type, any). Reinici anual (R5).

    Anàleg de models_app.ModelSequence però escopat per (tipus de document, any) en lloc de
    (customer, any, temporada). El consumeix reserve_document_number() (commerce/services.py)
    amb select_for_update — concurrency-safe, per-schema sota django-tenants.
    """
    doc_type = models.CharField(max_length=20)
    year = models.PositiveIntegerField()
    last_seq = models.PositiveIntegerField(default=0, help_text="Últim número reservat.")

    class Meta:
        unique_together = [('doc_type', 'year')]
        verbose_name = 'Document sequence'
        verbose_name_plural = 'Document sequences'

    def __str__(self):
        return f'{self.doc_type} {self.year} → {self.last_seq}'
