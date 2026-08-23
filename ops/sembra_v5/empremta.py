#!/usr/bin/env python
"""EMPREMTA v2 DEL CATÀLEG — EL GATE de la sembra v5 (2026-08-23).

    cd /var/www/ftt-staging/backend
    PGOPTIONS='-c default_transaction_read_only=on' \
      venv/bin/python ../ops/sembra_v5/empremta.py [--tenant fhort] [--out DIR]

Successora de `docs/ordres/empremta_cataleg_v5.py` (v1, 22/08), que es conserva perquè és qui
va produir la línia de base d'aquell dia. **Les dues NO són comparables entre elles**: la v2
canvia l'amplada del hash i afegeix dos blocs. Es compara v2 amb v2.

## Què canvia respecte de la v1, i per què

1. **HASH SENCER (64).** La v1 truncava el hash de fila a 16 caràcters. Amb 165 POMs el risc de
   col·lisió era teòric, però un gate que decideix si dos entorns diuen el mateix no ha de
   tenir cap truncament que explicar.
2. **BLOC DE FAMÍLIES.** El v5 remapa 23 famílies a 14 (S1/S5). Sense aquest bloc, dos entorns
   amb els mateixos POMs i **famílies diferents** donarien el mateix hash: la família entra al
   bloc de POMs pel seu codi, però el RÈTOL i l'ORDRE —el que el patronista veu a `/poms`— no
   hi entrava enlloc.
3. 🚩 **BLOC DE GLOBALS — I ÉS UNA AMPLIACIÓ DEL QUE EL BRIEF DEMANAVA.** El brief demanava
   «els 3 fitxers de detall»; aquí n'hi ha **quatre**. El motiu: S2 sembra 165 `POMGlobal` amb
   el «com es mesura» sencer, i el bloc de POMs només en veu el CODI (`pom_global_codi`). Amb
   tres fitxers, dos entorns amb el mateix lligam i **definicions diferents** —una tolerància
   retocada a mà, un punt A reescrit— passarien el gate com a idèntics. Un gate que no pot
   veure el que la sembra escriu no és el gate d'aquesta sembra.
4. **`separat_de_global` al final del bloc de POMs.** La sobirania és ara part del significat
   del catàleg (S3 la respecta i no la toca): dos entorns que discrepin en QUINS POMs són
   sobirans discrepen de debò. Va **al final**, com la v1 mana per als camps nous.

## El que NO canvia

🔒 **READ-ONLY PER CONSTRUCCIÓ**: només `SELECT`, cap import del motor, cap camí d'escriptura.
Es corre sempre amb `PGOPTIONS='-c default_transaction_read_only=on'`.

🔑 **ELS pk NO SÓN IDENTITAT** (llei R-POM). Tot va per CODI —el POM pel seu `codi_client`, la
família pel `POMCategory.codi`, el joc pel `nom`, el global pel `codi`— i les pks surten com a
columna informativa `pk_local` que **no entra a cap hash**.

🚨 **`breaks` i `talla_break_pos` HI SÓN.** El paquet LOSAN no els transporta (cens del 22/08,
§③): sense aquestes columnes, un cicle export→load donaria dos entorns per iguals havent perdut
tots els intervals del TRAM F.

🔑 **RÈGIM I LÒGICA SÓN DUES COLUMNES.** `logica` és el que hi ha desat; `regim` és el que el
motor n'entén (llei del 22/07: LINEAR amb delta 0 i sense break ÉS FIXED).

## Sortida — quatre CSV i un JSON, SEMPRE (també si un bloc surt buit)

  · `empremta_poms_<tenant>.csv`     una fila per `POMMaster`, per `codi_client`
  · `empremta_regles_<tenant>.csv`   una fila per `GradingRule` de catàleg
  · `empremta_families_<tenant>.csv` una fila per `POMCategory`, per `codi`
  · `empremta_globals_<tenant>.csv`  una fila per `POMGlobal` del schema, per `codi`
  · `empremta_<tenant>.json`         els hashes: un per bloc i un de global

## El gate

    # staging i PROD, EL MATEIX FITXER SENSE CAP CANVI
    PGOPTIONS='...' venv/bin/python ../ops/sembra_v5/empremta.py --out /tmp/emp_staging
    PGOPTIONS='...' venv/bin/python ../ops/sembra_v5/empremta.py --out /tmp/emp_prod
    diff -r /tmp/emp_staging /tmp/emp_prod

`hash_global` igual → els dos catàlegs diuen el mateix. Diferent → el `diff` diu quina fila i
quin camp, i llavors es repara LA CAUSA (quina comanda no va fer el que havia de fer), mai el
símptoma.
"""
import argparse
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                                'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402

django.setup()

from django_tenants.utils import schema_context  # noqa: E402

#: L'ORDRE DE LES COLUMNES ÉS DADA: entra al hash de fila. Un camp nou va AL FINAL i es diu a
#: l'acta (és el que s'ha fet amb `separat_de_global`).
COLS_POM = ('codi_client', 'nom_client', 'familia', 'unitat', 'actiu', 'pom_global_codi',
            'separat_de_global')
COLS_REGLA = ('joc', 'pom_codi', 'regim', 'logica', 'talla_base', 'increment_base',
              'increment_break', 'talla_break_label', 'talla_break_pos', 'breaks',
              'valors_step', 'increment_llegat', 'actiu')
COLS_FAMILIA = ('codi', 'nom_en', 'nom_ca', 'display_order', 'actiu')
COLS_GLOBAL = ('codi', 'nom_en', 'nom_ca', 'nom_es', 'categoria', 'unitat', 'actiu', 'scope',
               'body_section', 'start_point', 'end_point', 'reference_point', 'tol_prod_cm',
               'tol_samp_cm')


def _norm(v):
    """Text estable per a un valor. `None` i `''` NO són el mateix i no es col·lapsen."""
    if v is None:
        return '\\N'
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, (list, dict)):
        return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    if isinstance(v, float):
        return format(v, '.6f')
    return str(v)


def _hash_fila(cols, fila):
    """SHA-256 SENCER (64). La v1 el truncava a 16; un gate no ha de tenir truncaments."""
    return hashlib.sha256('\x1f'.join(_norm(fila[c]) for c in cols).encode()).hexdigest()


def empremta_poms():
    from fhort.pom.models import POMMaster
    files = []
    for p in (POMMaster.objects.select_related('pom_global', 'categoria')
              .order_by('codi_client', 'id')):
        f = {
            'codi_client': p.codi_client,
            'nom_client': p.nom_client,
            'familia': p.categoria.codi if p.categoria_id else None,
            # La UNITAT és la CASCADA tenant > global (sobirania del POM, 22/08).
            'unitat': (p.unitat or (p.pom_global.unitat if p.pom_global_id else '')) or None,
            'actiu': p.actiu,
            'pom_global_codi': p.pom_global.codi if p.pom_global_id else None,
            'separat_de_global': p.separat_de_global or None,
            'pk_local': p.pk,
        }
        f['hash_fila'] = _hash_fila(COLS_POM, f)
        files.append(f)
    return files


def empremta_regles():
    from fhort.pom.grading_regime import normalitza_logica
    from fhort.pom.models import GradingRule
    files = []
    for r in (GradingRule.objects.select_related('rule_set', 'pom', 'talla_base')
              .order_by('rule_set__nom', 'pom__codi_client', 'id')):
        breaks = r.breaks or []
        f = {
            'joc': r.rule_set.nom if r.rule_set_id else None,
            'pom_codi': r.pom.codi_client if r.pom_id else None,
            'regim': normalitza_logica(r.logica, r.increment_base, r.increment,
                                       r.increment_break, r.talla_break_label, breaks),
            'logica': r.logica,
            'talla_base': r.talla_base.etiqueta if r.talla_base_id else None,
            'increment_base': r.increment_base,
            'increment_break': r.increment_break,
            'talla_break_label': r.talla_break_label,
            'talla_break_pos': r.talla_break_pos,
            'breaks': breaks,
            'valors_step': r.valors_step or {},
            'increment_llegat': r.increment,
            'actiu': r.actiu,
            'pk_local': r.pk,
        }
        f['hash_fila'] = _hash_fila(COLS_REGLA, f)
        files.append(f)
    return files


def empremta_families():
    from fhort.pom.models import POMCategory
    files = []
    for c in POMCategory.objects.order_by('codi'):
        f = {'codi': c.codi, 'nom_en': c.nom_en, 'nom_ca': c.nom_ca,
             'display_order': c.display_order, 'actiu': c.actiu, 'pk_local': c.pk}
        f['hash_fila'] = _hash_fila(COLS_FAMILIA, f)
        files.append(f)
    return files


def empremta_globals():
    from fhort.pom.models import POMGlobal
    files = []
    for g in POMGlobal.objects.order_by('codi'):
        f = {c: getattr(g, c) for c in COLS_GLOBAL}
        f['pk_local'] = g.pk
        f['hash_fila'] = _hash_fila(COLS_GLOBAL, f)
        files.append(f)
    return files


def _escriu_csv(cami, cols, files):
    with open(cami, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(list(cols) + ['hash_fila', 'pk_local'])
        for f in files:
            w.writerow([_norm(f[c]) for c in cols] + [f['hash_fila'], f['pk_local']])


def _hash_bloc(files):
    """Hash del bloc = hash dels hashes de fila, EN ORDRE (i l'ordre ja és per codi)."""
    return hashlib.sha256(''.join(f['hash_fila'] for f in files).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--tenant', default='fhort')
    ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    with schema_context(a.tenant):
        blocs = {
            'poms': (COLS_POM, empremta_poms()),
            'regles': (COLS_REGLA, empremta_regles()),
            'families': (COLS_FAMILIA, empremta_families()),
            'globals': (COLS_GLOBAL, empremta_globals()),
        }

    hashes = {}
    for nom, (cols, files) in blocs.items():
        _escriu_csv(os.path.join(a.out, f'empremta_{nom}_{a.tenant}.csv'), cols, files)
        hashes[nom] = _hash_bloc(files)

    global_h = hashlib.sha256(''.join(hashes[n] for n in sorted(hashes)).encode()).hexdigest()
    regles = blocs['regles'][1]
    resum = {
        'versio': 2,
        'tenant': a.tenant,
        'n': {nom: len(files) for nom, (_c, files) in blocs.items()},
        'jocs': sorted({f['joc'] for f in regles if f['joc']}),
        'regles_amb_breaks': sum(1 for f in regles if f['breaks']),
        'hash': hashes,
        'hash_global': global_h,
        'columnes': {'poms': list(COLS_POM), 'regles': list(COLS_REGLA),
                     'families': list(COLS_FAMILIA), 'globals': list(COLS_GLOBAL)},
    }
    with open(os.path.join(a.out, f'empremta_{a.tenant}.json'), 'w', encoding='utf-8') as fh:
        json.dump(resum, fh, indent=2, ensure_ascii=False)
        fh.write('\n')

    print(f'\nEMPREMTA v2 · tenant `{a.tenant}`')
    for nom, (_c, files) in blocs.items():
        print(f'  {nom:<10} {len(files):>5}   hash {hashes[nom][:32]}…')
    print(f'  jocs ................. {resum["jocs"]}')
    print(f'  regles amb `breaks` .. {resum["regles_amb_breaks"]}')
    print(f'  HASH GLOBAL .......... {global_h}')
    print(f'\n  {a.out}/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
