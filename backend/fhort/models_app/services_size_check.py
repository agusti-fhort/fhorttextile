"""SC-1 — Size Check service: validació del proto a talla base, ABANS del fitting.

Entitat NETA (no reusa PieceFitting). En obrir parteix dels BaseMeasurement VIGENTS
del model (valor_teoric = snapshot del base_value_cm en crear la línia). En resoldre
amb 'Acceptat', les línies acceptades amb valor_real escriuen BaseMeasurement amb
origen='CHECKED' — NOMÉS la base (no toca deltes/ModelGradingRule/ModelGradingOverride).
El signal F1 (log_measurement_change) registra el canvi igual que amb 'FITTED'.
"""
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def _materialize_lines(size_check, model) -> int:
    """Crea una SizeCheckLine per cada BaseMeasurement VIGENT del model.

    valor_teoric = snapshot del base_value_cm en aquest moment; valor_real null (el tècnic
    l'anota); decisio/nota als defaults. Només s'invoca quan el check NO té cap línia
    (crear de nou o reomplir un Pendent orfe) → no clobbera feina anotada. Retorna n línies.
    """
    from fhort.models_app.models import BaseMeasurement, SizeCheckLine
    bms = (
        BaseMeasurement.objects
        .filter(model=model, is_active=True, base_value_cm__isnull=False)
        .select_related('pom')
    )
    n = 0
    for bm in bms:
        SizeCheckLine.objects.create(
            size_check=size_check,
            pom=bm.pom,
            valor_teoric=bm.base_value_cm,   # snapshot del vigent en crear la línia
            valor_real=None,                 # el tècnic l'anota
        )
        n += 1
    return n


def open_size_check(model_id: int, *, created_by_id: int | None = None):
    """Obre (o reutilitza) un SizeCheck Pendent del model i garanteix les línies.

    Reutilitza el SizeCheck Pendent viu si n'hi ha (no en crea un de segon); l'històric
    són els resolts. Cada open parteix del BaseMeasurement VIGENT: una línia per cada
    BaseMeasurement actiu amb valor (base_value_cm no null), valor_teoric = snapshot.

    GARANTIA: si el model té BaseMeasurements vigents, open MAI retorna un check sense
    línies — si reusa un Pendent orfe (0 línies) el reomple; si ja en té, NO el regenera
    (preserva valor_real/decisio anotats).

    Retorna (SizeCheck, n_lines).
    """
    from fhort.models_app.models import Model, SizeCheck

    model = Model.objects.get(pk=model_id)

    existing = (
        SizeCheck.objects.filter(model=model, estat='Pendent')
        .order_by('-created_at').first()
    )
    if existing is not None:
        n = existing.linies.count()
        if n == 0:
            # Pendent orfe → reomple des dels BaseMeasurements vigents (no regenera si ja en té).
            n = _materialize_lines(existing, model)
            logger.info(f"SizeCheck {existing.pk} reomplert (orfe): {n} lines")
        return existing, n

    sc = SizeCheck.objects.create(
        model=model,
        estat='Pendent',
        talla_base_label=(model.base_size_label or '').strip(),
        created_by_id=created_by_id,
    )
    n = _materialize_lines(sc, model)
    logger.info(f"SizeCheck {sc.pk} created for model {model_id}: {n} lines")
    return sc, n


def model_te_deltes(model) -> bool:
    """El model té regles de grading (deltes informats)?

    Resident (ModelGradingRule, PG-0) o fallback al GradingRuleSet compartit. És el
    booleà que decideix si una correcció de base es propaga a les talles en resoldre.
    """
    from fhort.models_app.models import ModelGradingRule
    if ModelGradingRule.objects.filter(model=model, actiu=True).exists():
        return True
    if model.grading_rule_set_id:
        from fhort.pom.models import GradingRule
        return GradingRule.objects.filter(
            rule_set_id=model.grading_rule_set_id, actiu=True
        ).exists()
    return False


def resolve_size_check(size_check_id: int, estat: str, missatge: str = '',
                       *, user_profile_id: int | None = None, data_represa=None,
                       allow_reopen_sealed: bool = False) -> dict:
    """Resol un SizeCheck Pendent. L'acció sol·licitada (`estat`) i les decisions de línia
    determinen l'estat FINAL i si es propaga al grading:

    GRAVAR (estat='Acceptat'):
      · cap línia 'valor_descartat' → estat='Acceptat': promou None→'tolerancia_acceptada',
        escriu CHECKED (NOMÉS base, abs<1e-6 skip), regradua si base canvia i té deltes
        (mirror close_piece_fitting; NO toca ModelGradingRule), finalitza tasca → Done.
      · alguna línia 'valor_descartat' → estat='Rebutjat': NO promou, NO CHECKED, NO regrade,
        NO Done (proto a refer). Es grava la constància de decisions.
    DESCARTAR (estat='Descartat'): NO toca línies, NO propaga, tasca viva.

    REAGENDAR: quan la tasca queda viva (Rebutjat o Descartat) i ve `data_represa` (date o
    'YYYY-MM-DD'), fixa la tasca size_check al calendari: planned_start/end (calendari
    laboral) + planned_locked, status Pending. Gate tou (sense tasca → no peta).

    Retorna {'estat', 'propagat', 'descartades', 'written', 'lines_accepted', 'base_changed',
             'te_deltes', 'regradat', 'nova_version', 'tasca_finalitzada', 'reagendada',
             'data_represa'}.
    """
    from fhort.models_app.models import (
        BaseMeasurement, SizeCheck, SizeCheckLine,
    )

    if estat not in ('Acceptat', 'Descartat'):
        raise ValueError(f"Estat invàlid: {estat!r} (Acceptat | Descartat).")

    sc = SizeCheck.objects.select_related('model').get(pk=size_check_id)
    if sc.estat != 'Pendent':
        raise ValueError(f"El check ja està resolt (estat actual: {sc.estat}).")
    model = sc.model

    # Resol usuaris: UserProfile (capa SizeCheck) + el seu auth.User (capa log F1).
    profile = None
    auth_user = None
    if user_profile_id:
        from fhort.accounts.models import UserProfile
        profile = UserProfile.objects.select_related('user').filter(pk=user_profile_id).first()
        auth_user = profile.user if profile else None

    descartades = SizeCheckLine.objects.filter(size_check=sc, decisio='valor_descartat').count()

    # Estat final: GRAVAR amb descartades → Rebutjat (no propaga); sense → Acceptat (propaga).
    if estat == 'Acceptat':
        final_estat = 'Rebutjat' if descartades > 0 else 'Acceptat'
    else:
        final_estat = 'Descartat'
    propagat = (final_estat == 'Acceptat')

    written = 0
    lines_accepted = 0
    base_changed = False
    te_deltes = model_te_deltes(model)
    regradat = False
    nova_version = None
    tasca_finalitzada = False

    if propagat:
        # GRAVAR-acceptat: les línies sense decisió expressa s'accepten (tolerància acceptada).
        SizeCheckLine.objects.filter(size_check=sc, decisio__isnull=True).update(
            decisio='tolerancia_acceptada'
        )

        # Escriu CHECKED de les acceptades amb valor_real editat (NOMÉS base; abs<1e-6 skip).
        lines = list(
            SizeCheckLine.objects.filter(size_check=sc, decisio='tolerancia_acceptada')
            .select_related('pom')
        )
        for line in lines:
            if line.valor_real is None:
                continue
            lines_accepted += 1
            bm, _created = BaseMeasurement.objects.get_or_create(
                model=model, pom=line.pom,
                defaults={'base_value_cm': line.valor_real, 'origen': 'CHECKED'},
            )
            # Guarda contra el valor VIGENT: no escriure canvis nuls.
            if not _created and bm.base_value_cm is not None \
                    and abs(line.valor_real - bm.base_value_cm) < 1e-6:
                continue
            bm.base_value_cm = line.valor_real
            bm.origen = 'CHECKED'
            bm._changed_by = auth_user
            bm._motiu = f'Size check · check {sc.pk}'   # deute (b): sense size_check_ref
            bm.save()
            written += 1

        base_changed = written > 0

        # Propagació: regradua les talles des de la base nova (mirror de close_piece_fitting).
        # Només si hi ha canvi de base I el model té deltes. NO toca ModelGradingRule.
        if base_changed and te_deltes:
            from fhort.fitting.services import _resolve_working_size_fitting
            from fhort.pom.services import bump_grading_version_and_generate

            sf = _resolve_working_size_fitting(model)
            if sf is not None:
                # PEÇA 1: mateix helper que close_piece_fitting (guard D-1 + desactiva actives +
                # crea v+1 + measurements_version++ si base_changed + re-propaga). Comportament
                # idèntic al bloc inline anterior; NO toca ModelGradingRule.
                nv = bump_grading_version_and_generate(
                    sf.pk,
                    base_changed=base_changed,
                    profile_id=user_profile_id,
                    allow_reopen_sealed=allow_reopen_sealed,
                    nom=f'Size check {sc.pk}',
                    reopen_context=f'SizeCheck {sc.pk}',
                )
                nova_version = nv.version_number
                regradat = True

        # Finalitza la tasca Kanban size_check → Done. Gate TOU: si no existeix la tasca
        # o la transició no és vàlida, NO peta.
        try:
            from fhort.tasks.models import ModelTask
            from fhort.tasks.services_c import transition_task
            task = (ModelTask.objects
                    .filter(model=model, task_type__code='size_check')
                    .exclude(status='Done').order_by('-id').first())
            if task is not None:
                if task.status != 'InProgress':
                    transition_task(task, 'InProgress', profile)   # Done només des d'InProgress
                transition_task(task, 'Done', profile)
                tasca_finalitzada = True
        except Exception as e:
            logger.warning(f"SizeCheck {sc.pk}: no s'ha pogut finalitzar la tasca size_check: {e}")

    # Rebutjat / Descartat: NO es propaga; la tasca queda viva. Si ve data_represa, reagenda.
    reagendada = False
    if final_estat in ('Rebutjat', 'Descartat') and data_represa:
        from fhort.tasks.services_scheduling import reagenda_tasca
        reagendada = reagenda_tasca(model, data_represa, task_type_code='size_check')

    sc.estat = final_estat
    sc.resolt_per = profile
    sc.resolt_at = timezone.now()
    sc.save(update_fields=['estat', 'resolt_per', 'resolt_at'])

    logger.info(
        f"SizeCheck {sc.pk} resolved [{final_estat}] (req {estat}): descartades={descartades} "
        f"propagat={propagat} written={written} regradat={regradat} nova_version={nova_version} "
        f"tasca_finalitzada={tasca_finalitzada} reagendada={reagendada}"
    )
    return {
        'estat': final_estat, 'propagat': propagat, 'descartades': descartades,
        'written': written, 'lines_accepted': lines_accepted, 'base_changed': base_changed,
        'te_deltes': te_deltes, 'regradat': regradat, 'nova_version': nova_version,
        'tasca_finalitzada': tasca_finalitzada, 'reagendada': reagendada,
        'data_represa': str(data_represa) if data_represa else None,
    }


# Sprint Y — `_reagenda_tasca_size_check` s'ha extret i parametritzat a
# `tasks/services_scheduling.py::reagenda_tasca(model, data_represa, task_type_code)`, perquè la
# convocatòria el pugui reusar. El caller de sota l'invoca directament (cap wrapper).
