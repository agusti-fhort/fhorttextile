"""
fhort/pom/translation_views.py
LA PORTA DE LA ⓘ. Un sol GET, de lectura, per referència i en lot.

`GET /api/v1/translate/pom/?pom_ids=1,2,3&lang=ca`  (o `?pom_id=1` per a un de sol)

    {"lang": "ca",
     "items": [{"pom_id": 1, "text": "Amplada de pit", "font": "cache"}, …]}

**PER QUÈ UN PROXY I NO UNA CRIDA DEL FRONT.** La clau del proveïdor viu al servidor i no ha
d'arribar mai al bundle: qualsevol persona amb el navegador obert la podria llegir i gastar la
quota de la casa. El front no sap ni quin proveïdor hi ha.

**PER QUÈ EN LOT.** Una taula de mesures té tretze files i el catàleg en té 142: una petició per
nom serien 142 rellotges per pintar una pantalla. `font` viatja per fila perquè es pugui veure
d'on ve cada text sense entrar a la BD.

**MAI 500 PER UNA TRADUCCIÓ.** Tot el que pot fallar cap enfora ja cau al fallback dins del
servei; aquí només queda validar l'entrada.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.pom.translation_service import MAX_IDS, normalitza_lang, tradueix_poms


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def translate_poms_view(request):
    cru = request.GET.get('pom_ids') or request.GET.get('pom_id') or ''
    ids = [t for t in (x.strip() for x in cru.split(',')) if t]
    lang = normalitza_lang(request.GET.get('lang'))

    # LA POLÍTICA DEL LÍMIT, UNA I AQUÍ (F4 · 26/08). El servei ja no talla res: si això
    # deixés passar 400 ids, la resposta en portaria 400. Qui en tingui més, que ho demani en
    # més d'una petició — que és el que el client fa des del trossejat de `traduccioPomCua.js`.
    #
    # L'error DIU EL NÚMERO i porta codi propi: un client que rebi això ha de poder trossejar
    # sol sense endevinar el sostre, i `detail` es queda perquè cap lector antic es quedi mut.
    if len(ids) > MAX_IDS:
        return Response({
            'codi': 'MASSA_POMS',
            'max': MAX_IDS,
            'rebuts': len(ids),
            'detail': (f'Massa POMs en una petició: {len(ids)} (màxim {MAX_IDS}). '
                       f'Demana-les en lots de {MAX_IDS} o menys.'),
        }, status=400)

    traduccions = tradueix_poms(ids, lang)
    return Response({
        'lang': lang,
        'items': [
            {'pom_id': pom_id, 'text': dada['text'], 'font': dada['font']}
            for pom_id, dada in traduccions.items()
        ],
    })
