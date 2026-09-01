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


def alies_del_codi(customer_id, codi):
    """L'ÀLIES que aquest client ja anomena `codi`, o None. La consulta, sencera.

    🚨 EXISTEIX PERQUÈ `pom_del_codi` LLENÇAVA LA FILA. Aquella funció feia exactament aquesta
    consulta —amb `select_related('pom')` i tot— i en tornava només `alias.pom`, o sigui que
    tot el que el sistema sap del conflicte moria en un `return`: de quin diccionari ve el codi,
    si està pendent de revisió, amb quina caixa el va escriure el client, quan es va editar.
    Un refús que no pot dir res d'això només pot dir «no», i la persona no té més sortida que
    tornar-hi (tres reintents en viu a la formació del 26/08).

    Només mira àlies amb `pom` informat: un àlies sense POM és vocabulari del client pendent de
    mapar (no vincula res), i deixar que bloquegi un codi seria barrar el pas per una fila que
    encara no diu a què es refereix.

    `pom__pom_global` perquè qui rep l'àlies en voldrà el NOM RESOLT (`noms_de`), i sense el
    prefetch cada col·lisió compraria una query.
    """
    if not customer_id or not codi:
        return None
    from fhort.pom.models import CustomerPOMAlias

    return (CustomerPOMAlias.objects
            .filter(customer_id=customer_id, client_code__iexact=str(codi).strip(),
                    pom__isnull=False)
            .select_related('pom', 'pom__pom_global')
            .first())


def pom_del_codi(customer_id, codi):
    """El POM que aquest client ja anomena `codi`, o None.

    Es queda com la porta curta per a qui només vol saber SI el codi és lliure; qui hagi
    d'explicar el conflicte va per `alies_del_codi`, que és el mateix viatge a la BD.
    """
    alias = alies_del_codi(customer_id, codi)
    return alias.pom if alias else None


def colisio_de_codi(customer_id, codi, excloent_pom_id=None):
    """`(pom, etiqueta, context)` si el codi ja és d'un ALTRE POM d'aquest client.

    `(None, None, None)` si és lliure. `excloent_pom_id` és per a l'edició: rebatejar una fila
    amb el codi que ja tenia no és cap col·lisió amb ella mateixa.

    L'etiqueta és el text que ha de llegir la persona —«U1 és BUTTON SPACING al catàleg
    Brownie»—, i es construeix aquí perquè el missatge sigui el mateix vingui d'on vingui la
    validació (crear un POM propi, o el llapis d'identitat).

    🚨 L'ETIQUETA ES RESOL, NO ES LLEGEIX CRUA. Començava per `pom.nom_client`, i aquell camp
    és buit a **103 dels 144 POMs actius** de `fhort` (mesurat el 26/08): la cadena tenia un
    fallback al global i se salvava per poc, però als **7 POMs sense cap nom enlloc** queia a
    `codi_client` i el refús es llegia «**BT** ja és **BT** al catàleg d'aquest client» — una
    tautologia. Ara passa per `noms_de`, que és el resolutor únic de la llei
    ÀLIES > TENANT > GLOBAL, i el codi hi queda com a últim recurs de debò.

    ⚠️ LA SIGNATURA TÉ TRES ELEMENTS I NO DOS, i els dos cridadors s'han tocat alhora a posta:
    és justament el que fa que el missatge del refús sigui UN DE SOL vingui d'on vingui.
    """
    alias = alies_del_codi(customer_id, codi)
    pom = alias.pom if alias else None
    if pom is None or (excloent_pom_id is not None and pom.pk == excloent_pom_id):
        return None, None, None
    noms = noms_de(pom)
    nom = (noms['nom_en'] or noms['nom_ca'] or pom.codi_client or '').strip()
    return pom, nom, _context_de_alias(alias, pom, nom)


#: Com es diu cada origen d'àlies a una persona. Viu aquí i no a la vista perquè el refús ha de
#: sonar igual a totes les portes; `CustomerPOMAlias.ORIGEN_CHOICES` en té els codis.
ORIGEN_LLEGIBLE = {
    'DICCIONARI': 'del diccionari del client',
    'IMPORT': "d'una importació anterior",
    'MANUAL': 'creat a mà',
    'MIGRACIO': "d'una migració",
    'MODEL': "nascut d'un model",
}


def nom_client(customer_id):
    """El nom del client, per posar-lo a la frase del refús («…del diccionari del client BRW»).

    Una consulta de `values_list` i prou, i mai una excepció: si el client no es pot llegir
    —la FK creua schemes i va sense constraint de BD—, la frase es queda sense el nom i segueix
    dient tot el que importa. Un refús no pot petar per una etiqueta.
    """
    if not customer_id:
        return ''
    try:
        from fhort.tasks.models import Customer
        return Customer.objects.filter(pk=customer_id).values_list('nom', flat=True).first() or ''
    except Exception:
        return ''


def frase_de_colisio(codi, context, client=''):
    """LA FRASE DEL REFÚS, una i la mateixa a totes les portes.

    «BT ja és Leg opening girth (BT) del diccionari del client BRW, pendent de revisió. Fes-lo
    servir des del cercador, revisa'l al catàleg, o dona-li una nomenclatura diferent.»

    🚨 PER QUÈ VIU AQUÍ I NO A LA VISTA. Hi ha DUES portes que refusen per aquest motiu —
    `gravar_pom_view` (400) i `create_model_pom_view` (409)— i fins ara cadascuna es redactava
    la seva: la del 409 ja deia una sortida («Fes-lo servir des del cercador, o dona-li una
    nomenclatura diferent») i la del 400 només deia el xoc. La persona ha de llegir el mateix
    vingui d'on vingui, i el dia que la frase millori ha de millorar a totes dues alhora.

    ⚠️ **DIU AMB QUÈ XOCA I QUÈ POT FER**, que és la doctrina que `create_model_pom_view` ja
    tenia escrita al seu comentari: «la sortida no és inventar un codi: és DIR AMB QUÈ XOCA
    (…) el que necessita no és un codi nou, és que li ensenyin l'existent».
    """
    if not context:
        return f'«{codi}» ja és al catàleg d\'aquest client.'
    qui = context['pom_nom'] or context['pom_codi'] or ''
    # El codi de la casa al costat del nom quan són coses diferents: qui ha d'anar a buscar-lo
    # al cercador el buscarà per aquell, no pel del client.
    if context['pom_codi'] and context['pom_codi'] != context['client_code']:
        qui = f'{qui} ({context["pom_codi"]})' if qui else context['pom_codi']
    on = context['origen_llegible']
    if client:
        on = f'{on} {client}'
    pendent = ', pendent de revisió' if context['pendent_revisio'] else ''
    # Les sortides: la que revisa només s'ofereix si hi ha res a revisar.
    sortides = ['Fes-lo servir des del cercador']
    if context['pendent_revisio']:
        sortides.append('revisa\'l al catàleg')
    sortides.append('o dona-li una nomenclatura diferent')
    return (f'«{context["client_code"]}» ja és {qui} {on}{pendent}. '
            f'{", ".join(sortides)}.')


def _context_de_alias(alias, pom, nom):
    """Tot el que el sistema sap del conflicte, en una forma que una resposta pot servir.

    Això ja era a la mà i es llençava. No hi ha cap consulta nova: `alies_del_codi` porta
    l'àlies sencer i el seu POM amb el global prefetchat.
    """
    return {
        # El codi TAL COM el client l'escriu: la comparació és `iexact` (i la unique de
        # `POMMaster` és `upper(codi_client)`), o sigui que qui ha escrit «bt» ha de veure que
        # el que ja hi ha es diu «BT». Sense això el refús sembla que no parli del que s'ha fet.
        'client_code': alias.client_code,
        'pom_id': pom.pk,
        'pom_codi': pom.codi_client,
        'pom_nom': nom,
        'origen': alias.origen,
        'origen_llegible': ORIGEN_LLEGIBLE.get(alias.origen, alias.origen),
        # El cas de PROD: un àlies de DICCIONARI encara pendent de revisar. Qui ho llegeix ha de
        # saber que el codi el reserva una fila que ENCARA no ha validat ningú — és el que fa
        # que «revisa'l» sigui una sortida i no una endevinalla.
        'pendent_revisio': bool(alias.pendent_revisio),
        'es_instancia': bool(alias.es_instancia),
        'description_en': alias.description_en or '',
        'description_local': alias.description_local or '',
        'editat_at': alias.editat_at.isoformat() if alias.editat_at else None,
    }


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
    · `nom_es`: **NOMÉS el global** — el tenant no té camp de castellà i l'àlies només en té un
      de «local» sense declarar de quina llengua és. Inventar-li una regla seria endevinar de
      quina llengua parla `description_local`; el que hi ha és el castellà del CATÀLEG, i quan
      el POM no està lligat, no n'hi ha. (Sembra v5, 23/08: el catàleg v5 en porta 165.)

    Que els dos caiguin al mateix `nom_client` quan el tenant té un sol nom NO és un defecte:
    el catàleg del tenant bateja una vegada, i qui pinta ja sap que una segona línia que
    repeteix la primera és soroll (ho resol `nomsDePom` al front).
    """
    if pom is None:
        return {'nom_en': '', 'nom_ca': '', 'nom_es': ''}
    pg = _global(pom)
    a = alias if isinstance(alias, dict) else None
    propi = _net(pom.nom_client)
    return {
        'nom_en': (_net(a.get('client_name_en') if a else '') or propi
                   or _net(pg.nom_en if pg else '')),
        'nom_ca': (_net(a.get('client_name_local') if a else '') or propi
                   or _net(pg.nom_ca if pg else '')),
        # `getattr` i no `pg.nom_es`: aquest lector rep objectes duck-typed (stubs de banc,
        # DTOs de paquet) i un camp NOU de la regla no pot fer petar qui encara no el porta.
        # És la llei de la casa des del 21/08 —un camp nou vol `getattr` als lectors genèrics—
        # i aquí ja hi havia dos bancs amb un `_Global` sense `nom_es`.
        'nom_es': _net(getattr(pg, 'nom_es', '') if pg else ''),
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


# ─────────────────────────────────────────────────────────────────────────────
# EL «COM ES MESURA» — cascada TENANT > GLOBAL
# ─────────────────────────────────────────────────────────────────────────────
#
# Els nou camps que descriuen com es pren una mesura (`unitat` i el bloc «des d'on · fins on ·
# referència · scope · orientació · estat · línia · secció») només vivien a `POMGlobal`. Des
# del 22/08 també viuen al tenant, buits per defecte, i la llei és la mateixa que la del nom:
# **el que el tenant ha informat mana; el global és el pla B.**
#
# Buit al tenant NO vol dir «no hi ha»: vol dir «no informat aquí», i per això cau al global
# en comptes de tapar-lo. Qui pinta segueix podent distingir els tres estats —dada / lligat
# sense informar / no lligat— perquè el POM segueix dient si té `pom_global` o no.

COM_ES_MESURA = ('unitat', 'start_point', 'end_point', 'reference_point',
                 'scope', 'orientation', 'state', 'line', 'body_section')


def com_es_mesura_de(pom):
    """`{camp: valor}` dels nou camps, amb el tenant al davant i el global de reserva."""
    if pom is None:
        return {c: '' for c in COM_ES_MESURA}
    pg = _global(pom)
    return {c: (_net(getattr(pom, c, '')) or _net(getattr(pg, c, '') if pg else ''))
            for c in COM_ES_MESURA}


# ─────────────────────────────────────────────────────────────────────────────
# LA SEPARACIÓ — copy-on-write (decisió d'Agus, 22/08)
# ─────────────────────────────────────────────────────────────────────────────
#
# 🚨 «EL POM SE SEPARA I PASSA A SER MEU.» En editar qualsevol camp PROPI d'un POM lligat al
# catàleg global, el POM deixa de dependre'n: `pom_global → NULL`. És la mateixa llei que el
# model que reescriu una regla sembrada —qui toca una dada n'assumeix la propietat— i té el
# mateix motiu: el catàleg global el comparteixen tots els tenants i **no es toca mai**.
#
# 🔑 I ÉS COPY-ON-WRITE, NO UN TALL. Separar-se no pot voler dir perdre informació: abans de
# desfer el lligam, tot el que el POM ENSENYAVA gràcies al global es COPIA al tenant —el nom,
# l'abreviatura si no en tenia codi propi, i els nou camps del «com es mesura»—. Un POM separat
# ha de seguir dient exactament el mateix que deia el segon abans; el que canvia és de qui és.
#
# La marca (`separat_de_global` + `separat_at`) és el que permet als importadors distingir
# aquest POM d'un que mai no ha estat lligat, i per tant no tornar-li a enganxar el global.


def separa_del_global(pom, *, quan=None):
    """Separa `pom` del catàleg global copiant-hi el que en penjava. NO desa.

    Retorna la llista de camps que ha tocat (buida si el POM ja era del tenant), perquè qui
    crida pugui incloure'ls al seu `update_fields` i el desat segueixi sent acotat.

    No fa `save()` a posta: la separació és part de l'escriptura que la provoca i ha d'entrar
    a la MATEIXA transacció, mai en una de pròpia que pugui quedar orfe si l'altra falla.
    """
    if pom is None or not getattr(pom, 'pom_global_id', None):
        return []
    from django.utils import timezone

    pg = pom.pom_global
    tocats = []

    def _posa(camp, valor):
        valor = _net(valor)
        if valor and not _net(getattr(pom, camp, '')):
            setattr(pom, camp, valor)
            tocats.append(camp)

    # El NOM de la casa: si el tenant no en tenia, hereta el CANÒNIC (mai el deixa mut).
    #
    # 🔒 I NOMÉS EL CANÒNIC. `POMGlobal` té dos noms (`nom_en` + `nom_ca`) i `POMMaster` en té
    # UN: és la decisió d'Agus del 09/08, vigent — *la traducció de vocabulari de domini NO viu
    # a la BD*, i `nom_ca`/`nom_es` a `POMMaster` hi estan explícitament descartats. El nom
    # local no es perd en separar-se: CANVIA DE FONT, i passa a `TranslationCache`
    # (`/api/v1/translate/pom/`), que és on la casa ha decidit que viu. Afegir aquí un camp
    # «per no perdre'l» seria desfer aquella decisió de passada.
    _posa('nom_client', pg.nom_en or pg.nom_ca)
    # El CODI: si el tenant no en tenia, hereta l'abreviatura del global i, si no n'hi ha, el
    # codi canònic. Que la columna no surti mai buida és una promesa d'aquest producte.
    _posa('codi_client', pg.abbreviation or pg.codi)
    for camp in COM_ES_MESURA:
        _posa(camp, getattr(pg, camp, ''))

    pom.separat_de_global = pg.codi
    pom.separat_at = quan or timezone.now()
    pom.pom_global = None
    tocats += ['separat_de_global', 'separat_at', 'pom_global']
    return tocats


#: Els camps que, en canviar, fan que un POM lligat es SEPARI. Són els que descriuen el POM
#: en si —què és i com es mesura—, no els que descriuen la seva vida al tenant.
#:
#: `actiu`, `notes`, `pendent_revisio`, `origen_import` i les toleràncies per defecte NO hi
#: són a posta: desactivar un POM del catàleg o anotar-hi una nota és administrar-lo, no
#: redefinir-lo, i separar-lo per això obligaria a triar entre arxivar-lo i mantenir-lo lligat.
CAMPS_QUE_SEPAREN = ('codi_client', 'nom_client', 'categoria') + COM_ES_MESURA


# ─────────────────────────────────────────────────────────────────────────────
# LA COL·LISIÓ DE NOMENCLATURA DINS D'UN MODEL (Decisió 7, 2026-08-28)
# ─────────────────────────────────────────────────────────────────────────────
#
# `colisio_de_codi` (a dalt) vigila el catàleg del CLIENT: que dos POMs d'un mateix client no
# es diguin igual. Això és un nivell amunt i NO serveix aquí. El que la Decisió 7 demana és el
# nivell de sota: que dues FILES DEL MATEIX MODEL no comparteixin `nom_fitxa`.
#
# 🚨 I NO ÉS UNA PRECAUCIÓ TEÒRICA: la fitxa tècnica JA HO ASSUMEIX. El lligam fletxa↔fila del
# `TechSheetEditor` es resol pel TEXT de la nomenclatura i ho diu al seu comentari —«és exacte
# per al cas real (els nom_fitxa són curts i únics dins un model)»—. Fins avui el valor el
# sembrava l'import, i un document de client rarament repeteix codi; a partir d'ara el sembra
# una persona. El supòsit passa de «cert per costum» a «cert perquè es comprova».
#
# ── L'ÀMBIT ÉS model + garment + capa, i no és la clau de fila sencera ───────────
# La clau de fila és `(model, pom, capa, instancia, garment)`. L'àmbit d'unicitat en deixa
# fora DOS eixos, i cadascun per un motiu diferent:
#   · `pom` — òbviament: si hi entrés, la comprovació no compararia res (una fila només xoca
#     amb ella mateixa). El sentit de la llei és justament que DOS POMs diferents no es puguin
#     dir igual dins de la mateixa peça.
#   · `instancia` — a posta: dues instàncies del mateix POM a la mateixa peça i capa (la sisa
#     dreta i l'esquerra) SÓN el cas que ha de tenir nomenclatures diferents. Deixar-la fora
#     de l'àmbit és el que fa que 'AH' i 'AH' a dues instàncies germanes es refusi, que és el
#     que la comporta `instancia_exigeix_nom` (migració 0074) ja intentava assegurar demanant
#     que en tinguessin una.
#
# Viu aquí i no a la vista pel mateix argument que `frase_de_colisio`: el refús ha de sonar
# igual vingui d'on vingui, i el dia que millori ha de millorar a totes les portes alhora.

def colisio_de_nomenclatura(bm, codi):
    """`(fila, etiqueta, context)` si `codi` ja el porta una ALTRA fila del mateix àmbit.

    `(None, None, None)` si és lliure, si el codi és buit (treure el bateig no xoca mai amb
    ningú) o si la fila que el porta és la mateixa que s'està editant.

    `bm` és la `BaseMeasurement` que s'edita: d'ella surt l'àmbit (model + garment + capa) i
    l'exclusió d'ella mateixa. No es fa cap consulta si el codi ve buit.
    """
    codi = _net(codi)
    if not codi or bm is None:
        return None, None, None
    from fhort.models_app.models import BaseMeasurement

    germana = (BaseMeasurement.objects
               .filter(model_id=bm.model_id, garment=bm.garment or '', capa=bm.capa or '',
                       nom_fitxa__iexact=codi)
               .exclude(pk=bm.pk)
               .select_related('pom', 'pom__pom_global')
               .order_by('ordre', 'pk')
               .first())
    if germana is None:
        return None, None, None

    noms = noms_de(germana.pom)
    nom = (germana.nom_canonic_model or germana.nom_traduit_model
           or noms['nom_en'] or noms['nom_ca'] or '').strip()
    context = {
        'nom_fitxa': germana.nom_fitxa,
        'fila_id': germana.pk,
        'pom_nom': nom,
        'pom_codi': codi_de(germana.pom),
        'instancia': germana.instancia or '',
        'garment': germana.garment or '',
    }
    return germana, nom, context


def frase_de_colisio_nomenclatura(codi, context):
    """LA FRASE DEL REFÚS d'unicitat dins del model, una i la mateixa a totes les portes.

    ««AH» ja és la nomenclatura de Armhole girth (AH) en aquesta peça. Dona-li una
    nomenclatura diferent, o canvia la d'aquella fila.»

    ⚠️ Mateixa doctrina que `frase_de_colisio`: **diu amb què xoca i què pot fer**. No proposa
    cap codi — la sortida no és inventar-ne un, és ensenyar el que ja hi és perquè qui edita
    decideixi quin dels dos ha de canviar.
    """
    if not context:
        return f'«{codi}» ja és la nomenclatura d\'una altra fila d\'aquest model.'
    qui = context['pom_nom'] or context['pom_codi'] or ''
    if context['pom_codi'] and context['pom_codi'] != context['nom_fitxa'] and qui:
        qui = f'{qui} ({context["pom_codi"]})'
    if context['instancia']:
        qui = f'{qui} · {context["instancia"]}' if qui else context['instancia']
    on = 'en aquesta peça' if context['garment'] else 'en aquest model'
    return (f'«{context["nom_fitxa"]}» ja és la nomenclatura de {qui} {on}. '
            f'Dona-li una nomenclatura diferent, o canvia la d\'aquella fila.')


# ─────────────────────────────────────────────────────────────────────────────
# L'HOMONÍMIA DINS D'UN MATEIX DESAT — AVÍS, NO REFÚS (Agus, Decisió 8)
# ─────────────────────────────────────────────────────────────────────────────
#
# 🚨 PER QUÈ AQUESTA FUNCIÓ NO ÉS UNA GERMANA DE `colisio_de_codi`, I LA DIFERÈNCIA ÉS LA LLEI.
#
# `colisio_de_codi` pregunta «aquest codi ja és d'un altre POM al catàleg DEL CLIENT?» — abast
# CUSTOMER, i és la pregunta que protegeix la `UNIQUE (customer, client_code)` de la BD quan
# algú dona d'alta un POM propi. Aquella pregunta segueix viva a `create_model_pom_view`, que
# és on realment neix una fila d'aquella taula.
#
# Aplicada a `gravar_pom_view` era una pregunta ALIENA: desar la taula de mesures d'un model no
# escriu cap `CustomerPOMAlias`, i tanmateix el refús barrava el pas per una col·lisió amb un
# ALTRE MODEL del mateix client. Efecte mesurat (M1194): un model verge de BRW no es podia
# gravar perquè algú, en un altre model, ja havia anomenat «B» i «SF» — i com que la pantalla
# no oferia cap manera de reanomenar, l'única acció disponible era tornar-hi.
#
# La llei diu: **entre models, lliure. Dins del model, avís.** Un mateix nom de fitxa a dues
# files de la MATEIXA peça, capa i instància, apuntant a POMs DIFERENTS, és ambigu a la fitxa
# impresa —dues línies que es diuen igual i mesuren coses diferents— però no és cap dada
# impossible: es desa, i qui la llegeix decideix. Un avís que bloqueja és un refús amb bones
# maneres, i el que la formació del 26/08 va ensenyar és que un refús sense sortida no és una
# barana: és un mur.
#
# ⚠️ L'ÀMBIT ES MIRA CRU I SENCER. La clau és `(garment, capa, instancia, nom_fitxa)` — els
# QUATRE—, i ve de la mateixa normalització que farà servir l'escriptura (`_identitat_de_mesura`
# al costat del cridador). Comparar per menys camps —o barrejar files normalitzades amb files
# crues— és la família de defectes que aquest sprint ha anat tancant per l'altra banda: el que
# no comparteix àmbit no és homònim, i el que el comparteix ha de caure al mateix cistell.
#
# La comparació del nom va en `casefold` pel mateix motiu que `alies_del_codi` fa `iexact`: qui
# llegeix la fitxa no distingeix «AH» de «ah», i dues línies que es llegeixen igual són el cas
# que l'avís existeix per ensenyar.

def avisos_de_nomenclatura(files):
    """Els avisos d'homonímia d'un desat, sense refusar-ne cap ni tocar la BD.

    `files` és un iterable de dicts amb `ref` (com anomenar la fila a la resposta: la posició
    dins del payload), `pom_id` i els quatre camps de l'àmbit ja normalitzats — `garment`,
    `capa`, `instancia`, `nom_fitxa`.

    Torna una llista d'avisos, un per àmbit que en tingui: mateix `(garment, capa, instancia,
    nom_fitxa)` amb **dos `pom_id` o més**. Repetir el mateix POM no és homonímia (i el guard de
    duplicats de la porta ja el refusa per un altre motiu: dues escriptures a la mateixa fila).

    Sense nom de fitxa no hi ha res a comparar: les files sense bateig no entren mai.

    L'ordre de sortida és el de la PRIMERA fila de cada grup, i els `poms`/`files` van en l'ordre
    en què han arribat: la resposta ha de poder-se llegir al costat de la taula que s'ha desat.
    """
    grups = {}
    for f in files or []:
        nom = _net(f.get('nom_fitxa'))
        if not nom:
            continue
        clau = (f.get('garment') or '', f.get('capa') or '', f.get('instancia') or '',
                nom.casefold())
        g = grups.get(clau)
        if g is None:
            g = grups[clau] = {
                'garment': f.get('garment') or '',
                'capa': f.get('capa') or '',
                'instancia': f.get('instancia') or '',
                # El literal de la PRIMERA fila: és el que la persona ha escrit i el que veurà.
                'nom_fitxa': nom,
                'poms': [],
                'files': [],
            }
        pom_id = f.get('pom_id')
        if pom_id is not None and pom_id not in g['poms']:
            g['poms'].append(pom_id)
        g['files'].append(f.get('ref'))
    return [g for g in grups.values() if len(g['poms']) > 1]
