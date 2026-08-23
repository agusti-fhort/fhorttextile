#!/usr/bin/env python
"""EMPREMTA DE CONTINGUT DEL CATÀLEG — el gate permanent de M2 (v5, 2026-08-22).

    cd /var/www/ftt-staging/backend
    PGOPTIONS='-c default_transaction_read_only=on' \
      venv/bin/python ../docs/ordres/empremta_cataleg_v5.py [--tenant fhort] [--out DIR]

🔒 READ-ONLY PER CONSTRUCCIÓ. Només fa `SELECT` (querysets `.values_list`), no importa cap
servei del motor i no té cap camí d'escriptura. Es corre sempre amb la barana de sessió
`PGOPTIONS='-c default_transaction_read_only=on'`, que s'ha de provar amb una escriptura sobre
una fila REAL abans de començar.

🔑 **ELS pk NO SÓN IDENTITAT** (llei R-POM del v4). Un mateix POM té pk diferent a staging i a
PROD, i comparar-los per pk donaria un delta sencer de soroll. L'empremta va **PER CODI**:
`POMMaster.codi_client` i, a les regles, el codi del POM al qual apunten. Cap pk entra a cap
hash ni a cap CSV: entren només com a columna informativa `pk_local`, que el delta IGNORA.

🚨 **`breaks` ÉS OBLIGATORI A L'EMPREMTA.** El paquet LOSAN **no el transporta** (0 ocurrències a
`export_losan_package.py` i a `load_losan_package.py`, verificat el 22/08), i és el punt únic
del relleu des del TRAM F. Una empremta que no el mirés donaria dos entorns per IGUALS havent
perdut tots els intervals pel camí. Per la mateixa raó hi entra `talla_break_pos`, que tampoc
viatja.

🔑 **RÈGIM I LÒGICA SÓN DUES COLUMNES, no una.** `logica` és el que hi ha DESAT; `regim` és el
que el motor n'entén després de `grading_regime.normalitza_logica` — i la llei d'Agus del
22/07 diu que **LINEAR amb delta 0 i sense break ÉS FIXED**. Dos entorns poden desar `logica`
diferent i comportar-se igual (i a l'inrevés): amb una sola columna, el delta mentiria en tots
dos sentits.

## Sortida

Tres fitxers a `--out` (default: el directori d'aquest script):

  · `empremta_poms_<tenant>.csv`     una fila per POMMaster, ordenada per `codi_client`
  · `empremta_regles_<tenant>.csv`   una fila per GradingRule de CATÀLEG (`pom.GradingRule`),
                                     ordenada per (joc, codi del POM)
  · `empremta_<tenant>.json`         els hashes: un per fila, un per bloc, i un de global

`ModelGradingRule` (les residents d'un model) **NO hi entra**: és dada de MODEL, no de catàleg,
i el que M2 mou és el catàleg.

## Com es fa el delta

    # a staging
    PGOPTIONS='...' venv/bin/python ../docs/ordres/empremta_cataleg_v5.py --out /tmp/emp_staging
    # a PROD, EL MATEIX FITXER SENSE CAP CANVI
    PGOPTIONS='...' venv/bin/python ../docs/ordres/empremta_cataleg_v5.py --out /tmp/emp_prod
    diff /tmp/emp_staging/empremta_poms_fhort.csv /tmp/emp_prod/empremta_poms_fhort.csv

Si els `hash_global` coincideixen, els dos catàlegs diuen el mateix. Si no, el `diff` dels CSV
diu exactament quina fila i quin camp.
"""
import argparse
import csv
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402
django.setup()

from django_tenants.utils import schema_context  # noqa: E402


#: Les columnes de cada bloc. L'ORDRE ÉS DADA: entra al hash de fila, i canviar-lo canvia
#: totes les empremtes. Si algun dia s'hi afegeix un camp, va AL FINAL i es diu a l'acta.
COLS_POM = ('codi_client', 'nom_client', 'familia', 'unitat', 'actiu', 'pom_global_codi')
COLS_REGLA = ('joc', 'pom_codi', 'regim', 'logica', 'talla_base', 'increment_base',
              'increment_break', 'talla_break_label', 'talla_break_pos', 'breaks',
              'valors_step', 'increment_llegat', 'actiu')


def _norm(v):
    """Text estable per a un valor. `None` i `''` NO són el mateix i no es col·lapsen."""
    if v is None:
        return '\\N'
    if isinstance(v, bool):
        return '1' if v else '0'
    if isinstance(v, (list, dict)):
        # `breaks` i `valors_step` són JSON: ordre de claus estable o el hash balla sol.
        return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    if isinstance(v, float):
        # Els decimals arriben com a Decimal; un float pel mig faria ballar el hash.
        return format(v, '.6f')
    return str(v)


def _hash_fila(cols, fila):
    return hashlib.sha256('\x1f'.join(_norm(fila[c]) for c in cols).encode()).hexdigest()[:16]


def empremta_poms(tenant):
    from fhort.pom.models import POMMaster
    files = []
    for p in (POMMaster.objects
              .select_related('pom_global', 'categoria')
              .order_by('codi_client', 'id')):
        # 🔑 La FAMÍLIA va pel seu CODI, mai per la pk: `POMCategory.pk` divergeix entre
        # entorns exactament igual que la del POM (cens de famílies, 22/08).
        f = {
            'codi_client': p.codi_client,
            'nom_client': p.nom_client,
            'familia': p.categoria.codi if p.categoria_id else None,
            # La UNITAT és la CASCADA tenant > global (sobirania del POM, 22/08), no el camp
            # cru: és el que el producte ensenya i el que un delta ha de comparar.
            'unitat': (p.unitat or (p.pom_global.unitat if p.pom_global_id else '')) or None,
            'actiu': p.actiu,
            'pom_global_codi': p.pom_global.codi if p.pom_global_id else None,
            'pk_local': p.pk,          # informatiu; NO entra al hash
        }
        f['hash_fila'] = _hash_fila(COLS_POM, f)
        files.append(f)
    return files


def empremta_regles(tenant):
    from fhort.pom.models import GradingRule
    from fhort.pom.grading_regime import normalitza_logica
    files = []
    for r in (GradingRule.objects
              .select_related('rule_set', 'pom', 'talla_base')
              .order_by('rule_set__nom', 'pom__codi_client', 'id')):
        breaks = r.breaks or []
        f = {
            # El JOC pel seu NOM: `GradingRuleSet.pk` no és identitat (a staging el Brownie
            # és 219 i el brief el citava com a #152 — la pk ja ha divergit).
            'joc': r.rule_set.nom if r.rule_set_id else None,
            'pom_codi': r.pom.codi_client if r.pom_id else None,
            # RÈGIM = el que el motor n'entén (LINEAR+0 sense break ÉS FIXED, llei 22/07).
            'regim': normalitza_logica(r.logica, r.increment_base, r.increment,
                                       r.increment_break, r.talla_break_label, breaks),
            'logica': r.logica,                      # el que hi ha DESAT
            'talla_base': r.talla_base.etiqueta if r.talla_base_id else None,
            'increment_base': r.increment_base,
            'increment_break': r.increment_break,
            'talla_break_label': r.talla_break_label,
            'talla_break_pos': r.talla_break_pos,
            'breaks': breaks,                        # 🚨 el paquet LOSAN NO el transporta
            'valors_step': r.valors_step or {},
            'increment_llegat': r.increment,         # camp llegat: ningú el llegeix, però viatja
            'actiu': r.actiu,
            'pk_local': r.pk,          # informatiu; NO entra al hash
        }
        f['hash_fila'] = _hash_fila(COLS_REGLA, f)
        files.append(f)
    return files


def _escriu_csv(cami, cols, files):
    with open(cami, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(list(cols) + ['hash_fila', 'pk_local'])
        for f in files:
            w.writerow([_norm(f[c]) for c in cols] + [f['hash_fila'], f['pk_local']])


def _hash_bloc(files):
    """Hash del bloc = hash dels hashes de fila, EN ORDRE. L'ordre ja és per codi, o sigui
    que dues bases amb les mateixes files i pks diferents donen el mateix bloc."""
    return hashlib.sha256(''.join(f['hash_fila'] for f in files).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--tenant', default='fhort')
    ap.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    with schema_context(a.tenant):
        poms = empremta_poms(a.tenant)
        regles = empremta_regles(a.tenant)

    c_poms = os.path.join(a.out, f'empremta_poms_{a.tenant}.csv')
    c_regl = os.path.join(a.out, f'empremta_regles_{a.tenant}.csv')
    _escriu_csv(c_poms, COLS_POM, poms)
    _escriu_csv(c_regl, COLS_REGLA, regles)

    h_poms, h_regl = _hash_bloc(poms), _hash_bloc(regles)
    resum = {
        'tenant': a.tenant,
        'n_poms': len(poms),
        'n_regles_cataleg': len(regles),
        'jocs': sorted({f['joc'] for f in regles if f['joc']}),
        'poms_amb_breaks': sum(1 for f in regles if f['breaks']),
        'hash_poms': h_poms,
        'hash_regles': h_regl,
        'hash_global': hashlib.sha256((h_poms + h_regl).encode()).hexdigest(),
        'columnes_poms': list(COLS_POM),
        'columnes_regles': list(COLS_REGLA),
    }
    c_json = os.path.join(a.out, f'empremta_{a.tenant}.json')
    with open(c_json, 'w', encoding='utf-8') as fh:
        json.dump(resum, fh, indent=2, ensure_ascii=False)
        fh.write('\n')

    print(f'\nEMPREMTA · tenant `{a.tenant}`')
    print(f'  POMMaster ............ {len(poms):>5}   hash {h_poms}')
    print(f'  GradingRule catàleg .. {len(regles):>5}   hash {h_regl}')
    print(f'  jocs ................. {resum["jocs"]}')
    print(f'  regles amb `breaks` .. {resum["poms_amb_breaks"]}')
    print(f'  HASH GLOBAL .......... {resum["hash_global"]}')
    print(f'\n  {c_poms}\n  {c_regl}\n  {c_json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
