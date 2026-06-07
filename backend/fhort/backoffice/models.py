# Sprint 1 — Capa 9: Usuaris i permisos del backoffice.
# El backoffice viu NOMÉS al schema public (SHARED_APPS). Aquests models són la
# RBAC pròpia del backoffice (separada dels usuaris de tenant) i el log d'accions
# del personal FHORT. Mai referencien models de tenant.
from django.conf import settings
from django.db import models


class BackofficeUser(models.Model):
    """Perfil de backoffice associat a un auth.User del schema public.

    L'auth.User custodia credencials/identitat; aquest model hi afegeix el rol
    de negoci i l'estat d'accés al backoffice. La separació manté la RBAC del
    backoffice independent dels flags de Django (is_staff/is_superuser).
    """

    class Rol(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        COMERCIAL = 'COMERCIAL', 'Comercial'
        FACTURACIO = 'FACTURACIO', 'Facturació'
        SUPORT = 'SUPORT', 'Suport'

    usuari = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='backoffice_profile',
    )
    rol = models.CharField(max_length=20, choices=Rol.choices)
    actiu = models.BooleanField(default=True)
    data_alta = models.DateField(auto_now_add=True)
    ultim_acces = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.usuari.email} ({self.rol})'


class BackofficeActionLog(models.Model):
    """Auditoria de les accions del personal FHORT al backoffice (Capa 8).

    Es conserva encara que l'usuari es doni de baixa (SET_NULL) per no perdre la
    traça. `detall` guarda context lliure (JSON) sense dades sensibles de tenant.
    """

    usuari = models.ForeignKey(
        BackofficeUser,
        on_delete=models.SET_NULL,
        null=True,
        related_name='accions',
    )
    accio = models.CharField(max_length=100)
    objecte_tipus = models.CharField(max_length=100, blank=True)
    objecte_id = models.CharField(max_length=100, blank=True)
    detall = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.accio} @ {self.timestamp:%Y-%m-%d %H:%M}'


class ModelConsumptionEvent(models.Model):
    """Sprint 4: esdeveniment de consum a PUBLIC. El que FHORT factura (recompte).
    Mínim absolut: cap codi ni nom de model. Referència fluixa per codi_client +
    opaque_ref (rep el MATEIX UUID que el ConsumptionRecord del tenant via senyal a 4.2).
    Total a facturar = COUNT() per {codi_client, period}."""
    codi_client = models.CharField(max_length=3)   # = Client.codi_tenant (ref fluixa)
    period = models.CharField(max_length=7)         # 'YYYY-MM'
    opaque_ref = models.UUIDField(unique=True)      # SENSE default: el valor ve del tenant
    merited_at = models.DateTimeField()

    class Meta:
        ordering = ['-merited_at']

    def __str__(self):
        return f'{self.codi_client} · {self.period} · {self.opaque_ref}'


class ServiceCatalog(models.Model):
    """Catàleg global de conceptes facturables (Sprint 5 · Capa 4).
    Sense preu — el preu viu al ContractLine de cada tenant.
    Tipus: tier_fee=quota base mensual, model_count=per model iniciat, manual=puntual."""
    TIPUS_CHOICES = [
        ('tier_fee',    'Quota base tier'),
        ('model_count', 'Per model iniciat'),
        ('manual',      'Manual (setup/formació)'),
    ]
    code        = models.CharField(max_length=50, unique=True)
    nom         = models.CharField(max_length=200)
    descripcio  = models.TextField(blank=True, default='')
    tipus       = models.CharField(max_length=20, choices=TIPUS_CHOICES)
    actiu       = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tipus', 'code']

    def __str__(self):
        return f'{self.code} · {self.nom}'


class TenantContract(models.Model):
    """Contracte SaaS entre FHORT i un tenant (Sprint 5 · Capa 4).
    Múltiples contractes possibles per tenant (historial). El vigent és
    actiu=True i data_fi=null o futura. El motor de facturació (Sprint 6)
    llegirà les ContractLine, no el Plan.preu_model_extra."""
    client      = models.ForeignKey(
        'tenants.Client', on_delete=models.PROTECT, related_name='contracts'
    )
    data_inici  = models.DateField()
    data_fi     = models.DateField(null=True, blank=True)
    actiu       = models.BooleanField(default=True)
    nota        = models.TextField(blank=True, default='')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_inici']

    def __str__(self):
        return f'{self.client.codi_tenant} · {self.data_inici}'


class ContractLine(models.Model):
    """Línia de servei dins un TenantContract (Sprint 5 · Capa 4).
    preu = el que realment es cobra a aquest tenant (pot diferir del Plan).
    inclosos = franquícia gratuïta (rellevant per a model_count)."""
    contract    = models.ForeignKey(
        TenantContract, on_delete=models.CASCADE, related_name='lines'
    )
    service     = models.ForeignKey(
        ServiceCatalog, on_delete=models.PROTECT, related_name='lines'
    )
    preu        = models.DecimalField(max_digits=10, decimal_places=4)
    moneda      = models.CharField(max_length=3, default='EUR')
    inclosos    = models.IntegerField(default=0)
    actiu       = models.BooleanField(default=True)

    class Meta:
        ordering = ['service__tipus', 'service__code']
        unique_together = [('contract', 'service')]

    def __str__(self):
        return f'{self.contract} · {self.service.code} · {self.preu}'


class Invoice(models.Model):
    """Factura generada pel motor de facturació (Sprint 6 · Capa 4).
    tipus=auto: generada pel motor mensual (tier_fee + model_count).
    tipus=manual: creada per un humà (setup, formació, etc.).
    Idempotència: unique_together (client, period, tipus) per a auto.
    Sprint 7 mourà estat esborrany→emesa→pagada via Stripe."""
    TIPUS = [('auto', 'Automàtica'), ('manual', 'Manual')]
    ESTAT = [
        ('esborrany', 'Esborrany'),
        ('emesa',     'Emesa'),
        ('pagada',    'Pagada'),
        ('cancel·lada', 'Cancel·lada'),
    ]
    client     = models.ForeignKey(
        'tenants.Client', on_delete=models.PROTECT, related_name='invoices'
    )
    period     = models.CharField(max_length=7)          # 'YYYY-MM'
    tipus      = models.CharField(max_length=10, choices=TIPUS, default='auto')
    estat      = models.CharField(max_length=15, choices=ESTAT, default='esborrany')
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    moneda     = models.CharField(max_length=3, default='EUR')
    created_at = models.DateTimeField(auto_now_add=True)
    emesa_at   = models.DateTimeField(null=True, blank=True)
    nota       = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-period', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['client', 'period', 'tipus'],
                condition=models.Q(tipus='auto'),
                name='unique_auto_invoice_per_client_period',
            )
        ]

    def __str__(self):
        return f'{self.client.codi_tenant} · {self.period} · {self.tipus}'


class InvoiceLine(models.Model):
    """Línia d'una factura (Sprint 6 · Capa 4).
    service pot ser null per a línies manuals lliures sense servei del catàleg."""
    invoice    = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='lines'
    )
    service    = models.ForeignKey(
        ServiceCatalog, on_delete=models.PROTECT,
        null=True, blank=True, related_name='invoice_lines'
    )
    descripcio = models.CharField(max_length=200)
    quantitat  = models.DecimalField(max_digits=10, decimal_places=4)
    preu_unit  = models.DecimalField(max_digits=10, decimal_places=4)
    total      = models.DecimalField(max_digits=10, decimal_places=2)
    moneda     = models.CharField(max_length=3, default='EUR')

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.invoice} · {self.descripcio} · {self.total}'
