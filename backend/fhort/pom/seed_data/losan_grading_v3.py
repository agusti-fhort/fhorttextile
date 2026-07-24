"""Config versionable de la re-sembra grading v3 LOSAN (PAS 3).

Cada cel·la compleix l'ESPEC de DIAGNOSI_GRADING_V3.md: origen CLIENT_RUN + customer LOS +
size_system + targets M2M PLENS + construction FK + fit REGULAR + garment_type_item=NULL +
ABAST (garment_group quan basta; RuleSetScopeNode a items quan cal tall fi) + UN SizingProfile.
Regles NOMÉS via àlies LOS→POM consolidat (PAS 4). Noms SENSE temporada.

Fonts de regles: JSON v1/v2 (ja al repo) + grading_rules_v3_delta.json. Font per cel·la:
  - {'delta': '<cella>'}          → grading_rules_v3_delta.json (camp `alias`+`inc`)
  - {'v1_item': '<item>'}         → grading_rules_losan_ss27_v1.json contenidors_complets (alias_fitxa)
  - {'v2': ('<system>','<item>')} → grading_rules_losan_ss27_v2.json contenidors (alias)

profile_target = target ÚNIC del SizingProfile (representatiu); garment_type = FK obligatori
del SizingProfile (tipus representatiu de l'abast). scope: {'group':codi} o {'items':[codes]}.
"""

CUSTOMER_CODI = 'LOS'
FIT_CODI = 'REGULAR'
TENANT = 'fhort'

# Els 18 rulesets rebutjats (v1/v2): customer LOS + origen CLIENT_RUN + nom acaba en 'SS27'.
DELETE_MATCH = {'customer_codi': 'LOS', 'origen': 'CLIENT_RUN', 'nom__endswith': 'SS27'}

# Rename dels 10 size systems (codi → nom nou EN). Codis intactes.
RENAME_SYSTEMS = {
    'NEWBORN_LOS_01':    'LOS New Born 0-24M',
    'BABY_LOS_01':       'LOS Baby 3-36M',
    'GIRL_LOS_01':       'LOS Kids Girl 2-12Y',
    'BOY_LOS_01':        'LOS Kids Boy 2-12Y',
    'YOUTH_GIRL_LOS_01': 'LOS Teen Girl 8-16Y',
    'YOUTH_BOY_LOS_01':  'LOS Teen Boy 8-16Y',
    'WOMAN_LOS_01':      'LOS Woman Alpha XS-3XL',
    'MAN_LOS_01':        'LOS Man Alpha S-6XL',
    'WOMAN_NUM_LOS_01':  'LOS Woman Numeric 36-52',
    'MAN_NUM_LOS_01':    'LOS Man Numeric 38-58',
}

# Les 14 cel·les amb font (les 16 del gate menys Home Knit/BERG i Teen Girl Knit/ONA, sense font).
CELLS = [
    {'nom': 'LOS New Born Knit — Tops', 'system': 'NEWBORN_LOS_01',
     'targets': ['NEWBORN_GIRL', 'NEWBORN_BOY', 'NEWBORN_UNISEX'], 'construction': 'KNIT',
     'profile_target': 'NEWBORN_GIRL', 'garment_type': 'NEWBORN',
     'scope': {'items': ['baby_top', 'baby_bodysuit']}, 'break': None,
     'source': {'delta': 'LOS New Born Knit — Tops'}},
    {'nom': 'LOS New Born Knit — Bottoms', 'system': 'NEWBORN_LOS_01',
     'targets': ['NEWBORN_GIRL', 'NEWBORN_BOY', 'NEWBORN_UNISEX'], 'construction': 'KNIT',
     'profile_target': 'NEWBORN_GIRL', 'garment_type': 'NEWBORN',
     'scope': {'items': ['baby_leggings', 'baby_bloomers']}, 'break': None,
     'source': {'delta': 'LOS New Born Knit — Bottoms'}},
    {'nom': 'LOS New Born Knit — Onepieces', 'system': 'NEWBORN_LOS_01',
     'targets': ['NEWBORN_GIRL', 'NEWBORN_BOY', 'NEWBORN_UNISEX'], 'construction': 'KNIT',
     'profile_target': 'NEWBORN_GIRL', 'garment_type': 'NEWBORN',
     'scope': {'items': ['baby_sleepsuit', 'baby_sleepbag', 'booties']}, 'break': None,
     'source': {'delta': 'LOS New Born Knit — Onepieces'}},
    {'nom': 'LOS Baby Knit — Tops', 'system': 'BABY_LOS_01',
     'targets': ['BABY_GIRL', 'BABY_BOY'], 'construction': 'KNIT',
     'profile_target': 'BABY_GIRL', 'garment_type': 'NEWBORN',
     'scope': {'items': ['baby_top', 'baby_bodysuit']}, 'break': None,
     'source': {'v2': ('BABY_LOS_01', 'baby_top')}},
    {'nom': 'LOS Kids Girl — Dresses', 'system': 'GIRL_LOS_01',
     'targets': ['KID_GIRL'], 'construction': 'KNIT',
     'profile_target': 'KID_GIRL', 'garment_type': 'DRESSES',
     'scope': {'group': 'DRESSES'}, 'break': '9/10',
     'source': {'v1_item': 'dress_simple'}},
    {'nom': 'LOS Kids Boy Woven — Bottoms', 'system': 'BOY_LOS_01',
     'targets': ['KID_BOY'], 'construction': 'WOVEN',
     'profile_target': 'KID_BOY', 'garment_type': 'TAILORED_PANTS',
     'scope': {'group': 'BOTTOMS'}, 'break': '9/10',
     'source': {'v2': ('BOY_LOS_01', 'jeans')}},
    {'nom': 'LOS Teen Boy Knit — Tops', 'system': 'YOUTH_BOY_LOS_01',
     'targets': ['TEEN_BOY'], 'construction': 'KNIT',
     'profile_target': 'TEEN_BOY', 'garment_type': 'JERSEY_TOPS',
     'scope': {'group': 'TOPS'}, 'break': None,
     'source': {'delta': 'LOS Teen Boy Knit — Tops'}},
    {'nom': 'LOS Teen Boy Woven — Shirts', 'system': 'YOUTH_BOY_LOS_01',
     'targets': ['TEEN_BOY'], 'construction': 'WOVEN',
     'profile_target': 'TEEN_BOY', 'garment_type': 'BUTTONED_TOPS',
     'scope': {'group': 'TOPS'}, 'break': None,
     'source': {'delta': 'LOS Teen Boy Woven — Shirts'}},
    {'nom': 'LOS Teen Boy Woven — Bottoms', 'system': 'YOUTH_BOY_LOS_01',
     'targets': ['TEEN_BOY'], 'construction': 'WOVEN',
     'profile_target': 'TEEN_BOY', 'garment_type': 'TAILORED_PANTS',
     'scope': {'group': 'BOTTOMS'}, 'break': None,
     'source': {'v2': ('YOUTH_BOY_LOS_01', 'trousers')}},
    {'nom': 'LOS Teen Girl — Bottoms', 'system': 'YOUTH_GIRL_LOS_01',
     'targets': ['TEEN_GIRL'], 'construction': 'WOVEN',
     'profile_target': 'TEEN_GIRL', 'garment_type': 'TAILORED_PANTS',
     'scope': {'group': 'BOTTOMS'}, 'break': '14',
     'source': {'v2': ('YOUTH_GIRL_LOS_01', 'trousers')}},
    {'nom': 'LOS Teen Girl Stretch — Swimwear', 'system': 'YOUTH_GIRL_LOS_01',
     'targets': ['TEEN_GIRL'], 'construction': 'STRETCH_KNIT',
     'profile_target': 'TEEN_GIRL', 'garment_type': 'SWIMWEAR',
     'scope': {'group': 'SWIMWEAR'}, 'break': None,
     'source': {'v1_item': 'bikini'}},
    {'nom': 'LOS Woman Knit — Tops', 'system': 'WOMAN_LOS_01',
     'targets': ['WOMAN'], 'construction': 'KNIT',
     'profile_target': 'WOMAN', 'garment_type': 'JERSEY_TOPS',
     'scope': {'group': 'TOPS'}, 'break': None,
     'source': {'v2': ('WOMAN_LOS_01', 't_shirt')}},
    {'nom': 'LOS Woman Woven — Bottoms', 'system': 'WOMAN_NUM_LOS_01',
     'targets': ['WOMAN'], 'construction': 'WOVEN',
     'profile_target': 'WOMAN', 'garment_type': 'TAILORED_PANTS',
     'scope': {'group': 'BOTTOMS'}, 'break': None,
     'source': {'v2': ('WOMAN_NUM_LOS_01', 'trousers')}},
    {'nom': 'LOS Man Woven — Bottoms', 'system': 'MAN_NUM_LOS_01',
     'targets': ['MAN'], 'construction': 'WOVEN',
     'profile_target': 'MAN', 'garment_type': 'TAILORED_PANTS',
     'scope': {'group': 'BOTTOMS'}, 'break': None,
     'source': {'v2': ('MAN_NUM_LOS_01', 'trousers')}},
]
