"""Sprint C: màquina d'estats del kanban del tècnic + timer server-side."""
from django.db import transaction
from django.utils import timezone
from .models import ModelTask, TimerEntrada, TaskTransition

# Transicions permeses (from -> {to})
ALLOWED = {
    'Pending':    {'InProgress'},
    'Paused':     {'InProgress'},
    'InProgress': {'Paused', 'Done'},
    'Done':       {'InProgress'},   # reobertura = rectificació
}


def _open_timer(task, profile):
    TimerEntrada.objects.create(model_task=task, tecnic=profile,
                                inici=timezone.now(), actiu=True)


def _close_open_timer(task):
    t = TimerEntrada.objects.filter(model_task=task, fi__isnull=True, actiu=True).first()
    if t:
        now = timezone.now()
        t.fi = now
        t.minuts = max(0, int((now - t.inici).total_seconds() // 60))
        t.actiu = False
        t.save(update_fields=['fi', 'minuts', 'actiu'])


def _log(task, frm, to, profile):
    TaskTransition.objects.create(model_task=task, from_status=frm, to_status=to, by=profile)


class TransitionError(Exception):
    pass


@transaction.atomic
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
        from fhort.models_app.models import Model
        Model.objects.filter(pk=task.model_id, fase_actual='Pending').update(fase_actual='Dev')

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
