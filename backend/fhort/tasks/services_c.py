"""Sprint C: màquina d'estats del kanban del tècnic + timer server-side."""
import logging

from django.db import transaction
from django.utils import timezone
from .models import ModelTask, TimerEntrada, TaskTransition

logger = logging.getLogger(__name__)

# Transicions permeses (from -> {to})
ALLOWED = {
    'Pending':    {'InProgress'},
    'Paused':     {'InProgress'},
    'InProgress': {'Paused', 'Done'},
    'Done':       {'InProgress'},   # reobertura = rectificació
}


def _open_timer(task, profile):
    # Invariant ≤1 timer obert per tasca: tanca qualsevol obert previ abans d'obrir-ne un de nou
    # (defensa contra fuites; en condicions normals no n'hi ha cap d'obert en entrar a InProgress).
    _close_open_timer(task)
    TimerEntrada.objects.create(model_task=task, tecnic=profile,
                                inici=timezone.now(), actiu=True)


def _close_open_timer(task):
    # Tanca TOTS els timers oberts de la tasca (no només .first()): si se n'havien acumulat 2+
    # per una fuita, abans en quedava un de penjat permanent. Cada timer tanca amb la SEVA durada.
    now = timezone.now()
    for t in TimerEntrada.objects.filter(model_task=task, fi__isnull=True, actiu=True):
        t.fi = now
        t.minuts = max(0, int((now - t.inici).total_seconds() // 60))
        t.actiu = False
        t.save(update_fields=['fi', 'minuts', 'actiu'])


def _log(task, frm, to, profile):
    TaskTransition.objects.create(model_task=task, from_status=frm, to_status=to, by=profile)


class TransitionError(Exception):
    pass


def _is_off_recipe(task, work_order):
    """Un extra és off_recipe si el seu task_type NO és a la recepta congelada del WO ORDER.
    Al col·lector —o si la recepta encara no s'ha congelat (B4b)— res no és off_recipe: no
    hi ha base contra què comparar."""
    if work_order.kind != 'ORDER':
        return False
    codes = (work_order.recipe_snapshot or {}).get('task_codes')
    if not codes:
        return False
    return task.task_type.code not in codes


def _resolve_work_order(task, when):
    """Resol l'encàrrec (WorkOrder) d'una tasca segons la regla B4a. Retorna
    (work_order, off_recipe). (None, False) si no es pot resoldre —model sense customer, o
    col·lector del mes ja tancat— i llavors es deixa per al reconcile.

    Regla: si el model té un WO ORDER obert → aquell (off_recipe segons recepta); si no →
    col·lector (customer, mes de `when`), on tot és off_recipe=False."""
    from fhort.commerce.models import WorkOrder
    model = task.model
    if not model.customer_id:
        return None, False
    order_wo = (WorkOrder.objects.filter(model=model, kind='ORDER', status='OPEN')
                .order_by('-created_at').first())
    if order_wo is not None:
        return order_wo, _is_off_recipe(task, order_wo)
    period = when.strftime('%Y-%m')
    collector, created = WorkOrder.objects.get_or_create(
        customer_id=model.customer_id, kind='COLLECTOR', period=period,
        defaults={'origin': 'MANUAL'})
    if not created and collector.status == 'CLOSED':
        return None, False   # el col·lector del mes ja s'ha tancat → resolució manual/reconcile
    return collector, False


def assign_work_order(task, when):
    """Assigna l'encàrrec a una tasca si encara no en té (IDEMPOTENT). Reutilitzat pel hook
    (primera InProgress) i pel reconcile. Si la tasca ja té work_order, no fa res."""
    if task.work_order_id is not None:
        return
    work_order, off_recipe = _resolve_work_order(task, when)
    if work_order is None:
        return
    task.work_order = work_order
    task.off_recipe = off_recipe
    task.save(update_fields=['work_order', 'off_recipe', 'updated_at'])


@transaction.atomic
def transition_task(task, to_status, profile):
    """Aplica una transició d'estat. Imposa 'una sola InProgress per tècnic' (global):
    en entrar a InProgress, pausa l'altra InProgress del mateix tècnic (tanca timer + log).
    Retorna dict amb la tasca i, si escau, la pausada automàticament."""
    frm = task.status
    if to_status not in ALLOWED.get(frm, set()):
        raise TransitionError(f'Transició no permesa: {frm} → {to_status}')

    paused_task_id = None
    now = timezone.now()

    if to_status == 'InProgress':
        # Regla: una sola InProgress per tècnic (a qualsevol model)
        other = (ModelTask.objects.filter(assignee=profile, status='InProgress')
                 .exclude(pk=task.pk).first())
        if other:
            _close_open_timer(other)
            other.status = 'Paused'
            other.save(update_fields=['status', 'updated_at'])
            _log(other, 'InProgress', 'Paused', profile)
            paused_task_id = other.pk
        # Obrir timer de la tasca que entra
        _open_timer(task, profile)
        if task.started_at is None:
            task.started_at = now
        if frm == 'Done':
            # Reobrir torna la tasca a oberta; conserva started_at, neteja finished_at
            task.finished_at = None

    elif frm == 'InProgress' and to_status in ('Paused', 'Done'):
        _close_open_timer(task)
        if to_status == 'Done':
            task.finished_at = now

    # Si entra una tasca sense assignee, l'assignem al tècnic que l'executa
    if to_status == 'InProgress' and task.assignee_id is None:
        task.assignee = profile

    task.status = to_status
    task.save()
    _log(task, frm, to_status, profile)

    # Pas 5B-fix: arrencar la PRIMERA tasca treu el model de Pending → Dev.
    if to_status == 'InProgress':
        from fhort.models_app.models import Model, ConsumptionRecord
        from fhort.tasks.signals import model_consumption_started

        # MÓN TÈCNIC (sagrat): la fase passa a Dev com avui, fora de tota lògica de facturació.
        Model.objects.filter(pk=task.model_id, fase_actual='Pending').update(fase_actual='Dev')

        # MÓN FACTURACIÓ (N10: no-fatal, aïllat — mai bloqueja la transició del tècnic).
        try:
            with transaction.atomic():
                rows = Model.objects.filter(
                    pk=task.model_id, consumption_started_at__isnull=True
                ).update(consumption_started_at=now)
                if rows:  # primera vegada que aquest model arrenca → meritar
                    model = Model.objects.select_related('customer').get(pk=task.model_id)
                    record = ConsumptionRecord.objects.create(
                        model=model,
                        code_snapshot=model.codi_intern,
                        name_snapshot=model.nom_prenda or '',
                        period=now.strftime('%Y-%m'),
                        merited_at=now,
                    )
                    model_consumption_started.send(
                        sender=Model,
                        codi_client=model.customer.codi,
                        period=record.period,
                        opaque_ref=record.opaque_ref,
                        merited_at=now,
                    )
                # B4a — ENCÀRREC: assigna work_order a CADA primera InProgress de tasca (no
                # només la del model): el col·lector és per-model×mes però l'assignació és
                # per-tasca. Idempotent i dins el mateix atomic no-fatal.
                assign_work_order(task, now)
        except Exception:
            logger.exception(
                "meritacio/assignacio fallida model=%s task=%s", task.model_id, task.pk
            )
            # NO re-raise: el tecnic ja te la transicio feta; el forat es reconcilia despres.

    if to_status == 'Done':
        # Sprint I: alimentar l'estadística Welford amb el temps real (timers ja tancats;
        # defensiu, no trenca el tancament de la tasca)
        from .services_i import record_actual_time
        record_actual_time(task)

    return {'task_id': task.pk, 'status': to_status, 'paused_task_id': paused_task_id}


def rectification_count(task) -> int:
    """Nombre de rectificacions = transicions Done -> InProgress."""
    return TaskTransition.objects.filter(model_task=task, from_status='Done',
                                         to_status='InProgress').count()
