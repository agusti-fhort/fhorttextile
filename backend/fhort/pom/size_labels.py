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


# ── N1 (2026-08-06 nit) · DEDUCCIÓ DEL TIPUS D'ESCALA ─────────────────────────────────
# Un run de talles ja diu de quina mena és; només que ho diu amb les seves etiquetes i no
# amb un camp. Això ho llegeix. NO persisteix res: qui decideix desar és la data migration
# (idempotent) o el serializer.
#
# L'etiqueta MANA sobre `base_unit`. Motiu mesurat: a staging, `TODDLER_EU` porta
# `base_unit='AGE_YEARS'` i unes etiquetes que són alçades en cm (86-116, pas de 6, amb
# `body_height_cm == etiqueta` a les 6 talles). El camp mentia; les etiquetes no. Quan les
# etiquetes no donen veredicte, `base_unit` fa de xarxa.

#: Etiqueta alfa: S, M, L amb prefix de X repetides (XXL) o numèric (3XL).
_ALPHA = re.compile(r'^(?:\d+X|X*)(?:S|M|L)$')
#: Mesos explícits: '3M', '06M', '0M-1M', '3M/6M'.
_MESOS = re.compile(r'^\d+\s*M$|^\d+\s*M[-/]\d+\s*M$')
#: Anys explícits: '6Y', '12Y'.
_ANYS = re.compile(r'^\d+\s*Y$')
#: Parell zero-padded de dos dígits: '00/01', '03/06', '18-24'.
_PARELL_PADDED = re.compile(r'^\d\d[-/]\d\d$')
#: Primer número d'una etiqueta ('9/10' -> 9, '104' -> 104).
_PRIMER_NUM = re.compile(r'\d+')

#: `base_unit` (6 choices històrics) → tipus d'escala (4 categories). Total i sense ambigüitat
#: de forma; el que no és fiable és la DADA (1 error de 24 files mesurat a staging).
BASE_UNIT_A_TIPUS = {
    'ALPHA': 'ALPHA',
    'NUMERIC_EU': 'NUM',
    'NUMERIC_US': 'NUM',
    'CM_HEIGHT': 'ALTURA',
    'MONTHS': 'MESOS',
    'AGE_YEARS': 'MESOS',
}


def _mediana(valors):
    if not valors:
        return None
    ordenats = sorted(valors)
    n = len(ordenats)
    mig = n // 2
    return ordenats[mig] if n % 2 else (ordenats[mig - 1] + ordenats[mig]) / 2


def _tipus_de_les_etiquetes(etiquetes):
    """Veredicte NOMÉS per etiquetes, o None si no en donen cap."""
    nets = [(e or '').strip().upper() for e in etiquetes]
    nets = [e for e in nets if e]
    if not nets:
        return None

    if any(e == 'NB' or _MESOS.match(e) for e in nets):
        return 'MESOS'
    if any(_ANYS.match(e) for e in nets):
        return 'MESOS'
    if sum(1 for e in nets if _ALPHA.match(e)) * 2 >= len(nets):
        return 'ALPHA'

    # A partir d'aquí, món numèric. Es pren el PRIMER número de cada etiqueta ('9/10' -> 9)
    # i s'ordena: hi ha runs a staging amb l'`ordre` trencat i el pas s'ha de poder llegir
    # igualment (el pas és una propietat de l'escala, no de com està desada).
    valors = [int(m.group()) for m in (_PRIMER_NUM.search(e) for e in nets) if m]
    if len(valors) < 2:
        return None
    ordenats = sorted(valors)
    pas = _mediana([b - a for a, b in zip(ordenats, ordenats[1:])])

    if sum(1 for e in nets if _PARELL_PADDED.match(e)) * 2 >= len(nets) and max(ordenats) <= 36:
        return 'MESOS'
    # El pas és el desempat fort entre NUM i ALTURA, i és gratuït: l'escalat EU d'alçada
    # infantil va de 6 en 6 (50·56·62…170) i el numèric EU adult de 2 en 2 (34·36·38…).
    if pas == 6 and 44 <= min(ordenats) and max(ordenats) <= 188:
        return 'ALTURA'
    if pas == 1 and max(ordenats) <= 18:
        return 'MESOS'
    if pas == 2 and min(ordenats) >= 28:
        return 'NUM'
    return None


def dedueix_tipus_escala(etiquetes, base_unit=''):
    """(tipus, font) per a un run. `tipus` és '' quan no es dedueix sol.

    font: 'etiquetes' · 'base_unit' · '' (indeduïble). El caller la fa servir per anotar els
    casos que necessiten domini davant i els conflictes entre les dues fonts.
    """
    per_etiqueta = _tipus_de_les_etiquetes(etiquetes)
    if per_etiqueta:
        return per_etiqueta, 'etiquetes'
    per_base = BASE_UNIT_A_TIPUS.get((base_unit or '').strip().upper())
    if per_base:
        return per_base, 'base_unit'
    return '', ''


def conflicte_tipus_escala(etiquetes, base_unit=''):
    """El `base_unit` desat contradiu el que diuen les etiquetes? (per a auditoria)."""
    per_etiqueta = _tipus_de_les_etiquetes(etiquetes)
    per_base = BASE_UNIT_A_TIPUS.get((base_unit or '').strip().upper())
    return bool(per_etiqueta and per_base and per_etiqueta != per_base)
