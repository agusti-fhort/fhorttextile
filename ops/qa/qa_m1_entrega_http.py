"""M1 · FUM HTTP DE L'ENTREGA — porta real, Host de tenant, JWT real.

🚨 **UN FUM EN PROCÉS NO VERIFICA UNA PORTA HTTP** (lliçó del 400 de la F, 21/08): un servei que
diu 200 des d'un `shell` i un endpoint que diu 400 a l'usuari són compatibles, i cap dels dos
menteix. Per això aquest fitxer parla per socket: `Host:` del tenant, `Authorization: Bearer`, i
els codis d'estat que veurà el navegador.

⚠️ **ESCRIU**, i només sobre el banc `[QA-M1]` (`ops/qa/banc_m1_rondes.py`): informa una entrega
de debò, que tanca una ronda de debò i la feina que hi penja. Per això el banc és sintètic i es
torna a muntar amb un sol `python banc_m1_rondes.py` — aquest fum NO restaura res, i no ha de
córrer dues vegades sobre el mateix model sense remuntar-lo (la segona entrega es rebutja, que
és precisament un dels criteris).

    BASE=http://127.0.0.1:8123 venv/bin/python ../ops/qa/qa_m1_entrega_http.py

`BASE` ha d'apuntar al gunicorn que serveix EL CODI QUE ES VOL MESURAR. El servei
`ftt-staging.service` serveix `/var/www/ftt-staging`, que és un ALTRE arbre: mesurar-lo mesuraria
el codi d'una altra sessió.
"""
import json
import os
import sys
import urllib.error
import urllib.request

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                + '/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()

from django_tenants.utils import schema_context                    # noqa: E402

from fhort.accounts.models import UserProfile                      # noqa: E402
from fhort.auth_jwt import TenantTokenObtainPairSerializer         # noqa: E402
from fhort.models_app.models import Model                          # noqa: E402

BASE = os.environ.get('BASE', 'http://127.0.0.1:8123')
HOST = 'staging.fhorttextile.tech'
CODI = 'QA-M1-0001'

ok, ko = [], []


def crit(nom, cond, detall=''):
    (ok if cond else ko).append(nom)
    print(f"  {'OK  ' if cond else 'FAIL'} {nom}{(' · ' + str(detall)) if detall else ''}")


def crida(metode, cami, cos=None, token=None):
    """Retorna (status, body_json_o_text). Els 4xx NO són excepcions: són el criteri."""
    dades = json.dumps(cos).encode() if cos is not None else None
    req = urllib.request.Request(BASE + cami, data=dades, method=metode)
    req.add_header('Host', HOST)
    req.add_header('Content-Type', 'application/json')
    if token:
        req.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            brut = r.read().decode()
            return r.status, (json.loads(brut) if brut else None)
    except urllib.error.HTTPError as e:
        brut = e.read().decode()
        try:
            return e.code, json.loads(brut)
        except ValueError:
            return e.code, brut[:200]


with schema_context('fhort'):
    model = Model.objects.filter(codi_intern=CODI).first()
    if model is None:
        raise SystemExit(f'Falta el banc: corre `banc_m1_rondes.py` (no hi ha {CODI}).')
    perfil = UserProfile.objects.order_by('pk').first()
    # 🔑 NO serveix un `RefreshToken.for_user` pelat: `TenantJWTAuthentication` exigeix el claim
    # `tenant_schema` i, sense ell, la porta contesta 401 «token no vàlid» —que és exactament el
    # mateix 401 que dona un token absent, i es confon amb un problema de permisos. El claim
    # l'estampa `TenantTokenObtainPairSerializer.get_token`, i el llegeix de l'schema ACTIU: per
    # això s'ha de cridar aquí dins del `schema_context`.
    token = str(TenantTokenObtainPairSerializer.get_token(perfil.user).access_token)

print(f'BASE={BASE} · Host={HOST} · model {model.pk} ({CODI})\n')

# ── 0 · La porta hi és I està tancada. 401 ≠ 404, i la diferència ho és tot: 404 voldria dir
#        que el backend servit NO porta aquest codi (el gunicorn ranci de la lliçó del 21/08).
st, _ = crida('GET', f'/api/v1/models/{model.pk}/rondes/')
crit('sense token la porta contesta 401 (existeix i està tancada)', st == 401, st)

# ── 1 · Lectura: la volta hi és, oberta i sense entrega.
st, rondes = crida('GET', f'/api/v1/models/{model.pk}/rondes/', token=token)
crit('GET rondes = 200', st == 200, st)
oberta = next((r for r in (rondes or []) if r['tancada_el'] is None), None)
crit('hi ha una ronda OBERTA al banc', oberta is not None)
if oberta is None:
    print('\nSense ronda oberta no es pot mesurar res més: remunta el banc.')
    raise SystemExit(1)
crit('encara no és entregada', oberta['entregada'] is False and oberta['entrega'] is None)

# ── 2 · L'acte: informar l'entrega.
st, cos = crida('POST', f"/api/v1/rondes/{oberta['id']}/entrega/", token=token,
                cos={'destinatari': 'QA · Compres Brumà SL',
                     'descripcio': 'Fum M1: fitxa PDF + patró DXF'})
crit('POST entrega = 201', st == 201, cos)
entrega_id = (cos or {}).get('id')
crit("l'acte torna qui informa", bool((cos or {}).get('qui_informa')), (cos or {}).get('qui_informa_nom'))

# ── 3 · FIT-13 + FIT-6: la ronda ha quedat tancada i la feina, tancada amb ella.
st, rondes = crida('GET', f'/api/v1/models/{model.pk}/rondes/', token=token)
fila = next((r for r in (rondes or []) if r['id'] == oberta['id']), {})
crit('la ronda ha quedat TANCADA (FIT-13)', fila.get('tancada_el') is not None)
crit('i diu entregada=true amb l\'acte niuat',
     fila.get('entregada') is True and (fila.get('entrega') or {}).get('destinatari')
     == 'QA · Compres Brumà SL')
with schema_context('fhort'):
    from fhort.tasks.models import ModelTask
    vives = list(ModelTask.objects.filter(ronda_id=oberta['id']).exclude(status='Done')
                 .values_list('task_type__code', 'status'))
crit('cap tasca viva a la volta (FIT-6)', not vives, vives)

# ── 4 · Una volta s'entrega un cop.
st, cos = crida('POST', f"/api/v1/rondes/{oberta['id']}/entrega/", token=token,
                cos={'destinatari': 'un altre'})
crit('la segona entrega es rebutja amb 400', st == 400 and (cos or {}).get('code') == 'entrega_invalida', st)

# ── 5 · L'ok del client: manual, posterior, un sol cop.
st, cos = crida('PATCH', f'/api/v1/entregues/{entrega_id}/ok-client/', token=token, cos={})
crit('PATCH ok-client = 200 i data_ok informada', st == 200 and (cos or {}).get('data_ok'), st)
st, _ = crida('PATCH', f'/api/v1/entregues/{entrega_id}/ok-client/', token=token, cos={})
crit("el segon ok-client es rebutja (és un fet, no un interruptor)", st == 400, st)

print(f'\n{len(ok)} OK · {len(ko)} FAIL')
if ko:
    print('FALLA: ' + ' | '.join(ko))
sys.exit(1 if ko else 0)
