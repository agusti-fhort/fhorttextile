"""Data-op (one-off, TEST): re-tipa les ModelTask de 'scaling' a 'grading'.

Context (diagnosi §10/§12): l'eina /escalat = DEFINIR la regla de gradació = task_type 'grading'.
Estava mal cablejada al code 'scaling' (eina CAD futura, latent). Les ModelTask creades sota
'scaling' són, de fet, feina d'escalat-regla mal etiquetada → es re-tipen a 'grading'.

Regles:
  - Re-tipus = UPDATE del FK task_type (NO delete): la PROTECT de ModelTask.task_type protegeix
    el TaskType, no impedeix moure una instància entre tipus.
  - Col·lisió unique_together(model, task_type): si el model JA té una ModelTask de 'grading',
    la de 'scaling' no es pot re-tipar. Si és test buit (0 timers) → s'esborra; si té timers → SKIP.
  - Les re-tipades amb timers>0 (feina real, TEST) es tanquen a Done via transition_task perquè
    record_actual_time alimenti l'estadística Welford de la cel·la (item, grading).

Idempotent (re-execució: 0 scaling MT → no fa res). Per defecte DRY-RUN; cal --apply per escriure.
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = "Re-tipa ModelTask scaling→grading (data-op TEST) i tanca a Done les reals per arrencar Welford."

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort', help="Esquema tenant (per defecte: fhort).")
        parser.add_argument('--apply', action='store_true', help="Escriu a BD. Sense flag: dry-run.")

    def handle(self, *args, **opts):
        from fhort.tasks.models import TaskType, ModelTask
        from fhort.tasks.services_c import transition_task

        schema, apply = opts['schema'], opts['apply']
        mode = 'APPLY' if apply else 'DRY-RUN'
        with schema_context(schema):
            sc = TaskType.objects.get(code='scaling')
            gr = TaskType.objects.get(code='grading')
            grading_models = set(ModelTask.objects.filter(task_type=gr)
                                 .values_list('model_id', flat=True))

            retyped, deleted, doned, skipped = [], [], [], []
            with transaction.atomic():
                for mt in (ModelTask.objects.filter(task_type=sc)
                           .select_related('assignee').order_by('id')):
                    tmin = mt.timers.aggregate(s=Sum('minuts'))['s'] or 0
                    if mt.model_id in grading_models:
                        if tmin == 0:
                            deleted.append((mt.id, mt.model_id))
                            if apply:
                                mt.delete()
                        else:
                            skipped.append((mt.id, mt.model_id, tmin))
                        continue
                    retyped.append((mt.id, mt.model_id, mt.status, tmin))
                    if apply:
                        mt.task_type = gr
                        mt.save(update_fields=['task_type', 'updated_at'])
                    if tmin > 0:
                        doned.append((mt.id, tmin, mt.assignee_id))
                        if apply:
                            prof = mt.assignee
                            # force=True: migració d'històric; salta el guard d'albarà v2 (mai
                            # reobre per a usuari, aquí reprocessa re-tipades scaling→grading).
                            if mt.status != 'InProgress':
                                transition_task(mt, 'InProgress', prof, force=True)
                            transition_task(mt, 'Done', prof, force=True)
                if not apply:
                    transaction.set_rollback(True)

            w = self.stdout.write
            w(f"[{mode}] schema={schema}")
            w(f"  re-tipades scaling→grading: {len(retyped)} → {[r[0] for r in retyped]}")
            w(f"  tancades a Done (Welford): {len(doned)} → {[(d[0], f'{d[1]}min') for d in doned]}")
            w(f"  esborrades (col·lisió, test buit): {len(deleted)} → {deleted}")
            w(f"  SKIP (col·lisió amb timers): {len(skipped)} → {skipped}")
