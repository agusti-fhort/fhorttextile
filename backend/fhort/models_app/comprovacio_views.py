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

#: LA FINESTRA D'UN DESAT. El log és append-only i una sola desada n'hi escriu N files: la
#: presa, i darrere seu les germanes que la regla bidireccional deriva. Al 1320 tot el desat
#: del fitting 152 cap en 81 mil·lisegons. Dues desades HUMANES separades per menys de dos
#: segons no existeixen; agrupar per aquesta finestra és el que permet distingir «la base es
#: va moure DESPRÉS» de «això ÉS el resultat de la presa» (v. `_events`).
FINESTRA_DESAT = timedelta(seconds=2)


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


def _events(logs):
    """Talla el log del model en ESDEVENIMENTS D'ESCRIPTURA: un desat = un event.

    `logs` ha d'arribar en ordre cronològic. Es talla per la `FINESTRA_DESAT`, no per fila:
    una fila del log no és un acte, és una CONSEQÜÈNCIA d'un acte, i la mateixa desada en
    genera tantes com mesures toca (la presa + les germanes derivades).
    """
    events = []
    for l in logs:
        if events and (l.created_at - events[-1]['fi']) <= FINESTRA_DESAT:
            events[-1]['fi'] = l.created_at
            events[-1]['files'].append(l)
        else:
            events.append({'fi': l.created_at, 'files': [l]})
    return events


def _seccio_enrere(model, mesures):
    """VAN QUEDAR ENRERE QUAN LA BASE ES VA MOURE.

    És el punt que la maqueta posa primer entre els «a revisar» i el que costa més de
    descobrir sol: un valor que falta el veus a la taula; una mesura que es va prendre i que
    després va quedar desalineada perquè la base es va moure, no.

    🚨 EL DEFECTE QUE AQUESTA VERSIÓ TANCA (Agus, 09/08, model 1320): la secció acusava YT de
    «van quedar enrere · mesurat 19 · base d'ara 13 · la base es va moure 0 DIES després de la
    darrera presa». Zero dies perquè no s'havia mogut després de res: dins del MATEIX desat del
    fitting 152, el tècnic va entrar YT=19 i tot seguit YB=25, i la regla bidireccional
    (YT = YB − 6) va reescriure YT a 13 vint-i-dos mil·lisegons més tard. La versió anterior
    llegia FILA A FILA —l'última fila `fitting` contra l'última fila de qualsevol mena— i una
    derivació de la pròpia presa li semblava un moviment posterior.

    LA REGLA, ara (decisió d'Agus, 10/08): **un canvi derivat dins de la mateixa desada no és
    una base que s'ha mogut: és el resultat de la presa.** Per tant
      · l'acte de comparació és l'EVENT, no la fila (`_events`);
      · el que es va prendre és el que l'event va deixar ESCRIT a la mesura —l'última paraula
        del desat, derivacions incloses—, no la xifra que la mà va teclejar pel camí;
      · només un event ESTRICTAMENT POSTERIOR pot deixar una presa enrere.
    Amb això, un punt d'aquesta secció ja no pot dir mai «fa 0 dies».

    Els dies es diuen perquè «fa 9 dies» i «fa 3 hores» no volen dir el mateix a qui ha de
    decidir si cal tornar a mesurar.
    """
    logs = (MeasurementChangeLog.objects
            .filter(model=model)
            .order_by('created_at', 'id'))
    # Per mesura, el rastre event a event: [(ordre_event, valor_final_a_l_event, es_presa, quan)].
    per_mesura = {}
    for i, ev in enumerate(_events(logs)):
        toc = {}
        for l in ev['files']:
            if l.valor_nou is None:
                continue
            t = toc.setdefault(l.base_measurement_id, {'valor': None, 'presa': False})
            t['valor'] = l.valor_nou          # l'ÚLTIMA paraula del desat sobre aquesta mesura
            t['presa'] = t['presa'] or l.context in CONTEXTOS_DE_PRESA
        for bm_id, t in toc.items():
            per_mesura.setdefault(bm_id, []).append((i, t['valor'], t['presa'], ev['fi']))

    punts = []
    for bm in mesures:
        historia = per_mesura.get(bm.id) or []
        presa = next((h for h in reversed(historia) if h[2]), None)
        if presa is None:
            continue
        posteriors = [h for h in historia if h[0] > presa[0]]
        if not posteriors:
            continue
        mesurat = presa[1]
        if bm.base_value_cm is None or mesurat is None:
            continue
        if float(bm.base_value_cm) == float(mesurat):
            continue
        ultim = posteriors[-1]
        dies = (ultim[3] - presa[3]) / timedelta(days=1)
        punts.append(_fila(
            bm, mesurat=mesurat, base_ara=bm.base_value_cm,
            dies=round(dies, 1), presa_at=presa[3], mogut_at=ultim[3]))
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
        bm = mesures_per_clau.get(
            (l.pom_id, l.capa or 'exterior', l.instancia or '', l.garment))
        base = {'pom_id': l.pom_id,
                'codi': (bm and _codi(bm)) or l.pom.codi_client or '',
                'nom': (bm and _nom(bm)) or getattr(getattr(l.pom, 'pom_global', None), 'nom_en', '') or '',
                'capa': l.capa or 'exterior', 'instancia': l.instancia or ''}
        punts.append({**base, 'bm_id': bm.id if bm else None,
                      'va_arribar': l.valor_real, 'vigent': l.valor_teoric,
                      'sessio': f'Size check {l.size_check_id}', 'nota': l.nota or ''})
    return punts


def _seccio_tolerancia(model, mesures, peca):
    """FORA DE TOLERÀNCIA AL DARRER FITTING.

    `peca` la resol la vista i s'hi passa: la secció i la capçalera que diu de quin fitting
    parla han de referir-se a LA MATEIXA, i resoldre-la dos cops és obrir la porta que un dia
    no ho siguin.

    La banda és la de la FILA (`tolerancia_minus/plus`), no la del catàleg: és la que algú ha
    afinat per a aquesta mesura d'aquest model. Sense banda declarada no s'acusa ningú —una
    tolerància que no existeix no es pot superar.

    🚨 TRES DEFECTES DE CONSULTA que feien que els números no lliguessin amb el model (Agus,
    09/08, model 1320 — «E2 teòric 29 / real 31 quan la base d'E2 és 31»):

    1. **CAP FILTRE DE TALLA.** La secció compara contra `BaseMeasurement`, que ÉS la talla
       base, però llegia les línies de totes les talles i es quedava amb la primera que
       Postgres tornés. El 29/31 d'E2 era la fila **XXS**; la fila S —la base— deia 31/33.
       Files diferents del mateix quadre acabaven citant talles diferents.
    2. **«EL DARRER FITTING» NO ERA EL DARRER.** Recorria TOTES les peces per id descendent i
       es quedava amb el primer encert de cada mesura: barrejava fittings i, a més, l'id de
       peça és l'ordre en què es van OBRIR les graelles, no el dia de la prova. Ara la peça la
       resol `fitting.esdeveniments`, que a més descarta les graelles obertes i no tocades.
    3. **L'EIX D'INSTÀNCIA, ESCRIT A MÀ A `''`.** `clau.get((pom, capa, ''))` no podia trobar
       cap germana: al 1320 això deixava CINC mesures fora de tota vigilància, entre elles
       J1·extended, que se n'anava 2 cm amb una banda de 0,60.

    EL TEÒRIC ÉS L'HISTÒRIC (decisió d'Agus, 10/08): «el valor de l'última data disponible,
    que és sobre el que es va mesurar». O sigui `PieceFittingLine.valor_teoric` d'aquella peça
    —el número que la modista tenia al davant—, i no la base d'ara ni l'spec d'ara. La secció
    explica un fet datat i no es desdiu quan després es propaga.
    """
    if peca is None:
        return []
    # La talla és LA BASE, perquè és contra la base que es compara. Una desviació d'una altra
    # talla no es pot mesurar amb la banda d'aquesta fila: parlen de peces diferents.
    talla = (model.base_size_label or '').strip()
    clau = {(bm.pom_id, bm.capa or 'exterior', bm.instancia or '', bm.garment): bm
            for bm in mesures}
    punts = []
    for l in (peca.linies
              .filter(size_label=talla, valor_real__isnull=False)
              .select_related('pom')):
        bm = clau.get((l.pom_id, l.capa or 'exterior', l.instancia or '', l.garment))
        if bm is None:
            continue
        if l.valor_teoric is None or bm.tolerancia_minus is None or bm.tolerancia_plus is None:
            continue
        desviacio = float(l.valor_real) - float(l.valor_teoric)
        if -float(bm.tolerancia_minus) <= desviacio <= float(bm.tolerancia_plus):
            continue
        punts.append(_fila(bm, teoric=l.valor_teoric, real=l.valor_real,
                           desviacio=round(desviacio, 2),
                           tol_minus=float(bm.tolerancia_minus),
                           tol_plus=float(bm.tolerancia_plus),
                           talla=l.size_label,
                           # El VEREDICTE de la cel·la viatja: una desviació que la modista ja
                           # ha ajustat i una que ningú no ha mirat no són el mateix punt.
                           veredicte=l.decisio or ''))
    return punts


def _darrer_fitting(peca):
    """La capçalera de la secció de tolerància: DE QUIN fitting parlen aquests números.

    Sense això la secció cita xifres sense dir de quin dia ni de quina talla són, i és
    exactament el que va fer que no «lliguessin» amb res del que es veu a la taula.
    """
    if peca is None:
        return None
    s = peca.session
    return {'session_id': peca.session_id, 'piece_fitting_id': peca.id,
            'data': s.data.isoformat() if s.data else None,
            'fase': s.fase, 'estat': s.estat}


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
    # SET-2/T6a — la PEÇA a la clau, i als tres mapes d'aquest fitxer alhora: tots tres
    # creuen una línia (de size check o de fitting) amb la seva mesura base, i amb la clau
    # curta la línia d'una prenda es jutjava contra la base i la tolerància de l'altra.
    per_clau = {(b.pom_id, b.capa or 'exterior', b.instancia or '', b.garment): b
                for b in mesures}

    # Un POM «té regla» si el MODEL n'hi ha materialitzada una de resident. La proposta del
    # catàleg no compta a posta: el 1302 va ensenyar què passa quan una proposta que ningú ha
    # adoptat es llegeix com a regla del model.
    poms_amb_regla = set(ModelGradingRule.objects
                         .filter(model=model)
                         .values_list('pom_id', flat=True))

    from fhort.fitting.esdeveniments import darrera_peca_amb_contingut

    # LA PEÇA DEL «DARRER FITTING», resolta UN COP: la secció de tolerància i la capçalera que
    # diu de quin fitting parla han de referir-se a la mateixa.
    peca = darrera_peca_amb_contingut(model.id)
    bloquegen = _seccio_bloquegen(model, mesures, poms_amb_regla)
    enrere = _seccio_enrere(model, mesures)
    descartades = _seccio_descartades(model, per_clau)
    tolerancia = _seccio_tolerancia(model, mesures, peca)

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
        # DE QUIN FITTING I DE QUINA TALLA parlen els números de la secció de tolerància. Anava
        # mut, i uns números sense procedència són el primer motiu perquè no «lliguin» amb res.
        'darrer_fitting': _darrer_fitting(peca),
        'talla_base': (model.base_size_label or '').strip() or None,
        'families': _families(mesures),
        # El que aquesta versió NO pot dir, dit a la resposta i no només al report: el client
        # ha de poder explicar per què una secció no ensenya el que la maqueta promet.
        'limitacions': ['buit_declarat_amb_motiu'],
    })
