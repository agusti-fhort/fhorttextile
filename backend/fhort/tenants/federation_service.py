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
from django.db import transaction
from django_tenants.utils import schema_context

from .models import Client, TenantLink


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
              .select_related('garment_type_item__garment_type', 'size_system', 'grading_rule_set')
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
            })
    return total_brand, n_assignats, rows


def instancia_al_studio(studio_schema, brand_codi, rows, commit):
    """Crea al Studio els models llegits, com a EXTERN. Idempotent per `codi_intern`.

    L'EXTERN NEIX AMB IDENTITAT I CONFIGURACIÓ, MAI AMB FEINA: viatgen codi, nom, any,
    temporada, sequencial i els camps de CONFIG_KEYS resolts per clau natural. No viatgen
    mesures, regles, fitxes, fittings ni tasques — la feina es fa al Studio i neix a zero.

    `Model.objects.create()` i NO `bulk_create`: els signals s'han de disparar (la SizeFitting
    buida, el watchpoint). Un bulk_create seria més ràpid i deixaria els models a mitges.
    """
    from fhort.models_app.models import Model
    from fhort.pom.models import GarmentType, GradingRuleSet, SizeSystem
    from fhort.tasks.models import Customer, GarmentTypeItem

    creats, saltats = [], []
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
                    )
                creats.append(r['codi_intern'])

        if commit:
            with transaction.atomic():
                _crea_tots()
        else:
            _crea_tots()

    return {'creats': creats, 'saltats': saltats, 'unmatched': unmatched}


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
            'estat_local': 'TRASPASSAT' if r['codi_intern'] in ja_hi_son else 'PENDENT',
        } for r in rows]

        grups.append({
            'brand_codi': brand.codi_tenant,
            'brand_nom': brand.nom,
            'models': models,
            'n_pendents': sum(1 for m in models if m['estat_local'] == 'PENDENT'),
            'n_traspassats': sum(1 for m in models if m['estat_local'] == 'TRASPASSAT'),
        })

    return grups
