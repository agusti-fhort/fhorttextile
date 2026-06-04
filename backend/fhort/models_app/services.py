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
