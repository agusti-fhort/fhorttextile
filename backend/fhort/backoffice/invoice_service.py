"""
invoice_service.py — El document fiscal: numeració, IVA i emissió (F-FACT B1).

Separat de `billing_service` a posta: allà hi viu el MOTOR AUTOMÀTIC (què es merita
i quant), aquí hi viu el DOCUMENT (quin número porta, quin IVA li toca i quan es
congela). Les dues factures —l'automàtica de meritació i la manual de serveis— surten
per aquesta porta quan s'emeten.

Llei de la numeració: el número es reserva EN EMETRE, dins d'una transacció i amb
select_for_update sobre la sèrie. Un esborrany no té número, i un esborrany descartat
no forada la sèrie.

Llei de l'IVA: el tipus surt de la fila de VATRate lligada al règim del client
(Client.regim_vat, que ja es deriva sol de país + VAT). Cap percentatge viu al codi.
En emetre, el pct i la quota es congelen a la línia (snapshot): canviar la taula demà
no reescriu una factura d'ahir.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from .models import Invoice, InvoiceLine, InvoiceSerie, VATRate

logger = logging.getLogger(__name__)

CENTIM = Decimal('0.01')


def _q(value):
    """Arrodoniment monetari canònic: 2 decimals, half-up (el de la factura, no el del float)."""
    return Decimal(value or 0).quantize(CENTIM, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Numeració
# ---------------------------------------------------------------------------
def reserve_invoice_number(serie, *, now=None):
    """Reserva atòmicament el següent correlatiu de `serie` i retorna (numero, num_seq).

    Ha de córrer DINS d'una transacció (l'emissió n'obre una): el select_for_update
    manté el bloqueig fins al commit, i és el que garanteix que dues emissions
    simultànies no es donin el mateix número.

    Amb `reinici_anual`, el comptador torna a 1 en canviar d'any. Sense, creix sempre.
    """
    now = now or timezone.now()
    any_ = now.year
    s = InvoiceSerie.objects.select_for_update().get(pk=serie.pk)
    if not s.activa:
        raise ValueError(f"La sèrie {s.codi} està desactivada: no pot emetre.")
    if s.reinici_anual and s.any_actual != any_:
        seq = 1
    else:
        seq = s.comptador + 1
    numero = s.render(seq, any_)          # valida la plantilla ABANS d'escriure res
    s.comptador = seq
    s.any_actual = any_
    s.save(update_fields=['comptador', 'any_actual'])
    return numero, seq


# ---------------------------------------------------------------------------
# IVA
# ---------------------------------------------------------------------------
def default_vat_for(client):
    """El VATRate per defecte del règim del client. Falla TANCAT si no n'hi ha cap.

    `Client.regim_vat` es deriva sol a cada save() (tenants/models.py): ES → espanyol,
    UE B2B amb VAT → inversió, UE B2C → OSS, fora UE → exempt. Aquí només s'hi mapa la
    fila; si l'operador no l'ha creada, no ens l'inventem.
    """
    regim = client.regim_vat or ''
    if not regim:
        raise ValueError(
            f"El client {client.codi_tenant} no té règim d'IVA derivat (falta país?). "
            f"No es pot determinar l'IVA.")
    rate = VATRate.objects.filter(regim_default=regim, actiu=True).first()
    if rate is None:
        raise ValueError(
            f"No hi ha cap tipus d'IVA actiu per al règim '{regim}' "
            f"(client {client.codi_tenant}). Crea'l a Facturació → Tipus d'IVA.")
    return rate


def compute_totals(invoice, *, persist=False):
    """Calcula base, quota i total de `invoice` a partir de les seves línies.

    Retorna (base, quota, total, per_tipus) on `per_tipus` és la llista de bases i
    quotes agrupades per tipus d'IVA — el desglossament que el peu del PDF necessita
    (una factura amb dos tipus ha d'ensenyar les dues bases per separat).

    `persist=True` escriu el snapshot a les línies i a la factura. Només l'emissió el
    fa servir; la previsualització calcula i no toca res.
    """
    fallback = None
    base_total = Decimal('0.00')
    quota_total = Decimal('0.00')
    grups = {}

    for line in invoice.lines.select_related('vat_rate').all():
        rate = line.vat_rate
        if rate is None:
            if fallback is None:
                fallback = default_vat_for(invoice.client)
            rate = fallback
        base = _q(line.total)
        quota = _q(base * rate.percentatge / Decimal('100'))
        if persist:
            line.pct_iva = rate.percentatge
            line.quota_iva = quota
            # update() i no save(): el guard de la línia barra qualsevol escriptura si
            # la factura ja no és esborrany, i aquí encara ho és — però passar per
            # update() deixa clar que això és el motor, no una edició d'usuari.
            InvoiceLine.objects.filter(pk=line.pk).update(
                pct_iva=rate.percentatge, quota_iva=quota)
        base_total += base
        quota_total += quota
        g = grups.setdefault(rate.codi, {
            'codi': rate.codi, 'nom': rate.nom, 'pct': rate.percentatge,
            'mencio_legal': rate.mencio_legal, 'base': Decimal('0.00'),
            'quota': Decimal('0.00'),
        })
        g['base'] += base
        g['quota'] += quota

    total = _q(base_total + quota_total)
    if persist:
        Invoice.objects.filter(pk=invoice.pk).update(
            base_imposable=_q(base_total), quota_iva=_q(quota_total), total=total)
        invoice.base_imposable, invoice.quota_iva, invoice.total = (
            _q(base_total), _q(quota_total), total)
    return _q(base_total), _q(quota_total), total, list(grups.values())


# ---------------------------------------------------------------------------
# Emissió
# ---------------------------------------------------------------------------
@transaction.atomic
def emit_invoice(invoice, serie, *, now=None):
    """Emet `invoice`: congela l'IVA, reserva el número de `serie` i passa a EMESA.

    Idempotent per definició: una factura ja emesa no es torna a emetre (tindria dos
    números). L'ordre importa — primer el càlcul (que encara pot fallar per manca de
    tipus d'IVA) i després el número, perquè un error de configuració no es mengi un
    correlatiu.
    """
    if invoice.estat != Invoice.ESTAT_ESBORRANY:
        raise ValueError(
            f"La factura {invoice.numero or invoice.pk} ja està {invoice.estat}: "
            f"no es pot tornar a emetre.")
    if not invoice.lines.exists():
        raise ValueError('Una factura sense línies no es pot emetre.')

    # 1) IVA congelat a les línies i totals a la capçalera (encara en esborrany).
    compute_totals(invoice, persist=True)

    # 2) Número: l'últim pas abans de congelar. Si el pas 1 peta, la sèrie no s'ha mogut.
    numero, seq = reserve_invoice_number(serie, now=now)

    # 3) Congelació. update() directe: el guard de save() ja consideraria immutables
    #    aquests mateixos camps un cop l'estat canviï, i aquí els escrivim tots alhora.
    ts = now or timezone.now()
    Invoice.objects.filter(pk=invoice.pk).update(
        serie=serie, numero=numero, num_seq=seq,
        estat=Invoice.ESTAT_EMESA, emesa_at=ts)
    invoice.refresh_from_db()
    logger.info('Factura EMESA: %s (client=%s, total=%s %s)',
                invoice.numero, invoice.client.codi_tenant, invoice.total, invoice.moneda)
    return invoice


@transaction.atomic
def create_rectificativa(original, *, motiu=''):
    """Crea l'esborrany de la rectificativa d'una factura EMESA, amb les línies en negatiu.

    No emet res: torna un esborrany editable perquè l'operador el revisi i l'emeti amb
    la sèrie que toqui. La correcció d'una emesa mai és una edició (models.Invoice.save).
    """
    if original.estat == Invoice.ESTAT_ESBORRANY:
        raise ValueError(
            'Un esborrany no es rectifica: s\'edita o s\'esborra directament.')
    if original.tipus == Invoice.TIPUS_RECTIFICATIVA:
        raise ValueError('Una rectificativa no es rectifica: emet-ne una de nova sobre l\'original.')

    rect = Invoice.objects.create(
        client=original.client, period=original.period,
        tipus=Invoice.TIPUS_RECTIFICATIVA, estat=Invoice.ESTAT_ESBORRANY,
        moneda=original.moneda, rectifica=original,
        nota=motiu or f'Rectificativa de {original.numero}',
    )
    for l in original.lines.select_related('vat_rate').all():
        InvoiceLine.objects.create(
            invoice=rect, service=l.service,
            descripcio=f'Rectificació · {l.descripcio}',
            quantitat=l.quantitat, preu_unit=-l.preu_unit, total=-l.total,
            moneda=l.moneda, vat_rate=l.vat_rate,
        )
    compute_totals(rect, persist=True)
    return rect
