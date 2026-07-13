"""Qui es cus amb qui: la PROPOSTA.

**Proposar, mai escriure.** Aquest mòdul no crea cap costura: llegeix la geometria i diu
quines parelles de trams *semblen* una costura, amb quina confiança i —això és el que el fa
útil— **per què**. Qui decideix és el patronista, amb un clic. La llei és la mateixa que
governa la lectura del `.ftt` i la segmentació gir→gir: el CAD (i ara el motor) fa hipòtesis;
les afirmacions les fa una persona.

Per això cada proposta viatja amb el DESGLÒS dels senyals que l'han produïda. Una xifra de
confiança sola («87%») no es pot discutir; «els dos trams fan 25,3 i 25,2 cm, tots dos van de
piquet a piquet, i són el davant i l'esquena» sí. El patronista ha de poder dir «aquest no» i
saber què ha vist la màquina per equivocar-se.

─────────────────────────────────────────────────────────────────────────────
El que el material real ens ha ensenyat (mesurat sobre el TATE, no suposat)
─────────────────────────────────────────────────────────────────────────────

1. **Cada piquet surt DUES vegades al fitxer**: una còpia sobre la línia de tall i una altra
   sobre la de cosit, separades pel marge de costura (7,5 mm al TATE). Són el MATEIX piquet.
   Projectats sobre la vora base, els dos donen pràcticament la mateixa `t` (0,1882 i 0,1884),
   i per això la deduplicació es fa **per posició sobre la vora**, no per coordenades: dues
   marques a 7,5 mm l'una de l'altra en línia recta són el mateix punt de la costura.

2. **Els piquets seuen sobre punts de GIR.** Cap piquet del TATE cau al mig d'un tram: tots
   coincideixen amb una cantonada, perquè el CAD hi posa un gir. Conseqüència directa: el
   senyal dels piquets **no** pot mirar només l'interior del tram (hi hauria zero piquets
   sempre) — ha de mirar el tram amb els EXTREMS INCLOSOS. Un tram que va de piquet a piquet
   és una unitat de costura declarada pel CAD, i que dos trams ho siguin tots dos, amb el
   mateix nombre de marques als mateixos llocs, és el senyal fort.

3. **Un tram no és mai una vora sencera.** La sisa del cos i la copa de la màniga arriben
   subdividides pels mateixos piquets a banda i banda: entre dos piquets homòlegs, la copa fa
   una mica més que la sisa, i aquesta mica **és l'embut**. Per això el frunzit es pot inferir
   tram a tram i no cal endevinar-lo mirant la vora sencera.

─────────────────────────────────────────────────────────────────────────────
Els tres senyals, i per què pesen el que pesen
─────────────────────────────────────────────────────────────────────────────

· **PIQUETS** (pes dominant, 0,50). El piquet és l'única marca que el patronista posa
  EXPRESSAMENT perquè dues vores es trobin: no és una casualitat geomètrica, és una
  instrucció. Dos trams amb el mateix nombre de piquets a les mateixes posicions relatives
  són, gairebé sempre, la mateixa costura vista des dels dos costats. Es prova en els DOS
  sentits (les dues vores es cusen encarades, i el que en una va del 0 a l'1 en l'altra sol
  anar de l'1 al 0): si casen invertides, casen igual.
  Un nombre DIFERENT de piquets és evidència EN CONTRA, no absència d'evidència.

· **LONGITUD** (0,35). Igual dins tolerància → casat. Excés sistemàtic d'un costat dins d'un
  rang raonable → frunzit, i el diferencial és la xifra llegida, no una invenció.
  **L'ordre importa**: primer la tolerància ABSOLUTA, després el percentatge. Un excés de
  2 mm sobre un tram de 10 cm és un 2% —i no és cap frunzit, és la precisió del CAD—; dir-ne
  frunzit ensenyaria la cosidora a no fer cas dels diferencials, que és el pitjor que li pot
  passar a un.

· **NOMS** (0,15, i MAI suficient sol). Que una peça es digui FRONT i l'altra BACK fa
  plausible una costura; no la demostra. Per això el nom no proposa res per si mateix
  (v. `_te_evidencia_geometrica`): sense un senyal de geometria al davant, el nom calla.
  El nom SÍ que pot desproposar: dues peces de la mateixa família i la mateixa capa
  (dues mànigues, dos colls) no es cusen l'una contra l'altra —són la mateixa peça
  duplicada, o el parell simètric—, i això és evidència en contra prou forta per tombar una
  coincidència de longitud perfecta. Sense aquesta regla, un fitxer de niada amb la màniga
  repetida proposaria «màniga ⛓ màniga» amb tota la confiança del món.

─────────────────────────────────────────────────────────────────────────────
Restricció global: cap tram a dues costures
─────────────────────────────────────────────────────────────────────────────
Les propostes no s'emeten d'una en una: es reparteixen. Un tram que ja s'ha adjudicat a una
costura no es pot oferir a una altra —seria cosir la mateixa tela dues vegades, que és
exactament el que `sew.validar_cobertura` denuncia—, i el repartiment es resol per confiança
descendent: la parella més ben fonamentada s'endú els seus trams, i les que en depenien
cauen. És una assignació voraç, no òptima, i ho és a posta: el criteri ha de ser explicable
en una frase («la millor primera»), perquè el patronista l'ha de poder predir.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot

MM_PER_CM = 10.0

#: Pesos dels tres senyals. Sumen 1.0 quan tots tres van a favor.
PES_PIQUETS = 0.50
PES_LONGITUD = 0.35
PES_NOMS = 0.15

#: Per sota d'això no es proposa res. No és un llindar de veritat, és un llindar de SOROLL:
#: una proposta que ningú confirmarà mai fa més mal que bé, perquè ensenya a ignorar la llista.
#:
#: **Calibrat sobre el TATE i l'AMELIA, no triat a ull.** Una parella de geometria perfecta però
#: de noms incompatibles (el coll amb la màniga: passa, i amb longituds clavades) suma
#: 0,35 + 0,33 − 0,30 = 0,38. El llindar va JUST per sobre perquè aquestes cauguin i les bones no:
#: la lateral del TATE fa 0,74 i la més fluixa de les certes, 0,50. Baixar-lo a 0,30 tornava a
#: obrir la porta a «coll ⛓ màniga» i a «coll ⛓ entretela del coll», que és exactament el soroll
#: que fa que ningú es miri la llista.
LLINDAR_PROPOSTA = 0.40

#: Trams més curts que això no entren de candidats. Una vora real en té un reguitzell d'1–2 cm
#: (cantonades, arrodoniments), i aparellar-los per longitud és tirar els daus: n'hi ha desenes
#: que fan el mateix. Els descartats es DIUEN (`Descartats.curts`), mai s'amaguen.
LLARG_MIN_CM = 3.0

#: Igual de llargs = casat. És més ampla que la tolerància de VALIDACIÓ (`sew.TOLERANCIA_CM`,
#: 1 mm) i ha de ser-ho: aquí es decideix si val la pena ENSENYAR una parella, allà si la
#: costura CASA. Una proposta que es queda a 2 mm mereix sortir a la llista —amb el seu
#: veredicte dient, sense maquillar, que li faltaran 2 mm.
TOL_CASAT_CM = 0.3

#: Frunzit: l'excés d'un costat, en tant per u de la seva longitud. Per sota del mínim és
#: precisió de CAD; per sobre del màxim ja no és un frunzit, és que la parella no ho és.
FRUNZIT_MIN_REL = 0.02
FRUNZIT_MAX_REL = 0.15

#: Dos piquets casen si les seves posicions RELATIVES dins del tram no es diferencien més
#: d'això (5% del tram: sobre un tram de 25 cm, 1,2 cm).
TOL_PIQUET_S = 0.05

#: Un piquet «és» d'aquest tram si la seva projecció cau dins del rang, amb aquest gruix als
#: extrems. Els piquets seuen sobre els girs que delimiten els trams: sense marge, el mateix
#: piquet quedaria dins o fora segons l'error de coma flotant de la quinzena xifra.
EPS_EXTREM_S = 0.02

#: Distància màxima (mm) entre un piquet i la vora base perquè se'l consideri d'aquesta vora.
#: Al TATE, cada piquet hi és dos cops: a 0 mm (el de la línia base) i a 7,5 mm (el bessó de
#: l'altra línia, el marge de costura). Els dos s'accepten i després es dedupliquen: el que
#: interessa no és sobre quina línia el va dibuixar el CAD, sinó A QUINA ALÇADA de la costura
#: cau. Un marge de 20 mm cobreix els marges de costura de la indústria sense empassar-se
#: marques internes (butxaques, plecs), que viuen molt més endins.
DIST_MAX_PIQUET_MM = 20.0

#: Dos piquets projectats a menys d'això (mm d'arc) són el MATEIX piquet vist dues vegades.
#: Al TATE, les dues còpies d'un piquet disten 0–5 mm d'arc un cop projectades, i dos piquets
#: DIFERENTS mai no baixen de 16 mm. El llindar viu al mig, amb marge per als dos costats.
DIST_DEDUP_PIQUET_MM = 8.0


# ─────────────────────────────────────────────────────────────────────────────
# Vocabulari de peça — el senyal feble, i l'únic que sap dir que no
# ─────────────────────────────────────────────────────────────────────────────

#: Família de la peça: quin tros de la peça de roba és. Les claus són els lexemes que apareixen
#: als noms de bloc dels CAD reals (anglès de la indústria, i el català/castellà que els
#: patronistes de casa fan servir). Un nom pot dur-ne més d'una (TATE_FRONT_YOKE és FRONT i
#: YOKE alhora), i això és informació, no ambigüitat.
FAMILIES: dict[str, tuple[str, ...]] = {
    'FRONT': ('FRONT', 'DAVANT', 'DAVANTER', 'DELANTERO'),
    'BACK': ('BACK', 'ESQUENA', 'DARRERE', 'ESPALDA', 'TRASERO'),
    'SLEEVE': ('SLEEVE', 'MANIGA', 'MANGA'),
    'YOKE': ('YOKE', 'CANESU', 'CANESU'),
    'COLLAR': ('COLLAR', 'NECK', 'BAND', 'COLL', 'CUELLO'),
    'CUFF': ('CUFF', 'PUNY', 'PUNO'),
    'POCKET': ('POCKET', 'BUTXACA', 'BOLSILLO'),
    'WAISTBAND': ('WAISTBAND', 'CINTURA', 'PRETINA'),
}

#: Capa de la peça: de què serveix aquest tros de tela. Una vista (FACING) es cus a la seva
#: peça; un folre (LINING) es cus amb els altres folres; una entretela (INTERLINING) no es cus
#: contra ningú —es termofixa— i per això no proposa mai res.
CAPA_SHELL = 'shell'
CAPA_LINING = 'lining'
CAPA_FACING = 'facing'
CAPA_INTERLINING = 'interlining'

CAPES: dict[str, tuple[str, ...]] = {
    # L'ordre de comprovació mana: INTERLINING abans que LINING, perquè 'INTERLINING' conté
    # 'LINI' i, mirat a l'inrevés, una entretela passaria per folre.
    CAPA_INTERLINING: ('INTERLINING', 'ENTRETELA', 'INTERFACING'),
    CAPA_FACING: ('FACING', 'VISTA'),
    CAPA_LINING: ('LINI', 'LINING', 'FORRO', 'FORRE'),
}

#: Quines famílies es cusen amb quines. És una relació simètrica i deliberadament CURTA: només
#: hi ha el que un patronista signaria sense pensar-s'hi. El que hi falta no es proposa pel nom
#: —es proposa per la geometria, si la geometria ho diu— i això és exactament el que volem.
VEINES: frozenset[frozenset[str]] = frozenset({
    frozenset({'FRONT', 'BACK'}),        # els costats, i les espatlles
    frozenset({'SLEEVE', 'FRONT'}),      # la sisa
    frozenset({'SLEEVE', 'BACK'}),
    frozenset({'YOKE', 'BACK'}),         # el canesú
    frozenset({'YOKE', 'FRONT'}),
    frozenset({'COLLAR', 'FRONT'}),      # l'escot
    frozenset({'COLLAR', 'BACK'}),
    frozenset({'COLLAR', 'YOKE'}),
    frozenset({'CUFF', 'SLEEVE'}),
    frozenset({'WAISTBAND', 'FRONT'}),
    frozenset({'WAISTBAND', 'BACK'}),
})


def _lexemes(nom: str) -> list[str]:
    """El nom de bloc, trossejat en paraules comparables. `TATE_FRONT_YOKE` → [TATE, FRONT, YOKE]."""
    net = ''.join(c if c.isalnum() else ' ' for c in (nom or '').upper())
    return [w for w in net.split() if w]


def families(nom: str) -> frozenset[str]:
    """Quins trossos de peça de roba anomena aquest nom de bloc."""
    paraules = _lexemes(nom)
    trobades = {
        fam for fam, claus in FAMILIES.items()
        if any(any(clau in p for p in paraules) for clau in claus)
    }
    return frozenset(trobades)


def capa(nom: str) -> str:
    """Shell, folre, vista o entretela. El que no es declara és shell."""
    paraules = _lexemes(nom)
    for nom_capa, claus in CAPES.items():
        if any(any(clau in p for p in paraules) for clau in claus):
            return nom_capa
    return CAPA_SHELL


# ─────────────────────────────────────────────────────────────────────────────
# Geometria d'entrada — el que el matcher necessita saber d'un tram
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Candidat:
    """Un tram que es podria cosir: la seva geometria, i els piquets que hi cauen.

    `piquets` són posicions RELATIVES dins del tram (0 = l'inici, 1 = el final), no `t` de la
    vora: dos trams de vores i peces diferents s'han de poder comparar, i el que es compara és
    on cau la marca DINS DEL TRAM, no on cau dins de la peça.
    """
    segment_id: int
    piece_id: int
    piece_nom: str
    vora: int
    t_inici: float
    t_fi: float
    longitud_mm: float
    piquets: tuple[float, ...] = ()
    nom: str = ''

    @property
    def longitud_cm(self) -> float:
        return self.longitud_mm / MM_PER_CM


@dataclass(frozen=True)
class Senyal:
    """Un motiu, amb el seu pes i les seves xifres.

    `dades` porta els números CRUS i `detall` la frase en català. La UI construeix el seu text
    de les dades (i18n-gate: ca/en/es); la frase del servidor es guarda per al `title`, que és
    on hi ha el matís que no cap a la fila.
    """
    mena: str            # 'piquets' | 'longitud' | 'noms'
    punts: float         # la seva contribució a la confiança (pot ser NEGATIVA)
    detall: str
    dades: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Proposta:
    """Una parella que sembla una costura, amb tot el que cal per discutir-la."""
    a: Candidat
    b: Candidat
    tipus: str                     # 'casat' | 'frunzit'
    diferencial_cm: float
    confianca: float
    #: Els piquets casen amb els trams ENCARATS (l'inici d'un contra el final de l'altre).
    #: És el cas normal —dues vores es cusen mirant-se—, i cal dir-ho perquè és el que decideix
    #: en quin sentit s'han de fer coincidir les marques a la màquina.
    invertit: bool
    senyals: tuple[Senyal, ...]


@dataclass(frozen=True)
class Descartats:
    """Què NO ha entrat, i per què. Un matcher que amaga el que ha tirat és un matcher que
    menteix sobre la seva cobertura: si al patronista li falta una costura, ha de poder saber si
    és que el motor no l'ha vista o és que ni tan sols l'ha mirada."""
    curts: int = 0                 # trams per sota de LLARG_MIN_CM
    ja_cosits: int = 0             # trams que una costura declarada ja reclama
    sota_llindar: int = 0          # parelles mirades que no arriben a LLINDAR_PROPOSTA
    en_conflicte: int = 0          # parelles bones que han perdut el tram contra una de millor
    rebutjades: int = 0            # parelles que una persona ja ha dit que no


# ─────────────────────────────────────────────────────────────────────────────
# Piquets sobre una vora
# ─────────────────────────────────────────────────────────────────────────────

def projectar(punts, closed: bool, x: float, y: float) -> tuple[float, float]:
    """El punt de la polilínia més proper a (x, y): a quina distància, i a quina `t`.

    Un piquet no pertany a cap vora (no té `boundary_index`): és una marca damunt del dibuix. El
    que el lliga a una costura és ON CAU sobre la vora, i això és una projecció —la mateixa que
    fa el patronista quan transporta la marca del tall a la línia de cosit.
    """
    pts = list(punts)
    if len(pts) < 2:
        return (float('inf'), 0.0)
    if closed:
        pts = pts + [pts[0]]

    total = sum(hypot(pts[i + 1].x - pts[i].x, pts[i + 1].y - pts[i].y) for i in range(len(pts) - 1))
    if total <= 0:
        return (float('inf'), 0.0)

    millor_d, millor_t, acumulat = float('inf'), 0.0, 0.0
    for i in range(len(pts) - 1):
        ax, ay = pts[i].x, pts[i].y
        dx, dy = pts[i + 1].x - ax, pts[i + 1].y - ay
        llarg = hypot(dx, dy)
        l2 = dx * dx + dy * dy
        # u = on cau la projecció DINS d'aquest tros, retallada al tros: fora d'ell, el punt més
        # proper és un dels dos extrems, i no el peu de la perpendicular (que cauria en un tros
        # que no existeix).
        u = 0.0 if l2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / l2))
        d = hypot(x - (ax + u * dx), y - (ay + u * dy))
        if d < millor_d:
            millor_d, millor_t = d, (acumulat + u * llarg) / total
        acumulat += llarg
    return (millor_d, millor_t)


def piquets_de_la_vora(punts, closed: bool, notches, longitud_mm: float) -> tuple[float, ...]:
    """Els piquets d'una peça, situats sobre la seva vora base i DEDUPLICATS.

    Cada piquet arriba dues vegades del CAD (la còpia del tall i la del cosit, separades pel
    marge de costura). Les dues projecten a la mateixa `t`, i comptar-les dues vegades duplicaria
    el nombre de marques —que és precisament el número que el senyal fort compara.
    """
    if longitud_mm <= 0:
        return ()

    tolerancia_t = DIST_DEDUP_PIQUET_MM / longitud_mm
    trobats: list[float] = []
    for n in notches:
        dist, t = projectar(punts, closed, n.x, n.y)
        if dist > DIST_MAX_PIQUET_MM:
            # Massa endins: no és una marca de vora, és una marca interna (una butxaca, un plec).
            continue
        if any(_dist_circular(t, altre) <= tolerancia_t for altre in trobats):
            continue
        trobats.append(t)
    return tuple(sorted(trobats))


def _dist_circular(a: float, b: float) -> float:
    """Distància entre dues `t` d'una vora TANCADA: 0.99 i 0.01 disten 0.02, no 0.98."""
    d = abs(a - b) % 1.0
    return min(d, 1.0 - d)


def piquets_del_tram(
    piquets_vora: tuple[float, ...], t_inici: float, t_fi: float,
) -> tuple[float, ...]:
    """Els piquets que cauen sobre un tram, en posició RELATIVA (0–1), extrems inclosos.

    **Extrems inclosos, i no és un detall**: al material real TOTS els piquets seuen sobre punts
    de gir, i els girs són justament el que talla els trams. Mirant només l'interior, cap tram
    no tindria mai cap piquet i el senyal fort no existiria.

    Un tram amb `t_fi` < `t_inici` passa per l'origen de la vora (la mateixa convenció que
    `engine.segments.fraccio_tram`): la volta es dona amb aritmètica modular, no amb un `if`.
    """
    fraccio = (t_fi - t_inici) % 1.0
    if fraccio <= 0:
        return ()

    dins: list[float] = []
    for t in piquets_vora:
        s = ((t - t_inici) % 1.0) / fraccio
        # El piquet d'un extrem cau a s≈0 o s≈1; el marge els admet tots dos sense admetre els
        # dels trams veïns (que cauen molt més enllà d'1 o molt més ençà de 0).
        if -EPS_EXTREM_S <= s <= 1.0 + EPS_EXTREM_S:
            dins.append(min(1.0, max(0.0, s)))
        else:
            # La volta: un piquet just abans de l'inici del tram té s ≈ 1/fraccio ≫ 1, però el
            # mateix piquet mirat des de l'altra banda de l'origen pot ser el de l'extrem final.
            s_alt = s - (1.0 / fraccio)
            if -EPS_EXTREM_S <= s_alt <= EPS_EXTREM_S:
                dins.append(0.0)
    return tuple(sorted(dins))


# ─────────────────────────────────────────────────────────────────────────────
# Els tres senyals
# ─────────────────────────────────────────────────────────────────────────────

def casen_piquets(sa: tuple[float, ...], sb: tuple[float, ...]) -> tuple[bool, bool, float]:
    """Els piquets de dos trams: casen? En quin sentit? Amb quin desviament?

    Es prova en els dos sentits perquè **dues vores es cusen encarades**: el que en una va del
    principi al final, en l'altra sol anar del final al principi. Un matcher que només provés el
    sentit directe perdria la meitat de les costures d'una peça de roba —i les perdria en
    silenci, que és pitjor.
    """
    if len(sa) != len(sb) or not sa:
        return (False, False, 1.0)

    directe = max(abs(x - y) for x, y in zip(sa, sb))
    invers = max(abs(x - y) for x, y in zip(sa, tuple(1.0 - v for v in reversed(sb))))

    if invers < directe:
        return (invers <= TOL_PIQUET_S, True, invers)
    return (directe <= TOL_PIQUET_S, False, directe)


def senyal_piquets(a: Candidat, b: Candidat) -> tuple[Senyal, bool]:
    """El senyal FORT: les marques que el patronista ha posat perquè aquestes dues vores es trobin.

    Retorna també el sentit (invertit o no), que és el que després dirà a la màquina en quin
    ordre s'han de fer coincidir les marques.
    """
    na, nb = len(a.piquets), len(b.piquets)
    dades = {'n_a': na, 'n_b': nb}

    if na != nb:
        # Evidència EN CONTRA, no absència d'evidència: si un costat porta tres marques i l'altre
        # una, o no són la mateixa costura, o una de les dues peces està mal piquetada. Les dues
        # coses mereixen que la parella baixi a la llista, no que hi pugi.
        return (Senyal(
            mena='piquets', punts=-0.15,
            detall=f'Nombre de piquets diferent: {na} contra {nb}.',
            dades=dades,
        ), False)

    if na == 0:
        # Cap dels dos en porta: el senyal no diu res. No penalitza —moltes costures reals no
        # porten piquets— però tampoc no aporta, i la parella haurà de guanyar-se la vida amb la
        # longitud.
        return (Senyal(
            mena='piquets', punts=0.0,
            detall='Cap dels dos trams no porta piquets: el senyal no diu res.',
            dades=dades,
        ), False)

    casen, invertit, desviament = casen_piquets(a.piquets, b.piquets)
    dades = {**dades, 'desviament_s': round(desviament, 4), 'invertit': invertit}

    if not casen:
        return (Senyal(
            mena='piquets', punts=-0.10,
            detall=(f'Els {na} piquets no cauen als mateixos llocs: se separen fins a un '
                    f'{desviament * 100:.1f}% del tram.'),
            dades=dades,
        ), invertit)

    # Qualitat: com de clavades cauen les marques. Informació: quantes n'hi ha. Dos piquets (els
    # dos extrems del tram) diuen menys que quatre, i la confiança ho ha de notar — si no, un
    # tram qualsevol delimitat per girs valdria tant com una costura piquetada de debò.
    qualitat = 1.0 - (desviament / TOL_PIQUET_S)
    informacio = min(1.0, na / 3.0)
    return (Senyal(
        mena='piquets', punts=PES_PIQUETS * qualitat * informacio,
        detall=(f'{na} piquets homòlegs, {"invertits" if invertit else "en el mateix sentit"}, '
                f'amb un desviament màxim del {desviament * 100:.1f}% del tram.'),
        dades=dades,
    ), invertit)


def senyal_longitud(a: Candidat, b: Candidat) -> tuple[Senyal, str, float]:
    """Igual de llargs (casat) o un que sobra a posta (frunzit). Retorna també què proposar.

    **L'ordre de les dues preguntes és la decisió de disseny d'aquesta funció.** Primer
    «és el mateix, dins la tolerància?» (absoluta, en cm) i només després «un sobra
    sistemàticament?» (relativa, en %). A l'inrevés, un tram curt amb 2 mm de diferència sortiria
    com un frunzit del 2% —i un frunzit de 2 mm no és un frunzit: és el gruix del llapis.
    """
    la, lb = a.longitud_cm, b.longitud_cm
    diferencia = la - lb                       # amb signe: diu QUIN costat sobra
    excess = abs(diferencia)
    base = max(la, lb)
    relatiu = (excess / base) if base > 0 else 1.0
    dades = {
        'llarg_a_cm': round(la, 2), 'llarg_b_cm': round(lb, 2),
        'diferencia_cm': round(diferencia, 2), 'relatiu': round(relatiu, 4),
    }

    if excess <= TOL_CASAT_CM:
        return (Senyal(
            mena='longitud', punts=PES_LONGITUD,
            detall=f'Els dos costats fan el mateix: {la:.1f} i {lb:.1f} cm.',
            dades=dades,
        ), 'casat', 0.0)

    if FRUNZIT_MIN_REL <= relatiu <= FRUNZIT_MAX_REL:
        # El diferencial NO és una invenció: és la diferència llegida. Si la parella és bona,
        # aquests centímetres són l'embut que la cosidora ha d'arronsar; si no ho és, el
        # veredicte ho dirà. El motor no maquilla: proposa la xifra que ha mesurat.
        quin = a.piece_nom if diferencia > 0 else b.piece_nom
        return (Senyal(
            mena='longitud', punts=PES_LONGITUD * 0.6,
            detall=(f'Un costat sobra {excess:.1f} cm ({relatiu * 100:.1f}%): {quin} és el llarg. '
                    f'Dins del rang d\'un frunzit.'),
            dades={**dades, 'sobra': 'a' if diferencia > 0 else 'b'},
        ), 'frunzit', round(excess, 2))

    if relatiu < FRUNZIT_MIN_REL:
        # Passa de la tolerància però no arriba a frunzit: és un casat que no acaba de casar. Es
        # proposa igualment (i el veredicte dirà per quant no casa), amb mitja força.
        return (Senyal(
            mena='longitud', punts=PES_LONGITUD * 0.5,
            detall=(f'Gairebé iguals: {la:.1f} i {lb:.1f} cm ({excess:.1f} cm de diferència, '
                    f'un {relatiu * 100:.1f}%).'),
            dades=dades,
        ), 'casat', 0.0)

    return (Senyal(
        mena='longitud', punts=-0.30,
        detall=(f'Massa diferents: {la:.1f} i {lb:.1f} cm ({relatiu * 100:.0f}%). Ni casen ni és '
                f'un frunzit raonable.'),
        dades=dades,
    ), 'casat', 0.0)


def senyal_noms(a: Candidat, b: Candidat) -> Senyal:
    """El senyal feble: què diuen els noms de les peces. Mai proposa sol; sí que pot desproposar."""
    fam_a, fam_b = families(a.piece_nom), families(b.piece_nom)
    capa_a, capa_b = capa(a.piece_nom), capa(b.piece_nom)
    dades = {
        'peca_a': a.piece_nom, 'peca_b': b.piece_nom,
        'families_a': sorted(fam_a), 'families_b': sorted(fam_b),
        'capa_a': capa_a, 'capa_b': capa_b,
    }

    # Una entretela no es cus contra ningú: es termofixa. Al fitxer és una peça idèntica a la que
    # folra, i sense aquesta regla proposaria cosir-se amb ella amb una confiança altíssima —les
    # dues fan exactament el mateix, tram per tram.
    if CAPA_INTERLINING in (capa_a, capa_b):
        return Senyal(
            mena='noms', punts=-0.30,
            detall='Una de les dues és una entretela: es termofixa, no es cus.',
            dades={**dades, 'motiu': 'entretela'},
        )

    # La mateixa família i la mateixa capa: dues mànigues, dos colls. No són una costura, són la
    # mateixa peça duplicada (o el parell simètric) — i per longitud casarien perfectament.
    if fam_a and fam_a == fam_b and capa_a == capa_b:
        return Senyal(
            mena='noms', punts=-0.30,
            detall=(f'Les dues peces són el mateix ({", ".join(sorted(fam_a))}): una peça no es '
                    f'cus contra la seva bessona.'),
            dades={**dades, 'motiu': 'bessones'},
        )

    # Una VISTA es cus a la seva peça: comparteixen família (TATE_FACING_YOKE amb TATE_FRONT_YOKE)
    # i es diferencien per la capa. És la parella més ben fonamentada que un nom pot suggerir.
    if {capa_a, capa_b} == {CAPA_FACING, CAPA_SHELL} and (fam_a & fam_b):
        return Senyal(
            mena='noms', punts=PES_NOMS,
            detall=f'Una vista i la seva peça ({", ".join(sorted(fam_a & fam_b))}).',
            dades={**dades, 'motiu': 'vista'},
        )

    # Famílies veïnes DE LA MATEIXA CAPA: el davant amb l'esquena, la màniga amb el cos, el folre
    # amb el folre. Que les dues siguin folre (o les dues shell) importa: un folre no es cus
    # contra la tela de fora.
    if capa_a == capa_b and any(
        frozenset({x, y}) in VEINES for x in fam_a for y in fam_b if x != y
    ):
        parella = next(
            (x, y) for x in sorted(fam_a) for y in sorted(fam_b)
            if x != y and frozenset({x, y}) in VEINES
        )
        return Senyal(
            mena='noms', punts=PES_NOMS,
            detall=f'{parella[0]} amb {parella[1]}: peces veïnes.',
            dades={**dades, 'motiu': 'veines', 'parella': list(parella)},
        )

    # Sabem què són totes dues, i no es toquen: un coll no es cus a una màniga. **No és el
    # mateix que no saber-ho**, i per això són dues branques i no una: si el CAD bateja les peces
    # amb noms que el vocabulari no reconeix (`PIEZA_1`), el nom ha de callar i deixar decidir la
    # geometria; si els reconeix tots dos i diuen que no es toquen, això és informació i ha de
    # pesar. Sense aquesta branca, un coll i una màniga que casualment fan el mateix i porten un
    # piquet al mateix lloc —passa, i al TATE passava— es proposaven amb mitja confiança.
    if fam_a and fam_b and not (fam_a & fam_b):
        return Senyal(
            mena='noms', punts=-0.30,
            detall=(f'{", ".join(sorted(fam_a))} amb {", ".join(sorted(fam_b))}: no són peces '
                    f'veïnes.'),
            dades={**dades, 'motiu': 'llunyanes'},
        )

    return Senyal(
        mena='noms', punts=0.0,
        detall='Els noms de les peces no diuen ni que sí ni que no.',
        dades=dades,
    )


def _te_evidencia_geometrica(senyals: dict[str, Senyal]) -> bool:
    """Hi ha ALGUNA cosa més que el nom?

    La llei del brief, escrita com a porta i no com a pes: **el nom mai és suficient sol**. Si el
    únic senyal a favor fos que una peça es diu FRONT i l'altra BACK, el motor estaria proposant
    per lèxic, no per patró — i el dia que algú bategés les peces d'una altra manera, el motor
    es quedaria mut o mentiria. La geometria mana; el nom acompanya.
    """
    return senyals['piquets'].punts > 0 or senyals['longitud'].punts > 0


def avaluar(a: Candidat, b: Candidat) -> Proposta | None:
    """Els tres senyals sobre una parella. `None` si no arriba a proposta."""
    s_piquets, invertit = senyal_piquets(a, b)
    s_longitud, tipus, diferencial = senyal_longitud(a, b)
    s_noms = senyal_noms(a, b)
    senyals = {'piquets': s_piquets, 'longitud': s_longitud, 'noms': s_noms}

    if not _te_evidencia_geometrica(senyals):
        return None

    confianca = s_piquets.punts + s_longitud.punts + s_noms.punts
    confianca = max(0.0, min(1.0, confianca))
    if confianca < LLINDAR_PROPOSTA:
        return None

    return Proposta(
        a=a, b=b, tipus=tipus, diferencial_cm=diferencial,
        confianca=round(confianca, 3), invertit=invertit,
        # Ordenades per FORÇA: qui llegeixi la proposta ha de trobar primer el motiu que més
        # pesa, no el primer que el codi ha calculat.
        senyals=tuple(sorted(senyals.values(), key=lambda s: -abs(s.punts))),
    )


# ─────────────────────────────────────────────────────────────────────────────
# El repartiment
# ─────────────────────────────────────────────────────────────────────────────

def proposar(
    candidats: list[Candidat],
    exclosos: frozenset[tuple[int, int]] = frozenset(),
    descartats: Descartats | None = None,
) -> tuple[list[Proposta], Descartats]:
    """Totes les parelles possibles, ordenades per confiança i repartides sense conflictes.

    `exclosos` són les parelles que una persona ja ha rebutjat, per la clau canònica
    `(segment_id petit, segment_id gran)`. Un rebuig és PERSISTENT: la proposta rebutjada no
    torna a sortir a cada recàrrega —tornar-la a oferir seria no haver escoltat—, però tampoc no
    bloqueja els seus trams, que queden lliures per a la parella bona.

    **Només parelles de peces DIFERENTS.** Dos trams de la mateixa peça que fan el mateix són,
    gairebé sempre, els dos costats simètrics de la peça (els dos laterals de l'esquena fan
    exactament el mateix i NO es cusen l'un amb l'altre), o els dos costats d'una pinça —que té
    la seva pròpia eina i la seva pròpia llei. Proposar-los seria omplir la llista de disbarats
    amb la màxima confiança, i el cost de no fer-ho és que una costura interna d'una peça (la
    costura de sota-màniga) s'ha de declarar a mà. És un canvi que val la pena.
    """
    desc = descartats or Descartats()

    parelles: list[Proposta] = []
    for i in range(len(candidats)):
        for j in range(i + 1, len(candidats)):
            a, b = candidats[i], candidats[j]
            if a.piece_id == b.piece_id:
                continue
            if clau_parella(a.segment_id, b.segment_id) in exclosos:
                desc = _mes(desc, rebutjades=1)
                continue
            proposta = avaluar(a, b)
            if proposta is None:
                desc = _mes(desc, sota_llindar=1)
                continue
            parelles.append(proposta)

    # Repartiment voraç: la millor primera. Un tram adjudicat no es torna a oferir — cosir-lo dues
    # vegades és el defecte que `validar_cobertura` denuncia, i val més no proposar-lo que
    # proposar-lo i denunciar-lo després.
    parelles.sort(key=lambda p: (-p.confianca, p.a.segment_id, p.b.segment_id))
    presos: set[int] = set()
    triades: list[Proposta] = []
    for p in parelles:
        if p.a.segment_id in presos or p.b.segment_id in presos:
            desc = _mes(desc, en_conflicte=1)
            continue
        presos.add(p.a.segment_id)
        presos.add(p.b.segment_id)
        triades.append(p)

    return triades, desc


def clau_parella(a: int, b: int) -> tuple[int, int]:
    """La clau CANÒNICA d'una parella: sempre el mateix ordre.

    Una costura no té costat A i costat B «de veritat» —quin és quin depèn de com s'ha mirat—, i
    si el rebuig es desés amb l'ordre en què va arribar, la mateixa parella rebutjada tornaria a
    sortir mirada de l'altra banda."""
    return (a, b) if a <= b else (b, a)


def _mes(d: Descartats, **camps) -> Descartats:
    return Descartats(**{**d.__dict__, **{k: getattr(d, k) + v for k, v in camps.items()}})
