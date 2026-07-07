"""Signals del mòdul comercial.

Recàlcul de totals de la capçalera cada cop que una línia canvia o s'esborra. Es re-consulta
el Quote per pk (no la instància cachejada de la línia) per no petar en el cas CASCADE (quan
s'esborra un Quote, les seves línies disparen post_delete però la capçalera ja no existeix).
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import QuoteLine, Quote


def _recalc_quote(quote_id):
    q = Quote.objects.filter(pk=quote_id).first()
    if q is not None:
        q.recalculate_totals()


@receiver(post_save, sender=QuoteLine)
def quoteline_saved(sender, instance, **kwargs):
    _recalc_quote(instance.quote_id)


@receiver(post_delete, sender=QuoteLine)
def quoteline_deleted(sender, instance, **kwargs):
    _recalc_quote(instance.quote_id)
