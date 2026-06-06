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
