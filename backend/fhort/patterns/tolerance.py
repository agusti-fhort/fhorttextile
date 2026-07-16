"""Graduació del veredicte d'una costura o pinça — PRESENTACIÓ, no motor.

El motor (`engine/sew.py`) diu la XIFRA: quants mil·límetres de desajust hi ha, i prou. Aquí
aquella xifra es tradueix a un SEMÀFOR —verd/groc/vermell— que diu una cosa més tova: si el
desajust és plausiblement acceptable o no. **Tolerància ≠ error:** un groc no és una costura
trencada, és una que val la pena mirar; el vermell tampoc no bloqueja res —el patronista mana—,
només diu que allò no s'hauria d'ignorar sense pensar-hi.

Els LLINDARS són criteri d'OFICI, no llei de física. Són **afinables** i la Montse els ha de
validar; per això viuen AQUÍ, documentats i en un sol lloc, i no repartits pel codi ni cablejats
a la UI. Cada mena de relació té la seva exigència: una pinça demana més precisió que una costura
de muntatge, perquè un costat de pinça desigual es nota en tancar-la.

Es diuen en MIL·LÍMETRES perquè és com es parla al taller; el motor treballa en centímetres, i la
conversió es fa aquí, un sol cop.

Aquest mòdul NO toca el motor: `sew.py` continua dient «casa/no casa» i la xifra exacta. El grau
és una lectura de sobre, i és també el que es CONGELA quan un tècnic accepta un desajust
(`SewToleranceAcceptance`): acceptar ha de poder desar QUÈ es va considerar acceptable, i el
llindar aplicat és part d'aquell judici.
"""

GRAU_OK = 'ok'       # verd — plausiblement acceptable
GRAU_WARN = 'warn'   # groc — val la pena mirar-ho
GRAU_ERR = 'err'     # vermell — desajust que no s'hauria d'ignorar sense pensar-hi
GRAU_NA = 'na'       # sense gradient (frunzit: el desajust és intencional)

#: Verd fins a `verd_mm` (inclòs); groc entre `verd_mm` i `groc_mm` (inclòs); vermell per sobre.
#: Criteri d'ofici — afinable, a validar per la Montse.
BANDES = {
    # Costura de muntatge genèrica: la més tolerant. També és la banda de FALLBACK (v. avall).
    'muntatge': {'verd_mm': 3.0, 'groc_mm': 6.0},
    # Casat: dues vores que han de fer el MATEIX; més exigent que un muntatge qualsevol.
    'casat':    {'verd_mm': 2.0, 'groc_mm': 4.0},
    # Pinça: els dos costats s'han de poder cosir l'un contra l'altre; la més exigent.
    'pinca':    {'verd_mm': 1.5, 'groc_mm': 3.0},
    # 'frunzit' NO hi és a posta: el diferencial és una instrucció de muntatge, no un error
    # a graduar. Es queda amb la lectura binària del motor (casa el diferencial declarat o no).
}


def mena_de_tolerancia(tipus: str) -> str:
    """La mena de relació → la banda que se li aplica.

    `frunzit` es marca com a tal (sense gradient). Un tipus desconegut cau a `muntatge`, la
    banda MÉS tolerant: val més graduar de menys que inventar-se una exigència que ningú no ha
    validat. Quan el domini afegeixi un tipus nou de costura, aquí és on li dona la seva banda.
    """
    if tipus == 'frunzit':
        return 'frunzit'
    if tipus in BANDES:
        return tipus
    return 'muntatge'


def graduar(tipus: str, desviament_cm: float) -> dict:
    """El semàfor d'un desajust, amb la banda aplicada (sempre, encara que sigui verd).

    Torna la banda que s'ha mirat fins i tot quan el grau és verd, perquè acceptar una costura
    ha de poder desar el llindar contra el qual es va jutjar: sense el llindar, un desajust
    acceptat no es pot tornar a llegir («era acceptable segons què?»).
    """
    mena = mena_de_tolerancia(tipus)
    if mena == 'frunzit':
        return {'grau': GRAU_NA, 'mena': 'frunzit', 'verd_mm': None, 'groc_mm': None}

    banda = BANDES[mena]
    mm = abs(desviament_cm) * 10.0
    if mm <= banda['verd_mm']:
        grau = GRAU_OK
    elif mm <= banda['groc_mm']:
        grau = GRAU_WARN
    else:
        grau = GRAU_ERR
    return {
        'grau': grau, 'mena': mena,
        'verd_mm': banda['verd_mm'], 'groc_mm': banda['groc_mm'],
    }
