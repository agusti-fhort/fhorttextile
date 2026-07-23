from django.dispatch import receiver
from django_tenants.utils import schema_context
from fhort.tasks.signals import model_consumption_started
from .models import ModelConsumptionEvent


@receiver(model_consumption_started)
def on_model_consumption_started(sender, codi_client, period, opaque_ref, merited_at,
                                 actor_schema='', **kwargs):
    """Sprint 4.1/4.2: escriu l'esdeveniment de consum a public. Pur i explícit.

    Federació v2 (P4): `actor_schema` és el tenant que merita. Kwarg opcional (default '')
    perquè el signal és nu: cap emissor antic es trenca si no el passa."""
    with schema_context('public'):
        ModelConsumptionEvent.objects.get_or_create(
            opaque_ref=opaque_ref,
            defaults={
                'codi_client': codi_client,
                'period': period,
                'merited_at': merited_at,
                'actor_schema': actor_schema,
            },
        )
