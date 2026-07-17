"""
invoice_pdf.py — El PDF de la factura de FHORT a un tenant (F-FACT B1).

NO reinventa el generador: reutilitza les primitives ja provades i aprovades de
`commerce/pdf_service` (fonts Montserrat amb fallback, format monetari EU, paleta,
geometria de pàgina). El que canvia és el document: una factura no és un pressupost
—porta sèrie+número, bases per tipus d'IVA, quotes i mencions legals— i el seu emissor
no és el tenant sinó FHORT.

FRONTERA: `backoffice` viu a public i `accounts.TenantConfig` (l'emissor) viu al schema
del tenant. La lectura es fa explícitament amb schema_context(EMISSOR_SCHEMA); és una
lectura delegada, no una FK: el backoffice segueix sense referenciar models de tenant a
la seva capa de dades.
"""
import logging
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from django.utils import timezone
from django_tenants.utils import schema_context
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)

# Primitives compartides amb el generador comercial: una sola definició de la marca.
from fhort.commerce.pdf_service import (
    _fonts, _money, _fmt_date, F_LIGHT, F_REG, F_SEMI, F_BOLD,
    GOLD, GREY, LGREY, DARK, DGREY, ROWLINE,
    PAGE_W, PAGE_H, ML, MR, MT, MB, CW, ZP,
)

logger = logging.getLogger(__name__)

# El schema del tenant que ÉS FHORT (l'emissor de les factures de plataforma).
EMISSOR_SCHEMA = getattr(settings, 'FHORT_EMISSOR_SCHEMA', 'fhort')

X_B = 100 * mm
COL_LEFT_W, COL_RIGHT_W = X_B, CW - X_B


def _emissor():
    """Dades de l'emissor (FHORT), llegides del TenantConfig del seu schema."""
    from fhort.accounts.models import TenantConfig
    with schema_context(EMISSOR_SCHEMA):
        cfg = TenantConfig.objects.first()
        if cfg is None:
            return None
        # Còpia dels valors: fora del schema_context l'objecte no s'ha de tornar a consultar.
        return {
            'legal_name': (cfg.legal_name or cfg.nom_empresa or '').strip(),
            'tax_id': (cfg.tax_id or '').strip(),
            'address': (cfg.address or '').strip(),
            'postal_code': (cfg.postal_code or '').strip(),
            'city': (cfg.city or '').strip(),
            'country': (cfg.country or '').strip(),
            'email': (cfg.email or '').strip(),
            'phone': (cfg.phone or '').strip(),
            'iban': (cfg.iban or '').strip(),
            'payment_notes': (cfg.payment_notes or '').strip(),
            'legal_footer': (cfg.legal_footer or '').strip(),
            'logo_path': (cfg.logo_file.path if cfg.logo_file else None),
        }


def _receptor(client):
    """Dades fiscals del client destinatari (registre public de tenants)."""
    linia = ', '.join(x for x in [client.adreca_linia1, client.adreca_linia2] if x)
    ciutat = ' '.join(x for x in [client.codi_postal, client.ciutat] if x)
    return {
        'nom': (client.rao_social or client.nom or '').strip(),
        'nif': (client.vat_number or client.nif or '').strip(),
        'address': linia.strip(),
        'city': ciutat.strip(),
        'country': (client.pais or '').strip(),
        'email': (client.email_facturacio or '').strip(),
    }


def _styles():
    F = _fonts()
    return {
        'h1': ParagraphStyle('h1', fontName=F[F_BOLD], fontSize=15, leading=18, textColor=DARK),
        'lbl': ParagraphStyle('lbl', fontName=F[F_SEMI], fontSize=6.5, leading=9,
                              textColor=GREY, spaceAfter=1),
        'body': ParagraphStyle('body', fontName=F[F_REG], fontSize=8.5, leading=11.5, textColor=DARK),
        'small': ParagraphStyle('small', fontName=F[F_LIGHT], fontSize=7.5, leading=10, textColor=DGREY),
        'foot': ParagraphStyle('foot', fontName=F[F_LIGHT], fontSize=6.5, leading=8.5, textColor=GREY),
        'cell': ParagraphStyle('cell', fontName=F[F_REG], fontSize=8, leading=10.5, textColor=DARK),
        'num': ParagraphStyle('num', fontName=F[F_SEMI], fontSize=11, leading=14, textColor=GOLD),
    }


def _party_block(titol, d, S, amb_contacte=True):
    rows = [[Paragraph(titol, S['lbl'])]]
    if d.get('nom') or d.get('legal_name'):
        rows.append([Paragraph(f"<b>{d.get('legal_name') or d.get('nom')}</b>", S['body'])])
    if d.get('tax_id') or d.get('nif'):
        rows.append([Paragraph(f"NIF: {d.get('tax_id') or d.get('nif')}", S['small'])])
    adreca = ', '.join(x for x in [d.get('address'), _ciutat(d)] if x)
    if adreca:
        rows.append([Paragraph(adreca, S['small'])])
    if amb_contacte and d.get('email'):
        rows.append([Paragraph(d['email'], S['small'])])
    return Table(rows, colWidths=[COL_LEFT_W - 6 * mm], style=TableStyle(ZP))


def _ciutat(d):
    trossos = [x for x in [d.get('postal_code'), d.get('city')] if x] or ([d['city']] if d.get('city') else [])
    ciutat = ' '.join(trossos)
    return ', '.join(x for x in [ciutat, d.get('country')] if x)


def generate_invoice_pdf(invoice):
    """Bytes del PDF de `invoice`. Serveix esborranys (marcats) i emeses."""
    from .invoice_service import compute_totals

    S = _styles()
    F = _fonts()
    em = _emissor()
    if em is None:
        raise ValueError(
            f"No hi ha TenantConfig al schema '{EMISSOR_SCHEMA}': falten les dades "
            f"de l'emissor per generar el PDF.")
    re_ = _receptor(invoice.client)
    base, quota, total, grups = compute_totals(invoice)

    story = []

    # ── Capçalera: logo + identitat de la factura ────────────────────────────
    logo = None
    if em['logo_path']:
        try:
            logo = Image(em['logo_path'], width=30 * mm, height=12 * mm, kind='proportional')
        except Exception as e:  # noqa: BLE001 — mai petar la factura per un logo
            logger.warning('invoice_pdf: logo no carregat (%s)', e)

    es_esborrany = invoice.estat == invoice.ESTAT_ESBORRANY
    titol = 'FACTURA' if invoice.tipus != invoice.TIPUS_RECTIFICATIVA else 'FACTURA RECTIFICATIVA'
    dret = [[Paragraph(titol, S['h1'])]]
    if es_esborrany:
        dret.append([Paragraph('ESBORRANY — SENSE VALIDESA FISCAL', S['lbl'])])
    else:
        dret.append([Paragraph(invoice.numero, S['num'])])
    dret.append([Paragraph(f"Data: {_fmt_date(timezone.localtime(invoice.emesa_at).date() if invoice.emesa_at else None)}", S['small'])])
    if invoice.tipus == invoice.TIPUS_RECTIFICATIVA and invoice.rectifica_id:
        dret.append([Paragraph(f"Rectifica: {invoice.rectifica.numero}", S['small'])])

    story.append(Table(
        [[logo or Paragraph(em['legal_name'], S['body']),
          Table(dret, colWidths=[COL_RIGHT_W], style=TableStyle(ZP))]],
        colWidths=[COL_LEFT_W, COL_RIGHT_W],
        style=TableStyle(ZP + [('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ('ALIGN', (1, 0), (1, 0), 'RIGHT')])))
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGREY))
    story.append(Spacer(1, 5 * mm))

    # ── Emissor / Receptor ──────────────────────────────────────────────────
    story.append(Table(
        [[_party_block('EMISSOR', em, S), _party_block('FACTURAR A', re_, S)]],
        colWidths=[COL_LEFT_W, COL_RIGHT_W],
        style=TableStyle(ZP + [('VALIGN', (0, 0), (-1, -1), 'TOP')])))
    story.append(Spacer(1, 7 * mm))

    # ── Línies ──────────────────────────────────────────────────────────────
    head = ['CONCEPTE', 'QTAT', 'PREU', 'IVA', 'IMPORT']
    w = [CW - 92 * mm, 18 * mm, 24 * mm, 16 * mm, 34 * mm]
    data = [[Paragraph(f'<b>{h}</b>', S['lbl']) for h in head]]
    for l in invoice.lines.select_related('vat_rate').all():
        pct = l.pct_iva if l.pct_iva else (l.vat_rate.percentatge if l.vat_rate else Decimal('0'))
        data.append([
            Paragraph(l.descripcio, S['cell']),
            Paragraph(f'{Decimal(l.quantitat).normalize():f}', S['cell']),
            Paragraph(_money(l.preu_unit), S['cell']),
            Paragraph(f'{Decimal(pct).normalize():f}%', S['cell']),
            Paragraph(_money(l.total), S['cell']),
        ])
    t = Table(data, colWidths=w, repeatRows=1)
    t.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, GOLD),
        ('LINEBELOW', (0, 1), (-1, -1), 0.25, ROWLINE),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(t)
    story.append(Spacer(1, 6 * mm))

    # ── Totals: una base i una quota PER TIPUS (una factura amb dos tipus ho ha de dir) ──
    tot = [['Base imposable', _money(base)]]
    for g in grups:
        tot.append([f"IVA {Decimal(g['pct']).normalize():f}% sobre {_money(g['base'])}", _money(g['quota'])])
    tot.append(['TOTAL', f"{_money(total)} {invoice.moneda}"])
    tt = Table(tot, colWidths=[46 * mm, 34 * mm], hAlign='RIGHT')
    tt.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -2), F[F_REG]), ('FONTSIZE', (0, 0), (-1, -2), 8.5),
        ('FONTNAME', (0, -1), (-1, -1), F[F_BOLD]), ('FONTSIZE', (0, -1), (-1, -1), 10),
        ('TEXTCOLOR', (0, -1), (-1, -1), GOLD),
        ('LINEABOVE', (0, -1), (-1, -1), 0.5, GOLD),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(tt)

    # ── Mencions legals dels tipus (inversió del subjecte passiu, exempcions) ──
    mencions = [g['mencio_legal'] for g in grups if g.get('mencio_legal')]
    if mencions:
        story.append(Spacer(1, 5 * mm))
        for m in mencions:
            story.append(Paragraph(m, S['small']))

    # ── Pagament ────────────────────────────────────────────────────────────
    pag = []
    if em['iban']:
        pag.append(f"<b>IBAN:</b> {em['iban']}")
    if em['payment_notes']:
        pag.append(em['payment_notes'])
    if pag:
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph('PAGAMENT', S['lbl']))
        for p in pag:
            story.append(Paragraph(p, S['small']))

    if invoice.nota:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(invoice.nota, S['small']))

    # ── Peu legal ───────────────────────────────────────────────────────────
    def _peu(canvas, doc):
        if not em['legal_footer']:
            return
        canvas.saveState()
        p = Paragraph(em['legal_footer'].replace('\n', '<br/>'), _styles()['foot'])
        w, h = p.wrap(CW, 20 * mm)
        p.drawOn(canvas, ML, MB - h - 2 * mm)
        canvas.restoreState()

    buf = BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4,
                          leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
                          title=f'Factura {invoice.numero or "esborrany"}')
    frame = Frame(ML, MB, CW, PAGE_H - MT - MB, id='f',
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame], onPage=_peu)])
    doc.build(story)
    return buf.getvalue()
