"""
fhort/pom/s4_views.py — Sprint S4: Versioning + CM/INCH + History
"""
from decimal import Decimal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

from fhort.pom.grading_regime import (CODI_LINEAR_ZERO, MISSATGE_LINEAR_ZERO,
                                      es_linear_degenerada)

#: La precisió del camp (`DecimalField(6,2)`). Els deltes s'hi quantitzen abans de desar-los
#: perquè `increment != increment_base` —la comparació del backfill i la del gate— no balli per
#: l'últim dígit d'un float que ve del JSON.
DOS_DEC = Decimal('0.01')


# ─── Unit conversion ─────────────────────────────────────────────────────────

CM_TO_INCH = 0.393701
INCH_TO_CM = 2.54

def convert_value(value, from_unit, to_unit):
    """Convert a value between CM and INCH."""
    if from_unit == to_unit or value is None:
        return value
    if from_unit == 'CM' and to_unit == 'INCH':
        return round(float(value) * CM_TO_INCH, 3)
    if from_unit == 'INCH' and to_unit == 'CM':
        return round(float(value) * INCH_TO_CM, 2)
    return value

def get_tenant_unit(request):
    """Return the tenant's measurement unit (CM or INCH)."""
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
    Update an increment with a history record.
    Body: { increment: 2.5, logica: "LINEAR", nota: "Ajust per Brownie SS27" }

    If the RuleSet is standard, return an error (clone first).
    If it is custom, update and record the history.
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
        from fhort.pom.s2_views import _prioritat_codi_mostrat
        rule = GradingRule.objects.filter(
            rule_set=rs,
        ).filter(
            Q(pom__pom_global__codi=pom_codi) | Q(pom__codi_client=pom_codi)
        ).annotate(
            _prioritat=_prioritat_codi_mostrat(pom_codi),
        ).select_related('pom', 'pom__pom_global').order_by('_prioritat', 'pk').first()

        if not rule:
            return Response({'error': f'Regla {pom_codi} no trobada'}, status=404)

        # 🚨 FIX-A/PAS-1 — AQUESTA PORTA ESCRIVIA EL CAMP QUE EL MOTOR NO LLEGEIX.
        #
        # `increment` és el camp LLEGAT. El motor gradua per `increment_base` (forma canònica,
        # `_apply_rule`) i només cau a `increment` quan `increment_base` és NULL — que al corpus
        # d'avui no passa mai. O sigui que aquest PATCH desava, escrivia una fila d'historial que
        # deia que el valor havia canviat, tornava 200 OK... i la corba es quedava exactament on
        # era. L'historial documentava un canvi que no existia.
        #
        # El paràmetre públic segueix dient-se `increment` (contracte de l'endpoint) i la
        # conversió d'unitats no es toca: el que canvia és ON aterra. El mirall al llegat és
        # TRANSITORI i mor al PAS 3.
        #
        # ⚠️ `val_anterior` passa a llegir el delta que MANAVA, no el llegat: una fila d'historial
        # que comparés el llegat vell amb el canònic nou seria una tercera mentida sobre les dues
        # que això arregla.
        val_anterior = rule.increment_base if rule.increment_base is not None else rule.increment
        logica_anterior = rule.logica

        # Apply changes
        # If the tenant uses INCH, convert to CM before saving
        tenant_unit = get_tenant_unit(request)
        if 'increment' in request.data:
            try:
                val_input = float(request.data['increment'])
            except (TypeError, ValueError):
                return Response({'error': "increment ha de ser un número."}, status=400)
            val_cm = Decimal(str(convert_value(val_input, tenant_unit, 'CM'))).quantize(DOS_DEC)
            rule.increment_base = val_cm
            rule.increment = val_cm         # mirall transitori (PAS 1) — v. la nota de dalt
        if 'logica' in request.data:
            rule.logica = request.data['logica']

        # A3 — el MATEIX guard que les altres portes d'autoria. Ara que aquesta mou la graduació
        # de debò, també pot fabricar la LINEAR+0 que A3 va tancar a la resta.
        if es_linear_degenerada(rule.logica, rule.increment_base, rule.increment,
                                rule.increment_break, rule.talla_break_label):
            return Response({'error': MISSATGE_LINEAR_ZERO, 'code': CODI_LINEAR_ZERO}, status=400)

        rule.save(update_fields=['increment', 'increment_base', 'logica'])

        # Record history. rule.pom is POMMaster; GradingRuleHistory.pom is FK to POMGlobal.
        pom_global = rule.pom.pom_global if rule.pom_id and rule.pom.pom_global_id else None
        user_nom = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
        GradingRuleHistory.objects.create(
            rule_set=rs,
            pom=pom_global,
            pom_codi=pom_codi,
            valor_anterior=val_anterior,
            valor_nou=rule.increment_base,
            logica_anterior=logica_anterior,
            logica_nova=rule.logica,
            modificat_per_id=request.user.id,
            modificat_per_nom=user_nom,
            nota=request.data.get('nota', ''),
        )

        # Return in the tenant unit. Surt del delta que MANA.
        increment_display = convert_value(float(rule.increment_base), 'CM', tenant_unit)

        return Response({
            'pom_codi': pom_codi,
            'increment_cm': float(rule.increment_base),
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
    Return a RuleSet's change history.
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
    Return all versions of a profile (standard + client customs).
    """
    try:
        from fhort.pom.models import SizingProfile

        original = SizingProfile.objects.get(pk=profile_id)

        # Find root (if custom, go to the parent)
        root = original
        while root.parent_profile_id:
            root = root.parent_profile

        # All versions of this root
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
    Return all rules converted to the tenant unit.
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

        def _pom_name_en(p):
            if p.pom_global_id and p.pom_global.nom_en:
                return p.pom_global.nom_en
            return p.nom_client

        def _pom_name_ca(p):
            if p.pom_global_id and p.pom_global.nom_ca:
                return p.pom_global.nom_ca
            return p.nom_client

        data = [{
            'pom_id': r.pom_id,
            'pom_codi': _pom_codi(r.pom) if r.pom_id else '',
            'pom_nom_en': _pom_name_en(r.pom) if r.pom_id else '',
            'pom_nom_cat': _pom_name_ca(r.pom) if r.pom_id else '',
            'categoria_nom': r.pom.categoria.nom_ca or r.pom.categoria.nom_en if (r.pom_id and r.pom.categoria_id) else '',
            'logica': r.logica,
            # FIX-A/PAS-4 — el delta que MANA, no el llegat. Aquest llistat deia
            # `r.increment` i, per tant, podia ensenyar un número que ni el motor llegia ni
            # cap pantalla d'edició tocava. `None` quan la regla no en té: `float(None)` hauria
            # petat amb 500, i un 0 hauria semblat una regla que no gradua (que és una altra
            # cosa: la que no gradua és FIXED).
            'increment_cm': (float(r.increment_base) if r.increment_base is not None else None),
            'increment_display': (convert_value(float(r.increment_base), 'CM', tenant_unit)
                                  if r.increment_base is not None else None),
            # El relleu també viatja: un joc amb break servit amb una sola xifra és mig joc.
            'increment_break_cm': (float(r.increment_break)
                                   if r.increment_break is not None else None),
            'talla_break_label': r.talla_break_label,     # convenció de MOTOR
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
    Restore a profile to the standard version (discard client changes).
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

        # C3 — restaurar és sincronitzar regles contra les del pare. Si algun dels dos perfils no
        # porta graduació no hi ha res a sincronitzar: es diu, en comptes de tornar «0 regles
        # restaurades» com si la feina s'hagués fet.
        if not (original.grading_rule_set_id and profile.grading_rule_set_id):
            return Response(
                {'error': 'perfil_sense_graduacio',
                 'message': ("Aquest perfil (o el seu estàndard) no porta graduació: no hi ha "
                             "regles a restaurar.")},
                status=400)

        # Sync the custom rules with the parent's
        original_rules = {r.pom_id: r for r in GradingRule.objects.filter(
            rule_set_id=original.grading_rule_set_id
        )}
        custom_rules = GradingRule.objects.filter(rule_set_id=profile.grading_rule_set_id)

        # 🚨 FIX-A/PAS-1 — RESTAURAR NO RESTAURAVA LA GRADUACIÓ.
        #
        # Comparava i copiava `increment` + `logica`, que són DOS dels camps de la llei i no els
        # que manen. Dues conseqüències, i totes dues silencioses:
        #   · una regla de client amb el break canviat respecte de l'estàndard es declarava
        #     IGUAL (el `!=` no mirava el break) i no es restaurava mai;
        #   · i quan sí que es restaurava, el break del client hi quedava — o sigui que el
        #     resultat no era ni l'estàndard ni el que hi havia.
        # «Perfil restaurat a l'estàndard» era, literalment, fals.
        #
        # Ara la comparació i la còpia són de la FORMA SENCERA. La llista de camps és una i
        # serveix per a les dues coses: comparar i copiar amb criteris diferents és com es va
        # arribar aquí.
        CAMPS_LLEI = ('logica', 'increment_base', 'increment_break',
                      'talla_break_label', 'talla_break_pos', 'valors_step',
                      'increment')          # el llegat hi va mentre existeixi (mor al PAS 3)
        updated = 0
        for rule in custom_rules:
            if rule.pom_id in original_rules:
                orig = original_rules[rule.pom_id]
                if any(getattr(rule, c) != getattr(orig, c) for c in CAMPS_LLEI):
                    for c in CAMPS_LLEI:
                        setattr(rule, c, getattr(orig, c))
                    rule.save(update_fields=list(CAMPS_LLEI))
                    updated += 1

        return Response({
            'missatge': f"Perfil restaurat a l'estàndard. {updated} regles restaurades.",
            'regles_restaurades': updated,
        })

    except SizingProfile.DoesNotExist:
        return Response({'error': 'Perfil no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
