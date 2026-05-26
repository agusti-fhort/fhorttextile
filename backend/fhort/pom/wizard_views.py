"""
fhort/pom/wizard_views.py
Endpoints per al flux de Design Freeze + Talla Base wizard.
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
def aprovar_design_freeze_view(request, model_id):
    """
    POST /api/v1/models/{id}/aprovar-design-freeze/
    El tècnic aprova el Design Freeze del model.
    No requereix mesures — és una aprovació visual/conceptual.
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
# POMs SUGGERITS PER GARMENT TYPE
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def poms_suggerits_view(request):
    """
    GET /api/v1/poms/suggerits/?garment_type=X
    Retorna els POMs suggerits per a un garment_type,
    amb la nomenclatura del tenant (codi_client, nom_client).
    Si no hi ha GarmentPOMMap, retorna tots els POMs actius del tenant.
    """
    garment_type_id = request.query_params.get('garment_type')

    try:
        from fhort.pom.models import POMMaster, GarmentPOMMap, GarmentType

        # Intentar carregar des de GarmentPOMMap (no té flag is_active al schema;
        # cada entrada del mapping es considera vàlida per al seu garment_type).
        if garment_type_id:
            mapped_pom_ids = GarmentPOMMap.objects.filter(
                garment_type_id=garment_type_id,
            ).values_list('pom_id', flat=True)

            if mapped_pom_ids:
                poms = POMMaster.objects.filter(
                    id__in=mapped_pom_ids,
                    actiu=True,
                ).select_related('categoria', 'pom_global').order_by(
                    'categoria__display_order', 'codi_client'
                )
            else:
                # Fallback: tots els POMs del tenant
                poms = POMMaster.objects.filter(actiu=True).select_related(
                    'categoria', 'pom_global'
                ).order_by('categoria__display_order', 'codi_client')
        else:
            poms = POMMaster.objects.filter(actiu=True).select_related(
                'categoria', 'pom_global'
            ).order_by('categoria__display_order', 'codi_client')

        data = []
        for pom in poms:
            data.append({
                'id': pom.id,
                'codi_client': pom.codi_client,
                'nom_client': pom.nom_client,
                'nom_global_ca': pom.pom_global.nom_ca if pom.pom_global_id else '',
                'nom_global_en': pom.pom_global.nom_en if pom.pom_global_id else '',
                'categoria_id': pom.categoria_id,
                'categoria_nom': pom.categoria.nom_ca if pom.categoria_id else '',
                'categoria_ordre': pom.categoria.display_order if pom.categoria_id else 99,
                'is_key_measure': False,
                'unitat': pom.pom_global.unitat if pom.pom_global_id else 'cm',
            })

        return Response({'count': len(data), 'results': data})

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error carregant POMs suggerits")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cerca_poms_view(request):
    """
    GET /api/v1/poms/cerca/?q=chest
    Cerca POMs al catàleg del tenant per codi o nom.
    Retorna max 20 resultats per a l'autocomplet.
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
# TALLA BASE: GUARDAR I CONFIRMAR
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def guardar_talla_base_view(request, model_id):
    """
    POST /api/v1/models/{id}/guardar-talla-base/
    Body: {
      "poms": [
        {"pom_id": 1, "valor_cm": 22.5, "tolerancia_minus": 0.5, "tolerancia_plus": 0.5},
        {"pom_id": 2, "valor_cm": 0}   ← valor 0 = eliminar
      ]
    }
    Guarda BaseMeasurements. No tanca la talla base.
    """
    poms_data = request.data.get('poms', [])
    if not poms_data:
        return Response({'error': 'Cal proporcionar almenys un POM'}, status=400)

    try:
        from fhort.models_app.models import Model, BaseMeasurement

        model = Model.objects.get(pk=model_id)
        sf_qs = model.size_fittings.filter(numero=1)
        if not sf_qs.exists():
            return Response({'error': 'No existeix Size & Fitting per a aquest model'}, status=400)
        sf = sf_qs.first()

        creats = 0
        eliminats = 0
        for item in poms_data:
            pom_id = item.get('pom_id')
            valor = item.get('valor_cm', 0)

            if not pom_id:
                continue

            if valor is None or float(valor) == 0:
                # Eliminar si existeix
                deleted, _ = BaseMeasurement.objects.filter(
                    model=model, pom_id=pom_id
                ).delete()
                eliminats += deleted
            else:
                BaseMeasurement.objects.update_or_create(
                    model=model,
                    pom_id=pom_id,
                    defaults={
                        'base_value_cm': float(valor),
                        'is_active': True,
                        'notes': item.get('notes', ''),
                    }
                )
                creats += 1

        return Response({
            'creats_o_actualitzats': creats,
            'eliminats': eliminats,
            'missatge': f'{creats} POMs guardats, {eliminats} eliminats',
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Error guardant talla base")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirmar_talla_base_view(request, model_id):
    """
    POST /api/v1/models/{id}/confirmar-talla-base/
    Valida que hi ha prou POMs i tanca la talla base.
    Opcionalment genera les talles si hi ha GradingRuleSet assignat.
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

        # Validar mínim de POMs
        n_poms = BaseMeasurement.objects.filter(model=model, is_active=True).count()
        if n_poms < 3:
            return Response({
                'error': f'Cal tenir almenys 3 POMs amb mesures. Ara en tens {n_poms}.',
                'poms_actuals': n_poms,
            }, status=400)

        # Tancar talla base
        from django.utils import timezone
        sf.base_tancada = True
        sf.data_tancament_base = timezone.now()
        sf.estat = 'BaseTancada'
        sf.save(update_fields=['base_tancada', 'data_tancament_base', 'estat'])

        # Generar talles si hi ha grading_rule_set i size_run_model
        grading_generated = 0
        if model.grading_rule_set_id and model.size_run_model and model.base_size_label:
            try:
                from fhort.pom.services import generar_graded_specs
                grading_generated = generar_graded_specs(sf.id)
                sf.estat = 'TallesGenerades'
                sf.save(update_fields=['estat'])
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Grading no generat: {e}")

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
        logging.getLogger(__name__).exception("Error confirmant talla base")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def base_measurements_view(request, model_id):
    """
    GET /api/v1/models/{id}/base-measurements/
    Retorna les BaseMeasurements actuals del model amb dades del POM.
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
        } for bm in bms]

        return Response({'count': len(data), 'results': data})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# CREAR POM NOU AL TENANT
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def crear_pom_tenant_view(request):
    """
    POST /api/v1/poms/crear-tenant/
    Crea un POM nou al tenant (sense POMGlobal associat, o amb un de nou).
    Body: {
      codi_client, nom_client, categoria_id,
      descripcio (opcional), notes (opcional)
    }
    """
    codi = request.data.get('codi_client', '').strip()
    nom = request.data.get('nom_client', '').strip()
    categoria_id = request.data.get('categoria_id')

    if not codi or not nom:
        return Response({'error': 'codi_client i nom_client són obligatoris'}, status=400)

    try:
        from fhort.pom.models import POMMaster

        if POMMaster.objects.filter(codi_client=codi).exists():
            return Response({'error': f'Ja existeix un POM amb codi {codi}'}, status=400)

        pom = POMMaster.objects.create(
            codi_client=codi,
            nom_client=nom,
            categoria_id=categoria_id,
            notes=request.data.get('notes', ''),
            actiu=True,
        )

        return Response({
            'id': pom.id,
            'codi_client': pom.codi_client,
            'nom_client': pom.nom_client,
            'missatge': f'POM {codi} creat correctament',
        }, status=201)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def editar_nomenclatura_pom_view(request, pom_id):
    """
    PATCH /api/v1/poms/{id}/nomenclatura/
    Edita codi_client i nom_client d'un POM del tenant.
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
