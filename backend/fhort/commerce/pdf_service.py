"""commerce/pdf_service.py — generació del PDF d'una oferta (B2, decisió R7).

reportlab.platypus: taula REAL paginable amb text vectorial (NO la foto PNG del pipeline
Konva de la fitxa tècnica — tecnologies diferents, no reutilitzable; confirmat al diagnòstic
B0/B2). Emissor = TenantConfig (nom_empresa); dades fiscals de l'emissor són placeholder fins
que existeixin al tenant. Client = camps fiscals de Customer (B1-P3). Etiquetes en català
(els documents van en català; el naming EN és només BD/codi).
"""
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)

FONT = 'Helvetica'
FONT_BOLD = 'Helvetica-Bold'


def _money(value):
    """Format monetari 2 decimals amb coma decimal (convenció EU)."""
    v = Decimal(value or 0).quantize(Decimal('0.01'))
    return f'{v:,.2f}'.replace(',', '§').replace('.', ',').replace('§', '.')


def _emitter_lines():
    """Nom i (placeholder) dades fiscals de l'emissor (el tenant). B1 només té nom_empresa."""
    try:
        from fhort.accounts.models import TenantConfig
        cfg = TenantConfig.objects.first()
    except Exception:
        cfg = None
    nom = (getattr(cfg, 'nom_empresa', '') or 'Empresa').strip()
    return [nom]


def _customer_lines(customer):
    """Bloc fiscal del client (Customer, B1-P3). Omet les línies buides."""
    c = customer
    out = [c.rao_social or c.nom]
    if c.nif:
        out.append(f'NIF: {c.nif}')
    if c.adreca_linia1:
        out.append(c.adreca_linia1)
    if c.adreca_linia2:
        out.append(c.adreca_linia2)
    ciutat = ' '.join(x for x in [c.codi_postal, c.ciutat] if x)
    if ciutat:
        out.append(ciutat)
    if c.pais:
        out.append(c.pais)
    return out


def generate_quote_pdf(quote):
    """Retorna els bytes del PDF de l'oferta `quote`."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=quote.document_number or 'Oferta',
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle('small', parent=styles['Normal'], fontName=FONT, fontSize=9, leading=12)
    h1 = ParagraphStyle('h1', parent=styles['Title'], fontName=FONT_BOLD, fontSize=18)
    label = ParagraphStyle('label', parent=small, fontName=FONT_BOLD)

    story = []

    # Capçalera: emissor (esquerra) · títol+número+dates (dreta)
    emitter = '<br/>'.join(_emitter_lines())
    meta = [
        f'<b>OFERTA</b>',
        f'Núm.: {quote.document_number or "—"}',
        f'Data: {quote.issued_at.isoformat() if quote.issued_at else "—"}',
        f'Vàlida fins: {quote.valid_until.isoformat() if quote.valid_until else "—"}',
    ]
    head = Table(
        [[Paragraph(emitter, small), Paragraph('<br/>'.join(meta), small)]],
        colWidths=[95 * mm, 75 * mm])
    head.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story += [head, Spacer(1, 8 * mm)]

    # Bloc client
    story += [Paragraph('Client', label),
              Paragraph('<br/>'.join(_customer_lines(quote.customer)), small),
              Spacer(1, 6 * mm)]

    # Taula de línies
    header = ['#', 'Descripció', 'Quantitat', 'Preu unitari', 'Total línia']
    rows = [header]
    for i, line in enumerate(quote.lines.all(), start=1):
        desc = line.description or (line.product.name if line.product_id else '')
        rows.append([str(i), desc, _money(line.quantity), _money(line.unit_price),
                     _money(line.line_total)])
    table = Table(rows, colWidths=[10 * mm, 80 * mm, 25 * mm, 27 * mm, 28 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTNAME', (0, 0), (-1, 0), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0ece3')),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, colors.HexColor('#8a7a5c')),
        ('LINEBELOW', (0, 1), (-1, -1), 0.3, colors.HexColor('#d9d2c4')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story += [table, Spacer(1, 6 * mm)]

    # Totals (dreta)
    totals = [
        ['Subtotal', _money(quote.subtotal)],
        ['Impostos', _money(quote.tax_amount)],
        ['Total', _money(quote.total)],
    ]
    tot_table = Table(totals, colWidths=[35 * mm, 30 * mm], hAlign='RIGHT')
    tot_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), FONT),
        ('FONTNAME', (0, -1), (-1, -1), FONT_BOLD),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 0.6, colors.HexColor('#8a7a5c')),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story += [tot_table]

    # Notes / condicions
    if quote.notes:
        story += [Spacer(1, 8 * mm), Paragraph('Condicions', label),
                  Paragraph(quote.notes.replace('\n', '<br/>'), small)]

    doc.build(story)
    return buf.getvalue()
