# Sprint 1 — Capa 9: Usuaris i permisos del backoffice.
# El backoffice viu NOMÉS al schema public (SHARED_APPS). Aquests models són la
# RBAC pròpia del backoffice (separada dels usuaris de tenant) i el log d'accions
# del personal FHORT. Mai referencien models de tenant.
import hashlib
from decimal import Decimal

from django.conf import settings
from django.db import models


def normalitza_legal(contingut):
    """Normalització canònica per al hash d'un document legal: UTF-8 + line endings
    LF. El hash es calcula SEMPRE sobre aquesta forma perquè sigui determinista i
    reproduïble (F4: re-publicar el mateix text en una versió nova dona el mateix hash)."""
    text = (contingut or '').replace('\r\n', '\n').replace('\r', '\n')
    return text


def sha256_legal(contingut):
    """SHA-256 hex del contingut normalitzat."""
    return hashlib.sha256(normalitza_legal(contingut).encode('utf-8')).hexdigest()


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
    # Federació v2 (P4) — ACTOR: el schema del tenant que va OBRIR la tasca (qui merita).
    # Additiu i informatiu: `codi_client` NO canvia de semàntica (segueix sent el customer del
    # model, dualitat P4-b de la diagnosi). L'actor pot no coincidir amb `codi_client` quan un
    # Studio treballa el model d'un altre. La facturació futura filtrarà per actor; els
    # consumidors d'avui (que filtren per codi_client) no es toquen. '' = actor desconegut.
    actor_schema = models.CharField(max_length=63, blank=True, default='')
    # F-RECUR — anti-doble-cobrament PER BD, no per disciplina. Un event facturat apunta a
    # la seva línia; un event apuntat no re-entra mai a cap generació (el motor filtra
    # invoice_line__isnull=True). SET_NULL: si s'esborra un DRAFT no emès, els seus events
    # tornen a ser facturables (el vincle es desfà, no es perd l'event).
    invoice_line = models.ForeignKey(
        'InvoiceLine', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consumption_events')
    # Capacitat (no decisió d'ara): un event exclòs no es factura mai. Per als orfes de
    # tenants morts i qualsevol event que l'operador vulgui arxivar.
    exclos = models.BooleanField(default=False)
    exclos_motiu = models.CharField(max_length=200, blank=True, default='')

    class Meta:
        ordering = ['-merited_at']

    def __str__(self):
        return f'{self.codi_client} · {self.period} · {self.opaque_ref}'


class InvoiceSerie(models.Model):
    """Sèrie de numeració de factures (F-FACT B1).

    Una sèrie és DADA, no una constant del codi: l'operador crea les que necessiti
    (automàtiques de plataforma, manuals de serveis, rectificatives...) i cada una
    porta el seu correlatiu independent. El codi no en sembra cap ni en coneix cap:
    si algun dia calen tres sèries més, es creen per la UI, no per un deploy.

    `format` és una plantilla amb claus anomenades. Disponibles:
      {codi}  codi de la sèrie          {any}   any a 4 xifres (2026)
      {any2}  any a 2 xifres (26)       {num}   correlatiu (accepta format spec)
    Exemples: '{codi}-{any}-{num:04d}' → 'FT-2026-0001'
              '{codi}{any2}-{num:06d}' → 'APP26-000001'

    `reinici_anual`: el correlatiu torna a 1 en canviar d'any (norma habitual a ES).
    Amb False, el comptador no es reinicia mai i {any} és només decoratiu.
    """
    codi          = models.CharField(max_length=10, unique=True)
    nom           = models.CharField(max_length=100)
    format        = models.CharField(
        max_length=60, default='{codi}-{any}-{num:04d}',
        help_text="Plantilla del número. Claus: {codi} {any} {any2} {num}.")
    reinici_anual = models.BooleanField(default=True)
    # Estat viu del correlatiu. NO s'edita a mà: el mou reserve_invoice_number().
    any_actual    = models.IntegerField(null=True, blank=True)
    comptador     = models.IntegerField(default=0)
    activa        = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['codi']
        verbose_name = 'Sèrie de factures'
        verbose_name_plural = 'Sèries de factures'

    def __str__(self):
        return f'{self.codi} · {self.nom}'

    def render(self, num, any_=None):
        """El número formatat per a `num`. Valida la plantilla; mai executa res de l'usuari."""
        any_ = any_ or (self.any_actual or 0)
        try:
            return self.format.format(
                codi=self.codi, any=any_, any2=any_ % 100, num=num,
            )
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(
                f"Format de sèrie invàlid ({self.format!r}): {e}. "
                f"Claus permeses: {{codi}} {{any}} {{any2}} {{num}}."
            )

    def exemple(self):
        """Mostra com quedaria el pròxim número (per a la UI). No reserva res."""
        from django.utils import timezone
        any_ = timezone.now().year
        seg = 1 if (self.reinici_anual and self.any_actual != any_) else self.comptador + 1
        try:
            return self.render(seg, any_)
        except ValueError as e:
            return f'⚠ {e}'


class VATRate(models.Model):
    """Tipus d'IVA aplicable (F-FACT B1).

    El percentatge i la menció legal són DADA, no literals al codi: un canvi de tipus
    o de redactat legal és una fila, no un deploy. `regim_default` lliga el tipus al
    règim del client (Client.regim_vat, que ja es deriva sol de país+VAT): en emetre,
    cada línia sense override agafa el tipus per defecte del règim del client.
    """
    codi           = models.CharField(max_length=20, unique=True)
    nom            = models.CharField(max_length=100)
    percentatge    = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0.00'),
        help_text='0 per als règims exempts o d\'inversió del subjecte passiu.')
    # Si té valor, aquest és el tipus per DEFECTE del règim (un de sol per règim).
    regim_default  = models.CharField(max_length=30, blank=True, default='')
    mencio_legal   = models.TextField(
        blank=True, default='',
        help_text="Text obligatori al PDF (p.ex. inversió del subjecte passiu, exempció).")
    actiu          = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-percentatge', 'codi']
        verbose_name = "Tipus d'IVA"
        verbose_name_plural = "Tipus d'IVA"
        constraints = [
            # Un sol tipus per defecte per règim. Parcial: els que no en tenen (blank)
            # no competeixen entre ells.
            models.UniqueConstraint(
                fields=['regim_default'],
                condition=~models.Q(regim_default=''),
                name='uniq_vat_default_per_regim',
            ),
        ]

    def __str__(self):
        return f'{self.codi} · {self.percentatge}%'


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
    # F-RECUR — periodicitat de la QUOTA. El consum (model_count) sempre és del període
    # que es factura; la quota, en canvi, pot ser mensual/trimestral/anual. Dada
    # configurable, mai un supòsit al codi. 'mensual' és el default de LOSAN i la resta.
    PERIODICITAT = [
        ('mensual', 'Mensual'),
        ('trimestral', 'Trimestral'),
        ('anual', 'Anual'),
    ]
    client      = models.ForeignKey(
        'tenants.Client', on_delete=models.PROTECT, related_name='contracts'
    )
    data_inici  = models.DateField()
    data_fi     = models.DateField(null=True, blank=True)
    periodicitat = models.CharField(max_length=12, choices=PERIODICITAT, default='mensual')
    actiu       = models.BooleanField(default=True)
    nota        = models.TextField(blank=True, default='')
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_inici']

    def quota_toca_al_periode(self, period):
        """La quota d'aquesta periodicitat es cobra al mes `period` ('YYYY-MM')?

        Àncora = el mes de `data_inici`. Mensual: sempre. Trimestral: cada 3 mesos des de
        l'inici. Anual: el mateix mes de l'inici. Així una quota trimestral iniciada al
        febrer toca al febrer/maig/agost/novembre, no en un trimestre natural arbitrari.
        """
        y, m = int(period[:4]), int(period[5:7])
        if self.periodicitat == 'mensual':
            return True
        delta = (y - self.data_inici.year) * 12 + (m - self.data_inici.month)
        if delta < 0:
            return False
        if self.periodicitat == 'trimestral':
            return delta % 3 == 0
        return delta % 12 == 0   # anual

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


class InvoiceQuerySet(models.QuerySet):
    """Bloqueja l'esborrat massiu si el conjunt conté cap factura ja emesa.
    QuerySet.delete() no passa per Model.delete(), així que el guard ha de viure
    també aquí (mateix motiu que NoDeleteQuerySet a F4-legal)."""
    def delete(self):
        if self.exclude(estat=Invoice.ESTAT_ESBORRANY).exists():
            raise ValueError(
                'Una factura emesa és immutable: no es pot esborrar. '
                'La correcció d\'una factura emesa és una RECTIFICATIVA.')
        return super().delete()


class Invoice(models.Model):
    """Factura generada pel motor de facturació (Sprint 6 · Capa 4; fiscal a F-FACT B1).
    tipus=auto: generada pel motor mensual (tier_fee + model_count).
    tipus=manual: creada per un humà (setup, formació, etc.).
    tipus=rectificativa: corregeix una factura EMESA (FK `rectifica`).
    Idempotència: unique_together (client, period, tipus) per a auto.

    CICLE DE VIDA (F-FACT B1): esborrany (editable, SENSE número) → emesa (congelada,
    amb número reservat de la sèrie). Una emesa no s'edita ni s'esborra: es rectifica.
    """
    ESTAT_ESBORRANY = 'esborrany'
    ESTAT_EMESA = 'emesa'
    ESTAT_PAGADA = 'pagada'
    ESTAT_CANCELADA = 'cancel·lada'
    TIPUS_AUTO = 'auto'
    TIPUS_MANUAL = 'manual'
    TIPUS_RECTIFICATIVA = 'rectificativa'
    TIPUS = [
        (TIPUS_AUTO, 'Automàtica'),
        (TIPUS_MANUAL, 'Manual'),
        (TIPUS_RECTIFICATIVA, 'Rectificativa'),
    ]
    ESTAT = [
        (ESTAT_ESBORRANY, 'Esborrany'),
        (ESTAT_EMESA,     'Emesa'),
        (ESTAT_PAGADA,    'Pagada'),
        (ESTAT_CANCELADA, 'Cancel·lada'),
    ]
    # Un cop la factura surt d'esborrany, aquests camps són el document fiscal i no
    # es toquen mai més. `estat` i `nota` en queden fora a posta: una emesa encara ha
    # de poder passar a pagada/cancel·lada i admetre una anotació interna.
    CAMPS_CONGELATS = (
        'client_id', 'period', 'tipus', 'serie_id', 'numero', 'num_seq',
        'base_imposable', 'quota_iva', 'total', 'moneda', 'emesa_at', 'rectifica_id',
    )

    client     = models.ForeignKey(
        'tenants.Client', on_delete=models.PROTECT, related_name='invoices'
    )
    period     = models.CharField(max_length=7)          # 'YYYY-MM'
    tipus      = models.CharField(max_length=15, choices=TIPUS, default=TIPUS_AUTO)
    estat      = models.CharField(max_length=15, choices=ESTAT, default=ESTAT_ESBORRANY)
    # Numeració (F-FACT B1). Buits en esborrany: el número es reserva EN EMETRE, mai
    # abans — un esborrany descartat no ha de foradar la sèrie.
    serie      = models.ForeignKey(
        InvoiceSerie, on_delete=models.PROTECT, null=True, blank=True,
        related_name='invoices')
    numero     = models.CharField(max_length=40, blank=True, default='')
    num_seq    = models.IntegerField(null=True, blank=True)   # correlatiu cru (auditoria)
    # Rectificativa: apunta a la factura EMESA que corregeix.
    rectifica  = models.ForeignKey(
        'self', on_delete=models.PROTECT, null=True, blank=True,
        related_name='rectificatives')
    # Fiscal. base_imposable + quota_iva = total (el que paga el client).
    base_imposable = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quota_iva      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    moneda     = models.CharField(max_length=3, default='EUR')
    created_at = models.DateTimeField(auto_now_add=True)
    emesa_at   = models.DateTimeField(null=True, blank=True)
    nota       = models.TextField(blank=True, default='')

    objects = InvoiceQuerySet.as_manager()

    class Meta:
        ordering = ['-period', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['client', 'period', 'tipus'],
                condition=models.Q(tipus='auto'),
                name='unique_auto_invoice_per_client_period',
            ),
            # El número és únic dins la seva sèrie. Guarda dura: la carrera que el
            # select_for_update ja evita, la BD la torna a barrar.
            models.UniqueConstraint(
                fields=['serie', 'numero'],
                condition=~models.Q(numero=''),
                name='uniq_numero_per_serie',
            ),
        ]

    def __str__(self):
        return f'{self.numero or "(esborrany)"} · {self.client.codi_tenant} · {self.tipus}'

    @property
    def emesa(self):
        return self.estat != self.ESTAT_ESBORRANY

    def save(self, *args, **kwargs):
        # IMMUTABILITAT (patró F4-legal, models.py:368-380): es llegeix l'estat REAL a
        # la BD, no el de la instància, que podria haver-se mutat en memòria.
        if self.pk:
            anterior = (type(self).objects.filter(pk=self.pk)
                        .only(*self.CAMPS_CONGELATS, 'estat').first())
            if anterior and anterior.estat != self.ESTAT_ESBORRANY:
                canviats = [c for c in self.CAMPS_CONGELATS
                            if getattr(anterior, c) != getattr(self, c)]
                if canviats:
                    raise ValueError(
                        f'Factura {anterior.numero or self.pk} està {anterior.estat} i és '
                        f'immutable: no es poden canviar {", ".join(canviats)}. '
                        f'La correcció d\'una factura emesa és una RECTIFICATIVA.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.estat != self.ESTAT_ESBORRANY:
            raise ValueError(
                f'Factura {self.numero or self.pk} està {self.estat} i és immutable: '
                f'no es pot esborrar. Emet-ne una RECTIFICATIVA.')
        return super().delete(*args, **kwargs)


class SeedProfile(models.Model):
    """Perfil de sembra (F3 · P-FREE-SEED). Decisió D-P4: en donar d'alta un tenant
    Free, se li sembra sol el catàleg; QUÈ se sembra ho defineix aquest perfil,
    gestionat des del backoffice — no el codi.

    FRONTERA: el backoffice és SHARED (public) i NO ha de conèixer el detall del
    catàleg d'un tenant. Per això `seleccio` guarda BLOCS (concepte de producte,
    p.ex. 'grading', 'garments'), no models ni registres concrets. El mapatge
    bloc→models de catàleg i el graf de dependències viuen a
    `tasks/management/commands/bootstrap_tenant.py` (SEED_BLOCKS/SEED_BLOCK_DEPS),
    l'únic lloc que sí depèn del catàleg.

    Granularitat = per blocs de tipus (decisió Agus A2): seleccionar un bloc
    arrossega les seves dependències (les resol el bootstrap, no aquesta taula).
    """

    class Bloc(models.TextChoices):
        # Claus canòniques dels blocs de sembra. L'etiqueta és de producte, no i18n
        # de UI (la UI tradueix per la clau). Han de coincidir amb SEED_BLOCKS a
        # bootstrap_tenant.py (validat per `bootstrap_tenant --check-blocks`).
        BASE = 'base', 'Catàlegs base'
        SIZE_SYSTEMS = 'size_systems', 'Sistemes de talles'
        GARMENTS = 'garments', 'Tipus de peça'
        POM_MASTERS = 'pom_masters', 'POMs i mapes'
        SIZING_PROFILES = 'sizing_profiles', 'Perfils de mesures'
        TIME_SEEDS = 'time_seeds', 'Llavors de temps'
        GRADING = 'grading', 'Escalat (grading)'

    nom = models.CharField(max_length=100, unique=True)
    descripcio = models.TextField(blank=True, default='')
    # {"blocks": ["base", "garments", ...]} — llista de claus de Bloc. El bootstrap
    # en calcula la clausura transitiva de dependències abans de sembrar.
    seleccio = models.JSONField(default=dict, blank=True)
    # Únic perfil marcat com a default del flux Free (el que dispara el hook d'alta).
    is_default_free = models.BooleanField(default=False)
    actiu = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nom']
        constraints = [
            # Com a molt un default-Free actiu: garanteix que el hook d'alta tingui
            # un únic perfil a disparar.
            models.UniqueConstraint(
                fields=['is_default_free'],
                condition=models.Q(is_default_free=True),
                name='unique_default_free_seed_profile',
            )
        ]

    def __str__(self):
        marca = ' [default-Free]' if self.is_default_free else ''
        return f'{self.nom}{marca}'

    @property
    def blocks(self):
        """Llista neta de claus de bloc seleccionades (tolerant a JSON incomplet)."""
        val = self.seleccio or {}
        return list(val.get('blocks', []) if isinstance(val, dict) else [])


class InvoiceLineQuerySet(models.QuerySet):
    """Les línies d'una factura emesa són part del document fiscal: no s'esborren."""
    def delete(self):
        if self.exclude(invoice__estat=Invoice.ESTAT_ESBORRANY).exists():
            raise ValueError(
                'No es poden esborrar línies d\'una factura emesa (immutable).')
        return super().delete()


class InvoiceLine(models.Model):
    """Línia d'una factura (Sprint 6 · Capa 4; fiscal a F-FACT B1).
    service pot ser null per a línies manuals lliures sense servei del catàleg.

    `total` = base imposable de la línia (quantitat × preu_unit), SENSE IVA — la
    semàntica que ja tenia i que el motor auto escriu. L'IVA viu als seus camps:
    `vat_rate` (override per línia; NULL = el del règim del client, resolt en emetre),
    i `pct_iva`/`quota_iva`, que són SNAPSHOT del moment d'emissió: si demà el tipus
    canvia de fila, la factura ja emesa segueix dient el que deia.
    """
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
    # IVA de la línia. vat_rate = override explícit; si és NULL, mana el règim del client.
    vat_rate   = models.ForeignKey(
        VATRate, on_delete=models.PROTECT, null=True, blank=True,
        related_name='invoice_lines')
    pct_iva    = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    quota_iva  = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    objects = InvoiceLineQuerySet.as_manager()

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.invoice} · {self.descripcio} · {self.total}'

    def save(self, *args, **kwargs):
        # Una línia no es pot afegir ni tocar si la factura ja no és esborrany.
        estat = (Invoice.objects.filter(pk=self.invoice_id)
                 .values_list('estat', flat=True).first())
        if estat and estat != Invoice.ESTAT_ESBORRANY:
            # L'emissió escriu pct_iva/quota_iva just ABANS de moure l'estat, així que
            # aquí ja no hi ha cap escriptura legítima possible.
            raise ValueError(
                f'La factura està {estat} i és immutable: no se\'n poden tocar les línies.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.invoice.estat != Invoice.ESTAT_ESBORRANY:
            raise ValueError(
                'No es poden esborrar línies d\'una factura emesa (immutable).')
        return super().delete(*args, **kwargs)


# ---------------------------------------------------------------------------
# F4 P-LEGAL — documents legals amb hash + acceptacions probatòries.
# Patró: BackofficeActionLog (append-only). Viuen a public (SHARED): el registre
# legal és de la plataforma, i LegalAcceptance referencia el Client (registre
# public de tenants), mai models de tenant-schema.
# ---------------------------------------------------------------------------
class NoDeleteQuerySet(models.QuerySet):
    """QuerySet que bloqueja l'esborrat massiu (QuerySet.delete() no passa per
    Model.delete(), així que cal aturar-lo aquí per garantir l'append-only a l'ORM)."""
    def delete(self):
        raise ValueError('Append-only: esborrat no permès en aquest model.')


class VersionQuerySet(models.QuerySet):
    """Bloqueja l'esborrat massiu si hi ha alguna versió PUBLICADA al conjunt."""
    def delete(self):
        if self.filter(estat=LegalDocumentVersion.ESTAT_PUBLICADA).exists():
            raise ValueError('No es pot esborrar una versió PUBLICADA (immutable).')
        return super().delete()


class LegalDocument(models.Model):
    """Un document legal de la plataforma (Termes, Privacitat, DPA, SLA...).
    El contingut viu a les VERSIONS; aquí només la identitat i el tipus."""

    TIPUS_TERMES = 'TERMES'
    TIPUS_PRIVACITAT = 'PRIVACITAT'
    TIPUS_DPA = 'DPA'
    TIPUS_SLA = 'SLA'
    TIPUS_CHOICES = [
        (TIPUS_TERMES, 'Termes i condicions'),
        (TIPUS_PRIVACITAT, 'Política de privacitat'),
        (TIPUS_DPA, 'Acord de tractament de dades (DPA)'),
        (TIPUS_SLA, 'Acord de nivell de servei (SLA)'),
    ]

    tipus = models.CharField(max_length=20, choices=TIPUS_CHOICES)
    nom = models.CharField(max_length=200)
    actiu = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tipus', 'nom']

    def __str__(self):
        return f'{self.tipus} · {self.nom}'


class LegalDocumentVersion(models.Model):
    """Una versió d'un document legal. DRAFT és editable; en PUBLICAR es calcula el
    sha256 sobre el contingut normalitzat i es CONGELA: cap canvi de contingut/hash
    a partir d'aquí (save-guard). Cap endpoint d'esborrat sobre publicades."""

    ESTAT_DRAFT = 'DRAFT'
    ESTAT_PUBLICADA = 'PUBLICADA'
    ESTAT_CHOICES = [(ESTAT_DRAFT, 'Esborrany'), (ESTAT_PUBLICADA, 'Publicada')]

    objects = VersionQuerySet.as_manager()

    document = models.ForeignKey(LegalDocument, on_delete=models.PROTECT,
                                 related_name='versions')
    numero_versio = models.PositiveIntegerField()
    contingut = models.TextField(blank=True, default='')
    sha256 = models.CharField(max_length=64, blank=True, default='')
    estat = models.CharField(max_length=10, choices=ESTAT_CHOICES, default=ESTAT_DRAFT)
    data_publicacio = models.DateTimeField(null=True, blank=True)
    requereix_reacceptacio = models.BooleanField(
        default=False,
        help_text='Si True, els clients que havien acceptat versions anteriors han de '
                  'reacceptar (apareix a pending/ i al gate del /me del tenant).')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['document', '-numero_versio']
        constraints = [
            models.UniqueConstraint(fields=['document', 'numero_versio'],
                                    name='unique_versio_per_document'),
        ]

    def __str__(self):
        return f'{self.document.tipus} v{self.numero_versio} [{self.estat}]'

    def save(self, *args, **kwargs):
        # IMMUTABILITAT: una versió PUBLICADA no pot canviar el contingut ni el hash.
        # Es llegeix l'estat REAL a la BD (no el de la instància, que podria haver-se
        # mutat en memòria) per decidir si el guard salta.
        if self.pk:
            anterior = type(self).objects.filter(pk=self.pk).only(
                'estat', 'contingut', 'sha256').first()
            if anterior and anterior.estat == self.ESTAT_PUBLICADA:
                if self.contingut != anterior.contingut or self.sha256 != anterior.sha256:
                    raise ValueError(
                        f'LegalDocumentVersion {self.pk} està PUBLICADA i és immutable: '
                        f'no es pot canviar contingut ni hash.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Una versió PUBLICADA és immutable: no s'esborra a cap capa.
        if self.estat == self.ESTAT_PUBLICADA:
            raise ValueError('Versió PUBLICADA immutable: no es pot esborrar.')
        return super().delete(*args, **kwargs)

    def publica(self):
        """Congela la versió: normalitza, calcula sha256, marca PUBLICADA i segella la
        data. Determinista: mateix contingut → mateix hash. Idempotent si ja publicada."""
        from django.utils import timezone
        if self.estat == self.ESTAT_PUBLICADA:
            return self
        self.contingut = normalitza_legal(self.contingut)
        self.sha256 = sha256_legal(self.contingut)
        self.estat = self.ESTAT_PUBLICADA
        self.data_publicacio = timezone.now()
        self.save()
        return self


class LegalAcceptance(models.Model):
    """Prova d'acceptació d'una versió legal per part d'un client (empresa). APPEND-ONLY:
    cap update ni delete a cap capa (save-guard aquí + cap endpoint). Idempotent per
    (client, versio): re-acceptar no duplica."""

    METODE_CHECKBOX = 'CHECKBOX'
    METODE_API = 'API'
    METODE_CHOICES = [(METODE_CHECKBOX, 'Checkbox UI'), (METODE_API, 'API')]

    objects = NoDeleteQuerySet.as_manager()

    client = models.ForeignKey('tenants.Client', on_delete=models.PROTECT,
                               related_name='legal_acceptances')
    versio = models.ForeignKey(LegalDocumentVersion, on_delete=models.PROTECT,
                               related_name='acceptances')
    accepted_by = models.CharField(max_length=254,
                                   help_text="Email/identificador de qui va clicar.")
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    metode = models.CharField(max_length=10, choices=METODE_CHOICES, default=METODE_CHECKBOX)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        constraints = [
            models.UniqueConstraint(fields=['client', 'versio'],
                                    name='unique_acceptance_per_client_versio'),
        ]

    def __str__(self):
        return f'{self.client.codi_tenant} accepta {self.versio} @ {self.timestamp:%Y-%m-%d}'

    def save(self, *args, **kwargs):
        # APPEND-ONLY: una fila existent no es pot modificar mai.
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValueError('LegalAcceptance és append-only: no es pot modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # APPEND-ONLY: una prova d'acceptació no s'esborra mai.
        raise ValueError('LegalAcceptance és append-only: no es pot esborrar.')
