"""
fhort/pom/s2_views.py — Sprint S2 views
"""
import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def targets_list_view(request):
    """GET /api/v1/targets/ — List all available targets."""
    try:
        from fhort.pom.models import Target
        from fhort.pom.s2_serializers import TargetSerializer
        targets = Target.objects.all().order_by('display_order')
        return Response({
            'count': targets.count(),
            'results': TargetSerializer(targets, many=True).data
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def construction_types_list_view(request):
    """GET /api/v1/construction-types/ — List construction types."""
    try:
        from fhort.pom.models import ConstructionType
        from fhort.pom.s2_serializers import ConstructionTypeSerializer
        items = ConstructionType.objects.all().order_by('display_order')
        return Response({
            'count': items.count(),
            'results': ConstructionTypeSerializer(items, many=True).data
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fit_types_list_view(request):
    """GET /api/v1/fit-types/ — List all fit types (FitType has no `actiu` field)."""
    try:
        from fhort.pom.models import FitType
        from fhort.pom.s2_serializers import FitTypeSerializer
        items = FitType.objects.all().order_by('display_order')
        return Response({
            'count': items.count(),
            'results': FitTypeSerializer(items, many=True).data
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sizing_profiles_view(request):
    """
    GET /api/v1/sizing-profiles/
    Query params: target=WOMAN, construction=KNIT, fit_type=REGULAR, garment_type=1,
                  customer_codi=ABC
    Retorna TOTS els perfils del target+construction (ja no filtra is_default), ordenats:
    primer els del customer_codi, després els canònics (is_default), després la resta;
    dins cada grup, per nom del sistema.
    """
    try:
        from fhort.pom.models import SizingProfile
        from fhort.pom.s2_serializers import SizingProfileSerializer

        qs = SizingProfile.objects.select_related(
            'target', 'construction', 'fit_type',
            'size_system', 'size_system__parent', 'grading_rule_set', 'customer'
        )

        target_codi = request.query_params.get('target')
        construction_codi = request.query_params.get('construction')
        fit_type_id = request.query_params.get('fit_type')
        fit_codi = request.query_params.get('fit')
        garment_type_id = request.query_params.get('garment_type')
        customer_codi = request.query_params.get('customer_codi')
        # Resol l'id del Customer per prioritzar pel FK directe (autoritatiu) a més del
        # senyal indirecte size_system.customer_codi.
        cust_id = None
        if customer_codi:
            from fhort.tasks.models import Customer
            _c = Customer.objects.filter(codi=customer_codi).first()
            cust_id = _c.id if _c else None

        if target_codi:
            qs = qs.filter(target__codi=target_codi)
        if construction_codi:
            qs = qs.filter(construction__codi=construction_codi)
        if fit_type_id:
            qs = qs.filter(fit_type_id=fit_type_id)
        if fit_codi:
            qs = qs.filter(fit_type__codi=fit_codi)
        if garment_type_id:
            qs = qs.filter(garment_type_id=garment_type_id)

        def _grup(p):
            cc = (p.size_system.customer_codi or '') if p.size_system_id else ''
            own = (cust_id is not None and p.customer_id == cust_id) or \
                  (customer_codi and cc == customer_codi)
            if own:
                return 0  # perfil/run d'aquest client (FK directe o senyal indirecte)
            if p.is_default and p.customer_id is None:
                return 1  # canònic genèric del tenant
            return 2      # altres (perfils d'altres clients / no-default)
        profiles = sorted(
            qs,
            key=lambda p: (_grup(p), p.size_system.nom if p.size_system_id else ''),
        )

        return Response({
            'count': len(profiles),
            'results': SizingProfileSerializer(profiles, many=True).data,
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("sizing_profiles_view error")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sizing_profile_detail_view(request, pk):
    """GET /api/v1/sizing-profiles/{id}/ — Full detail of a profile."""
    try:
        from fhort.pom.models import SizingProfile, GradingRule
        from fhort.pom.s2_serializers import SizingProfileSerializer, GradingRuleLightSerializer

        profile = SizingProfile.objects.select_related(
            'target', 'construction', 'fit_type',
            'size_system', 'grading_rule_set'
        ).get(pk=pk)

        data = SizingProfileSerializer(profile).data

        # All rules (not only KEY). C3 — un perfil sense graduació no té regles: llista buida,
        # no una query amb `rule_set IS NULL` (que retornaria buit igualment, però mentint sobre
        # la intenció).
        all_rules = GradingRule.objects.filter(
            rule_set_id=profile.grading_rule_set_id,
            actiu=True
        ).select_related('pom', 'pom__pom_global').order_by('pom__codi_client') \
            if profile.grading_rule_set_id else []
        data['grading_rules_all'] = GradingRuleLightSerializer(all_rules, many=True).data

        return Response(data)
    except SizingProfile.DoesNotExist:
        return Response({'error': 'Perfil no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clone_sizing_profile_view(request, pk):
    """
    POST /api/v1/sizing-profiles/{id}/clonar/
    Create a client version of the standard profile.
    Body: { nom_client: "Brownie Knit Woman Regular" }
    """
    try:
        from fhort.pom.models import SizingProfile, GradingRuleSet, GradingRule
        from django.utils import timezone
        from django.db import transaction

        original = SizingProfile.objects.get(pk=pk)
        # C3 — clonar un perfil vol dir clonar-ne la GRADUACIÓ (ruleset + regles). Un perfil que
        # només declara àmbit no en té: es diu clar, en comptes de petar amb un 500 dins l'atòmic.
        if original.grading_rule_set_id is None:
            return Response(
                {'error': 'perfil_sense_graduacio',
                 'message': ("Aquest perfil declara àmbit però no porta graduació: no hi ha res a "
                             "clonar. Assigna-li un joc de regles abans de fer-ne una versió.")},
                status=400)
        nom_client = request.data.get('nom_client', f"Custom v{original.version + 1}")

        # Atòmic: GradingRuleSet + regles + SizingProfile són un tot; una fallada
        # parcial no ha de deixar rule_set/regles òrfens.
        with transaction.atomic():
            # Clone the GradingRuleSet (el nom de la variant viu a GradingRuleSet.nom)
            original_rs = original.grading_rule_set

            # PROVINENÇA (decisió CTO 2026-07-10): una versió de client és CLIENT_RUN encara que
            # sigui autoria manual i no vingui de cap run importat. Mai viatja a un tenant nou.
            # El customer surt del perfil clonat o del seu ruleset; si cap dels dos el té (clon
            # d'un estàndard pur), l'origen ja tanca la fuita i deixem traça al log.
            variant_customer = original.customer or original_rs.customer
            if variant_customer is None:
                logger.warning(
                    "GradingRuleSet CLIENT_RUN sense customer resoluble (clon de perfil %s, "
                    "nom=%r): procedència tancada per origen.", original.pk, nom_client)

            nou_rs = GradingRuleSet.objects.create(
                nom=nom_client,
                codi_sistema=f"{original_rs.codi_sistema}_CUSTOM",
                construction=original_rs.construction,
                fit_type=original_rs.fit_type,
                origen=GradingRuleSet.ORIGEN_CLIENT_RUN,
                customer=variant_customer,
                is_system_default=False,
                parent_version=original_rs,
                version_number=original_rs.version_number + 1,
            )
            # P7 — el ventall de targets és la M2M (font única): el clon hereta el conjunt
            # sencer de l'original, no només el primer com feia el FK legacy.
            nou_rs.targets.set(original_rs.targets.all())

            # Copy all the rules — tots els camps reals de GradingRule des de l'original
            # (talla_base és NOT NULL; valors_step preserva la fidelitat del grading).
            rules_creades = 0
            for rule in GradingRule.objects.filter(rule_set=original_rs):
                GradingRule.objects.create(
                    rule_set=nou_rs,
                    pom=rule.pom,
                    talla_base=rule.talla_base,
                    logica=rule.logica,
                    increment=rule.increment,
                    valors_step=rule.valors_step,
                    actiu=rule.actiu,
                )
                rules_creades += 1

            # Clone the SizingProfile
            nou_profile = SizingProfile.objects.create(
                target=original.target,
                garment_type=original.garment_type,
                construction=original.construction,
                fit_type=original.fit_type,
                size_system=original.size_system,
                grading_rule_set=nou_rs,
                is_default=False,
                parent_profile=original,
                version=original.version + 1,
                modified_by_id=request.user.id,
                modified_at=timezone.now(),
                notes=f"Clonat de {original} per {request.user}",
            )

        return Response({
            'id': nou_profile.id,
            'grading_rule_set_id': nou_rs.id,
            'rules_copiades': rules_creades,
            'missatge': f"Perfil clonat com a {nom_client}",
        }, status=201)

    except SizingProfile.DoesNotExist:
        return Response({'error': 'Perfil no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("clone_sizing_profile error")
        return Response({'error': str(e)}, status=500)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_grading_rule_view(request, rule_set_id, pom_codi):
    """
    PATCH /api/v1/grading-rule-sets/{id}/regles/{pom_codi}/
    Update a rule's increment.
    Body: { increment: 2.5, logica: "LINEAR" }
    """
    try:
        from fhort.pom.models import GradingRule, GradingRuleSet
        from django.db.models import Q

        rs = GradingRuleSet.objects.get(pk=rule_set_id)
        if rs.is_system_default:
            return Response({
                'error': "No es pot editar un RuleSet estandard. Clona'l primer."
            }, status=400)

        rule = GradingRule.objects.filter(
            rule_set=rs,
        ).filter(
            Q(pom__pom_global__codi=pom_codi) | Q(pom__codi_client=pom_codi)
        ).select_related('pom', 'pom__pom_global').first()

        if not rule:
            return Response({'error': f'Regla {pom_codi} no trobada'}, status=404)

        if 'increment' in request.data:
            rule.increment = float(request.data['increment'])
        if 'logica' in request.data:
            rule.logica = request.data['logica']
        rule.save(update_fields=['increment', 'logica'])

        return Response({
            'pom_codi': pom_codi,
            'increment': rule.increment,
            'logica': rule.logica,
            'missatge': 'Regla actualitzada',
        })
    except GradingRuleSet.DoesNotExist:
        return Response({'error': 'RuleSet no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def tenant_config_view(request):
    """
    GET  /api/v1/tenant-config/ — Return the tenant configuration
    PATCH /api/v1/tenant-config/ — Update unitat_mesura or norma_referencia
    """
    try:
        from fhort.accounts.models import TenantConfig
        from fhort.pom.s2_serializers import TenantConfigSerializer

        config = TenantConfig.get_or_create_default()
        ctx = {'request': request}   # perquè logo_file surti com a URL absoluta

        if request.method == 'GET':
            return Response(TenantConfigSerializer(config, context=ctx).data)

        # PATCH — camps escalars + upload opcional del logo (multipart, camp 'logo_file').
        allowed = ['unitat_mesura', 'norma_referencia', 'nom_empresa', 'logo_url', 'hourly_rate',
                   'iban', 'payment_notes', 'legal_name', 'tax_id', 'address', 'postal_code',
                   'city', 'country', 'email', 'phone', 'legal_footer']
        for field in allowed:
            if field in request.data:
                setattr(config, field, request.data[field])
        if 'logo_file' in request.FILES:
            # L'usuari puja SVG/PNG/JPG; el backend el normalitza SEMPRE a un PNG ràster que
            # reportlab dibuixa a la capçalera (fi de l'exigència "màxim 15 mm PNG").
            from fhort.accounts.logo import normalize_logo
            try:
                content = normalize_logo(request.FILES['logo_file'])
            except ValueError as e:
                return Response({'error': f'Logo no vàlid: {e}'}, status=400)
            if config.logo_file:
                config.logo_file.delete(save=False)   # neteja el fitxer anterior
            config.logo_file = content
        config.save()
        return Response(TenantConfigSerializer(config, context=ctx).data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pom_global_search_view(request):
    """
    GET /api/v1/pom-global/cerca/?q=chest&categoria=Upper+body
    Search POMs in the global catalog by code or name.
    """
    q = request.query_params.get('q', '').strip()
    categoria = request.query_params.get('categoria', '').strip()

    if len(q) < 2 and not categoria:
        return Response({'results': []})

    try:
        from fhort.pom.models import POMGlobal
        from fhort.pom.s2_serializers import POMGlobalLightSerializer
        from django.db.models import Q

        qs = POMGlobal.objects.filter(actiu=True)

        if q:
            qs = qs.filter(
                Q(codi__icontains=q) |
                Q(nom_en__icontains=q) |
                Q(nom_ca__icontains=q)
            )
        if categoria:
            qs = qs.filter(categoria__icontains=categoria)

        qs = qs.order_by('categoria', 'codi')[:30]

        return Response({
            'count': qs.count(),
            'results': POMGlobalLightSerializer(qs, many=True).data
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# garment_types_by_target_view JUBILAT (2026-07-19): filtrava famílies per `targets_recomanats` (M2M
# buit i jubilat). El substitueix GarmentTypeViewSet `?target` (via SizingProfile). 0 cridadors.
