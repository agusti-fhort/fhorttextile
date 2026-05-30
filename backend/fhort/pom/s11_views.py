"""
fhort/pom/s11_views.py — Sprint S11: Automatic notifications
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone

CM_TO_INCH = 0.393701


def get_unit():
    try:
        from fhort.accounts.models import TenantConfig
        return TenantConfig.get_or_create_default().unitat_mesura
    except Exception:
        return 'CM'


def cv(val, unit):
    if val is None:
        return None
    v = float(val)
    return round(v * CM_TO_INCH, 3) if unit == 'INCH' else round(v, 2)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def pom_alerts_summary_view(request):
    """
    GET /api/v1/alerts/summary/
    Filtres: ?estat=Obert&model_id=X&dies=30
    """
    try:
        from fhort.fitting.models import POMAlert
        from django.db.models import Count
        import datetime

        qs = POMAlert.objects.select_related('pom', 'model')

        estat = request.query_params.get('estat')
        model_id = request.query_params.get('model_id')
        dies = int(request.query_params.get('dies', 30))

        if estat:
            qs = qs.filter(estat=estat)
        if model_id:
            qs = qs.filter(model_id=model_id)

        data_limit = timezone.now() - datetime.timedelta(days=dies)
        qs = qs.filter(data_creacio__gte=data_limit)

        per_estat = list(qs.values('estat').annotate(n=Count('id')).order_by('estat'))
        top_poms = list(qs.values('pom__codi_client', 'pom__nom_client')
                          .annotate(n=Count('id')).order_by('-n')[:10])
        recents = qs.order_by('-data_creacio')[:20]

        unit = get_unit()

        return Response({
            'periode_dies': dies,
            'total': qs.count(),
            'per_estat': per_estat,
            'top_poms': top_poms,
            'unitat': unit,
            'recents': [{
                'id': a.id,
                'model_nom': a.model.nom_prenda if a.model_id else '',
                'model_codi': a.model.codi_intern if a.model_id else '',
                'pom_codi': a.pom.codi_client if a.pom_id else '',
                'desviacio_display': cv(a.desviacio_cm, unit),
                'tolerancia_display': cv(a.tolerancia_cm, unit),
                'estat': a.estat,
                'missatge': a.missatge or '',
                'creat_at': a.data_creacio.isoformat() if a.data_creacio else None,
                'origen': a.origen or 'FITTING',
            } for a in recents],
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('pom_alerts_summary_view error')
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolve_alert_view(request, alert_id):
    """
    POST /api/v1/alerts/{id}/resoldre/
    Body: { nota: "..." }
    """
    try:
        from fhort.fitting.models import POMAlert

        alert = POMAlert.objects.get(pk=alert_id)
        alert.estat = 'Resolt'
        alert.nota_resolucio = request.data.get('nota', '')
        alert.data_resolucio = timezone.now()
        alert.resolt_per_user_id = request.user.id
        alert.save()

        return Response({
            'id': alert_id,
            'estat': alert.estat,
            'missatge': 'Alerta marcada com a resolta',
        })
    except POMAlert.DoesNotExist:
        return Response({'error': 'Alerta no trobada'}, status=404)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('resolve_alert_view error')
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_alerts_view(request, model_id):
    """GET /api/v1/models/{id}/alerts/"""
    try:
        from fhort.fitting.models import POMAlert

        alerts = POMAlert.objects.filter(
            model_id=model_id
        ).select_related('pom').order_by('-data_creacio')

        data = [{
            'id': a.id,
            'pom_codi': a.pom.codi_client if a.pom_id else '',
            'desviacio_cm': float(a.desviacio_cm) if a.desviacio_cm is not None else None,
            'tolerancia_cm': float(a.tolerancia_cm) if a.tolerancia_cm is not None else None,
            'estat': a.estat,
            'origen': a.origen or 'FITTING',
            'missatge': a.missatge or '',
            'creat_at': a.data_creacio.isoformat() if a.data_creacio else None,
        } for a in alerts]

        return Response({'count': len(data), 'results': data})
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception('model_alerts_view error')
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def check_tolerances_view(request, model_id):
    """
    POST /api/v1/models/{id}/check-tolerances/
    Body: { measurements: [{pom_id, value_cm}] }
    """
    measurements = request.data.get('measurements', [])
    if not measurements:
        return Response({'error': 'Cal proporcionar measurements'}, status=400)

    try:
        from fhort.models_app.models import BaseMeasurement, Model
        from fhort.pom.models import POMMaster
        from fhort.fitting.models import POMAlert

        model = Model.objects.get(pk=model_id)
        base_map = {
            bm.pom_id: float(bm.base_value_cm)
            for bm in BaseMeasurement.objects.filter(model=model, is_active=True)
            if bm.base_value_cm is not None
        }

        TOL_DEFAULT = 0.6
        alerts_creats = []
        for m in measurements:
            pom_id = m.get('pom_id')
            val = m.get('value_cm')
            if pom_id is None or val is None:
                continue

            pom = POMMaster.objects.filter(pk=pom_id).select_related('pom_global').first()
            if not pom:
                continue

            spec = base_map.get(pom_id)
            if spec is None:
                continue

            tol = TOL_DEFAULT
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
        import logging
        logging.getLogger(__name__).exception('check_tolerances_view error')
        return Response({'error': str(e)}, status=500)
