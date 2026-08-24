"""M2 · LA CARA DE LES RONDES — FUM HTTP dels payloads que les dues superfícies consumeixen.

Mateixa disciplina que els fums d'M1 i M1-bis: **per socket**, amb `Host:` de tenant i
`Authorization: Bearer`, contra la BD viva d'staging i contra un gunicorn del worktree. Un fum
en procés no verifica una porta.

⚠️ **QUÈ COMPROVA I QUÈ NO.** Aquest fum verifica que **la dada que la cara pinta hi és i és
correcta**: que el Pla pot agrupar per volta, que el Registre pot fer-ho també i sap qui va
treballar cada pas, que el rastre d'FIT-8 surt per la porta, i que informar una entrega tanca la
volta i la cara ho pot dir. **No verifica píxels**: això és la revisió visual de l'acta.

⚠️ **ESCRIU**, i només sobre el banc `[QA-M1]` (`ops/qa/banc_m1_rondes.py`): informa una entrega
de prova i reobre una tasca ja entregada. **Consumeix el banc** —una entrega tanca la ronda i no
es pot desfer—, i per això **el remunta ell mateix abans de començar**: corregut dos cops seguits
sense remuntar, el segon donava 400 a l'entrega i el fum semblava trencat quan el que passava és
que ja s'havia entregat. Amb `--sense-banc` es corre sobre el banc tal com estigui.

Gunicorn del worktree (mai `systemctl restart ftt-staging`: serveix un ALTRE arbre):

    cd /var/www/ftt-m1/backend && venv/bin/gunicorn fhort.wsgi:application \\
        --chdir /var/www/ftt-m1/backend --bind 127.0.0.1:8124 --workers 2 --timeout 60

    BASE=http://127.0.0.1:8124 venv/bin/python ../ops/qa/qa_m2_cara_http.py

⚠️ Per aturar-lo, MAI `pkill -f 8124`: el patró es troba a si mateix a la línia de comandes del
teu propi shell i et mata la sessió. `ps -eo pid,cmd | grep '[g]unicorn.*8124'` i `kill` del màster.
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

BASE = os.environ.get('BASE', 'http://127.0.0.1:8124')
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
        with urllib.request.urlopen(req, timeout=60) as r:
            brut = r.read().decode()
            return r.status, (json.loads(brut) if brut else None)
    except urllib.error.HTTPError as e:
        brut = e.read().decode()
        try:
            return e.code, json.loads(brut)
        except ValueError:
            return e.code, brut[:300]


with schema_context('fhort'):
    if '--sense-banc' not in sys.argv:
        # El fum es fabrica el seu propi punt de partida. Importar el banc no en corre el
        # `__main__`: només en pren les dues funcions.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from banc_m1_rondes import desmunta, munta       # noqa: E402
        desmunta()
        munta()
        print()
    models = {m.codi_intern: m.pk
              for m in Model.objects.filter(codi_intern__startswith='QA-M1-')}
    if len(models) < 4:
        raise SystemExit('Falta el banc: corre `banc_m1_rondes.py --remunta`.')
    # 🚨 El JWT vol el claim `tenant_schema` i el llegeix de l'schema ACTIU: `RefreshToken
    # .for_user()` pelat dona 401 «token no vàlid», el MATEIX 401 que un token absent.
    perfil = UserProfile.objects.order_by('pk').first()
    token = str(TenantTokenObtainPairSerializer.get_token(perfil.user).access_token)

print(f'BASE={BASE} · Host={HOST} · banc {sorted(models)}\n')

VARIATS = models['QA-M1-0001']    # R1 oberta, quatre estats diferents
DUES = models['QA-M1-0004']       # R1 tancada + R2 replicada
VERGE = models['QA-M1-0003']      # cap volta, cap albarà

# ── 0 · EL BACKEND SERVIT PORTA AQUEST CODI ────────────────────────────────────────────────
#
# 🔑 La primera asserció és 401, no 200. Sense token la porta ha de dir **401** i no 404: un 404
# voldria dir que el backend servit no porta aquest codi (el gunicorn ranci de la lliçó del
# 21/08). És el criteri que distingeix «és viu amb el meu codi» de «és viu».
print('── 0 · el backend servit ──')
st, _ = crida('GET', f'/api/v1/models/{VARIATS}/rondes/')
crit('sense token la porta de voltes contesta 401 (existeix i està tancada)', st == 401, st)

# ── 1 · EL PLA · el compositor diu de quina VOLTA és cada tasca ─────────────────────────────
print('\n── 1 · el Pla de treball (mockup A v2) ──')
st, dash = crida('GET', f'/api/v1/models/{VARIATS}/dashboard/', token=token)
crit('GET dashboard = 200', st == 200, st)
tasques = (dash or {}).get('tasques') or []
crit('el compositor porta les 4 tasques del banc', len(tasques) == 4, len(tasques))
crit('i CADA UNA diu la seva volta (`ronda` + `ronda_seq`)',
     all('ronda' in t and 'ronda_seq' in t for t in tasques),
     [(t['task_type_code'], t.get('ronda_seq')) for t in tasques])
crit('totes són de la R1 (el banc no n\'hi té cap altra)',
     {t.get('ronda_seq') for t in tasques} == {1},
     sorted({t.get('ronda_seq') for t in tasques}))
crit('i porten temps consumit, que és el que la capçalera de volta agrega',
     any((t.get('temps_consumit_min') or 0) > 0 for t in tasques),
     [(t['task_type_code'], t.get('temps_consumit_min')) for t in tasques])

st, rondes = crida('GET', f'/api/v1/models/{VARIATS}/rondes/', token=token)
crit('GET rondes = 200 i n\'hi ha una', st == 200 and len(rondes or []) == 1, st)
r1 = (rondes or [{}])[0]
crit('la capçalera té inici i estat (oberta_el · tancada_el)',
     r1.get('oberta_el') is not None and r1.get('tancada_el') is None, r1.get('oberta_el'))
crit('`lliurable` i `entregada` són DUES respostes diferents i totes dues hi són',
     'lliurable' in r1 and 'entregada' in r1, (r1.get('lliurable'), r1.get('entregada')))
crit('encara no és entregada', r1.get('entregada') is False)

# El model amb DUES voltes: el Pla ha de poder-les separar i pintar-ne una de plegada.
st, dash2 = crida('GET', f'/api/v1/models/{DUES}/dashboard/', token=token)
seqs = sorted({t.get('ronda_seq') for t in (dash2 or {}).get('tasques') or []})
crit('el model de dues voltes reparteix les tasques entre R1 i R2', seqs == [1, 2], seqs)
st, rondes2 = crida('GET', f'/api/v1/models/{DUES}/rondes/', token=token)
crit('i la porta diu quina està tancada i quina és vigent',
     [(r['seq'], r['tancada_el'] is not None) for r in (rondes2 or [])] == [(1, True), (2, False)],
     [(r['seq'], r['tancada_el'] is not None) for r in (rondes2 or [])])

# ── 2 · EL REGISTRE · l'albarà diu la volta i QUI ───────────────────────────────────────────
print('\n── 2 · el Registre d\'activitat (mockup B v3) ──')
st, alb = crida('GET', f'/api/v1/models/{DUES}/albara/', token=token)
crit('GET albarà = 200', st == 200, st)
crit('el model del banc ja no dona `merited: False` (el banc li dona albarà sintètic)',
     (alb or {}).get('merited') is True, (alb or {}).get('merited'))
passos = (alb or {}).get('steps') or []
crit('cada PAS diu de quina volta és', all('ronda_seq' in p for p in passos),
     [(p['task_type'], p.get('ronda_seq')) for p in passos])
crit('i els passos es reparteixen entre les dues voltes',
     sorted({p.get('ronda_seq') for p in passos}) == [1, 2],
     sorted({p.get('ronda_seq') for p in passos}))
crit('cada PAS diu QUI hi ha treballat (null si ningú)', all('qui' in p for p in passos),
     [(p['task_type'], p.get('qui')) for p in passos])
crit('els passos treballats porten TEMPS de debò (si no, la columna no es pot revisar)',
     any((p.get('minutes') or 0) > 0 for p in passos),
     [(p['task_type'], p.get('minutes')) for p in passos])
# `qui` surt del RELLOTGE, no de l'`assignee`: un pas amb minuts ha de NOMENAR algú, i un pas
# sense minuts no pot nomenar ningú (callar és una dada; omplir-ho amb qui la tenia assignada
# seria dir que hi va treballar).
crit('tot pas amb minuts NOMENA el tècnic que els va fer',
     all(p.get('qui') for p in passos if (p.get('minutes') or 0) > 0),
     [(p['task_type'], p.get('minutes'), p.get('qui')) for p in passos])
crit('…i cap pas sense minuts no nomena ningú',
     all(p.get('qui') is None for p in passos if not (p.get('minutes') or 0)),
     [(p['task_type'], p.get('minutes'), p.get('qui')) for p in passos])

# El VERGE segueix sent el control negatiu: sense activitat no hi ha registre que ensenyar.
st, albv = crida('GET', f'/api/v1/models/{VERGE}/albara/', token=token)
crit('el model verge segueix dient `merited: False` (control negatiu)',
     st == 200 and (albv or {}).get('merited') is False, (albv or {}).get('merited'))

# ── 3 · L'ENTREGA · el gest que tanca la volta, i la cara ho ha de poder dir ────────────────
print('\n── 3 · informar una entrega (FIT-1 + FIT-13 + FIT-6) ──')
st, ent = crida('POST', f'/api/v1/rondes/{r1["id"]}/entrega/',
                {'destinatari': 'QA M2 · destinatari de prova',
                 'descripcio': 'Fitxa tècnica v1 · patró + escalat (fum M2)'}, token=token)
crit('POST entrega = 201', st == 201, st)
crit('l\'acte torna QUI informa, que la cara pinta a la línia d\'entrega',
     bool((ent or {}).get('qui_informa_nom')), (ent or {}).get('qui_informa_nom'))
crit('…i la descripció, que és TEXT LLIURE (FIT-1: cap FK a cap artefacte)',
     bool((ent or {}).get('descripcio')), (ent or {}).get('descripcio'))
crit('l\'OK del client neix PENDENT', (ent or {}).get('data_ok') is None)

st, rondes = crida('GET', f'/api/v1/models/{VARIATS}/rondes/', token=token)
r1b = (rondes or [{}])[0]
crit('la ronda ha quedat TANCADA (FIT-13)', r1b.get('tancada_el') is not None, r1b.get('tancada_el'))
crit('i la cara la pot pintar «Entregada» amb l\'acte niuat',
     r1b.get('entregada') is True and r1b.get('entrega') is not None)

st, dash = crida('GET', f'/api/v1/models/{VARIATS}/dashboard/', token=token)
vives = [t for t in (dash or {}).get('tasques') or [] if t['status'] != 'Done']
crit('cap tasca viva a la volta entregada (FIT-6)', vives == [],
     [(t['task_type_code'], t['status']) for t in vives])

# ── 4 · L'OK DEL CLIENT · un FET, no un interruptor ────────────────────────────────────────
print('\n── 4 · l\'OK del client ──')
st, ok_cos = crida('PATCH', f'/api/v1/entregues/{ent["id"]}/ok-client/', {}, token=token)
crit('PATCH ok-client = 200 i la data hi queda', st == 200 and ok_cos.get('data_ok'),
     (st, (ok_cos or {}).get('data_ok')))
crit('i diu QUI l\'ha informat', bool((ok_cos or {}).get('qui_informa_ok_nom')),
     (ok_cos or {}).get('qui_informa_ok_nom'))
st, _ = crida('PATCH', f'/api/v1/entregues/{ent["id"]}/ok-client/', {}, token=token)
crit('el segon OK es rebutja (és un fet, no un interruptor)', st == 400, st)

# ── 5 · FIT-8 · el rastre de la reobertura post-entrega SURT per la porta ───────────────────
print('\n── 5 · el rastre FIT-8 ──')
st, log = crida('GET', f'/api/v1/models/{VARIATS}/task-log/', token=token)
crit('GET task-log = 200', st == 200, st)
files = (log or {}).get('log') or []
crit('el log porta `nota` i `ronda_seq` a cada fila',
     bool(files) and all('nota' in f and 'ronda_seq' in f for f in files), len(files))
crit('abans de reobrir res, cap fila no té nota',
     all(f.get('nota') is None for f in files),
     [f['nota'] for f in files if f.get('nota')])

# Reobrir una tasca d'una volta JA ENTREGADA. El segell és TOU: això ha de passar, no fallar.
with schema_context('fhort'):
    from fhort.tasks.models import ModelTask
    feta = ModelTask.objects.filter(model_id=VARIATS, status='Done').order_by('pk').first()
st, cos = crida('POST', f'/api/v1/model-task-items/{feta.pk}/transition/',
                {'to_status': 'InProgress'}, token=token)
crit('Done→InProgress sobre feina ENTREGADA segueix sent LEGAL (segell tou, FIT-2)',
     st == 200, (st, cos))
st, log = crida('GET', f'/api/v1/models/{VARIATS}/task-log/', token=token)
files = (log or {}).get('log') or []
amb_nota = [f for f in files if f.get('nota')]
crit('…i ara el log deixa dit que aquella feina ja s\'havia entregat',
     len(amb_nota) == 1, [(f['task_type'], f['nota'], f['ronda_seq']) for f in amb_nota])
crit('el rastre ve amb la VOLTA, que és el que deixa comptar «/ rectificació m» sense '
     'parsejar la frase',
     bool(amb_nota) and amb_nota[0].get('ronda_seq') == 1,
     amb_nota[0].get('ronda_seq') if amb_nota else None)

# ── 6 · «+ NOVA RONDA» · la porta diu QUÈ ha replicat ──────────────────────────────────────
print('\n── 6 · «+ Nova ronda» amb la llista buida ──')
st, nova = crida('POST', f'/api/v1/models/{VARIATS}/obrir-ronda/',
                 {'motiu': 'nova_mostra', 'codes': []}, token=token)
crit('+Ronda amb codes buits = 201 (el cas normal des d\'M1-bis)', st == 201, (st, nova))
crit('i la porta diu QUÈ ha replicat, per poder-ho dir en veu alta al toast',
     isinstance((nova or {}).get('codes_replicats'), list)
     and isinstance((nova or {}).get('codes_adoptats'), list)
     and isinstance((nova or {}).get('codes_omesos'), list),
     {k: nova.get(k) for k in ('codes_replicats', 'codes_adoptats', 'codes_omesos')})
crit('la volta nova és la 2', (nova or {}).get('seq') == 2, (nova or {}).get('seq'))
st, rondes = crida('GET', f'/api/v1/models/{VARIATS}/rondes/', token=token)
crit('i el Pla ja pot pintar-ne dues: la 1 entregada i la 2 vigent',
     [(r['seq'], r['entregada'], r['tancada_el'] is not None) for r in (rondes or [])]
     == [(1, True, True), (2, False, False)],
     [(r['seq'], r['entregada'], r['tancada_el'] is not None) for r in (rondes or [])])

print(f'\n{len(ok)} OK · {len(ko)} FAIL')
if ko:
    print('FALLEN: ' + ' | '.join(ko))
sys.exit(1 if ko else 0)
