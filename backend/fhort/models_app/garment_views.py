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

── L'ESCRIPTURA (SET-2/R11, 2026-08-11) ────────────────────────────────────────────────
POST   /api/v1/models/<model_id>/peces/          {codi, nom?, ordre?}
PATCH  /api/v1/models/<model_id>/peces/<peca_id>/ {nom?, ordre?, size_system?,
                                                   grading_rule_set?, size_run_model?,
                                                   base_size_label?}
DELETE /api/v1/models/<model_id>/peces/<peca_id>/

El POST i el PATCH tornen la peça RESOLTA, amb la MATEIXA forma que cada element de `peces`
del GET: qui pinta no ha de saber dos formats, i després d'escriure ha de poder repintar
sense tornar a demanar la llista.

🔑 **`null` EXPLÍCIT vol dir «torna a heretar»; el camp ABSENT vol dir «no toquis».** És la
distinció que fa possible desheretar: sense ella, un PATCH que envia només el camp que canvia
no podria mai buidar-ne un altre, i un que els enviés tots convertiria cada herència en una
declaració. Enviar `{"size_run_model": null}` retorna la peça a l'herència del model; no
enviar la clau la deixa com estigui.

ELS CODIS D'ERROR, que són el contracte de debò (el text del missatge pot canviar):
  · 400 `garment_mare_no_te_fila`   — `codi` buit. La mare és el model (D3).
  · 400 `talles_desconegudes`       — el run porta talles que el sistema no coneix. És la
                                      PORTA ÚNICA del model (S24b): la peça es comporta
                                      exactament com el model, sense política pròpia.
  · 400 `referencia_no_trobada`     — el `size_system`/`grading_rule_set` no existeix.
  · 409 `garment_duplicat`          — ja hi ha una peça amb aquest codi al model.
  · 409 `garment_amb_dades`         — l'esborrat topa amb files penjades. El payload diu
                                      QUANTES i DE QUINA taula (`penjades`), perquè «no pots»
                                      sense el motiu obliga a endevinar per on buidar-la.

⚠️ AQUESTA PORTA NO TOCA CAP DE LES SET TAULES DE MESURA, i el 409 de l'esborrat ho garanteix
PER CONSTRUCCIÓ: si hi ha una sola fila penjada, no s'esborra. Les comportes de mesura
segueixen vives i aquesta porta no en depèn ni les travessa.
"""
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.models_app.models import Model, ModelGarment
from fhort.models_app.services_garment import (_peca_resolta, actualitza_peca, crea_peca,
                                               esborra_peca, peces_del_model,
                                               te_mes_duna_peca)


def _model_o_404(model_id):
    try:
        return (Model.objects
                .select_related('size_system', 'grading_rule_set')
                .prefetch_related('garments__size_system', 'garments__grading_rule_set')
                .get(pk=model_id)), None
    except Model.DoesNotExist:
        return None, Response({'error': 'Model no trobat'}, status=404)


def _peca_o_404(model, peca_id):
    peca = ModelGarment.objects.filter(model=model, pk=peca_id).first()
    if peca is None:
        # La peça d'UN ALTRE model no és «no trobada per casualitat»: el 404 és el que evita
        # que aquesta porta serveixi de sonda per saber quines peces existeixen en models que
        # no s'estan mirant.
        return None, Response({'error': 'Peça no trobada en aquest model'}, status=404)
    return peca, None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def peces_del_model_view(request, model_id):
    model, err = _model_o_404(model_id)
    if err:
        return err

    if request.method == 'POST':
        with transaction.atomic():
            peca, error = crea_peca(model, request.data or {})
            if error:
                payload, status_code = error
                return Response(payload, status=status_code)
        return Response(_peca_resolta(model, peca), status=201)

    return Response({
        'model_id': model.id,
        'te_mes_duna_peca': te_mes_duna_peca(model),
        'peces': peces_del_model(model),
    })


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def peca_del_model_view(request, model_id, peca_id):
    model, err = _model_o_404(model_id)
    if err:
        return err
    peca, err = _peca_o_404(model, peca_id)
    if err:
        return err

    if request.method == 'DELETE':
        with transaction.atomic():
            _, error = esborra_peca(model, peca)
            if error:
                payload, status_code = error
                return Response(payload, status=status_code)
        return Response(status=204)

    with transaction.atomic():
        peca, error = actualitza_peca(model, peca, request.data or {})
        if error:
            payload, status_code = error
            return Response(payload, status=status_code)
    # Es resol contra el `model` tal com estava: un PATCH de peça no toca cap camp del model,
    # o sigui que el que la peça hereta no s'ha mogut. El que sí que ha canviat és la peça, i
    # `peca` és la instància acabada de desar.
    return Response(_peca_resolta(model, peca), status=200)
