"""Mòdul Comercial Studio — mestre d'articles (bloc B1).

Model fundacional del pipeline comercial tenant→tercer (oferta→comanda→encàrrec→albarà→
liquidació). AQUEST bloc només construeix el MESTRE (articles + satèl·lits); els documents
(Quote/SalesOrder/WorkOrder/Expense/DeliveryNote/Settlement) i el gate de tier arriben a B2-B5.

Lleis heretades (DECISIONS.md · DISSENY_MODUL_COMERCIAL.md):
- Naming BD/codi en ANGLÈS; català només a UI (i18n) i documents.
- Referència a tasques per CODE (task_code), mai per PK.
- El sistema PROPOSA el preu (cost/Welford × tarifa + markup); l'humà FIXA a la línia (B2+).
- Additiu: cap camp d'aquest mòdul toca el nucli tècnic (mesures/grading/fitting/tasques).
"""
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import models

_CENT = Decimal('0.01')

# Fonaments dels documents comercials (B2+): abstractes + comptador de numeració.
# DocumentSequence s'importa aquí perquè Django el registri sota l'app commerce.
from .models_base import AbstractDocument, AbstractDocumentLine, DocumentSequence  # noqa: F401


class Unit(models.Model):
    """Unitat de venda/mesura comercial (peça, hora, enviament, joc, metre, kg).

    Taula petita (no enum) perquè el tenant en pugui afegir. NO confondre amb
    `accounts.TenantConfig.unitat_mesura` (cm/inch), que és la unitat MÈTRICA de les
    mesures POM — una altra cosa. Aquí es parla d'unitats de facturació/quantitat.
    """
    code = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=100, help_text="Nom canònic EN; display i18n a la UI.")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Unit'
        verbose_name_plural = 'Units'

    def __str__(self):
        return self.code


class Product(models.Model):
    """Article comercial del catàleg del tenant: servei intern/extern, mercaderia o pack.

    ⚠️ NO confondre amb `tasks.Production` (confecció externa d'una peça): homofonia visual,
    conceptes diferents. Product = línia de catàleg vendible; Production = encàrrec de taller.

    `nature` decideix com es costeja i què genera en executar-se (B3+):
      - INTERNAL_SERVICE → cost = Σ cascada(task_code, GTI) × TenantConfig.hourly_rate; genera tasques.
      - EXTERNAL_SERVICE → cost = preu de compra al proveïdor (ProductSupplier); genera Expense.
      - GOODS           → mercaderia; cost = preu de compra; genera Expense.
      - PACK            → composició de components (ProductComponent), un sol nivell.

    `price_mode` decideix com es proposa el preu de VENDA:
      - FIXED      → base_price per unitat.
      - TIME_BASED → temps estimat (cascada Welford del GTI) × `sale_rate` + markup_pct.
    `sale_rate` (tarifa de VENDA per minut) viu AQUÍ, no a TenantConfig: és preu, no cost.
    `TenantConfig.hourly_rate` és el COST intern (tarifa plana v1); són eixos separats (decisió #3).
    """
    NATURE_CHOICES = [
        ('INTERNAL_SERVICE', 'Internal service'),
        ('EXTERNAL_SERVICE', 'External service'),
        ('GOODS', 'Goods'),
        ('PACK', 'Pack'),
    ]
    PRICE_MODE_CHOICES = [
        ('FIXED', 'Fixed'),
        ('TIME_BASED', 'Time based'),
    ]
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=200, help_text="Nom canònic EN; display i18n a la UI.")
    nature = models.CharField(max_length=20, choices=NATURE_CHOICES)
    price_mode = models.CharField(max_length=20, choices=PRICE_MODE_CHOICES, default='FIXED')
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                     help_text="Preu de venda per unitat (FIXED).")
    sale_rate = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True,
                                    help_text="Tarifa de VENDA per minut (TIME_BASED). ≠ cost intern.")
    markup_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0,
                                     help_text="% de marge sobre el cost (externs/goods i TIME_BASED).")
    # Comercial Studio (B3a) — classificador de grup de base impositiva. NO s'usa per calcular
    # línia a línia: agrupa les línies per tipus i l'IVA es calcula sobre la base agregada.
    tax_rate = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal('21.00'),
                                   help_text="Tipus d'IVA de l'article (classificador de grup).")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True,
                             related_name='products')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f'{self.code} · {self.name}'


class ProductRecipe(models.Model):
    """Recepta d'un servei intern: task_codes esperats amb quantitat.

    Referència a la tasca per CODE (mai FK a TaskType.pk — el catàleg és canònic i el
    sistema s'hi ancora per code). És el contracte contra el qual es computen extres i
    regularitzacions a l'entrega (B4). Només té sentit per a Product.nature=INTERNAL_SERVICE.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='recipe_lines')
    task_code = models.SlugField(max_length=50, help_text="Referència a TaskType.code (mai PK).")
    qty = models.DecimalField(max_digits=6, decimal_places=2, default=1,
                              help_text="Quantitat esperada d'aquesta tasca a la recepta.")

    class Meta:
        ordering = ['product', 'task_code']
        unique_together = [('product', 'task_code')]
        verbose_name = 'Product recipe line'
        verbose_name_plural = 'Product recipe lines'

    def clean(self):
        if self.product_id and self.product.nature != 'INTERNAL_SERVICE':
            raise ValidationError("La recepta només s'aplica a serveis interns (INTERNAL_SERVICE).")

    def __str__(self):
        return f'{self.product_id}: {self.task_code} ×{self.qty}'


class ProductSupplier(models.Model):
    """Relació N:M article↔proveïdor amb preu de cost propi (multi-proveïdor).

    Un article extern/goods pot tenir diversos proveïdors amb preus diferents; a la línia
    (B3) es tria proveïdor (default: `is_default`, o el més barat) i el marge es calcula
    contra el seu cost. FK al catàleg `tasks.Supplier` EXISTENT (no es duplica).
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='suppliers')
    supplier = models.ForeignKey('tasks.Supplier', on_delete=models.PROTECT,
                                 related_name='product_offers')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2,
                                     help_text="Preu de compra d'aquest proveïdor per a l'article.")
    is_default = models.BooleanField(default=False,
                                     help_text="Proveïdor triat per defecte a la línia.")

    class Meta:
        ordering = ['product', '-is_default', 'cost_price']
        unique_together = [('product', 'supplier')]
        verbose_name = 'Product supplier'
        verbose_name_plural = 'Product suppliers'

    def __str__(self):
        return f'{self.product_id} ← {self.supplier_id} ({self.cost_price})'


class ProductComponent(models.Model):
    """Composició d'un PACK: un component és un altre Product. UN SOL NIVELL.

    Guard: `pack` ha de ser nature=PACK i `component` NO pot ser PACK (packs de packs = NO v1).
    """
    pack = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='components')
    component = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='in_packs')
    qty = models.DecimalField(max_digits=6, decimal_places=2, default=1)

    class Meta:
        ordering = ['pack', 'component']
        unique_together = [('pack', 'component')]
        verbose_name = 'Product component'
        verbose_name_plural = 'Product components'

    def clean(self):
        if self.pack_id and self.pack.nature != 'PACK':
            raise ValidationError("El contenidor d'un component ha de ser un PACK.")
        if self.component_id and self.component.nature == 'PACK':
            raise ValidationError("Un PACK no pot contenir un altre PACK (un sol nivell).")
        if self.pack_id and self.component_id and self.pack_id == self.component_id:
            raise ValidationError("Un pack no pot contenir-se a si mateix.")

    def __str__(self):
        return f'{self.pack_id} ⊃ {self.component_id} ×{self.qty}'


class ProductPriceGTI(models.Model):
    """Preu d'EXCEPCIÓ d'un article per a un GarmentTypeItem concret.

    ⚠️ NO és una graella densa per a "tots els GTI": és una taula d'EXCEPCIONS. Cada tenant
    crea els GTI que vulgui; aquí NOMÉS hi ha les files que calen. Rellevant per a:
      (a) nature=FIXED sense cascada de temps (preu concret per tipus de peça), o
      (b) correcció manual puntual sobre un preu TIME_BASED derivat.
    Si no hi ha fila per a un (product, GTI), mana el preu derivat de price_mode/sale_rate.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_exceptions')
    garment_type_item = models.ForeignKey('tasks.GarmentTypeItem', on_delete=models.CASCADE,
                                          related_name='product_price_exceptions')
    price = models.DecimalField(max_digits=10, decimal_places=2,
                                help_text="Preu de venda per a aquest article en aquest GTI.")

    class Meta:
        ordering = ['product', 'garment_type_item']
        unique_together = [('product', 'garment_type_item')]
        verbose_name = 'Product price exception (GTI)'
        verbose_name_plural = 'Product price exceptions (GTI)'

    def __str__(self):
        return f'{self.product_id} @ GTI{self.garment_type_item_id} = {self.price}'


# ═══════════════════════════════════════════════════════════════════════════════════════
# DOCUMENTS COMERCIALS — Quote (oferta), B2. Primera subclasse de les abstractes (P1).
# ═══════════════════════════════════════════════════════════════════════════════════════

class Quote(AbstractDocument):
    """Oferta comercial tenant→client. L'abstracta ja cobreix el 100% del cas Quote a B2.

    El `document_number` (OF-YYYY-NNNN) es genera a save() la primera vegada. Els totals es
    recalculen automàticament (signal a QuoteLine → recalculate_totals). Les línies només són
    editables mentre status='DRAFT' (guard a QuoteLine), patró de segellat del repo
    (close_base/seal_model_grading).
    """
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Quote'
        verbose_name_plural = 'Quotes'

    def save(self, *args, **kwargs):
        # doc_type sempre 'quote' per a un Quote; numeració atòmica només al crear (número buit).
        if not self.doc_type:
            self.doc_type = 'quote'
        if not self.document_number:
            from .services import reserve_document_number
            self.document_number = reserve_document_number('quote')
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        """Persisteix els totals fiscals del càlcul compartit (compute_document_totals, S1a).

        El motor fiscal viu a commerce/services.py (un sol lloc de veritat per a tots els
        documents). Aquí només es persisteix i es regeneren els venciments materialitzats
        (depenen del total + issued_at + payment_terms).
        """
        from .services import compute_document_totals, generate_due_dates
        self.subtotal, self.tax_amount, self.total, self.tax_breakdown = compute_document_totals(
            self, self.lines.all())
        self.save(update_fields=['subtotal', 'tax_amount', 'total', 'tax_breakdown', 'updated_at'])
        generate_due_dates(self)

    def __str__(self):
        return self.document_number or f'Quote (esborrany #{self.pk})'


class QuoteLine(AbstractDocumentLine):
    """Línia d'una oferta. `unit_price` congelat en crear-la (còpia del preu del Product)."""
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='lines')

    class Meta:
        ordering = ['quote', 'position', 'id']
        verbose_name = 'Quote line'
        verbose_name_plural = 'Quote lines'

    def _assert_editable(self):
        if self.quote_id and self.quote.status != 'DRAFT':
            raise ValidationError(
                "No es poden modificar línies d'una oferta que no està en esborrany (DRAFT).")

    def save(self, *args, **kwargs):
        self._assert_editable()
        # Quantize a 2 decimals a cada pas (llei de càlcul B3a): cap valor viatja amb >2 decimals.
        self.line_total = (Decimal(self.quantity or 0) * Decimal(self.unit_price or 0)).quantize(
            _CENT, rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self._assert_editable()
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.quote_id}: {self.description or self.product_id} ×{self.quantity}'


# ═══════════════════════════════════════════════════════════════════════════════════════
# DOCUMENTS COMERCIALS — SalesOrder (comanda), B3b. Segona subclasse de les abstractes.
# ═══════════════════════════════════════════════════════════════════════════════════════

class SalesOrder(AbstractDocument):
    """Comanda de venda tenant→client. Neix EXCLUSIVAMENT de la conversió d'una oferta
    (convert_quote_to_order, S3); no es crea a mà. IRREVERSIBILITAT de disseny (decisió Agus,
    B3b): un cop creada, les línies MAI són editables en preu/quantitat (guard read-only al
    serializer). L'única mutació permesa és qty_allocated (imputació de cartera) i el `status`
    del header. L'única sortida és status=CANCELLED (que NO reobre l'oferta).

    `source_quote` és la traçabilitat cap a l'oferta origen; unique → una oferta genera com a
    molt UNA comanda (guard de doble conversió a nivell de BD). `status` propi OPEN/COMPLETED/
    CANCELLED (sobreescriu el de l'abstracta, que és el cicle DRAFT/SENT… de les ofertes).
    """
    SO_STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    source_quote = models.OneToOneField(Quote, on_delete=models.PROTECT, null=True, blank=True,
                                         related_name='sales_order',
                                         help_text="Oferta origen (traçabilitat). 1 oferta → 1 comanda (unique).")
    status = models.CharField(max_length=20, choices=SO_STATUS_CHOICES, default='OPEN')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Sales order'
        verbose_name_plural = 'Sales orders'

    def save(self, *args, **kwargs):
        if not self.doc_type:
            self.doc_type = 'sales_order'
        if not self.document_number:
            from .services import reserve_document_number
            self.document_number = reserve_document_number('sales_order')
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        """Persisteix els totals del càlcul fiscal compartit (compute_document_totals, S1a) i
        regenera els venciments. Idèntic a Quote: un sol motor fiscal per a tots els documents."""
        from .services import compute_document_totals, generate_due_dates
        self.subtotal, self.tax_amount, self.total, self.tax_breakdown = compute_document_totals(
            self, self.lines.all())
        self.save(update_fields=['subtotal', 'tax_amount', 'total', 'tax_breakdown', 'updated_at'])
        generate_due_dates(self)

    def __str__(self):
        return self.document_number or f'SalesOrder (esborrany #{self.pk})'


class SalesOrderLine(AbstractDocumentLine):
    """Línia d'una comanda. Neix CONGELADA de la conversió d'una oferta (còpia de valors, cap FK
    viva a preus). `unit_price`/`quantity` MAI editables per API (irreversibilitat, B3b); l'única
    mutació és `qty_allocated` (control de cartera: ordered vs allocated, imputat a B4)."""
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='lines')
    qty_allocated = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                        help_text="Quantitat imputada (≤ quantity). Control de cartera (B4).")

    class Meta:
        ordering = ['order', 'position', 'id']
        verbose_name = 'Sales order line'
        verbose_name_plural = 'Sales order lines'

    def save(self, *args, **kwargs):
        # Quantize a 2 decimals (llei B3a). Sense guard de segellat al model: la
        # irreversibilitat s'imposa a l'API (serializer read-only), no al clonatge intern.
        self.line_total = (Decimal(self.quantity or 0) * Decimal(self.unit_price or 0)).quantize(
            _CENT, rounding=ROUND_HALF_UP)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.order_id}: {self.description or self.product_id} ×{self.quantity}'


# ═══════════════════════════════════════════════════════════════════════════════════════
# CONDICIONS DE PAGAMENT (B3a) — condició reutilitzable + fraccions (venciments).
# ═══════════════════════════════════════════════════════════════════════════════════════

class PaymentTerms(models.Model):
    """Condició de pagament reutilitzable (p.ex. 50-50, 30D). Les fraccions viuen a `lines`.
    S'assigna per defecte al Customer i s'hi pot fer override per document (AbstractDocument)."""
    code = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=100, help_text="Nom canònic; display i18n a la UI.")
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Payment terms'
        verbose_name_plural = 'Payment terms'

    def __str__(self):
        return self.code


class PaymentTermLine(models.Model):
    """Fracció d'una condició de pagament: percentatge + desfasament en dies des de la data
    del document. La suma de percentatges de totes les fraccions d'un terms ha de ser 100.00."""
    terms = models.ForeignKey(PaymentTerms, on_delete=models.CASCADE, related_name='lines')
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    days_offset = models.PositiveIntegerField(default=0, help_text="Dies des de la data del document.")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['terms', 'position', 'id']
        verbose_name = 'Payment term line'
        verbose_name_plural = 'Payment term lines'

    def clean(self):
        # Invariant: Σ percentatges de les fraccions del terms = 100.00 (incloent-hi aquesta).
        if not self.terms_id:
            return
        others = self.terms.lines.exclude(pk=self.pk)
        total = sum((ln.percentage for ln in others), Decimal('0')) + (self.percentage or Decimal('0'))
        if total != Decimal('100.00'):
            raise ValidationError(
                f"La suma de percentatges de les fraccions ha de ser 100.00 (actual: {total}).")

    def __str__(self):
        return f'{self.terms_id}: {self.percentage}% @ +{self.days_offset}d'


class DocumentDueDate(models.Model):
    """Venciment materialitzat d'un document comercial (B3a/B3b). Pertany EXACTAMENT a un
    document: Quote (oferta) o SalesOrder (comanda). v1 SIMPLE: dues FK nullable + CHECK que
    exactament una és no-null (NO GenericFK, decisió B3b). Es regenera per generate_due_dates()
    des del payment_terms efectiu (document > customer).
    """
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='due_dates',
                              null=True, blank=True)
    sales_order = models.ForeignKey('commerce.SalesOrder', on_delete=models.CASCADE,
                                    related_name='due_dates', null=True, blank=True)
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(quote__isnull=False) & models.Q(sales_order__isnull=True)) |
                          (models.Q(quote__isnull=True) & models.Q(sales_order__isnull=False)),
                name='duedate_exactly_one_parent'),
        ]
        verbose_name = 'Document due date'
        verbose_name_plural = 'Document due dates'

    @property
    def document(self):
        return self.quote if self.quote_id else self.sales_order

    def __str__(self):
        return f'{self.document}: {self.amount} @ {self.due_date}'


# ═══════════════════════════════════════════════════════════════════════════════════════
# ENCÀRREC / ORDRE DE TREBALL (B4a) — contenidor d'execució, NO document emès al client.
# ═══════════════════════════════════════════════════════════════════════════════════════

class WorkOrder(models.Model):
    """Contenidor d'execució que agrupa les ModelTask d'un encàrrec (B4a). NO és un
    AbstractDocument: no s'emet al client, no porta línies/totals fiscals; l'albarà (B4c)
    en serà el document derivat. Dues menes:

    - ORDER: encàrrec real d'un model × line de comanda; congela `price_snapshot` i
      `recipe_snapshot` en crear-lo des de l'order_line (base contra què es marquen els
      extres off_recipe).
    - COLLECTOR: contenidor mensual lazy per (customer, period='YYYY-MM') que recull les
      tasques de models sense encàrrec. Sense model/order_line/recepta: al col·lector res
      és off_recipe (no hi ha recepta contra què comparar).

    El tancament (status OPEN→CLOSED) és el gate real (B4a P5); un WO CLOSED no accepta
    més tasques.
    """
    KIND_CHOICES = [
        ('ORDER', 'Order'),          # encàrrec d'un model concret
        ('COLLECTOR', 'Collector'),  # col·lector mensual per client
    ]
    ORIGIN_CHOICES = [
        ('MANUAL', 'Manual'),
        ('EXTERNAL_BUS', 'External bus'),  # federation-aware (disseny §7)
    ]
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
    ]
    number = models.CharField(
        max_length=30, unique=True, blank=True,
        help_text="Generat a save() (reserve_document_number 'work_order'). Mai editable.")
    customer = models.ForeignKey('tasks.Customer', on_delete=models.PROTECT,
                                 related_name='work_orders')
    model = models.ForeignKey('models_app.Model', on_delete=models.PROTECT,
                              null=True, blank=True, related_name='work_orders',
                              help_text="null = col·lector (no lligat a un model concret).")
    order_line = models.ForeignKey('commerce.SalesOrderLine', on_delete=models.PROTECT,
                                   null=True, blank=True, related_name='work_orders',
                                   help_text="Línia de comanda origen (nullable: encàrrec sense comanda / col·lector).")
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='ORDER')
    origin = models.CharField(max_length=20, choices=ORIGIN_CHOICES, default='MANUAL')
    period = models.CharField(max_length=7, blank=True,
                              help_text="'YYYY-MM' — només per COLLECTOR (mes de recollida).")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN')
    # Congelats en crear des d'order_line; buits al col·lector (no hi ha recepta a comparar).
    price_snapshot = models.JSONField(default=dict, blank=True)
    recipe_snapshot = models.JSONField(default=dict, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL,
                                  null=True, blank=True, related_name='work_orders_closed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.UserProfile', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='work_orders_created')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Work order'
        verbose_name_plural = 'Work orders'
        constraints = [
            # Un sol col·lector per (customer, mes).
            models.UniqueConstraint(
                fields=['customer', 'period'], condition=models.Q(kind='COLLECTOR'),
                name='uniq_collector_customer_period'),
            # El col·lector no pot anar lligat a model ni a línia de comanda.
            models.CheckConstraint(
                condition=~models.Q(kind='COLLECTOR') |
                          (models.Q(model__isnull=True) & models.Q(order_line__isnull=True)),
                name='collector_no_model_no_orderline'),
        ]

    def save(self, *args, **kwargs):
        if not self.number:
            from .services import reserve_document_number
            self.number = reserve_document_number('work_order')
        super().save(*args, **kwargs)

    def __str__(self):
        tag = self.period if self.kind == 'COLLECTOR' else (self.model_id or '—')
        return f'{self.number or "WO?"} [{self.kind}] {tag}'
