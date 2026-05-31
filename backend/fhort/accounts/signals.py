"""Signal de creació de UserProfile (Sprint A). sender=User explícit + guarda d'schema."""
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile
from .capabilities import DEFAULT_ROLE

try:
    from django_tenants.utils import get_public_schema_name
except Exception:
    def get_public_schema_name():
        return "public"

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Crea UserProfile en crear un User DINS d'un schema de tenant (mai a 'public')."""
    if not created:
        return
    if connection.schema_name == get_public_schema_name():
        return
    UserProfile.objects.get_or_create(
        user=instance,
        defaults={
            "nom_complet": instance.get_username(),
            "rol_nom": DEFAULT_ROLE,
            "permisos": {},
        },
    )
