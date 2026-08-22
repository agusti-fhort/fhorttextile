"""
fhort/pom/s2_views.py — Sprint S2 views
"""
import logging
from decimal import Decimal, InvalidOperation

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from fhort.accounts.capabilities import CONFIGURE, get_capabilities
from fhort.pom.grading_regime import (CODI_LINEAR_ZERO, MISSATGE_LINEAR_ZERO,
                                      es_linear_degenerada)

logger = logging.getLogger(__name__)


def _to_decimal_delta(v):
    """Payload → `Decimal` amb la precisió del camp, o `None` si no és un número.

    `Decimal` i no `float`: els camps de delta són `DecimalField(6,2)` i barrejar-hi floats fa
    que la comparació `increment != increment_base` (la del backfill i la del gate) balli per
    l'últim dígit. `str(v)` abans del Decimal perquè un float que arribi del JSON no s'hi coli
    amb la seva cua binària.
    """
    if v is None or v == '':
        return None
    try:
        return Decimal(str(v)).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return None


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
            'size_system', 'size_system__parent', 'size_system__customer',
            'grading_rule_set', 'customer'
        ).prefetch_related(
            # N1 — les 4 capes del run les recorre el serializer per fila; sense prefetch
            # són 4 queries per perfil (mateix motiu que el prefetch de `targets` al ViewSet).
            'size_system__targets', 'size_system__construccions',
            'size_system__fits', 'size_system__grups',
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

            # 🚨 FIX-A/PAS-1 — EL CLON PERDIA ELS BREAKS, I NINGÚ HO PODIA VEURE.
            #
            # El comentari d'aquí deia «tots els camps reals de GradingRule» i en copiava SIS de
            # deu: hi faltaven `increment_base`, `increment_break`, `talla_break_label`,
            # `talla_break_pos` i `talla_base_label`. Un joc amb break clonat sortia amb el break
            # ESBORRAT i el `increment` llegat intacte — i com que el motor gradua per
            # `increment_base` (`_apply_rule`, forma canònica), el clon graduava PLA on
            # l'original tenia relleu. Res petava, res avisava: la corba simplement era una
            # altra. Al catàleg de `fhort` això són 98 regles LINEAR, de les quals les que porten
            # break perdien la meitat de la seva llei en un clic.
            #
            # Es copia la regla SENCERA i s'enumeren els camps un a un a posta (no
            # `pk=None; save()`): un camp nou al model ha d'aparèixer aquí i fer-se veure, no
            # colar-se per una còpia màgica que ningú revisa.
            rules_creades = 0
            for rule in GradingRule.objects.filter(rule_set=original_rs):
                GradingRule.objects.create(
                    rule_set=nou_rs,
                    pom=rule.pom,
                    talla_base=rule.talla_base,
                    talla_base_label=rule.talla_base_label,
                    logica=rule.logica,
                    increment=rule.increment,
                    valors_step=rule.valors_step,
                    # La FORMA CANÒNICA, que és la que el motor llegeix de debò.
                    increment_base=rule.increment_base,
                    increment_break=rule.increment_break,
                    talla_break_label=rule.talla_break_label,
                    talla_break_pos=rule.talla_break_pos,
                    # TRAM F — I ELS INTERVALS. El fix A va trobar aquesta còpia amb sis camps
                    # de deu i el clon graduant PLA on l'original tenia relleu; un camp de forma
                    # nou que no s'afegís aquí tornaria a obrir exactament aquell forat. Per
                    # això s'enumeren un a un: perquè el camp nou s'hi hagi de fer veure.
                    breaks=rule.breaks,
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


def _prioritat_codi_mostrat(pom_codi):
    """Ordre determinista quan un `pom_codi` casa amb MÉS D'UNA regla del mateix ruleset.

    El codi de la URL és una CADENA, no una clau: el filtre casa per codi global O per
    `codi_client`, i res impedeix que dos POMMaster del mateix ruleset hi responguin
    (cas viu a staging: ruleset 217, codi 'BJ' → poms 514 i 418, increments 0.20 i 0.50).
    Sense `order_by`, quina regla s'edita el decidia el pla de Postgres.

    Criteri: guanya la regla el codi de la qual la LLISTA MOSTRA per aquell POM —
    `grading_rules_with_units_view` (s4_views.py) emet el codi global si n'hi ha, i si no
    el `codi_client`. Així el que s'edita és la fila que l'usuari veu amb aquell codi.
    Empat (dos POMs que mostren el mateix codi) → `pk` més baix: el més antic.
    """
    from django.db.models import Case, IntegerField, Value, When
    return Case(
        When(pom__pom_global__codi=pom_codi, then=Value(0)),
        When(pom__pom_global__isnull=True, pom__codi_client=pom_codi, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )


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
        ).annotate(
            _prioritat=_prioritat_codi_mostrat(pom_codi),
        ).select_related('pom', 'pom__pom_global').order_by('_prioritat', 'pk').first()

        if not rule:
            return Response({'error': f'Regla {pom_codi} no trobada'}, status=404)

        # 🚨 FIX-A/PAS-1 — `increment` SOL NO GRADUAVA RES.
        #
        # Aquesta porta escrivia el camp LLEGAT i prou. El motor gradua per `increment_base`
        # (`_apply_rule`, forma canònica) i només cau a `increment` quan `increment_base` és
        # NULL — cosa que al corpus d'avui no passa mai. Resultat: aquest PATCH tornava 200 OK,
        # la resposta ensenyava el número nou, i la graduació no es movia ni un mil·límetre.
        #
        # El paràmetre públic segueix dient-se `increment` (és el contracte de l'endpoint); el
        # que canvia és ON aterra: al delta que MANA. El mirall al llegat és TRANSITORI i mor al
        # PAS 3, quan el camp es queda sense cap lector.
        if 'increment' in request.data:
            valor = _to_decimal_delta(request.data['increment'])
            if valor is None:
                return Response({'error': "increment ha de ser un número."}, status=400)
            rule.increment_base = valor
            rule.increment = valor          # mirall transitori (PAS 1) — v. la nota de dalt
        if 'logica' in request.data:
            rule.logica = request.data['logica']
        # A3 — el MATEIX guard que `set_pom_regim_view` i `gravar_pom_view`. Ara que aquesta
        # porta mou la graduació de debò, també pot fabricar la mentida que A3 va tancar: una
        # LINEAR amb delta 0 i sense trencament que es presenta com a graduada i no gradua.
        # TRAM F — el guard jutja la regla SENCERA, intervals inclosos: aquesta porta pot
        # canviar `logica` i deixar uns intervals penjats sota un règim que no els llegeix.
        if es_linear_degenerada(rule.logica, rule.increment_base, rule.increment,
                                rule.increment_break, rule.talla_break_label, rule.breaks):
            return Response({'error': MISSATGE_LINEAR_ZERO, 'code': CODI_LINEAR_ZERO},
                            status=400)
        rule.save(update_fields=['increment', 'increment_base', 'logica'])

        return Response({
            'pom_codi': pom_codi,
            # `increment` es conserva a la resposta per contracte, però ara diu el delta que
            # MANA (`increment_base`), no el llegat: un client que llegís l'antic hauria vist
            # el número nou i una corba vella.
            'increment': rule.increment_base,
            'increment_base': rule.increment_base,
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

    ⚠️ EL TALL VA PER MÈTODE, i els dos costats tenen motiu propi.

    El GET queda obert a qualsevol autenticat: tota la SPA el consulta per saber
    `unitat_mesura`, i tancar-lo trencaria qualsevol pantalla de mesures.

    El PATCH exigeix CONFIGURE. La llista blanca de sota porta `hourly_rate`, `iban`,
    `tax_id`, `legal_name` i `legal_footer`: fins al 14/08 un tècnic hi podia escriure la
    TARIFA DE COST PER HORA de la casa — la mateixa que alimenta `internal_cost` a les
    línies d'albarà (`commerce/serializers.py:449-457`) — i la identitat fiscal que va a la
    capçalera de tots els PDF. La UI que ho edita ja demanava `configure`
    (`frontend/src/pages/GeneralConfig.jsx:43`); el backend, no. Era l'única escriptura
    sense gate de tot el mòdul (diagnosi 2026-08-14 §4.3).

    Va abans del `try` a posta: el `except Exception` d'aquesta vista torna 500, i un gate
    que es pugui degradar a 500 en comptes de 403 no és un gate.
    """
    if request.method == 'PATCH' and CONFIGURE not in get_capabilities(request.user):
        return Response({'detail': 'Cal la capacitat de configuració per editar '
                                   "la configuració de l'empresa."}, status=403)
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
