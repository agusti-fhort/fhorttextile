"""N1 (2026-08-06 nit) — la deducció del tipus d'escala a partir de les etiquetes.

Els casos són els 30 runs REALS de staging (`fhort` + `los`), no exemples inventats: el que
aquesta suite fixa és que l'algorisme classifica el corpus que hi ha, i que els que no es
dedueixen sols siguin exactament els tres que no tenen cap senyal.
"""
from django.test import SimpleTestCase

from fhort.pom.size_labels import (BASE_UNIT_A_TIPUS, conflicte_tipus_escala,
                                   dedueix_tipus_escala)


class DedueixTipusEscalaTest(SimpleTestCase):

    def test_alpha_amb_x_repetides_i_amb_prefix_numeric(self):
        # Les dues escriptures de la mateixa talla (XXL i 2XL) han de comptar igual.
        self.assertEqual(dedueix_tipus_escala(['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']),
                         ('ALPHA', 'etiquetes'))
        self.assertEqual(dedueix_tipus_escala(['S', 'M', 'L', 'XL', '2XL', '6XL']),
                         ('ALPHA', 'etiquetes'))

    def test_la_M_solitaria_no_es_mesos(self):
        # 'M' és Medium. Només compta com a mesos amb dígit al davant.
        self.assertEqual(dedueix_tipus_escala(['S', 'M', 'L'])[0], 'ALPHA')

    def test_mesos_en_les_tres_escriptures_de_la_casa(self):
        for etiquetes in (['NB', '0M', '3M', '6M', '12M'],
                          ['0M-1M', '1M-3M', '3M-6M', '6M-9M', '9M-12M'],
                          ['00/01', '01/03', '03/06', '06/09', '09/12', '12/18', '18/24']):
            self.assertEqual(dedueix_tipus_escala(etiquetes), ('MESOS', 'etiquetes'), etiquetes)

    def test_edat_en_anys_es_MESOS(self):
        self.assertEqual(dedueix_tipus_escala(['6Y', '8Y', '10Y', '12Y']), ('MESOS', 'etiquetes'))
        self.assertEqual(
            dedueix_tipus_escala(['2', '3', '4', '5', '6', '7', '8', '9/10', '11/12', '13/14']),
            ('MESOS', 'etiquetes'))

    def test_el_pas_desempata_ALTURA_de_NUM(self):
        # Els dos són numèrics purs i es solapen en rang (48 vs 50). El que els separa és el
        # pas: l'alçada infantil EU va de 6 en 6, el numèric EU adult de 2 en 2.
        self.assertEqual(dedueix_tipus_escala(['50', '56', '62', '68', '74', '80', '86', '92']),
                         ('ALTURA', 'etiquetes'))
        self.assertEqual(dedueix_tipus_escala(['34', '36', '38', '40', '42', '44', '46', '48']),
                         ('NUM', 'etiquetes'))

    def test_un_run_amb_l_ordre_trencat_es_dedueix_igual(self):
        # `TODDLER_EU` té dues talles amb `ordre=1` i surt desordenat de la BD. El pas és una
        # propietat de l'ESCALA, no de com està desada: es llegeix ordenant els valors.
        self.assertEqual(dedueix_tipus_escala(['92', '86', '98', '104', '110', '116']),
                         ('ALTURA', 'etiquetes'))

    def test_l_etiqueta_mana_sobre_el_base_unit_quan_es_contradiuen(self):
        # El cas real: `TODDLER_EU` diu AGE_YEARS i porta alçades en cm.
        self.assertEqual(dedueix_tipus_escala(['92', '86', '98', '104', '110', '116'],
                                              'AGE_YEARS'),
                         ('ALTURA', 'etiquetes'))
        self.assertTrue(conflicte_tipus_escala(['86', '92', '98', '104'], 'AGE_YEARS'))
        self.assertFalse(conflicte_tipus_escala(['86', '92', '98', '104'], 'CM_HEIGHT'))

    def test_el_base_unit_es_la_xarxa_quan_les_etiquetes_callen(self):
        # Run sense talles: no hi ha senyal a les etiquetes, i el camp existent decideix.
        self.assertEqual(dedueix_tipus_escala([], 'ALPHA'), ('ALPHA', 'base_unit'))
        self.assertEqual(dedueix_tipus_escala([], 'NUMERIC_US'), ('NUM', 'base_unit'))
        # I el cas genuïnament indecidible per etiquetes: 8·10·12·14·16 pot ser edat en anys,
        # numèric US o numèric infantil. Sense `base_unit` no es dedueix.
        self.assertEqual(dedueix_tipus_escala(['8', '10', '12', '14', '16']), ('', ''))
        self.assertEqual(dedueix_tipus_escala(['8', '10', '12', '14', '16'], 'AGE_YEARS'),
                         ('MESOS', 'base_unit'))

    def test_sense_cap_senyal_es_queda_BUIT_i_no_s_inventa_res(self):
        # Els 3 runs de staging que no es dedueixen sols. Cap d'ells rep valor per defecte.
        self.assertEqual(dedueix_tipus_escala([], ''), ('', ''))
        self.assertEqual(dedueix_tipus_escala([], None), ('', ''))

    def test_el_mapa_de_base_unit_cobreix_els_6_choices_historics(self):
        historics = {'ALPHA', 'NUMERIC_EU', 'NUMERIC_US', 'CM_HEIGHT', 'MONTHS', 'AGE_YEARS'}
        self.assertEqual(set(BASE_UNIT_A_TIPUS), historics)
        self.assertEqual(set(BASE_UNIT_A_TIPUS.values()), {'ALPHA', 'NUM', 'ALTURA', 'MESOS'})
