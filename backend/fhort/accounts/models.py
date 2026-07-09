from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    nom_complet = models.CharField(max_length=200)
    rol_nom = models.CharField(max_length=80)
    actiu = models.BooleanField(default=True)
    cost_hora = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    color_avatar = models.CharField(max_length=7, default='#888888')
    permisos = models.JSONField(default=dict, blank=True)
    # Sprint A (calendari): horari propi del tècnic (mateix format que CompanyCalendar.horaris).
    # Null → s'usa la jornada de l'empresa (CompanyCalendar).
    jornada_override = models.JSONField(null=True, blank=True)

    class Meta:
        verbose_name = 'Perfil d\'usuari'
        verbose_name_plural = 'Perfils d\'usuari'

    def __str__(self):
        return self.nom_complet or self.user.get_username()


# Sprint S1 — Per-tenant configuration
class TenantConfig(models.Model):
    """Global tenant configuration. A single instance per tenant."""
    UNITAT_CHOICES = [('CM','Centimetres (EU)'),('INCH','Inches (US)')]
    NORMA_CHOICES  = [('ISO_8559','ISO 8559 (EU)'),('ASTM_D13','ASTM D13 (US)')]

    unitat_mesura    = models.CharField(max_length=10, choices=UNITAT_CHOICES, default='CM')
    norma_referencia = models.CharField(max_length=20, choices=NORMA_CHOICES, default='ISO_8559')
    nom_empresa      = models.CharField(max_length=200, blank=True)
    logo_url         = models.URLField(blank=True)
    # Comercial Studio (B2) — logo pujat (fitxer) per a la capçalera dels documents PDF. Es
    # serveix via MEDIA_ROOT (Pillow ja al requirements). Complementa logo_url (extern). La UI
    # d'upload i l'exposició al TenantConfigSerializer (pom/s2_serializers.py) són sprint futur.
    logo_file        = models.ImageField(upload_to='tenant_logos/', null=True, blank=True)
    # Comercial Studio (B1) — tarifa interna de COST per hora (plana, v1). Font del cost estàndard
    # dels serveis interns: Σ cascada(task_code, GTI) × hourly_rate. ≠ Product.sale_rate (VENDA).
    # null = no fixada (la cascada de cost recorrerà a captura quan calgui). Per-perfil = v2.
    hourly_rate      = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    # Comercial Studio (P6) — dades bancàries/pagament de l'emissor per als documents PDF (oferta i
    # comanda). El PDF les llegeix d'aquí (fi del hardcode). `iban` = compte de cobrament; blank = no
    # es mostra al document. `payment_notes` = text lliure (forma de pagament, referències, etc.).
    iban             = models.CharField(max_length=34, blank=True, help_text="IBAN de cobrament (emissor).")
    payment_notes    = models.TextField(blank=True, help_text="Notes de pagament de l'emissor (PDF).")
    # Comercial Studio (Empresa/fiscal) — dades fiscals de l'EMISSOR per a la capçalera dels documents
    # PDF (oferta/comanda/albarà). Additives (blank), mirall conceptual del vocabulari fiscal de
    # tasks.Customer (receptor) perquè el PDF llegeixi emissor i receptor amb la mateixa forma. Fi del
    # hardcode de capçalera ("FHORT MANAGEMENT, SL / Salmerón 165…"). `nom_empresa` (S1) queda com a nom
    # comercial curt; `legal_name` és la raó social legal. `country` = ISO 3166-1 alpha-2 (mirall Customer.pais).
    legal_name       = models.CharField(max_length=200, blank=True, help_text="Raó social legal de l'emissor.")
    tax_id           = models.CharField(max_length=20, blank=True, help_text="NIF/VAT/tax id de l'emissor.")
    address          = models.CharField(max_length=200, blank=True, help_text="Adreça de l'emissor.")
    postal_code      = models.CharField(max_length=20, blank=True)
    city             = models.CharField(max_length=100, blank=True)
    country          = models.CharField(max_length=2, default='ES', help_text="ISO 3166-1 alpha-2.")
    email            = models.EmailField(blank=True)
    phone            = models.CharField(max_length=40, blank=True)
    creat_at         = models.DateTimeField(auto_now_add=True)
    actualitzat_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tenant Configuration"

    def __str__(self):
        return f"Config — {self.unitat_mesura} | {self.norma_referencia}"

    @classmethod
    def get_or_create_default(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
