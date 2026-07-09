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
# Albarà v2 — franja per model (LITERAL del prototip validat).
CREAM = colors.HexColor('#FBF9F5')
MODEL_BAND = colors.HexColor('#F4EFE4')
DET_ROWLINE = colors.HexColor('#F2EFE9')
FETA_COL, PEND_COL = '#4a7a3a', '#b5892a'   # marcador ● feta (verd) / ● pendent (ambre)

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


# ── Capçalera de l'EMISSOR (TenantConfig) — compartida per tots els documents ────────────────
# Fi del hardcode: la identitat fiscal de l'emissor (legal_name/address/tax_id/email/phone) es
# llegeix de TenantConfig. Fallback NET: cada línia surt només si té contingut. El logo_file ja
# ve normalitzat a PNG ràster (accounts/logo.py), així que reportlab sempre el pot dibuixar.
_LOGO_MAX_H, _LOGO_MAX_W = 15 * mm, 45 * mm


def _emissor_oneliner(cfg):
    """Adreça, CP ciutat, país de l'emissor en una línia (omet buits). Mirall de _customer_oneliner."""
    if not cfg:
        return ''
    loc = ' '.join(x for x in [(cfg.postal_code or '').strip(), (cfg.city or '').strip()] if x)
    return ', '.join(x for x in [(cfg.address or '').strip(), loc, (cfg.country or '').strip()] if x)


def _brand_flowable(cfg, s, FS, FL):
    """Logo del tenant (logo_file, PNG ràster normalitzat) acotat a 15 mm d'alçada; si no n'hi ha o
    no es pot llegir, text de fallback 'Fhort Textile Tech'."""
    logo = getattr(cfg, 'logo_file', None)
    path = None
    if logo:  # ImageFieldFile buit → bool False → fallback de text.
        try:
            path = logo.path
        except Exception:  # noqa: BLE001 — storage sense path local
            path = None
    if path and os.path.isfile(path):
        try:
            img = Image(path)
            ratio = (img.imageWidth or 1) / (img.imageHeight or 1)
            h, w = _LOGO_MAX_H, _LOGO_MAX_H * ratio
            if w > _LOGO_MAX_W:  # logo molt ample → limita per amplada, recalcula alçada
                w, h = _LOGO_MAX_W, _LOGO_MAX_W / ratio
            img.drawWidth, img.drawHeight = w, h
            img.hAlign = 'LEFT'
            return img
        except Exception:  # noqa: BLE001 — imatge malmesa → text de fallback
            logger.warning("PDF logo: no s'ha pogut llegir logo_file (%s); fallback de text.", path)
    return Paragraph(f'<font name="{FS}" color="#B8860B">Fhort</font> '
                     f'<font name="{FL}" color="#888888">Textile Tech</font>', s('logo', size=14))


def _emissor_left(cfg, s, FS, FL):
    """Columna esquerra de la capçalera: marca + identitat fiscal de l'emissor (TenantConfig).
    Cada línia és opcional (fallback net). Compartida per generate_document_pdf i _delivery_note."""
    rows = [[_brand_flowable(cfg, s, FS, FL)], [Spacer(1, 2 * mm)]]
    if cfg:
        S_EN = s('en', font=FS, size=7.5)
        S_EM = s('em', size=7, color=GREY)   # línies fiscals secundàries, gris discret
        name = (getattr(cfg, 'legal_name', '') or getattr(cfg, 'nom_empresa', '') or '').strip()
        if name:
            rows.append([Paragraph(name, S_EN)])
        oneliner = _emissor_oneliner(cfg)
        if oneliner:
            rows.append([Paragraph(oneliner, S_EM)])
        tax_id = (getattr(cfg, 'tax_id', '') or '').strip()
        if tax_id:
            rows.append([Paragraph(f'NIF: {tax_id}', S_EM)])
        contact = ' · '.join(x for x in [(getattr(cfg, 'email', '') or '').strip(),
                                         (getattr(cfg, 'phone', '') or '').strip()] if x)
        if contact:
            rows.append([Paragraph(contact, S_EM)])
    return Table(rows, colWidths=[COL_LEFT_W], style=TableStyle(ZP))


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


def generate_document_pdf(quote, doc_title='Pressupost', show_payment=True):
    """Retorna els bytes del PDF d'un document comercial (`quote` = Quote, SalesOrder o
    DeliveryNote; layout idèntic). `doc_title` és el títol ('Pressupost'/'Comanda'/'Albarà').
    `show_payment=False` (albarà, B4c): SENSE bloc de venciments/condicions de pagament ni
    "Vàlid fins" (l'albarà no en porta); el peu queda amb les observacions/notes. Les línies
    DEDUCTION (import negatiu) es mostren amb signe − i color discret. Emissor = TenantConfig."""
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
    # Emissor = TenantConfig (marca + identitat fiscal), via helper compartit. Fi del hardcode.
    left = _emissor_left(cfg, s, FS, FL)

    meta_rows = [
        [Paragraph('Número', S_LABEL_R), Paragraph(quote.document_number or '—', SSM_R)],
        [Paragraph('Data', S_LABEL_R), Paragraph(_fmt_date(quote.issued_at), SSM_R)],
    ]
    if show_payment:  # "Vàlid fins" és propi d'oferta/comanda; un albarà no en porta.
        meta_rows.append([Paragraph('Vàlid fins', S_LABEL_R), Paragraph(_fmt_date(quote.valid_until), SSM_R)])
    meta = Table(meta_rows, colWidths=[COL_RIGHT_W - 30 * mm, 30 * mm], style=TableStyle(ZP))

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
    SR_NEG = s('rneg', align=TA_RIGHT, color=DGREY)  # línia negativa (deducció): color discret
    for line in quote.lines.all():
        name = (line.product.name if line.product_id else '') or ''
        desc = (line.description or '').strip()
        # Sense product (línia TASK/DEDUCTION/MANUAL d'albarà) → la descripció fa de títol.
        title = name or desc
        cell = [[Paragraph(title, s('ln', font=FR, size=8.5))]]
        if desc and desc != title:
            cell.append([Paragraph(desc, SSM_I)])
        neg = Decimal(line.line_total or 0) < 0
        num = SR_NEG if neg else SR
        rows.append([
            Table(cell, colWidths=[104 * mm], style=TableStyle(
                [('TOPPADDING', (0, 0), (-1, -1), 0.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 0.5),
                 ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])),
            Paragraph(_money(line.quantity), num),
            Paragraph(_money(line.unit_price), num),
            Paragraph(_money(line.line_total), num)])

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
    # Albarà (show_payment=False): sense forma/condicions de pagament ni venciments; només
    # observacions. Oferta/comanda: bloc esquerre (forma de pagament + notes) + bloc dret
    # (condicions + venciments materialitzats).
    peu_label = 'Forma de pagament' if show_payment else 'Observacions'
    peu_l_rows = [[Paragraph(peu_label, S_LABEL)]]
    if quote.notes:
        peu_l_rows.append([Paragraph(quote.notes.replace('\n', ' '), SSM_G)])
    # IBAN + notes de pagament de l'emissor (TenantConfig, P6) — fi del hardcode. Només al bloc de
    # pagament (oferta/comanda); l'albarà (show_payment=False) no en porta.
    if show_payment:
        iban = (getattr(cfg, 'iban', '') or '').strip()
        if iban:
            peu_l_rows.append([Paragraph(f'IBAN: {iban}', SSM_G)])
        pay_notes = (getattr(cfg, 'payment_notes', '') or '').strip()
        if pay_notes:
            peu_l_rows.append([Paragraph(pay_notes.replace('\n', ' '), SSM_G)])
    peu_l = Table(peu_l_rows, colWidths=[COL_LEFT_W - 6 * mm],
                  style=TableStyle(ZP + [('LINEABOVE', (0, 0), (0, 0), 0.5, LGREY)]))

    if not show_payment:
        story.append(Table([[peu_l]], colWidths=[COL_LEFT_W + COL_RIGHT_W],
            style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])))
    else:
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


# ═══════════════════════════════════════════════════════════════════════════════════════
# Albarà v2 — PDF compost per MODEL (prototip validat). Franja per model + detalls columnats
# + subtotal per model. Capçalera i client heretats del pressupost (mateixa família, geometria
# LITERAL). Només línies VISIBLES (visible=True); les amagades no surten ni compten. Cap dada
# interna (cost/temps/tècnic) al document.
# ═══════════════════════════════════════════════════════════════════════════════════════

DET_COLS = [78 * mm, 22 * mm, 16 * mm, 16 * mm, 20 * mm, 22 * mm]  # Descr·Data·Qt·Unitat·Preu·Import = 174
_UNIT_DEFAULT = 'ut'


def generate_delivery_note_pdf(delivery_note):
    """Retorna els bytes del PDF d'un albarà v2 compost per model. Agrupa les línies VISIBLES pel
    seu model FK; per cada model dibuixa una franja (fons cream) amb ref intern + nom + [ref client
    si difereix] + collection + temporada/any + data de lliurament (última tasca), els detalls
    columnats, els comentaris lliures (MANUAL) en cursiva i el subtotal del model. Els totals són
    els del document (calculats sobre línies visibles). SENSE venciments, SENSE cost intern."""
    F = _fonts()
    FL, FR, FS, FB = F[F_LIGHT], F[F_REG], F[F_SEMI], F[F_BOLD]
    cfg = _tenant_cfg()

    def s(name, font=FL, size=8.5, align=TA_LEFT, color=DARK, leading=None):
        return ParagraphStyle(name, fontName=font, fontSize=size, textColor=color,
                              alignment=align, leading=leading or size * 1.35)

    S = s('n')
    SB = s('b', font=FS)
    SR = s('r', align=TA_RIGHT)
    SRB = s('rb', font=FS, align=TA_RIGHT)
    SSM_G = s('smg', size=7.5, color=DGREY)
    SSM_I = s('smi', size=7.5, color=GREY)
    SSM_R = s('smr', size=7.5, align=TA_RIGHT)
    S_TITDOC = s('titdoc', font=FL, size=14, color=GOLD, align=TA_RIGHT)
    S_CLIENT = s('cli', font=FL, size=13)
    S_LABEL = s('lbl', size=7, color=GREY)
    S_LABEL_R = s('lblr', size=7, color=GREY, align=TA_RIGHT)
    S_MDELIV = s('mdeliv', size=7.5, color=DGREY, align=TA_RIGHT)

    buf = BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4,
                          leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
                          title=delivery_note.document_number or 'Albarà')
    frame = Frame(ML, MB, CW, PAGE_H - MT - MB,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame])])
    story = []

    # ═══ CAPÇALERA (heretada del pressupost validat) — emissor = TenantConfig, helper compartit ═══
    left = _emissor_left(cfg, s, FS, FL)

    meta = Table([
        [Paragraph('Número', S_LABEL_R), Paragraph(delivery_note.document_number or '—', SSM_R)],
        [Paragraph('Data', S_LABEL_R), Paragraph(_fmt_date(delivery_note.issued_at), SSM_R)],
    ], colWidths=[COL_RIGHT_W - 30 * mm, 30 * mm], style=TableStyle(ZP))
    right = Table([[Paragraph('Albarà', S_TITDOC)], [Spacer(1, 2 * mm)], [meta]],
                  colWidths=[COL_RIGHT_W], style=TableStyle(ZP))
    story.append(Table([[left, right]], colWidths=[COL_LEFT_W, COL_RIGHT_W],
        style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')] + ZP)))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGREY, spaceBefore=5 * mm, spaceAfter=4 * mm))

    # ═══ CLIENT ═══
    c = delivery_note.customer
    story.append(Paragraph('Per a:', S_LABEL))
    story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(c.rao_social or c.nom, S_CLIENT))
    oneliner = _customer_oneliner(c)
    if oneliner:
        story.append(Paragraph(oneliner, SSM_G))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGREY, spaceBefore=4 * mm, spaceAfter=5 * mm))

    # ═══ AGRUPACIÓ per model (només línies VISIBLES) ═══
    from collections import OrderedDict
    groups = OrderedDict()
    for ln in (delivery_note.lines.filter(visible=True)
               .select_related('model', 'model_task').order_by('position', 'id')):
        groups.setdefault(ln.model_id, []).append(ln)

    def _model_block(header_line, lines):
        m = header_line.model
        ref = (m.codi_intern if m else '') or '—'
        name = (m.nom_prenda if m else '') or ''
        refclient = None
        if m and m.codi_client and m.codi_client != m.codi_intern:
            refclient = m.codi_client
        collection = (m.collection if m else '') or ''
        season = ' '.join(x for x in [(m.temporada if m else ''), str(m.any) if (m and m.any) else ''] if x)
        # Detall = tot menys els comentaris (MANUAL, sota el bloc). Parcial = alguna tasca no-Done.
        det_lines = [l for l in lines if l.line_kind != 'MANUAL']
        comments = [l for l in lines if l.line_kind == 'MANUAL']
        partial = any(l.model_task_id and l.model_task and l.model_task.status != 'Done' for l in det_lines)
        # Data de lliurament = última finished_at de les tasques incloses.
        fdates = [l.model_task.finished_at for l in det_lines if l.model_task_id and l.model_task and l.model_task.finished_at]
        deliver = _fmt_date(max(fdates)) if fdates else '—'

        els = []
        # --- FRANJA DE MODEL (ample complet) ---
        meta_bits = []
        if refclient:
            meta_bits.append(f'ref. client {refclient}')
        if collection:
            meta_bits.append(collection)
        if season:
            meta_bits.append(season)
        meta_txt = '  ·  '.join(meta_bits)
        band = Table([[
            Paragraph(f'<font name="{FS}" color="#B8860B">{ref}</font>&nbsp;&nbsp;'
                      f'<font name="{FS}" color="#1A1A1A">{name}</font>&nbsp;&nbsp;'
                      f'<font name="{FL}" color="#888888" size="7.5">{meta_txt}</font>', s('band', size=10)),
            Paragraph(f'Lliurament · {deliver}', S_MDELIV),
        ]], colWidths=[CW * 0.68, CW * 0.32], style=TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), MODEL_BAND),
            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (0, 0), 8), ('RIGHTPADDING', (-1, 0), (-1, 0), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        els.append(band)
        # --- DETALLS COLUMNATS ---
        head = [Paragraph('Descripció', s('dh', font=FS, size=7, color=GREY)),
                Paragraph('Data', s('dh2', font=FS, size=7, color=GREY)),
                Paragraph('Qt.', s('dh3', font=FS, size=7, color=GREY, align=TA_RIGHT)),
                Paragraph('Unitat', s('dh4', font=FS, size=7, color=GREY)),
                Paragraph('Preu', s('dh5', font=FS, size=7, color=GREY, align=TA_RIGHT)),
                Paragraph('Import', s('dh6', font=FS, size=7, color=GREY, align=TA_RIGHT))]
        rows = [head]
        for l in det_lines:
            desc = (l.description or '').strip() or (l.product.name if l.product_id else '—')
            if partial and l.model_task_id:
                done = l.model_task and l.model_task.status == 'Done'
                col = FETA_COL if done else PEND_COL
                desc = f'{desc}  <font color="{col}" size="6.5">● {"feta" if done else "pendent"}</font>'
            date = _fmt_date(l.model_task.finished_at) if (l.model_task_id and l.model_task and l.model_task.finished_at) else '—'
            rows.append([
                Paragraph(desc, s('ld', size=8)),
                Paragraph(date, SSM_I),
                Paragraph(_money(l.quantity), s('lq', size=8, align=TA_RIGHT)),
                Paragraph(_UNIT_DEFAULT, s('lu', size=8)),
                Paragraph(_money(l.unit_price), s('lp', size=8, align=TA_RIGHT)),
                Paragraph(f'{_money(l.line_total)} €', s('li', size=8, align=TA_RIGHT)),
            ])
        els.append(Table(rows, colWidths=DET_COLS, style=TableStyle([
            ('LINEBELOW', (0, 0), (-1, 0), 0.4, LGREY),
            ('LINEBELOW', (0, 1), (-1, -1), 0.25, DET_ROWLINE),
            ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (0, -1), 8), ('RIGHTPADDING', (-1, 0), (-1, -1), 8),
            ('LEFTPADDING', (1, 0), (-1, -1), 2), ('RIGHTPADDING', (0, 0), (-2, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ])))
        # --- COMENTARIS LLIURES (MANUAL) del model, cursiva gris sota el bloc ---
        for cm in comments:
            els.append(Table([[Paragraph(f'<i>{(cm.description or "").strip()}</i>',
                s('cmt', size=7.5, color=GREY))]], colWidths=[CW], style=TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 8), ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2)])))
        # --- SUBTOTAL MODEL ---
        subtotal = sum((Decimal(l.line_total or 0) for l in det_lines), Decimal('0'))
        els.append(Table([[Paragraph('Subtotal model', s('stl', size=7.5, color=DGREY, align=TA_RIGHT)),
                           Paragraph(f'{_money(subtotal)} €', s('stv', font=FS, size=9, align=TA_RIGHT))]],
            colWidths=[CW - 30 * mm, 30 * mm], style=TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (-1, 0), (-1, 0), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')])))
        return els

    first = True
    for _mid, lines in groups.items():
        if not first:
            story.append(HRFlowable(width='100%', thickness=0.3, color=LGREY, spaceBefore=6 * mm, spaceAfter=6 * mm))
        first = False
        for el in _model_block(lines[0], lines):
            story.append(el)

    story.append(Spacer(1, 8 * mm))

    # ═══ RESUM (sense venciments; totals sobre línies visibles = els del document) ═══
    pct = _tax_pct(delivery_note.subtotal, delivery_note.tax_amount)
    story.append(Table([
        ['', Paragraph('Base imposable', S), Paragraph(f'{_money(delivery_note.subtotal)} €', SR)],
        ['', Paragraph(f'I.V.A. {pct}%', S), Paragraph(f'{_money(delivery_note.tax_amount)} €', SR)],
        ['', Paragraph('Import total', SB), Paragraph(f'{_money(delivery_note.total)} €', SRB)],
    ], colWidths=[104 * mm, 44 * mm, 26 * mm], style=TableStyle([
        ('LINEABOVE', (1, 2), (2, 2), 0.5, LGREY),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])))

    # ═══ OBSERVACIONS (notes de l'albarà; sense pagament/venciments) ═══
    if (delivery_note.notes or '').strip():
        story.append(Spacer(1, 8 * mm))
        story.append(Table([[Paragraph('Observacions', S_LABEL)],
                            [Paragraph(delivery_note.notes.replace('\n', ' '), SSM_G)]],
            colWidths=[CW], style=TableStyle(ZP + [('LINEABOVE', (0, 0), (0, 0), 0.5, LGREY)])))

    doc.build(story)
    return buf.getvalue()
