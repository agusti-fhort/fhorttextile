"""Captura les respostes REALS de l'API per al fum del tram W2.

El gunicorn viu rebutja els tokens encunyats des del shell (v. la nota d'e2e del vault) i a
staging no s'hi creen usuaris de QA. Per no haver d'inventar-se les formes de l'API —que és
com un fum acaba passant amb dades que el producte no veurà mai—, aquest script crida les
MATEIXES vistes amb l'APIClient de DRF i `force_authenticate`, i en desa la resposta tal com
surt. El fum de Playwright després serveix aquest fitxer.

    backend/venv/bin/python ../ops/qa/qa_w2_fixture.py     # des de backend/
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

SORTIDA = pathlib.Path(__file__).resolve().parent / 'qa_w2_fixture.json'

# Les crides que el pas 2 i el pas 3 del wizard fan de debò.
CRIDES = [
    ('/api/v1/garment-groups/', {'page_size': 200}),
    ('/api/v1/garment-types/', {'actiu': 'true', 'page_size': 500, 'compat_target': 'WOMAN'}),
    ('/api/v1/garment-type-items/', {'active': 'true', 'page_size': 1000}),
    ('/api/v1/size-systems/', {'actiu': 'true', 'page_size': 100}),
    ('/api/v1/customers/', {'ordering': 'codi', 'page_size': 500}),
    ('/api/v1/customers/7/', {}),
]


def main():
    with schema_context('fhort'):
        u = get_user_model().objects.filter(is_superuser=True).first()
        if u is None:
            print('✗ cap superusuari al tenant fhort'); return 1
        c = APIClient()
        c.force_authenticate(user=u)

        fixture = {}
        for path, params in CRIDES:
            r = c.get(path, params, HTTP_HOST='staging.fhorttextile.tech')
            if r.status_code != 200:
                print(f'  ✗ {path} → HTTP {r.status_code}')
                continue
            fixture[path] = r.json()
            n = fixture[path].get('count') if isinstance(fixture[path], dict) else None
            print(f'  · {path:42} HTTP 200  count={n}')

        SORTIDA.write_text(json.dumps(fixture, ensure_ascii=False))
        print(f'→ {SORTIDA} ({SORTIDA.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
