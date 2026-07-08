"""commerce/pdf_service.py — PDF d'una oferta (disseny validat, B2-PDF-v7, decisió R7).

reportlab.platypus (taula real vectorial, NO el raster Konva). Disseny aprovat amb l'Agus.

FIX D'ALINEACIÓ (v7): SimpleDocTemplate crea el Frame amb leftPadding/rightPadding=6pt →
paràgrafs i HRFlowable respectaven el padding (~2mm d'indent) mentre les Table de 174mm
(més amples que l'espai útil) es centraven i el desbordaven → dos orígens X diferents.
Solució: BaseDocTemplate + Frame amb padding 0. Un sol origen (el leftMargin) per a tot.

Tipografia Montserrat de `settings.PDF_FONTS_DIR` (fallback Helvetica + WARNING, mai 500).
Emissor = TenantConfig; client = quote.customer; línies/totals/dates = quote. Etiquetes en
català (naming EN només a BD/codi). doc_type al PDF hardcoded "Pressupost" (i18n = TODO).
"""
import logging
import os
from decimal import Decimal
from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)

logger = logging.getLogger(__name__)

# Paleta del disseny validat.
GOLD = colors.HexColor('#B8860B')
GREY = colors.HexColor('#888888')
LGREY = colors.HexColor('#DDDDDD')
DARK = colors.HexColor('#1A1A1A')
DGREY = colors.HexColor('#555555')
ROWLINE = colors.HexColor('#F0F0F0')

# Geometria (LITERAL del fitxer de referència v7). Un sol origen X per a tot.
PAGE_W, PAGE_H = A4
ML = MR = 18 * mm
MT, MB = 14 * mm, 18 * mm
CW = PAGE_W - ML - MR            # 174mm — TOT fa servir aquesta amplada exacta
X_B = 88 * mm                    # línia vertical del bloc dret
COL_LEFT_W, COL_RIGHT_W = X_B, CW - X_B

# Paddings zero reutilitzables per a les taules interiors.
ZP = [('TOPPADDING', (0, 0), (-1, -1), 1.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.5),
      ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]

# Noms lògics de font usats al layout → fitxer TTF esperat i fallback Helvetica.
F_LIGHT, F_REG, F_SEMI, F_BOLD = 'MS-Light', 'MS', 'MS-SemiBold', 'MS-Bold'
_FONT_FILES = {
    F_LIGHT: 'Montserrat-Light.ttf',
    F_REG: 'Montserrat-Regular.ttf',
    F_SEMI: 'Montserrat-SemiBold.ttf',
    F_BOLD: 'Montserrat-Bold.ttf',
}
_FALLBACK = {F_LIGHT: 'Helvetica', F_REG: 'Helvetica', F_SEMI: 'Helvetica-Bold', F_BOLD: 'Helvetica-Bold'}

_fonts_cache = None  # {nom_lògic: nom_registrat} — resolt un sol cop per procés


def _fonts():
    """Registra Montserrat un sol cop; retorna el mapa nom_lògic→nom_real (fallback Helvetica)."""
    global _fonts_cache
    if _fonts_cache is not None:
        return _fonts_cache
    fonts_dir = getattr(settings, 'PDF_FONTS_DIR', '') or ''
    resolved, missing = {}, []
    for logic, fname in _FONT_FILES.items():
        path = os.path.join(fonts_dir, fname)
        if os.path.isfile(path):
            try:
                pdfmetrics.registerFont(TTFont(logic, path))
                resolved[logic] = logic
            except Exception as e:  # noqa: BLE001 — mai petar la request per una font
                logger.warning("PDF fonts: fallada registrant %s (%s); fallback Helvetica", fname, e)
                resolved[logic] = _FALLBACK[logic]; missing.append(fname)
        else:
            resolved[logic] = _FALLBACK[logic]; missing.append(fname)
    if missing:
        logger.warning("PDF fonts: Montserrat no trobat (%s) a %s; fallback a Helvetica.",
                       ', '.join(missing), fonts_dir)
    _fonts_cache = resolved
    return resolved


def _money(value):
    """Format monetari 2 decimals amb coma decimal (convenció EU)."""
    v = Decimal(value or 0).quantize(Decimal('0.01'))
    return f'{v:,.2f}'.replace(',', '§').replace('.', ',').replace('§', '.')


def _fmt_date(d):
    """Data en format DD/MM/YYYY, o '—' si no n'hi ha."""
    return d.strftime('%d/%m/%Y') if d else '—'


def _tenant_cfg():
    try:
        from fhort.accounts.models import TenantConfig
        return TenantConfig.objects.first()
    except Exception:  # noqa: BLE001
        return None


def _customer_oneliner(c):
    """Adreça · NIF del client en una sola línia (omet buits)."""
    parts = []
    addr = ', '.join(x for x in [c.adreca_linia1, c.adreca_linia2,
                                 ' '.join(y for y in [c.codi_postal, c.ciutat] if y), c.pais] if x)
    if addr:
        parts.append(addr)
    if c.nif:
        parts.append(f'NIF: {c.nif}')
    return ' · '.join(parts)


def _tax_pct(subtotal, tax_amount):
    """% d'IVA derivat de subtotal/impostos; 21 per defecte si no es pot inferir."""
    s = Decimal(subtotal or 0)
    tx = Decimal(tax_amount or 0)
    if s > 0 and tx > 0:
        return int((tx / s * 100).quantize(Decimal('1')))
    return 21


def generate_quote_pdf(quote):
    """Retorna els bytes del PDF de l'oferta `quote` (disseny Montserrat; fallback Helvetica)."""
    return generate_document_pdf(quote, doc_title='Pressupost')


def generate_document_pdf(quote, doc_title='Pressupost'):
    """Retorna els bytes del PDF d'un document comercial (`quote` = Quote o SalesOrder; layout
    idèntic). `doc_title` és el títol del document ('Pressupost' per oferta, 'Comanda' per
    comanda). Emissor = TenantConfig; client/línies/totals/venciments = document."""
    F = _fonts()
    FL, FR, FS, FB = F[F_LIGHT], F[F_REG], F[F_SEMI], F[F_BOLD]
    cfg = _tenant_cfg()

    def s(name, font=FL, size=8.5, align=TA_LEFT, color=DARK, leading=None):
        return ParagraphStyle(name, fontName=font, fontSize=size, textColor=color,
                              alignment=align, leading=leading or size * 1.35)

    # Estils (geometria/mides LITERALS de la referència; fonts mapejades pel fallback).
    S = s('n')
    SB = s('b', font=FS)
    SSM_G = s('smg', size=7.5, color=DGREY)
    SSM_I = s('smi', size=7.5, color=GREY)
    SR = s('r', align=TA_RIGHT)
    SRB = s('rb', font=FS, align=TA_RIGHT)
    S_TITDOC = s('titdoc', font=FL, size=14, color=GOLD, align=TA_RIGHT)
    S_CLIENT = s('cli', font=FL, size=13)
    S_LABEL = s('lbl', size=7, color=GREY)
    S_LABEL_R = s('lblr', size=7, color=GREY, align=TA_RIGHT)
    SSM_R = s('smr', size=7.5, align=TA_RIGHT)

    # ── BaseDocTemplate amb Frame de padding 0 (un sol origen X per a tot) ──
    buf = BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4,
                          leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
                          title=quote.document_number or doc_title)
    frame = Frame(ML, MB, CW, PAGE_H - MT - MB,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame])])

    story = []

    # ═══ CAPÇALERA ═══
    # Marca: logo del tenant (logo_file) si existeix; si no, text de fallback.
    def _brand_flowable():
        logo = getattr(cfg, 'logo_file', None)
        path = None
        if logo:
            try:
                path = logo.path
            except Exception:  # noqa: BLE001 — storage sense path local
                path = None
        if path and os.path.isfile(path):
            try:
                img = Image(path)
                w = 35 * mm
                img.drawWidth = w
                img.drawHeight = w * (img.imageHeight / img.imageWidth)
                img.hAlign = 'LEFT'
                return img
            except Exception:  # noqa: BLE001 — imatge malmesa → text de fallback
                pass
        return Paragraph(f'<font name="{FS}" color="#B8860B">Fhort</font> '
                         f'<font name="{FL}" color="#888888">Textile Tech</font>',
                         s('logo', size=14))

    left_rows = [[_brand_flowable()], [Spacer(1, 2 * mm)]]
    nom_emissor = (getattr(cfg, 'nom_empresa', '') or '').strip()
    if nom_emissor:
        left_rows.append([Paragraph(nom_emissor, s('en', font=FS, size=7.5))])
    # TODO B-fi: adreça/NIF/email de l'emissor quan TenantConfig els tingui (avui no existeixen).
    left = Table(left_rows, colWidths=[COL_LEFT_W], style=TableStyle(ZP))

    meta = Table([
        [Paragraph('Número', S_LABEL_R), Paragraph(quote.document_number or '—', SSM_R)],
        [Paragraph('Data', S_LABEL_R), Paragraph(_fmt_date(quote.issued_at), SSM_R)],
        [Paragraph('Vàlid fins', S_LABEL_R), Paragraph(_fmt_date(quote.valid_until), SSM_R)],
    ], colWidths=[COL_RIGHT_W - 30 * mm, 30 * mm], style=TableStyle(ZP))

    right = Table([
        [Paragraph(doc_title, S_TITDOC)],
        [Spacer(1, 2 * mm)],
        [meta],
    ], colWidths=[COL_RIGHT_W], style=TableStyle(ZP))

    story.append(Table([[left, right]], colWidths=[COL_LEFT_W, COL_RIGHT_W],
        style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])))

    story.append(HRFlowable(width='100%', thickness=0.5, color=LGREY,
                            spaceBefore=5 * mm, spaceAfter=4 * mm))

    # ═══ CLIENT ═══
    c = quote.customer
    story.append(Paragraph('Per a:', S_LABEL))
    story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(c.rao_social or c.nom, S_CLIENT))
    oneliner = _customer_oneliner(c)
    if oneliner:
        story.append(Paragraph(oneliner, SSM_G))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGREY,
                            spaceBefore=4 * mm, spaceAfter=5 * mm))

    # ═══ LÍNIES ═══
    HDR = s('hdr', font=FS, size=8, color=GREY)
    HDR_R = s('hdrr', font=FS, size=8, color=GREY, align=TA_RIGHT)
    rows = [[Paragraph('Descripció', HDR), Paragraph('Unitats', HDR_R),
             Paragraph('Preu unit.', HDR_R), Paragraph('Import', HDR_R)]]
    for line in quote.lines.all():
        name = (line.product.name if line.product_id else '') or ''
        desc = (line.description or '').strip()
        cell = [[Paragraph(name, s('ln', font=FR, size=8.5))]]
        if desc and desc != name:
            cell.append([Paragraph(desc, SSM_I)])
        rows.append([
            Table(cell, colWidths=[104 * mm], style=TableStyle(
                [('TOPPADDING', (0, 0), (-1, -1), 0.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
                 ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])),
            Paragraph(_money(line.quantity), SR),
            Paragraph(_money(line.unit_price), SR),
            Paragraph(_money(line.line_total), SR)])

    story.append(Table(rows, colWidths=[104 * mm, 22 * mm, 26 * mm, 22 * mm],
        style=TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, LGREY),
            ('LINEBELOW', (0, 1), (-1, -1), 0.3, ROWLINE),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])))
    story.append(Spacer(1, 6 * mm))

    # ═══ TOTALS ═══
    pct = _tax_pct(quote.subtotal, quote.tax_amount)
    story.append(Table([
        ['', Paragraph('Base imposable', S), Paragraph(_money(quote.subtotal), SR)],
        ['', Paragraph(f'I.V.A. {pct}%', S), Paragraph(_money(quote.tax_amount), SR)],
        ['', Paragraph('Import total', SB), Paragraph(_money(quote.total), SRB)],
    ], colWidths=[104 * mm, 44 * mm, 26 * mm], style=TableStyle([
        ('LINEABOVE', (1, 2), (2, 2), 0.5, LGREY),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])))
    story.append(Spacer(1, 10 * mm))

    # ═══ PEU ═══
    peu_l_rows = [[Paragraph('Forma de pagament', S_LABEL)]]
    if quote.notes:
        peu_l_rows.append([Paragraph(quote.notes.replace('\n', ' '), SSM_G)])
    # TODO B-fi: IBAN/dades bancàries com a camp propi de TenantConfig (avui no existeix).
    peu_l = Table(peu_l_rows, colWidths=[COL_LEFT_W - 6 * mm],
                  style=TableStyle(ZP + [('LINEABOVE', (0, 0), (0, 0), 0.5, LGREY)]))

    # Terminis 50/50 derivats del total (v1; TODO camp propi de condicions de pagament).
    terms = quote.payment_terms or (quote.customer.payment_terms if quote.customer_id else None)
    due = list(quote.due_dates.all())
    peu_r_rows = [[Paragraph('Condicions de pagament', S_LABEL), '']]
    if terms:
        peu_r_rows.append([Paragraph(terms.name, SSM_I), ''])
    for dd in due:
        peu_r_rows.append([Paragraph(f'{dd.percentage:g}% · {_fmt_date(dd.due_date)}', SSM_G),
                           Paragraph(_money(dd.amount), SR)])
    if not due and not terms:
        peu_r_rows.append([Paragraph('—', SSM_G), ''])
    peu_r = Table(peu_r_rows, colWidths=[COL_RIGHT_W * 0.6, COL_RIGHT_W * 0.4],
                  style=TableStyle(ZP + [('LINEABOVE', (0, 0), (1, 0), 0.5, LGREY),
                                         ('SPAN', (0, 0), (1, 0))]))

    story.append(Table([[peu_l, peu_r]], colWidths=[COL_LEFT_W, COL_RIGHT_W],
        style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])))

    doc.build(story)
    return buf.getvalue()
