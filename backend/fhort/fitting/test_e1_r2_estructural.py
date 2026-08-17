"""E1/B4 · R2 ÉS ESTRUCTURAL — cap camí VIU decideix ni propaga des d'una talla no-base.

R2 del brief: els ajustos només s'accepten a la TALLA BASE, i l'acceptació a base es propaga a
la resta. Fins avui això era una CONVENCIÓ que la pantalla podia trencar en un clic: la columna
«Fit actual» de l'Escalat cridava `escalat/ajustar-talla/`, que acceptava qualsevol talla del
run i hi propagava des d'allà.

Aquest banc no prova una funció: prova **què queda connectat**. És un cens executable, i
existeix perquè el cens d'ahir (una diagnosi) no impedeix que demà algú torni a endollar una
ruta. Els tres camins que la diagnosi E1 §5 va censar com a vius o jubilables:

  1. `escalat/ajustar-talla/`  → SENSE RUTA des d'E1/B4 (la vista viu per als bancs que la fan
                                 servir de vehicle: segell G6, guarda de rang, germanes C4,
                                 STEP, i el banc F1 del `garment`).
  2. `set-size-override/`      → sense ruta des de D5 (21/07).
  3. `piece-fitting-lines/`    → viu, i amb el guard partit d'E1/B1: prendre sí, DECIDIR no.

⚠️ AQUEST BANC ÉS UN GUARDIÀ DE FRONTERA, i per això mira `urls`, no `views`. Si algú torna a
declarar la ruta, els tests de la vista seguirien verds i només aquest cauria.
"""
from django.test import SimpleTestCase
from django.urls import NoReverseMatch, Resolver404, resolve, reverse

from fhort.fitting.services import (
    CAMPS_DE_DECISIO, escriptura_es_decisio, fitting_line_decisio_fora_de_base,
)

RUTES_JUBILADES = [
    '/api/v1/models/1/escalat/ajustar-talla/',
    '/api/v1/models/1/set-size-override/',
]


class CapRutaVivaDAjustPerTallaTest(SimpleTestCase):

    def test_les_rutes_jubilades_NO_resolen(self):
        for ruta in RUTES_JUBILADES:
            with self.subTest(ruta=ruta):
                with self.assertRaises(Resolver404):
                    resolve(ruta)

    def test_la_porta_de_la_PRESA_si_que_resol(self):
        """El contrapunt: sense això, el test de sobre passaria amb l'Escalat mort del tot."""
        self.assertEqual(reverse('escalat-presa', args=[1]),
                         '/api/v1/fitting/model/1/presa/')
        self.assertTrue(resolve('/api/v1/fitting/model/1/presa/'))

    def test_cap_nom_de_ruta_apunta_a_la_vista_jubilada(self):
        """Una ruta amb nom però sense path no existeix; una amb path i sense nom sí. Es miren
        les dues bandes perquè `reverse` sol no ho hauria vist."""
        for nom in ('escalat-ajustar-talla', 'set-size-override'):
            with self.subTest(nom=nom):
                with self.assertRaises(NoReverseMatch):
                    reverse(nom, args=[1])


class ElGuardDeDecisioSegueixSentElQueEsTest(SimpleTestCase):
    """La segona meitat de R2: la porta que SÍ viu no deixa decidir fora de la base.

    Predicats purs, sense BD: el que es vigila aquí és la LLEI, no la vista (que ja té el seu
    banc a `test_e1_guard_partit`). Si algú afegís `decisio` a la llista de camps de presa,
    aquest test cauria abans que cap altre.
    """

    def test_decisio_es_lunic_camp_que_compta_com_a_decisio(self):
        self.assertEqual(tuple(CAMPS_DE_DECISIO), ('decisio',))
        self.assertTrue(escriptura_es_decisio(['decisio']))
        self.assertTrue(escriptura_es_decisio(['valor_real', 'decisio']))
        self.assertFalse(escriptura_es_decisio(['valor_real', 'nota']))
        self.assertFalse(escriptura_es_decisio([]))
        self.assertFalse(escriptura_es_decisio(None))

    def test_el_predicat_de_rebuig_creua_les_dues_condicions(self):
        class _Fals:
            def __init__(self, base, talla):
                self.size_label = talla
                self.piece_fitting = type('PF', (), {
                    'model': type('M', (), {'base_size_label': base})()})()

        no_base, base = _Fals('M', 'L'), _Fals('M', 'M')
        self.assertTrue(fitting_line_decisio_fora_de_base(no_base, ['decisio']))
        self.assertFalse(fitting_line_decisio_fora_de_base(no_base, ['valor_real']))
        self.assertFalse(fitting_line_decisio_fora_de_base(base, ['decisio']))
