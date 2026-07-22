"""Porta única d'escriptura del run del model (llei S24b).

`create-wizard` i `update-step2` comparteixen `_resolve_garment_def`: tancar-la allà cobreix
la creació I l'edició. Aquests tests cobreixen el camí HTTP real, no el helper pur (això ja
ho fa `test_run_del_model.py`).
"""
from fhort.models_app.tests_sembra_grading import _BaseSembraTest


class PortaRunModelTest(_BaseSembraTest):
    """El run que arriba per l'API mai es desa cru."""

    PREFIX = 'S24B'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        # Sistema ample, com l'ALPHA_EU_W del cas real: permet apendar per sota de la base.
        self.ss = self._size_system('ALPHA', talles=('XXS', 'XS', 'S', 'M', 'L'))
        self.model = self._model(
            garment_type_item=self.item, garment_type=self.item.garment_type,
            size_system=self.ss, size_run_model='XS·S·L', base_size_label='S',
        )

    def test_cas_166_apendar_per_sota_de_la_base_es_reordena(self):
        """El cas real reproduït a la diagnosi: l'usuari afegeix XXS i M al final i abans es
        desava 'XS·S·L·XXS·M'. Ara el SizeSystem hi imposa l'ordre."""
        resp = self._step2(self.model, {'size_run': 'XS·S·L·XXS·M'})
        self.assertEqual(resp.status_code, 200)
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'XXS·XS·S·M·L')

    def test_run_no_contigu_es_conserva_amb_el_forat(self):
        """Llei S24b: un run no contigu és LEGÍTIM. Ni es bloqueja ni se li afegeix la M."""
        resp = self._step2(self.model, {'size_run': 'L·XS·S'})
        self.assertEqual(resp.status_code, 200)
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'XS·S·L')

    def test_etiqueta_fora_del_sistema_es_400_amb_llista(self):
        resp = self._step2(self.model, {'size_run': 'XS·S·5XL'})
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['codi'], 'talles_desconegudes')
        self.assertEqual(resp.data['etiquetes_desconegudes'], ['5XL'])
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'XS·S·L')  # intacte

    def test_separador_punt_i_coma_tolerat(self):
        resp = self._step2(self.model, {'size_run': 'L;XXS;S'})
        self.assertEqual(resp.status_code, 200)
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'XXS·S·L')

    def test_duplicats_es_col_lapsen(self):
        resp = self._step2(self.model, {'size_run': 'S·XS·S·M'})
        self.assertEqual(resp.status_code, 200)
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'XS·S·M')

    def test_ordena_contra_el_sistema_NOU_quan_el_patch_el_canvia(self):
        """El mateix PATCH pot moure el size_system: el run s'ordena contra el que queda,
        no contra el que hi havia."""
        ss2 = self._size_system('INVERS', talles=('L', 'M', 'S'))
        resp = self._step2(self.model, {'size_system_id': ss2.id, 'size_run': 'S·M·L'})
        self.assertEqual(resp.status_code, 200)
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_system_id, ss2.id)
        self.assertEqual(self.model.size_run_model, 'L·M·S')

    def test_patch_sense_size_system_ordena_contra_el_del_model(self):
        """Camí d'edició: el payload porta run però no sistema → mana el que ja té el model.
        És per això que `_resolve_garment_def` rep el `model`."""
        resp = self._step2(self.model, {'size_run': 'M·XXS'})
        self.assertEqual(resp.status_code, 200)
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'XXS·M')
