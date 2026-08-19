"""Q3 · Q4 — EL RECORREGUT SENCER D'UNA PRESA, CONTRA L'API REAL.

El defecte del 06/08 (captures 13:10/13:13): la sessió de fitting del MILEY ensenyava —a la
presa i al PDF— els POMs VELLS del model, esborrats i re-entrats una hora abans. Les línies es
van sembrar en crear la peça i no es reconciliaven mai.

Aquest fum fa EL MATEIX que va fer l'Agus, en el mateix ordre, sobre el model de QA de la casa
(pk=182, el clon `[QA-SC]`), i escriu de debò: la sessió que en surt es pot obrir a staging.

  1. es crea la sessió («Fitting aquí i ara») i la seva peça → les línies se sembren de l'spec;
  2. ES RE-ENTREN ELS POMS del model: se'n poden uns quants i se'n creen de nous;
  3. s'OBRE la presa (`GET /piece-fittings/<id>/`) → les línies han de ser les del model D'ARA,
     en l'ORDRE del model (ordre · codi de client · capa · instància);
  4. es pren una mesura i es GRAVA (`close`) → la sessió queda Tancada;
  5. es torna a obrir → l'acta és IDÈNTICA a la del pas 3 (una sessió tancada no es reconcilia);
  6. es re-entra un POM MÉS amb la sessió ja tancada → l'acta NO es mou (és acta, no mirall);
  7. LES FILES DEL PDF (`FittingPrintSheet`: línies de la talla base, per identitat) són les
     mateixes i en el mateix ordre.

🚨 EL MILEY (1308) NO ES TOCA. Guard explícit a sota.

    backend/venv/bin/python ../ops/qa/qa_q34_presa_reconciliada.py
"""
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

MILEY = 1308
MODEL_QA = 182          # clon [QA-SC] OLIVIA DRESS — el model de proves de la casa
HOST = {'HTTP_HOST': 'staging.fhorttextile.tech'}


def identitat(l):
    return (l['codi'], l['capa'], l['instancia'])


def main():
    mid = int(sys.argv[1]) if len(sys.argv) > 1 else MODEL_QA
    if mid == MILEY:
        print('✗ el MILEY (1308) no es toca')
        return 1

    fallides = []
    with schema_context('fhort'):
        from fhort.models_app.models import BaseMeasurement, Model
        from fhort.fitting.models import PieceFittingLine
        from fhort.pom.models import POMMaster

        # 06/08 vespre — V4 va buidar `fhort` de models. Sense aquest guard, el fum moria amb un
        # `Model.DoesNotExist` pelat i qui el trobés demà hauria de sortir a investigar per què.
        model = Model.objects.filter(pk=mid).first()
        if model is None:
            print(f'✗ el model {mid} no existeix. Aquest fum corre contra dades VIVES: '
                  f'passa-li l\'id d\'un model de QA nou (`qa_q34_presa_reconciliada.py <id>`).')
            return 1
        u = get_user_model().objects.filter(is_superuser=True).first()
        c = APIClient()
        c.force_authenticate(user=u)
        print(f'== Q3·Q4 · model {mid} · {model.codi_intern} {model.nom_prenda} '
              f'· base {model.base_size_label!r} ==')

        def actives():
            return list(BaseMeasurement.objects
                        .filter(model=model, is_active=True, base_value_cm__isnull=False)
                        .select_related('pom')
                        .order_by('ordre', 'pom__codi_client', 'capa', 'instancia'))

        def esperat():
            return [(bm.pom.codi_client, bm.capa, bm.instancia) for bm in actives()]

        # ── 1 · la sessió i la peça ────────────────────────────────────────────────────────
        r = c.post('/api/v1/fitting-sessions/schedule-now/', {'model_id': mid, 'force': True},
                   format='json', **HOST)
        if r.status_code not in (200, 201):
            print(f'✗ schedule-now → {r.status_code} · {r.content[:200]}')
            return 1
        sid = r.json()['id']
        r = c.post(f'/api/v1/fitting-sessions/{sid}/create-piece/', {'model_id': mid},
                   format='json', **HOST)
        if r.status_code not in (200, 201):
            print(f'✗ create-piece → {r.status_code} · {r.content[:200]}')
            return 1
        pid = r.json()['id']
        sembrades = PieceFittingLine.objects.filter(piece_fitting_id=pid).count()
        print(f'  · sessió {sid} · peça {pid} · {sembrades} línies sembrades')

        # ── 2 · ES RE-ENTREN ELS POMS (el gest de l'Agus amb el MILEY) ────────────────────
        fora = actives()[:4]
        for bm in fora:
            bm.is_active = False
            bm.save(update_fields=['is_active'])
        usats = set(BaseMeasurement.objects.filter(model=model).values_list('pom_id', flat=True))
        nous = list(POMMaster.objects.exclude(pk__in=usats)[:2])
        for i, pom in enumerate(nous):
            BaseMeasurement.objects.create(model=model, pom=pom, base_value_cm=30.0 + i,
                                           origen='MANUAL', ordre=90 + i)
        print(f'  · re-entrada: −{len(fora)} podats ({[b.pom.codi_client for b in fora]}) '
              f'+{len(nous)} nous ({[p.codi_client for p in nous]}) → {len(actives())} actius')

        # ── 3 · OBRIR LA PRESA ────────────────────────────────────────────────────────────
        r = c.get(f'/api/v1/piece-fittings/{pid}/', **HOST)
        if r.status_code != 200:
            print(f'✗ obrir la presa → {r.status_code}')
            return 1
        base = (model.base_size_label or '').strip()
        lines = [l for l in r.json()['lines'] if l['size_label'] == base]
        vist = [identitat(l) for l in lines]
        if vist != esperat():
            fallides.append(f'3 · la presa no és el model d\'ara en l\'ordre del model\n'
                            f'      presa: {vist}\n      model: {esperat()}')
        podats = {b.pom.codi_client for b in fora}
        if podats & {v[0] for v in vist}:
            fallides.append(f'3 · la presa segueix pintant POMs esborrats del model: '
                            f'{podats & {v[0] for v in vist}}')
        if not {p.codi_client for p in nous} <= {v[0] for v in vist}:
            fallides.append('3 · els POMs nous del model no han arribat a la presa')
        if not fallides:
            print(f'  ✓ 3 · la presa ensenya les {len(vist)} mesures del model, en el seu ordre')

        # ── 4 · prendre una mesura i GRAVAR ───────────────────────────────────────────────
        primera = lines[0]
        nou_valor = round(float(primera['valor_teoric']) + 1.5, 2)
        r = c.patch(f'/api/v1/piece-fitting-lines/{primera["id"]}/',
                    {'valor_real': nou_valor}, format='json', **HOST)
        if r.status_code != 200:
            fallides.append(f'4 · no s\'ha pogut prendre la mesura: {r.status_code} {r.content[:160]}')
        r = c.post(f'/api/v1/piece-fittings/{pid}/close/', {}, format='json', **HOST)
        if r.status_code != 200:
            print(f'✗ gravar (close) → {r.status_code} · {r.content[:240]}')
            return 1
        from fhort.fitting.models import FittingSession
        estat = FittingSession.objects.get(pk=sid).estat
        if estat != 'Tancada':
            fallides.append(f'4 · després de gravar la sessió és {estat}, no Tancada')
        else:
            print(f'  ✓ 4 · gravat: {r.json()} · sessió Tancada')

        # ── 5 · l'acta és la mateixa que la presa reconciliada ────────────────────────────
        r = c.get(f'/api/v1/piece-fittings/{pid}/', **HOST)
        acta = [identitat(l) for l in r.json()['lines'] if l['size_label'] == base]
        if acta != vist:
            fallides.append(f'5 · l\'acta no és el que es va gravar\n      acta: {acta}\n'
                            f'      presa: {vist}')
        else:
            print(f'  ✓ 5 · l\'acta ({len(acta)} files) és exactament la presa gravada')

        # ── 6 · una acta NO es reconcilia ─────────────────────────────────────────────────
        pom_extra = POMMaster.objects.exclude(
            pk__in=BaseMeasurement.objects.filter(model=model).values_list('pom_id', flat=True)
        ).first()
        BaseMeasurement.objects.create(model=model, pom=pom_extra, base_value_cm=44.0,
                                       origen='MANUAL', ordre=95)
        r = c.get(f'/api/v1/piece-fittings/{pid}/', **HOST)
        acta2 = [identitat(l) for l in r.json()['lines'] if l['size_label'] == base]
        if acta2 != acta:
            fallides.append(f'6 · el model ha mogut una ACTA: {set(acta2) ^ set(acta)}')
        else:
            print('  ✓ 6 · el model ha canviat i l\'acta no s\'ha mogut (és acta, no mirall)')

        # ── 7 · les files del PDF ────────────────────────────────────────────────────────
        # Mateixa projecció que `FittingPrintSheet`: línies de la talla base, una per identitat.
        vistes, files_pdf = set(), []
        for l in r.json()['lines']:
            if base and l['size_label'] != base:
                continue
            clau = (l['pom_id'], l['capa'], l['instancia'])
            if clau in vistes:
                continue
            vistes.add(clau)
            files_pdf.append(identitat(l))
        if files_pdf != acta:
            fallides.append(f'7 · el PDF no porta les mateixes files ni el mateix ordre:\n'
                            f'      pdf: {files_pdf}\n      acta: {acta}')
        else:
            print(f'  ✓ 7 · el PDF: {len(files_pdf)} files, mateixes i en el mateix ordre')

        print(f'\n  → per mirar-ho a staging: /fittings/{sid} (acta) · '
              f'/fittings/{sid}/full/{mid} (PDF)')

    if fallides:
        print('\n🔴 FALLIDES')
        for f in fallides:
            print('  ✗', f)
        return 1
    print('\n🟢 Q3 · Q4 · recorregut sencer OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
