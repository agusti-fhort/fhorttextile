"""commerce/pdf_service.py — PDF d'una oferta (disseny validat, B2-PDF-v2, decisió R7).

reportlab.platypus (taula real vectorial, NO el raster Konva). Disseny aprovat amb l'Agus:
tipografia Montserrat carregada de `settings.PDF_FONTS_DIR`; si no hi és, fallback a Helvetica
amb WARNING (mai 500). Emissor = TenantConfig; client = camps fiscals de Customer (B1). Etiquetes
en català (naming EN només a BD/codi). doc_type al PDF hardcoded "Pressupost" (i18n = TODO).
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
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)

logger = logging.getLogger(__name__)

# Paleta del disseny validat.
GOLD = colors.HexColor('#B8860B')
GREY = colors.HexColor('#888888')
LGREY = colors.HexColor('#DDDDDD')
DARK = colors.HexColor('#1A1A1A')
DGREY = colors.HexColor('#555555')
ROWLINE = colors.HexColor('#F0F0F0')

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


def _ps(name, font, size, color, align=TA_LEFT, leading=None):
    return ParagraphStyle(name, fontName=font, fontSize=size, textColor=color,
                          alignment=align, leading=leading or size * 1.28)


def _tenant_cfg():
    try:
        from fhort.accounts.models import TenantConfig
        return TenantConfig.objects.first()
    except Exception:  # noqa: BLE001
        return None


def _brand_flowables(cfg, F):
    """Bloc de marca: logo del tenant si logo_file té valor i el fitxer existeix; si no, text."""
    out = []
    logo = getattr(cfg, 'logo_file', None)
    logo_path = None
    if logo:
        try:
            logo_path = logo.path
        except Exception:  # noqa: BLE001 — storage sense path local
            logo_path = None
    if logo_path and os.path.isfile(logo_path):
        try:
            img = Image(logo_path)
            w = 35 * mm
            img.drawWidth = w
            img.drawHeight = w * (img.imageHeight / img.imageWidth)
            img.hAlign = 'LEFT'
            out.append(img)
        except Exception:  # noqa: BLE001 — imatge malmesa → text de fallback
            logo_path = None
    if not out:
        out.append(Paragraph(
            f'<font name="{F[F_SEMI]}" size="14" color="#B8860B">Fhort</font> '
            f'<font name="{F[F_LIGHT]}" size="14" color="#888888">Textile Tech</font>',
            _ps('brand', F[F_SEMI], 14, DARK)))
    # Dades de l'emissor (TenantConfig només té nom_empresa; adreça/NIF/email = placeholder futur).
    nom = (getattr(cfg, 'nom_empresa', '') or '').strip()
    detail = []
    if nom:
        detail.append(f'<font name="{F[F_SEMI]}" size="7.5" color="#1A1A1A">{nom}</font>')
    # TODO B-fi: adreça/NIF/email de l'emissor quan TenantConfig els tingui (avui no existeixen).
    if detail:
        out.append(Spacer(1, 2 * mm))
        out.append(Paragraph('<br/>'.join(detail), _ps('emit', F[F_LIGHT], 7.5, GREY, leading=10)))
    return out


def _meta_flowable(quote, F):
    """Taula Número / Data / Vàlid fins (label gris + valor fosc), alineada a la dreta."""
    def row(label, value):
        return [Paragraph(label, _ps('ml', F[F_REG], 7, GREY, TA_LEFT)),
                Paragraph(value or '—', _ps('mv', F[F_LIGHT], 8.5, DARK, TA_LEFT))]
    t = Table([
        row('Número', quote.document_number),
        row('Data', quote.issued_at.isoformat() if quote.issued_at else None),
        row('Vàlid fins', quote.valid_until.isoformat() if quote.valid_until else None),
    ], colWidths=[22 * mm, 30 * mm], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


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
    F = _fonts()
    cfg = _tenant_cfg()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
        title=quote.document_number or 'Pressupost',
    )
    story = []

    # 1. CAPÇALERA — marca+emissor (esq.) · títol + meta (columna dreta, continguts a l'esquerra)
    right = [Paragraph('Pressupost', _ps('title', F[F_LIGHT], 14, GOLD, TA_LEFT)),
             Spacer(1, 3 * mm), _meta_flowable(quote, F)]
    head = Table([[_brand_flowables(cfg, F), right]], colWidths=[85 * mm, 89 * mm])
    head.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(head)

    # 2. HR
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGREY, spaceBefore=4 * mm, spaceAfter=4 * mm))

    # 3. BLOC CLIENT — dins un contenidor amb LEFTPADDING 5mm perquè el bloc s'alineï
    # visualment amb la columna "Descripció" de la taula de línies (també indentada 5mm).
    c = quote.customer
    client_block = [Paragraph('Per a:', _ps('forp', F[F_REG], 7, GREY)),
                    Paragraph(c.rao_social or c.nom, _ps('cust', F[F_LIGHT], 13, DARK, leading=15))]
    oneliner = _customer_oneliner(c)
    if oneliner:
        client_block.append(Paragraph(oneliner, _ps('custl', F[F_LIGHT], 7.5, GREY, leading=10)))
    client_tbl = Table([[client_block]], colWidths=[174 * mm])
    client_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 5 * mm), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(client_tbl)

    # 4. HR
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGREY, spaceBefore=4 * mm, spaceAfter=4 * mm))

    # 5. TAULA DE LÍNIES
    hstyle = _ps('lh', F[F_SEMI], 8, GREY)
    rows = [[Paragraph('Descripció', hstyle),
             Paragraph('Unitats', _ps('lhr', F[F_SEMI], 8, GREY, TA_RIGHT)),
             Paragraph('Preu unit.', _ps('lhr2', F[F_SEMI], 8, GREY, TA_RIGHT)),
             Paragraph('Import', _ps('lhr3', F[F_SEMI], 8, GREY, TA_RIGHT))]]
    for line in quote.lines.all():
        name = (line.product.name if line.product_id else '') or ''
        desc = (line.description or '').strip()
        cell = f'<font name="{F[F_REG]}" size="8.5" color="#1A1A1A">{name}</font>'
        if desc and desc != name:
            cell += f'<br/><font name="{F[F_LIGHT]}" size="7.5" color="#888888">{desc}</font>'
        rows.append([
            Paragraph(cell, _ps('ld', F[F_REG], 8.5, DARK, leading=10)),
            Paragraph(_money(line.quantity), _ps('lq', F[F_LIGHT], 8.5, DARK, TA_RIGHT)),
            Paragraph(_money(line.unit_price), _ps('lp', F[F_LIGHT], 8.5, DARK, TA_RIGHT)),
            Paragraph(_money(line.line_total), _ps('lt', F[F_LIGHT], 8.5, DARK, TA_RIGHT)),
        ])
    lines_table = Table(rows, colWidths=[108 * mm, 20 * mm, 24 * mm, 22 * mm], repeatRows=1)
    lstyle = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        # Col "Descripció" indentada 5mm (alinea amb el bloc client); numèriques a la dreta.
        ('LEFTPADDING', (0, 0), (0, -1), 5 * mm),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, LGREY),
    ]
    for i in range(1, len(rows)):
        lstyle.append(('LINEBELOW', (0, i), (-1, i), 0.3, ROWLINE))
    lines_table.setStyle(TableStyle(lstyle))
    story += [lines_table, Spacer(1, 5 * mm)]

    # 6. TOTALS
    pct = _tax_pct(quote.subtotal, quote.tax_amount)
    lbl = _ps('tl', F[F_REG], 8.5, DGREY, TA_RIGHT)
    val = _ps('tv', F[F_LIGHT], 8.5, DARK, TA_RIGHT)
    lblb = _ps('tlb', F[F_SEMI], 9.5, DARK, TA_RIGHT)
    valb = _ps('tvb', F[F_SEMI], 9.5, DARK, TA_RIGHT)
    totals = Table([
        ['', Paragraph('Base imposable', lbl), Paragraph(_money(quote.subtotal), val)],
        ['', Paragraph(f'I.V.A. {pct}%', lbl), Paragraph(_money(quote.tax_amount), val)],
        ['', Paragraph('Import total', lblb), Paragraph(_money(quote.total), valb)],
    ], colWidths=[80 * mm, 52 * mm, 42 * mm])
    totals.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LINEABOVE', (1, 2), (-1, 2), 0.5, LGREY),
    ]))
    story += [totals, Spacer(1, 10 * mm)]

    # 7. PEU — forma de pagament (esq.) · condicions (dreta)
    foot_l = [Paragraph('Forma de pagament', _ps('fl', F[F_REG], 7, GREY))]
    if quote.notes:
        foot_l.append(Paragraph(quote.notes.replace('\n', '<br/>'), _ps('fln', F[F_LIGHT], 7.5, GREY, leading=10)))
    # TODO B-fi: dades bancàries (IBAN) com a camp propi de TenantConfig (avui no existeix).
    foot_r = [Paragraph('Condicions de pagament', _ps('fr', F[F_REG], 7, GREY)),
              # TODO B-fi: terminis com a camp propi (avui v1 hardcoded).
              Paragraph('50% a l\'inici · 50% a l\'entrega', _ps('frv', F[F_LIGHT], 7.5, DGREY, leading=10))]
    foot = Table([[foot_l, foot_r]], colWidths=[90 * mm, 84 * mm])
    foot.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, GREY),
    ]))
    story.append(foot)

    doc.build(story)
    return buf.getvalue()
