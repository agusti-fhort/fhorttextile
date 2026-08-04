"""Precedent de col·locació de cotes POM (F2) — endpoints de lectura (cascada) i escriptura.

ENLLAÇ OBJECT-LEVEL (decisió Agus): la procedència pertany al SKETCH, no al document. Una
fitxa pot dur sketches de dos items alhora; l'objecte és l'única granularitat unívoca. El
frontend etiqueta cada objecte sketch importat amb el seu `sourceItemFitxer` i és aquest id
el que arriba aquí a la URL. La col·locació viu al CATÀLEG (`POMPlacement` penja d'`ItemFitxer`,
D1); un document hi accedeix a través de l'ItemFitxer d'origen del seu objecte sketch.

- GET  /api/v1/item-fitxers/<item_id>/pom-placements/?view_slot=<slot>&model_id=<model_id>
    Cascada de resolució:
      1. EXACTE  : precedents d'AQUEST ItemFitxer.
      2. GERMANA : precedents d'altres ItemFitxer del MATEIX GarmentTypeItem (marcats
                   `derivat=True`).
    Amb `model_id`, resol `bm_id` per materialitzar la cota VIVA de F1; un POM del precedent
    que el model no té va a `no_al_model` (a la llista de treball manual, mai crash, mai
    absència silenciosa).
- POST /api/v1/item-fitxers/<item_id>/pom-placements/   (gate CONFIGURE)
    Desa la cota actual com a precedent d'AQUEST ItemFitxer.

FRONTERA G1: cap camí escriu res al POM ni a BaseMeasurement — pura geometria normalitzada.
"""
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.pom.models import MeasurementLayer

from .models import BaseMeasurement, ItemFitxer, POMPlacement


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def item_fitxer_pom_placements_view(request, item_id):
    """/api/v1/item-fitxers/<item_id>/pom-placements/  ·  GET (cascada) + POST (desar precedent)."""
    item = get_object_or_404(
        ItemFitxer.objects.select_related('garment_type_item'), pk=item_id)
    if request.method == 'GET':
        return _cascada(request, item)
    return _desar_precedent(request, item)


def _cascada(request, item):
    view_slot = (request.query_params.get('view_slot') or '').strip()
    if not view_slot:
        return Response({'error': 'view_slot és obligatori.'}, status=400)

    gti_id = item.garment_type_item_id
    qs = POMPlacement.objects.filter(view_slot=view_slot).select_related(
        'pom', 'pom__pom_global')

    # FASE_2/C1-ins — la CASCADA també indexa per la clau completa. Fins ara col·lapsava
    # abans d'arribar al `bm_by_pom` de sota: dues cotes del mateix POM en capes o instàncies
    # diferents es trepitjaven aquí dins, i el precedent que sobrevivia el decidia l'ordre de
    # la consulta. La sisa dreta i l'esquerra són DUES fletxes al mateix croquis, i la
    # cascada les ha de saber portar totes dues.
    def clau(p):
        return (p.pom_id, p.capa, p.instancia)

    # EXACTE: precedents d'aquest ItemFitxer (una veritat de catàleg, D1).
    exacte = {clau(p): p for p in qs.filter(item_fitxer=item)}
    # GERMANA: altres ItemFitxer del mateix GarmentTypeItem (D7). L'exacte hi guanya.
    germana = {}
    if gti_id:
        for p in qs.filter(item_fitxer__garment_type_item_id=gti_id).exclude(
                item_fitxer=item).order_by('item_fitxer_id', 'id'):
            germana.setdefault(clau(p), p)

    merged = {}
    for k, p in germana.items():
        merged[k] = (p, True)      # derivat de peça germana
    for k, p in exacte.items():
        merged[k] = (p, False)     # precedent exacte d'aquest item

    # bm_id del model destí (opcional) → materialitzar la cota VIVA de F1 (pomId+bmId).
    model_id = request.query_params.get('model_id')
    # C2/Onada 1 — CLAU COMPOSTA: `POMPlacement` porta capa des de C1 i la cota es
    # materialitza contra la mesura de la SEVA capa. Per POM sol, una cota col·locada sobre
    # el folre rebria el `bm_id` de l'exterior i el dibuix quedaria lligat a una altra
    # mesura —el pitjor cas d'aquesta vista, perquè no peta: pinta.
    # FASE_2/C1-ins — i la INSTÀNCIA al mateix mapa i pel mateix argument: una cota de la
    # sisa esquerra rebria el `bm_id` de la dreta i el dibuix quedaria lligat a una altra
    # mesura. Creixen alhora, perquè és la mateixa clau a les dues bandes.
    bm_by_pom = {}
    if model_id:
        bm_by_pom = {
            (p, c, ins): i for p, c, ins, i in BaseMeasurement.objects.filter(
                model_id=model_id, is_active=True).values_list(
                    'pom_id', 'capa', 'instancia', 'id')
        }

    placements, no_al_model = [], []
    for (pom_id, _capa, _inst), (p, derivat) in merged.items():
        codi = p.pom.pom_global.codi if p.pom.pom_global_id else ''
        bm_id = bm_by_pom.get((pom_id, p.capa, p.instancia))
        if model_id and bm_id is None:
            # El POM del precedent NO existeix al model destí → a llista manual, mai crash.
            no_al_model.append({'pom_id': pom_id, 'codi': codi})
            continue
        placements.append({
            'pom_id': pom_id, 'bm_id': bm_id, 'codi': codi,
            'x1': p.x1, 'y1': p.y1, 'x2': p.x2, 'y2': p.y2,
            'label_dx': p.label_dx, 'label_dy': p.label_dy,
            'source_kind': p.source_kind, 'derivat': derivat,
        })

    return Response({
        'view_slot': view_slot,
        'item_fitxer': item.id,
        'placements': placements,
        'no_al_model': no_al_model,
    })


def _desar_precedent(request, item):
    # Escriptura al CATÀLEG → gate CONFIGURE (coherent amb ItemFitxerViewSet: el catàleg és
    # configuració).
    from fhort.accounts.capabilities import CONFIGURE, get_capabilities
    if CONFIGURE not in get_capabilities(request.user):
        return Response(
            {'error': "Cal la capacitat 'configure' per desar un precedent de catàleg."},
            status=403)

    data = request.data
    try:
        pom_id = int(data['pom_id'])
        coords = {k: float(data[k]) for k in ('x1', 'y1', 'x2', 'y2')}
        label_dx = float(data.get('label_dx', 0))
        label_dy = float(data.get('label_dy', 0))
    except (KeyError, TypeError, ValueError):
        return Response(
            {'error': 'pom_id i x1..y2 són obligatoris i numèrics.'}, status=400)

    view_slot = slugify(data.get('view_slot') or '')
    if not view_slot:
        return Response({'error': 'view_slot és obligatori.'}, status=400)

    source_kind = data.get('source_kind')
    if source_kind not in (POMPlacement.SOURCE_VECTOR, POMPlacement.SOURCE_RASTER):
        source_kind = POMPlacement.SOURCE_VECTOR

    # El POM ha d'existir (FK PROTECT): validem sense escriure-hi res (frontera G1).
    from fhort.pom.models import POMMaster
    if not POMMaster.objects.filter(pk=pom_id).exists():
        return Response({'error': 'pom_id no existeix.'}, status=400)

    perfil = getattr(request.user, 'profile', None)
    # FASE_3/C1-ins — la clau del lookup, alineada amb la unicitat real
    # `(item_fitxer, pom, view_slot, capa, instancia)`. Literals: el body és
    # `{'pom_id', 'view_slot', coords}` i no porta eixos fins a C4-ins.
    #
    # Era un dels vuit germans de l'accident armat, i el més visible de tots: la LECTURA
    # germana d'aquesta mateixa vista ja indexa per la clau completa des de FASE_2 —serveix
    # dues fletxes distintes— i l'escriptura se les hauria fusionat en una en desar. Cotes
    # que es veuen i que en gravar desapareixen és pitjor que no poder-les fer.
    obj, created = POMPlacement.objects.update_or_create(
        item_fitxer=item, pom_id=pom_id, view_slot=view_slot,
        capa=MeasurementLayer.SLUG_DEFECTE, instancia='',
        defaults={**coords, 'label_dx': label_dx, 'label_dy': label_dy,
                  'source_kind': source_kind, 'creat_per': perfil})

    return Response({
        'id': obj.id, 'created': created, 'item_fitxer': item.id,
        'pom_id': pom_id, 'view_slot': view_slot, 'source_kind': source_kind,
    }, status=201 if created else 200)
