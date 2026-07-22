"""
pom/services.py — Grading and measurement services.
Equivalent to the functions in Frappe's api.py:
  - generate_graded_specs
  - close_base
  - update_client_profile (Welford online)
"""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# G6-B · LA INTEGRITAT DEL SEGELL (DIAGNOSI_G6_DUAL_PATH, Fase 2 · R1)
#
# El segell MENTIA. El guard que hi havia (a `bump_grading_version_and_generate`) protegia
# **crear v+1** sobre una versió aprovada, però NO protegia **escriure dins** la versió activa:
# `_get_or_create_grading_version` filtrava `is_active=True` i prou —no mirava `aprovada`— i
# SIS endpoints hi entraven a reescriure `GradedSpec` in-place conservant `aprovada=True`.
#
# Això és el que feia perillós despinçar el motor de patrons: el motor confia en `gv.aprovada`
# (`patterns/engine/grading_projection.py`), i el flag podia ser cert **mentre el contingut havia
# canviat després del segell**. Una projecció "aprovada" podia projectar unes talles que ningú
# no havia aprovat mai.
#
# El guard viu AQUÍ, en UN sol lloc (mateix patró que `_te_regles`): a la porta per on tots els
# camins han de passar per obtenir la versió on escriuran. Cap guard local per endpoint —els
# endpoints només TRADUEIXEN l'error a 409, no decideixen res.
# ═════════════════════════════════════════════════════════════════════════════

class SealedGradingVersionError(Exception):
    """Escriptura rebutjada: la GradingVersion vigent està SEGELLADA (`aprovada=True`).

    El que s'ha aprovat no es reescriu. La sortida legítima NO és forçar l'escriptura: és
    **crear una versió nova** (v+1) que superi la segellada — el bump que ja existeix
    (`bump_grading_version_and_generate`), que deixa rastre i demana confirmació humana.
    Per això NO hi ha auto-bump aquí: qui escriu ha de decidir-ho, no descobrir-ho.
    """

    def __init__(self, version):
        self.version = version
        # ⚠️ Les dades del 409 es capturen AQUÍ, no a `payload`. Dos dels sis camins refusen des de
        # DINS d'un `transaction.atomic` i han de fer `set_rollback(True)` (si no, el `return` des
        # de dins del bloc atòmic faria COMMIT de l'override que acaben d'escriure). Després d'un
        # `set_rollback`, Django prohibeix qualsevol consulta més: si `payload` toqués la BD per
        # resoldre `version.size_fitting`, petaria amb TransactionManagementError i el 409 es
        # convertiria en un 500. El payload ha de ser PUR.
        sf = version.size_fitting      # (els guards fan select_related: no costa cap consulta)
        self._version_number = version.version_number
        self._version_id = version.pk
        self._sf_id = sf.pk
        self._model_id = sf.model_id
        super().__init__(
            f"GradingVersion v{version.version_number} està aprovada (segellada a producció): "
            f"no s'hi pot escriure. Cal crear una versió nova per superar-la."
        )

    @property
    def payload(self) -> dict:
        """Cos del 409. Viu a l'excepció perquè els sis camins diguin EXACTAMENT el mateix.

        PUR: no toca la BD (v. __init__).
        """
        return {
            'error': 'sealed',   # mateixa clau que el 409 ja existent de generar-grading
            'codi': 'GRADING_VERSION_SEALED',
            'grading_version_id': self._version_id,
            'version_number': self._version_number,
            'size_fitting_id': self._sf_id,
            'model_id': self._model_id,
            'message': (
                f'La versió vigent v{self._version_number} està aprovada (segellada a '
                f"producció). No s'hi pot escriure: el que ja s'ha aprovat no canvia."
            ),
            'sortida': {
                'accio': 'crear_nova_versio',
                'endpoint': f'/api/v1/models/{self._model_id}/generar-grading/',
                'body': {'new_version': True, 'allow_reopen_sealed': True},
                'descripcio': ('Crear una versió nova (v+1) que superi la segellada. '
                               'Queda rastre (Watchpoint) de qui la supera.'),
            },
        }


def sealed_active_version(sf_id):
    """La versió ACTIVA i SEGELLADA d'un SizeFitting, si n'hi ha. El predicat, en UN lloc.

    El feien servir per separat el guard del bump i la còpia PRE-guard de `generar-grading`.
    Ara tots dos —i el guard d'escriptura— pregunten el mateix a la mateixa funció: si el
    predicat del segell ha de canviar mai, que canviï en un sol lloc.
    """
    from fhort.fitting.models import GradingVersion
    return (GradingVersion.objects
            .select_related('size_fitting')     # SealedGradingVersionError el necessita, i sense
            .filter(size_fitting_id=sf_id, is_active=True, aprovada=True)   # consultar després
            .order_by('-version_number').first())


# ─────────────────────────────────────────────────────────────────────────────
# GRADING
# ─────────────────────────────────────────────────────────────────────────────

def escala_del_model(model):
    """ESPAI DE SISTEMA (llei S24b) → (size_run, run_sistema, pos, base_idx).

    Font ÚNICA de la geometria de graduació d'un model, compartida pel generador i pel
    preview. Si divergissin, el wizard ensenyaria una taula que el generador després no
    reprodueix — el mateix criteri que ja obliga `_te_regles` a ser un sol predicat (G6/0b).

    LLEI: **l'ordre i la distància entre talles els mana el SizeSystem.** El run del model és
    un subconjunt, potencialment NO CONTIGU, que mai els redefineix. Abans d'això, el motor
    comptava els passos per POSICIÓ dins la llista del run, i per tant:
      - un run apendat (`XS·S·L·XXS·M`, model 166) graduava la XXS amb el SIGNE INVERTIT;
      - un run amb forat (`XS·S·L`, sense M) comptava S→L com UN pas en comptes de DOS.

    Retorna:
      size_run:    les etiquetes del MODEL, reordenades en memòria per l'ordre del sistema.
                   Es conserva l'ORTOGRAFIA del model (és el que va a `GradedSpec.size_label`);
                   només se'n canvia l'ordre.
      run_sistema: les etiquetes del SISTEMA, ordenades per `SizeDefinition.ordre`. És el
                   referent sobre el qual `_apply_rule` recorre camins i resol el break.
      pos:         etiqueta → índex dins `run_sistema` (pont `canonical_size_label`: XXL↔2XL).
      base_idx:    posició de la talla base EN ESPAI DE SISTEMA.

    La normalització de l'ordre és en MEMÒRIA i no persisteix res: la porta única d'escriptura
    (S24b, `run_del_model`) és qui evita que n'entrin de nous. Això fa el motor robust davant
    dels runs desordenats que ja hi ha a la BD i que el sanejament encara no ha tocat.

    Alça `ValueError` si una etiqueta del run no pertany al sistema: un run que parla d'una
    talla que el seu propi sistema no coneix no té geometria, i calcular-hi seria inventar-se
    la distància en silenci.
    """
    from fhort.pom.grading_utils import run_sistema_de
    from fhort.pom.size_labels import canonical_size_label

    size_run = [s.strip() for s in model.size_run_model.replace(';', '·').split('·') if s.strip()]
    base_size = model.base_size_label.strip()

    if base_size not in size_run:
        raise ValueError(f"La talla base '{base_size}' no és al size run: {size_run}")

    run_sistema = run_sistema_de(model.size_system)
    if not run_sistema:
        raise ValueError(
            f"El sistema de talles del model {model.codi_intern} no té cap talla definida: "
            "no hi ha ordre ni distància contra què graduar."
        )

    pos = {canonical_size_label(e): i for i, e in enumerate(run_sistema)}

    def _pos(label):
        return pos.get(canonical_size_label(label))

    fora = [l for l in size_run if _pos(l) is None]
    if fora:
        raise ValueError(
            f"El size run del model {model.codi_intern} porta talles que el sistema "
            f"'{model.size_system.codi}' no coneix: {', '.join(fora)}."
        )

    size_run = sorted(size_run, key=_pos)
    return size_run, run_sistema, _pos, _pos(base_size)


def generate_graded_specs(size_fitting_id: int) -> int:
    """
    Generate GradedSpec for every size of the Size & Fitting.

    Flow:
      1. Read BaseMeasurement of the model's base size
      2. Read the model's grading rules (resident ModelGradingRule; else the RuleSet's)
      3. For each POM × size, apply the rule (LINEAR/STEP/FIXED/ZERO/EXCEPTION)
      4. Create or update GradedSpec
      5. Mark SF as "Talles generades"

    'EXCEPTION' now has a single source: ModelGradingOverride (per-model). The old second
    source, pom.GradingException (per shared rule set), was retired in G6/1a.

    Returns the number of created/updated GradedSpec.
    """
    from fhort.fitting.models import SizeFitting

    sf = SizeFitting.objects.select_related(
        'model',
        'model__grading_rule_set',
        'model__size_system',
    ).get(pk=size_fitting_id)

    model = sf.model

    # Pre-checks
    if not _te_regles(model):
        raise ValueError(
            f"El model {model.codi_intern} no té regles de grading: ni regles residents "
            f"(ModelGradingRule) ni Grading Rule Set assignat."
        )
    if not model.size_system_id:
        raise ValueError(f"El model {model.codi_intern} no té Size System assignat.")
    if not model.size_run_model:
        raise ValueError(f"El model {model.codi_intern} no té size_run_model definit.")
    if not model.base_size_label:
        raise ValueError(f"El model {model.codi_intern} no té base_size_label definit.")

    # S24b — la geometria (ordre i distància) surt del SizeSystem, no de la llista del run.
    size_run, run_sistema, _pos, base_idx = escala_del_model(model)

    # Load the RuleSet rules
    rules = _load_grading_rules(model)
    # Sprint 5B.3: per-model overrides from validated fittings (highest priority).
    model_overrides = _load_model_overrides(model.pk)
    poms_nomes_override = _poms_amb_override(model_overrides)

    # Load base measurements
    base_measurements = _load_base_measurements(model.pk)

    if not base_measurements:
        raise ValueError(
            f"No hi ha BaseMeasurements per al model {model.codi_intern}. "
            "Cal entrar les mesures de la talla base primer."
        )

    # Create a new grading version or reuse the active one
    grading_version = _get_or_create_grading_version(sf)

    # Sprint 4 / F2: record which measurement version these specs are born from.
    current_version = model.measurements_version

    # Generate specs
    created = 0
    warnings: list[str] = []
    sense_regla: set[int] = set()   # D2: POMs amb base i sense regla → no emeten cap cel·la
    for pom_id, base_val in base_measurements.items():
        rule = rules.get(pom_id)

        for size_label in size_run:
            # S24b: `i` és la posició EN ESPAI DE SISTEMA, no dins la llista del run. És
            # l'única línia que fa que un run amb forat compti la distància real.
            i = _pos(size_label)
            steps = i - base_idx  # negative = smaller size, positive = larger

            override = model_overrides.get((pom_id, size_label))
            if override is not None:
                # Per-model validated-fitting override wins over everything.
                # G6/1a: aquí hi havia una segona branca, `elif exc:` (GradingException), que
                # deixava EXACTAMENT la mateixa petja ('EXCEPTION') que l'override — la fila
                # ni tan sols distingia quin dels dos forks havia guanyat. Jubilada.
                graded_val = override
                gt_applied = 'EXCEPTION'
            elif pom_id in poms_nomes_override and i == base_idx:
                # D2 — POM NOMÉS-OVERRIDE, cel·la de la talla BASE. Vegeu `_poms_amb_override`.
                # L'import mai escriu override a la talla base (el seu valor viu a
                # BaseMeasurement), de manera que aquesta és l'ÚNICA cel·la de la fila que la
                # branca de dalt no pot cobrir. Sense això la fila sortia coixa pel centre.
                graded_val = base_val
                gt_applied = 'EXCEPTION'      # mateixa provinença que la resta de la fila
            elif rule is None:
                # D2 — LLEI DE CEL·LA ABSENT: regla absent → CAP CEL·LA. Mai un FIXED fabricat.
                # Abans aquí hi havia `graded_val = base_val; gt_applied = 'FIXED'`, que davant
                # d'un POM amb base i sense regla emetia el valor base repetit a totes les talles
                # i el reportava com a graduació legítima. És el que va deixar el model 163 amb
                # 225 specs 100% FIXED i delta 0 retornant 200 OK (DIAGNOSI_REFACTOR_GRADING
                # 2026-07-21, R3). Una regla que no existeix no gradua: no emet.
                #
                # Segueix valent per a les talles del run que el POM només-override no cobreix:
                # el rescat de dalt és NOMÉS la base. Un POM que gradua pels seus overrides no
                # és cobertura parcial per manca de regla → no entra a `sense_regla`.
                if pom_id not in poms_nomes_override:
                    sense_regla.add(pom_id)
                continue
            else:
                graded_val, gt_applied = _apply_rule(
                    rule, base_val, steps, i, base_idx,
                    size_run=run_sistema, warnings=warnings,
                )

            if graded_val is None:
                # Hard STEP validation failed for this cell: leave it uncomputed.
                continue

            graded_val = round(graded_val, 2)
            increment = round(graded_val - base_val, 2)

            _upsert_graded_spec(
                grading_version_id=grading_version.pk,
                pom_id=pom_id,
                size_label=size_label,
                graded_value_cm=graded_val,
                grading_type_applied=gt_applied,
                increment_applied_cm=increment,
                generated_from_version=current_version,
            )
            created += 1

    # D2 — una propagació que no produeix cap cel·la NO és un èxit buit: és un error.
    # Es llança ABANS de marcar l'SF, perquè un SF a 'TallesGenerades' amb 0 specs és
    # exactament l'estat mentider que descriu la diagnosi (R3/R5). Diu també PER QUÈ.
    if created == 0:
        if sense_regla:
            raise ValueError(
                f"Propagació avortada per al model {model.codi_intern}: cap de les "
                f"{len(sense_regla)} mesures base té regla de grading. Revisa el Grading "
                f"Rule Set assignat (pot estar buit o no correspondre a aquest model)."
            )
        raise ValueError(
            f"Propagació avortada per al model {model.codi_intern}: no s'ha pogut "
            f"calcular cap cel·la de grading."
        )

    # D2 — cobertura parcial: hi ha graduació, però alguns POMs no emeten. No és un error
    # (la cel·la absent és legítima), però ha de deixar rastre: el silenci era el bug.
    if sense_regla:
        logger.warning(
            f"Grading SF {size_fitting_id}: {len(sense_regla)} POM(s) amb mesura base i "
            f"sense regla → cap cel·la emesa (llei D2 de cel·la absent). POMs: "
            f"{sorted(sense_regla)}"
        )

    # Mark SF
    SizeFitting.objects.filter(pk=size_fitting_id).update(
        estat='TallesGenerades'
    )

    if warnings:
        logger.warning(
            f"Grading SF {size_fitting_id}: {len(warnings)} avís(os) STEP — "
            "cel·les no calculades: " + " | ".join(warnings)
        )
    logger.info(f"Grading generated for SF {size_fitting_id}: {created} specs")
    return created


def preview_graded_specs(model, base_values: dict, warnings: list | None = None) -> dict:
    """
    Càlcul de grading SENSE persistència (preview per al wizard d'importació, W3).

    Reutilitza EXACTAMENT la mateixa lògica que generate_graded_specs (regles, overrides
    per-model, _apply_rule) però sobre valors base en memòria, sense crear cap
    SizeFitting/GradingVersion/GradedSpec. Pensat per omplir talles buides a la taula del
    wizard abans del desament definitiu (W5).

    base_values: {pom_id (POMMaster): base_value_cm}
    Retorna: {pom_id: {size_label: graded_value}} (buit si manquen regles/run/base).
    """
    # G6/0b — el mateix criteri que el gate dur de generate_graded_specs (via `_te_regles`), i no
    # una còpia amb matisos: si el generador i el preview no coincideixen en "aquest model pot
    # graduar?", el wizard ensenya una taula buida per a un model que després gradua igualment.
    if not (_te_regles(model) and model.size_run_model and model.base_size_label):
        return {}
    # S24b — MATEIXA geometria que el generador, per la mateixa raó que el gate de dalt: si el
    # preview comptés els passos per posició i el generador per ordre de sistema, la taula del
    # wizard i la propagació dirien coses diferents per a un run amb forat. El preview no pot
    # petar (només omple una taula): un run invàlid degrada a taula buida.
    if not model.size_system_id:
        return {}
    try:
        size_run, run_sistema, _pos, base_idx = escala_del_model(model)
    except ValueError:
        return {}

    rules = _load_grading_rules(model)
    model_overrides = _load_model_overrides(model.pk)
    poms_nomes_override = _poms_amb_override(model_overrides)

    out = {}
    for pom_id, base_val in base_values.items():
        # D2 — base absent O A ZERO: el POM no existeix per a aquest model → cap cel·la.
        # Mateix criteri que _load_base_measurements, perquè el preview no pot prometre
        # una taula que el generador després no emetrà.
        if base_val is None or float(base_val) == 0.0:
            continue
        base_val = float(base_val)
        rule = rules.get(pom_id)
        row = {}
        for size_label in size_run:
            i = _pos(size_label)          # S24b: posició en espai de sistema
            steps = i - base_idx
            override = model_overrides.get((pom_id, size_label))
            if override is not None:
                graded_val = float(override)
            elif pom_id in poms_nomes_override and i == base_idx:
                # D2 — talla base d'un POM només-override. MATEIXA branca que el generador
                # (v. `_poms_amb_override`): si el preview se la saltés, el wizard ensenyaria
                # la fila coixa que la propagació després omple.
                graded_val = base_val
            elif rule is None:
                # D2 — regla absent → cel·la absent (mateixa llei que generate_graded_specs).
                continue
            else:
                graded_val, _ = _apply_rule(
                    rule, base_val, steps, i, base_idx,
                    size_run=run_sistema, warnings=warnings,
                )
            if graded_val is None:
                # Validació dura STEP fallida: deixa la cel·la buida (sense fallback).
                continue
            row[size_label] = round(graded_val, 2)
        # D2 — POM que no emet cap cel·la no apareix a la taula (fila ABSENT, no fila buida):
        # el generador tampoc no en crearà cap GradedSpec.
        if row:
            out[pom_id] = row
    return out


# Sprint B — final state of a closed measurement table.
CLOSED_STATE = 'Tancat'
# Starting states from which the table may be closed. 'TallesGenerades' is the
# normal state after grading is generated (the real-world entry point); legacy
# 'BaseTancada' is tolerated too.
_CLOSEABLE_FROM = ('Pendent', 'BaseOberta', 'TallesGenerades', 'BaseTancada')


def get_or_create_size_fitting(model, user_id: int | None = None, *, actor_profile_id: int | None = None):
    """
    Return the model's SizeFitting, creating one if it has none.

    ÚNICA funció de materialització lazy d'SF: qualsevol superfície que necessiti
    l'SF de treball i no en trobi (create-piece, tancar base, etc.) passa per aquí,
    no per un creador propi.

    SizeFitting requires numero/codi/tipus/creat_per (creat_per is a non-null
    PROTECT FK), so we resolve a UserProfile from, in order:
      actor_profile_id (l'usuari de la request — el responsable de facto)
      → user_id (auth User id, per compat amb el cridador de close_base)
      → model.responsable → model.created_by (metadades del propi model)
      → any profile (last resort).
    This lets the surface work even for models whose responsable is None and that
    never had an SF (e.g. model 131, o el cas d'onboarding verge B2).
    """
    from fhort.fitting.models import SizeFitting
    from fhort.accounts.models import UserProfile

    sf = SizeFitting.objects.filter(model=model).order_by('numero').first()
    if sf:
        return sf

    next_num = 1
    codi = f"{model.codi_intern}-SF-{next_num}"
    while SizeFitting.objects.filter(codi=codi).exists():
        next_num += 1
        codi = f"{model.codi_intern}-SF-{next_num}"

    profile = None
    if actor_profile_id is not None:
        profile = UserProfile.objects.filter(pk=actor_profile_id).first()
    if profile is None and user_id is not None:
        profile = UserProfile.objects.filter(user_id=user_id).first()
    if profile is None and model.responsable_id:
        profile = UserProfile.objects.filter(pk=model.responsable_id).first()
    if profile is None and model.created_by_id:
        profile = UserProfile.objects.filter(pk=model.created_by_id).first()
    if profile is None:
        profile = UserProfile.objects.first()

    return SizeFitting.objects.create(
        model=model, numero=next_num, codi=codi, tipus='SizeSet', creat_per=profile,
    )


def close_base(size_fitting_id: int, user_id: int | None = None) -> dict:
    """
    Close the measurement table for a Size & Fitting. Final state = 'Tancat'.

    State machine (Sprint B):
      - Valid starting states: Pendent, BaseOberta, TallesGenerades (the normal
        state after grading), plus legacy BaseTancada.
      - If sizes were never generated (no GradedSpec) -> generate them first.
      - Then seal the table: estat='Tancat', base_tancada=True,
        data_tancament_base=now(). Sealing happens AFTER generation so the
        'TallesGenerades' written by generate_graded_specs is overridden.
      - Idempotent: an already-closed table (base_tancada / 'Tancat') returns its
        current state without re-closing and without a hard error.

    Returns a dict: estat, base_tancada, graded_specs, generated_now, already_closed.
    """
    from django.utils import timezone
    from fhort.fitting.models import SizeFitting, GradedSpec

    sf = SizeFitting.objects.get(pk=size_fitting_id)

    def _spec_count():
        return GradedSpec.objects.filter(grading_version__size_fitting=sf).count()

    # Idempotent: already closed -> soft no-op (no hard error).
    if sf.base_tancada or sf.estat == CLOSED_STATE:
        return {
            'estat': sf.estat,
            'base_tancada': sf.base_tancada,
            'graded_specs': _spec_count(),
            'generated_now': 0,
            'already_closed': True,
        }

    if sf.estat not in _CLOSEABLE_FROM:
        raise ValueError(
            f"L'estat actual '{sf.get_estat_display()}' no permet tancar la taula."
        )

    # Generate sizes only if they were not generated yet.
    generated = 0
    if not GradedSpec.objects.filter(grading_version__size_fitting=sf).exists():
        generated = generate_graded_specs(size_fitting_id)  # sets estat='TallesGenerades'

    # Seal the table as closed (final state).
    SizeFitting.objects.filter(pk=size_fitting_id).update(
        base_tancada=True,
        data_tancament_base=timezone.now(),
        estat=CLOSED_STATE,
    )

    total = _spec_count()
    logger.info(f"Table closed for SF {size_fitting_id}: estat=Tancat, specs={total}")
    return {
        'estat': CLOSED_STATE,
        'base_tancada': True,
        'graded_specs': total,
        'generated_now': generated,
        'already_closed': False,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT MEASUREMENT PROFILE (Welford online)
# ─────────────────────────────────────────────────────────────────────────────

def update_client_profile(
    codi_client: str,
    garment_type_id: int,
    pom_id: int,
    size: str,
    value_cm: float,
) -> object:
    """
    Update the online measurement statistic per codi_client/garment/POM/size.
    Uses Welford's algorithm to compute mean and deviation without storing every
    individual value.

    Sprint 5B.3: keyed by `codi_client` (the brand-client within the tenant), not
    by the tenant-level Client FK.
    """
    from django.utils import timezone

    try:
        from fhort.pom.models import ClientMesuraPerfil
    except ImportError:
        logger.warning("ClientMesuraPerfil not found, skipping Welford update")
        return None

    profile, _ = ClientMesuraPerfil.objects.get_or_create(
        codi_client=codi_client or '',
        garment_type_id=garment_type_id,
        pom_id=pom_id,
        talla=size,
    )

    # Welford online algorithm
    n = (profile.n_mostres or 0) + 1
    old_mean = profile.mitjana or 0.0
    delta = value_cm - old_mean
    new_mean = old_mean + delta / n
    delta2 = value_cm - new_mean
    new_m2 = (profile.m2_acum or 0.0) + delta * delta2

    profile.n_mostres = n
    profile.mitjana = round(new_mean, 3)
    profile.m2_acum = new_m2
    profile.desviacio = round((new_m2 / n) ** 0.5, 3) if n > 1 else 0.0
    profile.darrera_actualitzacio = timezone.now()
    profile.save()

    return profile


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOMER POM ALIAS — biblioteca de nomenclatura del client (sembra reutilitzable)
# ─────────────────────────────────────────────────────────────────────────────

def maybe_learn_customer_alias(customer, client_code, description, pom, origen='IMPORT',
                               nomes_si_manual=True):
    """Sembra (idempotent) un CustomerPOMAlias reutilitzable quan un HUMÀ ha resolt la
    vinculació codi-de-document → POM.

    Llei (DIAGNOSI_BIBLIOTECA_CLIENT_2026-07-08): CAP àlies viu retroactiu — escriure un
    àlies NO modifica cap model existent; només sembra les FUTURES importacions d'aquest
    customer. Aquesta funció només toca CustomerPOMAlias.

    `nomes_si_manual` (per defecte True — el comportament de sempre):
      · True  → discriminador manual vs automàtic: si find_pom_master (encara sense aquest
                àlies) ja resol el codi al MATEIX POM amb confiança d'auto-vinculació
                (HIGH/MEDIUM), la vinculació és automàtica → NO se sembra. Evita
                retroalimentar el matcher amb els seus propis encerts.
      · False → s'aprèn de TOT vincle ferm, també dels que el matcher encerta sol
                (QA-S8-R1). El crida així la confirmació de l'import (W5), on el vincle
                **l'ha confirmat una persona**: allà l'objectiu no és protegir el matcher
                de si mateix, és que el REGISTRE DE NOMENCLATURA del client es completi sol
                a cada importació. Un codi que el tècnic ha donat per bo és nomenclatura
                d'aquell client, l'hagi encertat el matcher o no.

    Retorna l'àlies creat/actualitzat o None.
    """
    from fhort.pom.models import CustomerPOMAlias
    from fhort.models_app.extraction_views import find_pom_master

    code = (client_code or '').strip()
    if customer is None or not code or pom is None:
        return None

    if nomes_si_manual:
        pm, _mtype, conf = find_pom_master(code, description or '', customer=customer)
        if pm is not None and pm.id == pom.id and conf in ('HIGH', 'MEDIUM'):
            return None  # el matcher ja ho encerta sol → automàtic, no sembrem

    # GUARD ANTI-COL·LISIÓ (QA-S8 · D4a). Un POM que aquest client JA reclama amb un ALTRE codi
    # no es pot aprendre com a bo: o el codi nou és un sinònim del vell (i sobra), o són DUES
    # mesures distintes i una de les dues quedarà sobre el POM equivocat. No és teòric — al
    # catàleg viu de BRW hi ha 'F' (FRONT total length) i 'FF' (BACK total length) tots dos cap
    # al POM 389 'TOTAL LENGTH', i 'U'/'U2'/'U3' tots tres cap al 439. En comptes d'aprendre'l
    # en silenci, es crea PENDENT DE REVISIÓ perquè una persona el miri.
    ja_reclamat = (CustomerPOMAlias.objects
                   .filter(customer=customer, pom=pom)
                   .exclude(client_code__iexact=code)
                   .exists())

    alias, created = CustomerPOMAlias.objects.get_or_create(
        customer=customer, client_code=code[:60],
        defaults={
            'pom': pom,
            'client_description': (description or '')[:200],
            'origen': origen,
            'pendent_revisio': ja_reclamat,
        },
    )
    if not created and alias.pom_id != pom.id:
        alias.pom = pom
        alias.client_description = (description or '')[:200]
        alias.origen = origen
        alias.pendent_revisio = ja_reclamat
        alias.save(update_fields=['pom', 'client_description', 'origen',
                                  'pendent_revisio', 'actualitzat_at'])
    return alias


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _te_regles(model) -> bool:
    """El model té regles de grading? Residents (ModelGradingRule) O de set.

    G6/0b — LA PORTA D'ENTRADA DEL MOTOR, i ha de fer la MATEIXA pregunta que `_load_grading_rules`
    respon. Abans preguntava una altra cosa: exigia `model.grading_rule_set_id`, o sigui **el
    punter**, quan el motor fa temps que llegeix les regles del MODEL i només cau al set si el model
    no en té cap. Un model equipat amb la branca guanyadora no podia graduar per falta d'un punter
    que el motor ja no fa servir.

    I no era teòric: el model 163 (BRW-FW26-0001) té 25 ModelGradingRule actives, `grading_rule_set`
    NULL i **zero GradedSpec** — no ha pogut graduar mai.

    Alineat amb la Sobirania de la Regla (DECISIONS.md:280-294): *«tot sembra el model però tot viu i
    és modificable AL MODEL, inclosa la REGLA»*. Si la regla viu al model, tenir-ne una ha de bastar
    per graduar.

    El que NO canvia: un model sense regles enlloc continua sense poder graduar (ValueError al
    generador, `{}` al preview). La porta s'alinea amb el motor; no s'obre.

    R2 (2026-07-21) — la porta preguntava pel PUNTER del set (`bool(grading_rule_set_id)`), no
    per les REGLES. Un model apuntant a un GradingRuleSet BUIT passava el gate i graduava a
    FIXED tota la taula. Ara la segona branca compta regles actives del set: mateixa pregunta
    que respon `_load_grading_rules`, que és de qui ha de ser el mirall.
    """
    from fhort.models_app.models import ModelGradingRule
    if ModelGradingRule.objects.filter(model_id=model.id, actiu=True).exists():
        return True
    if not model.grading_rule_set_id:
        return False
    from fhort.pom.models import GradingRule
    return GradingRule.objects.filter(
        rule_set_id=model.grading_rule_set_id, actiu=True
    ).exists()


def _load_grading_rules(model) -> dict:
    """Return {pom_id: rule_obj} for the model's grading rules.

    PG-1 — Fallback: ModelGradingRule (resident al model) té prioritat; si el model
    no en té cap, recau a GradingRule del GradingRuleSet extern (camí vell). Així el
    comportament NO canvia fins que un backfill ompli ModelGradingRule. _apply_rule
    llegeix per getattr → tots dos rule_obj són intercanviables.

    Imports DINS la funció (mateix idioma que la resta del fitxer) per evitar cicles
    models_app ↔ pom a load time.

    R4 (2026-07-21) — aquí hi havia un `except Exception: logger.warning(...); return {}`. Un
    diccionari buit és indistingible de "aquest model no té regles", o sigui que QUALSEVOL
    error carregant-les es convertia en graduar-ho tot a FIXED amb un 200 OK. Era la segona
    porta al mateix símptoma del 163, independent del ruleset buit. Ara un error de càrrega
    puja: val més una propagació que peta que una que menteix.
    """
    from fhort.models_app.models import ModelGradingRule
    rules = ModelGradingRule.objects.filter(model_id=model.id, actiu=True)
    if rules.exists():
        return {r.pom_id: r for r in rules}
    if model.grading_rule_set_id:
        from fhort.pom.models import GradingRule
        return {r.pom_id: r for r in GradingRule.objects.filter(
            rule_set_id=model.grading_rule_set_id, actiu=True
        )}
    return {}


def _load_model_overrides(model_id: int) -> dict:
    """Return {(pom_id, size_label): value_cm} of per-model fitting overrides."""
    try:
        from fhort.models_app.models import ModelGradingOverride
        return {
            (o.pom_id, o.size_label): o.value_cm
            for o in ModelGradingOverride.objects.filter(model_id=model_id)
        }
    except Exception as e:
        logger.warning(f"Could not load ModelGradingOverride: {e}")
        return {}


def _poms_amb_override(model_overrides: dict) -> set:
    """POMs amb ALMENYS un override per-talla → la seva regla efectiva la fa el MODEL.

    D2 (decisió Agus 2026-07-22) · **sobirania del model**. Un import sobre un contenidor de
    client que ja té regles no toca el contenidor (llei M3, INTOCABLE): els POMs que hi
    divergeixen (`conflicte`) o que no hi són (`amplia`) es desen com a `BaseMeasurement` +
    `ModelGradingOverride` per-talla. Aquests POMs no tenen regla i, per tant, el motor els
    tractava com a "sense regla → cap cel·la"... **excepte** allà on hi havia override.

    El resultat era una fila coixa pel centre: l'import exclou explícitament la talla base de
    l'override (el seu valor viu a `BaseMeasurement`), de manera que l'única cel·la que la
    branca d'override no podia cobrir era precisament la base.

    Els overrides SÓN la regla efectiva del POM; a la talla base la font és el valor base del
    model. La resta de la llei D2 no s'afluixa: una talla del run sense override i sense ser
    la base segueix sent **cel·la absent**, mai un valor fabricat.

    El predicat viu en UNA funció perquè el generador i el preview no divergeixin — el mateix
    criteri que ja obliga `_te_regles` i `escala_del_model` a ser fonts úniques.
    """
    return {pom_id for pom_id, _label in model_overrides}


def _load_base_measurements(model_id: int) -> dict:
    """Return {pom_id: base_value_cm}."""
    try:
        from fhort.models_app.models import BaseMeasurement
        # Ignora files materialitzades sense valor (base_value_cm=None) → no es graden.
        # D2: i també les de valor 0 — una talla base a zero és físicament impossible, o
        # sigui que el POM no existeix per a aquest model. No gradua, no emet cel·la. Que
        # un 0 no arribi mai a la base és feina de la validació d'entrada (autoria/import).
        return {
            bm.pom_id: bm.base_value_cm
            for bm in BaseMeasurement.objects.filter(
                model_id=model_id, is_active=True, base_value_cm__isnull=False
            ).exclude(base_value_cm=0).order_by('ordre')
        }
    except Exception as e:
        logger.warning(f"Could not load BaseMeasurements: {e}")
        return {}


def _get_or_create_grading_version(sf):
    """La versió ACTIVA on s'escriurà — o una de nova si no n'hi ha cap.

    ⚠️ **LA PORTA D'ESCRIPTURA DEL GRADING (G6-B/T1).** Tots els camins que persisteixen
    `GradedSpec` passen per aquí per saber ON escriuen. Per tant és aquí —i només aquí— que es
    comprova que la destinació no estigui SEGELLADA. Si ho està, es refusa: `SealedGradingVersionError`.

    **Cap auto-bump.** Seria còmode crear la v+1 tot sol i escriure-hi... i seria un desastre: qui
    ha demanat "regenera les talles" es trobaria una versió nova que no ha demanat, i el segell
    hauria deixat de voler dir res (sempre se superaria sol). Superar un segell és un acte
    conscient: es refusa, es diu com fer-ho, i decideix una persona.

    El `try/except Exception` que embolcallava això s'ha retirat: repetia el mateix codi dues
    vegades com a "fallback" i **s'empassava qualsevol excepció** del cos — inclosa, ara, la del
    guard. Un guard dins d'un `except Exception:` que reintenta no és un guard.
    """
    from fhort.fitting.models import GradingVersion

    sealed = sealed_active_version(sf.pk)
    if sealed is not None:
        raise SealedGradingVersionError(sealed)

    # `-version_number` (no `.last()`): el Meta.ordering de GradingVersion és
    # ['size_fitting', '-data'], i per tant `.last()` retornava la MÉS ANTIGA de les actives
    # (fork 3 de la diagnosi, §B3). Avui és latent —cap SizeFitting té 2+ actives— però aquest
    # és el selector de la porta d'escriptura: no hi pot haver un criteri que ja sabem que és el
    # revés del de tothom (`_active_grading_version` desempata per -version_number).
    version = (GradingVersion.objects
               .filter(size_fitting=sf, is_active=True)
               .order_by('-version_number').first())
    if version is None:
        num = GradingVersion.objects.filter(size_fitting=sf).count() + 1
        version = GradingVersion.objects.create(
            size_fitting=sf, version_number=num, is_active=True,
        )
    return version


def bump_grading_version_and_generate(sf_id, *, base_changed, profile_id=None,
                                      allow_reopen_sealed=False, nom=None,
                                      reopen_context=''):
    """Crea la GradingVersion v+1 d'un SizeFitting i hi propaga el grading.

    PEÇA 1 (sprint paritat Grading): centralitza el versionat funcional que abans vivia
    DUPLICAT inline a close_piece_fitting i resolve_size_check, i el deixa disponible per a
    l'acte conscient de propagar (PEÇA 2). Comportament IDÈNTIC al bloc original.

    Ordre (preservat del bloc original, inclòs el camí d'error):
      1. GUARD D-1: si la versió activa està aprovada (segellada a producció) i no s'autoritza
         la reobertura → ValueError (mateixa forma). reopen_context és l'etiqueta de traça que
         s'incrusta a la nota ('PieceFitting <pk>' / 'SizeCheck <pk>').
      2. Desactiva TOTES les actives (invariant anti multi-activa) i crea la v+1 activa.
         NO toca `aprovada` (el segellat va a part, via advance_phase_gate).
      3. Si base_changed → measurements_version++ del model ABANS de propagar (el guard ja ha
         passat: un guard-raise no incrementa res). generate_graded_specs en deriva
         `generated_from_version`, per això l'increment ha de precedir la propagació.
      4. generate_graded_specs poblà la versió nova (que ja és l'activa).

    Retorna la GradingVersion creada.
    """
    from django.db.models import F, Max
    from fhort.fitting.models import GradingVersion, SizeFitting
    from fhort.models_app.models import Model

    profile = None
    if profile_id:
        from fhort.accounts.models import UserProfile
        profile = UserProfile.objects.filter(pk=profile_id).first()

    # 1. GUARD D-1. Mateix predicat que el guard d'escriptura (G6-B): `sealed_active_version`.
    sealed_active = sealed_active_version(sf_id)
    if sealed_active is not None and not allow_reopen_sealed:
        raise ValueError(
            f"GradingVersion v{sealed_active.version_number} està aprovada "
            f"(segellada a producció); cal reobertura explícita per superar-la."
        )
    reopen_note = None
    if sealed_active is not None:
        reopen_note = (f'Reobertura explícita D-1: supera v{sealed_active.version_number} '
                       f'aprovada ({reopen_context}).')
        logger.warning(f"D-1: {reopen_note}")

    # 2. Versionat funcional: desactiva totes les actives, crea la nova activa.
    GradingVersion.objects.filter(size_fitting_id=sf_id, is_active=True).update(is_active=False)
    max_num = GradingVersion.objects.filter(size_fitting_id=sf_id).aggregate(
        m=Max('version_number')
    )['m'] or 0
    new_version = GradingVersion.objects.create(
        size_fitting_id=sf_id,
        version_number=max_num + 1,
        is_active=True,
        creat_per=profile,
        nom=(nom or 'Propagació'),   # default sensat: nom és NOT NULL a la BD (footgun nom=None/buit)
        notes=reopen_note,
    )

    # 3. measurements_version++ ABANS de propagar (generate_graded_specs en deriva
    #    generated_from_version). Només si la base ha canviat.
    if base_changed:
        model_id = SizeFitting.objects.values_list('model_id', flat=True).get(pk=sf_id)
        Model.objects.filter(pk=model_id).update(
            measurements_version=F('measurements_version') + 1
        )

    # 4. Pobla la versió nova (ara és l'activa que llegeix _get_or_create_grading_version).
    generate_graded_specs(sf_id)
    return new_version


def _norm_label(s) -> str:
    """Normalize a size label for matching — same criterion as the run: upper + strip."""
    return str(s).strip().upper()


def _add_warning(warnings, msg: str) -> None:
    """Record a (deduplicated) grading warning and log it once."""
    if warnings is None:
        logger.warning(msg)
        return
    if msg not in warnings:
        warnings.append(msg)
        logger.warning(msg)


def _apply_rule(rule, base_val: float, steps: int, size_idx: int, base_idx: int,
                size_run=None, warnings=None):
    """Apply the grading rule and return (graded_value, grading_type_applied).

    graded_value is None when the cell cannot be computed (hard STEP validation
    failure); the caller MUST skip it instead of falling back silently.

    ⚠️ **ESPAI DE SISTEMA (llei S24b, 2026-07-22).** `size_run` és el run del **SIZE SYSTEM**
    (totes les talles, ordenades per `SizeDefinition.ordre`), NO el run del model; i
    `size_idx`/`base_idx` són posicions dins d'aquest. Ho prepara `escala_del_model`, i és el
    que fa que la distància entre talles la mani el sistema: un model amb run `XS·S·L` (sense
    M) compta S→L com DOS passos, perquè el camí es recorre sobre les talles del SISTEMA.
    Abans, `size_run` era la llista del model i els índexs hi eren posicions: un run apendat
    invertia el SIGNE de les talles petites (model 166) i un run amb forat col·lapsava la
    distància. Cap fórmula d'aquesta funció ha canviat — només el referent que rep.

    Real Django fields: rule.logica (was grading_type), rule.increment (DecimalField),
    rule.valors_step (JSONField).

    Contracts:
      - LINEAR: scalar `rule.increment`, applied uniformly per step.
      - STEP: `rule.valors_step` = {dest_label: delta}. Each delta is the increment
        between that label and its neighbour one step closer to the base; values
        accumulate outward from the base (added going up, subtracted going down).
        Every label the path CROSSES must have an entry — a missing one yields a
        warning and an uncomputed cell, never a silent fallback to `increment`.
        S24b: el camí es recorre sobre les talles del SISTEMA. Un model amb run no
        contigu, doncs, necessita el delta de la talla que ell no fabrica però que el
        camí travessa (`XS·S·L` cap a L travessa la M): és la distància real. Sense
        aquest delta la cel·la queda ABSENT, mai a zero ni col·lapsada — la mateixa llei
        D2 de cel·la absent que ja regia aquí.
      - FIXED / ZERO / (default): unchanged.
    """
    grading_type = rule.logica
    increment = float(rule.increment) if rule.increment else 0.0

    # Peça A — forma CANÒNICA: si increment_base està poblat, el motor gradua des d'aquí
    # (unifica import STEP, import LINEAR-amb-break i ISO above_xl). El llindar es resol per
    # ETIQUETA contra el RUN DE GRADUACIÓ (size_run del model), no contra el run del ruleset →
    # portable i cobreix rulesets sense size_system. Label absent al run → cap break (uniforme).
    # PG-4b-3a: `logica` és la veritat del règim. STEP NO grada canònic encara que increment_base
    # estigui poblat (es conserva latent per a STEP↔LINEAR no-destructiu) → cau a la branca STEP.
    if grading_type != 'STEP' and getattr(rule, 'increment_base', None) is not None:
        ib = float(rule.increment_base)
        brk = float(rule.increment_break) if rule.increment_break is not None else ib
        if size_idx == base_idx:
            return base_val, grading_type
        break_idx = None
        if rule.talla_break_label and size_run:
            norm = [_norm_label(x) for x in size_run]
            tl = _norm_label(rule.talla_break_label)
            if tl in norm:
                break_idx = norm.index(tl)
        if size_idx > base_idx:
            path, sign = range(base_idx + 1, size_idx + 1), 1.0
        else:
            path, sign = range(size_idx, base_idx), -1.0
        total = 0.0
        for j in path:
            total += brk if (break_idx is not None and j >= break_idx) else ib
        return base_val + sign * total, grading_type

    if grading_type == 'LINEAR':
        return base_val + (steps * increment), 'LINEAR'

    elif grading_type == 'STEP':
        pom_codi = getattr(getattr(rule, 'pom', None), 'codi_client', None) or rule.pom_id
        vs = rule.valors_step
        if not isinstance(vs, dict) or not vs:
            _add_warning(warnings,
                f"Regla STEP del POM {pom_codi}: valors_step buit o invàlid; cap cel·la calculada.")
            return None, 'STEP'
        if size_run is None:
            _add_warning(warnings,
                f"Regla STEP del POM {pom_codi}: falta el size run per calcular.")
            return None, 'STEP'
        # The base size itself is the origin: no delta needed.
        if size_idx == base_idx:
            return base_val, 'STEP'
        deltas = {_norm_label(k): v for k, v in vs.items()}
        # Indices crossed when moving from the base toward this size; the farther
        # label of each step carries that step's delta.
        if size_idx > base_idx:
            path, sign = range(base_idx + 1, size_idx + 1), 1.0
        else:
            path, sign = range(size_idx, base_idx), -1.0
        total = 0.0
        for j in path:
            delta = deltas.get(_norm_label(size_run[j]))
            if delta is None:
                _add_warning(warnings,
                    f"Regla STEP del POM {pom_codi}: falta delta per a la talla {size_run[j]}.")
                return None, 'STEP'
            total += float(delta)
        return base_val + sign * total, 'STEP'

    elif grading_type == 'FIXED':
        return base_val, 'FIXED'

    elif grading_type == 'ZERO':
        return 0.0, 'ZERO'

    # Default: FIXED
    return base_val, 'FIXED'


def _upsert_graded_spec(
    grading_version_id: int,
    pom_id: int,
    size_label: str,
    graded_value_cm: float,
    grading_type_applied: str,
    increment_applied_cm: float,
    generated_from_version: int | None = None,
):
    """Create or update a GradedSpec.

    G6-B/T1 — segona porta, i no és redundant. Avui l'ÚNIC cridador és `generate_graded_specs`,
    que ja ha passat pel guard de `_get_or_create_grading_version`; això protegeix el cridador
    de DEMÀ, que rebrà un `grading_version_id` d'on sigui i podria apuntar a una versió
    segellada sense passar per la porta. Cap `GradedSpec` no pot aterrar sobre un segell.
    """
    from fhort.fitting.models import GradedSpec, GradingVersion

    segellada = (GradingVersion.objects
                 .select_related('size_fitting')
                 .filter(pk=grading_version_id, aprovada=True)
                 .first())
    if segellada is not None:
        raise SealedGradingVersionError(segellada)

    try:
        GradedSpec.objects.update_or_create(
            grading_version_id=grading_version_id,
            pom_id=pom_id,
            size_label=size_label,
            defaults={
                'graded_value_cm': graded_value_cm,
                'grading_type_applied': grading_type_applied,
                'increment_applied_cm': increment_applied_cm,
                'is_active': True,
                'generated_from_version': generated_from_version,
            }
        )
    except Exception as e:
        logger.error(f"Error creating GradedSpec pom={pom_id} size={size_label}: {e}")
        raise
