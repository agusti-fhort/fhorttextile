"""Repàs de fittings d'un model — taula POM × sessions (LECTURA PURA).

GET /api/v1/fitting/model/<model_id>/repas/?talla=<size_label>

La superfície de FER fittings ja existeix (l'editor G1: PieceFittingGridSerializer, eix =
versions de grading d'UNA sessió). Aquí no es reinventa: es gira l'eix. La de REPASSAR
recull TOTES les sessions fetes del model i les posa en columnes cronològiques, amb els
COMENTARIS que l'editor desa però que després ningú tornava a llegir.

Mapa de dades (H1):
  · sessions      → FittingSession (model=…), ordenades per data
  · valors        → PieceFittingLine (per PieceFitting = (sessió, model)), clau (pom, talla)
  · comentaris    → PieceFittingLine.nota   (per CEL·LA: pom+talla+sessió)
                  → FittingSession.notes    (per SESSIÓ)
                  → PieceFitting.gate_motiu (per SESSIÓ i model: motiu del gate)

Una sessió entra a la taula si té PieceFitting d'aquest model (la peça es materialitza en
OBRIR la graella: existir-hi vol dir que el fitting s'ha fet). Les anul·lades queden fora:
la taula diu què s'ha fet, no què es va programar.

L'eix de TALLA és una sola talla per vista (default: la base del model), com l'editor de
fitting, que treballa la base i deixa el multi-talla a Escalat. `talles_disponibles` viatja
al payload perquè un selector de talla sigui una peça de front, no un endpoint nou.

Res d'escriptura: cap POST/PATCH, cap efecte lateral.
"""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from fhort.models_app.models import BaseMeasurement, Model

from .models import PieceFitting, PieceFittingLine


def _ordena_talles(labels, size_run_model):
    """Ordena les talles per l'ordre del run del model; les que no hi són, al final (alfabètic)."""
    run = [s.strip() for s in (size_run_model or '').split('·') if s.strip()]
    pos = {s: i for i, s in enumerate(run)}
    return sorted(labels, key=lambda s: (pos.get(s, len(run)), s))


class FittingRepasView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, model_id):
        model = get_object_or_404(Model, pk=model_id)

        # Peces d'aquest model, en ordre CRONOLÒGIC de sessió (data; id com a desempat
        # estable per a dues sessions el mateix dia).
        peces = list(
            PieceFitting.objects
            .filter(model_id=model.id)
            .exclude(session__estat='Anullada')
            .select_related('session', 'session__responsable')
            .order_by('session__data', 'session__id')
        )
        peca_per_sessio = {p.session_id: p for p in peces}

        # Totes les línies de cop (sense N+1). Les talles disponibles surten d'aquí: són les
        # que realment s'han pres, no les que el run del model promet.
        linies = list(
            PieceFittingLine.objects
            .filter(piece_fitting__in=peces)
            .select_related('pom', 'pom__pom_global', 'piece_fitting')
        )
        talles = _ordena_talles({l.size_label for l in linies}, model.size_run_model)

        # Talla de la vista: la demanada si existeix; si no, la base del model; si la base no
        # s'ha pres mai, la primera disponible (millor una taula amb dades que una buida).
        demanada = (request.query_params.get('talla') or '').strip()
        base = (model.base_size_label or '').strip()
        talla = next((s for s in (demanada, base) if s and s in talles),
                     talles[0] if talles else None)

        sessions = [{
            'id': p.session_id,
            'piece_fitting_id': p.id,
            'data': p.session.data.isoformat() if p.session.data else None,
            'fase': p.session.fase,
            'estat': p.session.estat,
            'responsable': getattr(p.session.responsable, 'nom_complet', None),
            'notes': p.session.notes or '',          # comentari de SESSIÓ
            'gate': p.gate,
            'gate_motiu': p.gate_motiu or '',        # comentari de SESSIÓ (motiu del gate)
        } for p in peces]

        # Nomenclatura i ordre de fitxa: BaseMeasurement del model, el mateix camí que
        # l'editor G1 i la taula de mesures (una query, tres mapes).
        bm_data = list(BaseMeasurement.objects.filter(model_id=model.id)
                       .values_list('pom_id', 'ordre', 'nom_fitxa', 'id'))
        ordre_map = {p: o for p, o, _, _ in bm_data}
        nom_fitxa_map = {p: nf for p, _, nf, _ in bm_data}
        bm_id_map = {p: i for p, _, _, i in bm_data}

        # Files = els POMs que s'han fitat en aquesta talla (no el cens sencer de POMs del
        # model: una fila buida a totes les sessions no és repàs, és soroll).
        files = {}
        for l in linies:
            if l.size_label != talla:
                continue
            pom = l.pom
            fila = files.get(l.pom_id)
            if fila is None:
                fila = files[l.pom_id] = {
                    'pom_id': l.pom_id,
                    'codi': nom_fitxa_map.get(l.pom_id) or (pom.pom_code if pom else ''),
                    'pom_code': pom.pom_code if pom else '',
                    'nom_en': pom.name_en if pom else '',
                    'nom_local': pom.name_cat if pom else '',
                    'nom_fitxa': nom_fitxa_map.get(l.pom_id),
                    'bm_id': bm_id_map.get(l.pom_id),
                    'is_key': pom.is_key_measure if pom else False,
                    'valors': {},
                    'ultim_comentari': None,
                }
            fila['valors'][str(l.piece_fitting.session_id)] = {
                'valor_real': l.valor_real,
                'valor_teoric': l.valor_teoric,
                'nota': l.nota or '',
            }

        # Últim comentari per POM: es recorren les sessions en ordre cronològic i es reté
        # l'ÚLTIM no buit. No és «el de l'última sessió»: si l'última no comenta un POM, el
        # que val és el darrer que algú en va dir, i la columna diu de quina sessió ve.
        for sessio in sessions:
            sid = str(sessio['id'])
            for fila in files.values():
                nota = (fila['valors'].get(sid) or {}).get('nota') or ''
                if nota:
                    fila['ultim_comentari'] = {
                        'text': nota, 'session_id': sessio['id'], 'data': sessio['data'],
                    }

        rows = sorted(files.values(), key=lambda r: (ordre_map.get(r['pom_id'], 10 ** 9), r['pom_id']))

        return Response({
            'model': {
                'id': model.id, 'codi': model.codi_intern, 'nom': model.nom_prenda,
                'base_size_label': model.base_size_label, 'size_run_model': model.size_run_model,
            },
            'talla': talla,
            'talles_disponibles': talles,
            'sessions': sessions,
            'rows': rows,
        })
