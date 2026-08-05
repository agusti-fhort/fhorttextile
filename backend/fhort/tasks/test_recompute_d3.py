"""F3.1 · LA LLEI D-3 AL CORPUS: **una tasca = una mostra.**

El que això protegeix, dit com a defecte: fins avui el corpus es construïa per TRANSICIÓ →Done.
Com que `Done→InProgress` és permesa (rectificació), cada re-tancament hi deixava una mostra
nova amb el total acumulat d'aquell moment. Les tasques que es reobren —les que costen— pesaven
tantes vegades com s'havien reobert, i sempre amb el número més alt. A `fhort` això és la tasca
250, tancada **17 vegades**, que tota sola omplia una cel·la de n=17 i 562 min de mitjana.

Els quatre tests són les quatre frases de la llei:

  1. una tasca reoberta N cops és UNA mostra, amb el seu total d'AVUI
  2. tres rondes són TRES mostres (feina real distinta)
  3. una correcció és mostra pròpia (també és treball fet)
  4. el temps DECLARAT compta igual que el mesurat

Convenció del repo: `python manage.py test fhort.tasks.test_recompute_d3` (no pytest).
"""
import datetime

from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from fhort.tasks.management.commands.recompute_welford import (_mostres_de_la_cella,
                                                               es_tram_orfe)
from fhort.tasks.models import Customer, ModelTask, TaskTransition, TaskType, TimerEntrada


class RecomputeD3Test(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TD3'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from django.contrib.auth import get_user_model
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model
        from fhort.pom.models import GarmentType
        from fhort.tasks.models import GarmentTypeItem

        user = get_user_model().objects.create(username='qa_d3')
        self.prof, _ = UserProfile.objects.get_or_create(user=user)
        gt = GarmentType.objects.create(codi_client='GD3', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_d3', name='Item D3')
        self.customer = Customer.objects.create(codi='CD3', nom='Client D3')
        self.model = Model.objects.create(
            codi_intern='TD3-SS27-0001', codi_tenant='TD3', any=2027, sequencial=1,
            nom_prenda='Peça D3', customer=self.customer, garment_type_item=self.item)
        self.tt = TaskType.objects.get(code='pom')
        self.tt_extern = TaskType.objects.get(code='pattern_hand')
        self.ara = timezone.now()

    # ── utillatge ────────────────────────────────────────────────────────────
    def _tasca(self, tt=None, **extra):
        tt = tt or self.tt
        extra.setdefault('status', 'Done')
        return ModelTask.objects.create(
            model=self.model, task_type=tt,
            order=ModelTask.objects.filter(model=self.model).count(), **extra)

    def _tram(self, task, minuts, origen=TimerEntrada.ORIGEN_MESURAT, fa_minuts=120):
        fi = self.ara - datetime.timedelta(minutes=fa_minuts)
        return TimerEntrada.objects.create(
            model_task=task, tecnic=self.prof, inici=fi - datetime.timedelta(minutes=minuts),
            fi=fi, minuts=minuts, actiu=False, origen=origen)

    def _tanca(self, task, vegades=1):
        for i in range(vegades):
            TaskTransition.objects.create(model_task=task, from_status='InProgress',
                                          to_status='Done', by=self.prof)

    def _mostres(self, **kw):
        tasques = list(ModelTask.objects
                       .filter(model__garment_type_item=self.item, task_type=self.tt)
                       .prefetch_related('timers'))
        return [int(x) for x in _mostres_de_la_cella(self.item.id, self.tt.id, tasques, **kw)]

    # ── 1 · UNA TASCA = UNA MOSTRA ───────────────────────────────────────────
    def test_una_tasca_reoberta_disset_cops_es_UNA_mostra(self):
        """El cas real de la tasca 250. Abans: 17 mostres. Ara: una, amb el total de debò."""
        t = self._tasca()
        self._tram(t, 300)
        self._tram(t, 460, fa_minuts=60)
        self._tanca(t, vegades=17)
        self.assertEqual(self._mostres(), [760])

    def test_la_mostra_es_el_total_D_AVUI_no_el_del_moment_de_tancar(self):
        """«Reobrir ACTUALITZA la mostra»: la feina feta DESPRÉS de l'últim tancament hi entra.
        Amb el criteri vell no hi entrava mai, i el que costava més es comptava per menys."""
        t = self._tasca()
        self._tram(t, 30, fa_minuts=300)
        self._tanca(t)
        self._tram(t, 90, fa_minuts=10)   # s'hi va tornar després de donar-la per feta
        self.assertEqual(self._mostres(), [120])

    def test_una_tasca_mai_tancada_no_es_mostra(self):
        """Feina en curs no és una peça feta: no té res a dir sobre quant costa fer-ne una."""
        t = self._tasca(status='InProgress')
        self._tram(t, 240)
        self.assertEqual(self._mostres(), [])

    # ── 2 i 3 · RONDES I CORRECCIONS ─────────────────────────────────────────
    def test_tres_rondes_son_tres_mostres(self):
        """Cada volta és feina real distinta. Surt sol de la llei: són tres `ModelTask`."""
        from fhort.tasks.models import Ronda

        for i, minuts in enumerate((100, 200, 300), start=1):
            ronda = Ronda.objects.create(model=self.model, seq=i + 1,
                                         motiu=Ronda.MOTIU_NOVA_MOSTRA)
            t = self._tasca(origen='ad_hoc', ronda=ronda)
            self._tram(t, minuts, fa_minuts=300 - i * 10)
            self._tanca(t)
        self.assertEqual(sorted(self._mostres()), [100, 200, 300])

    def test_una_correccio_es_mostra_propia(self):
        """També és treball fet. I no obre ronda (S-20): és una tasca amb `mare` i motiu."""
        from fhort.tasks.models import Ronda

        mare = self._tasca()
        self._tram(mare, 50, fa_minuts=300)
        self._tanca(mare)

        correccio = self._tasca(origen='ad_hoc', mare=mare, motiu=Ronda.MOTIU_CORRECCIO)
        self._tram(correccio, 20, fa_minuts=100)
        self._tanca(correccio)

        self.assertEqual(sorted(self._mostres()), [20, 50])

    # ── 4 · EL TEMPS DECLARAT ────────────────────────────────────────────────
    def test_el_temps_declarat_compta_igual_que_el_mesurat(self):
        t = self._tasca()
        self._tram(t, 40, origen=TimerEntrada.ORIGEN_MESURAT, fa_minuts=300)
        self._tram(t, 60, origen=TimerEntrada.ORIGEN_DECLARAT, fa_minuts=100)
        self._tanca(t)
        self.assertEqual(self._mostres(), [100])

    # ── 🚩 ELS RELLOTGES ORFES ───────────────────────────────────────────────
    def test_un_tram_mesurat_sobre_una_tasca_externa_es_orfe(self):
        """Una externa es fa FORA de l'eina: mesurar-la és impossible, i un tram mesurat només
        pot venir de la porta que obria rellotge sense pantalla (arreglada a T2)."""
        externa = self._tasca(tt=self.tt_extern)
        mesurat = self._tram(externa, 500, origen=TimerEntrada.ORIGEN_MESURAT)
        declarat = self._tram(externa, 120, origen=TimerEntrada.ORIGEN_DECLARAT)
        self.assertTrue(es_tram_orfe(mesurat, externa))
        self.assertFalse(es_tram_orfe(declarat, externa))

    def test_un_tram_mesurat_sobre_una_INTERNA_no_es_orfe(self):
        interna = self._tasca()
        self.assertFalse(es_tram_orfe(self._tram(interna, 30), interna))

    def test_sense_orfes_els_treu_del_total_sense_perdre_la_mostra(self):
        """La simulació que serveix per DECIDIR: el que canvia és el total, no si hi ha mostra."""
        t = self._tasca()
        self._tram(t, 45)
        self._tanca(t)
        self.assertEqual(self._mostres(sense_orfes=True), [45])   # interna: no se'n treu res
