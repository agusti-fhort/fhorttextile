"""
billing_service.py — Motor de facturació automàtica (Sprint 6 · Capa 4).
Genera Invoice + InvoiceLines per a un {codi_client, period} donat.
Només processa línies tier_fee i model_count (D1: manual = skip).
Idempotent: si ja existeix Invoice(client, period, auto) → retorna la que hi ha.
"""
import logging
from decimal import Decimal
from django.db import models, transaction
from django.utils import timezone
from .models import Invoice, InvoiceLine, TenantContract, ServiceCatalog
from .models import ModelConsumptionEvent
from fhort.tenants.models import Client

logger = logging.getLogger(__name__)


def _get_active_contract(client, period):
    """Retorna el TenantContract vigent per a client+period o None."""
    import datetime
    year, month = int(period[:4]), int(period[5:7])
    period_start = datetime.date(year, month, 1)
    import calendar
    period_end = datetime.date(year, month, calendar.monthrange(year, month)[1])

    qs = TenantContract.objects.filter(
        client=client,
        actiu=True,
        data_inici__lte=period_start,
    ).filter(
        models.Q(data_fi__isnull=True) | models.Q(data_fi__gte=period_end)
    ).prefetch_related('lines__service').order_by('-data_inici')
    return qs.first()


def generate_invoice(codi_client, period, dry_run=False):
    """
    Genera la factura automàtica per a {codi_client, period}.
    Retorna (invoice, created, warnings).
    dry_run=True: calcula però no persisteix res.
    """
    warnings = []

    try:
        client = Client.objects.get(codi_tenant=codi_client)
    except Client.DoesNotExist:
        raise ValueError(f"Client '{codi_client}' no trobat.")

    # Idempotència: si ja existeix, retornar-la
    if not dry_run:
        existing = Invoice.objects.filter(
            client=client, period=period, tipus='auto'
        ).first()
        if existing:
            return existing, False, ['Factura ja existent — retornada sense canvis.']

    # Contracte vigent
    contract = _get_active_contract(client, period)
    if not contract:
        raise ValueError(f"No hi ha cap contracte vigent per a {codi_client} al període {period}.")

    # Recompte de models meritats
    n_models = ModelConsumptionEvent.objects.filter(
        codi_client=codi_client, period=period
    ).count()

    # Calcular línies
    lines_data = []
    total = Decimal('0.00')

    for cl in contract.lines.filter(actiu=True):
        tipus = cl.service.tipus
        if tipus == 'manual':       # D1: skip
            continue
        elif tipus == 'tier_fee':
            quantitat = Decimal('1')
            preu_unit = cl.preu
            descripcio = cl.service.nom
        elif tipus == 'model_count':
            exces = max(0, n_models - cl.inclosos)
            quantitat = Decimal(str(exces))
            preu_unit = cl.preu
            descripcio = f'{cl.service.nom} ({n_models} models, {cl.inclosos} inclosos)'
            if exces == 0:
                warnings.append(
                    f'MODEL_INICIAT: {n_models} models dins la franquícia ({cl.inclosos} inclosos) → 0 €'
                )
        else:
            continue

        line_total = (quantitat * preu_unit).quantize(Decimal('0.01'))
        total += line_total
        lines_data.append(dict(
            service=cl.service,
            descripcio=descripcio,
            quantitat=quantitat,
            preu_unit=preu_unit,
            total=line_total,
            moneda=cl.moneda,
        ))

    if dry_run:
        return None, False, warnings + [
            f'DRY-RUN: {len(lines_data)} línies, total={total} EUR',
            *[f'  {l["descripcio"]}: {l["quantitat"]} × {l["preu_unit"]} = {l["total"]}' for l in lines_data]
        ]

    # Persistir
    with transaction.atomic():
        invoice = Invoice.objects.create(
            client=client, period=period, tipus='auto',
            estat='esborrany', total=total, moneda='EUR',
        )
        for ld in lines_data:
            InvoiceLine.objects.create(invoice=invoice, **ld)

    logger.info('Invoice generada: %s id=%s total=%s', invoice, invoice.id, total)
    return invoice, True, warnings
