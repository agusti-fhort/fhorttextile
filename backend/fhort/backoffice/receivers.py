from django.dispatch import receiver
from fhort.tasks.signals import model_consumption_started
from .models import ModelConsumptionEvent


@receiver(model_consumption_started)
def on_model_consumption_started(sender, codi_client, period, opaque_ref, merited_at, **kwargs):
    """Sprint 4.1: escriu l'esdeveniment de consum a public.
    Pur: NO toca cap dada del tenant; només rep el fet ja resolt i el persisteix.
    get_or_create per opaque_ref → idempotent davant un doble-send accidental."""
    ModelConsumptionEvent.objects.get_or_create(
        opaque_ref=opaque_ref,
        defaults={
            'codi_client': codi_client,
            'period': period,
            'merited_at': merited_at,
        },
    )
