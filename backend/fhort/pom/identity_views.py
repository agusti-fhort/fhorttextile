"""
fhort/pom/identity_views.py
EL VOCABULARI D'IDENTITAT D'UNA MESURA, publicat: capes i instàncies.

⚠️ NO confondre amb `dictionary_views.py`, que és el diccionari de NOMENCLATURA D'UN CLIENT
(els codis que Brownie fa servir als seus documents). Això d'aquí és el vocabulari CANÒNIC de
la casa amb què s'anomenen les cares d'una mesura: de quina matèria parla (capa, D-31.22) i
quina de les repeticions és (instància, D-31.26).

**PER QUÈ EXISTEIX.** Les dues taules estaven sembrades des de feia dies i **cap endpoint les
publicava**. El front se les havia d'escriure a mà (`utils/capaInstancia.js`), i com que allà
només hi van cabre les que algú va recordar, sis dels deu slugs d'instància es llegien crus
—`cf` sortia «Cf»— i el gest de crear una germana no podia oferir ni les vuit posicions ni la
proposta de codi.

**PER QUÈ UN SOL ENDPOINT I NO DOS.** Els dos eixos es miren SEMPRE junts: qualsevol pantalla
que ofereixi crear una germana necessita les capes I les instàncies a la mateixa obertura. Dues
peticions per pintar un diàleg serien dos rellotges per a una sola pregunta.

**EL SUFIX VIATJA, I LA REGLA DE COMPOSICIÓ TAMBÉ.** El client ha de poder PROPOSAR el codi de
la germana (`B` + `T` → `BT`) sense saber-se la regla: per això s'emet `sufix` per fila i, a
`regles`, com es componen —concatenació directa, sense separador, i la capa no toca mai el codi
(D-31.26)—. Que la regla sigui DADA i no codi repetit al front és el que evita que el dia que
canviï hi hagi dues respostes.

Lectura pura: cap escriptura, cap efecte.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.pom.models import MeasurementInstance, MeasurementLayer


def _fila(r):
    """Fila comuna dels dos vocabularis. ELS TRES NOMS VIATGEN SENCERS.

    No es tria l'idioma aquí: qui el sap és el navegador (llei D2 — la BD desa el slug i el
    literal és de qui llegeix). Enviar-ne un de sol obligaria a refer la petició en canviar
    d'idioma, i parlem de setze files en total.
    """
    return {
        'slug': r.slug,
        'nom_en': r.nom_en,
        'nom_ca': r.nom_ca,
        'nom_es': r.nom_es,
        'is_system': r.is_system,
        'pendent_revisio': r.pendent_revisio,
        'display_order': r.display_order,
    }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def measurement_identity_vocabulary_view(request):
    """
    GET /api/v1/mesures/diccionari/

    → {capes: [...], eixos: [...], instancies: {POSICIO: [...], ESTAT: [...]}, regles: {...}}

    Les instàncies van AGRUPADES PER EIX i no en una llista de deu: són ortogonals (una germana
    pot ser `left` i `relaxed` alhora) i barrejar-les faria que el diàleg de crear germana
    oferís deu opcions on n'hi ha vuit d'una mena i dues d'una altra.

    **ELS EIXOS VIATGEN AMB NOM I EN ORDRE** (D-31.18). La taula de mesures pinta un GRUP DE
    COLUMNES per eix, i les opcions de cada grup són les files de l'eix: si el nom de la columna
    se l'escrivís el front, hi hauria dos llocs que saben quins eixos existeixen i el dia que
    n'aparegui un tercer la columna nova sortiria sense capçalera. L'ordre de la llista és el de
    presentació —és el mateix que decideix quin eix es gira en partir un POM—, i per això s'emet
    com a LLISTA i no com les claus d'un diccionari, que no en tenen cap.
    """
    capes = [_fila(c) for c in MeasurementLayer.objects.all().order_by('display_order', 'slug')]

    # ⚠️ L'ORDRE DE LES CLAUS D'AQUEST DICCIONARI JA NO DECIDEIX RES, i abans sí. `order_by('eix')`
    # és ALFABÈTIC (`'ESTAT' < 'POSICIO'`) i el front en prenia l'ordre de composició del slug
    # (`pesCanonic` amb `Object.keys`), o sigui que la clau única de cinc taules depenia de com
    # es diguessin dos eixos. Des de la llei del 26/08 l'ordre canònic el diu `subeixos` (les
    # FAMÍLIES, en l'ordre declarat a `MeasurementInstance.FAMILIES`) i res més.
    #
    # Es reordena igualment per `EIX_CHOICES` —l'ordre DECLARAT— i no per l'alfabet: un
    # diccionari amb un ordre accidental és una mina esperant el proper lector que se'l cregui.
    _ordre_eix = {clau: i for i, (clau, _) in enumerate(MeasurementInstance.EIX_CHOICES)}
    instancies = {}
    for r in sorted(MeasurementInstance.objects.all(),
                    key=lambda x: (_ordre_eix.get(x.eix, 99), x.display_order, x.slug)):
        # El SUFIX només té sentit a l'eix POSICIÓ (els estats no componen codi, D-31.26); s'emet
        # a totes les files igualment perquè el client no hagi de saber en quin eix el pot trobar.
        # `subeix` — EL SEGON NIVELL DE LA POSICIÓ (22-23/08). `''` a tot el que no en té: una
        # posició sense sub-eix segueix sent excloent amb tota la resta del seu eix. El client
        # ha de poder dir QUINS xips es desmarquen entre ells sense saber-se cap slug: per això
        # viatja com a dada de la fila i no com una llista escrita al front.
        instancies.setdefault(r.eix, []).append({
            **_fila(r), 'eix': r.eix, 'sufix': r.sufix,
            'subeix': MeasurementInstance.subeix_de(r.slug),
        })

    # Només els eixos que TENEN files: un eix declarat i buit seria una columna sense cap opció.
    eixos = [
        {'clau': clau, **MeasurementInstance.EIX_NOMS.get(clau, {'nom_en': clau, 'nom_ca': clau, 'nom_es': clau})}
        for clau, _ in MeasurementInstance.EIX_CHOICES
        if instancies.get(clau)
    ]

    return Response({
        'capes': capes,
        'eixos': eixos,
        # LES FAMÍLIES, EN ORDRE CANÒNIC DE COMPOSICIÓ (llei d'Agus, 26/08):
        #     peça → banda → verticalitat → costura → línia → estat
        # `back`+`left` compon `back-left` i proposa `BL`, mai `LB`. Va com a LLISTA perquè
        # **l'ordre ÉS la dada**, i les claus d'un objecte no en tenen — que és exactament el
        # forat que això tanca: el front prenia l'ordre de les claus de `instancies` i aquelles
        # sortien alfabètiques. La clau es diu `subeixos` i no `families` perquè el nom és el
        # contracte publicat i renombrar-lo és un tram propi.
        # No porta noms: cap superfície n'ensenya el rètol; el dia que en calgui, s'hi afegeixen.
        'subeixos': [clau for clau, _ in MeasurementInstance.SUBEIXOS],
        'instancies': instancies,
        'regles': {
            # Com es compon el codi PROPOSAT d'una germana (D-31.26, estil Brownie natiu).
            'sufix_separador': '',
            'sufix_ordre': 'base+sufix',
            # La CAPA no entra mai al codi: diu de quina matèria és, no quina cara.
            'capa_al_codi': False,
            # Slug compost quan es creuen els dos eixos: `left` + `relaxed` → `left-relaxed`.
            'instancia_separador': '-',
            # La instància ÚNICA no és cap fila d'aquesta taula: és la cadena buida.
            'instancia_unica': MeasurementInstance.SLUG_UNICA,
            # La proposta no és l'obligació: qui exigeix el nom és la invariant de BD
            # `models_app_basemeasurement_instancia_exigeix_nom`.
            'instancia_exigeix_nom': True,
            'capa_defecte': MeasurementLayer.SLUG_DEFECTE,
        },
    })
