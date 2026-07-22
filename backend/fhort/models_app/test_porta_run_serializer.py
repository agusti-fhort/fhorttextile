"""Via 7 del cens: el CRUD genèric del `ModelViewSet` (llei S24b).

`POST/PUT/PATCH /api/v1/models/[<pk>/]` no passa per `_resolve_garment_def`: era l'única via
del cens que acceptava un run arbitrari sense cap guard, perquè `ModelDetailSerializer` té
`fields = '__all__'` i `size_run_model` no és read-only.
"""
from fhort.models_app.tests_sembra_grading import _BaseSembraTest


class PortaRunSerializerTest(_BaseSembraTest):
    """Via 7 del cens: el CRUD genèric del `ModelViewSet`, que no passa per
    `_resolve_garment_def` i acceptava qualsevol run sense guard."""

    PREFIX = 'S24BS'

    def setUp(self):
        super().setUp()
        self.item = self._item()
        self.ss = self._size_system('ALPHA', talles=('XXS', 'XS', 'S', 'M', 'L'))
        self.model = self._model(
            garment_type_item=self.item, garment_type=self.item.garment_type,
            size_system=self.ss, size_run_model='XS·S·L', base_size_label='S',
        )

    def _ser(self, data):
        from fhort.models_app.serializers import ModelDetailSerializer
        return ModelDetailSerializer(self.model, data=data, partial=True)

    def test_run_desordenat_es_desa_ordenat(self):
        ser = self._ser({'size_run_model': 'L·XXS·S'})
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save()
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'XXS·S·L')

    def test_etiqueta_fora_del_sistema_no_valida(self):
        ser = self._ser({'size_run_model': 'XS·5XL'})
        self.assertFalse(ser.is_valid())
        self.assertIn('size_run_model', ser.errors)
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'XS·S·L')  # intacte

    def test_ordena_contra_el_sistema_del_mateix_payload(self):
        ss2 = self._size_system('INVERS', talles=('L', 'M', 'S'))
        ser = self._ser({'size_system': ss2.id, 'size_run_model': 'S·L·M'})
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save()
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'L·M·S')

    def test_payload_sense_run_no_toca_res(self):
        ser = self._ser({'nom_prenda': 'Nom nou'})
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save()
        self.model.refresh_from_db()
        self.assertEqual(self.model.size_run_model, 'XS·S·L')
