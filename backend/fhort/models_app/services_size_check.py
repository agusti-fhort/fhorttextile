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


def open_size_check(model_id: int, *, created_by_id: int | None = None):
    """Obre (o reutilitza) un SizeCheck Pendent del model i materialitza les línies.

    Reutilitza el SizeCheck Pendent viu si n'hi ha (no en crea un de segon); l'històric
    són els resolts. Cada open parteix del BaseMeasurement VIGENT: una línia per cada
    BaseMeasurement actiu amb valor (base_value_cm no null), valor_teoric = snapshot.

    Retorna (SizeCheck, n_lines).
    """
    from fhort.models_app.models import (
        Model, BaseMeasurement, SizeCheck, SizeCheckLine,
    )

    model = Model.objects.get(pk=model_id)

    existing = (
        SizeCheck.objects.filter(model=model, estat='Pendent')
        .order_by('-created_at').first()
    )
    if existing is not None:
        n = existing.linies.count()
        return existing, n

    sc = SizeCheck.objects.create(
        model=model,
        estat='Pendent',
        talla_base_label=(model.base_size_label or '').strip(),
        created_by_id=created_by_id,
    )

    bms = (
        BaseMeasurement.objects
        .filter(model=model, is_active=True, base_value_cm__isnull=False)
        .select_related('pom')
    )
    n = 0
    for bm in bms:
        SizeCheckLine.objects.create(
            size_check=sc,
            pom=bm.pom,
            valor_teoric=bm.base_value_cm,   # snapshot del vigent en crear la línia
            valor_real=None,                 # el tècnic l'anota
            acceptat=False,
        )
        n += 1

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
                       *, user_profile_id: int | None = None) -> dict:
    """Resol un SizeCheck Pendent (Acceptat | Descartat).

    En 'Acceptat': cada SizeCheckLine amb decisio='tolerancia_acceptada' i valor_real no
    null escriu BaseMeasurement amb origen='CHECKED' (NOMÉS base). Guarda abs(<1e-6) contra
    el valor base VIGENT → no escriu canvis nuls. El signal F1 registra el canvi (context
    'checked'). Si hi ha canvi de base i el model té deltes, regradua les talles via el
    motor resident (mirror de close_piece_fitting): NO toca ModelGradingRule.

    Retorna {'estat', 'written', 'lines_accepted', 'base_changed', 'te_deltes',
             'regradat', 'nova_version'}.
    """
    from fhort.models_app.models import (
        BaseMeasurement, Model, SizeCheck, SizeCheckLine,
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

    written = 0
    lines_accepted = 0

    if estat == 'Acceptat':
        lines = list(
            SizeCheckLine.objects.filter(size_check=sc, decisio='tolerancia_acceptada')
            .select_related('pom')
        )
        for line in lines:
            if line.valor_real is None:
                continue
            lines_accepted += 1
            # Escriptura CHECKED — només la base (NO deltes ni ModelGradingRule).
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
    te_deltes = model_te_deltes(model)
    regradat = False
    nova_version = None

    # Propagació: regradua les talles des de la base nova (mirror de close_piece_fitting).
    # Només si hi ha hagut canvi de base I el model té deltes. NO toca ModelGradingRule.
    if base_changed and te_deltes:
        from django.db.models import F, Max
        from fhort.fitting.models import GradingVersion
        from fhort.fitting.services import _resolve_working_size_fitting
        from fhort.pom.services import generate_graded_specs

        sf = _resolve_working_size_fitting(model)
        if sf is not None:
            GradingVersion.objects.filter(size_fitting=sf, is_active=True).update(is_active=False)
            max_num = GradingVersion.objects.filter(size_fitting=sf).aggregate(
                m=Max('version_number')
            )['m'] or 0
            nv = GradingVersion.objects.create(
                size_fitting=sf,
                version_number=max_num + 1,
                is_active=True,
                creat_per=profile,
                nom=f'Size check {sc.pk}',
            )
            nova_version = nv.version_number
            Model.objects.filter(pk=model.pk).update(
                measurements_version=F('measurements_version') + 1
            )
            generate_graded_specs(sf.pk)   # llegeix base nova + regles residents
            regradat = True

    sc.estat = estat
    sc.resolt_per = profile
    sc.resolt_at = timezone.now()
    sc.save(update_fields=['estat', 'resolt_per', 'resolt_at'])

    logger.info(
        f"SizeCheck {sc.pk} resolved [{estat}]: {lines_accepted} accepted, {written} written, "
        f"te_deltes={te_deltes} regradat={regradat} nova_version={nova_version}"
    )
    return {
        'estat': estat, 'written': written, 'lines_accepted': lines_accepted,
        'base_changed': base_changed, 'te_deltes': te_deltes,
        'regradat': regradat, 'nova_version': nova_version,
    }
