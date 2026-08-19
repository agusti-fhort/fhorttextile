"""N4 · SEMBRA DE RONDA DE QA — perquè la cara LLIURADA del modal es pugui provar a mà.

La cara LLIURADA de F2.1 (D-5: «aquesta volta ja s'ha entregat, vols una mostra nova o és una
correcció?») no s'havia pogut veure mai a staging: `Ronda.objects.count()` era **0**. Estava
coberta pels 15 tests unitaris de `caraObrirTasca` i per res més.

QUÈ CREA (i res més):
  · una `Ronda` seq 2, motiu `nova_mostra`, sobre el model de QA
  · la seva `ModelTask` de `tech_sheet` — el tipus ha de ser `es_lliurable=True`, que és el que
    fa saltar la cara LLIURADA i no una reobertura silenciosa
  · aquella tasca queda `Done` amb `finished_at`, que és l'estat que el modal llegeix

COM ES DESFÀ: `--desfer`. Esborra la ronda i les seves tasques i deixa el model com estava.
No toca res més: la feina de la volta 1 no es mou.

IDEMPOTENT: dues corregudes seguides deixen el mateix estat (si la ronda ja hi és, la reusa).

Ús (des de `backend/`):
    venv/bin/python scripts_tmp/n4_sembra_ronda_qa.py          # sembra
    venv/bin/python scripts_tmp/n4_sembra_ronda_qa.py --desfer # neteja
"""
import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fhort.settings')
django.setup()

from django.utils import timezone                      # noqa: E402
from django_tenants.utils import schema_context        # noqa: E402

SCHEMA = 'fhort'
MODEL_QA = 185          # FTT-FW27-0001 · «Test camisa» — model de proves del tenant propi
GOLDEN = 162            # el golden path: NO S'HI TOCA MAI
CODE = 'tech_sheet'     # ha de ser es_lliurable=True


def main(desfer):
    with schema_context(SCHEMA):
        from fhort.models_app.models import Model
        from fhort.tasks.models import ModelTask, Ronda, TaskType
        from fhort.tasks.services_r import obrir_ronda

        if MODEL_QA == GOLDEN:
            raise SystemExit('El golden 162 no es toca.')
        model = Model.objects.get(pk=MODEL_QA)

        if desfer:
            rondes = Ronda.objects.filter(model=model)
            tasques = ModelTask.objects.filter(ronda__in=rondes)
            print(f'esborrant {tasques.count()} tasca/ques i {rondes.count()} ronda/es '
                  f'de {model.codi_intern}')
            tasques.delete()
            rondes.delete()
            print('fet · el model queda com abans de la sembra')
            return

        tt = TaskType.objects.get(code=CODE)
        if not tt.es_lliurable:
            raise SystemExit(f"'{CODE}' no és es_lliurable: la cara LLIURADA no sortiria.")

        ronda = Ronda.objects.filter(model=model, seq=2).first()
        if ronda is None:
            ronda = obrir_ronda(model, Ronda.MOTIU_NOVA_MOSTRA, [CODE])
            print(f'ronda {ronda.seq} creada sobre {model.codi_intern}')
        else:
            print(f'ronda {ronda.seq} ja hi era: la reuso')

        tasca = ronda.tasques.filter(task_type=tt).first()
        if tasca is None:
            raise SystemExit('la ronda no té la tasca esperada; revisa-ho a mà')
        if tasca.status != 'Done':
            tasca.status = 'Done'
            tasca.finished_at = timezone.now()
            tasca.save(update_fields=['status', 'finished_at', 'updated_at'])
        print(f'tasca {tasca.pk} ({CODE}) · {tasca.status} · lliurable={tt.es_lliurable}')
        print(f'\nA la UI: /models/{MODEL_QA} → tab «Fitxa tècnica» → obrir la tasca '
              f'→ ha de sortir la cara LLIURADA amb «Obrir ronda 3».')


if __name__ == '__main__':
    main('--desfer' in sys.argv)
