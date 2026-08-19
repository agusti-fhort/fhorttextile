"""V4 · NETEJA DE MODELS DE STAGING — tenant `fhort` i prou (decisió d'Agus, 06/08 vespre).

    EN SEC (per defecte):   backend/venv/bin/python manage.py shell < scripts_tmp/v4_neteja_models.py
    APLICA:              APLICA=1 backend/venv/bin/python manage.py shell < scripts_tmp/v4_neteja_models.py

(La convenció d'`APLICA=1` és la de `neteja_codis_duplicats.py`: en sec s'ensenya el pla, i
escriure exigeix una variable d'entorn explícita.)

── QUÈ FA I QUÈ NO ─────────────────────────────────────────────────────────────────────────
ESBORRA: **tots els models del tenant `fhort`** i el seu rastre. L'acta del que hi havia és
`v4_cens_models_OUT.txt` (46 models · 21 amb 10.162 min de corpus de temps). L'Agus va triar
esborrar-ho tot sabent el preu: el corpus del Welford queda a 0 i es refarà amb models nous de
QA; el planificador viurà de `TimeSeed` fins llavors, que és més honest que viure d'un corpus de
models que ja no existeixen.

NO TOCA MAI, i això no és una precaució meva sinó el brief: el CATÀLEG (`POMMaster`,
`CustomerPOMAlias`, `GradingRuleSet`+`GradingRule`, `TimeSeed`, diccionaris, `GarmentType(Item)`,
`SizeSystem`, `SizingProfile`) ni **res del tenant `los`**. El schema `public` tampoc.

── LA PARET DE L'ALBARÀ: NO ES DESMUNTA, I NO CAL ───────────────────────────────────────────
`te_paret_albara` (`tasks/services_c.py:44`) és un guard de TRANSICIÓ d'estat de tasca, no
d'esborrat: no bloqueja res d'aquí i es queda intacta per a la vida real, tal com mana l'Agus.
I `DeliveryNoteLine.model` és **SET_NULL**, o sigui que el model 188 (albarà DN-2026-0001,
ISSUED) s'esborra sense forçar res: la línia sobreviu amb `model=NULL`, que és exactament el que
l'autor de l'esquema va decidir per a aquest cas.
🔴 NO s'esborren les línies ni els albarans: fer-ho deixaria un document EMÈS amb un total que
no quadraria amb les seves línies —un document incoherent és pitjor que un enllaç a NULL—, i
canviar documents numerats no és neteja de dades, és una altra cosa.

── ELS DOS BLOQUEJANTS REALS (PROTECT) ──────────────────────────────────────────────────────
`SizeCheck.model` i `PieceFitting.model` són PROTECT: sense esborrar-los abans, `model.delete()`
peta. S'esborren explícitament, i les seves línies cauen per CASCADE des d'ells.
(`WorkOrder.model` també és PROTECT però les 5 files tenen `model=NULL`: no bloqueja.)

── EL QUE SOBREVIU AMB `model=NULL`, PER DISSENY ────────────────────────────────────────────
`ImportSession` (la sessió és el registre d'un import i té el seu token i el seu document),
`AIUsage` (comptabilitat de cost: esborrar-la seria esborrar despesa real), `BulkCollectionRow`
i `DeliveryNoteLine`. Cap d'aquests és un orfe penjant: són referències que l'esquema deixa a
NULL a posta. Es compten al final perquè constin.
"""
import os

from django.db import transaction
from django_tenants.utils import schema_context

from fhort.models_app.models import (Model, BaseMeasurement, MeasurementChangeLog,
                                     ModelGradingRule, Watchpoint, ConsumptionRecord, SizeCheck,
                                     ModelFitxer, ImportSession, AIUsage, BulkCollectionRow)
from fhort.fitting.models import FittingSession, SizeFitting, PieceFitting, POMAlert
from fhort.tasks.models import ModelTask, TimerEntrada, TaskTransition
from fhort.commerce.models import DeliveryNoteLine

SCHEMA = 'fhort'          # 🔴 NOMÉS aquest. `los` no es toca.
APLICA = os.environ.get('APLICA') == '1'

COMPTADORS = (
    ('Model', lambda: Model.objects.count()),
    ('BaseMeasurement', lambda: BaseMeasurement.objects.count()),
    ('MeasurementChangeLog', lambda: MeasurementChangeLog.objects.count()),
    ('ModelGradingRule', lambda: ModelGradingRule.objects.count()),
    ('SizeCheck', lambda: SizeCheck.objects.count()),
    ('Watchpoint', lambda: Watchpoint.objects.count()),
    ('FittingSession', lambda: FittingSession.objects.count()),
    ('SizeFitting', lambda: SizeFitting.objects.count()),
    ('PieceFitting', lambda: PieceFitting.objects.count()),
    ('POMAlert', lambda: POMAlert.objects.count()),
    ('ModelTask', lambda: ModelTask.objects.count()),
    ('TimerEntrada', lambda: TimerEntrada.objects.count()),
    ('TaskTransition', lambda: TaskTransition.objects.count()),
    ('ConsumptionRecord', lambda: ConsumptionRecord.objects.count()),
    ('ModelFitxer', lambda: ModelFitxer.objects.count()),
)
# El que ha de sobreviure amb `model=NULL` (i el que ha de sobreviure sencer).
SUPERVIVENTS = (
    ('ImportSession (model=NULL)', lambda: ImportSession.objects.filter(model__isnull=True).count()),
    ('AIUsage (model=NULL)', lambda: AIUsage.objects.filter(model__isnull=True).count()),
    ('BulkCollectionRow (model=NULL)', lambda: BulkCollectionRow.objects.filter(model_creat__isnull=True).count()),
    ('DeliveryNoteLine (model=NULL)', lambda: DeliveryNoteLine.objects.filter(model__isnull=True).count()),
)


def foto(titol):
    print(f'\n── {titol} {"─" * (60 - len(titol))}')
    for nom, fn in COMPTADORS:
        print(f'   {nom:24} {fn():>6}')
    for nom, fn in SUPERVIVENTS:
        print(f'   {nom:24} {fn():>6}')


with schema_context(SCHEMA):
    ids = list(Model.objects.order_by('id').values_list('id', flat=True))
    print(f'{"═" * 70}\nV4 · NETEJA DE MODELS · tenant «{SCHEMA}» · '
          f'{"APLICA" if APLICA else "EN SEC"}\n{"═" * 70}')
    print(f'Models a esborrar: {len(ids)}')
    print(f'  ids: {ids}')
    foto('ABANS')

    protect_sc = SizeCheck.objects.filter(model_id__in=ids).count()
    protect_pf = PieceFitting.objects.filter(model_id__in=ids).count()
    print(f'\n   bloquejants PROTECT a retirar abans: SizeCheck={protect_sc} · '
          f'PieceFitting={protect_pf}')

    if not APLICA:
        print('\n🟡 EN SEC: no s\'ha escrit res. Torna-hi amb APLICA=1 per executar-ho.')
    else:
        with transaction.atomic():
            # 1 · els dos PROTECT, explícitament (les seves línies cauen per CASCADE des d'ells)
            n_sc = SizeCheck.objects.filter(model_id__in=ids).delete()
            n_pf = PieceFitting.objects.filter(model_id__in=ids).delete()
            print(f'\n   · SizeCheck esborrats:    {n_sc}')
            print(f'   · PieceFitting esborrats: {n_pf}')
            # 2 · el model, pel seu propi delete: la resta cau per CASCADE, com quan
            #     s'esborra un model des de l'API. No es fa cap `raw` ni cap truc.
            esborrats = 0
            for mid in ids:
                m = Model.objects.filter(pk=mid).first()
                if m is None:
                    continue
                m.delete()
                esborrats += 1
            print(f'   · Models esborrats:       {esborrats}')
        print('\n🟢 APLICAT (dins d\'una sola transacció).')

    foto('DESPRÉS')

    # ── AUDITORIA DE ZERO-ORFES ────────────────────────────────────────────────────────────
    print(f'\n{"═" * 70}\nAUDITORIA · orfes que apunten a un model inexistent\n{"═" * 70}')
    vius = set(Model.objects.values_list('id', flat=True))
    orfes = []
    for nom, qs in (
        ('BaseMeasurement', BaseMeasurement.objects.all()),
        ('MeasurementChangeLog', MeasurementChangeLog.objects.all()),
        ('ModelGradingRule', ModelGradingRule.objects.all()),
        ('SizeCheck', SizeCheck.objects.all()),
        ('Watchpoint', Watchpoint.objects.all()),
        ('FittingSession', FittingSession.objects.all()),
        ('SizeFitting', SizeFitting.objects.all()),
        ('PieceFitting', PieceFitting.objects.all()),
        ('ModelTask', ModelTask.objects.all()),
        ('ConsumptionRecord', ConsumptionRecord.objects.all()),
        ('ModelFitxer', ModelFitxer.objects.all()),
    ):
        n = qs.exclude(model_id__in=vius).count()
        orfes.append((nom, n))
    # Els dos que pengen de la tasca, no del model.
    orfes.append(('TimerEntrada (sense tasca)',
                  TimerEntrada.objects.exclude(
                      model_task_id__in=ModelTask.objects.values('id')).count()))
    orfes.append(('TaskTransition (sense tasca)',
                  TaskTransition.objects.exclude(
                      model_task_id__in=ModelTask.objects.values('id')).count()))
    for nom, n in orfes:
        print(f'   {"✓" if n == 0 else "✗"} {nom:30} {n}')
    print(f'\n   TOTAL ORFES: {sum(n for _, n in orfes)}')
