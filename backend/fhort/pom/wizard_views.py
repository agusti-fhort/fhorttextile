"""
fhort/pom/wizard_views.py
Endpoints for the Design Freeze + Base Size wizard flow.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

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
        from fhort.pom.models import POMMaster
        from django.db.models import Q

        poms = POMMaster.objects.filter(
            actiu=True
        ).filter(
            Q(codi_client__icontains=q) |
            Q(nom_client__icontains=q) |
            Q(pom_global__nom_ca__icontains=q) |
            Q(pom_global__nom_en__icontains=q)
        ).select_related('pom_global', 'categoria')[:20]

        data = [{
            'id': p.id,
            'codi_client': p.codi_client,
            'nom_client': p.nom_client,
            'nom_ca': p.pom_global.nom_ca if p.pom_global_id else '',
            'nom_en': p.pom_global.nom_en if p.pom_global_id else '',
            'categoria_nom': p.categoria.nom_ca if p.categoria_id else '',
        } for p in poms]

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
        from fhort.models_app.models import Model, BaseMeasurement
        from fhort.pom.models import POMMaster

        model = Model.objects.get(pk=model_id)
        sf_qs = model.size_fittings.filter(numero=1)
        if not sf_qs.exists():
            return Response({'error': 'No existeix Size & Fitting per a aquest model'}, status=400)
        sf = sf_qs.first()

        created = 0
        removed = 0
        for item in poms_data:
            pom_id = item.get('pom_id')
            value = item.get('valor_cm', 0)

            if not pom_id:
                continue

            if value is None or float(value) == 0:
                # Materialització família→item: NO esborrar la fila (la pertinença de l'item es manté);
                # buidar el valor (base_value_cm=None) deixant-la com a materialitzada sense valor.
                cleared = BaseMeasurement.objects.filter(
                    model=model, pom_id=pom_id
                ).update(base_value_cm=None)
                removed += cleared
            else:
                # Sprint 5B.1: tolerance from the payload if present, else the catalogue POM.
                pom = POMMaster.objects.filter(pk=pom_id).first()
                tol_minus = item.get('tolerancia_minus')
                tol_plus = item.get('tolerancia_plus')
                if tol_minus is None and pom:
                    tol_minus = pom.tolerancia_default_minus
                if tol_plus is None and pom:
                    tol_plus = pom.tolerancia_default_plus
                BaseMeasurement.objects.update_or_create(
                    model=model,
                    pom_id=pom_id,
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
