"""Nomenclatura de CLIENT d'un POM (CustomerPOMAlias) — resolutor únic de presentació.

El catàleg anomena una mesura com l'anomena la casa (`POM.codi_client` / `nom_client`, i el
canònic del sector a `POMMaster`); el CLIENT del model l'anomena com vol (Brownie diu "A" on
la casa diu "CH"). Quan es treballa un model d'un client, la nomenclatura que ha de manar a
la pantalla és la del client: és la que hi ha als seus documents i la que el tècnic diu.

Aquest mòdul NO decideix res del domini ni escriu res: només resol, amb UNA consulta, quin
àlies correspon a cada POM per al customer d'un model. Viu fora de `pom/services.py` a
propòsit — allà hi ha el motor de graduació, i això és presentació.

Regla de tria (la mateixa que ja feia `base_measurements_view` en línia, ara compartida): un
client pot tenir DIVERSOS codis per al mateix POM —la unicitat és (customer, client_code), no
(customer, pom)—, així que s'ordena per `pendent_revisio` i `client_code` i es queda el
primer. Determinista i estable entre crides.
"""

CAMPS = ('client_code', 'client_name_en', 'client_name_local')


def alies_per_pom(customer_id):
    """{pom_id: {client_code, client_name_en, client_name_local}} del customer donat.

    Customer buit → {} (un model sense client no té nomenclatura de client). Els àlies sense
    `pom` són vocabulari del client encara pendent de mapar: no vinculen res i no hi entren.
    """
    if not customer_id:
        return {}
    from fhort.pom.models import CustomerPOMAlias

    out = {}
    for pom_id, codi, en, local in CustomerPOMAlias.objects.filter(
        customer_id=customer_id, pom__isnull=False
    ).order_by('pendent_revisio', 'client_code').values_list(
        'pom_id', 'client_code', 'description_en', 'description_local'
    ):
        out.setdefault(pom_id, {
            'client_code': codi,
            'client_name_en': en or '',
            'client_name_local': local or '',
        })
    return out


def camps_de(alias_by_pom, pom_id):
    """Els tres camps per a una fila de resposta; buits si el POM no té àlies del client.

    Sempre les MATEIXES claus, hi hagi àlies o no: el consumidor no ha de distingir entre
    "no n'hi ha" i "l'endpoint no ho serveix" (la presentació ja fa el fallback al catàleg).
    """
    a = (alias_by_pom or {}).get(pom_id)
    return {c: (a[c] if a else '') for c in CAMPS}
