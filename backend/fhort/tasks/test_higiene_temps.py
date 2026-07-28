"""S1 · LA FONT TANCADA — `MAX_MINUTS_TRAM` s'aplica a TOTES les lectures de temps (28/07).

Fins ara la regla d'higiene només vivia al rastre (`recompute_welford` i la data-op del 27/07):
el Welford es netejava, però les tres superfícies que el tècnic i el manager MIREN seguien
sumant `Sum('minuts')` en cru. Una tasca amb un tram desbocat de 3.710 min es veia com 61 h de
feina al dashboard, a l'albarà i a l'anàlisi de temps — i el `_real_minutes` que alimenta el
Welford en tancar-la hi tornava a injectar la mentida que el recompute acabava de treure.

CRITERI (una sola llei, `services_i.TRAMS_SANS`): EXCLUSIÓ, no retall. Un tram de 3.710 min no
és una jornada llarga a podar: és una fuita, i no sabem quant s'hi va treballar. Retallar a
1.440 inventaria feina que ningú no ha fet; excloure diu "d'aquest tram no en tenim dada".

Convenció del repo: `python manage.py test fhort.tasks` (el projecte NO fa servir pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import (Customer, GarmentTypeItem, ModelTask, TaskType,
                                TimerEntrada)
from fhort.tasks.services_i import (MAX_MINUTS_TRAM, _real_minutes, minuts_per_model_task,
                                    tram_compta)

TRAM_SA = 90
TRAM_DESBOCAT = 3710      # el cas real de la data-op del 27/07


class HigieneTempsTest(TenantTestCase):

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
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='techigiene')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CLI', nom='Client de prova')
        gt = GarmentType.objects.create(codi_client='GTH', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_h', name='Item H')
        self.tt = TaskType.objects.create(code='task_h', name='Task H', fase='Dev. tècnic')
        self.model = Model.objects.create(
            codi_intern='TST-SS26-0001', codi_tenant='TST', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item,
            nom_prenda='Peça')
        self.task = ModelTask.objects.create(model=self.model, task_type=self.tt, order=0,
                                             status='Pending', assignee=self.prof)

    def _tram(self, minuts, obert=False):
        """Un tram ja consolidat (o obert) sobre la tasca."""
        fi_at = None if obert else timezone.now()
        return TimerEntrada.objects.create(
            model_task=self.task, tecnic=self.prof,
            inici=timezone.now() - datetime.timedelta(minutes=minuts),
            fi=fi_at, minuts=None if obert else minuts, actiu=obert)

    # ---- la llei, nua -------------------------------------------------------------------

    def test_el_criteri_es_exclusio_no_retall(self):
        """El tram desbocat val 0, NO val MAX_MINUTS_TRAM. Si algun dia algú el converteix en
        retall, aquest test cau i obliga a decidir-ho conscientment (no a relliscar-hi)."""
        self._tram(TRAM_DESBOCAT)
        self.assertEqual(_real_minutes(self.task), 0)
        self.assertNotEqual(_real_minutes(self.task), MAX_MINUTS_TRAM)

    def test_el_llindar_es_inclusiu(self):
        """Exactament MAX_MINUTS_TRAM encara és sa (`<=`, com el recompute)."""
        self._tram(MAX_MINUTS_TRAM)
        self.assertEqual(_real_minutes(self.task), MAX_MINUTS_TRAM)
        self._tram(MAX_MINUTS_TRAM + 1)
        self.assertEqual(_real_minutes(self.task), MAX_MINUTS_TRAM)   # el segon no hi entra

    def test_tram_sa_intacte(self):
        self._tram(TRAM_SA)
        self.assertEqual(_real_minutes(self.task), TRAM_SA)

    def test_tram_obert_no_compta(self):
        """B1-a: només temps consolidat. El tram obert no té `fi` → fora."""
        self._tram(TRAM_SA)
        self._tram(30, obert=True)
        self.assertEqual(_real_minutes(self.task), TRAM_SA)

    def test_predicat_python_i_filtre_orm_diuen_el_mateix(self):
        """`tram_compta` és la versió Python de `TRAMS_SANS`. Si divergeixen, l'albarà i el
        dashboard tornen a donar xifres diferents — que és exactament el que es tanca aquí."""
        self._tram(TRAM_SA)
        self._tram(TRAM_DESBOCAT)
        self._tram(MAX_MINUTS_TRAM)
        self._tram(30, obert=True)
        per_orm = minuts_per_model_task(TimerEntrada.objects.filter(model_task=self.task))
        per_python = sum(t.minuts for t in self.task.timers.all() if tram_compta(t))
        self.assertEqual(per_orm.get(self.task.id, 0), per_python)
        self.assertEqual(per_python, TRAM_SA + MAX_MINUTS_TRAM)

    # ---- les superfícies visibles quadren entre elles -----------------------------------

    def test_les_tres_superficies_quadren(self):
        """Compositor del dashboard · albarà · anàlisi de temps: mateixa xifra, i és la SANA.
        Es criden els mateixos helpers que fan servir les vistes (una sola font de veritat)."""
        self._tram(TRAM_SA)
        self._tram(TRAM_DESBOCAT)

        # compositor del dashboard i anàlisi de temps → minuts_per_model_task
        compositor = minuts_per_model_task(
            TimerEntrada.objects.filter(model_task__model_id=self.model.id))
        analisi = minuts_per_model_task(
            TimerEntrada.objects.filter(model_task__in=ModelTask.objects.filter(
                model_id=self.model.id)))
        # albarà i registre de consum → bucle Python amb tram_compta
        albara = sum(tm.minuts for mt in self.model.model_tasks.all()
                     for tm in mt.timers.all() if tram_compta(tm))

        self.assertEqual(compositor.get(self.task.id, 0), TRAM_SA)
        self.assertEqual(analisi.get(self.task.id, 0), TRAM_SA)
        self.assertEqual(albara, TRAM_SA)
        self.assertEqual(_real_minutes(self.task), TRAM_SA)
