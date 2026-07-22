"""Test del helper `run_del_document` (llei S24: referent de derivació = run del DOCUMENT).

Pur, sense BD: el helper rep el run del sistema com a llista ja ordenada.
"""
from django.test import SimpleTestCase

from fhort.pom.grading_utils import run_del_document

# Sistema de referència: ALPHA_EU_W del cas real (8 talles).
ALPHA_EU_W = ['XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', '3XL']


class RunDelDocumentTest(SimpleTestCase):

    def test_document_subconjunt_cas_meredith(self):
        """Doc XXS-L sobre un sistema de 8 talles: el referent és el DEL DOCUMENT (5), no el
        del sistema. És el cas que avui marca 26 files com a incompletes."""
        files = [{'XXS': 41, 'XS': 43, 'S': 46, 'M': 49, 'L': 52}]
        doc_run, desconegudes = run_del_document(files, ALPHA_EU_W)
        self.assertEqual(doc_run, ['XXS', 'XS', 'S', 'M', 'L'])
        self.assertEqual(desconegudes, [])

    def test_document_dens_igual_al_sistema(self):
        files = [{e: 1 for e in ALPHA_EU_W}]
        doc_run, desconegudes = run_del_document(files, ALPHA_EU_W)
        self.assertEqual(doc_run, ALPHA_EU_W)
        self.assertEqual(desconegudes, [])

    def test_ordre_el_mana_el_sistema_no_el_document(self):
        """El document pot portar les columnes desordenades; l'ordre del referent SEMPRE
        surt del sistema (si no, els deltes es calcularien entre veïns falsos)."""
        files = [{'L': 52, 'XXS': 41, 'S': 46}]
        doc_run, _ = run_del_document(files, ALPHA_EU_W)
        self.assertEqual(doc_run, ['XXS', 'S', 'L'])

    def test_etiqueta_desconeguda_es_reporta(self):
        """Check (d): una talla que el sistema NO coneix és error real, no una talla que
        falta. Les que sí coneix segueixen entrant al referent."""
        files = [{'XS': 43, 'S': 46, '5XL': 99}]
        doc_run, desconegudes = run_del_document(files, ALPHA_EU_W)
        self.assertEqual(doc_run, ['XS', 'S'])
        self.assertEqual(desconegudes, ['5XL'])

    def test_pont_canonic_xxl_vs_2xl(self):
        """El pont únic `canonical_size_label` salva XXL↔2XL; el referent torna SEMPRE
        l'etiqueta del TENANT, mai la del document."""
        doc_run, desconegudes = run_del_document([{'2XL': 60, 'S': 46}], ALPHA_EU_W)
        self.assertEqual(doc_run, ['S', 'XXL'])
        self.assertEqual(desconegudes, [])

    def test_files_multiples_unio_de_columnes(self):
        """El referent és la UNIÓ de les columnes de totes les files: si una fila no porta
        una talla que una altra sí, això és un FORAT (el detecta el guard), no una talla
        absent del document."""
        files = [{'XS': 1, 'S': 2}, {'S': 3, 'M': 4}]
        doc_run, _ = run_del_document(files, ALPHA_EU_W)
        self.assertEqual(doc_run, ['XS', 'S', 'M'])

    def test_clau_amb_valor_none_es_columna_present(self):
        """Una columna present amb el valor buit segueix sent columna del document: el
        forat el denuncia el guard (missing_sizes), no el referent."""
        doc_run, _ = run_del_document([{'XS': 1, 'S': None, 'M': 3}], ALPHA_EU_W)
        self.assertEqual(doc_run, ['XS', 'S', 'M'])

    def test_sense_sistema_cami_crear(self):
        """Camí CREAR: encara no hi ha sistema. S'accepta el document tal com ve, en ordre
        de primera aparició, i no hi ha res de desconegut."""
        doc_run, desconegudes = run_del_document([{'T1': 1, 'T2': 2}], [])
        self.assertEqual(doc_run, ['T1', 'T2'])
        self.assertEqual(desconegudes, [])

    def test_document_buit(self):
        self.assertEqual(run_del_document([], ALPHA_EU_W), ([], []))
        self.assertEqual(run_del_document(None, ALPHA_EU_W), ([], []))
