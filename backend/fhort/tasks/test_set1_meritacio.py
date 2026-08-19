"""SET-1 · A3 — meritació de CONJUNT: **SET = 1 mèrit** (decisió 2 del sprint SET, 27/07).

Convenció del repo: fitxer `test*.py` dins de l'app, executat amb
`python manage.py test fhort.tasks` (el projecte NO fa servir pytest).

El que defensen aquests tests és el punt exacte on la diagnosi (§A3) diu que hi ha una trampa:
tocar només el guard de runtime deixa que `reconcile_consumption` re-meriti les germanes, i el
resultat és set=3 amb un retard. Per això els dos punts es proven junts:

F1.4 · D-10 (05/08/2026) — el GALLET ha canviat, la LLEI no. La meritació ja no es dispara amb
la primera `→InProgress` (obrir una porta no factura) sinó amb la primera ESCRIPTURA
(`services_batec.batec_escriptura`). Aquests tests protegeixen «SET = 1 mèrit», que segueix sent
exactament igual de cert; el que s'ha actualitzat és per on s'hi entra. El test que fixa el gallet
nou —i el negatiu «obrir no merita»— viu a `test_meritacio_batec.py`.

  1. Un conjunt de 3 parts, primera ESCRIPTURA → UN `ConsumptionRecord` ancorat al SET
     (amb `code_snapshot` = `codi_base`, no el codi intern d'una peça) i CAP als models.
  2. Les tres germanes queden estampades amb `consumption_started_at` — que és exactament el
     que treu les peces del criteri de forat del reconcile.
  3. `reconcile_consumption` no re-merita: ni el set (ja marcat) ni les peces (marcades).
  4. Arrencar una SEGONA peça del mateix conjunt no crea cap albarà nou.
"""
import datetime
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import ConsumptionRecord, GarmentSet, Model
from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, ModelTask, TaskType
from fhort.tasks.services_batec import batec_escriptura


class MeritacioConjuntTest(TenantTestCase):
    """Un conjunt merita UNA vegada, i cap dels dos punts (runtime / reconcile) el duplica."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        self.user = get_user_model().objects.create(username='tecset')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CLI', nom='Client de prova')
        GarmentType.objects.create(codi_client='GTS', nom_client='Família', grup='TOPS')
        self.tt = TaskType.objects.create(code='task_set', name='Task Set', fase='Dev. tècnic')

        self.gs = GarmentSet.objects.create(codi_base='TST-SS26-0001', nom_comercial='Bikini',
                                            num_pieces=3)
        self.peces = [
            Model.objects.create(
                codi_intern=f'TST-SS26-0001-{i:02d}', codi_tenant='TST', any=2026,
                temporada='SS', sequencial=1, customer=self.customer,
                garment_set=self.gs, piece_number=i, nom_prenda='Bikini')
            for i in (1, 2, 3)
        ]

    def _tasca(self, model):
        return ModelTask.objects.create(model=model, task_type=self.tt, order=0,
                                        status='Pending', assignee=self.prof)

    def _treballa(self, model):
        """El gest que merita, a F1.4: escriure. El batec obre la tasca si cal (batec fort)."""
        self._tasca(model)
        return batec_escriptura(model, self.tt.code, self.prof)

    def test_un_sol_albara_ancorat_al_set(self):
        self._treballa(self.peces[0])

        self.assertEqual(ConsumptionRecord.objects.count(), 1)
        rec = ConsumptionRecord.objects.get()
        self.assertEqual(rec.garment_set_id, self.gs.id)
        self.assertIsNone(rec.model_id)
        # L'albarà el veu el client: hi ha de constar el codi COMERCIAL, no el d'una peça.
        self.assertEqual(rec.code_snapshot, self.gs.codi_base)
        self.assertEqual(rec.name_snapshot, 'Bikini')

        self.gs.refresh_from_db()
        self.assertIsNotNone(self.gs.consumption_started_at)

    def test_totes_les_germanes_queden_estampades(self):
        """El que treu les peces 02/03 del criteri de forat del reconcile."""
        self._treballa(self.peces[0])
        for p in self.peces:
            p.refresh_from_db()
            self.assertIsNotNone(p.consumption_started_at, f'{p.codi_intern} sense marca')
        # Cap albarà per-model: la unitat que merita és el conjunt.
        self.assertEqual(ConsumptionRecord.objects.filter(model__isnull=False).count(), 0)

    def test_segona_peca_no_merita_de_nou(self):
        self._treballa(self.peces[0])
        self._treballa(self.peces[1])
        self.assertEqual(ConsumptionRecord.objects.count(), 1)

    def test_reconcile_no_re_merita(self):
        """LA TRAMPA de §A3: el reconcile no pot tornar a meritar ni el set ni les germanes."""
        self._treballa(self.peces[0])
        self.assertEqual(ConsumptionRecord.objects.count(), 1)

        out = StringIO()
        call_command('reconcile_consumption', tenant=self.tenant.schema_name, stdout=out)
        self.assertEqual(ConsumptionRecord.objects.count(), 1)

    def test_reconcile_merita_un_conjunt_orfe_un_sol_cop(self):
        """Forat heretat: activitat a les peces i cap marca enlloc → UN albarà, al SET."""
        self._treballa(self.peces[0])
        # Simulem l'estat pre-sprint: activitat real, però cap marca ni albarà.
        ConsumptionRecord.objects.all().delete()
        GarmentSet.objects.filter(pk=self.gs.pk).update(consumption_started_at=None)
        Model.objects.filter(garment_set=self.gs).update(consumption_started_at=None)

        out = StringIO()
        call_command('reconcile_consumption', tenant=self.tenant.schema_name, stdout=out)

        self.assertEqual(ConsumptionRecord.objects.count(), 1)
        rec = ConsumptionRecord.objects.get()
        self.assertEqual(rec.garment_set_id, self.gs.id)
        for p in self.peces:
            p.refresh_from_db()
            self.assertIsNotNone(p.consumption_started_at)

        # I una segona passada no n'afegeix cap.
        call_command('reconcile_consumption', tenant=self.tenant.schema_name, stdout=StringIO())
        self.assertEqual(ConsumptionRecord.objects.count(), 1)


class MeritacioModelSolTest(TenantTestCase):
    """El camí de sempre (~90% dels models) no canvia: albarà ancorat al MODEL."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        self.user = get_user_model().objects.create(username='tecsol')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CL2', nom='Client')
        self.tt = TaskType.objects.create(code='task_sol', name='Task Sol', fase='Dev. tècnic')
        self.model = Model.objects.create(
            codi_intern='TST-SS26-0009', codi_tenant='TST', any=2026, temporada='SS',
            sequencial=9, customer=self.customer, nom_prenda='Samarreta')

    def test_model_sol_merita_com_sempre(self):
        ModelTask.objects.create(model=self.model, task_type=self.tt, order=0,
                                 status='Pending', assignee=self.prof)
        batec_escriptura(self.model, self.tt.code, self.prof)
        rec = ConsumptionRecord.objects.get()
        self.assertEqual(rec.model_id, self.model.id)
        self.assertIsNone(rec.garment_set_id)
        self.assertEqual(rec.code_snapshot, 'TST-SS26-0009')
