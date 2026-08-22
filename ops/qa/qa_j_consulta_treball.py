"""J · CONSULTA ≠ TREBALL — els 4 casos de l'ordre, contra el banc 1383 VIU.

⚠️ AQUESTA QA ESCRIU (banc 1383, baseline v2): obre tasques, escriu una mesura i mou l'estat de
la 377 per fabricar el cas «tasca d'altri». Restaura el que canvia.

🚩 PER QUÈ NO VA PER nginx+gunicorn. El JWT de QA caduca en 1 h i **l'agent no en pot emetre**
(`RefreshToken.for_user` el bloqueja el classificador de permisos: v. la memòria del tram). Es fa
servir l'`APIClient` de DRF amb el Host del tenant i `force_authenticate`, que **recorre el
mateix URLconf, la mateixa vista, els mateixos permisos i el mateix serializer** contra la BD
VIVA de staging. El que NO s'exercita és la capa nginx/gunicorn, que no és on viu res d'aquest
tram. Amb token de l'Agus, el mateix fitxer corre igual canviant el client.

    venv/bin/python ../ops/qa/qa_j_consulta_treball.py     (des de backend/)
"""
import os
import sys

import django

sys.path.insert(0, '/var/www/ftt-staging/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()

from django_tenants.utils import schema_context           # noqa: E402
from rest_framework.test import APIClient                 # noqa: E402

from fhort.accounts.models import UserProfile             # noqa: E402
from fhort.tasks.models import ModelTask                  # noqa: E402

MODEL = 1383
JO = 1          # UserProfile del token (Agustí)
ALTRE = 13      # Montse
HOST = 'staging.fhorttextile.tech'

ok, ko = [], []


def crit(nom, cond, detall=''):
    (ok if cond else ko).append(nom)
    print(f"  {'OK ' if cond else 'FAIL'} {nom}{(' · ' + str(detall)) if detall else ''}")


with schema_context('fhort'):
    cli = APIClient(HTTP_HOST=HOST)
    cli.force_authenticate(user=UserProfile.objects.get(pk=JO).user)

    def post(cami, cos=None):
        return cli.post(cami, cos or {}, format='json', HTTP_HOST=HOST)

    def tasca(tid):
        return cli.get(f'/api/v1/model-task-items/{tid}/', HTTP_HOST=HOST).data

    # ── (a) ENTRAR PER TASCA, MIRAR, SORTIR ─────────────────────────────────
    print('\n(a) entrar · mirar · sortir  ->  cap modal, cap transicio humana, cap minut')
    abans = tasca(376)
    r = post(f'/api/v1/models/{MODEL}/open-task/', {'code': 'size_check'})
    crit('open-task entra', r.status_code == 200, r.status_code)
    t = tasca(376)
    crit('la tasca queda En curs', t['status'] == 'InProgress', t['status'])
    crit('i el tram NO porta escriptura', t['sessio_amb_escriptura'] is False,
         t['sessio_amb_escriptura'])
    r = post('/api/v1/model-tasks/376/sortir-sense-escriptura/')
    d = r.data
    crit('la sortida REVERTEIX', d.get('revertit') is True, d)
    t = tasca(376)
    crit('i torna a Paused, com abans', t['status'] == abans['status'] == 'Paused', t['status'])
    crit('el temps consumit NO ha crescut',
         t['temps_consumit_min'] == abans['temps_consumit_min'],
         f"{abans['temps_consumit_min']} -> {t['temps_consumit_min']}")
    tram = ModelTask.objects.get(pk=376).timers.order_by('-inici').first()
    crit('i el tram queda marcat consulta=True', tram.consulta is True,
         f'consulta={tram.consulta} escriptura_at={tram.escriptura_at}')
    from fhort.tasks.services_i import tram_compta
    crit('els agregadors ja no el compten (tram_compta)', tram_compta(tram) is False)

    # ── (b) ENTRAR, ESCRIURE, SORTIR ────────────────────────────────────────
    print('\n(b) entrar · escriure una mesura · sortir  ->  modal de sempre, temps comptat')
    # 🔑 LA SUPERFÍCIE HA DE CASAR AMB LA TASCA OBERTA, i és una lliçó d'aquesta QA: el batec va
    # per SLUG (`SUP_MESURES='pom'`, `SUP_ESCALAT='grading'`…) i bat SOBRE LA TASCA D'AQUELL CODI,
    # no sobre «la que tinguis oberta». La primera versió d'aquest cas obria `grading` i escrivia
    # per `base-measurements/` (que és `SUP_MESURES`): el batec anava a la tasca `pom` —que al
    # 1383 està Done, i per tant no-op— i el tram de `grading` es quedava sense marca. No era un
    # bug del tram J: era la prova mal aparellada. Es documenta perquè la propera no hi caigui.
    r = post(f'/api/v1/models/{MODEL}/open-task/', {'code': 'grading'})
    crit('open-task entra a `grading`', r.status_code == 200, r.status_code)
    bms = cli.get(f'/api/v1/models/{MODEL}/base-measurements/', HTTP_HOST=HOST).data['results']
    bm = bms[0]
    regla = bm.get('regla_model') or {}
    r = cli.post(f"/api/v1/models/{MODEL}/pom/{bm['pom_id']}/regim/",
                 {'increment_base': regla.get('increment_base')}, format='json', HTTP_HOST=HOST)
    crit("l'escriptura d'ESCALAT passa", r.status_code in (200, 201, 202), r.status_code)
    t = tasca(377)
    crit('el batec ha marcat ESCRIPTURA al tram', t['sessio_amb_escriptura'] is True,
         t['sessio_amb_escriptura'])
    r = post('/api/v1/model-tasks/377/sortir-sense-escriptura/')
    crit('la sortida NO reverteix (hi ha hagut feina)', r.data.get('revertit') is False, r.data)
    crit('i el motiu ho diu', r.data.get('motiu') == 'amb_escriptura', r.data.get('motiu'))

    # ── (c) ENTRAR A TASCA D'ALTRI ──────────────────────────────────────────
    print("\n(c) entrar a tasca d'ALTRI  ->  409 amb codi, mai endur silencios")
    t377 = ModelTask.objects.get(pk=377)
    previ = (t377.status, t377.assignee_id)
    ModelTask.objects.filter(pk=377).update(status='InProgress', assignee_id=ALTRE)
    r = post(f'/api/v1/models/{MODEL}/open-task/', {'code': 'grading'})
    crit('rebutja amb 409', r.status_code == 409, r.status_code)
    crit('i el codi es `tasca_dun_altre`', r.data.get('code') == 'tasca_dun_altre', dict(r.data))
    crit("NO se l'ha enduta (assignee intacte)",
         ModelTask.objects.get(pk=377).assignee_id == ALTRE)
    r = post(f'/api/v1/models/{MODEL}/open-task/', {'code': 'grading', 'handoff': True})
    crit('amb el GEST explicit, si que entra', r.status_code == 200, r.status_code)
    crit('i llavors si que es meva', ModelTask.objects.get(pk=377).assignee_id == JO)
    ModelTask.objects.filter(pk=377).update(status=previ[0], assignee_id=previ[1])

    # ── (d) ENTRAR A UNA FETA ───────────────────────────────────────────────
    print('\n(d) entrar a una tasca FETA  ->  409, reobrir nomes per gest')
    r = post(f'/api/v1/models/{MODEL}/open-task/', {'code': 'pom'})
    crit('rebutja amb 409', r.status_code == 409, r.status_code)
    crit('i el codi es `tasca_feta`', r.data.get('code') == 'tasca_feta', dict(r.data))
    crit('la tasca segueix Done', ModelTask.objects.get(pk=375).status == 'Done')

print(f'\n-- {len(ok)} OK · {len(ko)} FAIL')
if ko:
    print('FALLEN:', ko)
sys.exit(1 if ko else 0)
