"""On hi ha una pinça: la PROPOSTA.

Germà d'`engine.seam_matching` i amb la mateixa llei: **proposar, mai escriure**. Aquí es
llegeix la vora i es diu on sembla que hi ha una pinça, amb quines mesures i per què. Confirmar
és el gest manual de W4b (tres clics), i el fa una persona.

─────────────────────────────────────────────────────────────────────────────
LA PINÇA DE VORA APUNTA CAP A FORA, NO CAP A DINS
─────────────────────────────────────────────────────────────────────────────
Mesurat sobre el TATE, i comprovat de dues maneres independents (el signe del producte
vectorial contra l'orientació del contorn, i un ray-casting del vèrtex contra el polígon): la
pinça real del TATE —la del banc de W4b, costats 1,33 i 1,01 cm— té el **vèrtex FORA de la
peça**. No és una anomalia del fitxer: és com s'ha de dibuixar.

Una pinça de vora és tela que SOBRA a la vora i que desapareix quan es cus. Perquè desaparegui
cosint-la, ha d'HI SER: el patronista afegeix la boca de la pinça al perfil, i per això la vora
fa una V cap enfora. Quan els dos costats es cusen l'un contra l'altre, la V es plega, els dos
extrems de la boca passen a ser el mateix punt, i la vora queda llisa i casa amb la peça del
costat. És exactament el que diu l'aritmètica del banc: el davanter fa 32,13 cm de contorn i
l'esquena 29,80 — i els 2,34 que sobren SÓN la pinça (32,13 − 2,34 = 29,79 · casa).

Si la V anés cap a dins, la vora seria més CURTA, no més llarga, i no hi hauria res per cosir:
seria una osca retallada, no una pinça. Un detector que exigís «desviació cap a dins» rebutjaria
la pinça de referència d'aquest projecte.

(Les pinces INTERIORS —les que el CAD dibuixa com una tascó dins del cos de la peça, a la capa
de línies internes— són una altra bèstia i no viuen a la vora. Aquest detector no les mira.)

─────────────────────────────────────────────────────────────────────────────
QUÈ SEPARA UNA PINÇA D'UNA CANTONADA (i per què no és la forma)
─────────────────────────────────────────────────────────────────────────────
La temptació és buscar una forma: costats semblants, prou fondària, una V neta. No funciona, i
el material ho demostra. Al TATE:

  · pinça real  (69→70→71): costats 1,33 + 1,01 · boca 2,00 cm · fondària 0,60
  · cantonada   (81→97→98): costats 5,05 + 4,50 · boca 8,20 cm · fondària 2,29

Les DUES ràtios són iguals (boca/costats ≈ 0,86; fondària/boca ≈ 0,29). Són la mateixa forma a
escales diferents, i cap criteri invariant d'escala les pot distingir. El que les separa és la
**MIDA DE LA BOCA CONTRA LA VORA**: la pinça n'ocupa l'1,1%; totes les cantonades i corbes del
fitxer, un 3,1% o més. Una pinça és un accident LOCAL d'una vora llarga; una cantonada és
l'estructura de la peça.

Per això el llindar que mana és `BOCA_MAX_REL`, i els altres (simetria, fondària) són portes de
sanejament que treuen les degeneracions —trams rectes, osques de piquet— no el criteri central.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from .seam_matching import Senyal

MM_PER_CM = 10.0

#: **El llindar que mana.** La boca d'una pinça, contra la longitud de la vora. Calibrat sobre el
#: TATE: les dues pinces reals fan l'1,1% i el fals positiu més proper (una cantonada de
#: l'esquena) el 3,4%. El 2% passa pel mig amb marge als dos costats.
BOCA_MAX_REL = 0.02

#: Els dos costats d'una pinça es cusen l'un contra l'altre: si no fan el mateix, la pinça no
#: tanca plana. Es demana que s'assemblin (el brief: 0,7–1,3), i la ràtio real del TATE és 0,77
#: —desiguals, i W4b ja ho havia denunciat (3,1 mm de diferència). El detector no ho amaga: ho
#: cobra a la confiança.
RATIO_MIN = 0.7

#: Fondària mínima del vèrtex respecte de la corda de la boca. Sense això, tres girs gairebé
#: alineats (una recta amb un vèrtex al mig, que al TATE n'hi ha) passarien per pinces de
#: fondària zero.
PROF_MIN_CM = 0.3

#: Per sota d'això no es proposa. Com a A2: no és un llindar de veritat, és un llindar de soroll.
LLINDAR_PINCA = 0.30

#: Pesos de la confiança.
PES_BOCA = 0.45
PES_SIMETRIA = 0.35
PES_PIQUETS = 0.20

#: Un piquet «marca» un extrem de la boca si cau a menys d'això (mm d'arc) del punt.
#:
#: És GENEROSA a posta. Cada piquet arriba dues vegades del CAD (la còpia del tall i la del
#: cosit) i la deduplicació d'A2 es queda la primera que troba, que pot ser la de l'ALTRA línia:
#: projectada sobre la vora base, cau fins a 5 mm més enllà del punt que marca. Amb una
#: tolerància estreta, el piquet de la pinça del TATE —que hi és— no es veuria. Val més una
#: tolerància ampla en un senyal que només SUMA confiança que no un senyal mut.
TOL_PIQUET_BOCA_MM = 12.0


@dataclass(frozen=True)
class CandidatPinca:
    """Una V de la vora que sembla una pinça, amb tot el que cal per discutir-la.

    Els tres punts són ÍNDEXS de vèrtex de la vora, no coordenades: el gest de W4b es fa amb tres
    punts existents, i el que es proposa ha de ser exactament el que després es confirma.
    """
    piece_id: int
    piece_nom: str
    vora: int
    #: Els tres vèrtexs: inici de la boca, vèrtex de la pinça, final de la boca.
    index_a: int
    index_vertex: int
    index_b: int
    costat_a_cm: float
    costat_b_cm: float
    boca_cm: float
    profunditat_cm: float
    #: boca / longitud de la vora. El número que de debò decideix.
    boca_rel: float
    ratio: float
    #: Quants dels dos extrems de la boca porten piquet (0, 1 o 2).
    piquets_boca: int
    confianca: float
    senyals: tuple[Senyal, ...]

    @property
    def intake_cm(self) -> float:
        """La tela que la pinça es menja: la suma dels seus dos costats.

        És, exactament, el número que després apareixerà restat a la costura que la conté
        (`sew.descomptar_pinces`). Al TATE: 1,33 + 1,01 = 2,34.
        """
        return self.costat_a_cm + self.costat_b_cm


def _longitud(punts) -> float:
    return sum(
        hypot(punts[i + 1].x - punts[i].x, punts[i + 1].y - punts[i].y)
        for i in range(len(punts) - 1)
    )


def _arc(pts, i: int, j: int) -> list:
    """Els punts de la vora d'un índex a un altre, donant la volta si cal."""
    return list(pts[i:j + 1]) if i <= j else list(pts[i:]) + list(pts[:j + 1])


def _area_signada(pts) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        a += p.x * q.y - q.x * p.y
    return a / 2.0


def apex_cap_enfora(pts, ia: int, ib: int, ic: int) -> bool:
    """El vèrtex de la V, ¿surt de la peça?

    Es decideix pel signe del gir (A→B→C) contra l'orientació del contorn. En un contorn CCW
    l'interior queda a l'esquerra, i un vèrtex que gira a l'esquerra és una punta que SURT.

    És la condició que fa que la V sigui tela que SOBRA —i per tant cosible— i no una osca
    retallada. Vegeu la capçalera del mòdul: és el que el TATE fa, i el que el brief d'A1 deia a
    l'inrevés.
    """
    A, B, C = pts[ia], pts[ib], pts[ic]
    creu = (B.x - A.x) * (C.y - B.y) - (B.y - A.y) * (C.x - B.x)
    orientacio = 1.0 if _area_signada(pts) > 0 else -1.0
    return (creu * orientacio) > 0


def metriques(pts, ia: int, ib: int, ic: int) -> dict:
    """Les mesures d'una V: costats, boca, fondària. Sense judicar-la."""
    A, B, C = pts[ia], pts[ib], pts[ic]
    costat_a = _longitud(_arc(pts, ia, ib))
    costat_b = _longitud(_arc(pts, ib, ic))
    boca = hypot(C.x - A.x, C.y - A.y)

    # Fondària: distància del vèrtex a la corda de la boca. Amb la boca degenerada (els dos
    # extrems al mateix lloc) la corda no defineix cap direcció, i la fondària és la distància
    # pelada al punt — que és el que vol dir, i no una divisió per zero.
    if boca <= 1e-9:
        profunditat = hypot(B.x - A.x, B.y - A.y)
    else:
        profunditat = abs(
            (B.x - A.x) * (C.y - A.y) - (B.y - A.y) * (C.x - A.x)) / boca

    return {
        'costat_a_mm': costat_a,
        'costat_b_mm': costat_b,
        'boca_mm': boca,
        'profunditat_mm': profunditat,
        'ratio': (min(costat_a, costat_b) / max(costat_a, costat_b)
                  if max(costat_a, costat_b) > 0 else 0.0),
    }


def _senyal_boca(boca_rel: float) -> Senyal:
    """El senyal que MANA: com de local és la V respecte de la vora sencera."""
    qualitat = 1.0 - (boca_rel / BOCA_MAX_REL)
    return Senyal(
        mena='boca', punts=PES_BOCA * max(0.0, qualitat),
        detall=(f'La boca ocupa el {boca_rel * 100:.1f}% de la vora: és un accident local, no '
                f'una cantonada de la peça.'),
        dades={'boca_rel': round(boca_rel, 5), 'max_rel': BOCA_MAX_REL},
    )


def _senyal_simetria(ratio: float) -> Senyal:
    """Els dos costats es cusen l'un contra l'altre: si no fan el mateix, la pinça no tanca plana."""
    qualitat = 1.0 - (abs(1.0 - ratio) / (1.0 - RATIO_MIN))
    return Senyal(
        mena='simetria', punts=PES_SIMETRIA * max(0.0, qualitat),
        detall=(f'Els dos costats es diferencien un {abs(1.0 - ratio) * 100:.0f}% '
                f'(ràtio {ratio:.2f}).'),
        dades={'ratio': round(ratio, 3), 'ratio_min': RATIO_MIN},
    )


def _senyal_piquets(n: int) -> Senyal:
    """Els dos extrems de la boca, marcats.

    El piquet és l'única marca que el patronista posa EXPRESSAMENT perquè dues vores es trobin, i
    els dos extrems de la boca d'una pinça s'han de trobar quan es tanca. Que hi siguin tots dos
    és el CAD dient que allò es cus.
    """
    return Senyal(
        mena='piquets', punts=PES_PIQUETS * (n / 2.0),
        detall=(f'{n} dels 2 extrems de la boca porten piquet.' if n
                else 'Cap extrem de la boca no porta piquet.'),
        dades={'piquets_boca': n},
    )


def detectar(
    pts,
    girs: list[int],
    longitud_vora_mm: float,
    piquets_t: tuple[float, ...],
    acumulats: list[float],
    piece_id: int,
    piece_nom: str,
    vora: int,
) -> list[CandidatPinca]:
    """Les V de la vora que semblen pinces.

    Es miren TOTES les ternes de girs CONSECUTIVS (A→vèrtex→B), donant la volta a la vora. Els
    punts de corba no hi entren: una pinça és una cantonada de la vora, i el gir és justament el
    que el CAD marca com a cantonada (la mateixa llei que la segmentació de W1).
    """
    n = len(girs)
    if n < 3 or longitud_vora_mm <= 0:
        return []

    candidats: list[CandidatPinca] = []
    for k in range(n):
        ia, ib, ic = girs[k], girs[(k + 1) % n], girs[(k + 2) % n]
        if len({ia, ib, ic}) < 3:
            continue

        m = metriques(pts, ia, ib, ic)
        boca_rel = m['boca_mm'] / longitud_vora_mm

        # ── Les portes. Fallar-ne una és no ser una pinça, i no es negocia amb la confiança:
        # una V que no compleix la signatura no és una pinça fluixa, és una altra cosa.
        if boca_rel > BOCA_MAX_REL:
            continue                                   # una cantonada de la peça
        if m['ratio'] < RATIO_MIN:
            continue                                   # costats massa desiguals: no tanca plana
        if m['profunditat_mm'] / MM_PER_CM < PROF_MIN_CM:
            continue                                   # tres girs gairebé alineats: no és cap V
        if not apex_cap_enfora(pts, ia, ib, ic):
            continue                                   # osca retallada, no tela que sobri

        n_piquets = sum(
            1 for idx in (ia, ic)
            if _te_piquet(acumulats, longitud_vora_mm, piquets_t, idx)
        )

        senyals = (
            _senyal_boca(boca_rel),
            _senyal_simetria(m['ratio']),
            _senyal_piquets(n_piquets),
        )
        confianca = min(1.0, max(0.0, sum(s.punts for s in senyals)))
        if confianca < LLINDAR_PINCA:
            continue

        candidats.append(CandidatPinca(
            piece_id=piece_id, piece_nom=piece_nom, vora=vora,
            index_a=ia, index_vertex=ib, index_b=ic,
            costat_a_cm=round(m['costat_a_mm'] / MM_PER_CM, 2),
            costat_b_cm=round(m['costat_b_mm'] / MM_PER_CM, 2),
            boca_cm=round(m['boca_mm'] / MM_PER_CM, 2),
            profunditat_cm=round(m['profunditat_mm'] / MM_PER_CM, 2),
            boca_rel=round(boca_rel, 5),
            ratio=round(m['ratio'], 3),
            piquets_boca=n_piquets,
            confianca=round(confianca, 3),
            # Ordenats per força, com a A2: primer el motiu que més pesa.
            senyals=tuple(sorted(senyals, key=lambda s: -abs(s.punts))),
        ))

    candidats.sort(key=lambda c: (-c.confianca, c.index_vertex))
    return candidats


def _te_piquet(
    acumulats: list[float], total_mm: float, piquets_t: tuple[float, ...], idx: int,
) -> bool:
    """Aquest vèrtex, ¿porta piquet?"""
    if not piquets_t or total_mm <= 0 or idx >= len(acumulats):
        return False
    t = acumulats[idx] / total_mm
    for q in piquets_t:
        d = abs(t - q) % 1.0
        if min(d, 1.0 - d) * total_mm <= TOL_PIQUET_BOCA_MM:
            return True
    return False


def clau_pinca(punt_a: int, punt_vertex: int, punt_b: int) -> tuple[int, int, int]:
    """La clau CANÒNICA d'una pinça proposada: sempre el mateix ordre.

    Una V no té un costat A i un costat B «de veritat» —depèn de per quina banda es recorre la
    vora—, i si el rebuig es desés amb l'ordre en què va arribar, la mateixa pinça rebutjada
    tornaria a sortir llegida a l'inrevés. El vèrtex és el vèrtex i no es mou; els dos extrems
    de la boca s'ordenen. (Mateix principi que `seam_matching.clau_parella`.)
    """
    a, b = (punt_a, punt_b) if punt_a <= punt_b else (punt_b, punt_a)
    return (a, punt_vertex, b)
