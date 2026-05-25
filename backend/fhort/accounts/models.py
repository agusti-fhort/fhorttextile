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
