"""Endpoints de configuració del calendari (Sprint A, Peça 3).
- company-calendar/ (singleton tenant) — gated `configure`.
- users/<id>/jornada/ (override per tècnic) — gated `configure` o `manage_users`.
- absencies/ (CRUD, filtrable per ?user_profile=) — gated `configure` o `manage_users`.
"""
from rest_framework import viewsets, mixins
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status as http_status
from datetime import date as _date
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend

from fhort.accounts.models import UserProfile
from fhort.accounts.capabilities import (HasCapability, CONFIGURE, MANAGE_USERS,
                                         VIEW_TEAM_TASKS, DEFINE_TASKS, get_capabilities)
from .models import CompanyCalendar, Absencia, TechnicianQueueOrder
from .serializers import (CompanyCalendarSerializer, JornadaSerializer,
                          AbsenciaSerializer)
from . import plan_service
from fhort.tasks.models import ModelTask, PlanSnapshot, Production
from fhort.fitting.models import FittingSession


class _Configure(HasCapability):
    required_capability = CONFIGURE


class _DefineTasks(HasCapability):
    required_capability = DEFINE_TASKS


class _ConfigureOrManageUsers(BasePermission):
    """Permet si l'usuari té `configure` O `manage_users`."""
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        caps = get_capabilities(user)
        return CONFIGURE in caps or MANAGE_USERS in caps


@api_view(['GET', 'PUT'])
@permission_classes([_Configure])
def company_calendar_view(request):
    """GET/PUT /api/v1/company-calendar/ — calendari d'empresa (singleton del tenant)."""
    cal = CompanyCalendar.load()   # get_or_create del singleton
    if request.method == 'GET':
        return Response(CompanyCalendarSerializer(cal).data)
    ser = CompanyCalendarSerializer(cal, data=request.data, partial=True)
    ser.is_valid(raise_exception=True)
    ser.save()
    return Response(ser.data)


@api_view(['GET', 'PUT'])
@permission_classes([_ConfigureOrManageUsers])
def user_jornada_view(request, user_id):
    """GET/PUT /api/v1/users/<id>/jornada/ — override de jornada del tècnic (<id> = User id).
    PUT amb null/buit → torna a heretar la jornada de l'empresa."""
    try:
        profile = UserProfile.objects.get(user_id=user_id)
    except UserProfile.DoesNotExist:
        return Response({'error': 'Perfil no trobat en aquest tenant.'},
                        status=http_status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        return Response({'user_id': user_id, 'jornada_override': profile.jornada_override})
    ser = JornadaSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    profile.jornada_override = ser.validated_data['jornada_override']
    profile.save(update_fields=['jornada_override'])
    return Response({'user_id': user_id, 'jornada_override': profile.jornada_override})


class AbsenciaViewSet(mixins.ListModelMixin, mixins.CreateModelMixin,
                      mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                      viewsets.GenericViewSet):
    """CRUD d'absències per tècnic. Filtrable per ?user_profile=<id>."""
    queryset = Absencia.objects.select_related('user_profile').all()
    serializer_class = AbsenciaSerializer
    permission_classes = [_ConfigureOrManageUsers]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user_profile']


# ── Sprint B — motor de planificació (gated configure) ───────────────────────
@api_view(['POST'])
@permission_classes([_Configure])
def plan_compute_view(request):
    """POST /api/v1/plan/compute/ — planifica un conjunt amb el motor determinista,
    escriu planned_*/predicted_* i desa un PlanSnapshot.
    Body (tots opcionals; sense filtre = tot el pendent):
      {"model_ids":[110,111], "campaign_filter":{"temporada":"SS","any":26}}"""
    profile = getattr(request.user, 'profile', None)
    d = request.data
    try:
        out = plan_service.compute_and_save(
            model_ids=d.get('model_ids'), campaign_filter=d.get('campaign_filter'),
            computed_by=profile)
    except (ValueError, KeyError) as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response(out, status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_Configure])
def plan_preview_view(request):
    """POST /api/v1/plan/preview/ — simula reposicionar una tasca SENSE desar.
    Body: {"task_id":123, "new_start":"2026-06-09T08:00:00"}.
    Retorna {moved_task_id, placements, warnings, impact}."""
    d = request.data
    if not d.get('task_id') or not d.get('new_start'):
        return Response({'error': 'task_id i new_start requerits.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    try:
        out = plan_service.preview(task_id=d['task_id'], new_start=d['new_start'])
    except ModelTask.DoesNotExist:
        return Response({'error': 'Tasca no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)
    except (ValueError, KeyError) as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response(out, status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_Configure])
def plan_apply_view(request):
    """POST /api/v1/plan/apply/ — aplica una reposició acceptada: fixa la tasca
    (planned_locked=True a new_start) i desa el recàlcul de la cua (+ PlanSnapshot).
    Body: {"task_id":123, "new_start":"2026-06-09T08:00:00"}."""
    profile = getattr(request.user, 'profile', None)
    d = request.data
    if not d.get('task_id') or not d.get('new_start'):
        return Response({'error': 'task_id i new_start requerits.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    try:
        out = plan_service.apply(task_id=d['task_id'], new_start=d['new_start'],
                                 computed_by=profile)
    except ModelTask.DoesNotExist:
        return Response({'error': 'Tasca no trobada.'}, status=http_status.HTTP_404_NOT_FOUND)
    except (ValueError, KeyError) as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response(out, status=http_status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([_Configure])
def plan_snapshots_view(request):
    """GET /api/v1/plan/snapshots/ — historial de previsions (últimes 50)."""
    out = [{'id': s.id, 'computed_at': s.computed_at, 'start_date': s.start_date,
            'technician_count': s.technician_count,
            'campaign_filter': s.campaign_filter,
            'model_count': len(s.model_sequence)}
           for s in PlanSnapshot.objects.all()[:50]]
    return Response({'snapshots': out}, status=http_status.HTTP_200_OK)


# ── Tram 3 Peça 2A — Gantt read-only: pla vigent ─────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def plan_current_view(request):
    """GET /api/v1/plan/current/ — pla vigent (planned_* desats) per pintar el Gantt read-only.

    ACCÉS: qualsevol usuari autenticat (IsAuthenticated). El control fi és per DADES, no per gate:
    SCOPE (mateix patró que ModelTaskViewSet.get_queryset, tasks/views_b.py):
      - amb view_team_tasks (manager/admin) → totes les tasques planificades de tots els tècnics.
      - sense view_team_tasks (technician/product_manager) → NOMÉS les del seu propi UserProfile.
        El filtre passa al QUERYSET (físic), no al client: Montse rep 24, mai 48.

    DATES: planned_start/end es desen i es retornen en UTC (ISO). El front les pinta en local
    (Europe/Madrid). `en_risc` SÍ es calcula amb la data LOCAL de planned_end vs data_objectiu
    (DateField sense hora), perquè un planned_end a les 23:00 local no creui de dia en UTC i
    marqui risc fals. data_objectiu None → en_risc False.
    """
    qs = (ModelTask.objects
          .exclude(status='Done')
          .filter(planned_start__isnull=False)
          .select_related('model', 'task_type', 'assignee__user'))

    if VIEW_TEAM_TASKS not in get_capabilities(request.user):
        profile = getattr(request.user, 'profile', None)
        qs = qs.filter(assignee=profile) if profile is not None else qs.none()

    tasks = []
    for tk in qs:
        end_local = timezone.localtime(tk.planned_end).date() if tk.planned_end else None
        data_obj = tk.model.data_objectiu
        en_risc = bool(end_local and data_obj and end_local > data_obj)
        prof = tk.assignee
        user = getattr(prof, 'user', None)
        nom = (user.get_full_name() or user.username) if user else None
        tasks.append({
            'task_id': tk.id,
            'model': tk.model.codi_intern,
            'task_type': tk.task_type.code,
            'assignee': prof.id if prof else None,
            'assignee_nom': nom,
            'planned_start': tk.planned_start.isoformat() if tk.planned_start else None,
            'planned_end': tk.planned_end.isoformat() if tk.planned_end else None,
            'data_objectiu': data_obj.isoformat() if data_obj else None,
            'en_risc': en_risc,
        })
    return Response({'tasks': tasks}, status=http_status.HTTP_200_OK)


# ── Tram 3 Peça 2B-cal — Calendari propi: esdeveniments unificats ────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_events_view(request):
    """GET /api/v1/calendar/events/ — esdeveniments UNIFICATS per al calendari propi (agenda).

    Agrega TRES fonts sota el mateix contracte:
      - `tipus="tasca"` (ModelTask planificades): bloc HORARI, color del tècnic
        (UserProfile.color_avatar), agrupable per cua.
      - `tipus="confeccio"` (Production): estadi de DURADA en dies (enviament→retorn),
        `all_day=True`, color fix de tipus, SENSE tècnic (tecnic_id=None).
      - `tipus="fitting"` (FittingSession): marcador d'un dia, `all_day=True`, color fix,
        SENSE tècnic. Porta `meta.avis_abans_confeccio` (dependència tova, no en_risc).

    ACCÉS: IsAuthenticated. SCOPE (al queryset, igual que plan/current):
      - amb view_team_tasks → totes les tasques planificades.
      - sense → només les del propi UserProfile.
      - confecció/fitting → SEMPRE visibles a tot autenticat (no tenen tècnic per filtrar).

    PARAMS opcionals start/end (YYYY-MM-DD): acoten per data LOCAL de planned_start (inclusius).
    Sense params → tot el planificat no-Done.

    DATES: ISO 8601 amb offset Europe/Madrid via timezone.localtime() (p.ex. ...T08:00:00+02:00),
    MAI UTC cru "Z" → el front pinta directe amb new Date(). en_risc = data LOCAL de planned_end
    > data_objectiu (DateField); data_objectiu None → False.
    """
    qs = (ModelTask.objects
          .exclude(status='Done')
          .filter(planned_start__isnull=False)
          .select_related('model', 'task_type', 'assignee__user'))

    if VIEW_TEAM_TASKS not in get_capabilities(request.user):
        profile = getattr(request.user, 'profile', None)
        qs = qs.filter(assignee=profile) if profile is not None else qs.none()

    # Rang opcional sobre la data LOCAL de planned_start (inclusiu a banda i banda).
    start_raw, end_raw = request.query_params.get('start'), request.query_params.get('end')
    try:
        start_d = _date.fromisoformat(start_raw) if start_raw else None
        end_d = _date.fromisoformat(end_raw) if end_raw else None
    except ValueError:
        return Response({'error': 'start/end han de ser dates YYYY-MM-DD.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    if start_d:
        qs = qs.filter(planned_start__date__gte=start_d)
    if end_d:
        qs = qs.filter(planned_start__date__lte=end_d)

    events = []
    for tk in qs:
        end_local = timezone.localtime(tk.planned_end).date() if tk.planned_end else None
        data_obj = tk.model.data_objectiu
        en_risc = bool(end_local and data_obj and end_local > data_obj)
        prof = tk.assignee
        user = getattr(prof, 'user', None)
        nom = (prof.nom_complet or (user.get_username() if user else None)) if prof else None
        color = (getattr(prof, 'color_avatar', None) or '#6b7280') if prof else '#6b7280'
        events.append({
            'id': f'task-{tk.id}',
            'tipus': 'tasca',
            'start': timezone.localtime(tk.planned_start).isoformat() if tk.planned_start else None,
            'end': timezone.localtime(tk.planned_end).isoformat() if tk.planned_end else None,
            'titol': f'{tk.model.codi_intern} · {tk.task_type.code}',
            'tecnic_id': prof.id if prof else None,
            'tecnic_nom': nom,
            'color': color,
            'link': f'/models/{tk.model_id}',
            'en_risc': en_risc,
            'meta': {
                'model_id': tk.model_id,
                'task_id': tk.id,
                'task_type': tk.task_type.code,
                'data_objectiu': data_obj.isoformat() if data_obj else None,
            },
        })
    # ── Font 'confeccio' (Production) — estadi de durada en DIES, all-day, SENSE tècnic ──
    # Colors FIXOS per tipus (no per tècnic): confecció = to taller neutre, fitting = blau distint.
    COLOR_CONFECCIO = '#7c6f64'   # taupe (taller/proveïdor extern)
    COLOR_FITTING = '#3a7ca5'     # blau (sessió de fitting)
    # Scope: confecció/fitting NO tenen tècnic → SEMPRE visibles a tot autenticat (cap filtre de perfil).
    prods = Production.objects.select_related('model', 'supplier')
    # Filtre per SOLAPAMENT amb el rang demanat (no "inici dins rang"): el tram
    # [requested_at.date(), expected_at] talla [start, end].
    if start_d:
        prods = prods.filter(expected_at__gte=start_d)
    if end_d:
        prods = prods.filter(requested_at__date__lte=end_d)
    for p in prods:
        req_d = timezone.localtime(p.requested_at).date()
        # Sense expected_at no hi ha fi de tram → es pinta com a estadi d'un sol dia (el d'enviament).
        end_date = p.expected_at or req_d
        events.append({
            'id': f'confeccio-{p.id}',
            'tipus': 'confeccio',
            'start': req_d.isoformat(),
            'end': end_date.isoformat(),
            'titol': f'{p.model.codi_intern} · {p.supplier.name} · conf.',
            'tecnic_id': None,
            'tecnic_nom': None,
            'color': COLOR_CONFECCIO,
            'link': f'/models/{p.model_id}',
            'en_risc': False,
            'all_day': True,
            'meta': {
                'model_id': p.model_id,
                'supplier': p.supplier.name,
                'phase': p.phase,
                'status': p.status,
                'expected_at': p.expected_at.isoformat() if p.expected_at else None,
            },
        })

    # ── Font 'fitting' (FittingSession) — marcador d'un dia, all-day, SENSE tècnic ──
    fittings = list(FittingSession.objects.select_related('model', 'garment_set')
                    .filter(**({'data__gte': start_d} if start_d else {}))
                    .filter(**({'data__lte': end_d} if end_d else {})))
    # Dependència TOVA: expected_at de la confecció del mateix (model, fase). Es consulta a banda
    # (la Production pot caure FORA del rang visible). Si n'hi ha més d'una, en guardem la més tardana.
    model_ids = {f.model_id for f in fittings if f.model_id}
    expected_by_key = {}
    if model_ids:
        for p in (Production.objects.filter(model_id__in=model_ids, expected_at__isnull=False)
                  .values('model_id', 'phase', 'expected_at')):
            key = (p['model_id'], p['phase'])
            prev = expected_by_key.get(key)
            if prev is None or p['expected_at'] > prev:
                expected_by_key[key] = p['expected_at']
    for f in fittings:
        target = f.model.codi_intern if f.model_id else (f.garment_set.codi_base if f.garment_set_id else '?')
        exp = expected_by_key.get((f.model_id, f.fase)) if f.model_id else None
        avis = bool(exp and f.data < exp)   # avís TOVA (no en_risc): fitting abans de tenir la confecció
        events.append({
            'id': f'fitting-{f.id}',
            'tipus': 'fitting',
            'start': f.data.isoformat(),
            'end': f.data.isoformat(),
            'titol': f'{target} · fitting {f.fase}',
            'tecnic_id': None,
            'tecnic_nom': None,
            'color': COLOR_FITTING,
            'link': f'/fittings/{f.id}',
            'en_risc': False,
            'all_day': True,
            'meta': {
                'model_id': f.model_id,
                'fase': f.fase,
                'estat': f.estat,
                'avis_abans_confeccio': avis,
            },
        })

    return Response({'events': events}, status=http_status.HTTP_200_OK)


# ── Tram 3 Peça 3A — ordre MANUAL de la cua per tècnic ───────────────────────
@api_view(['POST'])
@permission_classes([_DefineTasks])
def plan_reorder_view(request):
    """POST /api/v1/plan/reorder/ — desa l'ordre MANUAL de la cua d'un tècnic i recalcula.
    Gated `define_tasks` (com assign/unassign). Body: {assignee_id, model_ids:[...ordenats]}.

    `model_ids` ha de ser la cua del tècnic (cada model amb ≥1 ModelTask no-Done amb aquell
    assignee); `position` = índex a la llista. S'espera la cua SENCERA: els models de la cua NO
    inclosos a la llista conserven la fila prèvia (si en tenien) — el front envia tota la cua.
    Després de desar, recalcula la cua del tècnic (els `planned_*` reflecteixen el nou ordre)."""
    assignee_id = request.data.get('assignee_id')
    model_ids = request.data.get('model_ids')
    if not assignee_id or not isinstance(model_ids, list) or not model_ids:
        return Response({'error': 'assignee_id i model_ids (llista no buida) requerits.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    if len(set(model_ids)) != len(model_ids):
        return Response({'error': 'model_ids amb duplicats.'}, status=http_status.HTTP_400_BAD_REQUEST)
    profile = UserProfile.objects.filter(pk=assignee_id).first()
    if profile is None:
        return Response({'error': 'Tècnic no trobat.'}, status=http_status.HTTP_404_NOT_FOUND)
    # Validació: tots els models pertanyen a la cua del tècnic (≥1 tasca no-Done amb aquell assignee).
    in_queue = set(ModelTask.objects.filter(assignee_id=assignee_id, model_id__in=model_ids)
                   .exclude(status='Done').values_list('model_id', flat=True))
    invalid = [m for m in model_ids if m not in in_queue]
    if invalid:
        return Response({'error': f'Models fora de la cua del tècnic: {invalid}.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    with transaction.atomic():
        for i, mid in enumerate(model_ids):
            TechnicianQueueOrder.objects.update_or_create(
                profile=profile, model_id=mid, defaults={'position': i})
    results = plan_service.recompute_for_technicians([int(assignee_id)])
    return Response({'ok': True, 'assignee_id': int(assignee_id),
                     'result': results.get(int(assignee_id))}, status=http_status.HTTP_200_OK)
