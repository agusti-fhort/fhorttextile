"""LES PECES D'UN MODEL — el contracte que T7 Fase B llegirà tal qual (SET-2/T2-bis).

GET /api/v1/models/<model_id>/peces/

⚠️ AQUEST DOCSTRING ÉS LA FONT DE VERITAT DEL CONTRACTE, no el brief que el va demanar. Qui
construeixi la pantalla ha de llegir això i el test que l'acompanya
(`test_set2_t2bis_modelgarment.py`), perquè un brief no es re-verifica i un test sí.

── QUÈ TORNA ────────────────────────────────────────────────────────────────────────────
    {
      "model_id": 1320,
      "te_mes_duna_peca": false,          # el predicat, resolt aquí i no deduït pel client
      "peces": [
        {
          "id": null,                     # la MARE no té fila (D3): editar-la és editar el model
          "codi": "",                     # '' = la mare, sempre la primera de la llista
          "nom": "Pijama",                # de la mare: `Model.nom_prenda`
          "ordre": 0,
          "es_mare": true,
          "size_system":     {"valor": 3,       "etiqueta": "EU_ALPHA", "heretat": false},
          "grading_rule_set":{"valor": null,    "etiqueta": "",         "heretat": false},
          "size_run_model":  {"valor": "S·M·L", "etiqueta": "S·M·L",    "heretat": false},
          "base_size_label": {"valor": "M",     "etiqueta": "M",        "heretat": false}
        },
        { "id": 7, "codi": "02", "nom": "Pantaló", "ordre": 1, "es_mare": false,
          "size_run_model": {"valor": "S·M·L", "etiqueta": "S·M·L", "heretat": true},  ... }
      ]
    }

── LES TRES COSES QUE CAL ENTENDRE ABANS DE PINTAR-HO ──────────────────────────────────
1. **`valor` ÉS SEMPRE L'EFECTIU**, mai el cru. Si la peça no declara res, hi surt el del
   model. `heretat` diu D'ON VE, no si hi ha valor: `heretat=true` vol dir «això és del
   model, i si el model canvia això canviarà». La pantalla que editi una peça ha de poder
   distingir «hereta S·M·L» de «declara S·M·L», i per això calen els dos camps i no un.
2. **La mare sempre té `heretat=false`** a tots els camps. No és un cas especial: la mare ÉS
   el model, i un valor no hereta d'ell mateix.
3. **`etiqueta` és per pintar i no és identitat.** Qui hagi de desar o comparar, que faci
   servir `valor` (la PK per als FK). Dos SizeSystem poden compartir nom.

La resolució viu a `services_garment.valor_efectiu` i NOMÉS allà (raó del revert de
`7cc133b5`): aquesta vista no en fa cap, només la publica.

🛑 NOMÉS LECTURA. L'autoria de peces —crear-ne, batejar-les, ordenar-les— és T7 i no s'ha
construït: aquesta vista no té POST ni PATCH a posta, perquè una porta d'escriptura sense la
pantalla que la fa servir és bastida, i aquest sprint ja n'ha revertit una.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.models_app.models import Model
from fhort.models_app.services_garment import peces_del_model, te_mes_duna_peca


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def peces_del_model_view(request, model_id):
    try:
        model = (Model.objects
                 .select_related('size_system', 'grading_rule_set')
                 .prefetch_related('garments__size_system', 'garments__grading_rule_set')
                 .get(pk=model_id))
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    return Response({
        'model_id': model.id,
        'te_mes_duna_peca': te_mes_duna_peca(model),
        'peces': peces_del_model(model),
    })
