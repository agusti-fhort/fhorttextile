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

    class Meta:
        verbose_name = 'Perfil d\'usuari'
        verbose_name_plural = 'Perfils d\'usuari'

    def __str__(self):
        return self.nom_complet or self.user.get_username()


# Sprint S1 — Configuracio per tenant
class TenantConfig(models.Model):
    """Configuracio global del tenant. Una sola instancia per tenant."""
    UNITAT_CHOICES = [('CM','Centimetres (EU)'),('INCH','Inches (US)')]
    NORMA_CHOICES  = [('ISO_8559','ISO 8559 (EU)'),('ASTM_D13','ASTM D13 (US)')]

    unitat_mesura    = models.CharField(max_length=10, choices=UNITAT_CHOICES, default='CM')
    norma_referencia = models.CharField(max_length=20, choices=NORMA_CHOICES, default='ISO_8559')
    nom_empresa      = models.CharField(max_length=200, blank=True)
    logo_url         = models.URLField(blank=True)
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
