"""SET-2/T6a — LA CLAU DE PAYLOAD I L'ORDRE DE LA TAULA INCORPOREN LA PEÇA.

`clau_mesura` és l'ÚNIC lloc que sap com s'aplana la identitat d'una mesura per servir-la com
a clau d'un objecte JSON (`grading_views.cells` i `models_app.deltes` la publiquen així). Amb
dues peces vives, tres trams deixen de ser una clau: la mesura del pit del top i la del pit
de la calceta hi cauen a sobre i l'última llegida guanya.

DUES PROVES DE FORMA I UNA D'ORDRE, i cadascuna vigila una cosa distinta:

  · La FORMA de la clau: quatre trams sempre, el buit inclòs. Si algun dia s'ometés el tram
    buit, `'12|exterior||'` i `'12|exterior|'` serien la mateixa mesura escrita de dues
    maneres i qualsevol `Set` diria que són distintes.
  · La INJECTIVITAT: dues peces del mateix POM, mateixa capa i mateixa instància, han de
    donar claus DIFERENTS. És el pin literal del dany.
  · L'ORDRE: `clau_ordre_taula` ha de ser TOTAL i ha d'agrupar per peça. Amb la clau curta,
    dues peces del mateix POM empataven a tots els trams i el desempat el decidia el pla de
    Postgres — mateixos POMs, mateixos ids, un altre ordre a cada consulta.

⚠️ La peça va a llocs DIFERENTS a les dues funcions, i no és una incoherència:
   · a `clau_mesura` va l'ÚLTIMA, perquè la clau és identitat i no jerarquia (i afegir al
     final és el que menys demana al consumidor: el front la tracta com a token opac);
   · a `clau_ordre_taula` va la PRIMERA, perquè allà sí que mana la jerarquia — la llei de T9
     és «la prenda a fora, la secció a dins», i les files d'una peça van juntes.
   Aquest fitxer fixa les dues coses precisament perquè ningú les «unifiqui» sense llegir-ho.
"""
from django.test import SimpleTestCase

from fhort.pom.identitat import SEPARADOR, clau_mesura


class _PomFals:
    """El mínim que `clau_ordre_taula` llegeix. Sense BD: la funció és pura."""

    def __init__(self, display_order=10, pom_code='CH', pk=7):
        self.display_order = display_order
        self.pom_code = pom_code
        self.id = pk


class FormaDeLaClauTest(SimpleTestCase):

    def test_quatre_trams_sempre_i_el_buit_hi_es(self):
        self.assertEqual(clau_mesura(12, 'exterior', '', ''), '12|exterior||')
        self.assertEqual(clau_mesura(12), '12|exterior||')
        self.assertEqual(clau_mesura(12, 'folre', 'dreta', '02'), '12|folre|dreta|02')
        self.assertEqual(clau_mesura(12).count(SEPARADOR), 3)

    def test_els_None_no_escriuen_mai_el_text_None(self):
        """Un `values()` sobre una taula, o un objecte a mig construir, hi poden arribar amb
        `None`. Una clau amb «None» a dins és un error mut que només es veu a la pantalla."""
        self.assertEqual(clau_mesura(12, None, None, None), '12|exterior||')

    def test_dues_peces_del_mateix_POM_NO_col·lapsen(self):
        """EL PIN DEL DANY. Mateix POM, mateixa capa, mateixa instància, peces distintes."""
        mare = clau_mesura(12, 'exterior', '', '')
        segona = clau_mesura(12, 'exterior', '', '02')
        self.assertNotEqual(mare, segona)
        self.assertEqual(len({mare, segona}), 2)

    def test_la_mare_segueix_escrivint_la_clau_de_sempre_amb_un_tram_mes(self):
        """Inèrcia: qui no sap de peces (una vora d'escriptura) escriu la de la mare."""
        self.assertTrue(clau_mesura(12, 'folre', 'dreta').endswith(SEPARADOR))
        self.assertEqual(clau_mesura(12, 'folre', 'dreta'),
                         clau_mesura(12, 'folre', 'dreta', ''))


class OrdreDeLaTaulaTest(SimpleTestCase):

    def _ordre(self, **kw):
        from fhort.pom.grading_views import clau_ordre_taula
        return clau_ordre_taula(_PomFals(**kw.pop('pom', {})), **kw)

    def test_la_clau_dordre_es_TOTAL_entre_dues_peces(self):
        """Sense el garment, aquests dos empataven a tots els trams i desempatava Postgres."""
        mare = self._ordre(capa='exterior', instancia='', garment='')
        segona = self._ordre(capa='exterior', instancia='', garment='02')
        self.assertNotEqual(mare, segona)

    def test_la_mare_va_PRIMER(self):
        mare = self._ordre(capa='exterior', instancia='', garment='')
        segona = self._ordre(capa='exterior', instancia='', garment='02')
        self.assertLess(mare, segona)

    def test_les_files_duna_peca_van_JUNTES_i_no_intercalades(self):
        """La llei de T9: la prenda és l'eix de FORA. Un POM d'ordre alt de la mare va
        igualment abans que un POM d'ordre baix de la segona peça."""
        mare_ordre_alt = self._ordre(pom={'display_order': 99, 'pom_code': 'ZZ', 'pk': 1},
                                     capa='exterior', instancia='', garment='')
        segona_ordre_baix = self._ordre(pom={'display_order': 1, 'pom_code': 'AA', 'pk': 2},
                                        capa='exterior', instancia='', garment='02')
        self.assertLess(mare_ordre_alt, segona_ordre_baix)

    def test_dins_duna_peca_lordre_de_sempre_no_es_mou(self):
        """CAS DE CONTROL: amb una sola peça —el 100% del corpus d'avui— l'ordre relatiu és
        exactament el d'abans de T6a: catàleg, després capa, després instància."""
        pit_ext = self._ordre(pom={'display_order': 1, 'pom_code': 'CH', 'pk': 1},
                              capa='exterior', instancia='', garment='')
        pit_folre = self._ordre(pom={'display_order': 1, 'pom_code': 'CH', 'pk': 1},
                                capa='folre', instancia='', garment='')
        maniga = self._ordre(pom={'display_order': 2, 'pom_code': 'SL', 'pk': 2},
                             capa='exterior', instancia='', garment='')
        self.assertLess(pit_ext, pit_folre)      # l'exterior abans que el folre
        self.assertLess(pit_folre, maniga)       # i el POM 1 sencer abans que el POM 2
