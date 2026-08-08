"""
fhort/models_app/vocabulari_views.py
LES ENUMERACIONS DE DOMINI, PUBLICADES: règims de graduació, fases i estats.

**PER QUÈ EXISTEIX.** Mateixa raó, i mateix patró, que `pom/identity_views.py` (el vocabulari de
capes i instàncies): les llistes estaven als `choices` dels models des de sempre i **cap endpoint
les publicava**, o sigui que el frontend se les havia d'escriure a mà. I havien derivat: la còpia
dels règims a `SizeMapSetup.jsx` en tenia QUATRE quan el model en declara CINC —hi faltava
`EXCEPTION`—, i una maqueta va arribar a dibuixar un `LINEAR+BREAK` que no existeix ni pot
existir (el break és una PROPIETAT de la regla, no un règim: v. `pom/grading_regime.py`).

La llei que això fa complir (Agus, 08/08): **cap enumeració de domini es declara al frontend**.
Una constant al client que dupliqui uns `choices` és una segona font de veritat que ningú
actualitza el dia que la primera canvia.

**PER QUÈ UN SOL ENDPOINT I NO QUATRE.** Són quatre llistes curtes i cap pantalla en fa servir
una de sola: la llista de models filtra per fase I per estat; la superfície de graduació
necessita els règims i el context del model. Quatre peticions per pintar una pantalla serien
quatre rellotges per a una sola pregunta.

**ELS CODIS NO ES TRADUEIXEN.** `LINEAR`, `FIXED`, `Pending`, `TOP` són DADA de domini, com un
codi de POM: viatgen crus i s'ensenyen crus. La mateixa llei que `MeasurementInstance` ja
aplica als noms d'instància (v. `utils/capaInstancia.js`). Per això aquí s'emet `codi` i
`etiqueta` —l'etiqueta que ve dels propis `choices`— i no cap `nom_ca`/`nom_es`: si algun dia
alguna d'aquestes llistes s'ha de traduir, la decisió serà d'Agus i el lloc serà una taula, no
aquest endpoint.

⚠️ **DUES «FASES» QUE NO SÓN LA MATEIXA COSA**, i per això tenen claus diferents i explícites:
`fases_model` és el cicle de vida del MODEL (`Model.FASE_CHOICES`: Pending…TOP) i `fases_tasca`
és la fase d'una TASCA del pla de treball (`tasks.TaskType.FASE_CHOICES`: Disseny…Producció). Són
vocabularis independents. `components/PhaseStepper.jsx` les barrejava —i hi afegia `'Nou'` i
`'Tancat'`, que són d'`ESTAT_CHOICES`, i un `'Tècnic'` que no existeix enlloc (la fase real és
`'Dev. tècnic'`)—; és codi mort i no el consumeix ningú, però el report ho deixa dit.

Lectura pura: cap escriptura, cap efecte, cap paràmetre.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from fhort.models_app.models import Model
from fhort.pom.models import GradingRule
from fhort.tasks.models import TaskType


def _llista(choices):
    """`[(codi, etiqueta), …]` → `[{codi, etiqueta}, …]`, en l'ordre en què el model els declara.

    L'ORDRE ÉS PART DE LA DADA: les fases d'un model van en seqüència (Pending → … → TOP) i
    reordenar-les alfabèticament al client trencaria qualsevol stepper que les pinti.
    """
    return [{'codi': c, 'etiqueta': str(e)} for c, e in choices]


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def vocabulari_domini_view(request):
    """
    GET /api/v1/vocabulari/

    → {regims_graduacio: [...], fases_model: [...], estats_model: [...], fases_tasca: [...]}

    Cada element: `{codi, etiqueta}`. El `codi` és el que es desa i el que viatja a l'API;
    l'`etiqueta` és la del `choices` i és per als ulls.
    """
    return Response({
        'regims_graduacio': _llista(GradingRule.LOGICA_CHOICES),
        'fases_model': _llista(Model.FASE_CHOICES),
        'estats_model': _llista(Model.ESTAT_CHOICES),
        'fases_tasca': _llista(TaskType.FASE_CHOICES),
    })
