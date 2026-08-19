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


# ─────────────────────────────────────────────────────────────────────────────
# EL RESOLUTOR INVERS — codi del client → POM
# ─────────────────────────────────────────────────────────────────────────────
#
# `alies_per_pom` va de POM a codi, que és el que necessita PINTAR una taula. Per ESCRIURE cal
# l'altra direcció: donat un customer i un codi, quin POM és ja? La consulta existia —enterrada
# dins de `find_pom_master` (`models_app/extraction_views.py:1030`), l'estratègia (a) del matcher
# d'importació— però no com a funció que ningú més pogués cridar. Per això cap escriptor de POM
# ni de nomenclatura validava col·lisions, i per això l'import va poder crear el POM 440 amb
# `codi_client='U1'` quan BRW ja tenia `U1 → BTN SP Button spacing` (POM 342).
#
# La unicitat de la BD és `(customer, client_code)` i és exacta; aquí es compara amb `iexact`
# perquè la pregunta que fa una persona escrivint a un formulari és «aquest codi ja hi és?», i
# «u1» i «U1» són el mateix codi per a qui el llegeix.


def pom_del_codi(customer_id, codi):
    """El POM que aquest client ja anomena `codi`, o None.

    Només mira àlies amb `pom` informat: un àlies sense POM és vocabulari del client pendent de
    mapar (no vincula res), i deixar que bloquegi un codi seria barrar el pas per una fila que
    encara no diu a què es refereix.
    """
    if not customer_id or not codi:
        return None
    from fhort.pom.models import CustomerPOMAlias

    alias = (CustomerPOMAlias.objects
             .filter(customer_id=customer_id, client_code__iexact=str(codi).strip(),
                     pom__isnull=False)
             .select_related('pom')
             .first())
    return alias.pom if alias else None


def colisio_de_codi(customer_id, codi, excloent_pom_id=None):
    """`(pom, etiqueta)` si el codi ja és d'un ALTRE POM d'aquest client; `(None, None)` si és lliure.

    `excloent_pom_id` és per a l'edició: rebatejar una fila amb el codi que ja tenia no és cap
    col·lisió amb ella mateixa.

    L'etiqueta és el text que ha de llegir la persona —«U1 és BUTTON SPACING al catàleg
    Brownie»—, i es construeix aquí perquè el missatge sigui el mateix vingui d'on vingui la
    validació (crear un POM propi, o el llapis d'identitat).
    """
    pom = pom_del_codi(customer_id, codi)
    if pom is None or (excloent_pom_id is not None and pom.pk == excloent_pom_id):
        return None, None
    nom = (pom.nom_client or getattr(getattr(pom, 'pom_global', None), 'nom_en', '') or
           pom.codi_client or '').strip()
    return pom, nom
