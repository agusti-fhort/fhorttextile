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
    """Completa el check amb una SizeCheckLine per cada BaseMeasurement VIGENT que no en tingui.

    valor_teoric = snapshot del base_value_cm EN AQUEST MOMENT; valor_real null (el tècnic
    l'anota); decisio/nota als defaults.

    FIX-3 (DIAGNOSI_MESURES_TEA_205) — abans això era tot-o-res: només s'invocava quan el
    check no tenia CAP línia, de manera que un POM nascut DESPRÉS d'obrir el check (un import
    que amplia la fitxa) no en rebia mai cap i quedava com una fila inerta a l'editor: es
    veia, però no es podia anotar. Ara la funció COMPLETA: recorre els BaseMeasurement vigents
    i crea només els que falten. Les línies ja existents no es toquen —ni el seu valor_teoric—
    perquè un check pendent és un contracte amb el que el tècnic ja té anotat: el teòric
    contra el qual mesura és el del moment en què es va obrir la seva línia, no un que li
    canviï sota els peus. El teòric FRESC és el de la línia NOVA, que és la que no existia.

    Retorna el nombre de línies CREADES.

    🚨 FASE_3/C1-ins — **EL PITJOR CAS DEL CENS, i el que aquesta funció fa que ho sigui.**

    L'aparellament era per `pom_id` PELAT a les dues bandes: `ja_hi_son` era un conjunt de
    `pom_id` i l'`exclude` filtrava per `pom_id__in`. Amb dues germanes del mateix POM al
    model, la PRIMERA que rebia línia BLOQUEJAVA totes les altres — la sisa esquerra no en
    tindria mai cap, i quedaria com una fila inerta a l'editor: es veu, però no es pot
    anotar. És exactament el símptoma que FIX-3 va tancar per l'altra porta, tornant a entrar
    pel segon eix.

    L'`exclude` no es pot expressar per tupla amb l'ORM (no hi ha `__in` de tuples), i per
    això el filtre passa a Python. El cost és irrellevant —una consulta per check— i
    l'alternativa (un `Q` gegant de `AND`/`OR`) diria pitjor el que fa.

    I el `create` estampa els eixos de la mesura d'origen: la línia parla de la mateixa fila
    que la va fer néixer, no d'una que se li assembla.
    """
    from fhort.models_app.models import BaseMeasurement, SizeCheckLine
    ja_hi_son = set(
        SizeCheckLine.objects
        .filter(size_check=size_check)
        .values_list('pom_id', 'capa', 'instancia')
    )
    bms = (
        BaseMeasurement.objects
        .filter(model=model, is_active=True, base_value_cm__isnull=False)
        .select_related('pom')
    )
    n = 0
    for bm in bms:
        if (bm.pom_id, bm.capa, bm.instancia) in ja_hi_son:
            continue
        SizeCheckLine.objects.create(
            size_check=size_check,
            pom=bm.pom,
            capa=bm.capa,
            instancia=bm.instancia,
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
    línies, ni amb POMs vigents sense línia. `_materialize_lines` només CREA les que falten,
    de manera que els valor_real/decisio ja anotats no es toquen mai.

    FIX-3 (DIAGNOSI_MESURES_TEA_205) — AQUEST és el punt on es completa un check Pendent, i
    no el camí d'import. Raons: (1) `open` ja és la porta única del check i ja carrega la
    responsabilitat de «garantir les línies» — completar-les hi és la mateixa promesa, no
    una de nova; (2) l'editor la crida SEMPRE en obrir-se, de manera que confirmar un import
    i després entrar a l'editor queda cobert sense que l'import hagi de saber que existeixen
    els size checks; i (3) qualsevol altra via que ampliï la fitxa (alta manual d'un POM,
    materialització família→item) queda coberta pel mateix preu. L'import no en sap res.

    Un check ja RESOLT no s'hi toca: el filtre és `estat='Pendent'`.

    Retorna (SizeCheck, n_lines) — n_lines és el TOTAL de línies del check, no les creades.
    """
    from fhort.models_app.models import Model, SizeCheck

    model = Model.objects.get(pk=model_id)

    existing = (
        SizeCheck.objects.filter(model=model, estat='Pendent')
        .order_by('-created_at').first()
    )
    if existing is not None:
        # Completa: POMs vigents nascuts DESPRÉS d'obrir el check (o Pendent orfe amb 0
        # línies) hi entren ara, amb el teòric d'ARA. Cap línia existent es reescriu.
        creades = _materialize_lines(existing, model)
        n = existing.linies.count()
        if creades:
            logger.info(f"SizeCheck {existing.pk} completat: +{creades} lines (total {n})")
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
    determinen l'estat FINAL.

    D4 (2026-07-21): resoldre un size check JA NO PROPAGA. Consolida la base i prou; propagar
    és acte conscient amb una sola porta (botó «Propagar a grading»). `regradat` i
    `nova_version` es retornen sempre False/None i es conserven per contracte d'API.
    ⚠️ `allow_reopen_sealed` queda INERT en aquesta funció (ja no hi ha cap escriptura de
    grading que un segell pugui refusar). Es conserva a la signatura perquè hi ha tests que
    el passen; candidat a retirar quan es netegi la signatura.

    GRAVAR (estat='Acceptat'):
      · cap línia 'valor_descartat' → estat='Acceptat': promou None→'tolerancia_acceptada',
        escriu CHECKED (NOMÉS base, abs<1e-6 skip), incrementa measurements_version si la base
        canvia (perquè l'estalitud ho vegi), finalitza tasca → Done.
      · alguna línia 'valor_descartat' → estat='Rebutjat': NO promou, NO CHECKED, NO Done
        (proto a refer). Es grava la constància de decisions.
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
    from fhort.models_app.services_derivacio import aplica as aplica_derivacio

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
            # FASE_3/C1-ins — el veredicte del check torna a la SEVA mesura base. La línia
            # sap dir els dos eixos (els va heretar de la BaseMeasurement que la va fer
            # néixer, a `_materialize_lines`): el lookup els diu també, o el valor acceptat
            # d'una germana aterraria sobre l'altra.
            bm, _created = BaseMeasurement.objects.get_or_create(
                model=model, pom=line.pom, capa=line.capa, instancia=line.instancia,
                defaults={'base_value_cm': line.valor_real, 'origen': 'CHECKED'},
            )
            # Guarda contra el valor VIGENT: no escriure canvis nuls.
            if not _created and bm.base_value_cm is not None \
                    and abs(line.valor_real - bm.base_value_cm) < 1e-6:
                continue
            # C3/E1 — el valor d'ABANS, capturat abans de trepitjar-lo (v. la nota bessona a
            # `fitting/services.py`). En una creació és None i no es deriva.
            valor_anterior = None if _created else bm.base_value_cm
            bm.base_value_cm = line.valor_real
            bm.origen = 'CHECKED'
            bm._changed_by = auth_user
            bm._motiu = f'Size check · check {sc.pk}'   # deute (b): sense size_check_ref
            bm.save()
            # C3/E1 — LA DERIVACIÓ. L'altre dels dos punts que coneixen els seus eixos per
            # còpia (els hereta de la línia, que els va heretar de la mesura que la va fer
            # néixer). Mateix mecanisme, mateix rastre: es mou el valor de les germanes i la
            # folgança es conserva sola. No-op mentre visquin les comportes.
            aplica_derivacio(
                bm, valor_anterior, line.valor_real, auth_user=auth_user,
                motiu_origen=f'size check {sc.pk}')
            written += 1

        base_changed = written > 0

        # D4 (2026-07-21) — AQUÍ hi havia una crida a bump_grading_version_and_generate.
        # Resoldre un size check ja NO propaga: consolida la BASE i prou (BaseMeasurement +
        # MeasurementChangeLog + Welford). Propagar és acte conscient i té una sola porta
        # (botó «Propagar a grading» → generar-grading). Llei de domini DECISIONS.md §2.
        #
        # EL QUE NO ES PERD: measurements_version++ el feia NOMÉS el helper. Sense ell, una base
        # moguda sota una versió segellada deixaria de detectar-se com a estal
        # (fitting/staleness.py). Es conserva aquí; el que marxa és la propagació.
        #
        # `regradat`/`nova_version` queden False/None per contracte: el front ja només ensenya
        # el missatge «grading regradat» quan són certs (CheckMeasureEditor.jsx:335), o sigui
        # que deixa d'ensenyar-lo tot sol — que és exactament el que ara és veritat.
        if base_changed:
            from django.db.models import F
            from fhort.models_app.models import Model as _Model
            _Model.objects.filter(pk=model.pk).update(
                measurements_version=F('measurements_version') + 1
            )

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
