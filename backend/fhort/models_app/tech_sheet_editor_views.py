"""Editor de fitxa tècnica — estat + lock col·laboratiu (full-screen al frontend).

NOU. No toca tech_sheet_views.py (Sprint S17, extracció IA per CREAR models). Aquí gestionem
la fitxa persistent d'un Model existent:

- TechSheetDetailView  GET  models/<model_id>/tech-sheet/         → get_or_create + serialitza
- TechSheetLockView    POST models/<model_id>/tech-sheet/lock/    → adquireix el lock (o força a >30min)
- TechSheetUnlockView  POST models/<model_id>/tech-sheet/unlock/  → allibera (propietari o `configure`)

El lock és cooperatiu (no transaccional fort): és una porta UX per evitar dos editors alhora,
amb caducitat automàtica a 30 min perquè una pestanya tancada sense unlock no bloquegi per sempre.
"""
import datetime

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fhort.accounts.capabilities import CONFIGURE, get_capabilities

from .models import Model
from .tech_sheet_models import TechSheet
from .tech_sheet_serializers import TechSheetSerializer

# Caducitat del lock: passat aquest temps sense unlock, un altre usuari el pot forçar.
LOCK_TTL = datetime.timedelta(minutes=30)


def _get_sheet(model_id):
    """Retorna (o crea) la fitxa del model. 404 si el model no existeix."""
    model = get_object_or_404(Model, pk=model_id)
    sheet, _ = TechSheet.objects.get_or_create(model=model)
    return sheet


class TechSheetDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, model_id):
        sheet = _get_sheet(model_id)
        return Response(TechSheetSerializer(sheet).data)


class TechSheetLockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, model_id):
        sheet = _get_sheet(model_id)
        now = timezone.now()
        holder = sheet.locked_by

        is_free = holder is None
        is_mine = holder is not None and holder == request.user
        is_stale = (
            holder is not None
            and sheet.locked_at is not None
            and sheet.locked_at < now - LOCK_TTL
        )

        if is_free or is_mine or is_stale:
            sheet.locked_by = request.user
            sheet.locked_at = now
            sheet.save(update_fields=['locked_by', 'locked_at', 'updated_at'])
            return Response(TechSheetSerializer(sheet).data)

        # Ocupada per un altre usuari i encara vigent → 409 amb qui i des de quan.
        return Response(
            {
                'detail': 'La fitxa està bloquejada per un altre usuari.',
                'locked_by': holder.get_username(),
                'locked_at': sheet.locked_at,
            },
            status=status.HTTP_409_CONFLICT,
        )


class TechSheetUnlockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, model_id):
        sheet = _get_sheet(model_id)
        holder = sheet.locked_by

        is_mine = holder is not None and holder == request.user
        can_override = CONFIGURE in get_capabilities(request.user)

        if holder is not None and not (is_mine or can_override):
            return Response(
                {
                    'detail': 'No pots alliberar un lock d\'un altre usuari.',
                    'locked_by': holder.get_username(),
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        sheet.locked_by = None
        sheet.locked_at = None
        sheet.save(update_fields=['locked_by', 'locked_at', 'updated_at'])
        return Response(TechSheetSerializer(sheet).data)
