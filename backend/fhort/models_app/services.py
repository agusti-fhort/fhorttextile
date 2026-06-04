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
    """
    from django.db import transaction
    from fhort.models_app.models import ModelSequence

    if n <= 0:
        return (0, -1)  # rang buit (cap fila a importar)

    with transaction.atomic():
        seq, _ = ModelSequence.objects.select_for_update().get_or_create(
            customer=customer, year=year, season=season,
        )
        first = seq.last_seq + 1
        seq.last_seq = seq.last_seq + n
        seq.save(update_fields=['last_seq'])
        last = seq.last_seq
    return (first, last)
