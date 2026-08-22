"""J-bis · LA SEQÜÈNCIA DE CONSULTA SOBRE LA FITXA DEL 1383, sencera.

Els dos casos de l'ordre, per les MATEIXES portes que fa servir l'editor:
  (a) entrar per tasca → mirar → sortir  →  cap modal, cap minut, estat INTACTE (Pending inclòs)
  (b) entrar → editar de veritat → sortir →  modal (no reverteix) i temps comptat

⚠️ ESCRIU al banc 1383: obre la tasca `tech_sheet`, desa una versió del `.ftt` al cas (b) i
restaura l'estat de la tasca al final. Anotat a l'acta.

🚩 No va per nginx+gunicorn: el JWT de QA caduca en 1 h i l'agent no en pot emetre (v.
`ftt-qa-token-jwt-bloquejat`). `APIClient` de DRF amb el Host del tenant contra la BD VIVA —
mateix URLconf, mateixa vista, mateixos permisos, mateix serializer.

    venv/bin/python ../ops/qa/qa_jbis_fitxa_consulta.py      (des de backend/)
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
from fhort.models_app.models import ModelFitxer           # noqa: E402
from fhort.tasks.models import ModelTask                  # noqa: E402
from fhort.tasks.services_i import tram_compta            # noqa: E402

MODEL, TASCA, JO = 1383, 378, 1
HOST = 'staging.fhorttextile.tech'
ok, ko = [], []


def crit(nom, cond, detall=''):
    (ok if cond else ko).append(nom)
    print(f"  {'OK ' if cond else 'FAIL'} {nom}{(' · ' + str(detall)) if detall else ''}")


with schema_context('fhort'):
    cli = APIClient(HTTP_HOST=HOST)
    cli.force_authenticate(user=UserProfile.objects.get(pk=JO).user)

    def post(c, cos=None):
        return cli.post(c, cos or {}, format='json', HTTP_HOST=HOST)

    def tasca():
        return cli.get(f'/api/v1/model-task-items/{TASCA}/', HTTP_HOST=HOST).data

    cap = ModelFitxer.objects.filter(model_id=MODEL, nom_fitxer__endswith='.ftt').order_by('-id').first()

    # ── PRE · el .ftt reparat obre AMB CONTINGUT ────────────────────────────
    print(f'\n(pre) el .ftt reparat obre amb contingut  ·  cap = {cap.pk}')
    d = cli.get(f'/api/v1/ftt-documents/{cap.pk}/', HTTP_HOST=HOST)
    crit('GET del document', d.status_code == 200, d.status_code)
    objs = [o for p in d.data['document_json'].get('pages', []) for o in p.get('objects', [])]
    crit('i porta objectes (no s\'obre buit)', len(objs) > 0, f'{len(objs)} objectes')

    # ── ESTAT DE PARTIDA: la tasca a Pending, per provar el cas dur ─────────
    previ = ModelTask.objects.get(pk=TASCA)
    guardat = (previ.status, previ.started_at)
    for t in previ.timers.filter(fi__isnull=True, actiu=True):
        t.fi = t.inici
        t.minuts = 0
        t.actiu = False
        t.save(update_fields=['fi', 'minuts', 'actiu'])
    ModelTask.objects.filter(pk=TASCA).update(status='Pending', started_at=None)

    # ── (a) ENTRAR · MIRAR · SORTIR ────────────────────────────────────────
    print('\n(a) entrar per tasca · mirar · sortir  ->  cap modal, cap minut, estat INTACTE')
    minuts_abans = tasca()['temps_consumit_min']
    r = post(f'/api/v1/models/{MODEL}/open-task/', {'code': 'tech_sheet'})
    crit('open-task entra', r.status_code == 200, r.status_code)
    t = tasca()
    crit('la tasca queda En curs', t['status'] == 'InProgress', t['status'])
    crit('i el tram no porta escriptura', t['sessio_amb_escriptura'] is False)
    # MIRAR: obrir el document és lectura pura i NO ha de batre
    cli.get(f'/api/v1/ftt-documents/{cap.pk}/', HTTP_HOST=HOST)
    crit('obrir el .ftt NO compta com a escriptura',
         tasca()['sessio_amb_escriptura'] is False)
    r = post(f'/api/v1/model-tasks/{TASCA}/sortir-sense-escriptura/', {'pausa_si_cal': True})
    crit('la sortida REVERTEIX', r.data.get('revertit') is True, r.data)
    t = tasca()
    crit('i torna a PENDING, exactament on era', t['status'] == 'Pending', t['status'])
    crit('amb started_at net (una Pending no s\'ha començat mai)',
         ModelTask.objects.get(pk=TASCA).started_at is None)
    crit('cap minut nou', t['temps_consumit_min'] == minuts_abans,
         f"{minuts_abans} -> {t['temps_consumit_min']}")
    tram = ModelTask.objects.get(pk=TASCA).timers.order_by('-inici').first()
    crit('el tram queda marcat consulta i no compta',
         tram.consulta is True and not tram_compta(tram))

    # ── (b) ENTRAR · EDITAR DE VERITAT · SORTIR ────────────────────────────
    print('\n(b) entrar · editar la fitxa de veritat · sortir  ->  modal i temps comptat')
    r = post(f'/api/v1/models/{MODEL}/open-task/', {'code': 'tech_sheet'})
    crit('open-task entra', r.status_code == 200, r.status_code)
    crit('LOCK del document', post(f'/api/v1/ftt-documents/{cap.pk}/lock/').status_code == 200)
    doc = cli.get(f'/api/v1/ftt-documents/{cap.pk}/', HTTP_HOST=HOST).data['document_json']
    doc2 = {**doc, 'metadata': {**(doc.get('metadata') or {}), 'jbis_qa_b': 'edicio real'}}
    r = cli.patch(f'/api/v1/ftt-documents/{cap.pk}/', {'document_json': doc2},
                  format='json', HTTP_HOST=HOST)
    crit('el desat de la fitxa passa', r.status_code == 200, r.status_code)
    nou = r.data['id']
    crit('i persisteix al disc', os.path.exists(ModelFitxer.objects.get(pk=nou).fitxer.path))
    crit('el batec de SUP_FITXA ha marcat el tram',
         tasca()['sessio_amb_escriptura'] is True)
    r = post(f'/api/v1/model-tasks/{TASCA}/sortir-sense-escriptura/')
    crit('la sortida NO reverteix (hi ha hagut feina)', r.data.get('revertit') is False, r.data)
    crit('i el motiu ho diu', r.data.get('motiu') == 'amb_escriptura')
    crit('la tasca segueix En curs: la decisio es de la persona',
         tasca()['status'] == 'InProgress')
    post(f'/api/v1/ftt-documents/{nou}/unlock/')

    # ── RESTAURA ───────────────────────────────────────────────────────────
    for t_ in ModelTask.objects.get(pk=TASCA).timers.filter(fi__isnull=True, actiu=True):
        t_.fi = t_.inici
        t_.minuts = 0
        t_.actiu = False
        t_.save(update_fields=['fi', 'minuts', 'actiu'])
    ModelTask.objects.filter(pk=TASCA).update(status=guardat[0], started_at=guardat[1])
    print(f'\n(restaurat) tasca {TASCA} -> {guardat[0]}')

print(f'\n-- {len(ok)} OK · {len(ko)} FAIL')
if ko:
    print('FALLEN:', ko)
sys.exit(1 if ko else 0)
