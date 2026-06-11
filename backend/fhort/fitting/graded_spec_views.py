"""Taula de specs graduades d'un SizeFitting — per a la fitxa tècnica (F3).

GET /api/v1/fitting/<size_fitting_id>/graded-table/

Retorna la GradingVersion is_active=True del SizeFitting amb les seves GradedSpec
enriquides amb la nomenclatura POM (POMMaster → POMGlobal: codi, noms EN/CA, abreviatura,
categoria, unitat). Format pensat per pintar una taula POM × talla:
  - size_labels: ordre d'aparició de les talles
  - rows: una fila per POMMaster, amb {valors: {size_label: graded_value_cm}}

JSON directe (no cal serializer DRF). Multitenant: la consulta corre dins l'esquema del
tenant resolt pel middleware; un SizeFitting d'un altre tenant simplement no existeix aquí → 404.
"""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import GradedSpec, GradingVersion, SizeFitting


class GradedSpecTableView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sf_id):
        sf = get_object_or_404(SizeFitting, pk=sf_id)

        gv = GradingVersion.objects.filter(size_fitting=sf, is_active=True).first()
        if gv is None:
            return Response(
                {'detail': "Aquest SizeFitting no té cap GradingVersion activa."},
                status=404,
            )

        specs = (
            GradedSpec.objects
            .filter(grading_version=gv, is_active=True)
            .select_related('pom__pom_global')
            .order_by('pom_id', 'id')
        )

        # size_labels en ordre d'aparició (no alfabètic: respecta l'ordre dels specs).
        size_labels = []
        seen_sizes = set()
        # rows indexats per POMMaster (un dict de valors per talla), en ordre d'aparició.
        rows_by_pom = {}
        rows_order = []

        for s in specs:
            if s.size_label not in seen_sizes:
                seen_sizes.add(s.size_label)
                size_labels.append(s.size_label)

            pom = s.pom
            pg = pom.pom_global  # pot ser None → fallback als camps *_client del POMMaster
            if pom.id not in rows_by_pom:
                rows_by_pom[pom.id] = {
                    'pom_id': pom.id,
                    'codi': (pg.codi if pg else None) or pom.codi_client,
                    'abbreviation': (pg.abbreviation if pg else '') or '',
                    'nom_en': (pg.nom_en if pg else None) or pom.nom_client,
                    'nom_ca': (pg.nom_ca if pg else None) or pom.nom_client,
                    'categoria': (pg.categoria if pg else '') or '',
                    'unitat': (pg.unitat if pg else 'cm') or 'cm',
                    'valors': {},
                    'deltas': {},   # TS-4a: increment_applied_cm per talla (delta vs base)
                }
                rows_order.append(pom.id)

            rows_by_pom[pom.id]['valors'][s.size_label] = s.graded_value_cm
            rows_by_pom[pom.id]['deltas'][s.size_label] = float(s.increment_applied_cm or 0)

        # TS-4a: enriquiment del payload — talla base, ordre de fitxa i nomenclatura del croquis.
        # Imports locals (evita cicle fitting↔models_app a nivell de mòdul).
        from fhort.models_app.models import Model as TechModel, BaseMeasurement
        base_size = (TechModel.objects.filter(pk=sf.model_id)
                     .values_list('base_size_label', flat=True).first())
        # ordre i nom_fitxa per POMMaster del model (precedent: serializers.py FIX 4B).
        bms = BaseMeasurement.objects.filter(model_id=sf.model_id).values('pom_id', 'ordre', 'nom_fitxa')
        ordre_map = {bm['pom_id']: bm['ordre'] for bm in bms}
        nom_fitxa_map = {bm['pom_id']: bm['nom_fitxa'] for bm in bms}

        rows = [rows_by_pom[pid] for pid in rows_order]
        # ref = nomenclatura del croquis (nom_fitxa) amb fallback a abbreviation del POMGlobal.
        for row in rows:
            row['ref'] = nom_fitxa_map.get(row['pom_id']) or row['abbreviation']
        # Ordre de fitxa (POMs sense BaseMeasurement → al final).
        rows.sort(key=lambda r: ordre_map.get(r['pom_id'], 10 ** 9))

        return Response({
            'size_fitting_id': sf.id,
            'grading_version_id': gv.id,
            'grading_version_nom': gv.nom,
            'base_size': base_size,
            'size_labels': size_labels,
            'rows': rows,
        })
