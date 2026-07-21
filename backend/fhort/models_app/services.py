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
    """L'últim seqüencial que hi ha AL TERRENY (el que sigui que l'hagi escrit)."""
    from django.db.models import Max
    from fhort.models_app.models import Model
    return Model.objects.filter(
        customer=customer, any=year, temporada=season,
    ).aggregate(m=Max('sequencial'))['m'] or 0


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


def materialize_model_grading_rules(model, source_rules, origen):
    """Materialitza regles de grading residents al model des d'un iterable de
    GradingRule. Wipe-and-recreate: el set resultant és EXACTAMENT source_rules.

    NO copia valor_base ni talla_base (viuen a BaseMeasurement / model.base_size_label).
    Idempotent per (model): esborra les regles residents prèvies abans de recrear.
    origen: 'IMPORTED' (W5) | 'CANONICAL' (wizard) | 'MANUAL'.
    """
    from fhort.models_app.models import ModelGradingRule
    model.grading_rules.all().delete()
    objs = [
        ModelGradingRule(
            model=model, pom_id=r.pom_id,
            logica=r.logica, increment=r.increment, valors_step=r.valors_step,
            increment_base=r.increment_base, increment_break=r.increment_break,
            talla_break_label=r.talla_break_label, talla_break_pos=r.talla_break_pos,
            origen=origen, actiu=True,
        )
        for r in source_rules
    ]
    ModelGradingRule.objects.bulk_create(objs)
    return len(objs)


def materialize_model_grading_rules_from_specs(model, specs, origen):
    """Com materialize_model_grading_rules però des d'SPECS (dicts uniformes de grading_utils),
    no objectes GradingRule. Permet barrejar regles de CONTENIDOR i residents-només-de-model
    (conflictes resolts 'model_resident' / camí sense contenidor) en una sola sembra selectiva.
    Wipe-and-recreate idempotent per (model): el set resultant és EXACTAMENT `specs`.
    origen: 'IMPORTED' (W5) | 'CANONICAL' | 'MANUAL'."""
    from fhort.models_app.models import ModelGradingRule
    model.grading_rules.all().delete()
    objs = [
        ModelGradingRule(
            model=model, pom_id=s['pom_id'],
            logica=s['logica'], increment=s.get('increment'), valors_step=s.get('valors_step'),
            increment_base=s.get('increment_base'), increment_break=s.get('increment_break'),
            talla_break_label=s.get('talla_break_label'), talla_break_pos=s.get('talla_break_pos'),
            origen=origen, actiu=True,
        )
        for s in specs
    ]
    ModelGradingRule.objects.bulk_create(objs)
    return len(objs)


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
