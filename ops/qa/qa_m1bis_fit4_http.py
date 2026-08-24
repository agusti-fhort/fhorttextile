"""M1-bis · FIT-4 — FUM HTTP: la R1 neix del gest, i la volta nova hereta el joc.

Mateixa disciplina que `qa_m1_entrega_http.py`: **per socket**, amb `Host:` de tenant i
`Authorization: Bearer`, contra la BD viva d'staging. Un fum en procés no verifica una porta.

⚠️ **ESCRIU**, i només sobre el banc `[QA-M1]` (`ops/qa/banc_m1_rondes.py`): obre una tasca al
model verge (que és, precisament, el gest que ha de fer néixer la R1) i obre una volta nova al
model «tot fet». **Consumeix el banc**: remunta'l amb `--remunta` abans de tornar-hi.

    BASE=http://127.0.0.1:8123 venv/bin/python ../ops/qa/qa_m1bis_fit4_http.py
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

ok, ko = [], []


def crit(nom, cond, detall=''):
    (ok if cond else ko).append(nom)
    print(f"  {'OK  ' if cond else 'FAIL'} {nom}{(' · ' + str(detall)) if detall else ''}")


def crida(metode, cami, cos=None, token=None):
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
    models = {m.codi_intern: m.pk
              for m in Model.objects.filter(codi_intern__startswith='QA-M1-')}
    if len(models) < 4:
        raise SystemExit('Falta el banc: corre `banc_m1_rondes.py --remunta`.')
    perfil = UserProfile.objects.order_by('pk').first()
    token = str(TenantTokenObtainPairSerializer.get_token(perfil.user).access_token)

print(f'BASE={BASE} · Host={HOST} · banc {sorted(models)}\n')

# ── 1 · La R1 existeix, és la 1 de debò, i ningú l'ha declarada ─────────────────────────────
st, rondes = crida('GET', f"/api/v1/models/{models['QA-M1-0001']}/rondes/", token=token)
crit('GET rondes = 200', st == 200, st)
crit('el model treballat té UNA volta, i és la seq 1',
     len(rondes or []) == 1 and rondes[0]['seq'] == 1, rondes)
crit('i està oberta', (rondes or [{}])[0].get('tancada_el') is None)

# ── 2 · Sense gest no hi ha volta. Aquest és el control negatiu del tram sencer ─────────────
verge = models['QA-M1-0003']
st, rondes = crida('GET', f'/api/v1/models/{verge}/rondes/', token=token)
crit('el model VERGE no té cap volta (la R1 no la crea el model, la crea el gest)',
     st == 200 and rondes == [], rondes)

# ── 3 · …i el gest la crea. Per la porta real, no per l'ORM ────────────────────────────────
st, cos = crida('POST', f'/api/v1/models/{verge}/open-task/', {'code': 'pom'}, token=token)
crit('open-task al verge = 200/201', st in (200, 201), cos)
st, rondes = crida('GET', f'/api/v1/models/{verge}/rondes/', token=token)
crit('el gest ha fet néixer la R1 (seq=1)',
     len(rondes or []) == 1 and rondes[0]['seq'] == 1, rondes)
with schema_context('fhort'):
    from fhort.tasks.models import ModelTask
    lligades = list(ModelTask.objects.filter(model_id=verge)
                    .values_list('task_type__code', 'ronda__seq'))
crit('i la tasca del gest hi ha quedat lligada', lligades == [('pom', 1)], lligades)

# ── 4 · La volta nova neix amb el joc de l'anterior, sense demanar cap code ─────────────────
#
# Primer cal TANCAR la R1, i es fa pel camí de producte: informar-ne l'entrega (FIT-13). Així el
# fum encadena les dues lleis en l'ordre real —s'entrega la volta, i llavors se n'obre una altra.
totfet = models['QA-M1-0002']
with schema_context('fhort'):
    from fhort.tasks.models import Ronda
    r1_totfet = Ronda.objects.get(model_id=totfet, seq=1).pk
st, cos = crida('POST', f'/api/v1/rondes/{r1_totfet}/entrega/',
                {'destinatari': 'QA · FIT-4', 'descripcio': 'fum M1-bis'}, token=token)
crit("l'entrega de la R1 = 201 (i la tanca)", st == 201, cos)

st, cos = crida('POST', f'/api/v1/models/{totfet}/obrir-ronda/',
                {'motiu': 'nova_mostra', 'codes': []}, token=token)
crit('+Ronda amb codes buits = 201 (abans era «una ronda sense cap tasca no és una ronda»)',
     st == 201, cos)
crit('la porta diu QUÈ ha replicat',
     sorted((cos or {}).get('codes_replicats') or []) == ['pom', 'tech_sheet'],
     (cos or {}).get('codes_replicats'))
crit('i la volta nova és la 2', (cos or {}).get('seq') == 2)
with schema_context('fhort'):
    r2 = Ronda.objects.get(pk=(cos or {}).get('ronda_id') or 0)
    filles = sorted(r2.tasques.values_list('task_type__code', 'status'))
crit('les replicades neixen Pending',
     filles == [('pom', 'Pending'), ('tech_sheet', 'Pending')], filles)

# ── 5 · El banc ja porta una R1 tancada + R2 replicada, i la lectura ho ha de dir ───────────
st, rondes = crida('GET', f"/api/v1/models/{models['QA-M1-0004']}/rondes/", token=token)
seqs = [(r['seq'], r['tancada_el'] is not None) for r in (rondes or [])]
crit('R1 tancada i R2 oberta, per la porta de lectura', seqs == [(1, True), (2, False)], seqs)

# ── 6 · La capability nova de l'entrega ────────────────────────────────────────────────────
with schema_context('fhort'):
    from django.contrib.auth import get_user_model
    from fhort.tasks.models import Ronda as _Ronda   # noqa: F811 (mateix model, nom local)
    u, _ = get_user_model().objects.get_or_create(username='qa-m1bis-sense-cap')
    p, _ = UserProfile.objects.get_or_create(user=u)      # el signal ja n'ha creat un: s'adopta
    p.rol_nom, p.permisos = 'technician', {'revoke': ['execute_tasks']}
    p.save(update_fields=['rol_nom', 'permisos'])
    u = get_user_model().objects.get(pk=u.pk)             # `user.profile` cacheja
    token_sense = str(TenantTokenObtainPairSerializer.get_token(u).access_token)
    ronda_0001 = Ronda.objects.get(model_id=models['QA-M1-0001'], seq=1).pk
st, cos = crida('POST', f'/api/v1/rondes/{ronda_0001}/entrega/',
                {'destinatari': 'no hauria de passar'}, token=token_sense)
crit("sense execute_tasks, la porta d'entrega dona 403", st == 403, st)

print(f'\n{len(ok)} OK · {len(ko)} FAIL')
if ko:
    print('FALLA: ' + ' | '.join(ko))
sys.exit(1 if ko else 0)
