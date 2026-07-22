"""Test del helper `run_del_model` (llei S24b: l'ordre i la distància els mana el SizeSystem).

Pur, sense BD: el helper rep el run del sistema com a llista ja ordenada.
Germà de `test_run_del_document.py`.
"""
from django.test import SimpleTestCase

from fhort.pom.grading_utils import run_del_model

# Sistema de referència: ALPHA_EU_W del cas real (8 talles).
ALPHA_EU_W = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']


class RunDelModelTest(SimpleTestCase):

    def test_run_ja_ordenat_no_es_toca(self):
        run, desconegudes = run_del_model(['XS', 'S', 'M', 'L'], ALPHA_EU_W)
        self.assertEqual(run, ['XS', 'S', 'M', 'L'])
        self.assertEqual(desconegudes, [])

    def test_cas_166_run_apendat_es_reordena(self):
        """El cas real: l'usuari amplia el run del model 166 i les talles noves queden al
        final. És el run que feia graduar la XXS amb el signe invertit."""
        run, desconegudes = run_del_model(['XS', 'S', 'L', 'XXS', 'M'], ALPHA_EU_W)
        self.assertEqual(run, ['XXS', 'XS', 'S', 'M', 'L'])
        self.assertEqual(desconegudes, [])

    def test_run_no_contigu_es_LEGITIM_i_conserva_el_forat(self):
        """Llei S24b: el run del model és un subconjunt potencialment NO CONTIGU (un client
        que no fabrica la M). Mai es bloqueja i mai s'hi afegeixen talles: el forat es
        conserva tal qual, i és el MOTOR qui hi compta la distància real."""
        run, desconegudes = run_del_model(['XS', 'S', 'L'], ALPHA_EU_W)
        self.assertEqual(run, ['XS', 'S', 'L'])
        self.assertEqual(desconegudes, [])

    def test_no_contigu_i_desordenat_alhora(self):
        run, _ = run_del_model(['L', 'XXS', 'S'], ALPHA_EU_W)
        self.assertEqual(run, ['XXS', 'S', 'L'])

    def test_etiqueta_fora_del_sistema_es_reporta_i_no_entra(self):
        """Coherent amb el check (d) de la S24: una talla que el sistema NO coneix és error
        real, no una talla que falta. Les que sí coneix segueixen entrant al run."""
        run, desconegudes = run_del_model(['XS', 'S', '5XL'], ALPHA_EU_W)
        self.assertEqual(run, ['XS', 'S'])
        self.assertEqual(desconegudes, ['5XL'])

    def test_duplicats_es_col_lapsen(self):
        """El toggle de chips del wizard pot enviar duplicats; el run persistit no en té."""
        run, desconegudes = run_del_model(['S', 'XS', 'S', 'M', 'XS'], ALPHA_EU_W)
        self.assertEqual(run, ['XS', 'S', 'M'])
        self.assertEqual(desconegudes, [])

    def test_pont_canonic_xxl_vs_2xl(self):
        """Pont únic `canonical_size_label`: el model pot dir 2XL on el tenant diu XXL. El
        run torna SEMPRE amb l'etiqueta del TENANT, mai amb la forma canònica."""
        run, desconegudes = run_del_model(['L', '2XL', 'XL'], ALPHA_EU_W)
        self.assertEqual(run, ['L', 'XL', 'XXL'])
        self.assertEqual(desconegudes, [])

    def test_espais_i_buits_s_ignoren(self):
        run, desconegudes = run_del_model([' S ', '', None, 'XS'], ALPHA_EU_W)
        self.assertEqual(run, ['XS', 'S'])
        self.assertEqual(desconegudes, [])

    def test_sense_sistema_degrada_amb_gracia(self):
        """Camí legacy (tech_sheet crea models sense size_system): sense res contra què
        ordenar, es conserva l'ordre d'entrada. Mai petar un import que ja funcionava."""
        run, desconegudes = run_del_model(['L', 'XXS', 'S'], None)
        self.assertEqual(run, ['L', 'XXS', 'S'])
        self.assertEqual(desconegudes, [])

    def test_sistema_sense_talles_es_com_no_tenir_sistema(self):
        run, desconegudes = run_del_model(['L', 'S'], [])
        self.assertEqual(run, ['L', 'S'])
        self.assertEqual(desconegudes, [])

    def test_run_buit(self):
        self.assertEqual(run_del_model([], ALPHA_EU_W), ([], []))
        self.assertEqual(run_del_model(None, ALPHA_EU_W), ([], []))

    def test_totes_les_etiquetes_desconegudes(self):
        run, desconegudes = run_del_model(['P', 'G'], ALPHA_EU_W)
        self.assertEqual(run, [])
        self.assertEqual(desconegudes, ['P', 'G'])

    def test_run_dens_igual_al_sistema(self):
        run, desconegudes = run_del_model(list(reversed(ALPHA_EU_W)), ALPHA_EU_W)
        self.assertEqual(run, ALPHA_EU_W)
        self.assertEqual(desconegudes, [])
