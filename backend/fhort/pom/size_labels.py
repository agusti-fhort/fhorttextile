"""Canonicalització d'etiquetes de talla per COMPARAR a la frontera d'import.

B1: XXL i 2XL són la mateixa talla però s'escriuen diferent. Aquest helper dona una
forma canònica (numèrica) per comparar-les, SENSE persistir res: la decisió d'import
segueix guardant SEMPRE l'etiqueta del tenant (SizeDefinition), no la del document.
"""
import re

# Forma X-repetida al davant d'una S/L final: XXL, XXXL, XXS, XXXXS...
_XREPEAT = re.compile(r'^(X{2,})(L|S)$')


def canonical_size_label(s):
    """Forma canònica d'una etiqueta de talla per comparar (no per guardar).

    Case/whitespace-fold + col·lapsa les formes X-repetides a numèric:
    compta les X consecutives davant la S/L final. Les formes d'una sola X (XL, XS)
    i les ja numèriques (2XL, 3XS) queden idèntiques. Les etiquetes que no encaixen
    amb el patró (34, 6M, 6Y, T2, S, M, L) només es passen a majúscules.

    Exemples:
        'XXL'  -> '2XL'
        'xxxl' -> '3XL'
        '2XL'  -> '2XL'   (ja numèrica)
        'XL'   -> 'XL'    (una sola X)
        'XXS'  -> '2XS'
        'XS'   -> 'XS'
        '34'   -> '34'
        '6M'   -> '6M'
        's'    -> 'S'
    """
    t = (s or '').strip().upper()
    m = _XREPEAT.match(t)
    if m:
        return f"{len(m.group(1))}X{m.group(2)}"
    return t
