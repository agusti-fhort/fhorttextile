"""
fhort/pom/wizard_views.py
Endpoints for the Design Freeze + Base Size wizard flow.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone


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
        if model.grading_rule_set_id and model.size_run_model and model.base_size_label:
            try:
                from fhort.pom.services import generate_graded_specs
                grading_generated = generate_graded_specs(sf.id)
                sf.estat = 'TallesGenerades'
                sf.save(update_fields=['estat'])
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def base_measurements_view(request, model_id):
    """
    GET /api/v1/models/{id}/base-measurements/
    Return the model's current BaseMeasurements with POM data.
    """
    try:
        from fhort.models_app.models import BaseMeasurement

        bms = BaseMeasurement.objects.filter(
            model_id=model_id, is_active=True
        ).select_related('pom', 'pom__pom_global', 'pom__categoria').order_by(
            'pom__categoria__display_order', 'pom__codi_client'
        )

        data = [{
            'id': bm.id,
            'pom_id': bm.pom_id,
            'codi_client': bm.pom.codi_client,
            'nom_client': bm.pom.nom_client,
            'nom_ca': bm.pom.pom_global.nom_ca if bm.pom.pom_global_id else '',
            'categoria_nom': bm.pom.categoria.nom_ca if bm.pom.categoria_id else '',
            'base_value_cm': bm.base_value_cm,
            'notes': bm.notes or '',
            'nom_fitxa': bm.nom_fitxa or '',
            'origen': bm.origen or '',
            'pom_abbreviation': bm.pom.pom_global.abbreviation if bm.pom.pom_global_id else '',
            'pom_code_global': bm.pom.pom_global.codi if bm.pom.pom_global_id else '',
            'pom_is_key': bool(bm.pom.pom_global.is_key) if bm.pom.pom_global_id else False,
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
