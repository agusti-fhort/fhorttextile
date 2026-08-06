"""P0.3 (cicle) — entrar un valor → Gravar → veure'l a la CONSULTA → F5 → hi segueix.

`qa_p03_consulta_mesures.py` prova la LECTURA amb les dades que ja hi ha (el MILEY, en lectura
pura). Això prova el cicle SENCER amb el gest real, sobre un model **propi que es crea i
s'esborra**. MAI el MILEY (1308) ni cap model de ningú.

    1. crea un model de prova i li obre la tasca POM (el gest de `?mode=entry`)
    2. GRAVA un valor per `gravar-pom/`, que és el botó «Gravar» de Definició POM
    3. comprova que `base-stages/` —la font que llegeix la consulta— ja el serveix
    4. obre la CONSULTA al navegador amb el bundle real i hi busca el número
    5. esborra el model, passi el que passi

    backend/venv/bin/python ../ops/qa/qa_p03_cicle.py

Necessita el venv de Playwright a /tmp/qa-venv (v. qa_mount_modelsheet.py).
"""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

BACKEND = pathlib.Path(__file__).resolve().parents[2] / 'backend'
REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django                                     # noqa: E402
django.setup()

from django.contrib.auth import get_user_model    # noqa: E402
from django_tenants.utils import schema_context    # noqa: E402
from rest_framework.test import APIClient          # noqa: E402

HOST = {'HTTP_HOST': 'staging.fhorttextile.tech'}
MILEY = 1308
VALOR = 42.5
QA_PY = pathlib.Path('/tmp/qa-venv/bin/python')
FUM = pathlib.Path(__file__).resolve().parent / 'qa_p03_consulta_mesures.py'


def main():
    problemes = []
    with schema_context('fhort'):
        from fhort.models_app.models import Model
        from fhort.pom.models import SizeSystem
        from fhort.tasks.models import Customer, GarmentTypeItem

        u = get_user_model().objects.filter(is_superuser=True).first()
        c = APIClient()
        c.force_authenticate(user=u)

        cust = Customer.objects.get(codi='BRW')
        sysx = SizeSystem.objects.prefetch_related('talles').get(codi='WOMAN_BRW_01')
        talles = [d.etiqueta for d in sysx.talles.all().order_by('ordre')]
        item = (GarmentTypeItem.objects.filter(active=True, garment_type__isnull=False,
                                               pom_maps__isnull=False)
                .select_related('garment_type').distinct().order_by('id').first())
        if item is None:
            print('✗ cap item amb POMs mapats'); return 1

        r = c.post('/api/v1/models/create-wizard/', {
            'customer_id': cust.id, 'year': 2026, 'season': 'FW', 'ref_client': 'QA-P03',
            'target': 'WOMAN', 'garment_type_id': item.garment_type_id,
            'garment_type_item_id': item.id, 'size_system_id': sysx.id,
            'size_run': '·'.join(talles), 'base_size': talles[len(talles) // 2],
        }, format='json', **HOST)
        if r.status_code not in (200, 201):
            print(f'✗ no s\'ha pogut crear el model de prova: {r.status_code} {r.content[:200]}')
            return 1
        mid = r.json().get('id')
        assert mid != MILEY
        print(f'  · model de prova {mid} · item {item.name} · base {talles[len(talles)//2]}')

        tmp = pathlib.Path(tempfile.mkdtemp()) / 'qa_p03_prova.json'
        try:
            # ── 1 · el gest real: obrir la tasca POM ───────────────────────
            ro = c.post(f'/api/v1/models/{mid}/open-task/', {'code': 'pom'}, format='json', **HOST)
            if ro.status_code not in (200, 201):
                problemes.append(f'open-task pom → HTTP {ro.status_code}')

            sug = c.get(f'/api/v1/models/{mid}/poms-suggerits/', **HOST).json().get('poms', [])
            if not sug:
                print('✗ l\'item no suggereix cap POM'); return 1
            pom_id = sug[0]['pom_id']

            # ── 2 · GRAVAR ─────────────────────────────────────────────────
            r = c.post(f'/api/v1/models/{mid}/gravar-pom/', {
                'measurements': [{'pom_id': pom_id, 'base_value_cm': VALOR}], 'rules': [],
            }, format='json', **HOST)
            if r.status_code not in (200, 201):
                problemes.append(f'gravar-pom → HTTP {r.status_code}: {str(r.content[:300])}')
            else:
                print(f'  ✓ gravat · POM {sug[0].get("pom_code")} = {VALOR}')

            # ── 3 · la font que llegeix la CONSULTA ────────────────────────
            crides = {}
            for path, params in [
                (f'/api/v1/models/{mid}/', {}),
                (f'/api/v1/models/{mid}/taula-mesures/', {}),
                (f'/api/v1/models/{mid}/base-stages/', {}),
                ('/api/v1/size-checks/', {'model': mid, 'ordering': '-created_at', 'page_size': 1}),
            ]:
                resp = c.get(path, params, **HOST)
                if resp.status_code != 200:
                    problemes.append(f'{path} → HTTP {resp.status_code}')
                    continue
                crides[path] = resp.json()

            bs = crides.get(f'/api/v1/models/{mid}/base-stages/', {})
            fila = next((x for x in bs.get('rows', []) if x.get('pom_id') == pom_id), None)
            if fila is None:
                problemes.append('base-stages NO retorna el POM gravat')
            elif fila.get('base_value_cm') in (None, ''):
                problemes.append(f'base-stages retorna la fila BUIDA: {fila.get("base_value_cm")!r}')
            else:
                print(f'  ✓ base-stages · {fila.get("base_value_cm")} '
                      f'({len(bs.get("rows", []))} files, {crides.get("/api/v1/size-checks/", {}).get("count", 0)} size-checks)')

            # ── 4 · LA CONSULTA, al navegador ──────────────────────────────
            crides['_model_id'] = mid
            tmp.write_text(json.dumps(crides, ensure_ascii=False))
            if not QA_PY.is_file():
                problemes.append(f'no hi ha venv de Playwright a {QA_PY} — el fum de navegador '
                                 f'no s\'ha pogut córrer')
            else:
                print('  · obrint la consulta al navegador…')
                p = subprocess.run([str(QA_PY), str(FUM), str(tmp)],
                                   cwd=str(REPO), capture_output=True, text=True, timeout=300)
                for ln in p.stdout.splitlines():
                    print(f'    {ln}')
                if p.returncode != 0:
                    problemes.append('el fum de navegador ha fallat sobre el model de prova')
        finally:
            c.delete(f'/api/v1/models/{mid}/delete/', **HOST)
            queda = Model.objects.filter(pk=mid).exists()
            print(f'  {"✗" if queda else "✓"} model de prova esborrat')
            if queda:
                problemes.append(f'el model de prova {mid} NO s\'ha esborrat')

    print()
    if problemes:
        print(f'✗ {len(problemes)} problema(es):')
        for x in problemes:
            print(f'   · {x}')
        return 1
    print('✓ P0.3 verd · gravar → base-stages → CONSULTA al navegador → F5')
    return 0


if __name__ == '__main__':
    sys.exit(main())
