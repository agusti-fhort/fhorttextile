# P-LEADS L2 — avís per correu (best-effort) d'un lead nou. Adormit fins que hi hagi
# SMTP real (EMAIL_HOST + LEADS_NOTIFY_EMAIL a l'entorn, vegeu settings.py i .env.example).
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _build_body(lead):
    return (
        'Nou lead des de la web.\n\n'
        f'Nom: {lead.nom}\n'
        f"Empresa: {lead.empresa or '—'}\n"
        f'Email: {lead.email}\n'
        f'Idioma: {lead.get_idioma_display()}\n'
        f"Interès: {lead.get_interes_display() if lead.interes else '—'}\n"
        f"Pàgina: {lead.pagina_origen or '—'}\n\n"
        f'Missatge:\n{lead.missatge}\n\n'
        f'Detall: /leads/{lead.pk}\n'
    )


def notifica_lead(lead):
    """Avís best-effort per correu d'un lead nou. Cridada via transaction.on_commit
    (DESPRÉS que el lead ja estigui desat) — el correu MAI fa fallar ni endarrereix
    la resposta pública. Sense EMAIL_HOST o LEADS_NOTIFY_EMAIL, no intenta res:
    `notificat` es queda False, el lead ja hi és igualment."""
    if not settings.EMAIL_HOST or not settings.LEADS_NOTIFY_EMAIL:
        return

    from django.core.mail import EmailMessage
    try:
        missatge = EmailMessage(
            subject=f'Nou lead: {lead.nom}',
            body=_build_body(lead),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.LEADS_NOTIFY_EMAIL],
            reply_to=[lead.email],
        )
        missatge.send(fail_silently=False)
    except Exception:   # noqa: BLE001 — best-effort dur: res pot escapar cap a la resposta
        logger.exception('leads: avís per correu fallit (best-effort, empassat)')
        return

    lead.notificat = True
    lead.save(update_fields=['notificat'])
