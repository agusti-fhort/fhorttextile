"""
tasks/services.py — Lògica de negoci per a generació i gestió de tasques.
Equivalent als Server Scripts de Frappe:
  - generar_tasques_model
  - recalcular_fase_actual (after_save + before_delete)
  - processar_gate
"""
from __future__ import annotations


def generar_tasques_model(model_id: int) -> int:
    """
    Genera ModelTasca a partir dels PaquetServei assignats al Model.
    Les tasques fins al primer gate queden Pendents.
    Les posteriors queden Bloquejades.
    Retorna el nombre de tasques creades.
    """
    from fhort.models_app.models import Model
    from fhort.tasks.models import PaquetServeiTasca

    # Importació local per evitar imports circulars
    ModelTasca = _get_model_tasca()

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

    # Recollir tasques de tots els paquets contractats, deduplicant per ordre_base
    totes_tasques = []
    ordres_vistos: set[int] = set()

    for servei_model in model.serveis_model.filter(contractat=True).select_related('servei'):
        pst_qs = PaquetServeiTasca.objects.filter(
            paquet=servei_model.servei
        ).select_related('tasca').order_by('ordre')

        for pst in pst_qs:
            t = pst.tasca
            if t.ordre_base in ordres_vistos:
                continue
            ordres_vistos.add(t.ordre_base)
            totes_tasques.append({
                'tasca_ref': t,
                'ordre_base': t.ordre_base,
                'nom_tasca': t.nom_tasca,
                'fase': t.fase,
                'tipus_tasca': t.tipus_tasca,
                'gate': t.gate,
                'slots_base': t.slots_base,
                'paquet_origen': servei_model.servei.nom,
            })

    if not totes_tasques:
        raise ValueError("No s'han trobat tasques per als serveis assignats.")

    totes_tasques = sorted(totes_tasques, key=lambda x: x['ordre_base'])

    # Marcar estats: Pendent fins al primer gate, Bloquejada la resta
    primer_gate_passat = False
    for t in totes_tasques:
        if primer_gate_passat:
            t['estat'] = 'Bloquejada'
        else:
            t['estat'] = 'Pendent'
        if t['gate']:
            primer_gate_passat = True

    # Crear ModelTasca
    creades = []
    for t in totes_tasques:
        mt = ModelTasca.objects.create(
            model=model,
            tasca_ref=t['tasca_ref'],
            nom_tasca=t['nom_tasca'],
            fase=t['fase'],
            tipus_tasca=t['tipus_tasca'],
            ordre=str(t['ordre_base']),
            gate=t['gate'],
            slots_base=t['slots_base'],
            estat=t['estat'],
            paquet_origen=t['paquet_origen'],
            responsable=model.responsable,
        )
        creades.append(mt)

    # Actualitzar model
    primera_activa = next((t for t in totes_tasques if t['estat'] == 'Pendent'), None)
    nova_fase = primera_activa['fase'] if primera_activa else totes_tasques[0]['fase']

    Model.objects.filter(pk=model_id).update(
        fase_actual=nova_fase,
        estat='En curs',
    )

    return len(creades)


def recalcular_fase_actual(model_id: int, excloure_tasca_id: int | None = None) -> str:
    """
    Recalcula Model.fase_actual basant-se en les tasques actives.
    - Si hi ha tasques Pendents/En curs → fase = la primera d'elles
    - Si totes Fetes/Bloquejades → fase = 'Tancat'
    - Si no hi ha tasques → fase = 'Nou'
    """
    from fhort.models_app.models import Model
    ModelTasca = _get_model_tasca()

    qs = ModelTasca.objects.filter(model_id=model_id)
    if excloure_tasca_id:
        qs = qs.exclude(pk=excloure_tasca_id)

    # Ordenació numèrica del camp ordre (pot ser text "10", "20", etc.)
    try:
        from django.db.models.functions import Cast
        from django.db.models import IntegerField
        tasques = list(qs.annotate(
            ordre_int=Cast('ordre', IntegerField())
        ).order_by('ordre_int'))
    except Exception:
        tasques = list(qs.order_by('ordre'))

    if not tasques:
        nova_fase = 'Nou'
    else:
        fase_activa = next(
            (t.fase for t in tasques if t.estat in ('Pendent', 'En curs')),
            None
        )
        if fase_activa:
            nova_fase = fase_activa
        else:
            totes_fetes = all(t.estat in ('Feta', 'Bloquejada') for t in tasques)
            nova_fase = 'Tancat' if totes_fetes else (tasques[0].fase or 'Nou')

    nova_fase = nova_fase or 'Nou'
    Model.objects.filter(pk=model_id).update(fase_actual=nova_fase)
    return nova_fase


def processar_gate(model_tasca_id: int) -> int:
    """
    Quan una ModelTasca de tipus gate passa a 'Feta',
    desbloqueja les tasques Bloquejades fins al proper gate.
    Retorna el nombre de tasques desblocades.
    """
    ModelTasca = _get_model_tasca()

    try:
        mt = ModelTasca.objects.get(pk=model_tasca_id)
    except ModelTasca.DoesNotExist:
        return 0

    if not mt.gate or mt.estat != 'Feta':
        return 0

    # Tasques Bloquejades posteriors a aquest gate
    try:
        from django.db.models.functions import Cast
        from django.db.models import IntegerField
        mt_ordre_int = int(mt.ordre) if mt.ordre else 0
        posteriors = ModelTasca.objects.filter(
            model=mt.model,
            estat='Bloquejada',
        ).annotate(ordre_int=Cast('ordre', IntegerField())).filter(
            ordre_int__gt=mt_ordre_int
        ).order_by('ordre_int')
    except Exception:
        posteriors = ModelTasca.objects.filter(
            model=mt.model,
            estat='Bloquejada',
        ).order_by('ordre')

    desblocades = 0
    for t in posteriors:
        t.estat = 'Pendent'
        t.save(update_fields=['estat'])
        desblocades += 1
        if t.gate:  # Para al proper gate
            break

    recalcular_fase_actual(mt.model_id)
    return desblocades


def _get_model_tasca():
    """Importació lazy per evitar imports circulars."""
    try:
        from fhort.tasks.models import ModelTasca
        return ModelTasca
    except ImportError:
        from fhort.models_app.models import ModelTasca
        return ModelTasca
