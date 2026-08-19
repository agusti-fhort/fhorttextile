"""F1.4 · D-10 — LA MERITACIÓ, AL SEU LLOC NOU.

El fet facturable era «algú ha obert una porta»: la primera `→InProgress` de qualsevol tasca
meritava el model, emetia l'event a `public` i reancorava el pla. Verificat al corpus: els 21
`ConsumptionRecord` del tenant tenien `merited_at == started_at` de la primera tasca. Tocar una
porta tres segons per error facturava.

Ara el fet facturable és **algú hi ha escrit**.

El test negatiu (`obrir una porta NO merita`) és el que dona sentit a tot això: si algun dia
torna a passar en verd, la decisió D-10 s'ha desfet sense que ningú se n'adoni.

Convenció del repo: `python manage.py test fhort.tasks.test_meritacio_batec` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, GarmentTypeItem, ModelTask, TaskType
from fhort.tasks.services_batec import SUP_MESURES, batec_escriptura
from fhort.tasks.services_c import transition_task


class MeritacioAlBatecTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TME'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='tecmerit')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CME', nom='Client de prova')
        gt = GarmentType.objects.create(codi_client='GTM', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_m', name='Item M')
        self.tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.Model = Model
        self.model = Model.objects.create(
            codi_intern='TME-SS26-0001', codi_tenant='TME', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')
        self.task = ModelTask.objects.create(model=self.model, task_type=self.tt, order=0,
                                             status='Pending', origen='prevista')

    def _n_records(self):
        from fhort.models_app.models import ConsumptionRecord
        return ConsumptionRecord.objects.filter(model=self.model).count()

    def _meritat(self):
        return self.Model.objects.get(pk=self.model.pk).consumption_started_at

    # ── EL TEST NEGATIU: obrir una porta no factura ──────────────────────────
    def test_obrir_la_porta_sense_escriure_NO_merita(self):
        """«Tocar una porta 3 s per error factura» era el cas real de D-10. Ha de morir aquí."""
        transition_task(self.task, 'InProgress', self.prof)
        self.assertEqual(self._n_records(), 0)
        self.assertIsNone(self._meritat())

    def test_obrir_i_tancar_sense_escriure_tampoc_merita(self):
        transition_task(self.task, 'InProgress', self.prof)
        transition_task(self.task, 'Done', self.prof)
        self.assertEqual(self._n_records(), 0)
        self.assertIsNone(self._meritat())

    # ── EL POSITIU: la primera escriptura factura, un sol cop ────────────────
    def test_la_primera_escriptura_merita(self):
        batec_escriptura(self.model, SUP_MESURES, self.prof)
        self.assertEqual(self._n_records(), 1)
        self.assertIsNotNone(self._meritat())

    def test_la_segona_escriptura_NO_torna_a_meritar(self):
        batec_escriptura(self.model, SUP_MESURES, self.prof)
        primer = self._meritat()
        batec_escriptura(self.model, SUP_MESURES, self.prof)
        batec_escriptura(self.model, SUP_MESURES, self.prof)
        self.assertEqual(self._n_records(), 1)
        self.assertEqual(self._meritat(), primer)

    def test_merita_igual_si_la_tasca_ja_estava_oberta(self):
        """Obrir la porta no merita, però escriure-hi després SÍ: el gallet és l'escriptura,
        no la transició que la precedeix."""
        transition_task(self.task, 'InProgress', self.prof)
        self.assertEqual(self._n_records(), 0)
        batec_escriptura(self.model, SUP_MESURES, self.prof)
        self.assertEqual(self._n_records(), 1)

    def test_escriure_sense_tasca_no_merita(self):
        """Sense tasca no hi ha batec, i sense batec no hi ha meritació."""
        ModelTask.objects.filter(pk=self.task.pk).delete()
        batec_escriptura(self.model, SUP_MESURES, self.prof)
        self.assertEqual(self._n_records(), 0)

    # ── El que NO s'ha mogut ─────────────────────────────────────────────────
    def test_la_fase_segueix_passant_a_Dev_en_obrir(self):
        """MÓN TÈCNIC (sagrat): el pas de fase es queda a `transition_task`. Només ha marxat la
        facturació."""
        self.assertEqual(self.Model.objects.get(pk=self.model.pk).fase_actual, 'Pending')
        transition_task(self.task, 'InProgress', self.prof)
        self.assertEqual(self.Model.objects.get(pk=self.model.pk).fase_actual, 'Dev')
