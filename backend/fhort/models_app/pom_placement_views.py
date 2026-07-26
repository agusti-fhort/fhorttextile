"""Precedent de col·locació de cotes POM (F2) — endpoints de lectura (cascada) i escriptura.

La col·locació d'una cota viu al CATÀLEG (`POMPlacement` penja d'`ItemFitxer`, D1). Un
document (`ModelFitxer`) hi accedeix a través de la seva procedència `derivat_de_item`:

- GET  → CASCADA de resolució per a un `view_slot`:
    1. EXACTE   : precedents de l'ItemFitxer d'origen (via `derivat_de_item`).
    2. GERMANA  : precedents d'altres ItemFitxer del MATEIX `GarmentTypeItem`, marcats
                  `derivat=True` a la resposta.
    3. La resta (POMs del model sense precedent en aquest slot) NO és absència silenciosa:
       el frontend els deixa a la llista de treball (reutilitza `cotesColocades` de F1).
- POST → desa la cota actual com a precedent a l'ItemFitxer d'origen (acte conscient, D1).

FRONTERA G1: cap camí escriu res al POM ni a BaseMeasurement. La cascada és NOMÉS LECTURA
sobre el POM; el precedent és pura geometria normalitzada.
"""
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import BaseMeasurement, ModelFitxer, POMPlacement


def _resolve_item_fitxer(mf):
    """L'ItemFitxer d'origen del document, resseguint la cadena de versions.

    `save_model_file` NO propaga `derivat_de_item` als fitxers-versió (només el porta el que
    va crear `usar_al_model`), però sí encadena `versio_anterior`. Sense aquest recorregut, un
    document que s'ha desat un cop perdria la seva procedència de catàleg. Retorna l'ItemFitxer
    o None."""
    seen = set()
    cur = mf
    while cur is not None and cur.id not in seen:
        if cur.derivat_de_item_id:
            return cur.derivat_de_item
        seen.add(cur.id)
        cur = cur.versio_anterior
    return None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def model_fitxer_pom_placements_view(request, mf_id):
    """/api/v1/model-fitxers/<mf_id>/pom-placements/  ·  GET (cascada) + POST (desar precedent)."""
    mf = get_object_or_404(
        ModelFitxer.objects.select_related('model', 'derivat_de_item'), pk=mf_id)
    if request.method == 'GET':
        return _cascada(request, mf)
    return _desar_precedent(request, mf)


def _cascada(request, mf):
    view_slot = (request.query_params.get('view_slot') or '').strip()
    if not view_slot:
        return Response({'error': 'view_slot és obligatori.'}, status=400)

    item = _resolve_item_fitxer(mf)
    gti_id = item.garment_type_item_id if item else mf.model.garment_type_item_id

    qs = POMPlacement.objects.filter(view_slot=view_slot).select_related(
        'pom', 'pom__pom_global')

    # EXACTE: precedents de l'ItemFitxer d'origen (una veritat, D1).
    exacte = {p.pom_id: p for p in qs.filter(item_fitxer=item)} if item else {}
    # GERMANA: altres ItemFitxer del mateix GarmentTypeItem (D7). L'exacte hi guanya.
    germana = {}
    if gti_id:
        germ_qs = qs.filter(item_fitxer__garment_type_item_id=gti_id)
        if item:
            germ_qs = germ_qs.exclude(item_fitxer=item)
        for p in germ_qs.order_by('item_fitxer_id', 'id'):
            germana.setdefault(p.pom_id, p)

    merged = {}
    for pom_id, p in germana.items():
        merged[pom_id] = (p, True)      # derivat de peça germana
    for pom_id, p in exacte.items():
        merged[pom_id] = (p, False)     # precedent exacte de l'item d'origen

    # bm_id del model destí per pom → permet materialitzar la cota VIVA de F1 (pomId+bmId).
    bm_by_pom = dict(BaseMeasurement.objects.filter(
        model=mf.model, is_active=True).values_list('pom_id', 'id'))

    placements, no_al_model = [], []
    for pom_id, (p, derivat) in merged.items():
        codi = p.pom.pom_global.codi if p.pom.pom_global_id else ''
        bm_id = bm_by_pom.get(pom_id)
        if bm_id is None:
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
        'origen_item_fitxer': item.id if item else None,
        'placements': placements,
        'no_al_model': no_al_model,
    })


def _desar_precedent(request, mf):
    # Escriptura al CATÀLEG → gate CONFIGURE (coherent amb ItemFitxerViewSet: el catàleg és
    # configuració). L'acció és deliberada; sense derivat_de_item ni tan sols és possible.
    from fhort.accounts.capabilities import CONFIGURE, get_capabilities
    if CONFIGURE not in get_capabilities(request.user):
        return Response(
            {'error': "Cal la capacitat 'configure' per desar un precedent de catàleg."},
            status=403)

    item = _resolve_item_fitxer(mf)
    if item is None:
        return Response(
            {'error': "Aquest document no prové d'un sketch de catàleg "
                      "(derivat_de_item buit): no es pot desar precedent."},
            status=400)

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
    obj, created = POMPlacement.objects.update_or_create(
        item_fitxer=item, pom_id=pom_id, view_slot=view_slot,
        defaults={**coords, 'label_dx': label_dx, 'label_dy': label_dy,
                  'source_kind': source_kind, 'creat_per': perfil})

    return Response({
        'id': obj.id, 'created': created, 'item_fitxer': item.id,
        'pom_id': pom_id, 'view_slot': view_slot, 'source_kind': source_kind,
    }, status=201 if created else 200)
