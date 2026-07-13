"""Script d'importació del master data Frappe → models Django.

Executar amb:

    cd /var/www/fhort-textile/backend
    source venv/bin/activate
    python manage.py tenant_command shell --schema=fhort < data/import_master.py

Per cada entitat usa get_or_create amb codi/name com a clau natural,
així es pot reexecutar de forma idempotent.
"""

import json
import sys
import traceback
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.db import transaction

from fhort.pom.models import (
    GarmentGroup,
    GarmentType,
    GradingRule,
    GradingRuleSet,
    POMCategory,
    POMMaster,
    SizeDefinition,
    SizeSystem,
)
from fhort.tasks.models import TipologiaModel

# Models opcionals (potser no existeixen encara).
try:
    from fhort.pom.models import FitType  # type: ignore
except ImportError:
    FitType = None  # noqa: N816


BASE = Path('/var/www/fhort-textile/backend/data/import')

_TOTALS = []


def _load(filename):
    return json.loads((BASE / filename).read_text(encoding='utf-8'))


def _bool(v, default=True):
    if v in (None, ''):
        return default
    if isinstance(v, str):
        return v.strip().lower() not in ('0', 'false', 'no', '')
    return bool(v)


def _str(v):
    return '' if v is None else str(v)


def _dec(v, default='0'):
    if v in (None, ''):
        return Decimal(default)
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _int(v, default=0):
    if v in (None, ''):
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _section(label, filename, fn):
    created = existed = errors = 0
    error_msgs = []
    try:
        rows = _load(filename)
    except FileNotFoundError:
        print(f'[SKIP] {label}: fitxer no trobat ({filename})')
        return
    except Exception as e:
        print(f'[ERROR] {label}: no s\'ha pogut llegir {filename}: {e}')
        return

    for row in rows:
        try:
            with transaction.atomic():
                was_created = fn(row)
            if was_created:
                created += 1
            else:
                existed += 1
        except Exception as e:
            errors += 1
            if len(error_msgs) < 5:
                error_msgs.append(f'  ! {row.get("name") or row}: {e.__class__.__name__}: {e}')

    total = created + existed + errors
    print(f'[{label:22s}]  llegits={total:4d}  creats={created:4d}  existents={existed:4d}  errors={errors:4d}')
    for m in error_msgs:
        print(m)
    _TOTALS.append((label, created, existed, errors))


# ──────────────────────────────────────────────────────────────
# a. POM_Category → POMCategory
# ──────────────────────────────────────────────────────────────
def _imp_pom_category(r):
    _, created = POMCategory.objects.get_or_create(
        codi=r['name'],
        defaults={
            'nom_en': _str(r.get('name_en')),
            'nom_ca': _str(r.get('name_cat')),
            'descripcio': _str(r.get('description')),
            'body_area': _str(r.get('body_area')),
            'display_order': _int(r.get('display_order')),
            'actiu': _bool(r.get('is_active')),
        },
    )
    return created


# ──────────────────────────────────────────────────────────────
# b. Garment_Group → GarmentGroup
# ──────────────────────────────────────────────────────────────
def _imp_garment_group(r):
    codi = r.get('group_code') or r['name']
    _, created = GarmentGroup.objects.get_or_create(
        codi=codi,
        defaults={
            'nom': _str(r.get('name_en') or r.get('name_cat') or codi),
            'descripcio': _str(r.get('grading_logic_note')),
            'actiu': _bool(r.get('is_active')),
        },
    )
    return created


# ──────────────────────────────────────────────────────────────
# c. Garment_Type → GarmentType
# ──────────────────────────────────────────────────────────────
def _imp_garment_type(r):
    codi = r.get('type_code') or r['name']
    _, created = GarmentType.objects.get_or_create(
        codi_client=codi,
        defaults={
            'nom_client': _str(r.get('name_cat') or r.get('name_en') or codi),
            'grup': _str(r.get('family')),
            'actiu': _bool(r.get('is_active')),
        },
    )
    return created


# ──────────────────────────────────────────────────────────────
# d. Fit_Type → FitType (només si el model existeix)
# ──────────────────────────────────────────────────────────────
def _imp_fit_type(r):
    if FitType is None:
        raise RuntimeError('model FitType no definit')
    codi = r.get('fit_code') or r['name']
    _, created = FitType.objects.get_or_create(
        codi=codi,
        defaults={
            'nom': _str(r.get('name_en') or codi),
            'actiu': _bool(r.get('is_active')),
        },
    )
    return created


# ──────────────────────────────────────────────────────────────
# e. Size_System → SizeSystem
# ──────────────────────────────────────────────────────────────
def _imp_size_system(r):
    codi = r.get('system_code') or r['name']
    _, created = SizeSystem.objects.get_or_create(
        codi=codi,
        defaults={
            'nom': _str(r.get('name_en') or codi),
            'descripcio': _str(r.get('size_basis') or r.get('market_standard')),
            'actiu': _bool(r.get('is_active')),
        },
    )
    return created


# ──────────────────────────────────────────────────────────────
# f. Size_Definition → SizeDefinition
# ──────────────────────────────────────────────────────────────
def _imp_size_definition(r):
    ss = SizeSystem.objects.filter(codi=r.get('system_code')).first()
    if not ss:
        raise LookupError(f'SizeSystem {r.get("system_code")} no trobat')
    # numeric only si parsejable
    val = r.get('body_chest_cm') or r.get('body_waist_cm') or r.get('body_hip_cm')
    valor_num = None
    if val not in (None, ''):
        try:
            valor_num = Decimal(str(val))
        except (InvalidOperation, ValueError):
            valor_num = None
    _, created = SizeDefinition.objects.get_or_create(
        size_system=ss,
        etiqueta=r['size_label'],
        defaults={
            'ordre': _int(r.get('display_order')),
            'valor_numeric': valor_num,
        },
    )
    return created


# ──────────────────────────────────────────────────────────────
# g. POM_Master → POMMaster (FK POMCategory; esquema anglès)
# ──────────────────────────────────────────────────────────────
def _imp_pom_master(r):
    cat = None
    if r.get('category'):
        cat = POMCategory.objects.filter(codi=r['category']).first()
    codi = r.get('pom_code') or r['name']
    _, created = POMMaster.objects.get_or_create(
        codi_client=codi,
        defaults={
            'nom_client': _str(r.get('name_en') or codi),
            'categoria': cat,
            'notes': _str(r.get('notes')),
            'actiu': _bool(r.get('is_active')),
        },
    )
    return created


# ──────────────────────────────────────────────────────────────
# h. Grading_Rule_Set → GradingRuleSet (FK GarmentGroup, SizeSystem)
# ──────────────────────────────────────────────────────────────
def _imp_grading_rule_set(r):
    gg = GarmentGroup.objects.filter(codi=r.get('garment_group')).first()
    ss = SizeSystem.objects.filter(codi=r.get('size_system')).first()
    if not ss:
        raise LookupError(f'SizeSystem {r.get("size_system")} no trobat')
    nom = r.get('set_code') or r['name']
    _, created = GradingRuleSet.objects.get_or_create(
        nom=nom,
        defaults={
            'garment_group': gg,
            'size_system': ss,
            'actiu': _bool(r.get('is_active')),
        },
    )
    return created


# ──────────────────────────────────────────────────────────────
# i. Grading_Rule → GradingRule (FK GradingRuleSet + POMMaster)
# ──────────────────────────────────────────────────────────────
def _imp_grading_rule(r):
    rs = GradingRuleSet.objects.filter(nom=r.get('rule_set')).first()
    if not rs:
        raise LookupError(f'GradingRuleSet {r.get("rule_set")} no trobat')
    pom = POMMaster.objects.filter(codi_client=r.get('pom')).first()
    if not pom:
        raise LookupError(f'POMMaster {r.get("pom")} no trobat')
    # talla_base obligatòria: agafem una talla del size_system del rule_set
    talla_base = None
    if rs.size_system_id:
        talla_base = SizeDefinition.objects.filter(size_system=rs.size_system).order_by('ordre').first()
    if not talla_base:
        raise LookupError(f'No hi ha SizeDefinition al sistema {rs.size_system_id}')

    grading_type = (r.get('grading_type') or 'LINEAR').upper()
    if grading_type not in ('LINEAR', 'STEP', 'FIXED', 'ZERO', 'EXCEPTION'):
        grading_type = 'LINEAR'

    _, created = GradingRule.objects.get_or_create(
        rule_set=rs,
        pom=pom,
        defaults={
            'talla_base': talla_base,
            'logica': grading_type,
            'valor_base': Decimal('0'),
            'increment': _dec(r.get('increment_cm')),
            'actiu': _bool(r.get('is_active')),
        },
    )
    return created


# j. Grading_Exception — JUBILAT (G6/1a, 2026-07-13). El model `pom.GradingException` ja no
# existeix: era una excepció penjada de la plantilla compartida i la va rellevar
# `models_app.ModelGradingOverride` (acotat a un sol model). Si un `Grading_Exception.json`
# legacy encara existeix, aquest importador ja no el llegeix — a propòsit.


# ──────────────────────────────────────────────────────────────
# k. Tipologia_model → TipologiaModel (6 camps de slots)
# ──────────────────────────────────────────────────────────────
def _imp_tipologia_model(r):
    gt = None
    if r.get('garment_type'):
        gt = GarmentType.objects.filter(codi_client=r['garment_type']).first()
    _, created = TipologiaModel.objects.get_or_create(
        codi=r['name'],
        defaults={
            'nom': _str(r.get('nom')),
            'familia': _str(r.get('familia')),
            'familia_codi': _str(r.get('familia_codi')),
            'garment_type': gt,
            'complexitat': r.get('complexitat'),
            'patrons_aprox': r.get('patrons_aprox'),
            # Nota: el JSON usa "slots_digitalització" amb tilde — el camp Django no.
            'slots_cad_client': _dec(r.get('slots_cad_client')),
            'slots_digitalitzacio': _dec(r.get('slots_digitalització') or r.get('slots_digitalitzacio')),
            'slots_des_de_zero': _dec(r.get('slots_des_de_zero')),
            'slots_conf_proto': _dec(r.get('slots_conf_proto')),
            'slots_conf_proto_sample': _dec(r.get('slots_conf_proto_sample')),
            'slots_conf_proto_sample_size': _dec(r.get('slots_conf_proto_sample_size')),
            'actiu': _bool(r.get('actiu')),
            'notes': _str(r.get('notes')),
        },
    )
    return created


# ──────────────────────────────────────────────────────────────
# Execució en ordre estricte de dependències
# ──────────────────────────────────────────────────────────────
print('\n========== IMPORT MASTER DATA FRAPPE → DJANGO ==========\n')

_section('a. POMCategory',     'POM_Category.json',     _imp_pom_category)
_section('b. GarmentGroup',    'Garment_Group.json',    _imp_garment_group)
_section('c. GarmentType',     'Garment_Type.json',     _imp_garment_type)
if FitType is not None:
    _section('d. FitType',     'Fit_Type.json',         _imp_fit_type)
else:
    print('[d. FitType            ]  SKIP — model no definit')
_section('e. SizeSystem',      'Size_System.json',      _imp_size_system)
_section('f. SizeDefinition',  'Size_Definition.json',  _imp_size_definition)
_section('g. POMMaster',       'POM_Master.json',       _imp_pom_master)
_section('h. GradingRuleSet',  'Grading_Rule_Set.json', _imp_grading_rule_set)
_section('i. GradingRule',     'Grading_Rule.json',     _imp_grading_rule)
# j. GradingException — jubilada (G6/1a); cap secció.
_section('k. TipologiaModel',  'Tipologia_model.json',  _imp_tipologia_model)


# ──────────────────────────────────────────────────────────────
# Recompte final
# ──────────────────────────────────────────────────────────────
print('\n========== RECOMPTE FINAL ==========')
print(f'{"POMCategory":24s}  total={POMCategory.objects.count()}')
print(f'{"GarmentGroup":24s}  total={GarmentGroup.objects.count()}')
print(f'{"GarmentType":24s}  total={GarmentType.objects.count()}')
print(f'{"SizeSystem":24s}  total={SizeSystem.objects.count()}')
print(f'{"SizeDefinition":24s}  total={SizeDefinition.objects.count()}')
print(f'{"POMMaster":24s}  total={POMMaster.objects.count()}')
print(f'{"GradingRuleSet":24s}  total={GradingRuleSet.objects.count()}')
print(f'{"GradingRule":24s}  total={GradingRule.objects.count()}')
print(f'{"TipologiaModel":24s}  total={TipologiaModel.objects.count()}')

tot_creats = sum(t[1] for t in _TOTALS)
tot_exist = sum(t[2] for t in _TOTALS)
tot_err = sum(t[3] for t in _TOTALS)
print(f'\nTOTALS: creats={tot_creats}  existents={tot_exist}  errors={tot_err}')
