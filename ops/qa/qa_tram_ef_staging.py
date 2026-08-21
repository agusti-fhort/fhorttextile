#!/usr/bin/env python
"""QA DEL TRAM E+F SOBRE STAGING — model de prova PROPI, mai el banc (2026-08-21).

    cd /var/www/ftt-staging/backend
    venv/bin/python ../ops/qa/qa_tram_ef_staging.py [--neteja]

Què fa, i per què així:

  · Crea (o reutilitza) el model `QA-TRAMF-0001` al tenant `fhort` amb el MATEIX sistema de
    talles del banc (ALPHA_EU_W) i run `XS·S·M·L·XL`, base `S`. **No toca el 1383**: el banc és
    dada viva i el gate el mesura abans i després de cada tram.
  · Escriu la regla **per la porta de veritat** (`set_pom_regim_view`, la que crida la pantalla
    de Graduació) i propaga amb el motor real. No fabrica cap `GradedSpec` a mà.
  · Comprova el **cas de la Montse**: general 2 · interval `S→L` 3 → S→M 3, M→L 3, i XL torna
    a 2. Cel·les exactes.
  · Comprova el **TRAM E**: una regla STEP sense valors treu el valor de la talla base a totes
    les talles i la propagació serveix la LLISTA DE TREBALL MANUAL (`step_base_copiada`), que
    el payload de la taula també deriva per fila.

🚩 Aquest script ESCRIU (crea un model de prova i el gradua). No és el banc, que és read-only.
Amb `--neteja` esborra el model de prova i tot el que en penja.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402
django.setup()

from django.contrib.auth import get_user_model            # noqa: E402
from django_tenants.utils import schema_context           # noqa: E402
from rest_framework.test import APIRequestFactory, force_authenticate  # noqa: E402

CODI = 'QA-TRAMF-0001'
RUN = ['XS', 'S', 'M', 'L', 'XL']
BASE = 'S'
BASE_VAL = 100.0
MONTSE = {'XS': 98.0, 'S': 100.0, 'M': 103.0, 'L': 106.0, 'XL': 108.0}


def _ok(cond, text):
    print(f"  {'✅' if cond else '❌'} {text}")
    return bool(cond)


def main(neteja=False):
    with schema_context('fhort'):
        from fhort.fitting.models import GradedSpec, SizeFitting
        from fhort.fitting.services import vigent_grading_version
        from fhort.models_app.models import BaseMeasurement, Model
        from fhort.models_app.views import (generate_grading_view, measurements_table_view,
                                            set_pom_regim_view)
        from fhort.pom.models import POMMaster, SizeSystem

        if neteja:
            n, _ = Model.objects.filter(codi_intern=CODI).delete()
            print(f"model de prova esborrat ({n} objectes)")
            return 0

        user = get_user_model().objects.get(username='a.devant@fhort.cat')
        ss = SizeSystem.objects.get(codi='ALPHA_EU_W')
        pom = POMMaster.objects.filter(codi_client='A').order_by('pk').first()
        assert pom is not None, 'cal un POM al catàleg del tenant'

        model = Model.objects.filter(codi_intern=CODI).first()
        if model is None:
            model = Model.objects.create(
                codi_intern=CODI, codi_tenant='QA', any=2027, sequencial=901,
                temporada='SS', nom_prenda='QA tram E+F', size_system=ss,
                size_run_model='·'.join(RUN), base_size_label=BASE)
        BaseMeasurement.objects.update_or_create(
            model=model, pom=pom, capa='exterior', instancia='', garment='',
            defaults={'base_value_cm': BASE_VAL, 'is_active': True, 'ordre': 0})
        sf = SizeFitting.objects.filter(model=model).order_by('numero').first()
        print(f"MODEL DE PROVA · {CODI} (pk={model.pk}) · SF#{sf.pk} · POM {pom.codi_client} "
              f"base {BASE}={BASE_VAL}\n")

        def _post(view, body, *args):
            r = APIRequestFactory().post('/x/', body, format='json')
            force_authenticate(r, user=user)
            return view(r, *args)

        def _get(view, *args):
            r = APIRequestFactory().get('/x/')
            force_authenticate(r, user=user)
            return view(r, *args)

        def _taula():
            gv = vigent_grading_version(sf)
            return {s.size_label: float(s.graded_value_cm)
                    for s in GradedSpec.objects.filter(grading_version=gv, pom=pom)}

        verds = []

        # ── F · EL CAS DE LA MONTSE ─────────────────────────────────────────────────────
        print("▸ TRAM F · cas Montse — general 2 · S→L 3 · XL torna a 2")
        resp = _post(set_pom_regim_view,
                     {'logica': 'LINEAR', 'increment_base': 2,
                      'breaks': [{'inici': 'S', 'final': 'L', 'delta': 3}]},
                     model.pk, pom.pk)
        verds.append(_ok(resp.status_code == 200, f"la porta desa la regla ({resp.status_code})"))
        verds.append(_ok(resp.data.get('breaks') == [{'inici': 'S', 'final': 'L', 'delta': 3.0}],
                         f"la resposta diu el relleu: {resp.data.get('breaks')}"))
        resp = _post(generate_grading_view, {'new_version': True, 'allow_reopen_sealed': True},
                     model.pk)
        verds.append(_ok(resp.status_code == 200,
                         f"propaga ({resp.status_code} · {getattr(resp, 'data', {}).get('error', '')})"))
        taula = _taula()
        print(f"     cel·les: {taula}")
        verds.append(_ok(taula == MONTSE, f"cel·les exactes {MONTSE}"))

        resp = _get(measurements_table_view, model.pk)
        fila = next((f for f in resp.data['rows'] if f['pom_id'] == pom.pk), {})
        verds.append(_ok(fila.get('breaks') == [{'inici': 'S', 'final': 'L', 'delta': 3.0}],
                         "el payload de la taula serveix els intervals"))
        verds.append(_ok(resp.data.get('run_sistema')[:3] == ['XXS', 'XS', 'S'],
                         f"i el run del SISTEMA per al picker: {resp.data.get('run_sistema')}"))

        # ── F · LA PORTA REBUTJA EL QUE NO VOL DIR RES ──────────────────────────────────
        print("\n▸ TRAM F · la porta (les quatre validacions més perilloses)")
        for cas, body, codi in (
            ('solapament', {'breaks': [{'inici': 'S', 'final': 'L', 'delta': 3},
                                       {'inici': 'L', 'final': 'XL', 'delta': 4}]},
             'BREAKS_SOLAPAMENT'),
            ('ordre invertit', {'breaks': [{'inici': 'L', 'final': 'S', 'delta': 3}]},
             'BREAKS_ORDRE'),
            ('talla forana', {'breaks': [{'inici': '46', 'final': 'XL', 'delta': 3}]},
             'BREAKS_TALLA_FORANA'),
            ('Δ redundant', {'breaks': [{'inici': 'S', 'final': 'L', 'delta': 2}]},
             'BREAKS_DELTA_REDUNDANT'),
            ('LINEAR+0 amb break', {'increment_base': 0, 'increment_break': 0,
                                    'talla_break_label': 'M', 'breaks': []},
             'LINEAR_INCREMENT_ZERO'),
        ):
            r = _post(set_pom_regim_view, body, model.pk, pom.pk)
            verds.append(_ok(r.status_code == 400 and r.data.get('codi') == codi,
                             f"{cas} → {r.status_code} {r.data.get('codi')}"))

        # ── E · STEP SENSE VALORS ───────────────────────────────────────────────────────
        print("\n▸ TRAM E · regla STEP sense valors → valor de la base + llista de treball")
        from fhort.models_app.models import ModelGradingRule
        ModelGradingRule.objects.filter(model=model, pom=pom).update(
            logica='STEP', valors_step=None, breaks=None)
        resp = _post(generate_grading_view, {'new_version': True, 'allow_reopen_sealed': True},
                     model.pk)
        verds.append(_ok(resp.status_code == 200, f"propaga ({resp.status_code})"))
        taula = _taula()
        print(f"     cel·les: {taula}")
        verds.append(_ok(taula == {s: BASE_VAL for s in RUN},
                         "totes les talles porten el valor de la talla base (cap fila desapareguda)"))
        pendents = resp.data.get('step_base_copiada')
        print(f"     avís   : {pendents}")
        verds.append(_ok(bool(pendents) and sorted(pendents[0]['talles']) == sorted(
            [s for s in RUN if s != BASE]),
            "la propagació serveix la llista de treball manual (POM × talles)"))
        resp = _get(measurements_table_view, model.pk)
        fila = next((f for f in resp.data['rows'] if f['pom_id'] == pom.pk), {})
        verds.append(_ok(sorted(fila.get('step_base_copiada') or []) == sorted(
            [s for s in RUN if s != BASE]),
            f"i la taula deriva la marca per fila: {fila.get('step_base_copiada')}"))

        print(f"\nVEREDICTE: {'✅ TOT VERD' if all(verds) else '❌ HI HA VERMELLS'} "
              f"({sum(verds)}/{len(verds)})")
        return 0 if all(verds) else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--neteja', action='store_true', help='esborra el model de prova i surt')
    sys.exit(main(**vars(ap.parse_args())))
