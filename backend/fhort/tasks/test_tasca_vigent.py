"""F1.0 · EL RESOLUTOR ÚNIC — `tasks/services_r.tasca_vigent`.

Aquest fitxer fixa el contracte del resolutor que substitueix els TRES criteris divergents
censats a `docs/diagnosis/DIAGNOSI_PREF1_CICLE_TASCA.md` §S-4. Dos d'aquells criteris tenien
l'ordre INVERTIT (`order_by('id')` contra `order_by('-id')`), i el dia que un model tingui dues
tasques del mateix tipus —que és exactament el que la RONDA de F1.1 crearà— triarien files
diferents.

El que es fixa aquí:
  1. Amb una sola tasca `prevista`, el resolutor la retorna (cap regressió del cas normal).
  2. Una tasca `ad_hoc` NO es confon amb la prevista mentre no hi hagi ronda (F1.0: la branca de
     ronda és stub i `_ronda_oberta` retorna None sempre).
  3. Regla 3: amb la prevista `Done` i cap altra, la retorna igualment (no inventa un None).
  4. Determinisme: el resolutor NO depèn de l'ordre d'inserció ni del `-id`.

Convenció del repo: `python manage.py test fhort.tasks.test_tasca_vigent` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, GarmentTypeItem, ModelTask, TaskType
from fhort.tasks.services_r import tasca_vigent


class TascaVigentTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TSV'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='tecvig')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CLV', nom='Client de prova')
        gt = GarmentType.objects.create(codi_client='GTV', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_v', name='Item V')
        self.tt_pom = TaskType.objects.create(code='pom_v', name='POM V', fase='Dev. tècnic')
        self.tt_altre = TaskType.objects.create(code='altre_v', name='Altre V', fase='Dev. tècnic')
        self.model = Model.objects.create(
            codi_intern='TSV-SS26-0001', codi_tenant='TSV', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item,
            nom_prenda='Peça')

    def _tasca(self, tt, status='Pending', origen='prevista'):
        return ModelTask.objects.create(model=self.model, task_type=tt, order=0,
                                        status=status, origen=origen)

    # ── El cas normal no es mou ──────────────────────────────────────────────
    def test_una_prevista_es_la_vigent(self):
        t = self._tasca(self.tt_pom)
        self.assertEqual(tasca_vigent(self.model, 'pom_v'), t)

    def test_sense_tasca_retorna_none(self):
        self.assertIsNone(tasca_vigent(self.model, 'pom_v'))

    def test_no_creua_task_types(self):
        self._tasca(self.tt_altre)
        self.assertIsNone(tasca_vigent(self.model, 'pom_v'))

    # ── L'ad_hoc no es confon amb la prevista (F1.0: encara no hi ha ronda) ──
    def test_ad_hoc_sense_ronda_no_es_vigent(self):
        """La constraint `uniq_prevista_model_tasktype` és PARCIAL: un `ad_hoc` del mateix tipus
        pot conviure amb la prevista. Sense ronda oberta, la vigent és la prevista i prou."""
        prevista = self._tasca(self.tt_pom)
        self._tasca(self.tt_pom, origen='ad_hoc')
        self.assertEqual(tasca_vigent(self.model, 'pom_v'), prevista)

    def test_nomes_ad_hoc_i_cap_prevista_retorna_none(self):
        self._tasca(self.tt_pom, origen='ad_hoc')
        self.assertIsNone(tasca_vigent(self.model, 'pom_v'))

    # ── Regla 3: la feina viva mana, però una Done sola es retorna ───────────
    def test_prevista_done_sola_es_retorna(self):
        """`_close_pom_task_for_model` depèn d'això: ha de poder veure la Done per respondre
        `already_done` en comptes de `no_pom_task`."""
        t = self._tasca(self.tt_pom, status='Done')
        self.assertEqual(tasca_vigent(self.model, 'pom_v'), t)

    # ── Determinisme: cap dels dos ordres antics decideix ────────────────────
    def test_el_resolutor_no_depen_de_l_ordre_d_insercio(self):
        """Els dos criteris vells (`order_by('id')` i `order_by('-id')`) donaven files diferents
        sobre el mateix conjunt. El nou ha de donar la MATEIXA amb qualsevol ordre d'alta."""
        prevista = self._tasca(self.tt_pom)
        self._tasca(self.tt_pom, origen='ad_hoc')            # posterior
        vigent_a = tasca_vigent(self.model, 'pom_v')

        ModelTask.objects.filter(origen='ad_hoc').delete()
        self._tasca(self.tt_pom, origen='ad_hoc')            # re-creada, id més alt encara
        vigent_b = tasca_vigent(self.model, 'pom_v')

        self.assertEqual(vigent_a, prevista)
        self.assertEqual(vigent_b, prevista)
