from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class Plan(models.Model):
    NOM_SOLO = 'Solo'
    NOM_STUDIO = 'Studio'
    NOM_BRAND = 'Brand'
    NOM_ENTERPRISE = 'Enterprise'
    NOM_CHOICES = [
        (NOM_SOLO, 'Solo'),
        (NOM_STUDIO, 'Studio'),
        (NOM_BRAND, 'Brand'),
        (NOM_ENTERPRISE, 'Enterprise'),
    ]

    TIPOLOGIA_ESTUDI = 'estudi'
    TIPOLOGIA_MARCA = 'marca'
    TIPOLOGIA_ENTERPRISE = 'enterprise'
    TIPOLOGIA_CHOICES = [
        (TIPOLOGIA_ESTUDI, 'Estudi'),
        (TIPOLOGIA_MARCA, 'Marca'),
        (TIPOLOGIA_ENTERPRISE, 'Enterprise'),
    ]

    nom = models.CharField(max_length=20, choices=NOM_CHOICES, unique=True)
    tipologia = models.CharField(max_length=20, choices=TIPOLOGIA_CHOICES)
    preu_mensual = models.DecimalField(max_digits=10, decimal_places=2)
    max_models_actius = models.IntegerField()
    max_usuaris = models.IntegerField()
    storage_gb = models.IntegerField()
    ia_credits_mes = models.IntegerField()
    feature_flags = models.JSONField(default=dict, blank=True)
    actiu = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Pla'
        verbose_name_plural = 'Plans'

    def __str__(self):
        return self.nom


class Client(TenantMixin):
    TIPOLOGIA_ESTUDI = 'estudi'
    TIPOLOGIA_MARCA = 'marca'
    TIPOLOGIA_CHOICES = [
        (TIPOLOGIA_ESTUDI, 'Estudi'),
        (TIPOLOGIA_MARCA, 'Marca'),
    ]

    UNITAT_CM = 'cm'
    UNITAT_INCH = 'inch'
    UNITAT_CHOICES = [(UNITAT_CM, 'cm'), (UNITAT_INCH, 'inch')]

    nom = models.CharField(max_length=200)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='clients', null=True, blank=True)
    tipologia = models.CharField(max_length=20, choices=TIPOLOGIA_CHOICES)
    feature_flags = models.JSONField(default=dict, blank=True)
    actiu = models.BooleanField(default=True)
    data_alta = models.DateField(auto_now_add=True)
    onboarding_complet = models.BooleanField(default=False)

    moneda = models.CharField(max_length=3, default='EUR')
    unitats = models.CharField(max_length=4, choices=UNITAT_CHOICES, default=UNITAT_CM)
    idioma = models.CharField(max_length=5, default='ca')

    codi_tenant = models.CharField(max_length=3, unique=True)

    auto_create_schema = True
    auto_drop_schema = False

    class Meta:
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenants'

    def __str__(self):
        return f'{self.nom} [{self.codi_tenant}]'


class Domain(DomainMixin):
    pass
