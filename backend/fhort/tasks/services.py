"""
tasks/services.py — Business logic for task generation and management.
Equivalent to Frappe Server Scripts:
  - generate_model_tasks
  - recalculate_current_phase (after_save + before_delete)
  - process_gate
"""
from __future__ import annotations


def generate_model_tasks(model_id: int) -> int:
    """
    Generate ModelTasca rows from the PaquetServei assigned to the Model.
    Tasks up to the first gate stay Pendents.
    Subsequent tasks stay Bloquejades.
    Returns the number of created tasks.
    """
    from fhort.models_app.models import Model
    from fhort.tasks.models import PaquetServeiTasca

    # Local import to avoid circular imports
    ModelTasca = _get_model_task()

    model = Model.objects.get(pk=model_id)

    if not model.serveis_model.exists():
        raise ValueError(
            "El model no té serveis assignats. "
            "Afegeix-ne al tab Servei abans de generar tasques."
        )

    if ModelTasca.objects.filter(model=model).exists():
        raise ValueError(
            "El model ja té tasques generades. "
            "Elimina-les manualment per regenerar."
        )

    # Collect tasks from every contracted package, deduplicating by ordre_base
    all_tasks = []
    seen_orders: set[int] = set()

    for model_service in model.serveis_model.filter(contractat=True).select_related('servei'):
        pst_qs = PaquetServeiTasca.objects.filter(
            paquet=model_service.servei
        ).select_related('tasca').order_by('ordre')

        for pst in pst_qs:
            t = pst.tasca
            if t.ordre_base in seen_orders:
                continue
            seen_orders.add(t.ordre_base)
            all_tasks.append({
                'tasca_ref': t,
                'ordre_base': t.ordre_base,
                'nom_tasca': t.nom_tasca,
                'fase': t.fase,
                'tipus_tasca': t.tipus_tasca,
                'gate': t.gate,
                'slots_base': t.slots_base,
                'paquet_origen': model_service.servei.nom,
            })

    if not all_tasks:
        raise ValueError("No s'han trobat tasques per als serveis assignats.")

    all_tasks = sorted(all_tasks, key=lambda x: x['ordre_base'])

    # Set states: Pendent up to the first gate, Bloquejada for the rest
    first_gate_passed = False
    for t in all_tasks:
        if first_gate_passed:
            t['estat'] = 'Bloquejada'
        else:
            t['estat'] = 'Pendent'
        if t['gate']:
            first_gate_passed = True

    # Create ModelTasca rows
    created = []
    for t in all_tasks:
        mt = ModelTasca.objects.create(
            model=model,
            tasca=t['tasca_ref'],
            ordre=str(t['ordre_base']),
            es_gate=t['gate'],
            slots_base=t['slots_base'],
            estat=t['estat'],
            paquet_origen=t['paquet_origen'],
            responsable=model.responsable,
            # nom_tasca/fase/tipus_tasca live on Tasca (FK), not duplicated here
        )
        created.append(mt)

    # Update the model
    first_active = next((t for t in all_tasks if t['estat'] == 'Pendent'), None)
    new_phase = first_active['fase'] if first_active else all_tasks[0]['fase']

    Model.objects.filter(pk=model_id).update(
        fase_actual=new_phase,
        estat='En curs',
    )

    return len(created)


def recalculate_current_phase(model_id: int, exclude_task_id: int | None = None) -> str:
    """
    Recompute Model.fase_actual based on the active tasks.
    - If there are Pendents/En curs tasks → phase = the first of them
    - If all are Fetes/Bloquejades → phase = 'Tancat'
    - If there are no tasks → phase = 'Nou'
    """
    from fhort.models_app.models import Model
    ModelTasca = _get_model_task()

    qs = ModelTasca.objects.filter(model_id=model_id).select_related('tasca')
    if exclude_task_id:
        qs = qs.exclude(pk=exclude_task_id)

    # Numeric ordering by the ordre field (IntegerField)
    tasks = list(qs.order_by('ordre'))

    if not tasks:
        new_phase = 'Nou'
    else:
        active_phase = next(
            (t.tasca.fase for t in tasks if t.estat in ('Pendent', 'En curs')),
            None
        )
        if active_phase:
            new_phase = active_phase
        else:
            all_done = all(t.estat in ('Feta', 'Bloquejada') for t in tasks)
            new_phase = 'Tancat' if all_done else (tasks[0].tasca.fase or 'Nou')

    new_phase = new_phase or 'Nou'
    Model.objects.filter(pk=model_id).update(fase_actual=new_phase)
    return new_phase


def process_gate(model_task_id: int) -> int:
    """
    When a gate-type ModelTasca moves to 'Feta',
    unblock the Bloquejades tasks up to the next gate.
    Returns the number of unblocked tasks.
    """
    ModelTasca = _get_model_task()

    try:
        mt = ModelTasca.objects.get(pk=model_task_id)
    except ModelTasca.DoesNotExist:
        return 0

    if not mt.es_gate or mt.estat != 'Feta':
        return 0

    # Bloquejades tasks after this gate
    subsequent = ModelTasca.objects.filter(
        model=mt.model,
        estat='Bloquejada',
        ordre__gt=mt.ordre,
    ).order_by('ordre')

    unblocked = 0
    for t in subsequent:
        t.estat = 'Pendent'
        t.save(update_fields=['estat'])
        unblocked += 1
        if t.es_gate:  # Stop at the next gate
            break

    recalculate_current_phase(mt.model_id)
    return unblocked


def _get_model_task():
    """Lazy import to avoid circular imports."""
    try:
        from fhort.tasks.models import ModelTasca
        return ModelTasca
    except ImportError:
        from fhort.models_app.models import ModelTasca
        return ModelTasca
