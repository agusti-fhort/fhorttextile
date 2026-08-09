"""El traspàs Brand→Studio, com a SERVEI. Font única de la federació v2 (P8).

Aquesta lògica va néixer dins de `instantiate_external_models` i era només seva. P8 li dona
una segona boca (l'endpoint `/api/v1/encarrecs/traspassar/`), i dues boques sobre la mateixa
llei és exactament com neixen les divergències: un guard que s'arregla en un camí i no en
l'altre, un informe que compta diferent. Per això el command passa a ser un embolcall prim
que formata el que aquest mòdul retorna, i l'endpoint en fa la versió JSON. **Cap regla de
domini viu ja al command.**

LES DUES CLAUS (no re-obrir): el `TenantLink` ACTIU autoritza el PONT; `Model.studio_assignat`
autoritza CADA MODEL. Cap de les dues sola mou res.

DISCIPLINA CROSS-SCHEMA: el Brand es llegeix com a DICTS dins de `schema_context` i se surt
del context amb la llista tancada — mai un objecte ORM viu (Bandera 3 de la diagnosi de
federació). Un objecte ORM que sobreviu al context arrossega la seva connexió i el seu
`_state.db`, i la següent consulta que en pengi (una FK peresosa, un `refresh_from_db`) es
resol contra l'schema equivocat sense dir res.

L'ERROR ÉS DE DOMINI, NO DE TRANSPORT: aquí es llança `FederacioError`, que no sap res de
`CommandError` ni de codis HTTP. Cada boca el tradueix a la seva llengua.
"""
import logging
import os

from django.db import connection, transaction
from django.utils import timezone
from django_tenants.utils import schema_context

from .models import Client, TenantLink

logger = logging.getLogger(__name__)


class FederacioError(Exception):
    """Violació d'una regla de la federació. `codi` és el discriminant estable (patró DA-30):
    el frontend i els tests hi enganxen, mai al text del missatge."""

    def __init__(self, missatge, codi='federacio_error'):
        super().__init__(missatge)
        self.codi = codi


# Camps de configuració que viatgen resolts per CLAU NATURAL contra el catàleg del Studio.
# Els no-aparellats NO bloquegen el traspàs: el model neix amb el camp a NULL i l'informe ho diu.
CONFIG_KEYS = ('garment_type_item', 'size_system', 'grading_rule_set')


def resol_vincle(brand_codi, studio_codi, exigeix_actiu=True):
    """El pont entre les dues parts. Sense vincle no hi ha federació; aturat, no hi ha pas."""
    link = TenantLink.objects.filter(
        brand_codi_tenant=brand_codi, studio_codi_tenant=studio_codi).first()
    if link is None:
        raise FederacioError(
            f'No hi ha cap vincle entre brand={brand_codi} i studio={studio_codi}.',
            'link_missing')
    if exigeix_actiu and not link.es_viu():
        raise FederacioError(
            f'El vincle {brand_codi}↔{studio_codi} no és ACTIU (estat={link.estat}). '
            f'El pont està tancat.', 'link_not_active')
    return link


def resol_schema(codi_tenant, rol):
    client = Client.objects.filter(codi_tenant=codi_tenant).first()
    if client is None:
        raise FederacioError(f"No existeix cap tenant amb codi_tenant='{codi_tenant}' ({rol}).",
                             'tenant_missing')
    return client


def llegeix_models_del_brand(brand_schema, studio_codi, limit=None, codis=None):
    """Els models que el Brand ha ASSIGNAT a aquest Studio, com a dicts tancats.

    `codis` acota a un subconjunt explícit (el que demana la safata quan l'usuari en tria
    uns quants); sense `codis`, són tots els assignats. Torna (total_brand, n_assignats, rows).
    Els dos primers números són l'informe honest: N models existeixen al Brand, M estan
    assignats, i només aquests M viatgen — la diferència no és un error, és la llei.
    """
    from fhort.models_app.models import Model

    rows = []
    with schema_context(brand_schema):
        total_brand = Model.objects.count()
        assignats = Model.objects.filter(studio_assignat=studio_codi)
        n_assignats = assignats.count()
        qs = (assignats
              .select_related('garment_type_item__garment_type', 'size_system',
                              'grading_rule_set', 'garment_set')
              .order_by('sequencial', 'codi_intern'))
        if codis is not None:
            qs = qs.filter(codi_intern__in=list(codis))
        if limit:
            qs = qs[:limit]
        for m in qs:
            gti = m.garment_type_item
            rows.append({
                'codi_intern': m.codi_intern,
                'nom_prenda': m.nom_prenda,
                'any': m.any,
                'temporada': m.temporada,
                'sequencial': m.sequencial,
                'fit_type': m.fit_type,
                'base_size_label': m.base_size_label,
                'size_run_model': m.size_run_model,
                # claus naturals del catàleg (per resoldre al Studio):
                'gti_code': gti.code if gti else None,
                'gti_gt_codi': (gti.garment_type.codi_client
                                if gti and gti.garment_type_id else None),
                'size_system_codi': m.size_system.codi if m.size_system_id else None,
                'grs_nom': m.grading_rule_set.nom if m.grading_rule_set_id else None,
                # SET-1 · C6 — la UNITAT COMERCIAL viatja. Sense això el Studio rebia N models
                # solts amb codis -01/-02 i el conjunt es dissolia en silenci (risc #2 d'A2):
                # res fallava, però el producte que el client va comprar desapareixia. La clau
                # natural del conjunt és `codi_base`; `consumption_started_at` NO viatja mai —
                # el mèrit és per tenant i cada tenant merita el seu.
                'set_codi_base': m.garment_set.codi_base if m.garment_set_id else None,
                'set_nom_comercial': (m.garment_set.nom_comercial if m.garment_set_id else None),
                'set_num_pieces': m.garment_set.num_pieces if m.garment_set_id else None,
                'piece_number': m.piece_number,
                # RETORN-0 (2026-07-27) — els camps de l'ENCÀRREC que faltaven a l'anada. Cap
                # d'ells és feina: són el que la marca DEMANA (què és la peça, per a quan la
                # vol i amb quina urgència). Sense ells el Studio rebia una identitat muda i
                # havia de tornar a preguntar per correu allò que la marca ja tenia escrit.
                # Tots són literals al model (CharField/TextField/Date/PositiveSmallInteger):
                # cap FK, cap choices per-tenant → viatgen tal qual, sense clau natural.
                'collection': m.collection,
                'descripcio': m.descripcio,
                'prioritat': m.prioritat,
                'data_objectiu': m.data_objectiu,
                'target': m.target,
                'construction': m.construction,
            })
    return total_brand, n_assignats, rows


def instancia_al_studio(studio_schema, brand_codi, rows, commit):
    """Crea al Studio els models llegits, com a EXTERN. Idempotent per `codi_intern`.

    L'EXTERN NEIX AMB IDENTITAT, CONFIGURACIÓ I ENCÀRREC, MAI AMB FEINA: viatgen codi, nom,
    any, temporada, sequencial, els camps de CONFIG_KEYS resolts per clau natural i els camps
    de l'encàrrec (collection, descripcio, target, construction, prioritat, data_objectiu). No
    viatgen mesures, regles, fitxes, fittings ni tasques — la feina es fa al Studio i neix a
    zero. La frontera no és "poques dades": és FEINA vs ENCÀRREC. El que la marca demana és
    seu i ha d'arribar; el que el Studio fa és del Studio.

    `Model.objects.create()` i NO `bulk_create`: els signals s'han de disparar (la SizeFitting
    buida, el watchpoint). Un bulk_create seria més ràpid i deixaria els models a mitges.
    """
    from fhort.models_app.models import GarmentSet, Model
    from fhort.pom.models import GarmentType, GradingRuleSet, SizeSystem
    from fhort.tasks.models import Customer, GarmentTypeItem

    creats, saltats = [], []
    sets_tocats = set()
    unmatched = {k: [] for k in CONFIG_KEYS}

    with schema_context(studio_schema):
        customer = Customer.objects.filter(codi=brand_codi).first()
        if customer is None:
            raise FederacioError(
                f"Al Studio no existeix cap client amb codi='{brand_codi}'. No es crea "
                f"(decisió): sembra'l abans o revisa el vincle.", 'customer_missing')

        def _crea_tots():
            for r in rows:
                if Model.objects.filter(codi_intern=r['codi_intern']).exists():
                    saltats.append(r['codi_intern'])
                    continue

                # Resolució per clau natural. Els no-aparellats NO bloquegen: NULL + informe.
                gti = None
                if r['gti_code']:
                    gt = (GarmentType.objects.filter(codi_client=r['gti_gt_codi']).first()
                          if r['gti_gt_codi'] else None)
                    if gt is not None:
                        gti = GarmentTypeItem.objects.filter(
                            garment_type=gt, code=r['gti_code']).first()
                    if gti is None:
                        unmatched['garment_type_item'].append(
                            f"{r['gti_gt_codi']}/{r['gti_code']}")

                size_system = None
                if r['size_system_codi']:
                    size_system = SizeSystem.objects.filter(codi=r['size_system_codi']).first()
                    if size_system is None:
                        unmatched['size_system'].append(r['size_system_codi'])

                grs = None
                if r['grs_nom']:
                    grs = GradingRuleSet.objects.filter(nom=r['grs_nom']).first()
                    if grs is None:
                        unmatched['grading_rule_set'].append(r['grs_nom'])

                # SET-1 · C6 — resoldre-O-CREAR el conjunt al destí per clau natural
                # (`codi_base`). `get_or_create` fa que el traspàs d'UNA sola part creï
                # igualment el set i que les germanes s'hi enganxin quan viatgin, en qualsevol
                # ordre i en execucions separades: no hi ha cap moment en què el conjunt
                # existeixi a mitges de manera irreparable. `consumption_started_at` es deixa a
                # NULL a posta — l'albarà és patrimoni del tenant que fa la feina.
                garment_set = None
                if r.get('set_codi_base'):
                    if commit:
                        garment_set, _ = GarmentSet.objects.get_or_create(
                            codi_base=r['set_codi_base'],
                            defaults={'nom_comercial': r.get('set_nom_comercial') or '',
                                      'num_pieces': r.get('set_num_pieces') or 1},
                        )
                    sets_tocats.add(r['set_codi_base'])

                if commit:
                    Model.objects.create(
                        codi_intern=r['codi_intern'],
                        customer=customer,
                        codi_tenant=customer.codi,
                        any=r['any'],
                        temporada=r['temporada'],
                        sequencial=r['sequencial'],
                        origen=Model.ORIGEN_EXTERN,
                        nom_prenda=r['nom_prenda'],
                        fit_type=r['fit_type'] or 'Regular',
                        base_size_label=r['base_size_label'],
                        size_run_model=r['size_run_model'],
                        garment_type_item=gti,
                        size_system=size_system,
                        grading_rule_set=grs,
                        garment_set=garment_set,
                        piece_number=r.get('piece_number'),
                        # RETORN-0 — l'encàrrec (vegeu `llegeix_models_del_brand`). `prioritat`
                        # cau al default del model (3) si el Brand la té a NULL: la columna és
                        # NOT NULL i un `None` explícit petaria l'INSERT.
                        collection=r.get('collection') or '',
                        descripcio=r.get('descripcio'),
                        prioritat=r.get('prioritat') if r.get('prioritat') is not None else 3,
                        data_objectiu=r.get('data_objectiu'),
                        target=r.get('target'),
                        construction=r.get('construction'),
                    )
                creats.append(r['codi_intern'])

        if commit:
            with transaction.atomic():
                _crea_tots()
        else:
            _crea_tots()

    # `ConsumptionRecord` NO viatja (i mai ho ha fet): l'albarà és el llibre de meritació del
    # tenant que ha fet la feina, i el Studio no ha meritat res per rebre un model.
    return {'creats': creats, 'saltats': saltats, 'unmatched': unmatched,
            'sets': sorted(sets_tocats)}


def traspassa(brand_codi, studio_codi, commit=False, limit=None, codis=None):
    """El traspàs sencer: vincle → lectura del Brand → escriptura al Studio → informe.

    És el que criden LES DUES boques (command i endpoint). L'informe torna els números en
    brut; qui el rep decideix com els diu (text al terminal, JSON a l'API).
    """
    resol_vincle(brand_codi, studio_codi)
    brand_client = resol_schema(brand_codi, 'brand')
    studio_client = resol_schema(studio_codi, 'studio')

    total_brand, n_assignats, rows = llegeix_models_del_brand(
        brand_client.schema_name, studio_codi, limit=limit, codis=codis)
    report = instancia_al_studio(studio_client.schema_name, brand_codi, rows, commit)

    report.update({
        'brand_codi': brand_codi, 'studio_codi': studio_codi, 'commit': commit,
        'total_brand': total_brand, 'n_assignats': n_assignats, 'n_llegits': len(rows),
    })
    return report


#: ELS DOS ESTATS LOCALS D'UN MODEL DE LA SAFATA, declarats **al mòdul que els calcula**.
#:
#: No són un `choices` ni un camp: `estat_local` és una COMPARACIÓ (v. el docstring de
#: `safata_del_studio`), i és a posta —així no es pot desincronitzar de la realitat. Però un
#: conjunt tancat de valors que una pantalla ha de saber pintar **és una enumeració de domini**
#: encara que no visqui en una columna, i la llei d'Agus (08/08) diu que aquestes no es
#: declaren al frontend: `pages/Encarrecs.jsx` en tenia la còpia. Es publica per
#: `/api/v1/vocabulari/` → `estats_locals_encarrec`.
#:
#: Els literals estaven inline dins de la comprensió i dels dos recomptes de sota (quatre
#: aparicions de dues cadenes). Pujar-los aquí no canvia cap valor —és mecànic i verificable—
#: i dona a l'endpoint una font que és la MATEIXA que el càlcul, no una còpia seva. El dia que
#: aparegui un tercer estat (p.ex. «traspassat però divergent»), la pantalla el rebrà sola.
ESTAT_LOCAL_PENDENT = 'PENDENT'
ESTAT_LOCAL_TRASPASSAT = 'TRASPASSAT'
ESTATS_LOCALS_ENCARREC = [
    (ESTAT_LOCAL_PENDENT, 'Pendent'),
    (ESTAT_LOCAL_TRASPASSAT, 'Traspassat'),
]


def safata_del_studio(studio_codi, limit_per_brand=500):
    """El que un Studio té a la safata: els models que cada Brand vinculat li ha assignat.

    L'ESTAT ÉS UNA COMPARACIÓ, NO UN CAMP. `estat_local` es calcula mirant si el `codi_intern`
    del Brand ja existeix al MEU schema; no hi ha cap booleà "traspassat" a cap banda que es
    pugui desincronitzar. És la mateixa condició que fa idempotent la instanciació, llegida
    des de fora en comptes de des de dins.

    Només vincles ACTIUS: un pont tancat no és feina pendent, és una relació aturada, i
    ensenyar-ne els models convidaria a intentar un traspàs que el guard rebutjarà.
    """
    from fhort.models_app.models import Model

    studio_client = resol_schema(studio_codi, 'studio')
    grups = []
    links = (TenantLink.objects
             .filter(studio_codi_tenant=studio_codi, estat=TenantLink.ESTAT_ACTIU)
             .order_by('brand_codi_tenant'))

    for link in links:
        brand = Client.objects.filter(codi_tenant=link.brand_codi_tenant).first()
        if brand is None:
            # Vincle a un tenant que ja no hi és: es diu, no es fa veure que no existeix.
            grups.append({'brand_codi': link.brand_codi_tenant, 'brand_nom': '',
                          'error': 'tenant_missing', 'models': [],
                          'n_pendents': 0, 'n_traspassats': 0})
            continue

        _, _, rows = llegeix_models_del_brand(
            brand.schema_name, studio_codi, limit=limit_per_brand)

        # UNA consulta per grup (no una per model) per saber què ja tinc a casa.
        codis = [r['codi_intern'] for r in rows]
        with schema_context(studio_client.schema_name):
            ja_hi_son = set(Model.objects
                            .filter(codi_intern__in=codis)
                            .values_list('codi_intern', flat=True))

        models = [{
            'codi_intern': r['codi_intern'],
            'nom_prenda': r['nom_prenda'],
            'any': r['any'],
            'temporada': r['temporada'],
            'estat_local': (ESTAT_LOCAL_TRASPASSAT if r['codi_intern'] in ja_hi_son
                            else ESTAT_LOCAL_PENDENT),
        } for r in rows]

        grups.append({
            'brand_codi': brand.codi_tenant,
            'brand_nom': brand.nom,
            'models': models,
            'n_pendents': sum(1 for m in models if m['estat_local'] == ESTAT_LOCAL_PENDENT),
            'n_traspassats': sum(1 for m in models if m['estat_local'] == ESTAT_LOCAL_TRASPASSAT),
        })

    return grups


# ═════════════════════════════════════════════════════════════════════════════════════════
# RETORN-2 · EL CANAL D'ESTAT (bidireccional, automàtic)
# ═════════════════════════════════════════════════════════════════════════════════════════
#
# DUES DECISIONS DEL PATRÓ C QUE AQUÍ ES FAN CODI (no re-obrir):
#
#   · El canal de DADES (la feina) és un ACTE HUMÀ i viu a `envia_a_la_marca`. Mai automàtic.
#   · El canal d'ESTAT és AUTOMÀTIC i bidireccional, i és aquest. Cadascú publica el que és
#     seu de debò: l'ESTUDI mana en la FASE (ell fa la feina, ell sap on és la peça); la
#     MARCA mana en la PRIORITAT i la DATA OBJECTIU (és el seu encàrrec, la seva botiga).
#
# CAP HORA, CAP TÈCNIC, CAP COST TRAVESSA MAI AQUEST CANAL (doctrina de `views_encarrecs`:
# «el Brand no veu ni temps ni tècnics»). El que viatja en sentit maduresa és un RECOMPTE de
# tasques —quantes n'hi ha, quantes estan fetes— i mai qui les fa, quant triguen ni què costen.
# El test negatiu `test_cap_hora_ni_tecnic_al_payload` és la guarda viva d'aquesta frase.
#
# UN SYNC NO FALLA MAI CAP AMUNT. No hi ha vincle, el pont està aturat, el bessó no existeix o
# el tenant ha desaparegut → no-op amb log, i la transició de tasca (o el gate, o el PATCH de
# prioritat) que l'ha disparat continua com si res. La federació és una capa d'informació
# sobre la feina, i cap capa d'informació té dret a impedir la feina.

#: Sentit ESTUDI → MARCA. Publica la maduresa al bessó de la marca.
SENTIT_MADURESA = 'maduresa'
#: Sentit MARCA → ESTUDI. Escriu prioritat i data_objectiu al bessó de l'estudi.
SENTIT_PRIORITAT = 'prioritat'


def _codi_del_schema_actual():
    """El `codi_tenant` (3 chars) de la casa on estem ara mateix, o None si som a `public`.

    Es resol per `schema_name` i no per `connection.tenant`: dins d'un `schema_context()` el
    `connection.tenant` pot ser el d'abans (el context canvia el search_path, no l'objecte), i
    els commands i els tests sovint no en tenen cap. L'`schema_name` sempre diu la veritat.
    """
    schema = connection.schema_name
    if not schema or schema == 'public':
        return None
    with schema_context('public'):
        client = Client.objects.filter(schema_name=schema).first()
    return client.codi_tenant if client else None


def _vincle_viu(brand_codi, studio_codi):
    """El vincle ACTIU entre les dues cases, o None. MAI llança: aquí un pont tancat no és un
    error, és una relació aturada, i el canal d'estat simplement calla."""
    with schema_context('public'):
        return (TenantLink.objects
                .filter(brand_codi_tenant=brand_codi, studio_codi_tenant=studio_codi,
                        estat=TenantLink.ESTAT_ACTIU)
                .first())


def _schema_de(codi_tenant):
    with schema_context('public'):
        client = Client.objects.filter(codi_tenant=codi_tenant).first()
    return client.schema_name if client else None


def resum_maduresa(model):
    """El resum que l'ESTUDI publica sobre una peça. Dict tancat, calculat al schema d'ara.

    Les quatre xifres del brief + el segell de quan es va dir. `n_total=0` (encara ningú no ha
    planificat res) NO és «tot acabat»: `totes_acabades` exigeix que n'hi hagi alguna, la
    mateixa condició que `model_ready_for_gate` — si no, una peça verge diria a la marca que
    ja està llesta.
    """
    from fhort.tasks.models import ModelTask

    qs = ModelTask.objects.filter(model_id=model.pk)
    n_total = qs.count()
    n_done = qs.filter(status='Done').count()
    n_in_progress = qs.filter(status='InProgress').count()
    return {
        'fase_actual': model.fase_actual,
        'tasques': {
            'n_total': n_total,
            'n_done': n_done,
            'n_in_progress': n_in_progress,
            'totes_acabades': bool(n_total) and n_done == n_total,
        },
        'actualitzat_at': timezone.now().isoformat(),
    }


def sync_estat(model, sentit):
    """Publica l'estat d'aquesta peça al seu BESSÓ de l'altra casa. No-op silenciós si no pot.

    `model` és un `models_app.Model` VIU del schema on som ara. Se'n treuen escalars ABANS
    d'entrar a cap `schema_context` i el que travessa és un `.update()` de queryset: cap
    objecte ORM surt del seu schema (Bandera 3 de la diagnosi de federació).

    El bessó es resol per `codi_intern` a través del `TenantLink` ACTIU. `codi_intern` és
    l'únic lligam que hi ha entre les dues files (diagnosi §Resum executiu 3) i és el mateix
    que fa idempotent el traspàs: aquí es fa servir per a la mateixa cosa, des de l'altra punta.

    Retorna un dict d'informe: `{'ok': bool, 'motiu': str, ...}`. Mai llança.
    """
    from fhort.models_app.models import Model

    codi_intern = model.codi_intern
    meu_codi = _codi_del_schema_actual()
    if meu_codi is None:
        return _noop(codi_intern, sentit, 'sense_tenant')

    if sentit == SENTIT_MADURESA:
        # L'estudi publica cap a la marca. La marca d'aquesta peça és el seu `codi_tenant`:
        # al Studio, `Model.codi_tenant` = `Customer.codi` = `brand_codi` (el traspàs
        # l'escriu així, :166). Un model INTERN no té bessó enlloc — no és cosa de ningú més.
        if model.origen != Model.ORIGEN_EXTERN:
            return _noop(codi_intern, sentit, 'model_intern')
        brand_codi, studio_codi = model.codi_tenant, meu_codi
        destinatari = brand_codi
        canvis = {'fase_actual': model.fase_actual, 'federacio_estat': resum_maduresa(model)}
    elif sentit == SENTIT_PRIORITAT:
        # La marca escriu al bessó de l'estudi. Camps REALS i no JSON: el planificador de
        # l'estudi ja els llegeix (`scheduler_service._ordre_model`) i posar-los en un JSON
        # obligaria a ensenyar-li a llegir dues fonts per a la mateixa pregunta.
        if not model.studio_assignat:
            return _noop(codi_intern, sentit, 'sense_studio_assignat')
        brand_codi, studio_codi = meu_codi, model.studio_assignat
        destinatari = studio_codi
        canvis = {'prioritat': model.prioritat, 'data_objectiu': model.data_objectiu}
    else:
        raise ValueError(f'Sentit desconegut: {sentit!r}')

    if _vincle_viu(brand_codi, studio_codi) is None:
        return _noop(codi_intern, sentit, 'sense_vincle_actiu')

    schema_desti = _schema_de(destinatari)
    if schema_desti is None:
        return _noop(codi_intern, sentit, 'tenant_desaparegut')

    with schema_context(schema_desti):
        n = Model.objects.filter(codi_intern=codi_intern).update(**canvis)
    if not n:
        return _noop(codi_intern, sentit, 'sense_besso')

    logger.info('federacio.sync_estat[%s] %s → %s: %s', sentit, codi_intern, destinatari,
                sorted(canvis))
    return {'ok': True, 'motiu': 'sync', 'sentit': sentit, 'codi_intern': codi_intern,
            'desti': destinatari}


def _noop(codi_intern, sentit, motiu):
    """Un canal d'estat que no pot parlar CALLA i ho diu al log. No llança mai: la feina de
    qui l'ha disparat no depèn d'això."""
    logger.info('federacio.sync_estat[%s] %s: no-op (%s)', sentit, codi_intern, motiu)
    return {'ok': False, 'motiu': motiu, 'sentit': sentit, 'codi_intern': codi_intern}


def sync_estat_segur(model, sentit):
    """`sync_estat` embolcallat per als DISPARADORS (patró de la meritació, services_c:247-257).

    Els ganxos viuen dins de transaccions que fan feina de veritat (transicions de tasca,
    gates, PATCH del model). Una excepció aquí —una connexió caiguda, un schema que
    desapareix a mig camí— tombaria aquella transacció i faria que la federació decidís si
    un tècnic pot tancar una tasca. No pot.
    """
    try:
        with transaction.atomic():
            return sync_estat(model, sentit)
    except Exception:
        logger.exception('federacio.sync_estat[%s] %s: excepció empassada al disparador',
                         sentit, getattr(model, 'codi_intern', '?'))
        return {'ok': False, 'motiu': 'excepcio', 'sentit': sentit}


# ═════════════════════════════════════════════════════════════════════════════════════════
# RETORN-1 · L'ENVIAMENT DE FEINA (acte humà, mai automàtic)
# ═════════════════════════════════════════════════════════════════════════════════════════
#
# LA DECISIÓ DEL PATRÓ C: el canal de DADES és un ACTE HUMÀ. Algú de l'estudi mira la peça,
# decideix que el que hi ha està prou madur per ensenyar-ho, i clica. No hi ha cap ganxo, cap
# signal ni cap cron que ho dispari — i no n'hi ha d'haver: una taula de mides a mig fer
# publicada sola a la casa del client és pitjor que no publicar-ne cap.
#
# ÉS EL MIRALL DE `traspassa`, DEL REVÉS. Allà la marca dona identitat i l'estudi la instancia;
# aquí l'estudi dona la feina feta i la marca la rep. Les DUES CLAUS són les mateixes: el
# `TenantLink` ACTIU autoritza el pont i el bessó per `codi_intern` autoritza la peça.
#
# SOBIRANIA DEL DESTÍ (patró `copiar_de_model_view`): la marca és sobirana del seu schema. Una
# fila seva amb origen específic (MANUAL/FITTED/IMPORTED…) o amb valor ja posat NO es trepitja
# MAI; només s'omple un TEMPLATE BUIT. El que no viatja no desapareix de l'informe: es compta.
#
# QUÈ NO VIATJA MAI, I PER QUÈ:
#   · El `.ftt` viu (TECHSHEET) — decisió del Patró C, literal. El document editable és d'una
#     sola casa; dues cadenes de versions amb dos `is_current` i dos locks que no es veuen és
#     el risc R4 de la diagnosi, i aquí no s'obre.
#   · Les TASQUES — decisió del Patró C, literal. Són el calaix B (local per actor): la marca
#     no ha de tenir les tasques de l'estudi ni sabria què fer-ne.
#   · El PATRÓ (DXF) — decisió d'aquest sprint. NO és perquè el DXF tingui dependències
#     locals (no en té: són bytes autocontinguts), sinó perquè el patró JA TÉ LA SEVA PORTA:
#     `patterns.ExportAcknowledgement` és una precondició DURA amb text literal acceptat i
#     versió de grading segellada («entre el nostre motor i la taula de tall hi ha d'haver una
#     persona que hagi dit sí»). Fer sortir el DXF per aquest botó genèric seria una SEGONA
#     boca sobre la mateixa llei, que és exactament la divergència contra la qual avisa el
#     docstring d'aquest mòdul. Si un dia el patró ha de federar-se, ha de passar per la seva
#     porta, no per aquesta.
#   · `GradedSpec` — es RECALCULA al destí. És sortida del motor, no dada: enviar-la seria
#     enviar una fotografia d'un càlcul que la marca pot tornar a fer amb les regles que sí
#     que viatgen.
#   · Cap hora, cap tècnic, cap cost (doctrina de sempre).

#: Els únics tipus de fitxer que travessen el pont. `EXPORT` és el PDF que ja està fet per
#: ensenyar; els `SKETCH_*` són el dibuix de la peça. Tota la resta —TECHSHEET, PATRO, ESCALAT,
#: MARCADA, RUL, DOCUMENT, ALTRES— es queda a casa.
TIPUS_FEDERABLES = ('EXPORT', 'SKETCH_FLETXES', 'SKETCH_NET', 'SKETCH_SVG')

#: Provinença de tot el que arriba per aquest camí (choice afegit al mateix sprint).
ORIGEN_FEDERAT = 'FEDERAT'


#: Versió del paquet de patrimoni que viatja entre cases. **1** = clau natural de 2 trams
#: (només el POM); **2** = clau de 4 trams, amb capa i instància. Un paquet sense el camp és
#: de la versió 1 per definició, i es llegeix com a exterior + instància única.
FORMAT_PATRIMONI = 2


def _clau_natural_pom(pom, capa=None, instancia=''):
    """La clau amb què una MESURA es reconeix a l'altra casa.

    `(codi del diccionari, codi de client, capa, instància)`.

    `POMGlobal.codi` és el diccionari CANÒNIC i és la clau forta —és el mateix vocabulari a
    totes les cases—; `POMMaster.codi_client` és la nomenclatura local i només serveix de
    darrer recurs. Mateixa forma que CONFIG_KEYS (clau natural, mai pk), i deliberadament MÉS
    ESTRICTA que `find_pom_master`: aquell matcher és per a fitxes de proveïdor, on cal
    endevinar; aquí les dues cases parlen el mateix sistema i endevinar seria posar una mesura
    sobre el POM equivocat sense que ningú se n'assabentés.

    🚨 FASE_3/C1-ins — **LA CLAU CREIX A 4 TRAMS, i és per l'argument que aquest docstring ja
    feia.** El POM identifica QUÈ es mesura; els dos eixos identifiquen DE QUÈ i DE QUINA
    REPETICIÓ. Amb la clau de 2, dues mesures germanes emetien la MATEIXA clau: el destí en
    resolia una, l'altra hi queia a sobre, i cap de les dues cases se n'assabentava. Endevinar
    hauria estat posar la mesura sobre el POM equivocat; col·lapsar-les és pitjor, perquè ni
    tan sols hi ha un POM equivocat a què assenyalar.

    Els eixos NO es resolen al catàleg del destí: no són del `POMMaster`, són de la FILA de
    mesura. Viatgen dins de la clau i s'escriuen tal qual a l'altra banda.

    `pom.GradingRule` i `models_app.ModelGradingRule` no tenen eixos (decisió Montse:
    «gradúen igual»); les regles viatgen amb el parell canònic com a farciment, perquè les
    dues cases parlin una sola forma de clau i no dues.
    """
    from fhort.pom.models import MeasurementLayer
    if capa is None:
        capa = MeasurementLayer.SLUG_DEFECTE
    return ((pom.pom_global.codi if pom.pom_global_id else None), pom.codi_client,
            capa, instancia)


def _clau_amb_eixos(clau):
    """Normalitza una clau de paquet a 4 trams. Un paquet VELL (format 1) en porta 2.

    Els paquets ja enviats abans de C1-ins parlen, de fet i sense excepció, de l'exterior i
    de la instància única —era l'única cosa que el sistema sabia escriure—, o sigui que
    completar-los amb el parell canònic no els atribueix res que no diguessin ja. Es fa aquí,
    a la porta d'entrada, i no a cada lloc que toca una clau.
    """
    from fhort.pom.models import MeasurementLayer
    if len(clau) == 4:
        return tuple(clau)
    global_codi, codi_client = clau
    return (global_codi, codi_client, MeasurementLayer.SLUG_DEFECTE, '')


def _nom_del_no_aparellat(clau):
    """Com s'anomena al informe un POM que no ha trobat parella.

    Les DUES cares, i a posta: el codi del diccionari és el que la marca reconeix i pot buscar
    al seu catàleg; el `codi_client` és el que l'estudi veu a la seva pantalla. Un informe que
    només digués un dels dos obligaria una de les dues cases a traduir-lo a mà.
    """
    global_codi, codi_client, capa, instancia = _clau_amb_eixos(clau)
    nom = (f'{global_codi} ({codi_client})' if (global_codi and codi_client)
           else (global_codi or codi_client or '?'))
    # FASE_3/C1-ins — els eixos només surten a l'informe quan diuen alguna cosa. Escriure
    # «(exterior, instància única)» a cada línia d'un informe on TOT és exterior seria soroll
    # que taparia les poques línies on de debò importa.
    from fhort.pom.models import MeasurementLayer
    qualificadors = [q for q in (capa if capa != MeasurementLayer.SLUG_DEFECTE else '',
                                 instancia) if q]
    return f'{nom} · {" · ".join(qualificadors)}' if qualificadors else nom


def _resol_pom_al_desti(clau, cache):
    """Resol la clau natural contra el catàleg del destí. None = no aparellat (i no viatja)."""
    if clau in cache:
        return cache[clau]
    from fhort.pom.models import POMMaster

    # Els DOS EIXOS no es resolen aquí i no hi han de ser: no són del `POMMaster` sinó de la
    # fila de mesura. Aquesta funció respon «quin POM del catàleg del destí és aquest», i la
    # resposta no depèn ni de la capa ni de la instància.
    global_codi, codi_client, _capa, _instancia = _clau_amb_eixos(clau)
    pom = None
    if global_codi:
        pom = POMMaster.objects.filter(pom_global__codi=global_codi, actiu=True).first()
    if pom is None and codi_client:
        pom = POMMaster.objects.filter(codi_client=codi_client, actiu=True).first()
    cache[clau] = pom
    return pom


def _llegeix_patrimoni(model):
    """Tot el que pot viatjar, com a DICTS TANCATS i BYTES ja llegits. Cap ORM en surt viu.

    Els bytes es llegeixen AQUÍ i no al destí a posta: `FileField.name` és relatiu al TENANT
    (memòria `ftt-media-namespace-tenant`), de manera que obrir el fitxer un cop ja som a
    l'altre schema el buscaria al calaix equivocat.

    🚨 FASE_2/C1-ins — ÀNCORA `capa='exterior', instancia=''` a les mesures, que aquesta
    lectura no havia tingut mai (la federació no es va mirar a l'Onada 1). El motiu és el
    mateix que fa que aquesta funció existeixi: el que en surt és el que VIATJA, i la clau
    amb què viatja és `_clau_natural_pom` —el codi del diccionari i el del client—, que no
    porta cap dels dos eixos. Dues mesures del mateix POM emetrien la MATEIXA clau, el destí
    en desaria una i l'altra desapareixeria sense que cap de les dues cases se n'assabentés.

    Que la clau natural creixi a 4-tupla i que els paquets es versionin és FASE_3: aquí no
    s'endevina res, es deixa de dir el que no se sap dir. Mentrestant, el patrimoni que
    viatja és el de l'exterior i el de la instància única, que és exactament el que fins avui
    hi havia.
    """
    from fhort.models_app.models import BaseMeasurement, ModelFitxer, ModelGradingRule
    from fhort.pom.models import MeasurementLayer

    mesures = []
    for bm in (BaseMeasurement.objects.filter(
                   model=model, is_active=True,
                   capa=MeasurementLayer.SLUG_DEFECTE, instancia='')
               .select_related('pom__pom_global').order_by('ordre', 'pom_id')):
        mesures.append({
            'clau': _clau_natural_pom(bm.pom, bm.capa, bm.instancia),
            'base_value_cm': bm.base_value_cm,
            'is_key': bm.is_key,
            'nom_fitxa': bm.nom_fitxa or '',
            'tolerancia_minus': bm.tolerancia_minus,
            'tolerancia_plus': bm.tolerancia_plus,
            'ordre': bm.ordre,
        })

    regles = []
    for r in (ModelGradingRule.objects.filter(model=model, actiu=True)
              .select_related('pom__pom_global').order_by('pom_id')):
        regles.append({
            # La regla NO té eixos (decisió Montse: la sisa dreta i l'esquerra gradúen
            # igual). Viatja amb el parell canònic com a farciment perquè les dues cases
            # parlin una sola forma de clau; el destí la resol pel POM i prou.
            'clau': _clau_natural_pom(r.pom),
            'logica': r.logica,
            'increment': r.increment,
            'valors_step': r.valors_step,
            'increment_base': r.increment_base,
            'increment_break': r.increment_break,
            'talla_break_label': r.talla_break_label,
            'talla_break_pos': r.talla_break_pos,
        })

    fitxers = []
    for f in (ModelFitxer.objects.filter(model=model, tipus__in=TIPUS_FEDERABLES,
                                         is_current=True)
              .exclude(fitxer='').exclude(fitxer__isnull=True).order_by('tipus', 'id')):
        try:
            f.fitxer.open('rb')
            contingut = f.fitxer.read()
        except (OSError, ValueError) as e:
            fitxers.append({'error': str(e), 'nom_fitxer': f.nom_fitxer, 'tipus': f.tipus})
            continue
        finally:
            try:
                f.fitxer.close()
            except (OSError, ValueError):
                pass
        fitxers.append({'nom_fitxer': f.nom_fitxer, 'tipus': f.tipus,
                        'checksum': f.checksum, 'bytes': contingut})

    return {
        # FASE_3/C1-ins — el paquet es VERSIONA. Sense això, un destí que ja sap llegir claus
        # de 4 trams no podria distingir un paquet vell d'un de nou i hauria d'endevinar, que
        # és precisament el que aquesta cadena de funcions existeix per no fer mai.
        'format': FORMAT_PATRIMONI,
        'mesures': mesures,
        'regles': regles,
        'fitxers': fitxers,
        'base_size_label': (model.base_size_label or '').strip(),
    }


def _escriu_a_la_marca(brand_schema, codi_intern, patrimoni):
    """Escriu el patrimoni al bessó de la marca respectant-ne la sobirania. Retorna l'informe."""
    from django.core.files.base import ContentFile

    from fhort.models_app.models import (BaseMeasurement, Model, ModelFitxer, ModelGradingRule,
                                         Watchpoint)
    from fhort.models_app.services_fitxers import save_model_file

    viatjat = {'mesures': 0, 'regles': 0, 'fitxers': 0, 'pertinences': 0}
    saltat = {'mesures': 0, 'regles': 0, 'fitxers': 0}
    no_aparellat, avisos = [], []
    cache = {}

    with schema_context(brand_schema):
        twin = Model.objects.filter(codi_intern=codi_intern).first()
        if twin is None:
            raise FederacioError(
                f"La marca no té cap model amb codi_intern='{codi_intern}'. Res a enviar: la "
                f'peça encara no existeix a l\'altra banda.', 'besso_missing')

        # GUARD DE TALLA (transposat de `copiar_de_model_view`): un valor està expressat EN UNA
        # TALLA. Si les dues cases no parlen la mateixa talla base, viatja la PERTINENÇA del
        # POM (fila TEMPLATE buida) i cap VALOR. Una mesura en una talla que no és la del model
        # que la rep no és una dada imprecisa: és una dada falsa.
        talla_origen = patrimoni['base_size_label']
        talla_desti = (twin.base_size_label or '').strip()
        talla_divergent = bool(talla_origen and talla_desti and talla_origen != talla_desti)
        if talla_divergent:
            avisos.append(
                f'TALLES DIVERGENTS: l\'estudi mesura en «{talla_origen}» i la marca té la base '
                f'a «{talla_desti}». No ha viatjat cap VALOR (sí la pertinença dels POMs).')
        elif talla_origen and not talla_desti:
            avisos.append(
                f'La marca no té talla base declarada; els valors han viatjat assumint que '
                f'parlen «{talla_origen}», que és el que diu l\'estudi.')

        with transaction.atomic():
            for row in patrimoni['mesures']:
                pom = _resol_pom_al_desti(row['clau'], cache)
                if pom is None:
                    no_aparellat.append(_nom_del_no_aparellat(row['clau']))
                    continue
                # FASE_3/C1-ins — els eixos viatgen DINS de la clau i s'escriuen tal qual.
                # `_clau_amb_eixos` accepta paquets vells (format 1, clau de 2 trams) i els
                # llegeix com a exterior + instància única.
                _g, _c, capa_row, instancia_row = _clau_amb_eixos(row['clau'])
                te_valor = (not talla_divergent) and row['base_value_cm'] is not None
                existent = BaseMeasurement.objects.filter(
                    model=twin, pom=pom, capa=capa_row, instancia=instancia_row).first()

                if existent is None:
                    BaseMeasurement.objects.create(
                        model=twin, pom=pom,
                        capa=capa_row, instancia=instancia_row,
                        base_value_cm=row['base_value_cm'] if te_valor else None,
                        # `notes` NO viatja: és text lliure escrit sobre l'altra fila i portat
                        # aquí seria una afirmació amb aparença d'auditoria (mateix criteri
                        # que la còpia model→model).
                        nom_fitxa=row['nom_fitxa'] if te_valor else '',
                        tolerancia_minus=row['tolerancia_minus'] if te_valor else None,
                        tolerancia_plus=row['tolerancia_plus'] if te_valor else None,
                        origen=ORIGEN_FEDERAT if te_valor else 'TEMPLATE',
                        is_key=row['is_key'], ordre=row['ordre'],
                    )
                    if te_valor:
                        viatjat['mesures'] += 1
                    else:
                        viatjat['pertinences'] += 1
                    continue

                # SOBIRANIA: només s'omple un TEMPLATE BUIT. Tota la resta és de la marca.
                template_buit = existent.origen == 'TEMPLATE' and existent.base_value_cm is None
                if te_valor and template_buit:
                    existent.base_value_cm = row['base_value_cm']
                    existent.nom_fitxa = row['nom_fitxa'] or existent.nom_fitxa
                    existent.tolerancia_minus = row['tolerancia_minus']
                    existent.tolerancia_plus = row['tolerancia_plus']
                    existent.origen = ORIGEN_FEDERAT
                    existent.save(update_fields=['base_value_cm', 'nom_fitxa', 'tolerancia_minus',
                                                 'tolerancia_plus', 'origen', 'updated_at'])
                    viatjat['mesures'] += 1
                else:
                    saltat['mesures'] += 1

            for row in patrimoni['regles']:
                pom = _resol_pom_al_desti(row['clau'], cache)
                if pom is None:
                    no_aparellat.append(_nom_del_no_aparellat(row['clau']))
                    continue
                # La regla RESIDENT de la marca és el seu judici sobre les seves dades: si ja
                # n'hi ha una, no es toca. `GradedSpec` no viatja mai — el motor de la marca
                # projectarà des d'aquestes regles quan li toqui.
                if ModelGradingRule.objects.filter(model=twin, pom=pom).exists():
                    saltat['regles'] += 1
                    continue
                ModelGradingRule.objects.create(
                    model=twin, pom=pom, logica=row['logica'], increment=row['increment'],
                    valors_step=row['valors_step'], increment_base=row['increment_base'],
                    increment_break=row['increment_break'],
                    talla_break_label=row['talla_break_label'],
                    talla_break_pos=row['talla_break_pos'],
                    origen=ORIGEN_FEDERAT,
                )
                viatjat['regles'] += 1

        # Els BYTES fora de l'atomic: un rollback no els desfaria i deixaria fitxers orfes
        # (mateix criteri que la còpia model→model).
        for f in patrimoni['fitxers']:
            if 'error' in f:
                avisos.append(f"No s'ha pogut llegir «{f['nom_fitxer']}»: {f['error']}")
                continue
            anterior = (ModelFitxer.objects.filter(model=twin, tipus=f['tipus'])
                        .order_by('-versio', '-id').first())
            # IDEMPOTÈNCIA PER CHECKSUM: re-enviar el mateix fitxer no encadena una versió
            # nova. Sense això, cada clic del botó inflaria la cadena del destí amb còpies
            # idèntiques i el «v7» de la marca no voldria dir res.
            if anterior is not None and anterior.checksum and anterior.checksum == f['checksum']:
                saltat['fitxers'] += 1
                continue
            num = (anterior.versio + 1) if anterior else 1
            ext = os.path.splitext(f['nom_fitxer'])[1] or ''
            nom = f"{twin.codi_intern}_{f['tipus']}_{num:03d}{ext}"
            try:
                save_model_file(twin, ContentFile(f['bytes'], name=nom),
                                versio_anterior=anterior, tipus=f['tipus'], origen='federacio',
                                nom=nom)
            except (ValueError, OSError) as e:
                avisos.append(f"No s'ha pogut desar «{f['nom_fitxer']}»: {e}")
                continue
            viatjat['fitxers'] += 1

        informe = {'viatjat': viatjat, 'saltat': saltat,
                   'no_aparellat': sorted(set(no_aparellat)), 'avisos': avisos}

        # L'INFORME, AL MODEL DE LA MARCA. `dades=None` a posta i no per descuit: el signal
        # `recompute_import_watchpoint` (models_app/signals.py) reclama TOT Watchpoint obert
        # amb `task IS NULL` i `dades` no-null, i li reescriu el text amb la config que falta.
        # Un informe d'enviament amb `dades` poblades duraria fins al següent save del model.
        # `created_by=None`: qui ha clicat viu a l'altre schema i el seu UserProfile no existeix
        # aquí — inventar-ne un seria mentir sobre l'autoria.
        Watchpoint.objects.create(model=twin, dades=None, text=_text_informe(informe))

    return informe


def _text_informe(informe):
    v, s = informe['viatjat'], informe['saltat']
    parts = [
        f"Enviament de l'estudi: {v['mesures']} mesura/es, {v['regles']} regla/es de graduació "
        f"i {v['fitxers']} fitxer/s.",
    ]
    if v['pertinences']:
        parts.append(f"{v['pertinences']} POM/s han arribat sense valor (només la pertinença).")
    if any(s.values()):
        parts.append(f"No s'ha trepitjat res del que ja teníeu: {s['mesures']} mesura/es, "
                     f"{s['regles']} regla/es i {s['fitxers']} fitxer/s intactes.")
    if informe['no_aparellat']:
        parts.append('POMs que NO s\'han pogut aparellar amb el vostre catàleg i no han '
                     'viatjat: ' + ', '.join(informe['no_aparellat']) + '.')
    parts.extend(informe['avisos'])
    return ' '.join(parts)


def envia_a_la_marca(model_estudi):
    """ACTE HUMÀ: l'estudi envia la feina feta al bessó de la marca. Mai automàtic.

    Llança `FederacioError` amb `codi` estable quan no es pot fer (la boca el tradueix a HTTP):
    `model_no_extern` · `link_missing`/`link_not_active` · `tenant_missing` · `besso_missing`.
    """
    from fhort.models_app.models import Model

    if model_estudi.origen != Model.ORIGEN_EXTERN:
        raise FederacioError(
            f"«{model_estudi.codi_intern}» no és un model EXTERN: no ve de cap marca i no hi ha "
            f'on enviar-lo.', 'model_no_extern')

    studio_codi = _codi_del_schema_actual()
    brand_codi = model_estudi.codi_tenant
    resol_vincle(brand_codi, studio_codi)          # les dues claus, com al traspàs
    brand_client = resol_schema(brand_codi, 'brand')

    patrimoni = _llegeix_patrimoni(model_estudi)
    informe = _escriu_a_la_marca(brand_client.schema_name, model_estudi.codi_intern, patrimoni)
    informe.update({'codi_intern': model_estudi.codi_intern, 'brand_codi': brand_codi})
    logger.info('federacio.envia_a_la_marca %s → %s: %s', model_estudi.codi_intern, brand_codi,
                informe['viatjat'])
    return informe
