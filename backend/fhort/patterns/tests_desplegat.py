"""Regressió del desplegat: `unfold_piece` contra material CAD real amb doblec.

Aquests tests neixen d'un defecte VIU trobat al cens
`docs/diagnosis/QA_TALLER_D_CONVENCIO_RECORREGUT_2026-08-25.md`: `_mirror_points`
empelta la còpia reflectida al final de la llista, o sigui que substitueix l'aresta de
TANCAMENT del bucle. Això només és correcte si aquella aresta és la vora del doblec —
i si ho és o no depèn **d'on el CAD va obrir la polilínia**, que és arbitrari.

De les 13 peces amb doblec del material real, **8 l'obrien en un altre lloc** i en
sortia un contorn creuat. El cas canònic és la peça 14 del CALLIE: un llaç en forma de
vuit d'àrea |−52.511| mm² quan la peça en fa 105.000.

⚠️ **Cap d'aquests tests no s'hauria pogut escriure amb un fixture sintètic.** El
defecte depèn d'una llibertat del format (per quin vèrtex s'obre un bucle tancat) que
només el material de veritat exercita. Per això T6-T8 van contra el CAD real i T9 —el
cas mínim— es construeix a mà, com a xarxa per al dia que el material canviï.

Viuen en un fitxer PROPI i no a `patterns/tests.py` perquè es puguin córrer sols: la
verificació d'aquest fix és proporcional al fix, i la suite de l'app no hi entra.
"""
from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from fhort.patterns.engine.aama_reader import (
    AAMAReader, _mirror_xy, _on_axis, unfold_piece,
)
from fhort.patterns.engine.geometry import LayerRole, PointData

FIXTURES = Path(__file__).parent / 'tests' / 'fixtures'

#: El CALLIE: l'únic material amb el recorregut en sentit HORARI (30 vores tancades de
#: 30) i el que porta totes les topologies d'eix que trencaven el desplegat — tirades
#: d'1, 3 i 5 punts, als extrems del bucle i al mig.
CALLIE_DXF = FIXTURES / 'CALLIE_prova.dxf'
CALLIE_DXF_MD5 = '0671cf5c6196ff7d167935bd263e1a06'

#: El MEREDITH: PolyPattern i antihorari, i tanmateix amb dues peces trencades. És la
#: prova que el defecte NO és del sentit del CAD sinó de l'origen del bucle — i porta
#: l'únic cas «trencat de poc» (àrea 1,96× en comptes de 2×), que el cens va donar per
#: bo i no ho era.
MEREDITH_DXF = FIXTURES / 'MEREDITH_prova.dxf'
MEREDITH_DXF_MD5 = '901504269f690d59e58a27c7425930b6'

#: Tolerància de l'àrea: 1 % de 2×. Les vores corbes es mostregen igual abans i després,
#: així que la igualtat hauria de ser exacta; l'1 % és per al soroll de coma flotant.
TOL_AREA = 0.01

#: Tolerància geomètrica punt a punt, en mm. Els punts no es MOUEN mai: només es
#: reordenen. Qualsevol desviació és un error de càlcul, no d'arrodoniment.
TOL_MM = 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# Utillatge de mesura
# ─────────────────────────────────────────────────────────────────────────────

def area_signada(punts) -> float:
    """Shoelace. El SIGNE hi és a posta: un contorn que es creua a ell mateix té els
    dos lòbuls de signe contrari i l'àrea se li cancel·la, que és justament el símptoma
    que aquests tests han de saber veure."""
    total = 0.0
    n = len(punts)
    for i in range(n):
        a, b = punts[i], punts[(i + 1) % n]
        total += a.x * b.y - b.x * a.y
    return total / 2.0


def _mirall_llegat(points, fold):
    """El `_mirror_points` D'ABANS DEL FIX, literal.

    És la referència de T8: per a les peces que el llegat ja resolia bé, el resultat
    nou ha de ser el MATEIX. Es copia aquí en comptes de mesurar-la contra una llista
    de noms de peça perquè el test no depengui de cap recompte escrit a mà: qui decideix
    quines peces «ja anaven bé» és el llegat mateix, executant-se.
    """
    reflectits = [
        PointData(
            *_mirror_xy(p.x, p.y, fold),
            kind=p.kind, grade_rule=p.grade_rule, raw=p.raw,
        )
        for p in reversed(points)
        if not _on_axis(p.x, p.y, fold)
    ]
    return tuple(points) + tuple(reflectits)


def _orientacio(a, b, c) -> float:
    return (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)


def _es_creuen(p1, p2, p3, p4, eps: float = 1e-9) -> bool:
    """Dos segments es creuen DE DEBÒ (no només es toquen per un extrem).

    Es demana canvi de signe ESTRICTE als dos costats: dos segments que comparteixen un
    vèrtex, o que es toquen de punta, no compten. El que es busca és el creuament
    pròpiament dit —el del llaç en vuit—, no la tangència, que en un contorn real amb
    punts repetits o quasi-col·lineals apareix sense voler dir res.
    """
    d1, d2 = _orientacio(p3, p4, p1), _orientacio(p3, p4, p2)
    d3, d4 = _orientacio(p1, p2, p3), _orientacio(p1, p2, p4)
    return ((d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps)) and \
           ((d3 > eps and d4 < -eps) or (d3 < -eps and d4 > eps))


def auto_interseccions(punts) -> list[tuple[int, int]]:
    """Parelles d'arestes NO adjacents del bucle tancat que es creuen."""
    n = len(punts)
    fora: list[tuple[int, int]] = []
    for i in range(n):
        for j in range(i + 1, n):
            if i == j or (j - i) % n <= 1 or (i - j) % n <= 1:
                continue
            if _es_creuen(punts[i], punts[(i + 1) % n], punts[j], punts[(j + 1) % n]):
                fora.append((i, j))
    return fora


def peces_amb_doblec():
    """Les peces amb doblec del material real, amb la seva vora de TALL tancada.

    Rendeix `(etiqueta, peça, vora_de_tall, eix)`.
    """
    for fitxer, tag in ((MEREDITH_DXF, 'MEREDITH'), (CALLIE_DXF, 'CALLIE')):
        doc = AAMAReader().read(fitxer.read_bytes())
        for piece in doc.pieces:
            if not piece.has_fold:
                continue
            vora = piece.boundary(LayerRole.CUT)
            if vora is None or not vora.closed or len(vora.points) < 3:
                continue
            yield f'{tag}:{piece.nom_block}', piece, vora, piece.doblec_original


def vora_desplegada(piece):
    return unfold_piece(piece).boundary(LayerRole.CUT)


class MaterialTest(unittest.TestCase):
    """Si el material canvia, els números d'aquests tests deixen de voler dir res."""

    def test_el_material_no_ha_canviat(self):
        for ruta, md5 in ((CALLIE_DXF, CALLIE_DXF_MD5), (MEREDITH_DXF, MEREDITH_DXF_MD5)):
            with self.subTest(fitxer=ruta.name):
                self.assertEqual(hashlib.md5(ruta.read_bytes()).hexdigest(), md5)

    def test_hi_ha_les_tretze_peces_amb_doblec(self):
        """El cens en va comptar 13. Si en surten més o menys, el material ha canviat i
        la cobertura d'aquests tests ja no és la que diuen que és."""
        self.assertEqual(len(list(peces_amb_doblec())), 13)


class T6AreaDelDesplegatTest(unittest.TestCase):
    """T6 — desplegar ha de DOBLAR l'àrea, i el signe ha de ser un de sol.

    Les dues meitats d'una peça de doblec són congruents: la sencera fa exactament el
    doble. Que l'àrea no dobli vol dir que el contorn no és el que crèiem —i si a més
    canvia de signe, és que els dos lòbuls s'estan cancel·lant, o sigui que es creuen.
    """

    def test_larea_del_desplegat_es_el_doble_de_la_meitat(self):
        for etiqueta, piece, vora, _fold in peces_amb_doblec():
            with self.subTest(peca=etiqueta):
                mitja = area_signada(list(vora.points))
                sencera = area_signada(list(vora_desplegada(piece).points))
                self.assertNotAlmostEqual(mitja, 0.0, msg='la meitat no té àrea')
                self.assertAlmostEqual(
                    sencera / mitja, 2.0, delta=TOL_AREA,
                    msg=f'{etiqueta}: la meitat fa {mitja:.1f} i la sencera {sencera:.1f}',
                )

    def test_el_signe_no_es_cancel_la(self):
        """El símptoma del llaç en vuit, aïllat: la peça 14 del CALLIE donava
        −52.511 → +52.511, i la 13 queia a −0,00. Mateix signe i magnitud creixent."""
        for etiqueta, piece, vora, _fold in peces_amb_doblec():
            with self.subTest(peca=etiqueta):
                mitja = area_signada(list(vora.points))
                sencera = area_signada(list(vora_desplegada(piece).points))
                self.assertGreater(
                    mitja * sencera, 0.0,
                    msg=f'{etiqueta}: el desplegat canvia de signe (lòbuls que es cancel·len)',
                )
                self.assertGreater(abs(sencera), abs(mitja))


class T7SenseAutoInterseccioTest(unittest.TestCase):
    """T7 — el contorn desplegat no s'ha de creuar a ell mateix.

    És la prova DIRECTA del defecte: l'àrea pot sortir bé per compensació, però un
    contorn creuat no és una peça i res que el consumeixi després (mesurar, cosir,
    escalar, dibuixar) en pot treure res de bo.
    """

    def test_cap_peca_desplegada_no_es_creua(self):
        for etiqueta, piece, _vora, _fold in peces_amb_doblec():
            with self.subTest(peca=etiqueta):
                creuaments = auto_interseccions(list(vora_desplegada(piece).points))
                self.assertEqual(
                    creuaments, [],
                    msg=f'{etiqueta}: {len(creuaments)} creuament(s), p.ex. arestes {creuaments[:3]}',
                )

    def test_la_meitat_dorigen_tampoc_no_es_creua(self):
        """Control: si la MEITAT ja vingués creuada del CAD, T7 estaria mesurant el
        material i no el fix."""
        for etiqueta, _piece, vora, _fold in peces_amb_doblec():
            with self.subTest(peca=etiqueta):
                self.assertEqual(auto_interseccions(list(vora.points)), [])


class T8SenseRegressioTest(unittest.TestCase):
    """T8 — el que el llegat ja resolia bé, ha de sortir IDÈNTIC.

    Qui decideix quines peces entren aquí no és una llista escrita a mà: és el llegat,
    executant-se. Una peça hi entra si el `_mirror_points` d'abans del fix ja li donava
    el doble d'àrea. Així el test no depèn de cap recompte —ni del meu.
    """

    def _peces_que_el_llegat_ja_resolia(self):
        for etiqueta, piece, vora, fold in peces_amb_doblec():
            mitja = area_signada(list(vora.points))
            llegat = _mirall_llegat(vora.points, fold)
            if abs(area_signada(list(llegat)) / mitja - 2.0) <= TOL_AREA:
                yield etiqueta, piece, llegat

    def test_hi_ha_peces_que_el_llegat_ja_resolia(self):
        """Si això falla, T8 no està provant res."""
        self.assertEqual(len(list(self._peces_que_el_llegat_ja_resolia())), 5)

    def test_el_resultat_no_canvia_on_ja_era_correcte(self):
        for etiqueta, piece, llegat in self._peces_que_el_llegat_ja_resolia():
            with self.subTest(peca=etiqueta):
                nou = list(vora_desplegada(piece).points)
                self.assertEqual(len(nou), len(llegat), f'{etiqueta}: ha canviat de mida')
                for i, (a, b) in enumerate(zip(nou, llegat)):
                    self.assertAlmostEqual(a.x, b.x, delta=TOL_MM, msg=f'{etiqueta} punt {i}')
                    self.assertAlmostEqual(a.y, b.y, delta=TOL_MM, msg=f'{etiqueta} punt {i}')

    def test_els_punts_no_es_mouen_mai(self):
        """El fix reordena i poda; no MOU res. Cada punt del desplegat ha de ser un punt
        de la meitat o el mirall exacte d'un punt de la meitat."""
        for etiqueta, piece, vora, fold in peces_amb_doblec():
            with self.subTest(peca=etiqueta):
                originals = {(round(p.x, 6), round(p.y, 6)) for p in vora.points}
                originals |= {
                    tuple(round(v, 6) for v in _mirror_xy(p.x, p.y, fold))
                    for p in vora.points
                }
                for p in vora_desplegada(piece).points:
                    self.assertIn((round(p.x, 6), round(p.y, 6)), originals,
                                  f'{etiqueta}: punt inventat a ({p.x}, {p.y})')


class T9CasMinimTest(unittest.TestCase):
    """T9 — el cas sintètic que hauria caçat el defecte el dia zero.

    Un quadrat a la dreta d'un eix vertical, amb els dos vèrtexs de l'eix als índexs
    INTERIORS del bucle. És la peça 14 del CALLIE reduïda a la seva essència, i és
    l'única forma d'aquests tests que no depèn de cap fitxer.
    """

    #: Eix vertical x=0. El quadrat va de x=0 a x=10, y=0 a y=10.
    EIX = ((0.0, 0.0), (0.0, 10.0))

    def _peca(self, punts):
        from fhort.patterns.engine.geometry import (
            BoundaryData, FoldData, PieceData, PieceMetadata, PointKind,
        )
        (x1, y1), (x2, y2) = self.EIX
        fold = FoldData(x1, y1, x2, y2, materialitzat=False, costat=1)
        vora = BoundaryData(
            role=LayerRole.CUT, layer='1', closed=True,
            points=tuple(PointData(x=x, y=y, kind=PointKind.TURN) for x, y in punts),
        )
        return PieceData(
            nom_block='T9', boundaries=(vora,), notches=(), grain=None,
            metadata=PieceMetadata(), rol='T9', doblec_original=fold,
            has_sew=False, has_fold=True, unknown_layers=(), raw_entities=(),
            insert_at=(0.0, 0.0), poms=(),
        )

    #: El mateix quadrat obert per cadascun dels seus quatre vèrtexs, batejats per ON
    #: cauen els dos punts de l'eix. En un bucle tancat, per on s'obre no vol dir res:
    #: les quatre rotacions són LA MATEIXA peça i han de donar el mateix desplegat.
    #:
    #: 🔑 Només `eix_al_tancament` funcionava abans del fix — és l'única on l'aresta de
    #: l'eix és la de tancament (índexs 0 i n−1). Les altres tres són el defecte.
    ROTACIONS = {
        'eix_al_tancament': [(0, 0), (10, 0), (10, 10), (0, 10)],   # eix a {0, 3}
        'eix_al_principi': [(0, 10), (0, 0), (10, 0), (10, 10)],    # eix a {0, 1}
        'eix_al_mig': [(10, 10), (0, 10), (0, 0), (10, 0)],         # eix a {1, 2}
        'eix_al_final': [(10, 0), (10, 10), (0, 10), (0, 0)],       # eix a {2, 3}
    }

    def test_totes_les_rotacions_donen_la_mateixa_area(self):
        for nom, punts in self.ROTACIONS.items():
            with self.subTest(rotacio=nom):
                piece = self._peca(punts)
                mitja = abs(area_signada(list(piece.boundaries[0].points)))
                sencera = abs(area_signada(list(vora_desplegada(piece).points)))
                self.assertAlmostEqual(mitja, 100.0, delta=1e-9)
                self.assertAlmostEqual(
                    sencera, 200.0, delta=1e-9,
                    msg=f'{nom}: el desplegat fa {sencera}, no 200 (20 x 10)',
                )

    def test_cap_rotacio_no_produeix_un_contorn_creuat(self):
        for nom, punts in self.ROTACIONS.items():
            with self.subTest(rotacio=nom):
                pts = list(vora_desplegada(self._peca(punts)).points)
                self.assertEqual(auto_interseccions(pts), [])

    def test_el_desplegat_va_de_menys_deu_a_deu(self):
        """La comprovació d'amplada: el quadrat desplegat ocupa els dos semiplans."""
        for nom, punts in self.ROTACIONS.items():
            with self.subTest(rotacio=nom):
                xs = [p.x for p in vora_desplegada(self._peca(punts)).points]
                self.assertAlmostEqual(min(xs), -10.0, delta=1e-9)
                self.assertAlmostEqual(max(xs), 10.0, delta=1e-9)

    def test_els_punts_de_leix_no_es_dupliquen(self):
        """Els dos vèrtexs de l'eix són la frontissa: hi han de ser un sol cop."""
        for nom, punts in self.ROTACIONS.items():
            with self.subTest(rotacio=nom):
                pts = vora_desplegada(self._peca(punts)).points
                a_leix = [p for p in pts if abs(p.x) < 1e-9]
                self.assertEqual(len(a_leix), 2, f'{nom}: {len(a_leix)} punts sobre l\'eix')

    def test_una_tirada_deix_subdividida_perd_els_interiors(self):
        """Una vora de doblec amb un punt EXTRA al mig (el cas [0, 39, 40] del MEREDITH):
        l'interior és de la vora del doblec, que en desplegar queda a dins de la peça i
        desapareix. Han de sobreviure els dos extrems i cap més."""
        piece = self._peca([(0, 10), (0, 5), (0, 0), (10, 0), (10, 10)])
        pts = vora_desplegada(piece).points
        self.assertEqual(len([p for p in pts if abs(p.x) < 1e-9]), 2)
        self.assertAlmostEqual(abs(area_signada(list(pts))), 200.0, delta=1e-9)
        self.assertEqual(auto_interseccions(list(pts)), [])


class T9SenseFrontissaTest(unittest.TestCase):
    """El braç prudent: sense dos punts d'eix no hi ha frontissa, i el bucle no es toca."""

    def test_un_bucle_que_no_toca_leix_no_es_gira(self):
        from fhort.patterns.engine.aama_reader import _bucle_des_del_doblec
        from fhort.patterns.engine.geometry import FoldData, PointKind
        fold = FoldData(0.0, 0.0, 0.0, 10.0, materialitzat=False, costat=1)
        punts = tuple(PointData(x=x, y=y, kind=PointKind.TURN)
                      for x, y in [(5, 1), (9, 1), (9, 9), (5, 9)])
        self.assertIs(_bucle_des_del_doblec(punts, fold), punts)

    def test_un_bucle_amb_un_sol_punt_a_leix_no_es_gira(self):
        from fhort.patterns.engine.aama_reader import _bucle_des_del_doblec
        from fhort.patterns.engine.geometry import FoldData, PointKind
        fold = FoldData(0.0, 0.0, 0.0, 10.0, materialitzat=False, costat=1)
        punts = tuple(PointData(x=x, y=y, kind=PointKind.TURN)
                      for x, y in [(0, 5), (9, 1), (9, 9)])
        self.assertIs(_bucle_des_del_doblec(punts, fold), punts)


if __name__ == '__main__':
    unittest.main()
