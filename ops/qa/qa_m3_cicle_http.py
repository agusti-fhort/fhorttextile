"""M3 · EL CICLE DE VIDA DEL MODEL — FUM HTTP contra el backend VIU del worktree.

⚠️ **AQUEST SCRIPT ESCRIU**, i escriu sobre el banc `[QA-M1]` i **només** sobre ell: tanca un
model, el reobre i el jubila. **Mai el 1383, mai el golden 162, mai un model real.** Consumeix
la volta oberta del `QA-M1-0004` (l'entrega la tanca i no es pot desfer): per tornar-hi,
`venv/bin/python ../ops/qa/banc_m1_rondes.py --remunta`.

🔑 **PER QUÈ UN FUM HTTP I NO NOMÉS ELS TESTS.** Un test de Django corre dins del procés i amb el
seu propi client; el que no prova és **la porta**: la ruta, el gate de capability, el codi HTTP i
el fet que el codi del disc sigui el que el servidor serveix. Un 200 al disc i un 400 a l'usuari
són l'estat normal quan el gunicorn és ranci ([[ftt-400-linear-zero-era-el-proces]]), i la manera
de veure-ho és aquesta.

    # 1) el banc i el backend del WORKTREE (mai `ftt-staging.service`)
    cd backend && venv/bin/python ../ops/qa/banc_m1_rondes.py --remunta
    setsid nohup venv/bin/gunicorn fhort.wsgi:application \\
        --chdir /var/www/ftt-m3cv/backend --bind 127.0.0.1:8131 --workers 2 --timeout 60 &
    # 2) això
    venv/bin/python ../ops/qa/qa_m3_cicle_http.py
"""
import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                + '/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')

import django  # noqa: E402

django.setup()

from django.utils import timezone                                      # noqa: E402
from django_tenants.utils import schema_context                        # noqa: E402

from fhort.accounts.models import UserProfile                          # noqa: E402
from fhort.auth_jwt import TenantTokenObtainPairSerializer             # noqa: E402
from fhort.models_app.models import Model                              # noqa: E402
from fhort.tasks.models import ModelTask, Ronda                        # noqa: E402

BASE = os.environ.get('BASE', 'http://127.0.0.1:8131')
HOST = 'staging.fhorttextile.tech'
TENANT = 'fhort'

ok, ko = [], []


def crit(nom, cond, detall=''):
    (ok if cond else ko).append(nom)
    print(f"  {'OK  ' if cond else 'FAIL'} {nom}{(' · ' + str(detall)) if detall else ''}")


def crida(metode, cami, cos=None, token=None):
    """(status, dades). Un 4xx NO és una excepció aquí: és una resposta que es mesura."""
    dades = json.dumps(cos).encode() if cos is not None else None
    r = urllib.request.Request(BASE + cami, data=dades, method=metode)
    r.add_header('Host', HOST)
    r.add_header('Content-Type', 'application/json')
    if token:
        r.add_header('Authorization', 'Bearer ' + token)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read() or b'null')
    except urllib.error.HTTPError as e:
        cru = e.read()
        try:
            return e.code, json.loads(cru or b'null')
        except json.JSONDecodeError:
            return e.code, {'_cru': cru[:200].decode('utf-8', 'replace')}


def main():
    with schema_context(TENANT):
        banc = {m.codi_intern: m.pk for m in
                Model.objects.filter(codi_intern__startswith='QA-M1-')}
        perfil = UserProfile.objects.order_by('pk').first()
        # 🚨 El claim `tenant_schema` l'estampa AQUEST serializer llegint l'schema ACTIU. Un
        # `RefreshToken.for_user()` pelat dona 401 «token no vàlid» — el MATEIX 401 que no dur-ne
        # cap, i es confon amb un problema de permisos (lliçó d'M1).
        token = str(TenantTokenObtainPairSerializer.get_token(perfil.user).access_token)

    if 'QA-M1-0004' not in banc:
        raise SystemExit('Falta el banc: corre `banc_m1_rondes.py --remunta`.')
    amb_volta = banc['QA-M1-0004']      # R1 tancada + R2 OBERTA → el flux estrella
    sense_volta = banc['QA-M1-0002']    # R1 amb tot Done
    print(f'BASE={BASE} · Host={HOST} · banc {sorted(banc)}\n')

    # ── 0 · LA PORTA EXISTEIX I ESTÀ TANCADA ────────────────────────────────────────────────
    print('── 0 · les portes ──')
    st, _ = crida('POST', f'/api/v1/models/{amb_volta}/tancar/', {'motiu': 'acabat'})
    crit('sense token la porta contesta 401 (existeix i està tancada)', st == 401, st)

    st, cos = crida('POST', f'/api/v1/models/{amb_volta}/tancar/', {'motiu': 'perque_si'},
                    token=token)
    crit('un motiu desconegut és 400 amb codi', st == 400 and cos.get('code') == 'motiu_invalid',
         (st, cos.get('code')))

    # ── 1 · EL FLUX ESTRELLA: tancar amb una volta OBERTA ────────────────────────────────────
    print('\n── 1 · tancar amb ronda oberta (FIT-10) ──')
    with schema_context(TENANT):
        r = Ronda.objects.filter(model_id=amb_volta, tancada_el__isnull=True).first()
    crit('el banc arriba amb una volta OBERTA', r is not None, r and f'R{r.seq}')

    st, cos = crida('POST', f'/api/v1/models/{amb_volta}/tancar/', {'motiu': 'acabat'},
                    token=token)
    crit('la primera crida AVISA amb 409 i el número de la volta',
         st == 409 and cos.get('code') == 'ronda_oberta'
         and cos.get('ronda', {}).get('seq') == (r.seq if r else None), (st, cos.get('code')))

    with schema_context(TENANT):
        m = Model.objects.get(pk=amb_volta)
        r.refresh_from_db()
    crit('…i NO ha tocat res: model obert i volta viva',
         m.estat == 'nou' and r.tancada_el is None, (m.estat, r.tancada_el))

    st, cos = crida('POST', f'/api/v1/models/{amb_volta}/tancar/',
                    {'motiu': 'acabat', 'confirmar_entrega': True,
                     'destinatari': 'QA · Brumà SL', 'descripcio': 'fitxa + patró'}, token=token)
    crit('en confirmar, 200 i el model queda ACABAT', st == 200 and cos.get('estat') == 'acabat',
         (st, cos.get('estat')))
    crit('la resposta porta l\'ENTREGA que acaba d\'informar',
         (cos.get('entrega') or {}).get('destinatari') == 'QA · Brumà SL', cos.get('entrega'))
    crit('…i el RASTRE amb qui i per què',
         (cos.get('rastre') or {}).get('a') == 'acabat'
         and (cos.get('rastre') or {}).get('motiu') == 'acabat', cos.get('rastre'))

    with schema_context(TENANT):
        r.refresh_from_db()
        vives = ModelTask.objects.filter(ronda=r).exclude(status='Done').count()
        m = Model.objects.get(pk=amb_volta)
    crit('la volta ha quedat TANCADA (FIT-13)', r.tancada_el is not None)
    crit('i sense cap feina viva a dins (FIT-6)', vives == 0, vives)
    crit('el motiu i la data del tancament, persistits',
         m.motiu_tancament == 'acabat' and m.data_tancament is not None,
         (m.motiu_tancament, m.data_tancament))

    st, cos = crida('POST', f'/api/v1/models/{amb_volta}/tancar/', {'motiu': 'acabat'},
                    token=token)
    crit('tancar dues vegades es rebutja', st == 400 and cos.get('code') == 'ja_acabat',
         (st, cos.get('code')))

    # ── 2 · EL BOARD (FASE 4) ───────────────────────────────────────────────────────────────
    print('\n── 2 · el board ──')

    # 🔑 PRECONDICIÓ C4a: «només els PLANIFICATS existeixen al Board». El banc d'M1 fabrica la
    # feina pels gestos de treball, que NO planifiquen res, o sigui que cap dels seus models
    # entraria al board i les tres mesures de sota sortirien verdes sense mesurar res. Se'ls hi
    # posa `planned_start` (fixture de QA, sobre el banc sintètic i només si és buit): l'única
    # alternativa era assignar-los pel planificador, que mouria la cua real d'un tècnic viu.
    with schema_context(TENANT):
        planificades = ModelTask.objects.filter(
            model_id__in=[amb_volta, sense_volta], planned_start__isnull=True).update(
                planned_start=timezone.now())
    print(f'  (fixture C4a: {planificades} tasca/ques del banc amb `planned_start`)')

    def al_board(model_id, **params):
        q = '&'.join(f'{k}={v}' for k, v in params.items())
        st, cos = crida('GET', f'/api/v1/model-task-items/by-model/?all=true&{q}', token=token)
        files = cos.get('results', cos) if isinstance(cos, dict) else cos
        return next((f for f in files if f['model_id'] == model_id), None)

    crit('un model ACABAT surt del board', al_board(amb_volta) is None)
    crit('…però es pot demanar EXPLÍCITAMENT', al_board(amb_volta, estat='acabat') is not None)
    fila = al_board(sense_volta)
    crit('un model viu hi segueix, i la seva fila diu la darrera volta',
         fila is not None and fila.get('ronda') is not None, fila and fila.get('ronda'))

    # ── 3 · REOBRIR i la paret d'FIT-11 ─────────────────────────────────────────────────────
    print('\n── 3 · reobrir (FIT-11) ──')
    st, cos = crida('POST', f'/api/v1/models/{amb_volta}/reobrir/',
                    {'motiu': 'QA · el client torna'}, token=token)
    crit('reobrir torna el model a OBERT', st == 200 and cos.get('estat') == 'nou',
         (st, cos.get('estat')))
    crit('…amb el motiu al rastre',
         (cos.get('rastre') or {}).get('motiu') == 'QA · el client torna', cos.get('rastre'))
    crit('i torna al board', al_board(amb_volta) is not None)

    with schema_context(TENANT):
        rondes = list(Ronda.objects.filter(model_id=amb_volta).order_by('seq'))
        vella = ModelTask.objects.filter(ronda=rondes[0], status='Done').first()
        nova = ModelTask.objects.filter(ronda=rondes[-1], status='Done').first()
    st, cos = crida('POST', f'/api/v1/model-task-items/{vella.pk}/transition/',
                    {'to_status': 'InProgress'}, token=token)
    crit('una tasca d\'una volta ANTERIOR ja no es rectifica (FIT-11)',
         st == 409 and cos.get('code') == 'volta_posterior', (st, cos.get('code')))

    st, cos = crida('POST', f'/api/v1/model-task-items/{nova.pk}/transition/',
                    {'to_status': 'InProgress'}, token=token)
    crit('…i la de la DARRERA volta sí (FIT-2 intacte)', st == 200, (st, cos.get('code')))
    if st == 200:      # es deixa com estava: aquest fum no vol trams oberts al banc
        crida('POST', f'/api/v1/model-task-items/{nova.pk}/transition/',
              {'to_status': 'Done'}, token=token)

    # ── 4 · JUBILAR ─────────────────────────────────────────────────────────────────────────
    print('\n── 4 · jubilar (FIT-9) ──')
    st, cos = crida('POST', f'/api/v1/models/{amb_volta}/jubilar/', {}, token=token)
    crit('un model OBERT no es jubila de cop', st == 400 and cos.get('code') == 'no_acabat',
         (st, cos.get('code')))

    crida('POST', f'/api/v1/models/{amb_volta}/tancar/', {'motiu': 'tret_de_cataleg'},
          token=token)
    st, cos = crida('POST', f'/api/v1/models/{amb_volta}/jubilar/',
                    {'motiu': 'QA · temporada tancada'}, token=token)
    crit('d\'ACABAT a JUBILAT, 200', st == 200 and cos.get('estat') == 'jubilat',
         (st, cos.get('estat')))
    crit('el jubilat també surt del board', al_board(amb_volta) is None)
    with schema_context(TENANT):
        m = Model.objects.get(pk=amb_volta)
        historia = list(m.esdeveniments_estat.order_by('id')
                        .values_list('de_estat', 'a_estat', 'motiu'))
    # tancar · reobrir · tancar · jubilar = QUATRE actes, i cap s'ha sobreescrit l'anterior:
    # és exactament el que un parell de camps `tancat_per`/`reobert_per` no hauria pogut dir.
    crit('la història hi és SENCERA i acumulativa (4 actes)', len(historia) == 4, historia)
    crit('…i el segon tancament diu «tret_de_cataleg»',
         any(a == 'acabat' and mo == 'tret_de_cataleg' for _, a, mo in historia), historia)

    print(f'\n{len(ok)} OK · {len(ko)} FAIL')
    if ko:
        print('FALLEN: ' + ', '.join(ko))
    return 1 if ko else 0


if __name__ == '__main__':
    raise SystemExit(main())
