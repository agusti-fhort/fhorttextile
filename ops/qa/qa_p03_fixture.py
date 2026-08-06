"""Captura les respostes REALS que llegeix la CONSULTA «Taula de mesures».

La consulta és `CheckMeasureEditor` en `readOnly` (`ModelSheet.jsx:884`) i menja exactament
dues crides: `base-stages/` (les files i la base vigent) i la llista de `size-checks/` (que
en consulta NO obre res, només llegeix el més recent).

Lectura PURA: aquest script no escriu res enlloc. Per això sí que pot mirar el MILEY.

    backend/venv/bin/python ../ops/qa/qa_p03_fixture.py [model_id]
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

SORTIDA = pathlib.Path(__file__).resolve().parent / 'qa_p03_fixture.json'
MILEY = 1308


def main():
    mid = int(sys.argv[1]) if len(sys.argv) > 1 else MILEY

    with schema_context('fhort'):
        u = get_user_model().objects.filter(is_superuser=True).first()
        c = APIClient()
        c.force_authenticate(user=u)

        crides = [
            (f'/api/v1/models/{mid}/', {}),
            # El GATE del tab Mesures: sense aquestes files, `pomReady` és fals i el tab
            # ensenya l'estat buit en comptes de la consulta (`ModelSheet.jsx:171-195`).
            (f'/api/v1/models/{mid}/taula-mesures/', {}),
            (f'/api/v1/models/{mid}/base-stages/', {}),
            ('/api/v1/size-checks/', {'model': mid, 'ordering': '-created_at', 'page_size': 1}),
            # LES TASQUES DEL MODEL. Sense elles no es pot reproduir el defecte del 06/08: n'hi
            # havia prou que la `pom` estigués En curs o Paused perquè una càrrega FREDA de
            # `?tab=Mesures` obrís l'edició. Un fum amb la llista de tasques buida mai el veurà.
            ('/api/v1/model-task-items/', {'model': mid}),
        ]
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

        bs = fixture.get(f'/api/v1/models/{mid}/base-stages/', {})
        files = bs.get('rows', [])
        amb_valor = [r for r in files if r.get('base_value_cm') is not None]
        checks = fixture.get('/api/v1/size-checks/', {})
        n_checks = checks.get('count', len(checks if isinstance(checks, list) else []))
        print(f'→ {SORTIDA.name} · model={mid} · base_size={bs.get("base_size")!r} '
              f'· files={len(files)} · amb base_value_cm={len(amb_valor)} · size_checks={n_checks}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
