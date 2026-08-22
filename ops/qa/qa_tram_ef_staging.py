#!/usr/bin/env python
"""QA DELS TRAMS E+F SOBRE STAGING — model de prova PROPI, mai el banc (2026-08-21).

    cd /var/www/ftt-staging/backend
    venv/bin/python ../ops/qa/qa_tram_ef_staging.py [--neteja]

Munta (o reutilitza) el model `QA-TRAMF-0001` al tenant `fhort` amb el sistema de talles del
banc (ALPHA_EU_W), run `XS·S·M·L·XL`, base `S`, i **dos POMs que exerciten un tram cadascun**:

    · `A`  → LINEAR amb INTERVAL `S→L +3` sobre un Δ general de 2   ......... TRAM F
    · `B`  → STEP **sense valors**: totes les talles amb el valor base prestat  TRAM E

Tot passa per les PORTES de veritat (`set_pom_regim_view`, `set_step_valor_view`,
`generate_grading_view`) i pel motor real: aquí no es fabrica cap `GradedSpec` a mà.

**El 1383 no es toca**: és el banc, i el gate el mesura abans i després de cada tram.

🚩 Aquest script ESCRIU (crea i gradua un model de prova). Amb `--neteja` l'esborra. Sense
`--neteja` el deixa VIU i amb les dues formes a la vista, que és el que la QA de pantalla vol.
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
BASE_A, BASE_B = 100.0, 60.0
#: TRAM F — general 2 · interval S→L 3 → S→M 3, M→L 3, i XL TORNA A 2 (cas de la Montse).
MONTSE = {'XS': 98.0, 'S': 100.0, 'M': 103.0, 'L': 106.0, 'XL': 108.0}


def _ok(cond, text):
    print(f"  {'✅' if cond else '❌'} {text}")
    return bool(cond)


def main(neteja=False):
    with schema_context('fhort'):
        from fhort.fitting.models import GradedSpec, SizeFitting
        from fhort.fitting.services import vigent_grading_version
        from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
        from fhort.models_app.views import (generate_grading_view, measurements_table_view,
                                            set_pom_regim_view, set_step_valor_view)
        from fhort.pom.models import POMMaster, SizeSystem

        if neteja:
            n, _ = Model.objects.filter(codi_intern=CODI).delete()
            print(f"model de prova esborrat ({n} objectes)")
            return 0

        user = get_user_model().objects.get(username='a.devant@fhort.cat')
        ss = SizeSystem.objects.get(codi='ALPHA_EU_W')
        pom_a = POMMaster.objects.filter(codi_client='A').order_by('pk').first()
        pom_b = POMMaster.objects.filter(codi_client='B').order_by('pk').first()
        assert pom_a and pom_b, 'calen dos POMs al catàleg del tenant'

        model = Model.objects.filter(codi_intern=CODI).first()
        if model is None:
            model = Model.objects.create(
                codi_intern=CODI, codi_tenant='QA', any=2027, sequencial=901,
                temporada='SS', nom_prenda='QA tram E+F', size_system=ss,
                size_run_model='·'.join(RUN), base_size_label=BASE)
        for pom, val, ordre in ((pom_a, BASE_A, 0), (pom_b, BASE_B, 1)):
            BaseMeasurement.objects.update_or_create(
                model=model, pom=pom, capa='exterior', instancia='', garment='',
                defaults={'base_value_cm': val, 'is_active': True, 'ordre': ordre})
        sf = SizeFitting.objects.filter(model=model).order_by('numero').first()
        print(f"MODEL DE PROVA · {CODI} (pk={model.pk}) · SF#{sf.pk}\n"
              f"  POM {pom_a.codi_client} base {BASE}={BASE_A} (TRAM F) · "
              f"POM {pom_b.codi_client} base {BASE}={BASE_B} (TRAM E)\n")

        def _post(view, body, *args):
            r = APIRequestFactory().post('/x/', body, format='json')
            force_authenticate(r, user=user)
            return view(r, *args)

        def _get(view, *args):
            r = APIRequestFactory().get('/x/')
            force_authenticate(r, user=user)
            return view(r, *args)

        def _taula(pom):
            gv = vigent_grading_version(sf)
            return {s.size_label: float(s.graded_value_cm)
                    for s in GradedSpec.objects.filter(grading_version=gv, pom=pom)}

        def _fila(pom):
            resp = _get(measurements_table_view, model.pk)
            return next(f for f in resp.data['rows'] if f['pom_id'] == pom.pk), resp.data

        def _propaga():
            return _post(generate_grading_view,
                         {'new_version': True, 'allow_reopen_sealed': True}, model.pk)

        verds = []

        # ── TRAM F · EL CAS DE LA MONTSE ────────────────────────────────────────────────
        print("▸ TRAM F · cas Montse — general 2 · S→L 3 · XL torna a 2")
        resp = _post(set_pom_regim_view,
                     {'logica': 'LINEAR', 'increment_base': 2,
                      'breaks': [{'inici': 'S', 'final': 'L', 'delta': 3}]},
                     model.pk, pom_a.pk)
        verds.append(_ok(resp.status_code == 200, f"la porta desa la regla ({resp.status_code})"))
        verds.append(_ok(resp.data.get('breaks') == [{'inici': 'S', 'final': 'L', 'delta': 3.0}],
                         f"la resposta diu el relleu: {resp.data.get('breaks')}"))
        # El POM B, mentrestant, és una STEP sense valors (el cas del TRAM E).
        ModelGradingRule.objects.update_or_create(
            model=model, pom=pom_b, garment='',
            defaults={'logica': 'STEP', 'valors_step': None, 'breaks': None,
                      'increment': 0, 'actiu': True, 'origen': 'MANUAL'})
        resp = _propaga()
        verds.append(_ok(resp.status_code == 200, f"propaga ({resp.status_code})"))
        taula = _taula(pom_a)
        print(f"     cel·les A: {taula}")
        verds.append(_ok(taula == MONTSE, f"cel·les exactes {MONTSE}"))

        fila_a, payload = _fila(pom_a)
        verds.append(_ok(fila_a.get('breaks') == [{'inici': 'S', 'final': 'L', 'delta': 3.0}],
                         "el payload de la taula serveix els intervals"))
        verds.append(_ok((payload.get('run_sistema') or [])[:3] == ['XXS', 'XS', 'S'],
                         f"i el run del SISTEMA per al picker: {payload.get('run_sistema')}"))

        # ── TRAM F · LA PORTA REBUTJA EL QUE NO VOL DIR RES ─────────────────────────────
        print("\n▸ TRAM F · la porta (les cinc validacions més perilloses)")
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
            r = _post(set_pom_regim_view, body, model.pk, pom_a.pk)
            verds.append(_ok(r.status_code == 400 and r.data.get('codi') == codi,
                             f"{cas} → {r.status_code} {r.data.get('codi')}"))

        # ── TRAM E · STEP SENSE VALORS ──────────────────────────────────────────────────
        print("\n▸ TRAM E · regla STEP sense valors → valor de la base + llista de treball")
        taula_b = _taula(pom_b)
        print(f"     cel·les B: {taula_b}")
        verds.append(_ok(taula_b == {s: BASE_B for s in RUN},
                         "totes les talles porten el valor de la talla base (cap fila desapareguda)"))
        fila_b, _ = _fila(pom_b)
        verds.append(_ok(sorted(fila_b.get('step_base_copiada') or [])
                         == sorted([s for s in RUN if s != BASE]),
                         f"la taula deriva la marca per fila: {fila_b.get('step_base_copiada')}"))

        # ── TRAM E · LA PORTA DEL VALOR VERMELL ─────────────────────────────────────────
        print("\n▸ TRAM E · la porta del valor vermell — escriu la REGLA, no un override")
        r = _post(set_step_valor_view, {'talla': 'L', 'valor': 66}, model.pk, pom_b.pk)
        verds.append(_ok(r.status_code == 400 and r.data.get('codi') == 'STEP_CAMI_INCOMPLET'
                         and r.data.get('talla_que_falta') == 'M',
                         f"camí incomplet → {r.status_code} {r.data.get('codi')} "
                         f"(falta la {r.data.get('talla_que_falta')})"))
        r = _post(set_step_valor_view, {'talla': BASE, 'valor': 61}, model.pk, pom_b.pk)
        verds.append(_ok(r.status_code == 400 and r.data.get('codi') == 'STEP_TALLA_BASE',
                         f"la talla base no hi entra → {r.data.get('codi')}"))

        r = _post(set_step_valor_view, {'talla': 'M', 'valor': 63}, model.pk, pom_b.pk)
        verds.append(_ok(r.status_code == 200 and r.data.get('delta') == 3.0,
                         f"M=63 → {r.status_code} · delta {r.data.get('delta')}"))
        verds.append(_ok(_taula(pom_b).get('M') == 63.0,
                         "la porta re-propaga in place: la cel·la ja val 63"))
        fila_b, _ = _fila(pom_b)
        verds.append(_ok('M' not in (fila_b.get('step_base_copiada') or []),
                         f"i la M surt del vermell: queden {fila_b.get('step_base_copiada')}"))

        # 🔑 EL QUE UN OVERRIDE NO HAURIA SOBREVISCUT: el llenç net d'una propagació conscient.
        resp = _propaga()
        verds.append(_ok(resp.status_code == 200 and _taula(pom_b).get('M') == 63.0,
                         "RE-PROPAGAR i el valor segueix intacte (és la regla, no un ajust)"))
        verds.append(_ok(_taula(pom_a) == MONTSE, "i la corba d'intervals tampoc no s'ha mogut"))

        # ── FITXA Q8b · el payload que la taula d'Escalat de la fitxa consumeix ──────────
        print("\n▸ FITXA Q8b · la fila de grading porta el relleu (i el 1383, el break d'1 tram)")
        verds.append(_ok(fila_a.get('breaks') and fila_a.get('logica') == 'LINEAR',
                         f"1384/A → breaks={fila_a.get('breaks')} (es pinta «S→L», motor)"))
        m1383 = Model.objects.filter(pk=1383).first()
        if m1383 is not None:
            resp = _get(measurements_table_view, 1383)
            amb_break = [f for f in resp.data['rows'] if f.get('talla_break_label')]
            amb_iv = [f for f in resp.data['rows'] if f.get('breaks')]
            verds.append(_ok(len(amb_break) > 0 and len(amb_iv) == 0,
                             f"1383 → {len(amb_break)} files amb break d'1 tram i {len(amb_iv)} "
                             "amb intervals: es pinta en convenció de DOCUMENT, com sempre"))

        print(f"\nVEREDICTE: {'✅ TOT VERD' if all(verds) else '❌ HI HA VERMELLS'} "
              f"({sum(verds)}/{len(verds)})")
        print(f"\nEl model queda VIU per a la QA de pantalla: POM {pom_a.codi_client} amb "
              f"INTERVAL i POM {pom_b.codi_client} amb cel·les prestades "
              f"({fila_b.get('step_base_copiada')}).")
        return 0 if all(verds) else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--neteja', action='store_true', help='esborra el model de prova i surt')
    sys.exit(main(**vars(ap.parse_args())))
