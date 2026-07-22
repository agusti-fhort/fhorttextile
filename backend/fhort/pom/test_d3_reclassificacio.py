"""D3 · re-classificació amb valors nets — QUÈ desinfla el bucket `conflicte` i què NO.

El brief demanava verificar si el bucket `conflicte` (F/FF/I4) es desinflava un cop
normalitzats els valors, per si la divergència era soroll de coma flotant.

**RESULTAT DE LA VERIFICACIÓ: la hipòtesi del soroll queda REFUTADA.** El soroll de float
no arribava mai al classificador. `detect_grading` ja arrodonia cada delta a 2 decimals
abans de classificar, i el soroll d'`openpyxl` (~1e-15) no creua mai una frontera de 2
decimals. Comprovat A/B sobre el càlcul vell i el nou:

    soroll openpyxl (1e-15)    vell=0.25   nou=0.25
    soroll acumulat (1e-12)    vell=0.25   nou=0.25
    frontera de 2 decimals     vell=0.25   nou=0.25
    cadena amb coma "12,35"    vell=ValueError   nou=0.25

L'ÚNIC camí que la normalització repara de debò a la classificació és l'últim: valors que
arriben com a CADENA amb coma decimal (sortida d'IA, enganxat d'un Excel europeu). Abans
`float("12,35")` petava dins de `detect_grading`, l'excepció se la menjava el `try` del
cridant i el POM es quedava sense forma detectada → divergència de catàleg fabricada.

Conclusió operativa: **els conflictes que hi ha són conflictes REALS de catàleg.** No es
resolen amb precisió; s'han de resoldre amb una decisió humana visible (proposta de
promoció). Els tests de soroll d'aquest fitxer són, doncs, guardes de regressió —
documenten que el comportament NO canvia—, no la demostració d'una desinflada.

⚠️ PENDENT DE CATÀLEG (Agus/Montse, fora d'abast d'aquest sprint): l'àlies I4→SL i el seu
xoc amb I→SL. És una decisió humana de catàleg, no un problema de precisió: cap
normalització el desinflarà. Ha de sortir com a proposta visible.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase

from fhort.pom.grading_utils import (
    _spec_from_detection, classifica_fitxa_vs_contenidor, detect_grading,
)

RUN = ['XS', 'S', 'M', 'L']
BASE = 'S'

#: La MATEIXA taula, escrita net i escrita tal com la torna `openpyxl`.
NET = {'XS': 12.10, 'S': 12.35, 'M': 12.60, 'L': 12.85}
BRUT = {'XS': 12.099999999999998, 'S': 12.350000000000001,
        'M': 12.599999999999998, 'L': 12.850000000000001}


def _spec(valors, pom_id=1):
    pm = SimpleNamespace(id=pom_id, codi_client='D1')
    res = detect_grading(valors, RUN, BASE)
    return _spec_from_detection(pm, res, base_def_id=None, run_ordenat=RUN)


def _contenidor(*regles):
    """Stub: `classifica_fitxa_vs_contenidor` només crida `container.regles.all()`."""
    return SimpleNamespace(regles=SimpleNamespace(all=lambda: list(regles)))


def _regla(pom_id, **kw):
    base = dict(id=100 + pom_id, pom_id=pom_id, pom=None, talla_base_id=None,
                logica='LINEAR', increment=0, valors_step=None, increment_base=None,
                increment_break=None, talla_break_label=None, talla_break_pos=None)
    base.update(kw)
    return SimpleNamespace(**base)


class SorollDeFloatTest(SimpleTestCase):
    """GUARDA DE REGRESSIÓ, no demostració: aquests casos ja passaven abans (v. capçalera)."""

    def test_la_taula_bruta_te_la_mateixa_forma_que_la_neta(self):
        self.assertEqual(_spec(BRUT)['logica'], _spec(NET)['logica'])
        self.assertEqual(_spec(BRUT)['increment_base'], _spec(NET)['increment_base'])

    def test_soroll_i_net_cauen_al_MATEIX_bucket(self):
        cont = _contenidor(_regla(1, increment_base=0.25))
        for etiqueta, valors in (('net', NET), ('brut', BRUT)):
            cls = classifica_fitxa_vs_contenidor([_spec(valors)], cont)
            with self.subTest(valors=etiqueta):
                self.assertEqual(len(cls['sembra']), 1, 'hauria d\'heretar del contenidor')
                self.assertEqual(cls['conflicte'], [])
                self.assertEqual(cls['amplia'], [])

class CadenaAmbComaTest(SimpleTestCase):
    """L'ÚNIC fals conflicte que la normalització desinfla de debò.

    Amb dents: sota el codi anterior `float("12,35")` petava dins de `detect_grading`, el
    POM es quedava sense forma i el sistema el declarava divergent del catàleg.
    """

    AMB_COMA = {'XS': '12,10', 'S': '12,35', 'M': '12,60', 'L': '12,85'}

    def test_valors_amb_coma_hereten_del_contenidor_com_els_numerics(self):
        cont = _contenidor(_regla(1, increment_base=0.25))
        cls = classifica_fitxa_vs_contenidor([_spec(self.AMB_COMA)], cont)
        self.assertEqual(len(cls['sembra']), 1)
        self.assertEqual(cls['conflicte'], [])

    def test_la_forma_detectada_es_identica_a_la_dels_numerics(self):
        self.assertEqual(_spec(self.AMB_COMA)['logica'], _spec(NET)['logica'])
        self.assertEqual(_spec(self.AMB_COMA)['increment_base'],
                         _spec(NET)['increment_base'])


class ConflicteRealTest(SimpleTestCase):

    def test_el_conflicte_REAL_no_es_desinfla(self):
        """La normalització no amaga divergències: un increment de debò diferent segueix
        sent conflicte, i és el que ha d'arribar a la proposta de promoció."""
        cont = _contenidor(_regla(1, increment_base=0.50))
        cls = classifica_fitxa_vs_contenidor([_spec(NET)], cont)
        self.assertEqual(len(cls['conflicte']), 1)
        self.assertEqual(cls['sembra'], [])

    def test_pom_absent_del_contenidor_segueix_a_amplia(self):
        cls = classifica_fitxa_vs_contenidor([_spec(NET, pom_id=9)], _contenidor())
        self.assertEqual(len(cls['amplia']), 1)
        self.assertEqual(cls['conflicte'], [])
