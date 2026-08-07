"""models_app/services.py — lògica de domini reutilitzable del model.

`customer_code_for` és la ÚNICA font de veritat del prefix del codi_intern: unifica els
camins que abans divergien (hardcode 'FTT', marca via codi_client, schema_name[:3]='FHO').
Sempre retorna un codi de 3 chars no buit gràcies al fallback al self-customer del tenant.
"""


def get_self_customer():
    """El Customer que representa el tenant com a client d'ell mateix (is_self=True).
    Sembrat per data migration amb codi = Client.codi_tenant. None si encara no existeix."""
    from fhort.tasks.models import Customer
    return Customer.objects.filter(is_self=True).order_by('id').first()


def resolve_customer_for(model):
    """El Customer efectiu d'aquest model: l'explícit, o el self-customer com a fallback.
    Pot ser None si encara no hi ha self-customer (cas degradat, cobert per customer_code_for)."""
    cust = getattr(model, 'customer', None)
    if cust and getattr(cust, 'codi', None):
        return cust
    return get_self_customer()


def customer_code_for(model):
    """Codi (3 chars) que prefixa el codi_intern d'aquest model i n'escopa la seqüència.

    Ordre: customer explícit del model → self-customer del tenant (fallback elegant).
    Mai retorna buit mentre existeixi el self-customer (sembrat al Pas 6); si tot falla,
    cau a 'IMP' com a últim recurs defensiu perquè el codi-gen no peti.
    """
    cust = resolve_customer_for(model)
    if cust and cust.codi:
        return cust.codi
    return 'IMP'


def reserve_sequence_range(customer, year, season, n):
    """Reserva atòmicament un rang de N seqüencials per a (customer, year, season).

    Retorna (first, last) inclusius (1-indexat dins el comptador). El rang cobreix tant
    models simples com GarmentSet (el codi_base d'un set consumeix 1 número, igual que un
    model simple) — qui crida distribueix els números fila a fila.

    Patró select_for_update (mateix que tasks/services_i.py:31): bloqueja la fila del
    comptador durant la transacció perquè pujades concurrents no col·lisionin. select_for_update
    funciona per-schema sota django-tenants. El camí manual (signal) NO usa això; segueix amb
    el scan MAX(sequencial). Només el bulk reserva rang.

    El comptador NO és l'única font de números: el camí manual (signal generate_model_code) i
    el wizard (models_app/views.py) creen models escrivint `sequencial` sense tocar-lo mai. Un
    comptador que només es mirés a si mateix començaria per 1 en un client que ja té models i
    xocaria contra codi_intern (unique) → IntegrityError. Per això el terra de la reserva és
    max(comptador, MAX(sequencial) real): monòton respecte del terreny, mai el contradiu.
    """
    from django.db import transaction
    from fhort.models_app.models import ModelSequence

    if n <= 0:
        return (0, -1)  # rang buit (cap fila a importar)

    with transaction.atomic():
        seq, _ = ModelSequence.objects.select_for_update().get_or_create(
            customer=customer, year=year, season=season,
        )
        # El terra es recalcula SOTA el lock (seq.last_seq ja és el valor bloquejat).
        floor = max(seq.last_seq, _real_max_seq(customer, year, season))
        first = floor + 1
        seq.last_seq = floor + n
        seq.save(update_fields=['last_seq'])
        last = seq.last_seq
    return (first, last)


def _real_max_seq(customer, year, season):
    """L'últim seqüencial que hi ha AL TERRENY (el que sigui que l'hagi escrit).

    Els models EXTERN (federació) queden EXCLOSOS: conserven el sequencial del Brand, que
    viu en un altre espai de numeració; comptar-lo aquí enverinaria el comptador local
    (Bandera 1 de la diagnosi). Només els INTERN defineixen el terra d'aquesta casa.
    """
    from django.db.models import Max
    from fhort.models_app.models import Model
    return Model.objects.filter(
        customer=customer, any=year, temporada=season,
    ).exclude(origen=Model.ORIGEN_EXTERN).aggregate(m=Max('sequencial'))['m'] or 0


def sequence_floor(customer, year, season):
    """L'últim seqüencial ocupat per (customer, year, season), sense reservar res.

    Mateixa llei que `reserve_sequence_range` —max(comptador, terreny)— però en lectura pura.
    La conciliació de l'import la fa servir per ENSENYAR quins codis s'ocuparan: el codi que
    el tècnic veu a la pantalla ha de ser exactament el que després s'escriurà, i això només
    es garanteix si les dues bandes comparteixen aquesta definició (una sola llei, un sol
    rellotge). Sense lock: és una ullada, no una reserva.
    """
    from fhort.models_app.models import ModelSequence
    counter = (ModelSequence.objects
               .filter(customer=customer, year=year, season=season)
               .values_list('last_seq', flat=True).first()) or 0
    return max(counter, _real_max_seq(customer, year, season))


# Claus estables dels 4 camps de configuració d'un Model. Ordre = ordre lògic
# d'ompliment (tipologia → talla base → run/sistema → regla d'escalat). FONT ÚNICA:
# reusada pel Watchpoint d'import (creació/recàlcul) i pel gate suau de POMs.
CONFIG_KEYS = ['garment_type_item', 'base_size', 'size_run', 'grading_rule_set']


def model_config_missing(model):
    """Retorna QUINS dels 4 camps de configuració del model encara són buits, per clau
    estable (subconjunt ordenat de CONFIG_KEYS). Llista buida = configuració completa.

    Pura lectura, sense efectes ni queries addicionals (usa els *_id ja carregats):
    - 'garment_type_item' → garment_type_item FK no assignada (la tipologia).
    - 'base_size'         → base_size_label buit (etiqueta de la talla base).
    - 'size_run'          → size_run_model buit O size_system FK no assignada (el run de talles).
    - 'grading_rule_set'  → grading_rule_set FK no assignada (la regla d'escalat).
    """
    missing = []
    if model.garment_type_item_id is None:
        missing.append('garment_type_item')
    if not (model.base_size_label or '').strip():
        missing.append('base_size')
    if not (model.size_run_model or '').strip() or model.size_system_id is None:
        missing.append('size_run')
    if model.grading_rule_set_id is None:
        missing.append('grading_rule_set')
    return missing


# Etiquetes curtes (CA) per al text de fallback del Watchpoint d'import. El front re-renderitza
# per clau en l'idioma del lector quan hi ha 'dades'; aquest text és el resum llegible de reserva.
_CONFIG_LABELS_CA = {
    'garment_type_item': 'tipologia de la peça',
    'base_size': 'talla base',
    'size_run': 'run de talles',
    'grading_rule_set': "regla d'escalat",
}


def config_missing_text(missing):
    """Text de fallback (CA) per al Watchpoint d'import segons les claus que falten.
    Llista buida → missatge de configuració completa."""
    if not missing:
        return 'Configuració del model completa.'
    labels = ', '.join(_CONFIG_LABELS_CA.get(k, k) for k in missing)
    return f'Completa la configuració del model abans de definir POMs: {labels}.'


#: D'on ha sortit la regla que la pantalla de Graduació ensenya. Vocabulari TANCAT: el front
#: hi penja el rètol de la franja, i el gest d'Acceptar només existeix per a les PROPOSTES.
PROPOSTA_MODEL = 'model'    # el model ja té graduació (resident o ruleset seu) — no és proposta
PROPOSTA_PERFIL = 'perfil'  # SizingProfile de la combinació (target×construcció×fit×família)
PROPOSTA_ITEM = 'item'      # GarmentTypeItem.grading_rule_set (fallback)


def ruleset_de_catalec(model):
    """El GradingRuleSet que el CATÀLEG proposa per a aquest model → `(font, rule_set)`.

    NO mira si el model ja en té: només diu què proposaria el catàleg. Els dos consumidors en
    volen coses diferents —`resol_proposta_graduacio` hi decideix la proposta, i
    `measurements_table_view` l'usa per OMPLIR ELS FORATS de la pantalla— i partir-ho evita que
    l'un hagi de desfer la decisió de l'altre.

    LA CADENA (decisió D-B, Agus 2026-07-31):
      1. `SizingProfile` de la combinació (target×construcció×fit×família) → 'perfil'. És la font
         VIVA del suggeriment des del 2026-07-23 i cobreix el 98% del catàleg de staging.
      2. `GarmentTypeItem.grading_rule_set` → 'item'. Fallback: és on la S4 va assignar a PROD
         (RS146-149) i on `measurements_table_view` ja queia per omplir la pantalla.
      3. Res → (None, None).

    AGNÒSTIC D'ENTORN (D-C): cap id cablejat. Proposa el que la cadena resolgui, sigui el
    catàleg de staging (75..217) o el de PROD (146-149).

    El `fit` surt de `Model.fit_type`, que MAI és buit (CharField amb default 'Regular',
    models_app/models.py:224); `normalize_fit_type` fa el pont entre el seu vocabulari CamelCase
    i el `FitType.codi` del catàleg. Un fit fora de catàleg no és un error: només vol dir que cap
    perfil hi casa, i la cadena baixa al fallback de l'item.
    """
    # 1 — SizingProfile. Tolerant a NULL a cada baula: si falta qualsevol eix, no hi ha perfil
    # que hi pugui casar i es baixa al fallback sense soroll.
    if model.target and model.construction and model.garment_type_id:
        from fhort.pom.models import (FitTypeDesconegut, SizingProfile,
                                      normalize_fit_type)
        try:
            fit = normalize_fit_type(model.fit_type)
        except FitTypeDesconegut:
            # Un fit que el catàleg no coneix ('Tailored' no té equivalent, v. FIT_ALIES_MODEL)
            # no és un error de pantalla: vol dir que cap perfil hi pot casar. Es busca sense
            # filtrar per fit i, si tampoc, la cadena baixa a l'item.
            fit = None
        qs = SizingProfile.objects.filter(
            target__codi=model.target,
            construction__codi=model.construction,
            garment_type_id=model.garment_type_id,
            grading_rule_set__isnull=False,
        ).select_related('grading_rule_set')
        if fit is not None:
            qs = qs.filter(fit_type_id=fit.id)
        # Perfil del CLIENT del model abans que el genèric: mateix criteri de prioritat que
        # `sizing_profiles_view` (pom/s2_views.py:107-119), aquí reduït al que decideix.
        perfil = (qs.filter(customer_id=model.customer_id).first() if model.customer_id else None) \
            or qs.filter(customer__isnull=True).first() \
            or qs.first()
        if perfil is not None:
            return (PROPOSTA_PERFIL, perfil.grading_rule_set)

    # 2 — l'item. `garment_type_item` pot ser NULL (models antics): getattr, no accés directe.
    rs = getattr(model.garment_type_item, 'grading_rule_set', None)
    if rs is not None:
        return (PROPOSTA_ITEM, rs)

    return (None, None)


def resol_proposta_graduacio(model):
    """Què ha d'ensenyar la pantalla de GRADUACIÓ d'aquest model → `(font, rule_set)`.

    El model MANA sempre: si ja té graduació (resident o ruleset seu) la resposta és
    ('model', None) i no hi ha res a acceptar — el catàleg proposa, el model disposa. Només
    quan no en té es baixa al catàleg (`ruleset_de_catalec`).

    `(None, None)` no és un error: és un model que encara no sap graduar, i el flux de
    Graduació existeix precisament per a ell.
    """
    from fhort.pom.services import _te_regles

    if _te_regles(model):
        return (PROPOSTA_MODEL, None)
    return ruleset_de_catalec(model)


#: R8 — traducció entre els dos vocabularis de provinença. `GradingRuleSet.origen` diu
#: CANONICAL/CLIENT_RUN/IMPORT (o NULL, no classificat); `ModelGradingRule.origen` diu
#: IMPORTED/CANONICAL/CLIENT_RUN/MANUAL. Abans el wizard resolia la diferència escrivint
#: sempre el literal 'CANONICAL', que és el que va fer que 104 regles de client es
#: presentessin com a canòniques.
_ORIGEN_RS_A_MGR = {
    'CANONICAL': 'CANONICAL',
    'CLIENT_RUN': 'CLIENT_RUN',
    'IMPORT': 'IMPORTED',
}


def origen_mgr_des_de_ruleset(rule_set) -> str:
    """Provinença que han de dur les regles residents materialitzades des de `rule_set`.

    Ruleset sense origen classificat (NULL) → 'MANUAL': la provinença no està establerta, i
    afirmar que és canònica seria tornar a mentir (decisió Agus, 2026-07-21).
    """
    return _ORIGEN_RS_A_MGR.get(getattr(rule_set, 'origen', None) or '', 'MANUAL')


#: Sentinella per a `joc_anterior`. NO és `None`: `None` vol dir «el model no tenia cap joc»,
#: que és una informació ben real; això vol dir «el caller no m'ho ha dit», i llavors el motor
#: es comporta exactament com abans de la decisió 6.1.
JOC_ANTERIOR_NO_INFORMAT = object()


def joc_classificat(rule_set) -> bool:
    """El joc declara la seva provinença?

    Un `GradingRuleSet` amb `origen` NULL no la declara, i les residents que en surten es
    materialitzen com a `MANUAL` (`origen_mgr_des_de_ruleset`). A partir d'aquell moment «el
    que ve del joc» i «el que ha escrit el tècnic» **es diuen igual i són indistingibles**:
    `ModelGradingRule` no guarda de quin joc ve cada fila.
    """
    return bool(rule_set) and (getattr(rule_set, 'origen', None) or '') in _ORIGEN_RS_A_MGR


def poms_manual_a_preservar(model, joc_anterior):
    """Els `pom_id` de les residents `MANUAL` que han de sobreviure al wipe (set, possiblement buit).

    ── DECISIÓ 6.1 (2026-08-06 nit), VERSIÓ MÍNIMA REVERSIBLE ────────────────────────────────
    La regla és **estricta i literal**: es preserva NOMÉS si el joc del qual venien les
    residents estava CLASSIFICAT. Llavors les seves regles porten el seu origen real
    (CANONICAL/CLIENT_RUN/IMPORTED) i una `MANUAL` no en pot venir — o sigui que és autoria.

    ── M1 (Agus, 2026-08-07 matí) · I EL MODEL **SENSE CAP JOC** TAMBÉ PRESERVA ──────────────
    `joc_anterior is None` vol dir «el model no en tenia cap», i llavors una `MANUAL` no pot
    ser còpia: no hi ha joc del qual hagi pogut sortir, i «Sense graduació» —l'únic gest que
    deixa un model sense joc havent-ne tingut— ja esborra TOTES les residents abans. El que
    hi hagi després, doncs, s'ha escrit a mà. Deixava de ser deducció i era política; l'Agus
    l'ha presa amb el cens de 7.2 al davant.

    Tota la resta es comporta com abans de 6.1 i **s'ANOTA** (`motiu_no_preserva`):

      · `no_informat` — el caller no diu de quin joc venien. Els camins que encara no han
        adoptat 6.1 no canvien de comportament.
      · `joc_sense_classificar` — el parany conegut: `origen_mgr_des_de_ruleset` materialitza
        `MANUAL` per als jocs amb `origen` NULL, i llavors autoria i còpia es diuen igual.
        L'extingeix el backfill (`manage.py set_grading_origen`, M2), no un filtre més ample.

    La preservació no és gratuïta: `ModelGradingRule` té `unique_together('model','pom')`, i el
    `bulk_create` de sota no porta conflict-handling. Per això la materialització SALTA les
    regles del joc nou que cauen sobre un POM preservat — si no, el que surt d'aquí no és una
    regla salvada, és un `IntegrityError`.
    """
    if motiu_no_preserva(joc_anterior):
        return set()
    return set(model.grading_rules.filter(origen='MANUAL').values_list('pom_id', flat=True))


def motiu_no_preserva(joc_anterior):
    """Per què aquest wipe NO preserva les `MANUAL`, com a codi curt, o `None` si sí que ho fa.

    Serveix perquè els camins destructius ho puguin deixar escrit (Watchpoint, resposta, log):
    la decisió 6.1 tancava el cas net i en deixava dos d'oberts; M1 (07/08) tanca `sense_joc`
    —un model sense joc preserva—, i queda obert només `joc_sense_classificar`, que no es tanca
    amb un filtre sinó classificant els jocs (M2, `manage.py set_grading_origen`).

    ⚠️ El codi `'sense_joc'` ja NO existeix: `joc_anterior is None` retorna `None` (preserva).
    Qui el busqui a un log vell, era això.
    """
    if joc_anterior is JOC_ANTERIOR_NO_INFORMAT:
        return 'no_informat'
    if joc_anterior is None:
        return None
    if not joc_classificat(joc_anterior):
        return 'joc_sense_classificar'
    return None


def materialize_model_grading_rules(model, source_rules, origen,
                                    joc_anterior=JOC_ANTERIOR_NO_INFORMAT):
    """Materialitza regles de grading residents al model des d'un iterable de
    GradingRule. Wipe-and-recreate: el set resultant és source_rules **més les `MANUAL`
    preservades** (decisió 6.1; v. `poms_manual_a_preservar`).

    NO copia valor_base ni talla_base (viuen a BaseMeasurement / model.base_size_label).
    Idempotent per (model): esborra les regles residents prèvies abans de recrear.
    origen: 'IMPORTED' (W5) | 'CANONICAL' (wizard) | 'MANUAL'.

    `joc_anterior`: el `GradingRuleSet` que el model tenia ABANS d'aquest gest (l'objecte, no
    l'id), o `None` si no en tenia cap. Sense aquest argument el motor esborra tot, com sempre:
    els camins que encara no l'informen no canvien de comportament.
    """
    from fhort.models_app.models import ModelGradingRule
    from fhort.pom.grading_regime import normalitza_logica
    preservats = poms_manual_a_preservar(model, joc_anterior)
    if preservats:
        model.grading_rules.exclude(origen='MANUAL').delete()
    else:
        model.grading_rules.all().delete()
    source_rules = [r for r in source_rules if r.pom_id not in preservats]
    objs = [
        ModelGradingRule(
            model=model, pom_id=r.pom_id,
            # A3 (2026-07-22) — LINEAR+0 sense break s'etiqueta FIXED en sembrar. Aquest camí
            # NO és autoria (no hi ha ningú a qui preguntar i rebutjar trencaria l'import):
            # es normalitza. La conversió és neutra — cap valor graduat canvia.
            logica=normalitza_logica(r.logica, r.increment_base, r.increment,
                                     r.increment_break, r.talla_break_label),
            increment=r.increment, valors_step=r.valors_step,
            increment_base=r.increment_base, increment_break=r.increment_break,
            talla_break_label=r.talla_break_label, talla_break_pos=r.talla_break_pos,
            origen=origen, actiu=True,
        )
        for r in source_rules
    ]
    ModelGradingRule.objects.bulk_create(objs)
    return len(objs)


def materialize_model_grading_rules_from_specs(model, specs, origen,
                                               joc_anterior=JOC_ANTERIOR_NO_INFORMAT):
    """Com materialize_model_grading_rules però des d'SPECS (dicts uniformes de grading_utils),
    no objectes GradingRule. Permet barrejar regles de CONTENIDOR i residents-només-de-model
    (conflictes resolts 'model_resident' / camí sense contenidor) en una sola sembra selectiva.
    Wipe-and-recreate idempotent per (model): el set resultant és `specs` **més les `MANUAL`
    preservades** (decisió 6.1; v. `poms_manual_a_preservar`).
    origen: 'IMPORTED' (W5) | 'CANONICAL' | 'MANUAL'."""
    from fhort.models_app.models import ModelGradingRule
    from fhort.pom.grading_regime import normalitza_logica
    preservats = poms_manual_a_preservar(model, joc_anterior)
    if preservats:
        model.grading_rules.exclude(origen='MANUAL').delete()
    else:
        model.grading_rules.all().delete()
    specs = [s for s in specs if s['pom_id'] not in preservats]
    objs = [
        ModelGradingRule(
            model=model, pom_id=s['pom_id'],
            # A3 — mateixa normalització que materialize_model_grading_rules (vegeu-hi la nota).
            logica=normalitza_logica(s['logica'], s.get('increment_base'), s.get('increment'),
                                     s.get('increment_break'), s.get('talla_break_label')),
            increment=s.get('increment'), valors_step=s.get('valors_step'),
            increment_base=s.get('increment_base'), increment_break=s.get('increment_break'),
            talla_break_label=s.get('talla_break_label'), talla_break_pos=s.get('talla_break_pos'),
            origen=origen, actiu=True,
        )
        for s in specs
    ]
    ModelGradingRule.objects.bulk_create(objs)
    return len(objs)


#: Codi del Watchpoint estructurat de proposta de promoció. El front hi enganxa el render.
PROMOCIO_CODI = 'promocio_poms'

#: Estat per POM dins la proposta. `nomes_model` és l'estat INICIAL de tothom: l'import ja
#: ha desat el POM al model (base + overrides per-talla) i el contenidor no s'ha tocat.
PROMOCIO_NOMES_MODEL = 'nomes_model'
PROMOCIO_PROMOCIONAT = 'promocionat'


def proposta_promocio(cls, container, base_def_id):
    """Els POMs `amplia`/`conflicte` d'un import, com a PROPOSTA accionable (dict o None).

    D1 (Agus 2026-07-22) · **el contenidor de client no s'escriu mai automàticament**. Un
    import que troba POMs que el catàleg no cobreix (`amplia`) o que hi divergeixen
    (`conflicte`) els desa al MODEL —base + overrides per-talla— i proposa promocionar-los
    al catàleg. Promocionar és una decisió humana, per POM.

    Fins ara aquests POMs generaven dos avisos de text lliure que no arribaven enlloc: el
    front descarta `grading_avisos` i cap serialitzador exposa `session.avisos`. La fila
    s'havia desat, però ningú no ho sabia. Això és la pèrdua silenciosa que la decisió D1
    tanca: si no es pot escriure al catàleg, com a mínim s'ha de VEURE que no s'hi ha escrit.

    El spec de cada POM viatja DINS de la proposta a posta: promocionar-lo després no ha de
    dependre que la ImportSession encara existeixi ni de re-derivar res del fitxer. La
    proposta és autosuficient.
    """
    items = []
    for bucket, entrades in (('amplia', cls.get('amplia') or []),
                             ('conflicte', cls.get('conflicte') or [])):
        for e in entrades:
            spec = e['spec_fitxa'] if bucket == 'conflicte' else e
            pom = spec.get('pom')
            items.append({
                'pom_id': spec['pom_id'],
                'pom_codi': getattr(pom, 'codi_client', None) or str(spec['pom_id']),
                'pom_nom': getattr(pom, 'nom_client', '') or '',
                'bucket': bucket,
                'estat': PROMOCIO_NOMES_MODEL,
                'detall': e.get('detall', '') if bucket == 'conflicte' else '',
                # `pom` és una instància de model: fora del JSON.
                'spec': {k: v for k, v in spec.items() if k != 'pom'},
            })
    if not items:
        return None
    return {
        'codi': PROMOCIO_CODI,
        'contenidor_id': container.id,
        'contenidor_nom': container.nom,
        'base_def_id': base_def_id,
        'items': items,
    }


def resum_proposta_promocio(proposta) -> str:
    """Text de reserva del Watchpoint: el que es llegeix si ningú en renderitza les `dades`.

    Un Watchpoint estructurat no pot dependre del seu render per dir alguna cosa: el mateix
    `text` viatja a llistes, exports i historials que no saben res del codi `promocio_poms`.
    """
    items = proposta['items']
    n_amplia = sum(1 for i in items if i['bucket'] == 'amplia')
    n_confl = len(items) - n_amplia
    trossos = []
    if n_amplia:
        trossos.append(f"{n_amplia} POM(s) que el catàleg no té")
    if n_confl:
        trossos.append(f"{n_confl} POM(s) que divergeixen del catàleg")
    return (f"Proposta de promoció al contenidor #{proposta['contenidor_id']} "
            f"'{proposta['contenidor_nom']}': " + " i ".join(trossos) +
            ". Desats NOMÉS al model (base + overrides per-talla); el catàleg del client "
            "NO s'ha tocat. Cal decidir, per POM, si es promocionen al catàleg.")


def afegeix_regles_al_contenidor(container, specs, base_def_id):
    """AMPLIAR (llei del contenidor): afegeix al contenidor les regles de la fitxa per a POMs que
    encara no hi són (o, si ja existeixen, N'ACTUALITZA la forma — cas 'update_catalog'). El
    catàleg d'un contenidor pot ser més ampli que qualsevol model: ampliar no destrueix res.
    Retorna el nombre de regles creades/actualitzades."""
    from fhort.pom.models import GradingRule
    n = 0
    for s in specs:
        GradingRule.objects.update_or_create(
            rule_set=container, pom_id=s['pom_id'],
            defaults=dict(
                talla_base_id=s['talla_base_id'], logica=s['logica'],
                increment=s.get('increment') or 0, valors_step=s.get('valors_step'),
                increment_base=s.get('increment_base'), increment_break=s.get('increment_break'),
                talla_break_label=s.get('talla_break_label'), talla_break_pos=s.get('talla_break_pos'),
                actiu=True,
            ),
        )
        n += 1
    return n
