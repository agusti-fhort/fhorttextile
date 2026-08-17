"""E1/B3 — LA PORTA DE LA PRESA DE L'ESCALAT.

GET  /api/v1/fitting/model/<model_id>/presa/   → l'estat de la presa viva i els seus valors
POST /api/v1/fitting/model/<model_id>/presa/   → anota (o esborra) la presa d'una cel·la

Pas 1 del flux E1: quan arriben les peces FÍSIQUES del model es mesura cada talla i s'anota a
la columna «Fit actual» de l'Escalat. Fins avui aquella columna editava LA CORBA TEÒRICA
(`models_app.views.escalat_ajustar_talla_view`), i per això el pas 2 —«Mesurar prenda»—
hidratava del que el pas 1 acabava d'escriure: desviació zero i acceptació buida
(`docs/diagnosis/DIAGNOSI_E1_MESURA_ESCALAT.md` §3.2).

── PER QUÈ AQUESTA VISTA VIU A `fitting/` I NO A `models_app/` ─────────────────────────────
Perquè el magatzem és seu. La presa va a `PieceFittingLine`, que ja té els CINC eixos, el
teòric al costat i el veredicte a sobre; l'única cosa que li faltava era una porta que
escrivís una talla no-base sense decidir-la, i aquella la va obrir E1/B1 (guard partit:
prendre ≠ decidir). La ruta segueix el patró que aquesta app ja té per a les vistes de model
(`fitting/model/<id>/repas/`).

── LA CLAU DEL PAYLOAD ─────────────────────────────────────────────────────────────────────
`preses` s'indexa per `{clau}:{talla}`, EXACTAMENT la forma que `MeasureGrid` fa servir com a
`lineId` a l'Escalat (`fittingGridAdapter.buildEscalatRows`) i la mateixa que emetia la
resposta de l'ajust de talla. La construeix `pom.identitat.clau_mesura`, que és l'únic lloc
que sap com s'aplana una identitat de mesura: aquí no se'n fabrica cap.

⚠️ NO CREA SESSIÓ (decisió D5 de la diagnosi, OBERTA). Sense presa viva, el POST retorna
409 `sense_presa_oberta` i el GET ho diu amb `presa_oberta: false`: obrir una presa crea
sessió + peça + N línies, i fer-ho néixer d'una tecla en una cel·la seria el mateix error de
naturalesa que aquesta peça arregla. El gest explícit ja existeix i és el que obre «Mesurar
prenda».
"""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from fhort.models_app.models import Model
from fhort.pom.identitat import clau_mesura
from fhort.pom.plausibilitat import CODI_MESURA_FORA_RANG, mesura_fora_de_rang
from fhort.tasks.services_batec import SUP_PRESA, batec_de_request

from . import services
from .esdeveniments import linia_te_contingut
from .models import PieceFittingLine


def _cella(linia):
    """Una cel·la del payload. `real` és `None` quan NINGÚ no ha mesurat.

    🚨 AQUÍ VIU LA LLEI QUE EVITA QUE LA PANTALLA MENTEIXI: una `PieceFittingLine` neix amb
    `valor_real = valor_teoric` copiat de l'spec (`services.create_piece_fitting`). Servir
    `valor_real` a pèl faria que TOTES les cel·les de l'Escalat diguessin que la peça física
    s'ha mesurat i que coincideix exacte amb la teòrica — un full ple de preses que ningú no
    ha fet. `linia_te_contingut` és el predicat de la casa i es reusa, no es reescriu: el
    Repàs i la Comprovació ja el fan servir, i tres còpies serien tres veritats.
    (El seu bessó al front és `utils/taulaPresaPerTalla.liniaTeContingut`, E1/B2.)
    """
    te = linia_te_contingut(linia)
    real = float(linia.valor_real) if (te and linia.valor_real is not None) else None
    teoric = float(linia.valor_teoric) if linia.valor_teoric is not None else None
    return {
        'linia_id': linia.id,
        'teoric': teoric,
        'real': real,
        # La DESVIACIÓ la calcula el servidor perquè el vermell de R1 no depengui de com
        # arrodoneixi cada client. `None` quan no hi ha presa: no desviar-se i no haver-se
        # mesurat no són el mateix estat, i la pantalla els ha de poder pintar diferent.
        'desviacio': (round(real - teoric, 2)
                      if (real is not None and teoric is not None) else None),
        'estat': linia.decisio or '',
        'nota': linia.nota or '',
    }


class EscalatPresaView(APIView):
    permission_classes = [IsAuthenticated]

    # ── LECTURA ─────────────────────────────────────────────────────────────────────────
    def get(self, request, model_id):
        try:
            model = Model.objects.get(id=model_id)
        except Model.DoesNotExist:
            return Response({'error': 'Model no trobat'}, status=404)

        pf = services.peca_de_presa_del_model(model)
        base = (model.base_size_label or '').strip()
        if pf is None:
            # Estat BUIT però COMPLET: la pantalla ha de poder dir «no hi ha presa oberta» i
            # oferir el gest, no quedar-se sense saber què passa.
            return Response({'presa_oberta': False, 'piece_fitting_id': None, 'session': None,
                             'base_size': base, 'preses': {},
                             'resum': {'n_preses': 0, 'n_linies': 0, 'talles_amb_presa': [],
                                       'decidides_base': 0, 'pendents_base': 0}}, status=200)

        linies = list(PieceFittingLine.objects
                      .filter(piece_fitting=pf)
                      .order_by('pom_id', 'size_label'))
        preses, talles, n_preses = {}, [], 0
        decidides_base = pendents_base = 0
        for l in linies:
            clau = clau_mesura(l.pom_id, l.capa, l.instancia, l.garment)
            cel = _cella(l)
            preses[f'{clau}:{l.size_label}'] = cel
            if cel['real'] is not None:
                n_preses += 1
                if l.size_label not in talles:
                    talles.append(l.size_label)
            if base and l.size_label.strip() == base:
                if (l.decisio or '').strip():
                    decidides_base += 1
                else:
                    pendents_base += 1

        s = pf.session
        return Response({
            'presa_oberta': True,
            'piece_fitting_id': pf.id,
            # QUI, QUAN I EN QUIN ESTAT: el flux és pausable i asíncron entre el taller i el
            # despatx, i qui reprèn ha de saber de quina presa parla sense obrir cap altra
            # pantalla. `session.data` és el DIA de la presa, no el de l'última tecla.
            'session': {'id': s.id, 'data': s.data.isoformat() if s.data else None,
                        'fase': s.fase, 'estat': s.estat,
                        'responsable': (s.responsable.nom_complet if s.responsable_id else '')},
            'base_size': base,
            'preses': preses,
            'resum': {'n_preses': n_preses, 'n_linies': len(linies),
                      'talles_amb_presa': talles,
                      'decidides_base': decidides_base, 'pendents_base': pendents_base},
        }, status=200)

    # ── ESCRIPTURA ──────────────────────────────────────────────────────────────────────
    def post(self, request, model_id):
        """Body: `{pom_id, talla, valor, capa?, instancia?, garment?, nota?}`.

        `valor` buit treu la presa (la línia torna al seu teòric), mirall de l'ancoratge de
        `propagar`. Aquesta porta NO accepta `decisio`: decidir és el gest de la talla base i
        té la seva porta (`piece-fitting-lines/<id>/`), amb el guard partit d'E1/B1 al davant.
        """
        try:
            model = Model.objects.get(id=model_id)
        except Model.DoesNotExist:
            return Response({'error': 'Model no trobat'}, status=404)

        data = request.data or {}
        pom_id = data.get('pom_id')
        talla = (data.get('talla') or '').strip()
        if pom_id is None or not talla:
            return Response({'error': 'Calen pom_id i talla.'}, status=400)
        if 'decisio' in data:
            # Explícit i no silenciós: qui l'enviï ha de saber que aquesta porta no decideix,
            # en comptes de veure com el camp desapareix sense dir res.
            return Response({'error': "Aquesta porta anota preses, no decisions.",
                             'codi': 'presa_no_decideix'}, status=400)

        valor = data.get('valor')
        if valor in (None, ''):
            valor = None
        else:
            try:
                valor = round(float(valor), 2)
            except (TypeError, ValueError):
                return Response({'error': 'valor ha de ser numèric.'}, status=400)
            # LA MATEIXA GUARDA DE RANG FÍSIC que les altres portes de mesura (la que va
            # aturar el 22224,7 del POP). Una porta nova de mesura que no hi passés seria la
            # tercera lectura del mateix llindar.
            fora = mesura_fora_de_rang(valor)
            if fora:
                return Response({'error': fora, 'codi': CODI_MESURA_FORA_RANG}, status=422)

        # ELS TRES EIXOS PEL PUNT ÚNIC. `_identitat_de_mesura` és qui decideix què rep el
        # client que no els diu (l'exterior de la instància única de la mare) i té l'acta
        # escrita; resoldre'ls aquí amb un `or 'exterior'` propi seria una segona llei que el
        # dia que divergís faria escriure aquesta porta a una fila que ningú més busca.
        from fhort.models_app.views import _identitat_de_mesura
        capa, instancia, garment = _identitat_de_mesura(data)
        try:
            linia = services.desa_presa_escalat(
                model, pom_id=pom_id, capa=capa, instancia=instancia,
                garment=garment, talla=talla, valor=valor,
                nota=data.get('nota'))
        except services.PresaNoObertaError as e:
            return Response({'error': str(e), 'codi': 'sense_presa_oberta'},
                            status=status.HTTP_409_CONFLICT)
        except services.PresaSenseLiniaError as e:
            return Response({'error': str(e), 'codi': 'sense_linia'}, status=404)
        except ValueError as e:
            return Response({'error': str(e), 'codi': 'sessio_segellada'},
                            status=status.HTTP_409_CONFLICT)

        # F1.3 — anotar una presa és el batec més fi que hi ha: el tècnic hi és, mesurant.
        batec_de_request(request, model.id, SUP_PRESA)
        clau = clau_mesura(linia.pom_id, linia.capa, linia.instancia, linia.garment)
        return Response({'ok': True, 'id': f'{clau}:{linia.size_label}',
                         **_cella(linia)}, status=200)
