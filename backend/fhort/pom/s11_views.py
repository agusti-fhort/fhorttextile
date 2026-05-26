"""
fhort/pom/s11_views.py — Sprint S11: Notificacions automàtiques
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pom_alerts_summary_view(request):
    """
    GET /api/v1/alerts/summary/
    Resum d'alertes per estat, model i POM.
    Filtres: ?estat=Obert&model_id=X&dies=30
    """
    try:
        from fhort.pom.models import POMAlert
        from django.db.models import Count, Q
        import datetime

        qs = POMAlert.objects.select_related('pom', 'model')

        estat = request.query_params.get('estat')
        model_id = request.query_params.get('model_id')
        dies = int(request.query_params.get('dies', 30))

        if estat: qs = qs.filter(estat=estat)
        if model_id: qs = qs.filter(model_id=model_id)

        data_limit = timezone.now() - datetime.timedelta(days=dies)
        qs = qs.filter(creat_at__gte=data_limit)

        # Resum per estat
        per_estat = qs.values('estat').annotate(n=Count('id')).order_by('estat')

        # Top POMs amb més alertes
        top_poms = qs.values(
            'pom__codi_client', 'pom__nom_client'
        ).annotate(n=Count('id')).order_by('-n')[:10]

        # Alertes recents detallades
        recents = qs.order_by('-creat_at')[:20]

        unit = 'CM'
        try:
            from fhort.accounts.models import TenantConfig
            unit = TenantConfig.get_or_create_default().unitat_mesura
        except Exception:
            pass

        CM_TO_INCH = 0.393701
        def cv(val):
            if val is None: return None
            v = float(val)
            return round(v * CM_TO_INCH, 3) if unit == 'INCH' else round(v, 2)

        return Response({
            'periode_dies': dies,
            'total': qs.count(),
            'per_estat': list(per_estat),
            'top_poms': list(top_poms),
            'unitat': unit,
            'recents': [{
                'id': a.id,
                'model_nom': a.model.nom_prenda if a.model_id else '',
                'model_codi': a.model.codi_intern if a.model_id else '',
                'pom_codi': a.pom.codi_client if a.pom_id else '',
                'desviacio_display': cv(a.desviacio_cm),
                'tolerancia_display': cv(a.tolerancia_cm),
                'estat': a.estat,
                'missatge': a.missatge,
                'creat_at': a.creat_at.isoformat(),
                'origen': getattr(a, 'origen', 'FITTING'),
            } for a in recents],
        })
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolve_alert_view(request, alert_id):
    """
    POST /api/v1/alerts/{id}/resoldre/
    Marca una alerta com a resolta.
    Body: { nota: "Ajust aplicat al proveïdor" }
    """
    try:
        from fhort.pom.models import POMAlert

        alert = POMAlert.objects.get(pk=alert_id)
        alert.estat = 'Resolt'
        if hasattr(alert, 'nota_resolucio'):
            alert.nota_resolucio = request.data.get('nota', '')
        if hasattr(alert, 'resolt_at'):
            alert.resolt_at = timezone.now()
        if hasattr(alert, 'resolt_per_id'):
            alert.resolt_per_id = request.user.id
        alert.save()

        return Response({
            'id': alert_id,
            'estat': alert.estat,
            'missatge': 'Alerta marcada com a resolta',
        })
    except POMAlert.DoesNotExist:
        return Response({'error': 'Alerta no trobada'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_alerts_view(request, model_id):
    """
    GET /api/v1/models/{id}/alerts/
    Totes les alertes d'un model específic.
    """
    try:
        from fhort.pom.models import POMAlert

        alerts = POMAlert.objects.filter(
            model_id=model_id
        ).select_related('pom').order_by('-creat_at')

        data = [{
            'id': a.id,
            'pom_codi': a.pom.codi_client if a.pom_id else '',
            'desviacio_cm': float(a.desviacio_cm) if a.desviacio_cm else None,
            'tolerancia_cm': float(a.tolerancia_cm) if a.tolerancia_cm else None,
            'estat': a.estat,
            'missatge': a.missatge,
            'creat_at': a.creat_at.isoformat(),
        } for a in alerts]

        return Response({'count': len(data), 'results': data})
    except Exception as e:
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_tolerances_view(request, model_id):
    """
    POST /api/v1/models/{id}/check-tolerances/
    Compara les BaseMeasurements amb les specs i genera alertes.
    Útil per verificar manualment sense fitting.
    Body: { measurements: [{pom_id: X, value_cm: Y}] }
    """
    measurements = request.data.get('measurements', [])
    if not measurements:
        return Response({'error': 'Cal proporcionar measurements'}, status=400)

    try:
        from fhort.models_app.models import BaseMeasurement, Model
        from fhort.pom.models import POMAlert

        model = Model.objects.get(pk=model_id)
        base_map = {
            bm.pom_id: float(bm.base_value_cm)
            for bm in BaseMeasurement.objects.filter(model=model, is_active=True)
        }

        alerts_creats = []
        for m in measurements:
            pom_id = m.get('pom_id')
            val = m.get('value_cm')
            if not pom_id or val is None: continue

            from fhort.pom.models import POMMaster
            pom = POMMaster.objects.filter(pk=pom_id).select_related('pom_global').first()
            if not pom: continue

            spec = base_map.get(pom_id)
            if spec is None: continue

            tol = float(pom.pom_global.tolerancia_woven_cm if pom.pom_global_id else 0.6)
            desv = round(float(val) - spec, 2)

            if abs(desv) > tol:
                alert, created = POMAlert.objects.update_or_create(
                    model=model, pom=pom,
                    defaults={
                        'desviacio_cm': desv,
                        'tolerancia_cm': tol,
                        'missatge': f'{pom.codi_client}: desvia {desv:+.2f}cm (tol ±{tol}cm)',
                        'estat': 'Obert',
                        'origen': 'MANUAL',
                    }
                )
                alerts_creats.append({
                    'pom': pom.codi_client,
                    'desviacio': desv,
                    'tolerancia': tol,
                    'nova': created,
                })

        return Response({
            'missatge': f'{len(alerts_creats)} alertes generades',
            'alerts': alerts_creats,
        })
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)
