"""
fhort/pom/s4_views.py — Sprint S4: Versioning + CM/INCH + Historial
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone


# ─── Conversió d'unitats ──────────────────────────────────────────────────────

CM_TO_INCH = 0.393701
INCH_TO_CM = 2.54

def convert_value(value, from_unit, to_unit):
    """Converteix un valor entre CM i INCH."""
    if from_unit == to_unit or value is None:
        return value
    if from_unit == 'CM' and to_unit == 'INCH':
        return round(float(value) * CM_TO_INCH, 3)
    if from_unit == 'INCH' and to_unit == 'CM':
        return round(float(value) * INCH_TO_CM, 2)
    return value

def get_tenant_unit(request):
    """Retorna la unitat de mesura del tenant (CM o INCH)."""
    try:
        from fhort.accounts.models import TenantConfig
        return TenantConfig.get_or_create_default().unitat_mesura
    except Exception:
        return 'CM'


# ─── Versioning ───────────────────────────────────────────────────────────────

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_grading_rule_with_history_view(request, rule_set_id, pom_codi):
    """
    PATCH /api/v1/grading-rule-sets/{id}/regles/{pom_codi}/
    Actualitza un increment amb registre d'historial.
    Body: { increment: 2.5, logica: "LINEAR", nota: "Ajust per Brownie SS27" }

    Si el RuleSet és estàndard, retorna error (cal clonar primer).
    Si és custom, actualitza i registra l'historial.
    """
    try:
        from fhort.pom.models import GradingRule, GradingRuleSet, GradingRuleHistory

        rs = GradingRuleSet.objects.get(pk=rule_set_id)

        if rs.is_system_default:
            return Response({
                'error': "No es pot editar un RuleSet estàndard. Clona'l primer.",
                'action': 'clone_first',
            }, status=400)

        from django.db.models import Q
        rule = GradingRule.objects.filter(
            rule_set=rs,
        ).filter(
            Q(pom__pom_global__codi=pom_codi) | Q(pom__codi_client=pom_codi)
        ).select_related('pom', 'pom__pom_global').first()

        if not rule:
            return Response({'error': f'Regla {pom_codi} no trobada'}, status=404)

        # Guardar valors anteriors
        val_anterior = rule.increment
        logica_anterior = rule.logica

        # Aplicar canvis
        # Si el tenant usa INCH, convertir a CM per guardar
        tenant_unit = get_tenant_unit(request)
        if 'increment' in request.data:
            val_input = float(request.data['increment'])
            val_cm = convert_value(val_input, tenant_unit, 'CM')
            rule.increment = val_cm
        if 'logica' in request.data:
            rule.logica = request.data['logica']

        rule.save(update_fields=['increment', 'logica'])

        # Registrar historial. rule.pom es POMMaster; GradingRuleHistory.pom es FK a POMGlobal.
        pom_global = rule.pom.pom_global if rule.pom_id and rule.pom.pom_global_id else None
        user_nom = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        GradingRuleHistory.objects.create(
            rule_set=rs,
            pom=pom_global,
            pom_codi=pom_codi,
            valor_anterior=val_anterior,
            valor_nou=rule.increment,
            logica_anterior=logica_anterior,
            logica_nova=rule.logica,
            modificat_per_id=request.user.id,
            modificat_per_nom=user_nom,
            nota=request.data.get('nota', ''),
        )

        # Retornar en la unitat del tenant
        increment_display = convert_value(float(rule.increment), 'CM', tenant_unit)

        return Response({
            'pom_codi': pom_codi,
            'increment_cm': float(rule.increment),
            'increment_display': increment_display,
            'unitat': tenant_unit,
            'logica': rule.logica,
            'missatge': f'{pom_codi} actualitzat a +{increment_display} {tenant_unit.lower()}/talla',
        })

    except GradingRuleSet.DoesNotExist:
        return Response({'error': 'RuleSet no trobat'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("update_grading_rule_with_history error")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grading_rule_history_view(request, rule_set_id):
    """
    GET /api/v1/grading-rule-sets/{id}/historial/
    Retorna l'historial de canvis d'un RuleSet.
    """
    try:
        from fhort.pom.models import GradingRuleHistory

        history = GradingRuleHistory.objects.filter(
            rule_set_id=rule_set_id
        ).order_by('-modificat_at')[:50]

        tenant_unit = get_tenant_unit(request)

        data = [{
            'id': h.id,
            'pom_codi': h.pom_codi,
            'valor_anterior': convert_value(float(h.valor_anterior), 'CM', tenant_unit),
            'valor_nou': convert_value(float(h.valor_nou), 'CM', tenant_unit),
            'unitat': tenant_unit,
            'logica_anterior': h.logica_anterior,
            'logica_nova': h.logica_nova,
            'modificat_per': h.modificat_per_nom,
            'modificat_at': h.modificat_at.isoformat(),
            'nota': h.nota,
        } for h in history]

        return Response({'count': len(data), 'results': data})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sizing_profile_versions_view(request, profile_id):
    """
    GET /api/v1/sizing-profiles/{id}/versions/
    Retorna totes les versions d'un perfil (estàndard + customs del client).
    """
    try:
        from fhort.pom.models import SizingProfile

        original = SizingProfile.objects.get(pk=profile_id)

        # Buscar root (si és custom, anar al pare)
        root = original
        while root.parent_profile_id:
            root = root.parent_profile

        # Totes les versions d'aquest root
        versions = list(SizingProfile.objects.filter(
            parent_profile=root
        ).select_related('grading_rule_set').order_by('version'))

        data = [{
            'id': root.id,
            'version': root.version,
            'nom': root.grading_rule_set.nom if root.grading_rule_set_id else '—',
            'is_system_default': True,
            'modified_at': None,
        }] + [{
            'id': v.id,
            'version': v.version,
            'nom': v.grading_rule_set.nom if v.grading_rule_set_id else '—',
            'is_system_default': False,
            'modified_at': v.modified_at.isoformat() if v.modified_at else None,
        } for v in versions]

        return Response({'count': len(data), 'results': data})
    except SizingProfile.DoesNotExist:
        return Response({'error': 'Perfil no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ─── CM/INCH ──────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def grading_rules_with_units_view(request, rule_set_id):
    """
    GET /api/v1/grading-rule-sets/{id}/regles/
    Retorna totes les regles converties a la unitat del tenant.
    """
    try:
        from fhort.pom.models import GradingRule, GradingRuleSet

        rs = GradingRuleSet.objects.get(pk=rule_set_id)
        rules = GradingRule.objects.filter(
            rule_set=rs, actiu=True
        ).select_related('pom', 'pom__categoria', 'pom__pom_global').order_by(
            'pom__categoria__display_order', 'pom__codi_client'
        )

        tenant_unit = get_tenant_unit(request)

        def _pom_codi(p):
            if p.pom_global_id:
                return p.pom_global.codi
            return p.codi_client or ''

        def _pom_nom_en(p):
            if p.pom_global_id and p.pom_global.nom_en:
                return p.pom_global.nom_en
            return p.nom_client

        def _pom_nom_ca(p):
            if p.pom_global_id and p.pom_global.nom_ca:
                return p.pom_global.nom_ca
            return p.nom_client

        data = [{
            'pom_id': r.pom_id,
            'pom_codi': _pom_codi(r.pom) if r.pom_id else '',
            'pom_nom_en': _pom_nom_en(r.pom) if r.pom_id else '',
            'pom_nom_cat': _pom_nom_ca(r.pom) if r.pom_id else '',
            'categoria_nom': r.pom.categoria.nom_ca or r.pom.categoria.nom_en if (r.pom_id and r.pom.categoria_id) else '',
            'logica': r.logica,
            'increment_cm': float(r.increment),
            'increment_display': convert_value(float(r.increment), 'CM', tenant_unit),
            'unitat': tenant_unit,
            'is_key': r.pom.is_key_measure if r.pom_id else False,
        } for r in rules]

        return Response({
            'rule_set_id': rule_set_id,
            'rule_set_nom': rs.nom,
            'is_system_default': rs.is_system_default,
            'unitat': tenant_unit,
            'count': len(data),
            'results': data,
        })
    except GradingRuleSet.DoesNotExist:
        return Response({'error': 'RuleSet no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def restore_version_view(request, profile_id):
    """
    POST /api/v1/sizing-profiles/{id}/restaurar/
    Restaura un perfil a la versió estàndard (descarta canvis client).
    Body: { confirmar: true }
    """
    try:
        from fhort.pom.models import SizingProfile, GradingRule

        if not request.data.get('confirmar'):
            return Response({'error': 'Cal confirmar: { "confirmar": true }'}, status=400)

        profile = SizingProfile.objects.get(pk=profile_id)

        if not profile.parent_profile_id:
            return Response({'error': 'Aquest ja és el perfil estàndard'}, status=400)

        original = profile.parent_profile

        # Sincronitzar les regles del custom amb les del pare
        original_rules = {r.pom_id: r for r in GradingRule.objects.filter(
            rule_set=original.grading_rule_set
        )}
        custom_rules = GradingRule.objects.filter(rule_set=profile.grading_rule_set)

        updated = 0
        for rule in custom_rules:
            if rule.pom_id in original_rules:
                orig = original_rules[rule.pom_id]
                if rule.increment != orig.increment or rule.logica != orig.logica:
                    rule.increment = orig.increment
                    rule.logica = orig.logica
                    rule.save(update_fields=['increment', 'logica'])
                    updated += 1

        return Response({
            'missatge': f"Perfil restaurat a l'estàndard. {updated} regles restaurades.",
            'regles_restaurades': updated,
        })

    except SizingProfile.DoesNotExist:
        return Response({'error': 'Perfil no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
