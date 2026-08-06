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
    GET /api/v1/poms/cerca/?q=chest
    Search POMs in the tenant catalog by code or name.
    Return max 20 results for autocomplete.
    """
    q = request.query_params.get('q', '').strip()
    if len(q) < 2:
        return Response({'results': []})

    try:
        from fhort.pom.models import CustomerPOMAlias, POMMaster
        from django.db.models import Q

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
        # Amb `?model=` (el cas del cercador de Definició POM) la cerca passa a resoldre contra
        # els àlies del client D'AQUEST MODEL: el seu codi, la seva descripció internacional i
        # la seva descripció local. Això no és un filtre a sobre del catàleg de la casa —és una
        # altra pregunta: «quines mesures coneix aquest client?».
        #
        # Sense `?model=` es manté el comportament de sempre (catàleg del tenant): hi ha
        # superfícies que cerquen sense model al davant i no tenen client de qui parlar.
        model_id = request.query_params.get('model')
        customer_id = None
        if model_id:
            from fhort.models_app.models import Model as ModelPeça
            customer_id = (ModelPeça.objects.filter(pk=model_id)
                           .values_list('customer_id', flat=True).first())

        if customer_id:
            # Els POMs que aquest client anomena d'alguna manera que casa amb `q`. Un client pot
            # tenir diversos codis per al mateix POM (la unicitat és (customer, client_code)),
            # així que es dedupliquen per `pom_id` conservant l'ordre d'aparició.
            alias_hits = (CustomerPOMAlias.objects
                          .filter(customer_id=customer_id, pom__isnull=False)
                          .filter(Q(client_code__icontains=q) |
                                  Q(description_en__icontains=q) |
                                  Q(description_local__icontains=q))
                          .order_by('pendent_revisio', 'client_code')
                          .values_list('pom_id', flat=True))
            ids = list(dict.fromkeys(alias_hits))[:20]
            poms = list(POMMaster.objects.filter(id__in=ids, actiu=True)
                        .select_related('pom_global', 'categoria'))
        else:
            poms = list(POMMaster.objects.filter(
                actiu=True
            ).filter(
                Q(codi_client__icontains=q) |
                Q(nom_client__icontains=q) |
                Q(pom_global__nom_ca__icontains=q) |
                Q(pom_global__nom_en__icontains=q)
            ).select_related('pom_global', 'categoria')[:20])

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

        # LA NOMENCLATURA QUE ES PINTA ÉS LA DEL CLIENT. El cercador ensenyava `codi_client` de
        # `POMMaster` sota el rètol «del catàleg del client», i és el codi de la CASA: el tècnic
        # de Brownie veia «CH» on el seu document diu «A». Els tres camps d'àlies els resol el
        # mateix `alies_per_pom`/`camps_de` que la resta de superfícies —una sola font— i queden
        # buits si el POM no té àlies d'aquest client (llavors mana el catàleg, com sempre).
        from fhort.pom.nomenclatura import alies_per_pom, camps_de
        alias_by_pom = alies_per_pom(customer_id)

        data = [{
            'id': p.id,
            'codi_client': p.codi_client,
            'nom_client': p.nom_client,
            'nom_ca': p.pom_global.nom_ca if p.pom_global_id else '',
            'nom_en': p.pom_global.nom_en if p.pom_global_id else '',
            'categoria_nom': p.categoria.nom_ca if p.categoria_id else '',
            'nivell': _nivell(p.id),
            **camps_de(alias_by_pom, p.id),
        } for p in poms]

        # L'ordre és el de PROXIMITAT: el que l'item ja declara primer. Qui busca «C» a la taula
        # d'un jersei vol la seva cintura, no la d'una americana que comparteix catàleg.
        ordre = {'item': 0, 'type': 1, 'cataleg': 2}
        data.sort(key=lambda r: (ordre[r['nivell']], (r['codi_client'] or '')))

        return Response({'results': data})
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
                        capa=MeasurementLayer.SLUG_DEFECTE, instancia='',
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

        bms = BaseMeasurement.objects.filter(
            model_id=model_id, is_active=True
        ).select_related('pom', 'pom__pom_global', 'pom__categoria').order_by(
            'pom__categoria__display_order', 'pom__codi_client'
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
        regla_by_pom = {
            r.pom_id: {
                'logica': r.logica,
                'increment_base': r.increment_base,
                'increment_break': r.increment_break,
                'talla_break_label': r.talla_break_label or '',
                'origen': r.origen,
            }
            for r in ModelGradingRule.objects.filter(model_id=model_id, actiu=True)
        }

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
            'instancia': bm.instancia,
            # F1: la regla resident d'aquest POM (None si el model no en té cap).
            'regla_model': regla_by_pom.get(bm.pom_id),
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
            'nom_fitxa': bm.nom_fitxa or '',
            'origen': bm.origen or '',
            # F3 — secció d'origen ('01.- DRESS', 'Bodice:'…). '' quan el document no en
            # tenia. La fitxa tècnica la fa servir per partir la taula en una per peça.
            'seccio': bm.seccio or '',
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
    """
    code = request.data.get('codi_client', '').strip()
    name = request.data.get('nom_client', '').strip()
    categoria_id = request.data.get('categoria_id')

    if not code or not name:
        return Response({'error': 'codi_client i nom_client són obligatoris'}, status=400)

    try:
        from fhort.pom.models import POMMaster

        if POMMaster.objects.filter(codi_client=code).exists():
            return Response({'error': f'Ja existeix un POM amb codi {code}'}, status=400)

        pom = POMMaster.objects.create(
            codi_client=code,
            nom_client=name,
            categoria_id=categoria_id,
            notes=request.data.get('notes', ''),
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
