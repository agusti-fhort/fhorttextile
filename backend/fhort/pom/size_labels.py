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

    Col·lapsa X-repetides a numèric (XXL->2XL), el sufix de MESOS ('3M'->'3', '06M'->'6')
    NOMÉS quan la 'M' va precedida de dígit (mai 'M' sola = Medium), i el zero-padding
    numèric ('03'->'3'). Els no-numèrics (S, M, L) queden en majúscules.
    """
    t = seg.strip().upper()
    m = _XREPEAT.match(t)
    if m:
        return f"{len(m.group(1))}X{m.group(2)}"
    # Sufix de mesos PER TRAM: treu una 'M' final només si va precedida de dígit (mesos:
    # '3M','06M','12M'), MAI la 'M' solitària (talla Medium) ni una lletra final no-mes.
    if len(t) >= 2 and t[-1] == 'M' and t[-2].isdigit():
        t = t[:-1]
    # Zero-padding: '03'->'3', '0'->'0'. lstrip('0') sobre no-numèrics (S) no els toca.
    return t.lstrip('0') or '0' if t else t


def canonical_size_label(s):
    """Forma canònica d'una etiqueta de talla per comparar (no per guardar).

    Case/whitespace-fold + separa PER TRAM en '/' i '-' (un rang '3-6' i '3/6' són la
    mateixa cosa) + col·lapsa per tram (a) les formes X-repetides a numèric, (b) el sufix
    de mesos precedit de dígit i (c) el zero-padding numèric. Així '3-6m'≡'03/06',
    '6-9m'≡'06/09', '3/6'≡'03/06', '2'≡'02'. Les formes d'una sola X (XL, XS), les ja
    numèriques (2XL) i les talles lletra soltes (S, M, L, 34) queden intactes.

    Exemples:
        'XXL'   -> '2XL'
        'XL'    -> 'XL'
        'XXS'   -> '2XS'
        '34'    -> '34'
        'S'/'M'/'L' -> 'S'/'M'/'L'   (mai es toquen; 'M' NO és mesos)
        '03/06' -> '3/6'   ·   '3-6m' -> '3/6'   ·   '6-9M' -> '6/9'
        '12M'   -> '12'    ·   '0M-1M' -> '0/1'
    """
    t = (s or '').strip().upper()
    if not t:
        return t
    return '/'.join(_canon_segment(seg) for seg in re.split(r'[/-]', t))
