"""accounts/logo.py — normalització del logo de l'emissor per als documents PDF.

L'usuari puja el que tingui (SVG, PNG o JPG) i el sistema SEMPRE el converteix a un PNG ràster
que reportlab pot dibuixar a la capçalera — adéu a l'exigència "màxim 15 mm PNG" que administració
no comprovarà. Els SVG es rasteritzen amb cairosvg a resolució alta; els ràsters es validen amb
Pillow (ja al requirements) i es redimensionen si són desmesurats. Retorna un ContentFile PNG
llest per assignar a l'ImageField `TenantConfig.logo_file`.
"""
import io
import logging

from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)

# El logo surt a ≤15 mm d'alçada a la capçalera; rasteritzar l'SVG a ~600 px d'alçada dona densitat
# de sobres per a impressió sense guardar un PNG enorme. `_MAX_DIM` acota els ràsters d'entrada.
_TARGET_H = 600
_MAX_DIM = 2000


def _is_svg(raw, name):
    """Heurística barata: extensió .svg o firma XML/<svg> a la capçalera del fitxer."""
    if (name or '').lower().endswith('.svg'):
        return True
    head = raw[:512].lstrip()
    return head[:5] == b'<?xml' or b'<svg' in head


def normalize_logo(uploaded):
    """Converteix un fitxer pujat (SVG/PNG/JPG) a un ContentFile PNG normalitzat i acotat.
    Retorna el ContentFile (name='logo.png'); llança ValueError si el fitxer no és processable."""
    raw = uploaded.read()
    if not raw:
        raise ValueError('fitxer buit')
    name = getattr(uploaded, 'name', '') or 'logo'

    if _is_svg(raw, name):
        try:
            import cairosvg
        except ImportError as e:  # requirements desalineat amb l'entorn
            raise ValueError(f'cairosvg no disponible: {e}')
        try:
            png = cairosvg.svg2png(bytestring=raw, output_height=_TARGET_H)
        except Exception as e:  # noqa: BLE001 — SVG malmès/no vàlid
            raise ValueError(f'SVG no vàlid: {e}')
        return ContentFile(png, name='logo.png')

    # Ràster (PNG/JPG/…): validar + normalitzar amb Pillow.
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception as e:  # noqa: BLE001 — no és una imatge llegible
        raise ValueError(f'imatge no vàlida: {e}')
    # Mode segur per a PNG (aplana paletes; preserva alfa si en té) i sostre de mida.
    if img.mode not in ('RGB', 'RGBA'):
        img = img.convert('RGBA' if ('A' in img.getbands() or img.mode == 'P') else 'RGB')
    w, h = img.size
    if max(w, h) > _MAX_DIM:
        scale = _MAX_DIM / max(w, h)
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))))
    out = io.BytesIO()
    img.save(out, format='PNG')
    return ContentFile(out.getvalue(), name='logo.png')
