"""Q4 — captura les respostes REALS d'una sessió de fitting TANCADA (l'acta) i de la seva peça.

Per defecte, la sessió que deixa el recorregut `qa_q34_presa_reconciliada.py` sobre el model de
QA (182). Lectura pura: cap escriptura.

    backend/venv/bin/python ../ops/qa/qa_q4_fixture.py [session_id]
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

SORTIDA = pathlib.Path(__file__).resolve().parent / 'qa_q4_fixture.json'
HOST = {'HTTP_HOST': 'staging.fhorttextile.tech'}


def main():
    with schema_context('fhort'):
        from fhort.fitting.models import FittingSession
        if len(sys.argv) > 1:
            sid = int(sys.argv[1])
        else:
            s = (FittingSession.objects.filter(estat='Tancada', model__isnull=False)
                 .order_by('-id').first())
            if s is None:
                print('✗ cap sessió Tancada')
                return 1
            sid = s.pk
        sessio = FittingSession.objects.get(pk=sid)
        mid = sessio.model_id

        u = get_user_model().objects.filter(is_superuser=True).first()
        c = APIClient()
        c.force_authenticate(user=u)

        fixture = {}
        r = c.get(f'/api/v1/fitting-sessions/{sid}/', **HOST)
        if r.status_code != 200:
            print(f'✗ sessió {sid} → {r.status_code}')
            return 1
        fixture[f'/api/v1/fitting-sessions/{sid}/'] = r.json()
        peces = r.json().get('piece_fittings') or []
        for p in peces:
            rp = c.get(f'/api/v1/piece-fittings/{p["id"]}/', **HOST)
            if rp.status_code == 200:
                fixture[f'/api/v1/piece-fittings/{p["id"]}/'] = rp.json()
        for path in (f'/api/v1/models/{mid}/', '/api/v1/mesures/diccionari/'):
            rr = c.get(path, **HOST)
            if rr.status_code == 200:
                fixture[path] = rr.json()

        fixture['_session_id'] = sid
        fixture['_model_id'] = mid
        fixture['_piece_id'] = peces[0]['id'] if peces else None
        SORTIDA.write_text(json.dumps(fixture, ensure_ascii=False))
        linies = fixture.get(f'/api/v1/piece-fittings/{peces[0]["id"]}/', {}).get('lines', []) if peces else []
        base = (sessio.model.base_size_label or '').strip()
        print(f'→ {SORTIDA.name} · sessió {sid} ({sessio.estat}) · model {mid} · '
              f'peça {fixture["_piece_id"]} · {len(linies)} línies '
              f'({len([l for l in linies if l["size_label"] == base])} a la talla base)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
