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
                                         VIEW_TEAM_TASKS, DEFINE_TASKS, SCHEDULE_FITTINGS,
                                         get_capabilities, scope_model_task_queryset)
from .models import CompanyCalendar, Absencia, TechnicianQueueOrder
from .serializers import (CompanyCalendarSerializer, JornadaSerializer,
                          AbsenciaSerializer)
from . import plan_service
from fhort.tasks.models import ModelTask, PlanSnapshot, Production
from fhort.fitting.models import FittingSession
from fhort.models_app.models import Model


class _Configure(HasCapability):
    required_capability = CONFIGURE


class _DefineTasks(HasCapability):
    required_capability = DEFINE_TASKS


class _ScheduleFittings(HasCapability):
    required_capability = SCHEDULE_FITTINGS


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

    qs = scope_model_task_queryset(qs, request.user)

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

    qs = scope_model_task_queryset(qs, request.user)

    # Rang opcional sobre la data LOCAL de planned_start (inclusiu a banda i banda).
    start_raw, end_raw = request.query_params.get('start'), request.query_params.get('end')
    model_id_raw = request.query_params.get('model_id')   # acota a UN model (bloc fites del ModelSheet)
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
    if model_id_raw:
        qs = qs.filter(model_id=model_id_raw)

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
    COLOR_FITTING = '#3a7ca5'     # blau (sessió de fitting viva)
    COLOR_FITTING_CLOSED = '#6b9e6b'   # verd apagat (sessió de fitting Tancada) — Peça 3 E1
    # Scope: confecció/fitting NO tenen tècnic → SEMPRE visibles a tot autenticat (cap filtre de perfil).
    prods = Production.objects.select_related('model', 'supplier')
    # Filtre per SOLAPAMENT amb el rang demanat (no "inici dins rang"): el tram
    # [requested_at.date(), expected_at] talla [start, end].
    if start_d:
        prods = prods.filter(expected_at__gte=start_d)
    if end_d:
        prods = prods.filter(requested_at__date__lte=end_d)
    if model_id_raw:
        prods = prods.filter(model_id=model_id_raw)
    for p in prods:
        req_d = timezone.localtime(p.requested_at).date()
        # Marcador d'UN SOL DIA al dia d'entrega (expected_at), com fa fitting. Ja no es pinta com a
        # banda de durada requested→expected (que replicava la confecció a tots els dies del tram).
        # Sense expected_at, cau al dia d'enviament (requested_at).
        marker_d = p.expected_at or req_d
        events.append({
            'id': f'confeccio-{p.id}',
            'tipus': 'confeccio',
            'start': marker_d.isoformat(),
            'end': marker_d.isoformat(),
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

    # ── Font 'fitting' (FittingSession) — UN bloc horari per ASSISTENT (com les tasques);
    # sense hora → marcador de dia (retrocompat). Peça 3 E1/E3: les Tancades es pinten (verd);
    # les Anul·lades segueixen excloses. ──
    import datetime as _dt

    def _eff_minutes(s):
        """E2 — durada REAL (finished_at − started_at) si disponible; si no, la prevista."""
        if s.started_at and s.finished_at:
            m = (s.finished_at - s.started_at).total_seconds() / 60
            if m > 0:
                return int(round(m))
        return s.duracio_minuts or 0

    fitting_qs = (FittingSession.objects
                  .select_related('model', 'garment_set')
                  .prefetch_related('attendees__user')
                  .exclude(estat='Anullada'))
    if start_d:
        fitting_qs = fitting_qs.filter(data__gte=start_d)
    if end_d:
        fitting_qs = fitting_qs.filter(data__lte=end_d)
    if model_id_raw:
        fitting_qs = fitting_qs.filter(model_id=model_id_raw)
    # Scope (mateix criteri que les tasques): sense view_team_tasks → només on sóc assistent.
    if VIEW_TEAM_TASKS not in get_capabilities(request.user):
        profile = getattr(request.user, 'profile', None)
        fitting_qs = fitting_qs.filter(attendees=profile) if profile is not None else fitting_qs.none()
    fitting_list = list(fitting_qs)
    # Dependència TOVA: expected_at de la confecció del mateix (model, fase). Es consulta a banda
    # (la Production pot caure FORA del rang visible). Si n'hi ha més d'una, en guardem la més tardana.
    model_ids = {f.model_id for f in fitting_list if f.model_id}
    expected_by_key = {}
    if model_ids:
        for p in (Production.objects.filter(model_id__in=model_ids, expected_at__isnull=False)
                  .values('model_id', 'phase', 'expected_at')):
            key = (p['model_id'], p['phase'])
            prev = expected_by_key.get(key)
            if prev is None or p['expected_at'] > prev:
                expected_by_key[key] = p['expected_at']
    # ── Partició convocatòria (C4): sessions soltes (convocatoria=None) → bloc P5 intacte;
    # sessions amb convocatoria → agregades en UN event per (convocatòria × assistent). ──
    individuals = [s for s in fitting_list if s.convocatoria is None]
    conv_groups = {}
    for s in fitting_list:
        if s.convocatoria is not None:
            conv_groups.setdefault(s.convocatoria, []).append(s)

    for s in individuals:
        target = s.model.codi_intern if s.model_id else (s.garment_set.codi_base if s.garment_set_id else '?')
        titol = f'{target} · fitting {s.fase}'
        link = f'/fittings/{s.id}'
        exp = expected_by_key.get((s.model_id, s.fase)) if s.model_id else None
        avis_abans = bool(exp and s.data and s.data < exp)   # avís TOVA (no en_risc)
        tancada = s.estat == 'Tancada'
        eff = _eff_minutes(s)
        if s.start_time and eff:
            base = timezone.make_aware(_dt.datetime.combine(s.data, s.start_time))
            start_dt = timezone.localtime(base).isoformat()
            end_dt = timezone.localtime(base + _dt.timedelta(minutes=eff)).isoformat()
            all_day = False
        else:
            start_dt = s.data.isoformat()
            end_dt = s.data.isoformat()
            all_day = True
        meta_base = {
            'model_id': s.model_id,
            'garment_set_id': s.garment_set_id,
            'fase': s.fase,
            'estat': s.estat,
            'duracio_minuts': s.duracio_minuts,
            'durada_real': eff if (s.started_at and s.finished_at) else None,
            'lloc': s.lloc,
            'avis_abans_confeccio': avis_abans,
            'tancada': tancada,
        }
        attendees_list = list(s.attendees.all())
        if attendees_list:
            for att in attendees_list:
                events.append({
                    'id': f'fitting-{s.id}-{att.id}',
                    'tipus': 'fitting', 'tancada': tancada,
                    'start': start_dt, 'end': end_dt, 'titol': titol,
                    'tecnic_id': att.id,
                    'tecnic_nom': att.user.get_full_name() or att.user.username,
                    'color': COLOR_FITTING_CLOSED if tancada else (att.color_avatar or '#888888'),
                    'link': link, 'en_risc': False, 'all_day': all_day,
                    'meta': meta_base,
                })
        else:
            # Sessió sense attendees interns: event únic (retrocompat, color fix de tipus).
            events.append({
                'id': f'fitting-{s.id}',
                'tipus': 'fitting', 'tancada': tancada,
                'start': start_dt, 'end': end_dt, 'titol': titol,
                'tecnic_id': None, 'tecnic_nom': None,
                'color': COLOR_FITTING_CLOSED if tancada else COLOR_FITTING,
                'link': link, 'en_risc': False, 'all_day': all_day,
                'meta': meta_base,
            })

    # ── Convocatòria (C4 + G7/4b): per cada (convocatòria × assistent) emetem UN marcador per
    # SESSIÓ REAL del grup (no un bloc/rang). Sense assistent intern → marcadors amb tecnic_id=None. ──
    for convocatoria, grup in conv_groups.items():
        per_att = {}   # att_id -> {'att', 'sessions'}
        for s in grup:
            for att in s.attendees.all():
                slot = per_att.setdefault(att.id, {'att': att, 'sessions': []})
                slot['sessions'].append(s)
        # grups a emetre: [(att|None, sessions)]. Sense attendees → un sol grup amb att=None.
        emis = ([(slot['att'], slot['sessions']) for slot in per_att.values()]
                if per_att else [(None, list(grup))])
        for att, sessions in emis:
            sessions_grup = sorted(sessions, key=lambda x: (x.data, x.start_time or _dt.time.min))
            # E4: n = sessions NO anul·lades (les Anul·lades ja s'han exclòs del queryset).
            n = len(sessions_grup)
            model_ids_grup = [s.model_id for s in sessions_grup]
            # G7 (Bloc 4 / 4b): UN marcador per cada FittingSession REAL del grup, cada un al
            # seu propi dia (start==end, com el fitting individual a dalt). NO un rang/bloc:
            # els dies SENSE sessió queden buits (abans inRange replicava l'all-day a tot el
            # rang primera→última). Cada marcador conserva meta de convocatòria (UUID + n_models)
            # perquè el front pugui agrupar-los visualment si vol.
            for s in sessions_grup:
                s_tancada = s.estat == 'Tancada'
                eff = _eff_minutes(s)
                if s.start_time and eff:
                    base = timezone.make_aware(_dt.datetime.combine(s.data, s.start_time))
                    start_dt = timezone.localtime(base).isoformat()
                    end_dt = timezone.localtime(base + _dt.timedelta(minutes=eff)).isoformat()
                    all_day = False
                else:
                    start_dt = s.data.isoformat()
                    end_dt = s.data.isoformat()
                    all_day = True
                avis = bool(s.model_id and expected_by_key.get((s.model_id, s.fase)) and
                            s.data and s.data < expected_by_key[(s.model_id, s.fase)])
                meta = {
                    'convocatoria': str(convocatoria),
                    'n_models': n,
                    'model_id': s.model_id,
                    'model_ids': model_ids_grup,
                    'fase': s.fase,
                    'lloc': s.lloc,
                    'avis_abans_confeccio': avis,
                    'tancada': s_tancada,
                    'duracio_minuts': s.duracio_minuts,
                    'durada_real': eff if (s.started_at and s.finished_at) else None,
                }
                titol = f'Fitting · {n} models · {s.fase}'
                if att is not None:
                    events.append({
                        'id': f'fitting-conv-{convocatoria}-{att.id}-{s.id}',
                        'tipus': 'fitting', 'tancada': s_tancada,
                        'start': start_dt, 'end': end_dt, 'titol': titol,
                        'tecnic_id': att.id,
                        'tecnic_nom': att.user.get_full_name() or att.user.username,
                        'color': COLOR_FITTING_CLOSED if s_tancada else (att.color_avatar or '#888888'),
                        'link': '/fittings', 'en_risc': False, 'all_day': all_day,
                        'meta': meta,
                    })
                else:
                    events.append({
                        'id': f'fitting-conv-{convocatoria}-{s.id}',
                        'tipus': 'fitting', 'tancada': s_tancada,
                        'start': start_dt, 'end': end_dt, 'titol': titol,
                        'tecnic_id': None, 'tecnic_nom': None,
                        'color': COLOR_FITTING_CLOSED if s_tancada else COLOR_FITTING,
                        'link': '/fittings', 'en_risc': False, 'all_day': all_day,
                        'meta': meta,
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
        # C4d — el reorder manual és l'ACK del planificador: neteja el marcador "+" dels
        # models reordenats (l'ordre torna a ser el seu, ja no "s'ha mogut sol per inici").
        Model.objects.filter(pk__in=model_ids).update(reanchored_by_start=False)
    results = plan_service.recompute_for_technicians([int(assignee_id)])
    return Response({'ok': True, 'assignee_id': int(assignee_id),
                     'result': results.get(int(assignee_id))}, status=http_status.HTTP_200_OK)


# ── Sprint multi-assign — wizard d'assignació (task_type × persona × data opcional) ──────
@api_view(['GET'])
@permission_classes([_DefineTasks])
def plan_eligible_technicians_view(request):
    """GET /api/v1/plan/eligible-technicians/?task_type=<code> — tècnics elegibles per a un
    task_type, ordenats pel més lliure primer. Gated `define_tasks`.

    Elegibilitat via get_allowed_task_types (bypass admin per rol inclòs) — NO ?can_task=,
    que és containment pur i exclouria els admins amb permisos.tasks buit.
    Annotate sense N+1 sobre la relació inversa ModelTask.assignee (related_name='assigned_tasks'):
      disponible_des_de = MAX(planned_end) de les tasques no-Done; NULL = lliure ara.
      models_en_cua     = COUNT DISTINCT model de les tasques no-Done.
    Ordre: disponible_des_de ASC NULLS FIRST."""
    code = request.query_params.get('task_type')
    if not code:
        return Response({'error': 'task_type requerit.'}, status=http_status.HTTP_400_BAD_REQUEST)
    from fhort.accounts.capabilities import get_allowed_task_types
    from django.db.models import Max, Count, Q, F

    actives = ['Pending', 'InProgress', 'Paused']
    base = UserProfile.objects.filter(user__is_active=True).select_related('user')
    eligible_ids = [p.id for p in base if code in get_allowed_task_types(p.user)]

    flt = Q(assigned_tasks__status__in=actives)
    qs = (UserProfile.objects.filter(pk__in=eligible_ids).select_related('user')
          .annotate(disponible_des_de=Max('assigned_tasks__planned_end', filter=flt),
                    models_en_cua=Count('assigned_tasks__model', distinct=True, filter=flt))
          .order_by(F('disponible_des_de').asc(nulls_first=True), 'id'))

    out = [{
        'profile_id': p.id,
        'full_name': p.user.get_full_name() or p.user.get_username(),
        'color_avatar': getattr(p, 'color_avatar', None),
        'disponible_des_de': (timezone.localtime(p.disponible_des_de).isoformat()
                              if p.disponible_des_de else None),
        'models_en_cua': p.models_en_cua,
    } for p in qs]
    return Response(out, status=http_status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([_ScheduleFittings])
def plan_eligible_attendees_view(request):
    """GET /api/v1/plan/eligible-attendees/ — assistents elegibles per a un fitting: usuaris
    actius amb la capability `schedule_fittings` (via get_capabilities; bypass admin inclòs).
    Gated `schedule_fittings`. Retorn: [{profile_id, full_name, color_avatar}]."""
    base = UserProfile.objects.filter(user__is_active=True).select_related('user').order_by('id')
    out = [{
        'profile_id': p.id,
        'full_name': p.user.get_full_name() or p.user.get_username(),
        'color_avatar': getattr(p, 'color_avatar', None),
    } for p in base if SCHEDULE_FITTINGS in get_capabilities(p.user)]
    return Response(out, status=http_status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([_DefineTasks])
def plan_assign_batch_view(request):
    """POST /api/v1/plan/assign-batch/ — wizard multi-assignació. Gated `define_tasks`.
    Body: {model_ids:[int], assignacions:[{task_type_code, assignee_profile_id,
           planned_start?, planned_end?}]}. 400 si planned_start i planned_end alhora."""
    d = request.data
    model_ids = d.get('model_ids')
    assignacions = d.get('assignacions')
    if not isinstance(model_ids, list) or not model_ids:
        return Response({'error': 'model_ids (llista no buida) requerit.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    if not isinstance(assignacions, list) or not assignacions:
        return Response({'error': 'assignacions (llista no buida) requerit.'},
                        status=http_status.HTTP_400_BAD_REQUEST)
    for a in assignacions:
        if not isinstance(a, dict) or not a.get('task_type_code') or not a.get('assignee_profile_id'):
            return Response({'error': 'cada assignació requereix task_type_code i assignee_profile_id.'},
                            status=http_status.HTTP_400_BAD_REQUEST)
    profile = getattr(request.user, 'profile', None)
    try:
        out = plan_service.assign_batch(model_ids=model_ids, assignacions=assignacions, actor=profile)
    except ValueError as e:
        return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)
    return Response(out, status=http_status.HTTP_200_OK)


# ── Sprint M3 — Calendari-Gantt de projecte (una barra per MODEL, eix=dies) ──────────────────
class _ViewTeamTasks(HasCapability):
    required_capability = VIEW_TEAM_TASKS


def _effective_responsable(tasks, model):
    """Tècnic que 'porta' el model (color del Gantt): assignee de tasca InProgress → assignee
    no-Done majoritari → Model.responsable. Retorna (id, nom, color) o (None, None, None)."""
    from collections import Counter
    for tk in tasks:                                   # 1) tasca activa
        if tk.status == 'InProgress' and tk.assignee_id:
            a = tk.assignee
            return a.id, a.nom_complet, a.color_avatar
    cnt = Counter(tk.assignee_id for tk in tasks if tk.status != 'Done' and tk.assignee_id)
    if cnt:                                            # 2) no-Done majoritari
        aid = cnt.most_common(1)[0][0]
        a = next(tk.assignee for tk in tasks if tk.assignee_id == aid)
        return a.id, a.nom_complet, a.color_avatar
    if model.responsable_id:                           # 3) responsable del model
        r = model.responsable
        return r.id, r.nom_complet, r.color_avatar
    return None, None, None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gantt_view(request):
    """GET /api/v1/plan/gantt/ — Gantt de projecte: UNA barra per model, eix=DIES (no hores).
    Per model: start (consumption_started_at real | predicted_start), end (predicted_end), pct
    (tasques Done/total), fase, responsable efectiu (color=tècnic), data_objectiu (línia vermella),
    fites [{tipus proto|fitting, data, estat}], esperes [{from,to}] (finestra de confecció externa
    Production: requested_at → delivered_at|expected_at). Filtres: ?model_id ?responsable
    ?collection ?temporada. CAPA DE LECTURA (drag = sprint posterior).

    Visibilitat (2 modes):
      - sense ?mine → Gantt d'EQUIP: exigeix view_team_tasks (comportament PM idèntic a abans).
      - ?mine=true → Gantt PERSONAL: acotat als models on l'usuari és assignee de tasca (reusa
        scope_model_task_queryset, mateix scope que el tauler/calendari). NO exigeix view_team_tasks.
    """
    qp = request.query_params
    mine = qp.get('mine') == 'true'
    if not mine and VIEW_TEAM_TASKS not in get_capabilities(request.user):
        return Response({'detail': "No tens permís per veure el Gantt d'equip."},
                        status=http_status.HTTP_403_FORBIDDEN)
    qs = (Model.objects.all().select_related('responsable')
          .prefetch_related('model_tasks', 'model_tasks__assignee', 'model_tasks__task_type',
                            'productions', 'fitting_sessions'))
    if mine:
        # Models on l'usuari és assignee de tasca (font única de scope, igual que el tauler).
        my_models = scope_model_task_queryset(ModelTask.objects.all(), request.user).values('model_id')
        qs = qs.filter(pk__in=my_models)
    if qp.get('model_id'):
        qs = qs.filter(pk=qp['model_id'])
    if qp.get('responsable'):
        qs = qs.filter(responsable_id=qp['responsable'])
    if qp.get('collection'):
        qs = qs.filter(collection=qp['collection'])
    if qp.get('temporada'):
        qs = qs.filter(temporada=qp['temporada'])

    out = []
    for m in qs:
        tasks = list(m.model_tasks.all())
        total = len(tasks)
        done = sum(1 for tk in tasks if tk.status == 'Done')
        # Maduresa = % de tasques Done sobre el total. Base consistent (recompte/recompte),
        # FITAT 0-100 per construcció. (Abans es barrejava minuts consumits/estimats → >100%.)
        pct = round(100 * done / total) if total else 0
        # Pròxima tasca pendent (primera no-Done en ordre [model, order]) → etiqueta de la pastilla.
        # Reusem la MATEIXA tasca per exposar-ne el planned_end (data a la qual s'enfronta el model).
        next_tk = next((tk for tk in tasks if tk.status != 'Done'), None)
        next_task = next_tk.task_type.code if next_tk else None
        next_task_date = (next_tk.planned_end.date().isoformat()
                          if next_tk and next_tk.planned_end else None)
        # C4c — barres derivades del PLA MATERIALITZAT (font única): min(planned_start) /
        # max(planned_end) de les tasques del model, fallback consumption_started_at. NO es
        # llegeix la columna predicted_* (queda per als altres consumidors; V2), només es deixa
        # d'usar aquí perquè el Gantt sigui pur lector del pla.
        planned_starts = [tk.planned_start for tk in tasks if tk.planned_start]
        planned_ends = [tk.planned_end for tk in tasks if tk.planned_end]
        plan_start = min(planned_starts).date() if planned_starts else None
        plan_end = max(planned_ends).date() if planned_ends else None
        start = plan_start or (m.consumption_started_at.date() if m.consumption_started_at else None)
        end = plan_end or start
        start = start or end
        if not start or not end:
            continue                                   # sense pla ancorable → fora del Gantt (C4a)
        resp_id, resp_nom, resp_color = _effective_responsable(tasks, m)
        objectiu = m.data_objectiu
        fites, esperes = [], []
        for p in m.productions.all():
            d = p.delivered_at.date() if p.delivered_at else p.expected_at
            if d:
                fites.append({'tipus': 'proto', 'data': d.isoformat(), 'estat': p.status})
            w_from = p.requested_at.date() if p.requested_at else None
            w_to = p.delivered_at.date() if p.delivered_at else p.expected_at
            if w_from and w_to and w_to > w_from:
                esperes.append({'from': w_from.isoformat(), 'to': w_to.isoformat(), 'tipus': 'confeccio'})
        for f in m.fitting_sessions.all():
            if f.data:
                fites.append({'tipus': 'fitting', 'data': f.data.isoformat(), 'estat': f.estat})
        fites.sort(key=lambda x: x['data'])
        out.append({
            'model_id': m.id, 'codi': m.codi_intern, 'nom': m.nom_prenda,
            'fase': m.fase_actual, 'pct': pct,
            'start': start.isoformat(), 'end': end.isoformat(),
            'data_objectiu': objectiu.isoformat() if objectiu else None,
            'responsable_id': resp_id, 'responsable_nom': resp_nom, 'responsable_color': resp_color,
            'next_task': next_task, 'next_task_date': next_task_date,
            'en_risc': bool(end and objectiu and end > objectiu),
            'collection': m.collection or '', 'temporada': m.temporada,
            'fites': fites, 'esperes': esperes,
            # C4d — marcador "+": el model s'ha mogut sol al pla per un inici real.
            'reanchored_by_start': m.reanchored_by_start,
        })
    # C4c — ORDRE DE FILES = el del PLA (planned_start asc), servit pel backend. El client ja
    # no reordena per defecte (lliurament/fita/fase queden com a vistes alternatives explícites).
    out.sort(key=lambda x: (x['start'], x['codi']))
    return Response({'models': out, 'today': _date.today().isoformat()})
