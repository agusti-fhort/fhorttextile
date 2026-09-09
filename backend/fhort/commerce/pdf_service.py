"""commerce/pdf_service.py — PDF d'una oferta (disseny validat, B2-PDF-v7, decisió R7).

reportlab.platypus (taula real vectorial, NO el raster Konva). Disseny aprovat amb l'Agus.

FIX D'ALINEACIÓ (v7): SimpleDocTemplate crea el Frame amb leftPadding/rightPadding=6pt →
paràgrafs i HRFlowable respectaven el padding (~2mm d'indent) mentre les Table de 174mm
(més amples que l'espai útil) es centraven i el desbordaven → dos orígens X diferents.
Solució: BaseDocTemplate + Frame amb padding 0. Un sol origen (el leftMargin) per a tot.

Tipografia Montserrat de `settings.PDF_FONTS_DIR` (fallback Helvetica + WARNING, mai 500).
Emissor = TenantConfig; client = quote.customer; línies/totals/dates = quote.

IDIOMA (decisió Patró C 2026-07-27): els literals del document viuen al diccionari
`_PDF_STRINGS` d'aquest fitxer i se serveixen per `t(lang, key)`. És una v1 CONSCIENT: no
és gettext. El backend no té cap canonada i18n (ni LocaleMiddleware, ni LOCALE_PATHS, ni
locale/, ni .po) i muntar-la per a una sola superfície seria arquitectura per endavant.
**Promoure a gettext quan hi hagi una 2a superfície backend amb i18n** — llavors el
diccionari es buida cap als .po i `t()` esdevé un àlies de gettext, sense tocar cap crida.

Llei del fitxer: cap literal de cara al lector fora de `_PDF_STRINGS`. Els títols dels
documents també hi entren; les views passen la CLAU ('doc_quote'…), mai el text.
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
    Table, TableStyle, Paragraph, Spacer, Image, HRFlowable, Flowable,
)

logger = logging.getLogger(__name__)

# Paleta del disseny validat (capçalera — Quote/SalesOrder/Albarà, NO tocada pel bloc A).
GOLD = colors.HexColor('#B8860B')
GREY = colors.HexColor('#888888')
LGREY = colors.HexColor('#DDDDDD')
DARK = colors.HexColor('#1A1A1A')
DGREY = colors.HexColor('#555555')
ROWLINE = colors.HexColor('#F0F0F0')

# Albarà v2 · COS (maqueta §3, `ops/maquetes/maqueta_albara_v1.html`) — tokens EXACTES de la
# maqueta (--text-main/--text-soft/--line). Paleta pròpia i separada de la de dalt: la
# capçalera hereta el disseny del pressupost validat i aquest bloc no la toca.
DN_TEXT_MAIN = colors.HexColor('#1D1D1B')
DN_TEXT_SOFT = colors.HexColor('#6E6A64')
DN_LINE = colors.HexColor('#E8E5E0')

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
# Albarà v2 · COS (maqueta §3) — IBM Plex Mono, mai la capçalera. Fallback Courier i no
# Helvetica: és l'únic dels dos que és monospace, com l'original (`--mono` de la maqueta).
F_MONO, F_MONO_SEMI = 'IBMPlexMono', 'IBMPlexMono-SemiBold'
_FONT_FILES = {
    F_LIGHT: 'Montserrat-Light.ttf',
    F_REG: 'Montserrat-Regular.ttf',
    F_SEMI: 'Montserrat-SemiBold.ttf',
    F_BOLD: 'Montserrat-Bold.ttf',
    F_MONO: 'IBMPlexMono-Regular.ttf',
    F_MONO_SEMI: 'IBMPlexMono-SemiBold.ttf',
}
_FALLBACK = {
    F_LIGHT: 'Helvetica', F_REG: 'Helvetica', F_SEMI: 'Helvetica-Bold', F_BOLD: 'Helvetica-Bold',
    F_MONO: 'Courier', F_MONO_SEMI: 'Courier-Bold',
}

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


# ── i18n dels literals del document (v1 diccionari; veure capçalera) ────────────────────────
# Els idiomes són els mateixos que tasks.Customer.LANGUAGE_CHOICES. 'ca' és la llengua base:
# és l'idioma en què es va dissenyar el document i el fallback de tota clau que falti.
PDF_LANGS = ('ca', 'en', 'es')
PDF_LANG_FALLBACK = 'ca'

_PDF_STRINGS = {
    'ca': {
        'doc_quote': 'Pressupost', 'doc_order': 'Comanda', 'doc_delivery_note': 'Albarà',
        'number': 'Número', 'date': 'Data', 'valid_until': 'Vàlid fins',
        'for': 'Per a:', 'tax_id': 'NIF', 'iban': 'IBAN',
        'description': 'Descripció', 'units': 'Unitats', 'unit_price': 'Preu unit.',
        'amount': 'Import',
        'taxable_base': 'Base imposable', 'vat': 'I.V.A.', 'total_amount': 'Import total',
        'payment_method': 'Forma de pagament',
        'payment_terms': 'Condicions de pagament',

        # BLOC A · maqueta §3.
        'dn_quote': 'Pressupost', 'dn_direct_order': 'Encàrrec directe sense pressupost', 'dn_round': 'Ronda', 'dn_comments': 'Comentaris', 'dn_qty': 'Qtt',
        'dn_extra': 'Extra', 'dn_deduction': 'Deducció', 'dn_expense': 'Despesa',

    },
    'en': {
        'doc_quote': 'Quotation', 'doc_order': 'Order', 'doc_delivery_note': 'Delivery note',
        'number': 'Number', 'date': 'Date', 'valid_until': 'Valid until',
        'for': 'For:', 'tax_id': 'Tax ID', 'iban': 'IBAN',
        'description': 'Description', 'units': 'Units', 'unit_price': 'Unit price',
        'amount': 'Amount',
        'taxable_base': 'Taxable base', 'vat': 'VAT', 'total_amount': 'Total amount',
        'payment_method': 'Payment method',
        'payment_terms': 'Payment terms',

        # BLOC A · maqueta §3.
        'dn_quote': 'Quote', 'dn_direct_order': 'Direct order, no quote', 'dn_round': 'Round', 'dn_comments': 'Comments', 'dn_qty': 'Qty',
        'dn_extra': 'Extra', 'dn_deduction': 'Deduction', 'dn_expense': 'Expense',

    },
    'es': {
        'doc_quote': 'Presupuesto', 'doc_order': 'Pedido', 'doc_delivery_note': 'Albarán',
        'number': 'Número', 'date': 'Fecha', 'valid_until': 'Válido hasta',
        'for': 'Para:', 'tax_id': 'NIF', 'iban': 'IBAN',
        'description': 'Descripción', 'units': 'Unidades', 'unit_price': 'Precio unit.',
        'amount': 'Importe',
        'taxable_base': 'Base imponible', 'vat': 'I.V.A.', 'total_amount': 'Importe total',
        'payment_method': 'Forma de pago',
        'payment_terms': 'Condiciones de pago',

        # BLOC A · maqueta §3.
        'dn_quote': 'Presupuesto', 'dn_direct_order': 'Encargo directo sin presupuesto', 'dn_round': 'Vuelta', 'dn_comments': 'Comentarios', 'dn_qty': 'Ctd',
        'dn_extra': 'Extra', 'dn_deduction': 'Deducción', 'dn_expense': 'Gasto',

    },
}


def t(lang, key):
    """Literal del document per (idioma, clau). Doble fallback: idioma desconegut → 'ca';
    clau absent en aquell idioma → la de 'ca'. Mai peta i mai retorna buit: un PDF no es
    trenca per una traducció que falta. Únic accés als literals — cap ternari inline."""
    table = _PDF_STRINGS.get(lang) or _PDF_STRINGS[PDF_LANG_FALLBACK]
    text = table.get(key)
    if text is None:
        text = _PDF_STRINGS[PDF_LANG_FALLBACK].get(key)
        if text is None:
            logger.warning("PDF i18n: clau desconeguda '%s' (idioma %s).", key, lang)
            return key
        logger.warning("PDF i18n: clau '%s' sense traducció a '%s'; fallback a '%s'.",
                       key, lang, PDF_LANG_FALLBACK)
    return text


def resolve_pdf_lang(requested, customer=None):
    """Idioma efectiu d'un PDF. Cadena de decisió ÚNICA (les views no decideixen res):
    petició explícita de l'operador → idioma del client destinatari → 'ca'.

    El buit és un valor legítim a Customer.language ('sense preselecció'): no és un error,
    simplement no aporta default i es cau al fallback."""
    if requested in PDF_LANGS:
        return requested
    cust_lang = (getattr(customer, 'language', '') or '').strip()
    if cust_lang in PDF_LANGS:
        return cust_lang
    return PDF_LANG_FALLBACK


def _money(value):
    """Format monetari 2 decimals amb coma decimal (convenció EU)."""
    v = Decimal(value or 0).quantize(Decimal('0.01'))
    return f'{v:,.2f}'.replace(',', '§').replace('.', ',').replace('§', '.')


def _fmt_date(d):
    """Data en format DD/MM/YYYY, o '—' si no n'hi ha."""
    return d.strftime('%d/%m/%Y') if d else '—'


class _TrackedLabel(Flowable):
    """Una línia de text amb tracking (character spacing) en em, dibuixada directament al
    canvas. `ParagraphStyle`/`Paragraph` de Platypus no exposen cap primitiu de character
    spacing (només `spaceBefore`/`spaceAfter`, entre paràgrafs); el canvas de baix nivell sí,
    via `textobject.setCharSpace()`. Només per a la capçalera «COMENTARIS» de la maqueta §3
    (0,08em) — cap altra etiqueta d'aquest document el demana."""

    def __init__(self, text, font, size, color, tracking_em=0.08):
        super().__init__()
        self.text, self.font, self.size, self.color = text, font, size, color
        self.char_space = tracking_em * size
        n = len(text)
        self.width = pdfmetrics.stringWidth(text, font, size) + self.char_space * max(0, n - 1)
        self.height = size * 1.3

    def draw(self):
        c = self.canv
        c.setFillColor(self.color)
        txt = c.beginText(0, 0)
        txt.setFont(self.font, self.size)
        txt.setCharSpace(self.char_space)
        txt.textOut(self.text)
        c.drawText(txt)


def _tenant_cfg():
    try:
        from fhort.accounts.models import TenantConfig
        return TenantConfig.objects.first()
    except Exception:  # noqa: BLE001
        return None


def _amb_pais(trossos, pais):
    """Uneix els trossos d'una adreça i hi afegeix el país NOMÉS si hi ha adreça.

    `pais`/`country` tenen `default='ES'` i **mai** són buits (tasks/models.py:172 i :216;
    tenants/models.py). Filtrar-los amb un `if x` final no els descarta: un client sense cap dada
    fiscal — els tres de staging — imprimia una línia solitària que deia literalment «ES» sota el
    seu nom, a tots els documents. El país qualifica una adreça; sense adreça no qualifica res.
    """
    addr = ', '.join(x for x in trossos if x)
    if not addr:
        return ''
    pais = (pais or '').strip()
    return f'{addr}, {pais}' if pais else addr


def _customer_oneliner(c, lang=PDF_LANG_FALLBACK):
    """Adreça · identificador fiscal del client en una sola línia (omet buits)."""
    parts = []
    addr = _amb_pais([c.adreca_linia1, c.adreca_linia2,
                      ' '.join(y for y in [c.codi_postal, c.ciutat] if y)], c.pais)
    if addr:
        parts.append(addr)
    if c.nif:
        parts.append(f'{t(lang, "tax_id")}: {c.nif}')
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
    return _amb_pais([(cfg.address or '').strip(), loc], cfg.country)


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


def _emissor_left(cfg, s, FS, FL, lang=PDF_LANG_FALLBACK):
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
            rows.append([Paragraph(f'{t(lang, "tax_id")}: {tax_id}', S_EM)])
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


def generate_quote_pdf(quote, lang=None):
    """Retorna els bytes del PDF de l'oferta `quote` (disseny Montserrat; fallback Helvetica)."""
    return generate_document_pdf(quote, doc_key='doc_quote', lang=lang)


def generate_document_pdf(quote, doc_key='doc_quote', show_payment=True, lang=None):
    """Retorna els bytes del PDF d'un document comercial (`quote` = Quote, SalesOrder o
    DeliveryNote; layout idèntic). `doc_key` és la CLAU del títol ('doc_quote'/'doc_order'/
    'doc_delivery_note'), no el text: el títol es tradueix aquí com la resta de literals.
    `lang` és l'idioma efectiu (ja resolt per resolve_pdf_lang); None → fallback 'ca'.
    `show_payment=False` (albarà, B4c): SENSE bloc de venciments/condicions de pagament ni
    "Vàlid fins" (l'albarà no en porta); el peu queda amb les observacions/notes. Les línies
    DEDUCTION (import negatiu) es mostren amb signe − i color discret. Emissor = TenantConfig."""
    lang = lang if lang in PDF_LANGS else PDF_LANG_FALLBACK
    doc_title = t(lang, doc_key)
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
    left = _emissor_left(cfg, s, FS, FL, lang)

    meta_rows = [
        [Paragraph(t(lang, 'number'), S_LABEL_R), Paragraph(quote.document_number or '—', SSM_R)],
        [Paragraph(t(lang, 'date'), S_LABEL_R), Paragraph(_fmt_date(quote.issued_at), SSM_R)],
    ]
    if show_payment:  # "Vàlid fins" és propi d'oferta/comanda; un albarà no en porta.
        meta_rows.append([Paragraph(t(lang, 'valid_until'), S_LABEL_R),
                          Paragraph(_fmt_date(quote.valid_until), SSM_R)])
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
    story.append(Paragraph(t(lang, 'for'), S_LABEL))
    story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(c.rao_social or c.nom, S_CLIENT))
    oneliner = _customer_oneliner(c, lang)
    if oneliner:
        story.append(Paragraph(oneliner, SSM_G))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGREY,
                            spaceBefore=4 * mm, spaceAfter=5 * mm))

    # ═══ LÍNIES ═══
    HDR = s('hdr', font=FS, size=8, color=GREY)
    HDR_R = s('hdrr', font=FS, size=8, color=GREY, align=TA_RIGHT)
    rows = [[Paragraph(t(lang, 'description'), HDR), Paragraph(t(lang, 'units'), HDR_R),
             Paragraph(t(lang, 'unit_price'), HDR_R), Paragraph(t(lang, 'amount'), HDR_R)]]
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
        ['', Paragraph(t(lang, 'taxable_base'), S), Paragraph(_money(quote.subtotal), SR)],
        ['', Paragraph(f'{t(lang, "vat")} {pct}%', S), Paragraph(_money(quote.tax_amount), SR)],
        ['', Paragraph(t(lang, 'total_amount'), SB), Paragraph(_money(quote.total), SRB)],
    ], colWidths=[104 * mm, 44 * mm, 26 * mm], style=TableStyle([
        ('LINEABOVE', (1, 2), (2, 2), 0.5, LGREY),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)])))
    story.append(Spacer(1, 10 * mm))

    # ═══ PEU ═══
    # Albarà (show_payment=False): sense forma/condicions de pagament ni venciments; només
    # observacions. Oferta/comanda: bloc esquerre (forma de pagament + notes) + bloc dret
    # (condicions + venciments materialitzats).
    peu_label = t(lang, 'payment_method' if show_payment else 'observations')
    peu_l_rows = [[Paragraph(peu_label, S_LABEL)]]
    if quote.notes:
        peu_l_rows.append([Paragraph(quote.notes.replace('\n', ' '), SSM_G)])
    # IBAN + notes de pagament de l'emissor (TenantConfig, P6) — fi del hardcode. Només al bloc de
    # pagament (oferta/comanda); l'albarà (show_payment=False) no en porta.
    if show_payment:
        iban = (getattr(cfg, 'iban', '') or '').strip()
        if iban:
            peu_l_rows.append([Paragraph(f'{t(lang, "iban")}: {iban}', SSM_G)])
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
        peu_r_rows = [[Paragraph(t(lang, 'payment_terms'), S_LABEL), '']]
        if terms:
            # Bandera tancada (2026-07-27): commerce/models.py:400 declarava des de B3a que aquest
            # nom surt "en l'idioma del document/client", però s'imprimia el canònic. PaymentTerms
            # és TranslatableMixin i la seva traducció viu a i18n_content; ara sí que s'hi passa.
            peu_r_rows.append([Paragraph(terms.translated('name', lang), SSM_I), ''])
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

# Les línies que NO són una targeta de model sinó una fila dins del bloc del seu model, i la
# clau amb què es diu el seu tipus quan la descripció ve buida. `MANUAL` en queda FORA a posta:
# una línia manual (comentari lliure, sense model) és una targeta pròpia, com abans.
_EXTRA_LABEL = {'EXTRA': 'dn_extra', 'DEDUCTION': 'dn_deduction', 'EXPENSE': 'dn_expense'}


def generate_delivery_note_pdf(delivery_note, lang=None):
    """Retorna els bytes del PDF d'un albarà v2 compost per model. Agrupa les línies VISIBLES pel
    seu model FK; per cada model dibuixa un bloc (nom + ref intern + [ref client si difereix] +
    collection + temporada/any), els detalls de cada volta/extra i el subtotal del model. Els
    totals són els del document (calculats sobre línies visibles). SENSE venciments, SENSE cost
    intern. `lang` és l'idioma efectiu (ja resolt per resolve_pdf_lang); None → fallback 'ca'.

    TIPOGRAFIA: la capçalera (logo, raó social, NIF, títol, Número/Data, «Per a») hereta
    Montserrat del disseny validat (B2-PDF-v7) i NO la toca aquesta funció. El COS —des del
    primer bloc de model fins als totals— és IBM Plex Mono i la paleta pròpia de la maqueta §3
    (`DN_TEXT_MAIN`/`DN_TEXT_SOFT`/`DN_LINE`), no la del pressupost. Cap franja de color.
    """
    lang = lang if lang in PDF_LANGS else PDF_LANG_FALLBACK
    F = _fonts()
    FL, FR, FS, FB = F[F_LIGHT], F[F_REG], F[F_SEMI], F[F_BOLD]
    FM, FMS = F[F_MONO], F[F_MONO_SEMI]
    cfg = _tenant_cfg()

    def s(name, font=FL, size=8.5, align=TA_LEFT, color=DARK, leading=None):
        return ParagraphStyle(name, fontName=font, fontSize=size, textColor=color,
                              alignment=align, leading=leading or size * 1.35)

    # ── CAPÇALERA — Montserrat, paleta DARK/GREY/LGREY del disseny validat. NO TOCAR. ──
    SSM_G = s('smg', size=7.5, color=DGREY)
    SSM_R = s('smr', size=7.5, align=TA_RIGHT)
    S_TITDOC = s('titdoc', font=FL, size=14, color=GOLD, align=TA_RIGHT)
    S_CLIENT = s('cli', font=FL, size=13)
    S_LABEL = s('lbl', size=7, color=GREY)
    S_LABEL_R = s('lblr', size=7, color=GREY, align=TA_RIGHT)

    # ── COS (maqueta §3) — IBM Plex Mono, tokens `DN_*`. Mides EXACTES de l'ordre de tipografia
    # (regla dels 8pt mínims: la més petita d'aquest document és la capçalera «Comentaris», a 8).
    S_MODEL = s('dn_model', font=FMS, size=11, color=DN_TEXT_MAIN, leading=14)
    S_META = s('dn_meta', font=FM, size=8.5, color=DN_TEXT_SOFT, leading=12)
    S_PACTE = s('dn_pacte', font=FM, size=9, color=DN_TEXT_MAIN, leading=13)
    S_RONDA = s('dn_ronda', font=FM, size=9, color=DN_TEXT_MAIN, leading=13)
    S_RONDA_IMP = s('dn_ronda_imp', font=FMS, size=9.5, color=DN_TEXT_MAIN, align=TA_RIGHT, leading=13)
    S_EXTRA = s('dn_extra_l', font=FM, size=9, color=DN_TEXT_MAIN, leading=13)
    S_EXTRA_IMP = s('dn_extra_r', font=FM, size=9, color=DN_TEXT_MAIN, align=TA_RIGHT, leading=13)
    S_COM_B = s('dn_com_b', font=FM, size=9, color=DN_TEXT_MAIN, leading=13)
    S_SUM = s('dn_sum', font=FM, size=9, color=DN_TEXT_MAIN, leading=13)
    S_SUM_R = s('dn_sum_r', font=FM, size=9, color=DN_TEXT_MAIN, align=TA_RIGHT, leading=13)
    S_SUM_TOT = s('dn_sum_tot', font=FMS, size=10, color=DN_TEXT_MAIN, leading=14)
    S_SUM_TOT_R = s('dn_sum_tot_r', font=FMS, size=10, color=DN_TEXT_MAIN, align=TA_RIGHT, leading=14)

    buf = BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4,
                          leftMargin=ML, rightMargin=MR, topMargin=MT, bottomMargin=MB,
                          title=delivery_note.document_number or t(lang, 'doc_delivery_note'))
    frame = Frame(ML, MB, CW, PAGE_H - MT - MB,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id='main', frames=[frame])])
    story = []

    # ═══ CAPÇALERA (heretada del pressupost validat) — emissor = TenantConfig, helper compartit ═══
    left = _emissor_left(cfg, s, FS, FL, lang)

    meta = Table([
        [Paragraph(t(lang, 'number'), S_LABEL_R), Paragraph(delivery_note.document_number or '—', SSM_R)],
        [Paragraph(t(lang, 'date'), S_LABEL_R), Paragraph(_fmt_date(delivery_note.issued_at), SSM_R)],
    ], colWidths=[COL_RIGHT_W - 30 * mm, 30 * mm], style=TableStyle(ZP))
    right = Table([[Paragraph(t(lang, 'doc_delivery_note'), S_TITDOC)], [Spacer(1, 2 * mm)], [meta]],
                  colWidths=[COL_RIGHT_W], style=TableStyle(ZP))
    story.append(Table([[left, right]], colWidths=[COL_LEFT_W, COL_RIGHT_W],
        style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')] + ZP)))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGREY, spaceBefore=5 * mm, spaceAfter=4 * mm))

    # ═══ CLIENT ═══
    c = delivery_note.customer
    story.append(Paragraph(t(lang, 'for'), S_LABEL))
    story.append(Spacer(1, 1 * mm))
    story.append(Paragraph(c.rao_social or c.nom, S_CLIENT))
    oneliner = _customer_oneliner(c, lang)
    if oneliner:
        story.append(Paragraph(oneliner, SSM_G))
    story.append(HRFlowable(width='100%', thickness=0.5, color=LGREY, spaceBefore=4 * mm, spaceAfter=5 * mm))


    def _capcalera_model(l):
        """LA IDENTITAT DEL MODEL d'una línia: nom gran i, sota, col·lecció · temporada · refs.

        Viu a part perquè la fan servir DUES coses: la targeta d'una línia de voltes i el bloc
        d'un model que en aquest albarà NOMÉS porta extres. Tenir-ne dues còpies era garantir
        que un dia diguessin identitats diferents del mateix model.
        """
        m = l.model
        # Una línia SENSE model (les 4 llegades i les MANUAL, comentari lliure) no és
        # una targeta de model: no té identitat ni pacte. El seu nom és la seva descripció, i
        # llavors la línia de concepte de sota s'ha de callar — si no, el mateix text sortia
        # DUES vegades, una com a títol i una com a concepte.
        nom = (m.nom_prenda if m else '') or (l.description or '—')
        # Identitat: col·lecció · temporada any · ref client · ref nostra. SENSE etiquetes: el
        # client sap què és cadascuna i els rètols només afegeixen soroll a una línia de 10px.
        ident = [(m.collection if m else '') or '',
                 ' '.join(x for x in [(m.temporada if m else ''),
                                      str(m.any) if (m and m.any) else ''] if x)]
        refs = [x for x in [(m.codi_client if m else ''), (m.codi_intern if m else '')] if x]
        # Les refs (client/nostra) es llegeixen en --text-main; la resta de la línia de meta
        # (col·lecció, temporada) es queda en --text-soft (color per defecte de `S_META`).
        ident = [x for x in ident if x] + [f'<font color="#{DN_TEXT_MAIN.hexval()[2:]}">{x}</font>'
                                           for x in refs]

        out = [Paragraph(nom, S_MODEL)]
        if ident:
            out.append(Paragraph(' · '.join(ident), S_META))
        return out

    def _linia_block(l):
        """UN BLOC PER LÍNIA · maqueta §3. La línia ÉS un model (A1) o una volta directa (A7).

        Cap franja de color i cap taula de columnes: el que el client ha de llegir és QUIN model,
        de quin pressupost surt i QUINES voltes se li han lliurat — i l'import a la dreta. La
        graella de sis columnes (descripció · data · qtt · unitat · preu · import) era la forma
        d'un albarà de LÍNIES DE TASCA i deia sis coses per fila quan ara n'hi ha una: l'import.

        🔒 CAP COST INTERN, MAI (A3). Ni la tarifa/hora ni el cost surten d'aquí: són lectura
        interna. El que sí que surt d'una volta directa són els NOMS de les tasques fetes, perquè
        una volta sense pressupost ha de dir què s'hi ha fet per justificar el preu.
        """
        m = l.model
        sense_model = m is None
        els = _capcalera_model(l)

        # LA LÍNIA DEL PACTE. Una volta directa no en té cap i ho diu en negreta: és la
        # justificació de per què aquell import no surt de cap pressupost.
        if l.encarrec_directe:
            els.append(Paragraph(f'<font name="{FMS}">{t(lang, "dn_direct_order")}</font>', S_PACTE))
        elif l.linia_comanda_id:
            lc = l.linia_comanda
            bits = [f'<font name="{FMS}">{t(lang, "dn_quote")} '
                    f'{lc.order.document_number if lc.order_id else "—"}</font>']
            if (l.description or '').strip():
                bits.append(l.description.strip())
            if lc.rounds_included is not None:
                bits.append(f'R×{lc.rounds_included}')
            bits.append(f'{t(lang, "dn_qty")} {Decimal(lc.qty_allocated or 0):.0f}/'
                        f'{Decimal(lc.quantity or 0):.0f}')
            els.append(Paragraph(' · '.join(bits), S_PACTE))
        elif (l.description or '').strip() and not sense_model:
            els.append(Paragraph(l.description.strip(), S_PACTE))

        # LES VOLTES EN UNA SOLA LÍNIA, amb l'import a la dreta i SENSE puntets: el punt de
        # conducció és d'una taula de moltes files, i aquí n'hi ha una.
        voltes = []
        for r in l.rondes.select_related('entrega').order_by('seq'):
            e = getattr(r, 'entrega', None)
            txt = f'{t(lang, "dn_round")} {r.seq}'
            if e is not None:
                txt += f' {_fmt_date(e.data.date())}'
            voltes.append(txt)
        detall = ' · '.join(voltes)
        if l.encarrec_directe:
            # Les tasques FETES de la volta directa, al costat de la volta.
            fetes = [tk.task_type.name for r in l.rondes.all()
                     for tk in r.tasques.select_related('task_type').order_by(
                         'task_type__default_order', 'task_type__code')
                     if tk.status == 'Done']
            if fetes:
                detall = ' · '.join([detall] + fetes) if detall else ' · '.join(fetes)
        els.append(Table([[
            Paragraph(detall or '—', S_RONDA),
            Paragraph(f'{_money(l.line_total)} €', S_RONDA_IMP),
        ]], colWidths=[CW - 30 * mm, 30 * mm], style=TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM')])))
        return els

    def _fila_extra(l):
        """UN EXTRA, UNA DESPESA o UNA DEDUCCIÓ dins del bloc del seu model: concepte a
        l'esquerra, import a la dreta. NO és una targeta de model —el model ja s'ha dit a la
        línia de dalt— i repetir-ne la identitat faria que el mateix nom sortís dues vegades.

        El concepte és la descripció de l'origen; quan l'origen no en porta cap, el diu el seu
        TIPUS, traduït aquí. La v1 congelava la paraula a la columna `description` en crear la
        línia i llavors un albarà en anglès imprimia «Deducció»: la frase es posa on hi ha
        l'idioma, que és aquí.
        """
        concepte = (l.description or '').strip() or t(lang, _EXTRA_LABEL.get(l.line_kind, 'dn_extra'))
        return Table([[
            Paragraph(concepte, S_EXTRA),
            Paragraph(f'{_money(l.line_total)} €', S_EXTRA_IMP),
        ]], colWidths=[CW - 30 * mm, 30 * mm], style=TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 1), ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))

    # UN BLOC PER LÍNIA, en l'ordre en què s'han afegit: la safata posa sempre el pacte abans de
    # la directa, i per això la volta fora de pressupost surt just després del seu model (A7).
    #
    # 🔑 ELS EXTRES NO OBREN BLOC: van SOTA LES VOLTES del bloc del seu model, com una fila més.
    # Un extra és una línia d'albarà com les altres, però la seva targeta seria una segona
    # capçalera amb el mateix nom de model just a sota de la primera. S'enganxen a l'ÚLTIMA
    # línia principal del seu model perquè quedin després de totes les seves voltes, i no entre
    # el bloc del pacte i el de la volta directa (que han d'anar seguits, A7).
    totes = list(delivery_note.lines.filter(visible=True)
                 .select_related('model', 'linia_comanda__order')
                 .prefetch_related('rondes__entrega', 'rondes__tasques__task_type')
                 .order_by('position', 'id'))
    principals = [l for l in totes if l.line_kind not in _EXTRA_LABEL]
    extres = {}
    for l in totes:
        if l.line_kind in _EXTRA_LABEL:
            extres.setdefault(l.model_id, []).append(l)
    ultima = {l.model_id: i for i, l in enumerate(principals)}

    # 6pt de padding vertical per bloc i una regla fina (--line) entre blocs — maqueta §3
    # (`.blk{padding:8px 0;border-bottom:1px solid var(--line)}`, adaptat a pt d'impressió).
    # Cap franja de color.
    for i, ln in enumerate(principals):
        story.append(Spacer(1, 6))
        for el in _linia_block(ln):
            story.append(el)
        if ultima.get(ln.model_id) == i:
            for ex in extres.pop(ln.model_id, []):
                story.append(_fila_extra(ex))
        story.append(HRFlowable(width='100%', thickness=0.5, color=DN_LINE,
                                spaceBefore=6, spaceAfter=0))

    # Els extres d'un model que no té cap línia de voltes en aquest albarà: llavors sí que
    # necessiten capçalera pròpia —si no, sortirien com un import solt sense dir de què és.
    for _mid, files in extres.items():
        story.append(Spacer(1, 6))
        for el in _capcalera_model(files[0]):
            story.append(el)
        for ex in files:
            story.append(_fila_extra(ex))
        story.append(HRFlowable(width='100%', thickness=0.5, color=DN_LINE,
                                spaceBefore=6, spaceAfter=0))

    story.append(Spacer(1, 4 * mm))

    # ═══ PEU · Comentaris | Sumes, EN UNA SOLA TAULA (maqueta §3) ═══
    # Dues columnes, VALIGN TOP, sense vores, la dreta d'amplada FIXA (la de les sumes): així
    # «COMENTARIS» (capçalera majúscules, tracking .08em — `_TrackedLabel`, Platypus no ho sap
    # fer amb `Paragraph`) queda a la MATEIXA alçada que «Base imposable», perquè totes dues
    # són el primer element de la seva columna dins la MATEIXA fila. Sense comentaris, la
    # columna esquerra queda buida i les sumes segueixen al seu lloc — no puja res per omplir
    # el forat, que seria el senyal contrari (que el document «s'ha mogut» sense comentari).
    notes = (delivery_note.notes or '').strip()
    if notes:
        comentaris = Table([
            [_TrackedLabel(t(lang, 'dn_comments').upper(), FM, 8, DN_TEXT_SOFT)],
            [Spacer(1, 3)],
            [Paragraph(notes, S_COM_B)],
        ], colWidths=[CW - 70 * mm], style=TableStyle(ZP))
    else:
        comentaris = ''

    # 🚨 UNA FILA PER TIPUS D'IVA REAL, MAI UN PERCENTATGE EFECTIU. `_tax_pct` (usat pel
    # pressupost/comanda, capçalera intacta) deriva un % del quocient tax/subtotal — amb dos
    # tipus barrejats a la mateixa base, això dona un número que no és cap tipus real. Aquí
    # es llegeix `tax_breakdown` (ja calculat i persistit per `recalculate_totals`, la mateixa
    # font que Quote/SalesOrder): una fila per tipus, amb la SEVA base. Amb un sol tipus, és
    # una fila — idèntic al que hi havia, però ja no per casualitat.
    sum_rows = [[Paragraph(t(lang, 'taxable_base'), S_SUM),
                Paragraph(f'{_money(delivery_note.subtotal)} €', S_SUM_R)]]
    for entry in (delivery_note.tax_breakdown or []):
        rate = Decimal(entry['rate'])
        rate_txt = f'{rate:.0f}' if rate == rate.to_integral_value() else str(rate).replace('.', ',')
        sum_rows.append([Paragraph(f'{t(lang, "vat")} {rate_txt}%', S_SUM),
                         Paragraph(f'{_money(entry["tax"])} €', S_SUM_R)])
    sum_rows.append([Paragraph(t(lang, 'total_amount'), S_SUM_TOT),
                     Paragraph(f'{_money(delivery_note.total)} €', S_SUM_TOT_R)])
    last = len(sum_rows) - 1
    # «Import total» amb regla superior --text-main (maqueta: `.sum .tot{border-top:1px solid
    # var(--text-main)}`) — DN_TEXT_MAIN i no la LGREY de la capçalera.
    sumes = Table(sum_rows, colWidths=[44 * mm, 26 * mm], style=TableStyle([
        ('LINEABOVE', (0, last), (1, last), 0.5, DN_TEXT_MAIN),
        ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0)]))

    story.append(Table([[comentaris, sumes]], colWidths=[CW - 70 * mm, 70 * mm],
        style=TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')] + ZP)))

    # 🚨 EL BLOC «OBSERVACIONS» SE'N VA. Imprimia `delivery_note.notes` una SEGONA vegada, al
    # peu del document, i el bloc «Comentaris» de la maqueta §3 ja el diu a dalt, al costat de
    # les sumes. Amb els dos, el mateix text sortia dues vegades a cada albarà amb comentari —
    # i no es veia llegint el diff, perquè cadascun és correcte per separat: el que falla és que
    # ara hi ha dos lectors del mateix camp. (Trobat pel guàrdia d'i18n llegint el generador.)

    doc.build(story)
    return buf.getvalue()
