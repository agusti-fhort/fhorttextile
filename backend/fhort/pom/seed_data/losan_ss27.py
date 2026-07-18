"""Config versionable de la sembra LOSAN SS27 (Fase 1 · FASE B).

Separada del management command (principi motor/config; anti-patró: seed_brownie_fw26
hardcoded). El command `seed_losan_ss27` llegeix D'AQUÍ; aquí NO hi ha lògica, només dades
per CLAU NATURAL (codi/slug). Cap pk. Autoritzat per Agus 2026-07-18.

Via A5 (resolta per Agus): EL GÈNERE VIU A LA SIZE LIBRARY (un size_system per gènere),
mai a `fit_type` ni via migració. Per això els contenidors de grading no col·lideixen:
la identitat (customer + size_system + garment_type_item + fit_type) ja separa nena/nen
perquè el size_system difereix.

Tenant objectiu: 'fhort'. Customer: 'LOS'. Fit únic de tots els contenidors: 'REGULAR'.
"""

# ═══════════════════════════════════════════════════════════════════════════════
# BLOC B1 — Catàleg (estructura v2)
# ═══════════════════════════════════════════════════════════════════════════════

# 1. Grups nous (codi, nom).
NEW_GROUPS = [
    ('NEWBORN', 'Newborn'),
]

# 2+5. Types nous (codi_client, nom_client, grup_codi).
NEW_TYPES = [
    ('NEWBORN', 'Newborn', 'NEWBORN'),
    ('ACCESSORIES', 'Accessories', 'ACCESSORIES'),
]

# 3. Moviments d'items existents a un type nou (item_code, type_codi_desti, complexity_order).
ITEM_MOVES = [
    ('baby_top',      'NEWBORN', 1),
    ('baby_bodysuit', 'NEWBORN', 1),
    ('baby_leggings', 'NEWBORN', 1),
    ('baby_dress',    'NEWBORN', 1),
    ('baby_swimwear', 'NEWBORN', 1),
    ('baby_bloomers', 'NEWBORN', 2),
    ('baby_sleepbag', 'NEWBORN', 2),
    ('baby_sleepsuit', 'NEWBORN', 3),
]

# 4+5+6. Items nous (code, name, type_codi, complexity_order). Sense POM-map (Montse els autora).
NEW_ITEMS = [
    ('booties', 'Peücs',           'NEWBORN',     1),
    ('bag',     'Bossa',           'ACCESSORIES', 2),
    ('hat_cap', 'Gorra / barret',  'ACCESSORIES', 1),
    ('scarf',   'Bufanda',         'ACCESSORIES', 1),
    ('socks',   'Mitjons',         'UNDERWEAR',   1),
]

# 7. Types a desactivar (actiu=False) NOMÉS quan quedin sense items (guard al command).
DEACTIVATE_TYPES_WHEN_EMPTY = ['BABY_SEPARATES', 'BABY_ONEPIECES']


# ═══════════════════════════════════════════════════════════════════════════════
# BLOC B2 — Size libraries LOSAN (crear si falten; les existents ja són bones)
# ═══════════════════════════════════════════════════════════════════════════════
# Notació canònica: mesos ERP (00/01…), alfa 2XL (mai XXL), composites 09/10 i 11/12 = UNA
# talla. Ordre de talles = ordre de la llista (camp `ordre` 1..n). valor_numeric=None
# (designation-only). Cap talla base/sample (el camp NO existeix al model → res a marcar).
# `mon` = etiqueta de món per construir el nom dels contenidors de B3.
SIZE_SYSTEMS = [
    {
        'codi': 'NEWBORN_LOS_01', 'nom': 'Newborn Losan', 'mon': 'Newborn',
        'base_unit': 'MONTHS', 'targets': ['BABY_GIRL', 'BABY_BOY', 'BABY_UNISEX'],
        'sizes': ['00/01', '01/03', '03/06', '06/09', '09/12', '12/18', '18/24'],
    },
    {
        'codi': 'BABY_LOS_01', 'nom': 'Baby Losan', 'mon': 'Baby',
        'base_unit': 'MONTHS', 'targets': ['TODDLER_GIRL', 'TODDLER_BOY'],
        'sizes': ['03/06', '06/09', '09/12', '12/18', '18/24', '24/36'],
    },
    {
        'codi': 'BOY_LOS_01', 'nom': 'LOS Grading Kid Boy 2Y - 12Y', 'mon': 'Kids Boy',
        'base_unit': 'AGE_YEARS', 'targets': ['BOY'],
        'sizes': ['2', '3', '4', '5', '6', '7', '8', '9/10', '11/12'],
    },
    {
        'codi': 'YOUTH_GIRL_LOS_01', 'nom': 'LOS Youth Girl 8Y - 16Y', 'mon': 'Youth Girl',
        'base_unit': 'AGE_YEARS', 'targets': ['TEEN_GIRL'],
        'sizes': ['8', '10', '12', '14', '16'],
    },
    {
        'codi': 'YOUTH_BOY_LOS_01', 'nom': 'LOS Youth Boy 8Y - 16Y', 'mon': 'Youth Boy',
        'base_unit': 'AGE_YEARS', 'targets': ['TEEN_BOY'],
        'sizes': ['8', '10', '12', '14', '16'],
    },
    {
        'codi': 'WOMAN_LOS_01', 'nom': 'Dona ALPHA — LOSAN IBERIA SA Run 01', 'mon': 'Woman',
        'base_unit': 'ALPHA', 'targets': ['WOMAN'],
        'sizes': ['XS', 'S', 'M', 'L', 'XL', '2XL', '3XL'],
    },
    {
        'codi': 'WOMAN_NUM_LOS_01', 'nom': 'Dona NUMERIC — LOSAN IBERIA SA Run 01', 'mon': 'Woman Num',
        'base_unit': 'NUMERIC_EU', 'targets': ['WOMAN'],
        'sizes': ['36', '38', '40', '42', '44', '46', '48', '50', '52'],
    },
    {
        'codi': 'MAN_NUM_LOS_01', 'nom': 'Home NUMERIC — LOSAN IBERIA SA Run 01', 'mon': 'Man Num',
        'base_unit': 'NUMERIC_EU', 'targets': ['MAN'],
        'sizes': ['38', '40', '42', '44', '46', '48', '50', '52', '54', '56', '58'],
    },
]

# Món per als size systems que JA existeixen (Fase A: correctes, no es toquen) però que
# B3 fa servir per construir noms de contenidor.
EXISTING_SYSTEM_MON = {
    'GIRL_LOS_01': 'Kids Girl',
    'MAN_LOS_01': 'Man',
}


# ═══════════════════════════════════════════════════════════════════════════════
# BLOC B3 — Contenidors de grading LOS (identitat + forma; SENSE regles per-POM)
# ═══════════════════════════════════════════════════════════════════════════════
# Cada contenidor: GradingRuleSet origen=CLIENT_RUN · customer=LOS · fit_type=REGULAR ·
# size_system + garment_type_item per codi · nom "LOS <mon> <item> SS27" · CAP GradingRule.
# `forma` i `font` són DOCUMENTALS (el model no té camp de nota lliure → viuen aquí, al config,
# no a BD). Les regles per-POM entren a la fase de mesures amb la fitxa com a font.
# (size_system_codi, item_code, forma, font_documental)
CONTAINERS = [
    ('NEWBORN_LOS_01',    'baby_top',       'LINEAR pur',        'LUZ/PELUCHE/ZEBRA/PINGU/RIZO'),
    ('NEWBORN_LOS_01',    'baby_leggings',  'LINEAR pur',        'SAFARI'),
    ('NEWBORN_LOS_01',    'baby_sleepsuit', 'LINEAR pur',        'OSITO'),
    ('NEWBORN_LOS_01',    'baby_dress',     'LINEAR pur',        'tech pack voile'),
    ('NEWBORN_LOS_01',    'booties',        'LINEAR pur',        'ESTELADO'),
    ('BABY_LOS_01',       'baby_top',       'LINEAR pur',        'GLACIAR/CAMPO/BLOSSOM'),
    ('BABY_LOS_01',       'baby_dress',     'LINEAR pur',        'FLORES'),
    ('BOY_LOS_01',        'jeans',          'LINEAR break 9/10', 'TARRAGONA/MARGARITA'),
    ('GIRL_LOS_01',       'dress_simple',   'LINEAR break 9/10', 'BOW/PETALO/DAIRA/VALENTINA/OLIVIA/BEA'),
    ('YOUTH_BOY_LOS_01',  't_shirt',        'LINEAR pur',        'SOFT/VEST/ROI/ALONSO'),
    ('YOUTH_GIRL_LOS_01', 't_shirt',        'LINEAR break 14',   'ONA/PUFFY'),
    ('YOUTH_GIRL_LOS_01', 'trousers',       'LINEAR break 14',   'GALA/LIVERPOOL/ANCHO/WIDE_LEG/FLARE'),
    ('YOUTH_BOY_LOS_01',  'trousers',       'LINEAR pur',        'JEREMY'),
    ('WOMAN_LOS_01',      't_shirt',        'LINEAR pur',        'DANIELA'),
    ('MAN_LOS_01',        'polo',           'LINEAR pur',        'BERG'),
    ('WOMAN_NUM_LOS_01',  'trousers',       'LINEAR pur (+2)',   'BUDAPEST/GENOVEVA'),
    ('MAN_NUM_LOS_01',    'trousers',       'LINEAR pur (+2)',   'ENRIC/ALFONSO'),
    ('YOUTH_GIRL_LOS_01', 'bikini',         'LINEAR pur',        'CRUZADO (tol ±0.5)'),
]

CUSTOMER_CODI = 'LOS'
FIT_TYPE_CODI = 'REGULAR'
TENANT = 'fhort'


# ═══════════════════════════════════════════════════════════════════════════════
# ADDENDUM — Neteja de material LOS antic (Agus 2026-07-18). Esborrat, commit propi.
# Per CLAU NATURAL. Guard al command: STOP si hi ha referències vives fora de les
# cascades pròpies (regles/scope del ruleset, talles del system).
# ═══════════════════════════════════════════════════════════════════════════════
# Rulesets orfes de la llei d'identitat (origen=None, item=None) — per nom + customer LOS.
DELETE_RULESETS_BY_NOM = [
    'LOS Kids Knit Regular 2Y - 12Y',       # id=104 al cens; penja de GIRL_LOS_03
    'EU ALPHA LOS TOP KNIT REGULAR V01',    # id=111 al cens; penja de MAN_LOS_01
]
# Size systems germans duplicats de GIRL_LOS_01 — per codi. Esborrar DESPRÉS dels rulesets
# (104 penja de GIRL_LOS_03 amb FK PROTECT).
DELETE_SIZE_SYSTEMS_BY_CODI = ['GIRL_LOS_02', 'GIRL_LOS_03']

# OPCIÓ 2 (Agus 2026-07-18): "esborrar només el net". Subconjunt sense cap ref viva al cens:
# ruleset 111 + system GIRL_LOS_02. 104 + GIRL_LOS_03 (sostenen 4 SizingProfile default del
# tenant) queden com a DEUTE, es resolen al domini SizingProfile en el futur. El flag
# --only-clean del command usa aquestes llistes i re-verifica refs (nova ref → STOP).
ONLY_CLEAN_RULESETS_BY_NOM = ['EU ALPHA LOS TOP KNIT REGULAR V01']
ONLY_CLEAN_SIZE_SYSTEMS_BY_CODI = ['GIRL_LOS_02']
