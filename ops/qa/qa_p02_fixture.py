"""Captura les respostes REALS de la pantalla «Definició POM» (mode entrada).

Model de PROVA (1302 · «Test Agus»), MAI el MILEY (1308), que és el que l'Agus està entrant.
Lectura pura: cap escriptura.

    backend/venv/bin/python ../ops/qa/qa_p02_fixture.py [model_id]
"""
import json
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

SORTIDA = pathlib.Path(__file__).resolve().parent / 'qa_p02_fixture.json'
MILEY = 1308


def main():
    mid = int(sys.argv[1]) if len(sys.argv) > 1 else 1302
    if mid == MILEY:
        print('✗ el MILEY (1308) no es toca: és el model que l\'Agus està entrant'); return 1

    crides = [
        ('/api/v1/mesures/diccionari/', {}),
        (f'/api/v1/models/{mid}/', {}),
        (f'/api/v1/models/{mid}/poms-suggerits/', {}),
        (f'/api/v1/models/{mid}/taula-mesures/', {}),
        (f'/api/v1/models/{mid}/grading-status/', {}),
        (f'/api/v1/models/{mid}/base-stages/', {}),
    ]
    with schema_context('fhort'):
        u = get_user_model().objects.filter(is_superuser=True).first()
        c = APIClient()
        c.force_authenticate(user=u)
        fixture = {}
        for path, params in crides:
            r = c.get(path, params, HTTP_HOST='staging.fhorttextile.tech')
            if r.status_code != 200:
                print(f'  ✗ {path} → HTTP {r.status_code}')
                continue
            fixture[path] = r.json()
            print(f'  · {path:44} HTTP 200')
        fixture['_model_id'] = mid
        SORTIDA.write_text(json.dumps(fixture, ensure_ascii=False))
        d = fixture.get('/api/v1/mesures/diccionari/', {})
        print(f'→ {SORTIDA.name} · eixos={[e["clau"] for e in d.get("eixos", [])]} '
              f'· files taula-mesures={len(fixture.get(f"/api/v1/models/{mid}/taula-mesures/", {}).get("rows", []))}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
