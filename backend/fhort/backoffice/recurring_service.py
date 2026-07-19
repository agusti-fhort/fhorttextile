"""
recurring_service.py — Facturació recurrent: quota + consum de models iniciats (F-RECUR).

Genera factures DRAFT per a un període. NO emet mai (l'emissió és acció humana amb
sèrie, a F-FACT-B1). Idempotent per construcció:
  · la quota per (client, període) no es duplica — un DRAFT existent es reaprofita;
  · els events de consum ja vinculats a una línia no re-entren (filtre invoice_line NULL).

Separat de billing_service (el motor previ, previ a F-FACT-B1): aquell comptava el
consum amb .count() sense vincular-lo i creava DRAFTs sense IVA. Aquest vincula i deixa
la factura llesta perquè compute_totals hi posi l'IVA en emetre. billing_service segueix
viu fins que es jubili; no es toca.
"""
import logging
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from .models import (
    ContractLine, Invoice, InvoiceLine, ModelConsumptionEvent, TenantContract,
)
from fhort.tenants.models import Client

logger = logging.getLogger(__name__)
CENTIM = Decimal('0.01')


def active_contract(client, period):
    """El TenantContract vigent per a client+període ('YYYY-MM'), o None."""
    import calendar
    import datetime
    y, m = int(period[:4]), int(period[5:7])
    start = datetime.date(y, m, 1)
    end = datetime.date(y, m, calendar.monthrange(y, m)[1])
    return (TenantContract.objects
            .filter(client=client, actiu=True, data_inici__lte=end)
            .filter(models.Q(data_fi__isnull=True) | models.Q(data_fi__gte=start))
            .order_by('-data_inici')
            .first())


def billable_events(codi_client, period):
    """Els events del període facturables: no exclosos i no ja vinculats a cap línia.

    Aquest filtre ÉS l'anti-doble-cobrament: un event amb invoice_line no torna a sortir,
    per molt que es re-executi el període.
    """
    return ModelConsumptionEvent.objects.filter(
        codi_client=codi_client, period=period,
        exclos=False, invoice_line__isnull=True)


def _plan_una_factura(client, period, contract, *, dry_run):
    """Calcula (i, si no és dry_run, persisteix) el DRAFT d'un client per al període.

    Retorna un dict-informe sempre; amb `invoice` (o None en dry_run). No emet: deixa
    la factura en esborrany amb les línies i els events vinculats.
    """
    report = {
        'codi_client': client.codi_tenant, 'period': period,
        'quota': None, 'consum': None, 'exclosos': 0, 'total_sense_iva': Decimal('0.00'),
        'invoice_id': None, 'creada': False, 'avisos': [],
    }
    lines_plan = []

    # ── QUOTA (tier_fee), només si la periodicitat toca en aquest període ───────────
    quota_line = contract.lines.filter(actiu=True, service__tipus='tier_fee').first()
    if quota_line:
        if contract.quota_toca_al_periode(period):
            lines_plan.append(dict(
                service=quota_line.service, descripcio=quota_line.service.nom,
                quantitat=Decimal('1'), preu_unit=quota_line.preu,
                total=quota_line.preu.quantize(CENTIM), moneda=quota_line.moneda,
                _events=[]))
            report['quota'] = str(quota_line.preu.quantize(CENTIM))
        else:
            report['avisos'].append(
                f'quota {contract.periodicitat}: no toca a {period} (àncora {contract.data_inici})')
    else:
        report['avisos'].append('cap ContractLine tier_fee: sense quota')

    # ── CONSUM (model_count): events facturables × tarifa, respectant inclosos ──────
    consum_line = contract.lines.filter(actiu=True, service__tipus='model_count').first()
    events = list(billable_events(client.codi_tenant, period))
    report['exclosos'] = ModelConsumptionEvent.objects.filter(
        codi_client=client.codi_tenant, period=period, exclos=True).count()
    if events:
        if consum_line is None:
            report['avisos'].append(
                f'{len(events)} events de consum però cap ContractLine model_count: '
                f'no es facturen (ni es vinculen).')
        else:
            n = len(events)
            exces = max(0, n - consum_line.inclosos)
            facturables = events[consum_line.inclosos:] if exces else []
            report['consum'] = {
                'events': n, 'inclosos': consum_line.inclosos, 'facturats': exces,
                'tarifa': str(consum_line.preu)}
            if exces:
                lines_plan.append(dict(
                    service=consum_line.service,
                    descripcio=f'{consum_line.service.nom} ({n} models, {consum_line.inclosos} inclosos)',
                    quantitat=Decimal(str(exces)), preu_unit=consum_line.preu,
                    total=(Decimal(str(exces)) * consum_line.preu).quantize(CENTIM),
                    moneda=consum_line.moneda, _events=facturables))
            else:
                report['avisos'].append(
                    f'{n} models dins la franquícia ({consum_line.inclosos} inclosos) → 0 €')

    report['total_sense_iva'] = sum((l['total'] for l in lines_plan), Decimal('0.00'))

    if dry_run or not lines_plan:
        if not lines_plan:
            report['avisos'].append('res a facturar: cap DRAFT creat')
        return report

    # ── Persistència: DRAFT idempotent ─────────────────────────────────────────────
    with transaction.atomic():
        invoice, creada = Invoice.objects.get_or_create(
            client=client, period=period, tipus=Invoice.TIPUS_AUTO,
            defaults={'estat': Invoice.ESTAT_ESBORRANY, 'moneda': 'EUR'})
        if invoice.estat != Invoice.ESTAT_ESBORRANY:
            report['avisos'].append(
                f'ja existeix una factura {invoice.estat} ({invoice.numero}) per aquest '
                f'període: no es toca.')
            report['invoice_id'] = invoice.id
            return report

        for lp in lines_plan:
            events = lp.pop('_events')
            # Idempotència fina: si la línia d'aquest servei ja existeix al DRAFT, no la
            # dupliquem (re-executar afegiria una segona quota). Els events NO facturats
            # abans (filtre NULL) sí que s'afegirien; per això la quota es guarda per
            # (invoice, service) i el consum per event no vinculat.
            existent = invoice.lines.filter(service=lp['service']).first()
            if existent and not events:
                continue
            line = InvoiceLine.objects.create(invoice=invoice, **lp)
            # VINCLE: aquests events queden facturats per BD. update() evita el guard de
            # save() de l'event (que no en té, però és el patró del motor).
            if events:
                ModelConsumptionEvent.objects.filter(
                    pk__in=[e.pk for e in events]).update(invoice_line=line)

        report['invoice_id'] = invoice.id
        report['creada'] = creada
    logger.info('F-RECUR: DRAFT %s per %s %s (total s/IVA %s)',
                report['invoice_id'], client.codi_tenant, period, report['total_sense_iva'])
    return report


def generate_invoices(period, *, codi_client=None, dry_run=False):
    """Genera els DRAFT recurrents del període. Retorna la llista d'informes per client.

    Un client entra si: és viu, no gratuït, i té contracte vigent al període. Els clients
    sense res a facturar surten a l'informe amb el motiu, però no generen DRAFT.
    """
    qs = Client.objects.all()
    if codi_client:
        qs = qs.filter(codi_tenant=codi_client)
    reports = []
    for client in qs.order_by('codi_tenant'):
        if client.es_gratuit:   # gratuïtat perpètua o promoció vigent → no es factura
            continue
        contract = active_contract(client, period)
        if contract is None:
            if codi_client:   # només es reporta el "sense contracte" si s'ha demanat el client
                reports.append({'codi_client': client.codi_tenant, 'period': period,
                                'avisos': ['sense contracte vigent'], 'invoice_id': None})
            continue
        reports.append(_plan_una_factura(client, period, contract, dry_run=dry_run))
    return reports
