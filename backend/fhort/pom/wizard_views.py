"""
fhort/pom/wizard_views.py
Endpoints for the Design Freeze + Base Size wizard flow.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone

from fhort.pom.models import MeasurementLayer
from fhort.pom.services import SealedGradingVersionError, _te_regles


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN FREEZE
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_design_freeze_view(request, model_id):
    """
    POST /api/v1/models/{id}/aprovar-design-freeze/
    The technician approves the model's Design Freeze.
    Does not require measurements — it is a visual/conceptual approval.
    """
    try:
        from fhort.models_app.models import Model
        model = Model.objects.get(pk=model_id)

        if model.design_freeze_at:
            return Response({
                'missatge': 'Design Freeze ja aprovat',
                'design_freeze_at': model.design_freeze_at,
                'design_freeze_by': str(model.design_freeze_by),
            })

        model.design_freeze_at = timezone.now()
        model.design_freeze_by = request.user
        if model.estat == 'Nou':
            model.estat = 'En curs'
        model.save(update_fields=['design_freeze_at', 'design_freeze_by', 'estat'])

        return Response({
            'missatge': 'Design Freeze aprovat correctament',
            'design_freeze_at': model.design_freeze_at,
            'design_freeze_by': str(request.user),
        })
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# SUGGESTED POMs BY GARMENT TYPE
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def suggested_poms_view(request):
    """
    GET /api/v1/poms/suggerits/?garment_type_item=X
    Return the suggested POMs for a garment_type_item (família → item migration),
    with the tenant nomenclature (codi_client, nom_client) and the real is_key from the map.
    No GarmentPOMMap for the item → empty + warning (NO 'all active POMs' fallback: it masked gaps).
    """
    item_id = request.query_params.get('garment_type_item')

    try:
        from fhort.pom.models import GarmentPOMMap

        if not item_id:
            return Response({'count': 0, 'results': [],
                             'warning': 'garment_type_item requerit'})

        # POMs de l'item, amb is_key/ordre reals del mapa (key primer, després ordre).
        maps = (GarmentPOMMap.objects
                .filter(garment_type_item_id=item_id)
                .select_related('pom', 'pom__categoria', 'pom__pom_global')
                .order_by('-is_key', 'ordre'))

        data = []
        for m in maps:
            pom = m.pom
            data.append({
                'id': pom.id,
                'codi_client': pom.codi_client,
                'nom_client': pom.nom_client,
                'nom_global_ca': pom.pom_global.nom_ca if pom.pom_global_id else '',
                'nom_global_en': pom.pom_global.nom_en if pom.pom_global_id else '',
                'categoria_id': pom.categoria_id,
                'categoria_nom': pom.categoria.nom_ca if pom.categoria_id else '',
                'categoria_ordre': pom.categoria.display_order if pom.categoria_id else 99,
                'is_key_measure': m.is_key,
                'ordre': m.ordre,
                'unitat': pom.pom_global.unitat if pom.pom_global_id else 'cm',
            })

        resp = {'count': len(data), 'results': data}
        if not data:
            resp['warning'] = 'Cap POM mapejat per a aquest item'
        return Response(resp)

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error loading suggested POMs")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_poms_view(request):
    """
    GET /api/v1/poms/cerca/?q=chest[&model=<id>][&page_size=N]
    Search POMs in the tenant catalog by code or name.
    """
    q = request.query_params.get('q', '').strip()

    # ⚠️ **SENSE TEXT NO ES TORNAVA RES, I AIXÒ NO ÉS «CERCAR»: ÉS OBLIGAR A ENDEVINAR.**
    # (QA Agus 09/08, segona volta.) Era `if not q: return {'results': []}`, o sigui que el
    # catàleg només existia per a qui ja en sabia el nom. Qui obre el carril per veure QUÈ hi ha
    # —el cas de qui encara no coneix la nomenclatura d'aquest client— es trobava un buit i en
    # deduïa que no hi havia catàleg. És la mateixa cadena que va fabricar el duplicat: el que no
    # es veu es torna a crear.
    #
    # Amb la consulta buida no es filtra res i es torna el CATÀLEG SENCER (els 142 + els àlies
    # del client), amb el mateix sostre declarat que la resta: `count` i `truncat` diuen quants
    # n'hi ha i si en falten. Ordenar no és amagar (D-31.3).
    cataleg_sencer = not q

    # ⚠️ **EL MÍNIM DE DOS CARÀCTERS FEIA INABASTABLE MIG CATÀLEG** (QA Agus 09/08).
    #
    # Era `len(q) < 2 → cap resultat`, i el catàleg v4 de Brownie té **22 POMs amb codi d'UN sol
    # caràcter** (A, B, C, D, E, **F**, I, J, K…) més 13 àlies igual de curts. Escriure «F» al
    # carril —que és exactament com es diu aquella cota— no tornava res, i el POM semblava no
    # existir. D'aquí va sortir un duplicat creat a mà.
    #
    # Amb un sol caràcter la cerca es fa NOMÉS PER CODI (i per prefix): qui escriu «F» en un
    # carril que va per nomenclatura demana el codi F, no totes les mesures que porten una efa
    # al mig del nom. Amb dos o més, la cerca és la de sempre, per codi I per nom.
    nomes_codi = len(q) == 1

    # EL SOSTRE ES DIU I ES POT MOURE. Era `[:20]` incrustat dues vegades i el client n'enviava
    # un altre (`page_size=10`) que ningú llegia: la llista es tallava en silenci i no hi havia
    # manera de saber si el que buscaves no hi era o només no hi cabia. Ara el `page_size` mana
    # i la resposta diu `count`/`truncat` (v. el final de la vista).
    try:
        limit = max(1, min(int(request.query_params.get('page_size') or 25), 100))
    except (TypeError, ValueError):
        limit = 25

    try:
        from fhort.pom.models import CustomerPOMAlias, POMMaster
        from django.db.models import Case, IntegerField, Q, Value, When

        # ─────────────────────────────────────────────────────────────────────────────────
        # ELS POMS ES VAN A BUSCAR AL CATÀLEG DEL CLIENT. ENLLOC MÉS. (Agus, 06/08)
        # ─────────────────────────────────────────────────────────────────────────────────
        #
        # Aquesta vista cercava per `POMMaster.codi_client`, i aquell camp **es diu "client"
        # però és el codi de la CASA**. El codi DEL CLIENT viu només a
        # `CustomerPOMAlias.client_code`. Conseqüència mesurada al schema `fhort`: un model de
        # Brownie veia els 393 POMs del tenant —inclosos els 240 de Losan— i, buscant «U1», se
        # li oferien `U1 JETTING WIDTH` (de LOS) i `U1 Height sequins piece` (un orfe creat per
        # un import), però NO `BTN SP Button spacing`, que és el que Brownie anomena U1.
        #
        # Amb `?model=` (el cas del cercador de Definició POM) la cerca resol TAMBÉ contra els
        # àlies del client D'AQUEST MODEL: el seu codi, la seva descripció internacional i la
        # seva descripció local. Això respon una pregunta que el catàleg de la casa sol no pot
        # respondre: «com anomena aquest client aquesta mesura?».
        #
        # ⚠️ **PERÒ ÉS UNA UNIÓ, NO UN FILTRE** (QA Agus 09/08, i és un defecte pagat en dades).
        #
        # Amb `?model=` la cerca es feia NOMÉS contra els àlies, i llavors un POM del catàleg
        # que aquest client encara no ha batejat **no existeix per al cercador**. Mesurat al
        # schema `fhort` amb el catàleg v4: 143 POMs actius i només 64 amb àlies de Brownie →
        # **79 invisibles**. Entre ells `EK · Neck width`, que és exactament el que es va anar a
        # buscar, no es va trobar, i es va acabar creant un duplicat (POM 1047). El cercador que
        # amaga dos terços del catàleg no protegeix de res: FABRICA duplicats.
        #
        # I hi havia un segon forat de la mateixa forma: contra els àlies només es miraven els
        # camps de l'àlies, o sigui que un POM SÍ batejat pel client tampoc no es trobava pel
        # seu nom canònic. Qui escriu «neck» al carril vol totes dues coses.
        #
        # Per això ara sempre hi ha les DUES consultes i el resultat és la seva unió, amb els
        # àlies al davant: la proximitat ordena, no exclou. Sense `?model=` només hi ha la
        # canònica, perquè no hi ha client de qui parlar.
        model_id = request.query_params.get('model')
        customer_id = None
        if model_id:
            from fhort.models_app.models import Model as ModelPeça
            customer_id = (ModelPeça.objects.filter(pk=model_id)
                           .values_list('customer_id', flat=True).first())

        # (a) EL CATÀLEG DE LA CASA — sempre. Codi i nom propis, i el canònic del sector si el POM
        #     hi està lligat.
        filtre_canonic = (
            Q() if cataleg_sencer else
            Q(codi_client__istartswith=q) if nomes_codi else
            Q(codi_client__icontains=q) |
            Q(nom_client__icontains=q) |
            Q(pom_global__nom_ca__icontains=q) |
            Q(pom_global__nom_en__icontains=q)
        )
        ids_canonic = list(POMMaster.objects.filter(actiu=True).filter(filtre_canonic)
                           # El codi EXACTE primer: qui escriu «F» vol la F, i després les seves
                           # germanes (F1, F2, FB…). Sense això la F queia enmig d'una llista
                           # alfabètica de setze codis que comencen igual.
                           .annotate(_exacte=Case(When(codi_client__iexact=q, then=Value(0)),
                                                  default=Value(1), output_field=IntegerField()))
                           .order_by('_exacte', 'codi_client').values_list('id', flat=True))

        # (b) EL VOCABULARI DEL CLIENT — només amb model al davant. Un client pot tenir diversos
        #     codis per al mateix POM (la unicitat és (customer, client_code)), així que es
        #     dedupliquen per `pom_id` conservant l'ordre d'aparició.
        ids_alies = []
        if customer_id:
            filtre_alies = (
                Q() if cataleg_sencer else
                Q(client_code__istartswith=q) if nomes_codi else
                Q(client_code__icontains=q) |
                Q(description_en__icontains=q) |
                Q(description_local__icontains=q)
            )
            ids_alies = list(CustomerPOMAlias.objects
                             .filter(customer_id=customer_id, pom__isnull=False)
                             .filter(filtre_alies)
                             .annotate(_exacte=Case(When(client_code__iexact=q, then=Value(0)),
                                                    default=Value(1), output_field=IntegerField()))
                             .order_by('_exacte', 'pendent_revisio', 'client_code')
                             .values_list('pom_id', flat=True))

        # EL NIVELL DE PROXIMITAT (v8.1 · cercador agrupat). Amb `?model=`, cada resultat diu si
        # el POM ve de l'ITEM d'aquest model, de la seva FAMÍLIA (un altre item del mateix
        # GarmentType) o del CATÀLEG del client. Sense `?model=` tots surten com a 'cataleg': el
        # nivell és una relació amb un model concret, i inventar-la sense model seria mentir.
        #
        # Es resol amb DUES consultes de `pom_id` i no per resultat: vint resultats × dues
        # comprovacions serien quaranta viatges a la BD per pintar una llista desplegable.
        ids_item, ids_familia = set(), set()
        if model_id:
            from fhort.pom.models import GarmentPOMMap
            m = (ModelPeça.objects
                 .filter(pk=model_id)
                 .values('garment_type_item_id', 'garment_type_item__garment_type_id')
                 .first())
            if m and m['garment_type_item_id']:
                ids_item = set(GarmentPOMMap.objects
                               .filter(garment_type_item_id=m['garment_type_item_id'])
                               .values_list('pom_id', flat=True))
                gt = m['garment_type_item__garment_type_id']
                if gt:
                    ids_familia = set(GarmentPOMMap.objects
                                      .filter(garment_type_item__garment_type_id=gt)
                                      .values_list('pom_id', flat=True)) - ids_item

        def _nivell(pom_id):
            if pom_id in ids_item:
                return 'item'
            if pom_id in ids_familia:
                return 'type'
            return 'cataleg'

        # ══ EL CERCADOR NO FUSIONA ENTITATS: DUES POBLACIONS, SEMPRE (Agus, 09/08) ═══════
        #
        # El canònic `F · Centre front length from HPS` i l'àlies `FB2` de Brownie **SÓN DUES
        # COSES**, i abans se n'oferia UNA: la unió deduplicava per `pom_id` i la presentació
        # tapava el canònic amb els camps de l'àlies. Qui tenia el catàleg de la casa al davant
        # i escrivia «F» no podia saber que aquell `FB2` el contenia; qui cercava pel nom
        # canònic rebia una fila que no deia el nom canònic enlloc. Dir-ho amb una sola fila
        # obligava el lector a saber-ho ja — i qui no ho sabia, duplicava.
        #
        # Ara el desplegable presenta SEMPRE dues poblacions, i cap fila és combinada:
        #   · CATÀLEG DEL CLIENT — els àlies del client d'aquest model, amb el SEU codi i la SEVA
        #     redacció, i la segona línia dient a quin canònic apunten;
        #   · CATÀLEG DE LA CASA — els canònics, cadascun com a ELL MATEIX (codi + nom canònic).
        #
        # Un POM amb àlies hi surt DUES vegades, una per secció, i **totes dues resolen al mateix
        # `pom_id`**: no es demana a ningú que sàpiga que són la mateixa cosa, es deixa que hi
        # arribi per qualsevol de les dues portes.
        #
        # Com a molt UNA fila d'àlies per POM: `alies_per_pom` en dona un per POM (és el que
        # PINTA la nomenclatura del client) i un client amb dos codis per al mateix POM no ha de
        # generar dues files calcades.
        from fhort.pom.nomenclatura import alies_per_pom, camps_de
        alias_by_pom = alies_per_pom(customer_id)
        CAMPS_ALIES = list(camps_de(alias_by_pom, None).keys())

        q_cf = q.casefold()

        def _rang_exacte(*codis):
            """0 si el que s'ha escrit ÉS un d'aquests codis. Es miren ELS DOS (casa i client):
            el tècnic pot escriure qualsevol dels dos i en tots dos casos vol aquella fila la
            primera. Amb el camp buit no hi ha res «exacte» a premiar."""
            if not q_cf:
                return 1
            return 0 if q_cf in {(c or '').casefold() for c in codis if c} else 1

        ordre_niv = {'item': 0, 'type': 1, 'cataleg': 2}

        def _fila(p, es_alies):
            camps = camps_de(alias_by_pom, p.id)
            fila = {
                'id': p.id,                       # ← el MATEIX pom_id per les dues portes
                'seccio': 'client' if es_alies else 'casa',
                'codi_client': p.codi_client,     # el codi de la CASA (v. `nomenclatura`)
                'nom_client': p.nom_client,
                'nom_ca': p.pom_global.nom_ca if p.pom_global_id else '',
                'nom_en': p.pom_global.nom_en if p.pom_global_id else '',
                'categoria_nom': p.categoria.nom_ca if p.categoria_id else '',
                'nivell': _nivell(p.id),
            }
            # LA FILA CANÒNICA VA SENSE CAP CAMP D'ÀLIES, i no és un descuit: si els portés, la
            # presentació tornaria a pintar-hi el codi del client a sobre — que és exactament el
            # defecte que això tanca. La fila de la casa és la casa.
            fila.update(camps if es_alies else {c: '' for c in CAMPS_ALIES})
            return fila

        pids_alies = list(dict.fromkeys(ids_alies))
        pids_canonic = list(dict.fromkeys(ids_canonic))
        per_id = {p.id: p for p in POMMaster.objects
                  .filter(id__in=set(pids_alies) | set(pids_canonic), actiu=True)
                  .select_related('pom_global', 'categoria')}

        sec_client = [_fila(per_id[i], True) for i in pids_alies if i in per_id]
        sec_casa = [_fila(per_id[i], False) for i in pids_canonic if i in per_id]
        # Es puntua i s'ordena DINS de cada secció: exacte primer, després la proximitat (el que
        # l'item ja declara va davant), i el codi desempata perquè l'ordre sigui estable.
        for seccio in (sec_client, sec_casa):
            seccio.sort(key=lambda r: (_rang_exacte(r['codi_client'], r.get('client_code')),
                                       ordre_niv[r['nivell']], (r['codi_client'] or '')))

        # ⚠️ **EL SOSTRE ES REPARTEIX ENTRE LES DUES SECCIONS.** Tallant la llista sencera, amb
        # el camp buit els 25 primers serien TOTS del client i la secció de la casa no existiria
        # mai: una secció buida per aritmètica del tall es llegeix com «aquí no hi ha res», que
        # és la mentida que aquest tram porta tres voltes tancant. Cada secció té la seva quota i
        # la que no l'omple cedeix el que li sobra a l'altra.
        quota = max(1, limit // 2)
        pren_client = min(len(sec_client), max(quota, limit - len(sec_casa)))
        pren_casa = min(len(sec_casa), limit - pren_client)
        data = sec_client[:pren_client] + sec_casa[:pren_casa]
        total = len(sec_client) + len(sec_casa)

        # `count` és el total REAL i `truncat` diu si el sostre ha tallat. Sense això, «no hi és»
        # i «no hi cabia» es deien igual — que és com es fabrica un duplicat. Ara cada SECCIÓ diu
        # també el seu, perquè amb dues poblacions un total sol no permet saber quina s'ha tallat.
        return Response({
            'results': data, 'count': total, 'truncat': total > len(data),
            'seccions': {
                'client': {'count': len(sec_client), 'mostrats': pren_client},
                'casa': {'count': len(sec_casa), 'mostrats': pren_casa},
            },
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# BASE SIZE: SAVE AND CONFIRM
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_base_size_view(request, model_id):
    """
    POST /api/v1/models/{id}/guardar-talla-base/
    Body: {
      "poms": [
        {"pom_id": 1, "valor_cm": 22.5, "tolerancia_minus": 0.5, "tolerancia_plus": 0.5},
        {"pom_id": 2, "valor_cm": 0}   ← value 0 = delete
      ]
    }
    Save BaseMeasurements. Does not close the base size.
    """
    poms_data = request.data.get('poms', [])
    if not poms_data:
        return Response({'error': 'Cal proporcionar almenys un POM'}, status=400)

    try:
        from fhort.models_app.models import Model, BaseMeasurement, MeasurementChangeLog
        from fhort.pom.models import POMMaster

        model = Model.objects.get(pk=model_id)
        sf_qs = model.size_fittings.filter(numero=1)
        if not sf_qs.exists():
            return Response({'error': 'No existeix Size & Fitting per a aquest model'}, status=400)
        sf = sf_qs.first()

        created = 0
        removed = 0
        # C3-A1 — el desat del wizard és UN acte: o entren tots els POMs del cos o no n'entra
        # cap. Aquest fitxer no tenia cap `atomic` i `ATOMIC_REQUESTS` no existeix
        # (settings.py:118-127), o sigui que cada POM del bucle es commitava per separat: una
        # petada al tercer deixava els dos primers escrits i el client sense saber-ho.
        with transaction.atomic():
            for item in poms_data:
                pom_id = item.get('pom_id')
                value = item.get('valor_cm', 0)

                if not pom_id:
                    continue

                if value is None or float(value) == 0:
                    # Materialització família→item: NO esborrar la fila (la pertinença de l'item es manté);
                    # buidar el valor (base_value_cm=None) deixant-la com a materialitzada sense valor.
                    #
                    # C3-A1 · LA CLAU COMPLETA. El filtre era `(model, pom_id)` sol: amb
                    # germanes vives buidava TOTES les files del POM, de qualsevol capa i
                    # qualsevol instància. Els eixos es declaren igual que al camí germà de
                    # sota, que ja ho feia.
                    bm = BaseMeasurement.objects.filter(
                        model=model, pom_id=pom_id,
                        # SET-2/T5 — i el garment. Sense ell, amb una segona peça viva el
                        # `.first()` triava a l'atzar: el `Meta.ordering` de `BaseMeasurement`
                        # (`['model','capa','ordre','pom']`) NO inclou ni la instància ni la
                        # peça, o sigui que el desempat el feia el pla de Postgres. Aquest
                        # camí escriu a la mare i ara ho diu.
                        capa=MeasurementLayer.SLUG_DEFECTE, instancia='', garment='',
                    ).first()
                    if bm is None:
                        continue
                    prev = bm.base_value_cm
                    if prev is not None:
                        bm.base_value_cm = None
                        bm._changed_by = request.user
                        bm.save(update_fields=['base_value_cm', 'updated_at'])
                        # El rastre s'escriu AQUÍ i no pel signal. Amb `base_value_cm=None` el
                        # receptor surt pel guard de `signals.py:290-291`, i la seva altra porta
                        # —la poda, gated per `_desactivat`— llegiria `valor_anterior` DESPRÉS
                        # del canvi: seria `None`, que en aquesta taula vol dir «és una creació»
                        # (models.py:842). En una taula append-only això és una fila que menteix
                        # i que ningú no podrà corregir després. S'escriu explícitament, com ja
                        # fan els dos escriptors d'override de talla no-base
                        # (models_app/views.py:2646 i :2820).
                        MeasurementChangeLog.objects.create(
                            model=model, pom_id=pom_id, base_measurement=bm,
                            capa=bm.capa, instancia=bm.instancia,
                            valor_anterior=float(prev), valor_nou=0.0,
                            context='manual', motiu='Wizard · valor de talla base buidat',
                            created_by=request.user,
                        )
                    removed += 1
                else:
                    # Sprint 5B.1: tolerance from the payload if present, else the catalogue POM.
                    pom = POMMaster.objects.filter(pk=pom_id).first()
                    tol_minus = item.get('tolerancia_minus')
                    tol_plus = item.get('tolerancia_plus')
                    if tol_minus is None and pom:
                        tol_minus = pom.tolerancia_default_minus
                    if tol_plus is None and pom:
                        tol_plus = pom.tolerancia_default_plus
                    # FASE_3/C1-ins — literals: el wizard encara no demana capa ni instància
                    # (Onada 3, amb maqueta). Declarats, no implícits.
                    BaseMeasurement.objects.update_or_create(
                        model=model,
                        pom_id=pom_id,
                        capa=MeasurementLayer.SLUG_DEFECTE,
                        instancia='',
                        # SET-2/T5 — declarat, no implícit (v. `_identitat_de_mesura`).
                        garment='',
                        defaults={
                            'base_value_cm': float(value),
                            'is_active': True,
                            'notes': item.get('notes', ''),
                            'tolerancia_minus': tol_minus,
                            'tolerancia_plus': tol_plus,
                        }
                    )
                    created += 1

        return Response({
            'creats_o_actualitzats': created,
            'eliminats': removed,
            'missatge': f'{created} POMs guardats, {removed} eliminats',
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error saving base size")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_base_size_view(request, model_id):
    """
    POST /api/v1/models/{id}/confirmar-talla-base/
    Validate that there are enough POMs and close the base size.
    Optionally generate the sizes if a GradingRuleSet is assigned.
    """
    try:
        from fhort.models_app.models import Model, BaseMeasurement
        from fhort.fitting.models import SizeFitting

        model = Model.objects.get(pk=model_id)
        sf = model.size_fittings.filter(numero=1).first()

        if not sf:
            return Response({'error': 'No existeix Size & Fitting per a aquest model'}, status=400)

        if sf.base_tancada:
            return Response({'error': 'La talla base ja està tancada'}, status=400)

        # Validate minimum number of POMs
        n_poms = BaseMeasurement.objects.filter(model=model, is_active=True).count()
        if n_poms < 3:
            return Response({
                'error': f'Cal tenir almenys 3 POMs amb mesures. Ara en tens {n_poms}.',
                'poms_actuals': n_poms,
            }, status=400)

        # Close the base size
        from django.utils import timezone
        sf.base_tancada = True
        sf.data_tancament_base = timezone.now()
        sf.estat = 'BaseTancada'
        sf.save(update_fields=['base_tancada', 'data_tancament_base', 'estat'])

        # Generate sizes if there is a grading_rule_set and size_run_model
        grading_generated = 0
        # G6-A/T2: `_te_regles` (residents O set), no el punter. Aquest caller es va quedar amb la
        # còpia vella del gate i saltava la graduació als models de regla resident, en silenci.
        if _te_regles(model) and model.size_run_model and model.base_size_label:
            try:
                from fhort.pom.services import generate_graded_specs
                grading_generated = generate_graded_specs(sf.id)
                sf.estat = 'TallesGenerades'
                sf.save(update_fields=['estat'])
            except SealedGradingVersionError as e:
                # G6-B/T1 · camí 6/6. Aquest `except Exception` de sota es limitava a fer un
                # WARNING i retornar 200: sobre una versió segellada, el rebuig del guard hauria
                # passat per un "no s'ha pogut graduar" al log i l'usuari hauria vist un OK. El
                # segell ha de ser visible a qui l'ha trobat, no només al fitxer de logs.
                return Response(e.payload, status=409)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Grading not generated: {e}")

        return Response({
            'missatge': 'Talla base confirmada correctament',
            'poms_confirmats': n_poms,
            'talles_generades': grading_generated,
            'estat_sf': sf.estat,
        })

    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error confirming base size")
        return Response({'error': str(e)}, status=500)


#: Últim recurs de tolerància de la casa. MATEIXA xifra que `pom.s10_views.TOL_FALLBACK` i
#: `patterns.views.TOL_FALLBACK`: una mesura no pot tenir una tolerància diferent segons quina
#: pantalla la miri. (DEUTE anotat, fora de scope: n'hi ha cinc còpies escampades.)
TOL_FALLBACK = 0.6


def _tol_vigent(de_la_mesura, del_cataleg):
    """La tolerància de la MESURA mana; la del catàleg és el pla B; 0.6 és l'últim recurs."""
    for v in (de_la_mesura, del_cataleg):
        if v is not None:
            return float(v)
    return TOL_FALLBACK


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def base_measurements_view(request, model_id):
    """
    GET /api/v1/models/{id}/base-measurements/
    Return the model's current BaseMeasurements with POM data.
    """
    try:
        from fhort.models_app.models import BaseMeasurement, Model
        from fhort.pom.nomenclatura import alies_per_pom

        # ⚠️ **AQUEST LECTOR LLENÇAVA L'ORDRE DE L'USUARI** (QA Agus 09/08). Ordenava per
        # `categoria + codi` —alfabètic—, i per tant una taula que la tècnica havia ordenat amb
        # el drag&drop del carril tornava a sortir per ordre de codi a la següent càrrega. La
        # feina d'ordenar-la no es perdia «de vegades»: es perdia SEMPRE, i en silenci.
        #
        # `ordre` mana, com a la resta de lectors de mesures (`views.py` 860, 1278, 1359, 1590) i
        # com la docstring de `base_measurements_reorder_view` ja donava per fet quan deia «totes
        # les taules llegeixen order_by('ordre')» — era cert a tot arreu menys aquí.
        # Categoria i codi es queden DARRERE, de desempat: amb `ordre` empatat (files nascudes
        # abans que la porta el desés, totes a 0) la llista segueix sent la d'abans i no balla.
        bms = BaseMeasurement.objects.filter(
            model_id=model_id, is_active=True
        ).select_related('pom', 'pom__pom_global', 'pom__categoria').order_by(
            'ordre', 'pom__categoria__display_order', 'pom__codi_client'
        )

        # F1 (cota viva) — àlies de client per pom_id, resolt amb UN sol prefetch (mai
        # find_pom_master per fila; l'N+1 està documentat a DIAGNOSI_COTES_POM_SKETCH.md
        # §B3). La tria determinista entre els diversos codis d'un client per al mateix POM
        # viu ara a `pom.nomenclatura`, compartida amb el wizard de definició de POMs i la
        # taula de Mesures: hi havia una còpia per superfície. NOMÉS LECTURA.
        customer_id = Model.objects.filter(
            id=model_id).values_list('customer_id', flat=True).first()
        alias_by_pom = {
            pom_id: a['client_code'] for pom_id, a in alies_per_pom(customer_id).items()}

        # F1 — la REGLA RESIDENT del model (ModelGradingRule), per pom_id. La T1a de la fitxa
        # necessita `increment_base` + `talla_break_label` per POM, i fins ara els llegia
        # NOMÉS de `grading-rules/?rule_set=<model.grading_rule_set>`: amb el ruleset a NULL
        # (graduació resident, el cas normal d'un model importat) la crida sortia amb `null`
        # a la URL i la taula naixia sense columna de regla. S'exposen aquí, al costat de la
        # base, perquè és la mateixa unitat de lectura (una fila per POM del model) i no cal
        # cap endpoint nou. Batch: un sol query, mai per fila.
        # Precedència a la fitxa: si el model TÉ ruleset, el consumidor segueix el camí del
        # ruleset; aquest camp és el que el substitueix quan no n'hi ha.
        from fhort.models_app.models import ModelGradingRule
        # SET-2/#12d — LA CLAU DE LA REGLA PORTA LA PRENDA, i aquí el dany era pitjor que a
        # l'escriptor. `{r.pom_id: ...}` és un col·lapse: amb la mare i la 02 amb regla pròpia
        # sobre el mateix POM, el diccionari en perdia una —guanyava l'última que retornés el
        # planner— i les DUES files ensenyaven la mateixa llei, sense cap avís. És el mode de
        # fallada que `_load_grading_rules` tenia abans de T4 i que la comporta de T3 existia
        # per fer impossible; amb la comporta fora, tornava a ser assolible.
        regla_by_pom = {
            (r.pom_id, r.garment): {
                'logica': r.logica,
                'increment_base': r.increment_base,
                'increment_break': r.increment_break,
                'talla_break_label': r.talla_break_label or '',
                'origen': r.origen,
            }
            for r in ModelGradingRule.objects.filter(model_id=model_id, actiu=True)
        }

        def _regla_de(pom_id, garment):
            """La llei d'una fila: la SEVA si en té, i si no la de la mare (D5-bis).

            «No en té» i «té la mateixa» no són el mateix estat —l'un es pot estrenar, l'altre
            ja s'ha decidit— i la pantalla ha de poder distingir-los per dir si el que ensenya
            és propi o heretat. Per això el `heretat` viatja DINS de l'objecte i no s'endevina
            comparant valors, que és el que obligaria a fer si només s'hi servís la llei.
            """
            propia = regla_by_pom.get((pom_id, garment))
            if propia is not None:
                return {**propia, 'heretat': False}
            if garment:
                mare = regla_by_pom.get((pom_id, ''))
                if mare is not None:
                    return {**mare, 'heretat': True}
            return None

        data = [{
            'id': bm.id,
            'pom_id': bm.pom_id,
            # C4/BLOC 1-BIS — ELS DOS EIXOS AL CONTRACTE. El queryset d'aquesta vista mai no
            # ha filtrat per capa ni per instància: ja servia les germanes. El que no feia era
            # dir de quina és cadascuna, i sense això `pom_id` no és una clau dins de
            # `results`.
            #
            # Aquest endpoint alimenta TOT l'editor de fitxa (`TechSheetEditor.pomRows`), que
            # hi munta mapes per `pom_id` per re-derivar l'etiqueta de les cotes vives i per
            # col·locar-ne de noves. `new Map(...)` es queda l'ÚLTIMA entrada de cada clau: amb
            # dues germanes, una cota es rellegia amb el nom de la que la consulta hagués
            # retornat després —desempat del planner, no del document— i el primer desat de
            # debò l'escrivia al `.ftt`.
            #
            # No s'hi afegeix cap identificador de fila: `id` (aquí sobre) JA és la PK del
            # BaseMeasurement.
            'capa': bm.capa,
            # SET-2/#12d — EL TERCER EIX AL CONTRACTE, i pel mateix argument que els dos de
            # sobre: aquesta vista mai no ha filtrat per prenda —ja servia les files de totes—
            # i el que no feia era dir de quina és cadascuna. Amb `TechSheetEditor.pomRows`
            # muntant `new Map(...)` per `pom_id`, dues files de prendes diferents es
            # trepitgen exactament igual que s'hi trepitjaven les germanes de capa abans de C4.
            'garment': bm.garment,
            'instancia': bm.instancia,
            # F1: la regla resident d'aquesta fila (None si no en té ni n'hereta cap).
            # SET-2/#12d: la SEVA si en té, la de la mare si no (D5-bis), i ho diu (`heretat`).
            'regla_model': _regla_de(bm.pom_id, bm.garment),
            'codi_client': bm.pom.codi_client,
            'nom_client': bm.pom.nom_client,
            'nom_ca': bm.pom.pom_global.nom_ca if bm.pom.pom_global_id else '',
            # `nom_en` és el nom CANÒNIC del sector: el parell "anglès primari + local al
            # costat" (PomNamePair) no es pot muntar sense ell, i fins ara els consumidors
            # d'aquest endpoint se l'havien d'anar a buscar a la GradingRule.
            'nom_en': bm.pom.pom_global.nom_en if bm.pom.pom_global_id else '',
            # Sprint NOMS-POM (30/07) — el BATEIG d'aquest model (nom canònic + traducció del
            # client), CRU. '' = no batejat → qui llegeix cau al catàleg (`nom_en`/`nom_ca`),
            # que segueixen exactament igual que abans. Camps NOUS, res existent no es toca.
            'nom_canonic_model': bm.nom_canonic_model or '',
            'nom_traduit_model': bm.nom_traduit_model or '',
            'categoria_nom': bm.pom.categoria.nom_ca if bm.pom.categoria_id else '',
            'base_value_cm': bm.base_value_cm,
            # Tolerància VIGENT (ja resolta), no la columna crua: qui la consumeix pinta una
            # cel·la, no ha de refer la cascada. Mateix criteri que `base_stages_view._tol`
            # (models_app/views.py) i `patterns/views._tol` — la de la MESURA mana, la del
            # catàleg és el pla B, 0.6 és l'últim recurs.
            'tol_minus': _tol_vigent(bm.tolerancia_minus, bm.pom.tolerancia_default_minus),
            'tol_plus': _tol_vigent(bm.tolerancia_plus, bm.pom.tolerancia_default_plus),
            'notes': bm.notes or '',
            # QUAN es va escriure aquesta base, i és la peça que faltava per poder DATAR la
            # taula de mesures base de la fitxa tècnica. La llei del domini és que l'última
            # mesura escrita és la veritat —temporal, no d'origen—: `base_value_cm` ja porta
            # l'últim fit vàlid (`consolidate_base_from_fitting`), i sense saber de QUAN és,
            # la fila de títol de la fitxa hauria d'anar muda o amb una data inventada, que en
            # un document que va al fabricant és pitjor. Camp del model (`auto_now`), servit
            # des del mateix `bms`: ZERO queries de més, cap camp existent tocat.
            'updated_at': bm.updated_at.isoformat() if bm.updated_at else None,
            'nom_fitxa': bm.nom_fitxa or '',
            'origen': bm.origen or '',
            # F3 — secció d'origen ('01.- DRESS', 'Bodice:'…). '' quan el document no en
            # tenia. La fitxa tècnica la fa servir per partir la taula en una per peça.
            'seccio': bm.seccio or '',
            # ⚠️ AQUÍ HI DEIA «per això no hi ha cap clau `garment`» (SET-2/T9, 10/08) I FA
            # TEMPS QUE ÉS FALS: la clau hi és, trenta línies més amunt (`'garment': bm.garment`),
            # posada per SET-2/F1 quan es va obrir el camí d'escriure mesures per peça. Es
            # corregeix i no s'hi deixa: aquest comentari, llegit per sobre, va fer concloure a
            # una diagnosi que aquesta font no servia l'eix —i per poc no fa néixer un endpoint
            # nou per a la taula de mesures base de la fitxa (Q8e). Un comentari datat no descriu
            # el codi d'avui: el COS de la funció, sí.
            'pom_abbreviation': bm.pom.pom_global.abbreviation if bm.pom.pom_global_id else '',
            'pom_code_global': bm.pom.pom_global.codi if bm.pom.pom_global_id else '',
            'pom_is_key': bool(bm.pom.pom_global.is_key) if bm.pom.pom_global_id else False,
            # F1 (cota viva): nomenclatura del client per a l'etiqueta de la cota, o None.
            'client_alias': alias_by_pom.get(bm.pom_id),
        } for bm in bms]

        return Response({'count': len(data), 'results': data})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# CREATE NEW TENANT POM
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_tenant_pom_view(request):
    """
    POST /api/v1/poms/crear-tenant/
    Create a new tenant POM (without an associated POMGlobal, or with a new one).
    Body: {
      codi_client, nom_client, categoria_id,
      descripcio (optional), notes (optional)
    }

    ── S45/D · AQUESTA ÉS LA PORTA DEL CATÀLEG PELAT ────────────────────────────────────
    Fins ara existia i **no la cridava ningú** (`endpoints.js:254`, `poms.crearTenant`, zero
    cridadors). El POMBrowser —645 POMs, cercador, assignar, treure, KEY, reordenar— no tenia
    cap botó de crear, i l'única alta de POM del producte era la del MODEL
    (`create_model_pom_view`, via `EditableTable`), que exigeix `modelId`.

    LES DUES PORTES NO FAN EL MATEIX, I ÉS DELIBERAT:
      · `pom-propi/<model>` neix amb `CustomerPOMAlias` (existeix PER A UN CLIENT), amb
        `pendent_revisio=True` i `origen_import='model:<codi>'`: l'ha creat un tècnic amb un
        model al davant i el catàleg encara no l'ha beneït.
      · AQUESTA neix SOLA al catàleg del tenant: sense àlies, sense GTI, sense sembra, sense
        `pom_global`. Vincular-la a un ítem és el flux ASSIGN que el POMBrowser ja té, i
        promoure-la a canònica és feina de backoffice. Un POM del catàleg no és un POM
        «pendent»: és el que hi ha, i per això NO neix `pendent_revisio`.
    """
    code = request.data.get('codi_client', '').strip()
    name = request.data.get('nom_client', '').strip()
    categoria_id = request.data.get('categoria_id')

    if not code or not name:
        return Response({'error': 'codi_client i nom_client són obligatoris'}, status=400)

    try:
        from fhort.pom.models import POMMaster

        # 🚨 S45/D — LA COMPROVACIÓ ANAVA EN MINÚSCULES I MAJÚSCULES, I LA CONSTRAINT NO.
        # El predicat era `filter(codi_client=code)` (exacte) i la unicitat de la BD és
        # CASE-INSENSITIVE (`uniq_pommaster_codi_client_ci`, `pom/models.py:421`). Amb «CF»
        # al catàleg, crear «cf» passava aquest `if`, petava contra la constraint, queia a
        # l'`except Exception` de sota i sortia per la finestra com un **500 amb el text cru
        # del driver**. El guard ha de mirar el que mira la BD o no és un guard: és un 500
        # amb passos previs.
        if POMMaster.objects.filter(codi_client__iexact=code).exists():
            return Response({'error': f'Ja existeix un POM amb codi {code}'}, status=400)

        pom = POMMaster.objects.create(
            codi_client=code,
            nom_client=name,
            categoria_id=categoria_id,
            notes=request.data.get('notes', ''),
            # Sense `pom_global`: catàleg de TENANT. El pont amb els 290 `POMGlobal` de
            # `public` és una decisió de la casa, no un efecte secundari d'aquest formulari.
            # La traça diu d'on ve, com a la resta d'altes de catàleg (l'import hi posa el
            # token de sessió; el model, `model:<codi>`).
            origen_import='cataleg',
            actiu=True,
        )

        return Response({
            'id': pom.id,
            'codi_client': pom.codi_client,
            'nom_client': pom.nom_client,
            'missatge': f'POM {code} creat correctament',
        }, status=201)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_model_pom_view(request, model_id):
    """POST /api/v1/models/<model_id>/pom-propi/ — CREAR POM PROPI DEL MODEL.

    Body: {nom, nomenclatura, categoria_id?, descripcio_local?}

    EL GEST QUE FALTAVA. La llei diu que els POMs es van a buscar al catàleg del client i que no
    s'encunyen codis lliures — però un model pot necessitar una mesura que el catàleg encara no
    té («Height sequins piece», el cas real del MILEY). Sense una porta explícita, aquesta
    necessitat es colava per on podia: l'import agafava el codi del document tal qual i creava un
    POM orfe, i així va néixer el POM 440 amb `codi_client='U1'` quan Brownie ja tenia
    `U1 → 342 Button spacing`. La feina d'aquesta vista és que aquell camí ja no calgui i que el
    que abans passava en silenci ara passi amb nom, nomenclatura i validació.

    EL POM NEIX AL CATÀLEG DEL CLIENT, no en un limbe (decisió d'Agus, 06/08). Es crea el
    `POMMaster` i, sobretot, el `CustomerPOMAlias` amb `origen='MODEL'`: és el que el fa
    EXISTIR per al client. Conseqüència volguda i acceptada — la validació de col·lisió el veurà
    a partir d'ara, i un altre model del mateix client el podrà reutilitzar des del cercador.
    Això és coneixement del client acumulant-se, que és el que ha de passar.

    NO es toca `POMMaster`: cap camp nou, cap FK a una app SHARED. «Del model» és la provinença
    de l'àlies, no una columna del catàleg de la casa.
    """
    from django.db import transaction
    from fhort.models_app.models import Model
    from fhort.pom.models import CustomerPOMAlias, POMMaster
    from fhort.pom.nomenclatura import colisio_de_codi

    nom = (request.data.get('nom') or '').strip()
    codi = (request.data.get('nomenclatura') or '').strip()
    if not nom or not codi:
        return Response({'error': 'nom i nomenclatura són obligatoris',
                         'codi': 'CAMPS_OBLIGATORIS'}, status=400)

    model = Model.objects.filter(pk=model_id).values('id', 'customer_id', 'codi_intern').first()
    if not model:
        return Response({'error': 'Model no trobat'}, status=404)
    customer_id = model['customer_id']
    if not customer_id:
        # Sense client no hi ha catàleg de client on posar-lo, i inventar-ne un seria tornar al
        # POM orfe que aquesta vista existeix per evitar.
        return Response({'error': 'Aquest model no té client assignat',
                         'codi': 'MODEL_SENSE_CLIENT'}, status=400)

    # ── LA VALIDACIÓ DE COL·LISIÓ ──────────────────────────────────────────────────────────
    # «U1 hauria estat rebutjat: U1 és BUTTON SPACING al catàleg Brownie». 409 i no 400 perquè
    # no és un camp mal escrit: és un conflicte amb una dada que ja hi és, i el que la persona
    # necessita saber és AMB QUÈ xoca per triar un altre codi.
    xoc, etiqueta = colisio_de_codi(customer_id, codi)
    if xoc is not None:
        return Response({
            'codi': 'NOMENCLATURA_OCUPADA',
            'nomenclatura': codi,
            'pom_id': xoc.pk,
            'pom_nom': etiqueta,
            'message': f'«{codi}» ja és {etiqueta} al catàleg d\'aquest client.',
        }, status=409)

    # ── EL CODI DE LA COTA VA NET, I SI ESTÀ OCUPAT ES DIU ─────────────────────────────────
    #
    # ⚠️ Aquí es qualificava el codi amb el del client quan la casa ja el tenia: `EK` ocupat →
    # la cota naixia com a **`BRW-EK`**. Està prohibit (Agus, 09/08): **el prefix de client
    # pertany a la FITXA —a l'àlies, que ja hi és— i mai a la nomenclatura de la cota**. Un codi
    # de casa qualificat amb un client és una tercera nomenclatura que ningú no ha demanat, i es
    # llegeix a totes les pantalles com si formés part del nom de la mesura.
    #
    # Però el prefix no era estètica: tapava la constraint `uniq_pommaster_codi_client_ci`. Sense
    # ell, `POMMaster.objects.create` peta amb IntegrityError i la persona rep un 500 sense saber
    # per què. Així que la sortida no és inventar un codi: és **DIR AMB QUÈ XOCA**, que és el
    # mateix consentiment informat que ja fa la validació de sobre contra el catàleg del client.
    #
    # I és la resposta ÚTIL, perquè el cas real és aquest: `EK · Neck width` ja existia i el
    # cercador no el trobava (el mínim de dos caràcters i la cerca només per àlies). Qui arriba
    # aquí amb un codi ocupat, la immensa majoria de vegades, està a punt de duplicar un POM que
    # ja hi és — i el que necessita no és un codi nou, és que li ensenyin l'existent.
    codi_casa = codi[:30]
    ja_hi_es = POMMaster.objects.filter(codi_client__iexact=codi_casa).first()
    if ja_hi_es is not None:
        etiqueta_casa = (ja_hi_es.nom_client or codi_casa).strip()
        return Response({
            'codi': 'CODI_CASA_OCUPAT',
            'nomenclatura': codi,
            'pom_id': ja_hi_es.pk,
            'pom_nom': etiqueta_casa,
            'message': f'«{codi}» ja és {etiqueta_casa} al catàleg. Fes-lo servir des del '
                       f'cercador, o dona-li una nomenclatura diferent.',
        }, status=409)

    with transaction.atomic():
        pom = POMMaster.objects.create(
            codi_client=codi_casa,
            nom_client=nom,
            categoria_id=request.data.get('categoria_id'),
            # Neix PENDENT DE REVISIÓ a posta: l'ha creat un tècnic amb un model al davant, no
            # el responsable del catàleg. És bo per treballar i encara no està consolidat.
            pendent_revisio=True,
            # LA REFERÈNCIA D'ORIGEN VA A `origen_import`, NO A `notes` (Agus, 06/08).
            #
            # Són dos senyals amb dos lectors, i cadascun al seu camp:
            #   · `CustomerPOMAlias.origen='MODEL'` = PROVINENÇA, permanent. La llegeix el
            #     cercador i qui pregunti d'on va sortir aquest àlies. Es queda per sempre.
            #   · `POMMaster.pendent_revisio` = ESTAT DE REVISIÓ, transitori. El neteja la
            #     Montse quan revisa, i llavors `origen='MODEL'` es queda com a història.
            #
            # `origen_import` és el camp fet per a això —el seu `help_text` diu literalment
            # «Referència del model/fitxa des d'on s'ha creat aquest POM»— i és el que l'import
            # ja omple (`extraction_views.py:1879`, amb el token de la sessió). Amb la referència
            # a `notes` la cua de la Montse hauria de distingir «nascut d'un import» de «nascut
            # d'un model» fent cerca de text lliure; amb el camp, mira UN lloc i sap quin és quin.
            origen_import=f'model:{model["codi_intern"] or model_id}',
            notes='',
            actiu=True,
        )
        CustomerPOMAlias.objects.create(
            customer_id=customer_id,
            pom=pom,
            client_code=codi,
            description_en=nom,
            description_local=(request.data.get('descripcio_local') or '').strip(),
            origen='MODEL',
            pendent_revisio=True,
        )

    # Mateixa forma que un resultat de `poms/cerca/`: qui l'ha creat el vol afegir a la taula tot
    # seguit, i hauria de poder-ho fer sense una segona petició ni una segona forma de dada.
    return Response({
        'id': pom.id,
        'codi_client': pom.codi_client,
        'nom_client': pom.nom_client,
        'nom_ca': '', 'nom_en': '',
        'categoria_nom': pom.categoria.nom_ca if pom.categoria_id else '',
        'nivell': 'model',
        'client_code': codi,
        'client_name_en': nom,
        'client_name_local': (request.data.get('descripcio_local') or '').strip(),
    }, status=201)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_pom_nomenclature_view(request, pom_id):
    """
    PATCH /api/v1/poms/{id}/nomenclatura/
    Edit a tenant POM's codi_client and nom_client.
    """
    try:
        from fhort.pom.models import POMMaster
        pom = POMMaster.objects.get(pk=pom_id)

        if 'codi_client' in request.data:
            pom.codi_client = request.data['codi_client'].strip()
        if 'nom_client' in request.data:
            pom.nom_client = request.data['nom_client'].strip()
        pom.save(update_fields=['codi_client', 'nom_client'])

        return Response({
            'id': pom.id,
            'codi_client': pom.codi_client,
            'nom_client': pom.nom_client,
        })
    except POMMaster.DoesNotExist:
        return Response({'error': 'POM no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
