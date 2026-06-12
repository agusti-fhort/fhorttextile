"""
fitting/services.py — Services for the fitting cycle.

The new cycle (FittingSession / PieceFitting / PieceFittingLine) lives below.
The legacy SFFitting cycle (create_fitting/close_fitting/cancel_fitting) was
removed in Sprint 5B.5 together with the SFFitting/SFFittingLinia models.
"""
from __future__ import annotations
import logging
import uuid as _uuid

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


# ── Peça 1 — guard de solapament ─────────────────────────────────────────────
class SessionOverlapError(Exception):
    """Conflicte DUR: ja hi ha una sessió viva del mateix model que solapa la franja
    (mateixa data i franja encavalcada, o alguna sense hora a la mateixa data).
    El `conflicts` és la llista d'ids de sessió en conflicte (per a la resposta 409)."""
    def __init__(self, message, conflicts):
        super().__init__(message)
        self.conflicts = conflicts


class SessionSoftConflict(Exception):
    """Conflicte SUAU: ja hi ha sessió viva del mateix model i mateixa fase en una
    franja DIFERENT. Requereix confirmació (force=True) per crear igualment."""
    def __init__(self, message, sessions):
        super().__init__(message)
        self.sessions = sessions


class SessionActionConflict(Exception):
    """409 — l'estat de la sessió (Oberta o amb peces) no permet l'acció directa
    (eliminació); cal anul·lar-la amb motiu via /discard/."""
    pass


def _slot_overlap(s_start, s_dur, n_start, n_dur):
    """True si [s_start, s_start+s_dur) ∩ [n_start, n_start+n_dur) ≠ ∅ (mateix dia)."""
    import datetime as _dt
    base = _dt.date(2000, 1, 1)
    a0 = _dt.datetime.combine(base, s_start)
    a1 = a0 + _dt.timedelta(minutes=s_dur or 0)
    b0 = _dt.datetime.combine(base, n_start)
    b1 = b0 + _dt.timedelta(minutes=n_dur or 0)
    return a0 < b1 and b0 < a1


def check_session_overlap(*, model_id, data, fase, start_time, duracio_minuts,
                          exclude_session_id=None):
    """Sessions vives (≠ Tancada/Anullada) del MATEIX model que xoquen amb la nova franja.

    Retorna (hard, soft) — dues llistes de FittingSession:
      hard → mateixa data i solapament de franja; o mateixa data amb alguna sense hora.
      soft → mateixa fase en una franja diferent (no dur).
    Només aplica a sessions de model (garment_set → ([], []), sense guard)."""
    from .models import FittingSession
    if not model_id:
        return [], []
    qs = (FittingSession.objects
          .filter(model_id=model_id)
          .exclude(estat__in=['Tancada', 'Anullada']))
    if exclude_session_id:
        qs = qs.exclude(pk=exclude_session_id)
    hard, soft = [], []
    for s in qs:
        if s.data == data:
            if s.start_time is None or start_time is None:
                hard.append(s)            # mateixa data, alguna sense hora → no desambiguable
            elif _slot_overlap(s.start_time, s.duracio_minuts, start_time, duracio_minuts):
                hard.append(s)            # franges encavalcades
            elif s.fase == fase:
                soft.append(s)            # mateix dia, franja diferent, mateixa fase
        elif s.fase == fase:
            soft.append(s)                # dia diferent, mateixa fase
    return hard, soft


# ═════════════════════════════════════════════════════════════════════════════
# Sprint 5B.3 — Fitting cycle (FittingSession / PieceFitting / PieceFittingLine)
# Open (create) + close with FUNCTIONAL versioning + brain stub. Gate is 5B.4.
# ═════════════════════════════════════════════════════════════════════════════

def create_session(
    *,
    fase: str,
    data,
    model_id: int | None = None,
    garment_set_id: int | None = None,
    responsable_id: int | None = None,
    model_persona: str = '',
    assistents: str = '',
    lloc: str = '',
    notes: str = '',
    created_by_id: int | None = None,
):
    """Create a FittingSession for a single Model OR a GarmentSet (XOR)."""
    from fhort.fitting.models import FittingSession

    if bool(model_id) == bool(garment_set_id):
        raise ValueError("Cal exactament un de model_id o garment_set_id (XOR).")

    return FittingSession.objects.create(
        fase=fase,
        data=data,
        model_id=model_id,
        garment_set_id=garment_set_id,
        responsable_id=responsable_id,
        model_persona=model_persona,
        assistents=assistents,
        lloc=lloc,
        notes=notes,
        created_by_id=created_by_id,
    )


def schedule_session(*, fase, data, responsable_id, model_id=None, garment_set_id=None,
                     lloc='', start_time=None, end_time=None,
                     duracio_minuts=None, attendee_ids=None, created_by_id=None,
                     force=False, _skip_recompute=False, _skip_guard=False):
    """Programa un fitting (estat Programada). El responsable fixa dia (i opcionalment hores).
    No s'executa fins que s'obre (open_session).
    `duracio_minuts`: default 10 min × N (N=peces del set, o 1 per single).
    `attendee_ids`: assistents interns; si hi ha start_time → recompute de la seva cua.
    `created_by_id`: UserProfile.id de qui crea (traçabilitat).
    `force`: salta el bloqueig per conflicte SUAU (no el dur, que sempre bloqueja).
    `_skip_recompute`: inhibeix el recompute per sessió (ús intern de schedule_bulk, que en
    fa UN de sol al final sobre la unió d'attendees). Els attendees s'assignen igualment.
    `_skip_guard`: omet el guard de solapament (ús intern de schedule_bulk, que el fa per
    model abans i decideix ometre/avisar a banda)."""
    if bool(model_id) == bool(garment_set_id):
        raise ValueError("Cal exactament un de model_id o garment_set_id (XOR).")
    # Redisseny 5C: el fitting ja NO exigeix Production Delivered prèvia. La via adaptativa
    # (gestió de la recepció esperada) viu a la view schedule(), no com a bloqueig dur aquí.
    from .models import FittingSession
    if duracio_minuts is None:
        if garment_set_id:
            from fhort.models_app.models import GarmentSet
            n = GarmentSet.objects.get(pk=garment_set_id).num_pieces or 1
        else:
            n = 1
        duracio_minuts = 10 * n
    # Guard de solapament (Peça 1): dur → 409; suau sense force → requereix confirmació.
    if not _skip_guard and model_id:
        hard, soft = check_session_overlap(
            model_id=model_id, data=data, fase=fase,
            start_time=start_time, duracio_minuts=duracio_minuts)
        if hard:
            raise SessionOverlapError(
                f"Ja hi ha una sessió viva d'aquest model que solapa la franja del {data}.",
                [s.id for s in hard])
        if soft and not force:
            raise SessionSoftConflict(
                f"Ja hi ha {len(soft)} sessió(ns) viva(es) de fase {fase} d'aquest model "
                "en una altra franja. Confirma per crear-ne una de nova.",
                [s.id for s in soft])
    session = FittingSession.objects.create(
        fase=fase, data=data, model_id=model_id, garment_set_id=garment_set_id,
        responsable_id=responsable_id, lloc=lloc,
        start_time=start_time, end_time=end_time,
        duracio_minuts=duracio_minuts, estat='Programada',
        created_by_id=created_by_id)
    if attendee_ids:
        session.attendees.set(attendee_ids)
        if start_time and not _skip_recompute:   # recompute només si hi ha franja real i no s'inhibeix
            try:
                from fhort.planning.plan_service import recompute_for_technicians
                recompute_for_technicians(set(attendee_ids))
            except Exception:
                logger.exception('recompute post-schedule no-fatal')
    return session


def schedule_bulk(*, fase, data, start_time, model_ids,
                  duracio_minuts=None, attendee_ids=None,
                  responsable_id=None, lloc='', created_by_id=None):
    """Crea N FittingSessions ENCADENADES amb un `convocatoria` UUID compartit.

    Les sessions s'encadenen: la i+1 comença on acaba la i, via add_working_minutes(None, …)
    sobre el CALENDARI D'EMPRESA PUR (salta pauses/jornada/caps de setmana/festius). Si no hi
    ha `start_time`, NO s'encadena (totes queden sense hora, marcador de dia). El recompute es
    fa UN sol cop al final sobre la unió d'attendees (cada sessió s'inhibeix amb _skip_recompute).

    Peça 1: `model_ids` es DEDUPLICA preservant ordre. El guard de solapament s'aplica per
    model: els conflictes DURS s'OMETEN (no es crea) i es reporten a `skipped`; els SUAUS NO
    bloquegen (el bulk és una acció deliberada), només s'avisa a `warnings`.

    Retorna (sessions, convocatoria, skipped, warnings):
      sessions → FittingSession creades; convocatoria → UUID (None si no se'n crea cap);
      skipped  → [{'model_id', 'reason'}] (durs omesos);
      warnings → [{'model_id', 'reason'}] (suaus creats igualment)."""
    from fhort.planning.calendar_service import add_working_minutes
    import datetime as _dt

    model_ids = list(dict.fromkeys(model_ids))   # dedup preservant ordre
    convocatoria = _uuid.uuid4()
    sessions = []
    skipped = []
    warnings = []
    current_data = data          # pot avançar si l'encadenament creua fi de jornada
    current_start = start_time   # time object o None

    with transaction.atomic():
        for model_id in model_ids:
            dur = duracio_minuts if duracio_minuts is not None else 10

            hard, soft = check_session_overlap(
                model_id=model_id, data=current_data, fase=fase,
                start_time=current_start, duracio_minuts=dur)
            if hard:
                # Conflicte dur → ometre i reportar; NO consumeix la franja (no s'encadena).
                skipped.append({
                    'model_id': model_id,
                    'reason': f"Solapament amb sessió viva existent (ids {[s.id for s in hard]}).",
                })
                continue
            if soft:
                warnings.append({
                    'model_id': model_id,
                    'reason': f"Ja existeix sessió de fase {fase} en una altra franja "
                              f"(ids {[s.id for s in soft]}); creada igualment.",
                })

            session = schedule_session(
                fase=fase,
                data=current_data,
                start_time=current_start,
                duracio_minuts=dur,
                attendee_ids=attendee_ids or [],
                responsable_id=responsable_id,
                model_id=model_id,
                lloc=lloc,
                created_by_id=created_by_id,
                _skip_recompute=True,
                _skip_guard=True,   # el guard ja s'ha fet aquí per model
            )
            session.convocatoria = convocatoria
            session.save(update_fields=['convocatoria'])
            sessions.append(session)

            # Encadenar només si hi ha hora real (sense hora → marcador de dia, no s'encadena).
            if current_start is not None:
                start_dt = _dt.datetime.combine(current_data, current_start)
                end_dt = add_working_minutes(None, start_dt, dur)  # naïf in → naïf out
                current_data = end_dt.date()    # pot ser un altre dia (salta jornada/festius)
                current_start = end_dt.time()

        # Recompute ÚNIC al final (no N): unió d'attendees. No-fatal.
        if attendee_ids and start_time and sessions:
            try:
                from fhort.planning.plan_service import recompute_for_technicians
                recompute_for_technicians(set(attendee_ids))
            except Exception:
                logger.exception('recompute post-schedule-bulk no-fatal')

    if not sessions:
        convocatoria = None   # no s'ha creat res → no hi ha convocatòria
    return sessions, convocatoria, skipped, warnings


def open_session(session_id):
    """Obre una sessió Programada (acte del tècnic, el dia del fitting): Programada→Oberta."""
    from .models import FittingSession
    s = FittingSession.objects.get(pk=session_id)
    if s.estat != 'Programada':
        raise ValueError(f"Només es pot obrir una sessió Programada (estat actual: {s.estat}).")
    s.estat = 'Oberta'
    fields = ['estat']
    if s.started_at is None:        # Peça 1 — marca real d'obertura
        s.started_at = timezone.now()
        fields.append('started_at')
    s.save(update_fields=fields)
    return s


def create_piece_fitting(session_id: int, model_id: int, *, created_by_id: int | None = None):
    """Create a PieceFitting for one piece and materialise its lines.

    Resolves the model's working SizeFitting → its active GradingVersion, then
    clones each active GradedSpec into a PieceFittingLine (valor_teoric = grading,
    valor_real = copy of the theoretical, editable). Returns (piece_fitting, n_lines).
    """
    from fhort.fitting.models import (
        FittingSession, PieceFitting, PieceFittingLine, GradedSpec,
    )
    from fhort.models_app.models import Model

    session = FittingSession.objects.get(pk=session_id)
    model = Model.objects.get(pk=model_id)

    sf = _resolve_working_size_fitting(model)
    if sf is None:
        raise ValueError(f"El model {model.codi_intern} no té cap SizeFitting de treball.")

    version = _active_grading_version(sf)
    if version is None:
        raise ValueError(
            f"El model {model.codi_intern} no té cap GradingVersion activa. "
            "Cal generar les talles primer."
        )

    pf = PieceFitting.objects.create(
        session=session,
        model=model,
        grading_version=version,
        created_by_id=created_by_id,
    )

    specs = GradedSpec.objects.filter(grading_version=version, is_active=True).select_related('pom')
    n = 0
    for spec in specs:
        PieceFittingLine.objects.create(
            piece_fitting=pf,
            pom=spec.pom,
            size_label=spec.size_label,
            valor_teoric=spec.graded_value_cm,
            valor_real=spec.graded_value_cm,  # copy, editable before close
        )
        n += 1

    logger.info(f"PieceFitting {pf.pk} created for model {model_id}: {n} lines")
    return pf, n


def close_piece_fitting(piece_fitting_id: int, *, user_profile_id: int | None = None) -> dict:
    """Close a PieceFitting, applying validated real values with FUNCTIONAL versioning.

    For each line where valor_real differs from valor_teoric:
      - BASE size  → promote to BaseMeasurement (root change) → F1 signal logs the
        change, measurements_version++, grading regenerated from the new base.
      - NON-base   → ModelGradingOverride (per-model, traceable), root untouched.
      - Welford fed with the real value (keyed by codi_client).
    Any validated change → a NEW GradingVersion (v+1) is created and the previous one
    deactivated (conserved). The brain stub is called once if anything changed.

    Returns: {'changed', 'base_changed', 'override_changed', 'new_version'}.
    """
    from django.db.models import F, Max
    from fhort.fitting.models import (
        PieceFitting, PieceFittingLine, GradingVersion,
    )
    from fhort.models_app.models import Model, BaseMeasurement, ModelGradingOverride

    pf = PieceFitting.objects.select_related(
        'model', 'grading_version', 'grading_version__size_fitting',
    ).get(pk=piece_fitting_id)
    model = pf.model
    sf = pf.grading_version.size_fitting
    base_size = (model.base_size_label or '').strip()

    # Resolve users: UserProfile (fitting layer) + its auth.User (F1 log layer).
    profile = None
    auth_user = None
    if user_profile_id:
        from fhort.accounts.models import UserProfile
        profile = UserProfile.objects.select_related('user').filter(pk=user_profile_id).first()
        auth_user = profile.user if profile else None

    lines = list(PieceFittingLine.objects.filter(piece_fitting=pf).select_related('pom'))

    changed = 0
    base_changed = False
    override_changed = False

    for line in lines:
        if line.valor_real is None:
            continue
        if abs(line.valor_real - line.valor_teoric) < 1e-6:
            continue  # no change on this line
        changed += 1
        is_base = line.size_label.strip() == base_size

        if is_base:
            # Root change → BaseMeasurement (the F1 signal writes the change log).
            bm, _created = BaseMeasurement.objects.get_or_create(
                model=model, pom=line.pom,
                defaults={'base_value_cm': line.valor_real, 'origen': 'FITTED'},
            )
            bm.base_value_cm = line.valor_real
            bm.origen = 'FITTED'
            bm._changed_by = auth_user
            bm._fitting_ref = sf            # MeasurementChangeLog.fitting_ref (→ SizeFitting)
            bm._motiu = f'Fitting · sessió {pf.session_id} · peça {pf.pk}'
            bm.save()
            base_changed = True
        else:
            # Per-model override (does NOT touch the shared rule_set or the root).
            ModelGradingOverride.objects.update_or_create(
                model=model, pom=line.pom, size_label=line.size_label,
                defaults={
                    'value_cm': line.valor_real,
                    'motiu': f'Fitting · sessió {pf.session_id} · peça {pf.pk}',
                    'fitting_ref': pf,
                    'created_by': profile,
                },
            )
            override_changed = True

        # Welford (keyed by codi_client within the tenant).
        if model.garment_type_id:
            try:
                from fhort.pom.services import update_client_profile
                update_client_profile(
                    codi_client=model.codi_client,
                    garment_type_id=model.garment_type_id,
                    pom_id=line.pom_id,
                    size=line.size_label,
                    value_cm=line.valor_real,
                )
            except Exception as e:
                logger.warning(f"Welford update failed: {e}")

    new_version_number = None
    if changed:
        # Functional versioning: deactivate ALL active versions (handles the
        # legacy multi-active anomaly), then create the new active one.
        GradingVersion.objects.filter(size_fitting=sf, is_active=True).update(is_active=False)
        max_num = GradingVersion.objects.filter(size_fitting=sf).aggregate(
            m=Max('version_number')
        )['m'] or 0
        new_version = GradingVersion.objects.create(
            size_fitting=sf,
            version_number=max_num + 1,
            is_active=True,
            creat_per=profile,
            nom=f'Fitting sessió {pf.session_id}',
        )
        new_version_number = new_version.version_number

        if base_changed:
            Model.objects.filter(pk=model.pk).update(
                measurements_version=F('measurements_version') + 1
            )

        # Regenerate grading into the NEW active version (reads new base + overrides).
        from fhort.pom.services import generate_graded_specs
        generate_graded_specs(sf.pk)

        # Brain stub (decoupled; no propagation yet).
        from fhort.fitting.brain import on_fitting_measurement_changed
        on_fitting_measurement_changed(
            piece_fitting_id=pf.pk,
            model_id=model.pk,
            base_changed=base_changed,
            new_grading_version_id=new_version.pk,
        )

    # Segellat correcte: single-model tanca en gravar; GarmentSet espera que totes les
    # peces estiguin resoltes (session_can_advance). _seal_session és idempotent i captura
    # la durada real al tancament.
    _seal_session(pf.session)

    result = {
        'changed': changed,
        'base_changed': base_changed,
        'override_changed': override_changed,
        'new_version': new_version_number,
    }
    logger.info(f"PieceFitting {pf.pk} closed: {result}")
    return result


def discard_piece_fitting(piece_fitting_id: int) -> dict:
    """Revert a PieceFitting to its OPENING state: valor_real := valor_teoric for
    every line, atomically. Pure measurement revert — does NOT touch FittingSession,
    FittingPhoto, notes, gates, GradingVersion or grading. Returns {'reverted': N}.
    """
    from django.db import transaction
    from django.db.models import F
    from fhort.fitting.models import PieceFittingLine

    with transaction.atomic():
        reverted = (
            PieceFittingLine.objects
            .filter(piece_fitting_id=piece_fitting_id)
            .update(valor_real=F('valor_teoric'))
        )

    logger.info(f"PieceFitting {piece_fitting_id} discarded: {reverted} lines reverted")
    return {'reverted': reverted}


# ── Sprint 5B.3 helpers ──────────────────────────────────────────────────────

def _resolve_working_size_fitting(model):
    """The model's single working SizeFitting (prefer one with an active version)."""
    from fhort.fitting.models import SizeFitting, GradingVersion
    sfs = list(SizeFitting.objects.filter(model=model).order_by('numero'))
    if not sfs:
        return None
    for sf in sfs:
        if GradingVersion.objects.filter(size_fitting=sf, is_active=True).exists():
            return sf
    return sfs[0]


def _active_grading_version(sf):
    """Active GradingVersion of a SizeFitting (highest version_number wins)."""
    from fhort.fitting.models import GradingVersion
    return (
        GradingVersion.objects
        .filter(size_fitting=sf, is_active=True)
        .order_by('-version_number')
        .first()
    )


# ═════════════════════════════════════════════════════════════════════════════
# Sprint 5B.4 — Two-level gate + manual phase advance + production seal
# ═════════════════════════════════════════════════════════════════════════════

_GATE_RESULTS = ('OK', 'NO_OK', 'EXCEPCIO')
_GATE_ADVANCEABLE = ('OK', 'EXCEPCIO')  # EXCEPCIO = accepted exception → advances


def set_piece_gate(
    piece_fitting_id: int,
    resultat: str,
    motiu: str = '',
    *,
    user_profile_id: int | None = None,
):
    """Set the gate of a PieceFitting (a step AFTER close). Records who/when.

    resultat ∈ {OK, NO_OK, EXCEPCIO}. NO_OK fires the brain stub (future re-opening).
    """
    from django.utils import timezone
    from fhort.fitting.models import PieceFitting

    if resultat not in _GATE_RESULTS:
        raise ValueError(f"resultat ha de ser un de {_GATE_RESULTS} (rebut: {resultat!r}).")

    pf = PieceFitting.objects.select_related('model').get(pk=piece_fitting_id)
    pf.gate = resultat
    pf.gate_motiu = motiu or ''
    pf.gate_per_id = user_profile_id
    pf.gate_at = timezone.now()
    pf.save(update_fields=['gate', 'gate_motiu', 'gate_per', 'gate_at'])

    if resultat == 'NO_OK':
        # "Fallar és individual": signal the brain so it can later re-open this
        # piece's tasks. Stub today (no propagation).
        from fhort.fitting.brain import on_fitting_measurement_changed
        on_fitting_measurement_changed(
            piece_fitting_id=pf.pk,
            model_id=pf.model_id,
            base_changed=False,
            new_grading_version_id=None,
        )

    # 3r trigger: en gatejar, si la sessió (GarmentSet) ja té totes les peces resoltes
    # → es segella aquí (sense esperar advance_phase). Idempotent.
    _seal_session(pf.session)

    logger.info(f"PieceFitting {pf.pk} gate set to {resultat}")
    return pf


def session_can_advance(session_id: int) -> bool:
    """DERIVED (not stored): the session may advance iff every PieceFitting gate is
    in {OK, EXCEPCIO} and there is at least one piece (none Pendent/NO_OK)."""
    from fhort.fitting.models import PieceFitting

    gates = list(
        PieceFitting.objects.filter(session_id=session_id).values_list('gate', flat=True)
    )
    if not gates:
        return False
    return all(g in _GATE_ADVANCEABLE for g in gates)


def _seal_session(session):
    """Segella una FittingSession (→Tancada) i captura la durada real. Idempotent.
    GarmentSet: només segella si totes les peces estan resoltes (session_can_advance,
    gates ∈ {OK, EXCEPCIO}). Single-model: segella directament."""
    if session.estat == 'Tancada':
        return  # idempotent
    if session.garment_set_id and not session_can_advance(session.id):
        return  # peces pendents o NO_OK → encara no es tanca
    session.estat = 'Tancada'
    fields = ['estat']
    if session.finished_at is None:     # Peça 1 — marca real de tancament
        session.finished_at = timezone.now()
        fields.append('finished_at')
    session.save(update_fields=fields)
    # Allibera la franja de fitting de la cua dels assistents (no-fatal).
    try:
        attendee_ids = list(session.attendees.values_list('id', flat=True))
        if attendee_ids:
            from fhort.planning.plan_service import recompute_for_technicians
            recompute_for_technicians(set(attendee_ids))
    except Exception:
        logger.exception('recompute post-seal no-fatal')
    _capture_duration(session)


def _capture_duration(session):
    """Captura la durada real de la sessió cap a FittingDurationStat (Welford, per model).
    Sense start_time → no es mesura. Durada < 0 o > 240 min → descartada (soroll)."""
    if not session.start_time:
        return  # guard: sense hora d'inici no podem mesurar
    import datetime as _dt
    from django.utils import timezone
    start_dt = timezone.make_aware(_dt.datetime.combine(session.data, session.start_time))
    durada_real = (timezone.now() - start_dt).total_seconds() / 60
    if durada_real < 0 or durada_real > 240:
        return  # guard de soroll
    n = (session.piece_fittings.count() or 1) if session.garment_set_id else 1
    update_fitting_duration_stat(durada_real / n)


def update_fitting_duration_stat(value_minutes):
    """Welford incremental de durada real per model de sessió (singleton pk=1).
    Mateix patró que pom.services.update_client_profile."""
    from fhort.fitting.models import FittingDurationStat
    stat, _ = FittingDurationStat.objects.get_or_create(pk=1)
    n = stat.n_mostres + 1
    delta = value_minutes - stat.mitjana
    new_mean = stat.mitjana + delta / n
    delta2 = value_minutes - new_mean
    new_m2 = stat.m2_acum + delta * delta2
    stat.n_mostres = n
    stat.mitjana = round(new_mean, 2)
    stat.m2_acum = new_m2
    stat.desviacio = round((new_m2 / n) ** 0.5, 3) if n > 1 else 0.0
    stat.save()
    return stat


@transaction.atomic
def advance_phase(session_id: int, nova_fase: str, *, user_profile_id: int | None = None) -> dict:
    """Manual phase advance: the responsible person CHOOSES nova_fase (may skip,
    repeat or go back — we do NOT compute "the next one").

    Guards: session Oberta + session_can_advance + nova_fase ∈ Model.FASE_CHOICES.
    For each PieceFitting: seal its vigent GradingVersion (aprovada + aprovada_per +
    data_aprovacio) and set its Model.fase_actual = nova_fase. Closes the session.

    Per-piece TOP guard: a piece already at 'TOP' asked to advance from TOP is a
    no-op (skipped, reported), not an error.
    """
    from django.utils import timezone
    from fhort.fitting.models import FittingSession, PieceFitting
    from fhort.models_app.models import Model

    valid_phases = {c[0] for c in Model.FASE_CHOICES}
    if nova_fase not in valid_phases:
        raise ValueError(f"nova_fase ha de ser ∈ {sorted(valid_phases)} (rebut: {nova_fase!r}).")

    session = FittingSession.objects.get(pk=session_id)
    if session.estat != 'Oberta':
        raise ValueError(f"La sessió ja està {session.estat}; només s'avança des d'Oberta.")
    if not session_can_advance(session_id):
        raise ValueError("La sessió no pot avançar: hi ha peces Pendent o NO_OK.")

    pieces = list(
        PieceFitting.objects.filter(session_id=session_id)
        .select_related('model', 'grading_version', 'grading_version__size_fitting')
    )

    # Regla dura (Sprint E): pre-check de confecció ABANS de cap mutació, per evitar estat
    # parcial en sessions multi-model. Els models a TOP se salten (no avancen, no s'exigeixen).
    from fhort.tasks.services_e import has_delivered_production
    missing = sorted({
        pf.model.pk for pf in pieces
        if pf.model.fase_actual != 'TOP'
        and not has_delivered_production(pf.model.pk, pf.model.fase_actual)
    })
    if missing:
        raise ValueError(
            f"No es pot avançar: cap confecció entregada per a la fase actual dels models {missing}."
        )

    now = timezone.now()
    sealed = []
    advanced = []
    skipped_top = []

    for pf in pieces:
        # TODO(§3.3 — deute conscient): Model.fase_actual el deriva avui tasks
        # (recalculate_current_phase via signal). Amb tasks=0 no hi ha conflicte;
        # la reconciliació múscul↔tasques és posterior. Escriptura directa a posta.
        model = pf.model
        if model.fase_actual == 'TOP':
            skipped_top.append(model.pk)
            continue

        # Seal the vigent (active) GradingVersion of this piece's SizeFitting.
        version = _active_grading_version(pf.grading_version.size_fitting)
        if version is not None:
            version.aprovada = True
            version.aprovada_per_id = user_profile_id
            version.data_aprovacio = now
            version.save(update_fields=['aprovada', 'aprovada_per', 'data_aprovacio'])
            sealed.append(version.pk)

        prev_phase = model.fase_actual
        Model.objects.filter(pk=model.pk).update(fase_actual=nova_fase)
        advanced.append(model.pk)

        try:
            from fhort.tasks.models import GateEvent
            GateEvent.objects.create(
                model_id=model.pk,
                from_phase=prev_phase,
                to_phase=nova_fase,
                by_id=user_profile_id,
                notes='(via fitting)',
            )
        except Exception:
            pass  # no trencar el fitting si el log falla

    _seal_session(session)

    result = {
        'nova_fase': nova_fase,
        'advanced_models': advanced,
        'sealed_versions': sealed,
        'skipped_top_models': skipped_top,
    }
    logger.info(f"Session {session_id} advanced: {result}")
    return result


# ═════════════════════════════════════════════════════════════════════════════
# Peça 2 — Gestió de convocatòria + segellat independent.
# Operacions de grup (per `convocatoria` UUID) i de cicle de vida de sessió.
# "Viu" = estat NOT IN (Tancada, Anullada).
# ═════════════════════════════════════════════════════════════════════════════
_DEAD_ESTATS = ['Tancada', 'Anullada']


def _group_live_qs(conv_uuid):
    """Sessions vives d'un grup (convocatoria), ordenades cronològicament."""
    from .models import FittingSession
    return (FittingSession.objects
            .filter(convocatoria=conv_uuid)
            .exclude(estat__in=_DEAD_ESTATS)
            .order_by('data', 'start_time', 'id'))


def _recompute_attendees(profile_ids):
    """Recompute no-fatal de la cua de planificació d'uns assistents."""
    if not profile_ids:
        return
    try:
        from fhort.planning.plan_service import recompute_for_technicians
        recompute_for_technicians(set(profile_ids))
    except Exception:
        logger.exception('recompute no-fatal')


def reschedule_group(conv_uuid, data, start_time=None):
    """(Op 1) Re-programa les sessions VIVES del grup. Manté l'interval relatiu
    original entre start_times (offset respecte la primera sessió amb hora). Si
    `start_time` és None, només canvia la data. Retorna [ids actualitzats]."""
    import datetime as _dt
    lives = list(_group_live_qs(conv_uuid))
    if not lives:
        return []
    aff_profiles = set()
    updated = []

    if start_time is None:
        for s in lives:
            s.data = data
            s.save(update_fields=['data'])
            updated.append(s.id)
            aff_profiles.update(s.attendees.values_list('id', flat=True))
        _recompute_attendees(aff_profiles)
        return updated

    # Re-encadenar mantenint l'offset relatiu respecte la primera start_time del grup.
    D0 = _dt.date(2000, 1, 1)
    bases = [s.start_time for s in lives if s.start_time is not None]
    base_dt = _dt.datetime.combine(D0, min(bases)) if bases else None
    new_base_dt = _dt.datetime.combine(D0, start_time)
    for s in lives:
        s.data = data
        if s.start_time is not None and base_dt is not None:
            offset = _dt.datetime.combine(D0, s.start_time) - base_dt
            s.start_time = (new_base_dt + offset).time()
            s.save(update_fields=['data', 'start_time'])
        else:
            s.save(update_fields=['data'])
        updated.append(s.id)
        aff_profiles.update(s.attendees.values_list('id', flat=True))
    _recompute_attendees(aff_profiles)
    return updated


def _delete_session_if_allowed(session, conflict_msg=None):
    """DELETE físic si Programada i sense PieceFitting. Si no:
       Oberta o amb peces → SessionActionConflict (409);
       Tancada/Anullada → ValueError (400). Retorna l'id esborrat."""
    if conflict_msg is None:
        conflict_msg = ("La sessió ja ha estat oberta; usa /discard/ per "
                        "anul·lar-la amb motiu.")
    if session.estat in _DEAD_ESTATS:
        raise ValueError("Estat no permet eliminació.")
    if session.estat == 'Oberta' or session.piece_fittings.exists():
        raise SessionActionConflict(conflict_msg)
    sid = session.id
    profiles = list(session.attendees.values_list('id', flat=True))
    session.delete()
    _recompute_attendees(profiles)
    return sid


def discard_session(session_id, motiu=''):
    """(Op 3) Anul·la una sessió des de Programada o Oberta → Anullada + motiu +
    finished_at. Des de Tancada/Anullada → ValueError (400)."""
    from .models import FittingSession
    s = FittingSession.objects.get(pk=session_id)
    if s.estat not in ('Programada', 'Oberta'):
        raise ValueError(
            f"La sessió està {s.estat}; només es pot anul·lar des de Programada o Oberta.")
    s.estat = 'Anullada'
    s.motiu_anullacio = motiu or ''
    s.finished_at = timezone.now()
    s.save(update_fields=['estat', 'motiu_anullacio', 'finished_at'])
    _recompute_attendees(list(s.attendees.values_list('id', flat=True)))
    return s


def add_model_to_group(conv_uuid, model_id, *, fase=None, created_by_id=None, force=False):
    """(Op 4) Afegeix un model nou al grup. 409 si el model ja hi té sessió viva.
    Encadena start_time al final de l'última sessió viva (start_time + duracio_minuts,
    calendari d'empresa). Aplica el guard de solapament existent (_skip_guard=False)."""
    import datetime as _dt
    from .models import FittingSession

    if not FittingSession.objects.filter(convocatoria=conv_uuid).exists():
        raise ValueError("Convocatòria no trobada.")
    if FittingSession.objects.filter(
            convocatoria=conv_uuid, model_id=model_id
            ).exclude(estat__in=_DEAD_ESTATS).exists():
        raise SessionActionConflict("Model ja és al grup.")

    last = _group_live_qs(conv_uuid).last()
    if fase is None:
        any_session = (FittingSession.objects.filter(convocatoria=conv_uuid)
                       .order_by('data', 'start_time', 'id').first())
        fase = (last or any_session).fase

    data = last.data if last else timezone.now().date()
    duracio = (last.duracio_minuts if last and last.duracio_minuts else 10)
    start_time = None
    if last and last.start_time is not None:
        from fhort.planning.calendar_service import add_working_minutes
        start_dt = _dt.datetime.combine(last.data, last.start_time)
        end_dt = add_working_minutes(None, start_dt, last.duracio_minuts or 10)
        data = end_dt.date()
        start_time = end_dt.time()

    responsable_id = last.responsable_id if last else None
    attendee_ids = list(last.attendees.values_list('id', flat=True)) if last else []

    session = schedule_session(
        fase=fase, data=data, responsable_id=responsable_id,
        model_id=model_id, start_time=start_time,
        duracio_minuts=duracio, attendee_ids=attendee_ids,
        created_by_id=created_by_id, force=force,
        _skip_guard=False,   # Op 4: guard de solapament ACTIU
    )
    session.convocatoria = conv_uuid
    session.save(update_fields=['convocatoria'])
    return session


def remove_model_from_group(conv_uuid, model_id):
    """(Op 5) Treu un model del grup. Programada sense peces → DELETE físic;
    Oberta o amb peces → 409 'Usa /discard/'; Tancada/Anullada → 400.
    Retorna l'id esborrat."""
    from .models import FittingSession
    qs = (FittingSession.objects
          .filter(convocatoria=conv_uuid, model_id=model_id)
          .order_by('id'))
    if not qs.exists():
        raise ValueError("El model no és al grup.")
    live = qs.exclude(estat__in=_DEAD_ESTATS).first()
    target = live or qs.first()
    return _delete_session_if_allowed(target, conflict_msg="Usa /discard/ per anul·lar-la amb motiu.")


def set_group_attendees(conv_uuid, attendee_ids):
    """(Op 6) Substitueix (set) el M2M attendees de TOTES les sessions vives del grup.
    Retorna [ids actualitzats]."""
    lives = list(_group_live_qs(conv_uuid))
    aff_profiles = set(int(a) for a in (attendee_ids or []))
    updated = []
    for s in lives:
        aff_profiles.update(s.attendees.values_list('id', flat=True))  # també els trets
        s.attendees.set(attendee_ids or [])
        updated.append(s.id)
    _recompute_attendees(aff_profiles)
    return updated


def seal_session(session_id):
    """(Op 7) Segellat INDEPENDENT: crida _seal_session (idempotent, marca finished_at,
    allibera franja). NO toca fase del model ni crida advance_phase. Anullada → 400."""
    from .models import FittingSession
    s = FittingSession.objects.get(pk=session_id)
    if s.estat == 'Anullada':
        raise ValueError("Una sessió anul·lada no es pot segellar.")
    _seal_session(s)
    s.refresh_from_db()
    return s


def delete_group(conv_uuid):
    """(Ajust 1) Elimina en BLOC totes les sessions d'una convocatòria — ATÒMIC.

    Conflicte = sessió Oberta o amb PieceFitting. Si n'hi ha cap → NO esborra res i
    retorna {'ok': False, 'conflicts': [{id, model_codi, model_nom}]}. Si no n'hi ha
    cap → esborra TOTES i retorna {'ok': True, 'removed': [ids]}."""
    from .models import FittingSession
    sessions = list(FittingSession.objects.filter(convocatoria=conv_uuid).select_related('model'))
    if not sessions:
        raise ValueError("Convocatòria no trobada.")
    conflicts = [s for s in sessions if s.estat == 'Oberta' or s.piece_fittings.exists()]
    if conflicts:
        return {'ok': False, 'conflicts': [
            {'id': s.id,
             'model_codi': (s.model.codi_intern if s.model_id else None),
             'model_nom': (s.model.nom_prenda if s.model_id else None)}
            for s in conflicts]}
    profiles = set()
    for s in sessions:
        profiles.update(s.attendees.values_list('id', flat=True))
    ids = [s.id for s in sessions]
    with transaction.atomic():
        FittingSession.objects.filter(id__in=ids).delete()
    _recompute_attendees(profiles)
    return {'ok': True, 'removed': ids}
