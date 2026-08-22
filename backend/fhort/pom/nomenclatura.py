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


# ─────────────────────────────────────────────────────────────────────────────
# EL RESOLUTOR ÚNIC DE PRESENTACIÓ — codi, noms, abreviatura i categoria d'un POM
# ─────────────────────────────────────────────────────────────────────────────
#
# 🚨 LA LLEI (Agus, 22/08): **ÀLIES DEL CLIENT > TENANT > GLOBAL.**
#
# La nomenclatura PENJA DEL CLIENT. `CustomerPOMAlias` existeix perquè el sistema sàpiga
# posar a un POM la nomenclatura del client que li correspon, no per multiplicar POMs; i el
# catàleg del TENANT és la casa del POM. El catàleg GLOBAL és, com a molt, l'últim recurs:
# un codi cert i estable per a un POM que ningú no ha batejat encara.
#
# 🚨 PER QUÈ CALIA UN PUNT ÚNIC (la sisena ocurrència del mateix patró). Hi havia DUES
# implementacions de la mateixa veritat dient coses CONTRÀRIES sobre la mateixa fila:
#
#     POMMaster.pom_code            (models.py:454)     → `codi_client or global.codi`   TENANT guanya
#     POMMasterSerializer.get_pom_code (serializers.py:97) → `global.codi or codi_client` GLOBAL guanya
#
# I encara pitjor: el MATEIX model ja es contradeia sol —`pom_code` feia guanyar el tenant i
# `name_cat`/`name_en` (models.py:459-467) feien guanyar el global—, o sigui que una mateixa
# fila podia sortir amb el codi de la casa i el nom del catàleg canònic. Això és, literalment,
# el «LOSPOM-548 · FRONT ARMHOLE» que l'Agus va veure a la fitxa on el seu catàleg diu una
# altra cosa.
#
# Aquest bloc no decideix res del domini i no escriu res: només RESOL. Qui té context de
# client li passa l'àlies (`alies_per_pom` de més amunt); qui no en té —el catàleg, que és de
# la casa i no d'un client— el deixa a None i la cadena comença al tenant.
#
# ⚠️ AIXÒ ÉS PRESENTACIÓ, NO CLAU. Els llocs que resolen un POM per CERCAR-LO (l'import,
# `_resolve_pom` del paquet LOSAN, `find_pom_master`) segueixen la llei de resolució que
# tenen: `pom_global.codi` hi és una clau natural, no una etiqueta per pintar. Aquests no
# passen per aquí a posta.


def _net(v):
    return (str(v).strip() if v is not None else '')


def _global(pom):
    """El POMGlobal del POM, o None. Mai dispara query si el FK és nul."""
    return pom.pom_global if getattr(pom, 'pom_global_id', None) else None


def codi_de(pom, alias=None):
    """EL CODI VISIBLE d'un POM: àlies del client > codi del tenant > codi global.

    `alias` accepta el `client_code` cru (str) o el diccionari que serveix `alies_per_pom`.
    Buit a tot arreu → cadena buida (la columna no pot mentir dient un codi que no existeix).
    """
    if pom is None:
        return ''
    pg = _global(pom)
    return (_net(_alias_code(alias))
            or _net(pom.codi_client)
            or _net(pg.codi if pg else ''))


def abreviatura_de(pom, alias=None):
    """LA NOMENCLATURA CURTA, mateixa llei: àlies > codi del tenant > abreviatura global.

    És el mateix concepte que `codi_de` vist per una columna estreta; l'abreviatura del
    catàleg global («FR AH») és de la CASA GLOBAL i per tant va l'última.
    """
    if pom is None:
        return ''
    pg = _global(pom)
    return (_net(_alias_code(alias))
            or _net(pom.codi_client)
            or _net(pg.abbreviation if pg else ''))


def noms_de(pom, alias=None):
    """`{'nom_en', 'nom_ca'}` — els dos noms llargs, amb la MATEIXA llei que el codi.

    · `nom_en`: descripció EN de l'àlies > `nom_client` del tenant > `nom_en` global.
    · `nom_ca`: descripció LOCAL de l'àlies > `nom_client` del tenant > `nom_ca` global.

    Que els dos caiguin al mateix `nom_client` quan el tenant té un sol nom NO és un defecte:
    el catàleg del tenant bateja una vegada, i qui pinta ja sap que una segona línia que
    repeteix la primera és soroll (ho resol `nomsDePom` al front).
    """
    if pom is None:
        return {'nom_en': '', 'nom_ca': ''}
    pg = _global(pom)
    a = alias if isinstance(alias, dict) else None
    propi = _net(pom.nom_client)
    return {
        'nom_en': (_net(a.get('client_name_en') if a else '') or propi
                   or _net(pg.nom_en if pg else '')),
        'nom_ca': (_net(a.get('client_name_local') if a else '') or propi
                   or _net(pg.nom_ca if pg else '')),
    }


def categoria_de(pom):
    """El nom de la CATEGORIA visible: la del tenant (`POMCategory`) > el text del global.

    Mateixa llei i mateix motiu: `POMGlobal.categoria` és text lliure d'un altre vocabulari
    («TORS», «Upper body») i no és la família que la casa ha declarat.
    """
    if pom is None:
        return ''
    cat = pom.categoria if getattr(pom, 'categoria_id', None) else None
    if cat is not None:
        return _net(cat.nom_ca or cat.nom_en)
    pg = _global(pom)
    return _net(pg.categoria if pg else '')


def _alias_code(alias):
    if isinstance(alias, dict):
        return alias.get('client_code') or ''
    return alias or ''

