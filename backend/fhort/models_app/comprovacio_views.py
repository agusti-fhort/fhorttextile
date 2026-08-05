"""models_app/comprovacio_views.py — LA COMPROVACIÓ D'UN MODEL (D-31.17), publicada.

Què falta i què s'ha de mirar ABANS que la fitxa surti cap al fabricant.

**CONSULTA PURA. Cap escriptura, cap efecte.** És la llei de la pantalla i també d'aquest
fitxer: comprovar i entrar són dos moments diferents, i barrejar-los és el que ha portat
problemes. Els «punts» que emet són enllaços cap a la fila de la taula, mai accions.

**PER QUÈ UN SOL ENDPOINT.** Les quatre seccions i les famílies es miren SEMPRE juntes —el
veredicte de dalt és la suma de totes— i partir-ho voldria dir cinc rellotges per a una sola
pregunta, amb el risc que el recompte del capçal no quadri amb el detall de sota.

**EL QUE AQUESTA VERSIÓ NO POT DIR, I NO S'INVENTA.** La maqueta té files de BUIT DECLARAT
(«la germana es va proposar i es va treure: el coll passa sota l'aixella esquerra») i el
domini encara no les té: no hi ha manera de declarar que una cara NO existeix i per què. Fins
que hi sigui, aquesta secció ensenya les cares que EXISTEIXEN i calla sobre les que no —que
és el contrari d'acusar-les de buides. Veure el report del tram.
"""
from datetime import timedelta

from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.models_app.models import (BaseMeasurement, MeasurementChangeLog, Model,
                                     ModelGradingRule, SizeCheckLine)

#: Contextos del log que són una PRESA de debò —algú ha mesurat una peça—, per oposició a
#: una escriptura d'autoria. Són els que fan que una base «quedi enrere» quan es mou després.
CONTEXTOS_DE_PRESA = ('fitting', 'checked')


def _nom(bm):
    """El nom que es llegeix a la pantalla: el bateig del model mana, el catàleg fa de fons."""
    pg = getattr(bm.pom, 'pom_global', None)
    return (bm.nom_canonic_model or getattr(pg, 'nom_en', '') or bm.pom.nom_client or '')


def _codi(bm):
    return bm.nom_fitxa or bm.pom.codi_client or getattr(getattr(bm.pom, 'pom_global', None), 'codi', '') or ''


def _fila(bm, **extra):
    return {'bm_id': bm.id, 'pom_id': bm.pom_id, 'codi': _codi(bm), 'nom': _nom(bm),
            'capa': bm.capa or 'exterior', 'instancia': bm.instancia or '', **extra}


def _seccio_bloquegen(model, mesures, poms_amb_regla):
    """BLOQUEGEN L'ENVIAMENT. Dos motius, i tots dos són certs amb el sistema d'avui.

    · Una fila que EXISTEIX i no té valor a la talla base: algú l'ha declarada i ningú l'ha
      mesurada. No és el mateix que «aquest POM no hi és», i per això bloqueja.
    · Una mesura sense regla de graduació: el motor no n'emetrà cap talla, i la fitxa sortiria
      amb una fila muda a totes les columnes menys la base.
    """
    punts = []
    for bm in mesures:
        if bm.base_value_cm is None:
            punts.append(_fila(bm, motiu='sense_valor'))
    for bm in mesures:
        if bm.pom_id not in poms_amb_regla:
            punts.append(_fila(bm, motiu='sense_regla'))
    return punts


def _seccio_enrere(model, mesures):
    """VAN QUEDAR ENRERE QUAN LA BASE ES VA MOURE.

    És el punt que la maqueta posa primer entre els «a revisar» i el que costa més de
    descobrir sol: un valor que falta el veus a la taula; una mesura que es va prendre i que
    després va quedar desalineada perquè la base es va moure, no.

    Es resol NOMÉS amb el log (append-only): l'última PRESA d'aquella mesura contra l'últim
    canvi de qualsevol mena. Si el canvi és posterior i el valor ja no és el que es va prendre,
    la presa ha quedat enrere. Els dies es diuen perquè «fa 9 dies» i «fa 3 hores» no volen dir
    el mateix a qui ha de decidir si cal tornar a mesurar.
    """
    punts = []
    logs = (MeasurementChangeLog.objects
            .filter(model=model)
            .order_by('base_measurement_id', '-created_at'))
    per_mesura = {}
    for l in logs:
        per_mesura.setdefault(l.base_measurement_id, []).append(l)
    for bm in mesures:
        historia = per_mesura.get(bm.id) or []
        if not historia:
            continue
        ultim = historia[0]
        presa = next((l for l in historia if l.context in CONTEXTOS_DE_PRESA), None)
        if presa is None or presa is ultim:
            continue
        if bm.base_value_cm is None or presa.valor_nou is None:
            continue
        if float(bm.base_value_cm) == float(presa.valor_nou):
            continue
        dies = (ultim.created_at - presa.created_at) / timedelta(days=1)
        punts.append(_fila(
            bm, mesurat=presa.valor_nou, base_ara=bm.base_value_cm,
            dies=round(dies, 1), presa_at=presa.created_at, mogut_at=ultim.created_at))
    return punts


def _seccio_descartades(model, mesures_per_clau):
    """PRESES DESCARTADES · PENDENTS DE RECLAMAR AL FABRICANT.

    Una presa que va arribar, es va mirar i es va DESCARTAR conscientment. No és un error del
    model: és una cosa que algú ha de dir al fabricant, i si no queda escrita enlloc es perd
    entre dues sessions.
    """
    punts = []
    linies = (SizeCheckLine.objects
              .filter(size_check__model=model, decisio='valor_descartat')
              .select_related('size_check', 'pom', 'pom__pom_global')
              .order_by('-size_check__id'))
    for l in linies:
        bm = mesures_per_clau.get((l.pom_id, l.capa or 'exterior', l.instancia or ''))
        base = {'pom_id': l.pom_id,
                'codi': (bm and _codi(bm)) or l.pom.codi_client or '',
                'nom': (bm and _nom(bm)) or getattr(getattr(l.pom, 'pom_global', None), 'nom_en', '') or '',
                'capa': l.capa or 'exterior', 'instancia': l.instancia or ''}
        punts.append({**base, 'bm_id': bm.id if bm else None,
                      'va_arribar': l.valor_real, 'vigent': l.valor_teoric,
                      'sessio': f'Size check {l.size_check_id}', 'nota': l.nota or ''})
    return punts


def _seccio_tolerancia(model, mesures):
    """FORA DE TOLERÀNCIA AL DARRER FITTING.

    La banda és la de la FILA (`tolerancia_minus/plus`), no la del catàleg: és la que algú ha
    afinat per a aquesta mesura d'aquest model. Sense banda declarada no s'acusa ningú —una
    tolerància que no existeix no es pot superar.
    """
    from fhort.fitting.models import PieceFittingLine
    punts = []
    per_bm = {bm.id: bm for bm in mesures}
    clau = {(bm.pom_id, bm.capa or 'exterior', bm.instancia or ''): bm for bm in mesures}
    linies = (PieceFittingLine.objects
              .filter(piece_fitting__model=model, valor_real__isnull=False)
              .select_related('piece_fitting', 'pom')
              .order_by('-piece_fitting__id'))
    vistes = set()
    for l in linies:
        bm = clau.get((l.pom_id, l.capa or 'exterior', ''))
        if bm is None or bm.id in vistes:
            continue
        if l.valor_teoric is None or bm.tolerancia_minus is None or bm.tolerancia_plus is None:
            continue
        desviacio = float(l.valor_real) - float(l.valor_teoric)
        if -float(bm.tolerancia_minus) <= desviacio <= float(bm.tolerancia_plus):
            continue
        vistes.add(bm.id)
        punts.append(_fila(bm, teoric=l.valor_teoric, real=l.valor_real,
                           desviacio=round(desviacio, 2),
                           tol_minus=float(bm.tolerancia_minus),
                           tol_plus=float(bm.tolerancia_plus),
                           talla=l.size_label))
    return punts


def _families(mesures):
    """LES FAMÍLIES DE MESURA: totes les cares d'un mateix POM, juntes.

    ⚠️ SENSE FILES DE BUIT DECLARAT. La maqueta en té —una cara que algú va decidir que NO
    existeix, amb el motiu escrit— i el domini encara no les pot desar. Aquí surten les cares
    que EXISTEIXEN; el que no hi és, no s'anomena. Inventar-hi un buit «no informat» diria que
    algú s'ha descuidat una mesura que potser la peça no té.
    """
    per_pom = {}
    for bm in mesures:
        per_pom.setdefault(bm.pom_id, []).append(bm)
    families = []
    for pom_id, files in per_pom.items():
        files = sorted(files, key=lambda b: ((b.capa or 'exterior') != 'exterior',
                                             b.capa or '', b.instancia or ''))
        cap = files[0]
        pg = getattr(cap.pom, 'pom_global', None)
        # LA FOLGANÇA és la resta entre l'exterior i el folre, i només es diu quan les dues
        # hi són amb valor: és una relació, no una propietat d'una fila sola.
        ext = next((b for b in files if (b.capa or 'exterior') == 'exterior'
                    and b.base_value_cm is not None), None)
        fol = next((b for b in files if (b.capa or '') == 'folre'
                    and b.base_value_cm is not None), None)
        folganca = (round(float(ext.base_value_cm) - float(fol.base_value_cm), 2)
                    if ext and fol else None)
        families.append({
            'pom_id': pom_id,
            'codi': _codi(cap),
            'nom': _nom(cap),
            'categoria': getattr(pg, 'categoria', '') or '',
            'folganca': folganca,
            'files': [{
                'bm_id': b.id,
                'capa': b.capa or 'exterior',
                'instancia': b.instancia or '',
                'valor': b.base_value_cm,
                'origen': b.origen,
            } for b in files],
        })
    families.sort(key=lambda f: f['codi'])
    return families


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def comprovacio_view(request, model_id):
    """
    GET /api/v1/models/<id>/comprovacio/

    → {veredicte: {...}, seccions: {...}, families: [...]}

    Lectura pura: cap escriptura, cap efecte.
    """
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return Response({'error': 'Model no trobat'}, status=404)

    mesures = list(BaseMeasurement.objects
                   .filter(model=model, is_active=True)
                   .select_related('pom', 'pom__pom_global')
                   .order_by('ordre', 'id'))
    per_clau = {(b.pom_id, b.capa or 'exterior', b.instancia or ''): b for b in mesures}

    # Un POM «té regla» si el MODEL n'hi ha materialitzada una de resident. La proposta del
    # catàleg no compta a posta: el 1302 va ensenyar què passa quan una proposta que ningú ha
    # adoptat es llegeix com a regla del model.
    poms_amb_regla = set(ModelGradingRule.objects
                         .filter(model=model)
                         .values_list('pom_id', flat=True))

    bloquegen = _seccio_bloquegen(model, mesures, poms_amb_regla)
    enrere = _seccio_enrere(model, mesures)
    descartades = _seccio_descartades(model, per_clau)
    tolerancia = _seccio_tolerancia(model, mesures)

    a_revisar = len(enrere) + len(descartades) + len(tolerancia)
    # CORRECTES = les mesures que no surten a cap punt. Es compta per FILA i no per POM: dues
    # germanes són dues mesures i una pot estar bé i l'altra no.
    tocades = {p['bm_id'] for p in bloquegen + enrere + tolerancia if p.get('bm_id')}
    tocades |= {p['bm_id'] for p in descartades if p.get('bm_id')}

    return Response({
        'veredicte': {
            'bloquegen': len(bloquegen),
            'a_revisar': a_revisar,
            'correctes': len([b for b in mesures if b.id not in tocades]),
        },
        'seccions': {
            'bloquegen': bloquegen,
            'enrere': enrere,
            'descartades': descartades,
            'tolerancia': tolerancia,
        },
        'families': _families(mesures),
        # El que aquesta versió NO pot dir, dit a la resposta i no només al report: el client
        # ha de poder explicar per què una secció no ensenya el que la maqueta promet.
        'limitacions': ['buit_declarat_amb_motiu'],
    })
