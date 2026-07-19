"""Canonicalització d'etiquetes de talla per COMPARAR a la frontera d'import.

B1: XXL i 2XL són la mateixa talla però s'escriuen diferent. Aquest helper dona una
forma canònica (numèrica) per comparar-les, SENSE persistir res: la decisió d'import
segueix guardant SEMPRE l'etiqueta del tenant (SizeDefinition), no la del document.
"""
import re

# Forma X-repetida al davant d'una S/L final: XXL, XXXL, XXS, XXXXS...
_XREPEAT = re.compile(r'^(X{2,})(L|S)$')


def _canon_segment(seg):
    """Forma canònica d'UN segment d'etiqueta.

    Col·lapsa X-repetides a numèric (XXL->2XL) i el zero-padding numèric ('03'->'3',
    '06'->'6', '02'->'2'). Els no-numèrics (S, M, L, 6M) queden en majúscules.
    """
    t = seg.strip().upper()
    m = _XREPEAT.match(t)
    if m:
        return f"{len(m.group(1))}X{m.group(2)}"
    # Zero-padding: '03'->'3', '0'->'0'. lstrip('0') sobre no-numèrics (S, 6M) no els toca.
    return t.lstrip('0') or '0' if t else t


def canonical_size_label(s):
    """Forma canònica d'una etiqueta de talla per comparar (no per guardar).

    Case/whitespace-fold + col·lapsa (a) les formes X-repetides a numèric i (b) el
    zero-padding numèric PER TRAM (segments separats per '/'), perquè '3/6'≡'03/06',
    '6/9'≡'06/09' i '2'≡'02'. Les formes d'una sola X (XL, XS) i les ja numèriques
    (2XL, 3XS) queden idèntiques. Les etiquetes sense padding ni patró (34, 6M, S, M, L)
    queden com abans (només majúscules).

    Exemples:
        'XXL'   -> '2XL'
        'xxxl'  -> '3XL'
        '2XL'   -> '2XL'   (ja numèrica)
        'XL'    -> 'XL'    (una sola X)
        'XXS'   -> '2XS'
        'XS'    -> 'XS'
        '34'    -> '34'
        '6M'    -> '6M'
        's'     -> 'S'
        '03/06' -> '3/6'   (zero-padding col·lapsat per tram)
        '02'    -> '2'
    """
    t = (s or '').strip().upper()
    if not t:
        return t
    return '/'.join(_canon_segment(seg) for seg in t.split('/'))
