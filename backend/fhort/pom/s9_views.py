"""
fhort/pom/s9_views.py — Sprint S9: Onboarding + Setup Wizard
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def onboarding_status_view(request):
    """
    GET /api/v1/onboarding/status/
    Return the tenant's onboarding status.
    Indicates which steps are completed and which are missing.
    """
    try:
        from fhort.pom.models import (POMMaster, GradingRuleSet, SizeSystem,
                                       GarmentType, GarmentPOMMap)
        from fhort.accounts.models import TenantConfig

        config = TenantConfig.get_or_create_default()

        steps = {
            'tenant_config': {
                'ok': bool(config.nom_empresa),
                'label': 'Configuració del tenant',
                'descripcio': 'Nom d''empresa i unitats de mesura',
            },
            'poms_carregats': {
                'ok': POMMaster.objects.filter(actiu=True).count() >= 10,
                'label': 'Catàleg de POMs',
                'descripcio': f'{POMMaster.objects.count()} POMs al catàleg',
                'count': POMMaster.objects.count(),
            },
            'grading_rules': {
                'ok': GradingRuleSet.objects.filter(is_system_default=True).count() >= 1,
                'label': 'Grading Rule Sets',
                'descripcio': f'{GradingRuleSet.objects.count()} conjunts de regles',
                'count': GradingRuleSet.objects.count(),
            },
            'size_systems': {
                'ok': SizeSystem.objects.count() >= 1,
                'label': 'Size Systems',
                'descripcio': f'{SizeSystem.objects.count()} sistemes de talles',
                'count': SizeSystem.objects.count(),
            },
            'garment_types': {
                'ok': GarmentType.objects.count() >= 1,
                'label': 'Tipus de prenda',
                'descripcio': f'{GarmentType.objects.count()} tipus definits',
                'count': GarmentType.objects.count(),
            },
            'garment_pom_map': {
                'ok': GarmentPOMMap.objects.count() >= 10,
                'label': 'Garment POM Map',
                'descripcio': f'{GarmentPOMMap.objects.count()} relacions POM-prenda',
                'count': GarmentPOMMap.objects.count(),
            },
        }

        total = len(steps)
        completats = sum(1 for s in steps.values() if s['ok'])
        percentatge = round(completats / total * 100)

        return Response({
            'percentatge': percentatge,
            'completats': completats,
            'total': total,
            'llest': percentatge == 100,
            'steps': steps,
            'tenant_nom': config.nom_empresa or '',
            'unitat': config.unitat_mesura,
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_tenant_from_excel_view(request):
    """
    POST /api/v1/onboarding/setup-from-excel/
    Multipart: file (Excel Master Data Reference v2)
    Run the full seed from the Excel file.
    """
    file_obj = request.FILES.get('file')
    if not file_obj:
        return Response({'error': 'Cal adjuntar l''Excel (camp "file")'}, status=400)

    if not file_obj.name.endswith(('.xlsx', '.xls')):
        return Response({'error': 'Format no suportat. Cal .xlsx'}, status=400)

    try:
        import tempfile, os, pandas as pd
        from django_tenants.utils import schema_context

        # Save temporarily
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            for chunk in file_obj.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        resultats = {}

        def safe(val, d=None):
            if val is None: return d
            s = str(val).strip()
            return d if s in ('nan','NULL','None','') else s

        def safe_bool(val): return str(val).upper() in ('TRUE','T','1','YES','SI','✓')
        def safe_int(val, d=None):
            try: return int(float(val))
            except: return d
        def safe_dec(val, d=None):
            try: return float(val)
            except: return d

        with schema_context(request.tenant.schema_name):
            from fhort.pom.models import (
                Target, ConstructionType, FitType, POMCategory,
                POMGlobal, GarmentGroup, SizeSystem, SizeDefinition,
                GradingRuleSet, GradingRule
            )
            from fhort.accounts.models import TenantConfig

            sheets_to_load = [
                ('Target', 'targets'),
                ('Construction_Types', 'construction_types'),
                ('Fit_Types', 'fit_types'),
                ('POM_Categories', 'pom_categories'),
                ('POM_MASTER_Catalog', 'pom_globals'),
                ('Garment_Groups', 'garment_groups'),
                ('Size_Systems', 'size_systems'),
                ('Size_Definitions', 'size_definitions'),
                ('Grading_RuleSets', 'grading_rule_sets'),
                ('Grading_Rules', 'grading_rules'),
            ]

            for sheet_nom, key in sheets_to_load:
                try:
                    df = pd.read_excel(tmp_path, sheet_name=sheet_nom, header=1)
                    count = 0

                    if key == 'targets':
                        for _, row in df.iterrows():
                            codi = safe(row.get('codi'))
                            if not codi: continue
                            Target.objects.update_or_create(
                                codi=codi,
                                defaults={'nom_en': safe(row.get('nom_en'), codi),
                                           'nom_cat': safe(row.get('nom_cat'), ''),
                                           'nom_es': safe(row.get('nom_es'), ''),
                                           'display_order': safe_int(row.get('id'), 0)}
                            )
                            count += 1

                    elif key == 'pom_categories':
                        for _, row in df.iterrows():
                            codi = safe(row.get('codi'))
                            if not codi: continue
                            POMCategory.objects.update_or_create(
                                codi=codi,
                                defaults={'nom_en': safe(row.get('nom_en'), codi),
                                           'nom_ca': safe(row.get('nom_cat'), ''),
                                           'display_order': safe_int(row.get('display_order'), 0)}
                            )
                            count += 1

                    elif key == 'pom_globals':
                        for _, row in df.iterrows():
                            pom_code = safe(row.get('POM Code'))
                            name_en = safe(row.get('Name EN ★'))
                            if not pom_code or not name_en: continue
                            if not pom_code.startswith('POM-'): continue
                            cat_nom = safe(row.get('Category'))
                            cat = POMCategory.objects.filter(nom_en__iexact=cat_nom).first() if cat_nom else None
                            try:
                                POMGlobal.objects.update_or_create(
                                    codi_intern=pom_code,
                                    defaults={'nom_en': name_en,
                                               'nom_cat': safe(row.get('Name CAT'), ''),
                                               'categoria': cat,
                                               'htm_metode_en': safe(row.get('Description EN (HTM)'), ''),
                                               'htm_cat': safe(row.get('Description CAT'), ''),
                                               'htm_punt_inici_en': safe(row.get('Start Point'), ''),
                                               'htm_punt_fi_en': safe(row.get('End Point'), ''),
                                               'htm_referencia': safe(row.get('Reference Point'), ''),
                                               'is_key_measure': '✓' in str(row.get('KEY', '')),
                                               'actiu': True}
                                )
                                count += 1
                            except Exception:
                                pass

                    resultats[key] = {'ok': True, 'count': count}
                except Exception as e:
                    resultats[key] = {'ok': False, 'error': str(e)}

        os.unlink(tmp_path)

        return Response({
            'missatge': 'Setup completat',
            'resultats': resultats,
            'total_carregat': sum(r.get('count', 0) for r in resultats.values() if r.get('ok')),
        })

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("setup_tenant_from_excel error")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def setup_client_config_view(request):
    """
    POST /api/v1/onboarding/config/
    Configure the tenant's basic data.
    Body: { nom_empresa, unitat_mesura, norma_referencia }
    """
    try:
        from fhort.accounts.models import TenantConfig
        config = TenantConfig.get_or_create_default()

        if 'nom_empresa' in request.data:
            config.nom_empresa = request.data['nom_empresa']
        if 'unitat_mesura' in request.data:
            config.unitat_mesura = request.data['unitat_mesura']
        if 'norma_referencia' in request.data:
            config.norma_referencia = request.data['norma_referencia']
        config.save()

        return Response({
            'nom_empresa': config.nom_empresa,
            'unitat_mesura': config.unitat_mesura,
            'norma_referencia': config.norma_referencia,
            'missatge': 'Configuració guardada',
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)
