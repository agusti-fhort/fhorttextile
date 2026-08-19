"""Cicle real d'un model de prova BRW: crear pels 3 passos → veure'l a la llista → esborrar-lo.

## Per què NO va pel navegador

El gunicorn viu rebutja els tokens encunyats des del shell (nota d'e2e del vault, confirmada
altre cop en aquest tram: `create-wizard` amb un token minat torna 401) i a staging **no s'hi
creen usuaris de QA** — és una credencial que sobreviu la sessió. Per no deixar el gest de
DESAR sense verificar, es crida la MATEIXA vista (`ModelViewSet.create_wizard`) amb l'APIClient
de DRF i `force_authenticate`: el codi de la vista, els serializers, la porta única del run i
la BD són els de debò; l'únic que no hi passa és la capa HTTP i el clic.

El payload és exactament el que munta `skeletonPayload()` a `ModelWizard.jsx` amb la tria que
la maqueta descriu: client BRW, peça per la cascada, i el RUN DE CLIENT del pas 3.

    backend/venv/bin/python ../ops/qa/qa_w2_cicle_model.py
"""
import os
import pathlib
import sys

BACKEND = pathlib.Path(__file__).resolve().parents[2] / 'backend'
sys.path.insert(0, str(BACKEND))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django                                     # noqa: E402
django.setup()

from django.contrib.auth import get_user_model    # noqa: E402
from django_tenants.utils import schema_context   # noqa: E402
from rest_framework.test import APIClient         # noqa: E402

HOST = {'HTTP_HOST': 'staging.fhorttextile.tech'}
RUN_CLIENT = 'WOMAN_BRW_01'      # el run de BRW que el pas 3 ha de posar PRIMER
CLIENT = 'BRW'


def main():
    problemes = []
    with schema_context('fhort'):
        from fhort.pom.models import SizeSystem
        from fhort.models_app.models import Model
        from fhort.tasks.models import Customer, GarmentTypeItem

        u = get_user_model().objects.filter(is_superuser=True).first()
        c = APIClient()
        c.force_authenticate(user=u)

        cust = Customer.objects.get(codi=CLIENT)
        sys_brw = SizeSystem.objects.prefetch_related('talles').get(codi=RUN_CLIENT)
        talles = [d.etiqueta for d in sys_brw.talles.all().order_by('ordre')]
        # Una peça REAL del catàleg, triada com la triaria la cascada: la primera activa que
        # tingui família (grup › família › ítem).
        item = (GarmentTypeItem.objects
                .filter(active=True, garment_type__isnull=False)
                .select_related('garment_type').order_by('id').first())
        if item is None or not talles:
            print('✗ falten dades de catàleg per fer el cicle'); return 1

        print(f'  · client {cust.codi} · peça {item.garment_type.codi_client} › {item.name} '
              f'· run {sys_brw.codi} {talles}')

        # ── CREAR (el gest de «Crear model» del pas 3) ─────────────────────
        payload = {
            'customer_id': cust.id, 'year': 2026, 'season': 'FW',
            'ref_client': 'QA-W2-CICLE',
            'target': 'WOMAN',
            'garment_type_id': item.garment_type_id,
            'garment_type_item_id': item.id,
            'size_system_id': sys_brw.id,
            'size_run': '·'.join(talles),
            'base_size': talles[len(talles) // 2],
        }
        r = c.post('/api/v1/models/create-wizard/', payload, format='json', **HOST)
        if r.status_code not in (200, 201):
            print(f'✗ create-wizard → HTTP {r.status_code}: {str(r.content[:400])}')
            return 1
        mid = r.json().get('id') or r.json().get('model', {}).get('id')
        print(f'  ✓ creat · model id={mid} · {r.json().get("codi_intern", "")}')

        # ── EL QUE HA QUEDAT DESAT ─────────────────────────────────────────
        m = Model.objects.get(pk=mid)
        if m.size_system_id != sys_brw.id:
            problemes.append(f'el run de client no s\'ha desat (size_system={m.size_system_id})')
        else:
            print(f'  ✓ run de client desat: {sys_brw.codi}')
        if m.size_run_model != '·'.join(talles):
            problemes.append(f'run desat diferent: {m.size_run_model!r} ≠ {"·".join(talles)!r}')
        else:
            print(f'  ✓ run desat en ordre del sistema: {m.size_run_model}')
        if m.garment_type_item_id != item.id:
            problemes.append('la peça triada per la cascada no s\'ha desat')
        else:
            print(f'  ✓ peça desada: {item.name}')
        if m.customer_id != cust.id:
            problemes.append('el client no s\'ha desat')
        elif not (m.codi_intern or '').startswith(CLIENT):
            problemes.append(f'el codi no porta el prefix del client: {m.codi_intern!r} '
                             f'(el gate del 04/06 diu que el client mana el prefix)')
        else:
            print(f'  ✓ client i prefix del codi: {m.codi_intern}')

        # ── VEURE'L A LA LLISTA ────────────────────────────────────────────
        r = c.get('/api/v1/models/', {'search': m.codi_intern, 'page_size': 50}, **HOST)
        ids = [x['id'] for x in (r.json().get('results') or [])]
        if mid not in ids:
            r2 = c.get('/api/v1/models/', {'page_size': 500}, **HOST)
            ids = [x['id'] for x in (r2.json().get('results') or [])]
        if mid in ids:
            print('  ✓ surt a la llista de models')
        else:
            problemes.append('el model creat NO surt a la llista')

        # ── ESBORRAR-LO (i comprovar que se n'ha anat de debò) ──────────────
        r = c.delete(f'/api/v1/models/{mid}/delete/', **HOST)
        if r.status_code not in (200, 202, 204):
            problemes.append(f'delete → HTTP {r.status_code}: {str(r.content[:200])}')
        elif Model.objects.filter(pk=mid).exists():
            problemes.append('el delete ha tornat OK però el model hi segueix')
        else:
            print('  ✓ esborrat · no queda rastre a la BD')

    print()
    if problemes:
        print(f'✗ {len(problemes)} problema(es):')
        for x in problemes:
            print(f'   · {x}')
        return 1
    print('✓ cicle W2 verd')
    return 0


if __name__ == '__main__':
    sys.exit(main())
