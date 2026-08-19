"""F2.0 · EL CONTRACTE DE DADES que la UI de F2 necessita.

F1 va construir la genealogia (`ronda`, `mare`, `motiu`) i les regles noves (paret d'albarà,
batec, exclusió per trams) però **no en va exposar res**: `ModelTaskSerializer` seguia sent el de
Sprint B. La UI de F2 ha de decidir quina cara del modal ensenya, i no pot deduir-ho de l'`status`.

Aquest fitxer fixa els sis camps derivats i, sobretot, que `obert_per` mira el **TRAM** i no
l'`assignee`: és la lliçó de F1.5 —`assignee` és planificació, el rellotge és realitat— i
confondre-les és el que va trencar l'exclusió durant mesos.

Convenció del repo: `python manage.py test fhort.tasks.test_contracte_f2` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, GarmentTypeItem, ModelTask, Ronda, TaskType
from fhort.tasks.serializers_b import ModelTaskSerializer
from fhort.tasks.services_c import transition_task
from fhort.tasks.services_r import obrir_correccio, obrir_ronda


class ContracteF2Test(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TCF'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.a_user = get_user_model().objects.create(username='tecCA')
        self.a, _ = UserProfile.objects.get_or_create(
            user=self.a_user, defaults={'nom_complet': 'Anna'})
        self.b_user = get_user_model().objects.create(username='tecCB')
        self.b, _ = UserProfile.objects.get_or_create(
            user=self.b_user, defaults={'nom_complet': 'Bru'})
        self.customer = Customer.objects.create(codi='CCF', nom='Client de prova')
        gt = GarmentType.objects.create(codi_client='GTC', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_c', name='Item C')
        self.tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='TCF-SS26-0001', codi_tenant='TCF', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')
        self.task = ModelTask.objects.create(model=self.model, task_type=self.tt, order=0,
                                             status='Pending', origen='prevista')

    def _dades(self, task=None):
        return ModelTaskSerializer(task or self.task).data

    # ── Els camps hi són ─────────────────────────────────────────────────────
    def test_el_contracte_exposa_els_sis_camps_derivats(self):
        d = self._dades()
        for camp in ('es_vigent', 'ronda_seq', 'albaranada', 'obert_per', 'obert_per_nom',
                     'es_lliurable', 'tipus_extern', 'mare', 'motiu', 'ronda', 'assignee_nom'):
            self.assertIn(camp, d, f'falta «{camp}» al contracte de F2')

    def test_la_genealogia_es_read_only(self):
        """`ronda`/`mare`/`motiu` els escriu `obrir_ronda`, mai el client."""
        camps = ModelTaskSerializer().fields
        for camp in ('ronda', 'mare', 'motiu'):
            self.assertTrue(camps[camp].read_only, f'«{camp}» és escrivible pel client')

    # ── es_vigent ────────────────────────────────────────────────────────────
    def test_la_tasca_sola_es_vigent(self):
        self.assertTrue(self._dades()['es_vigent'])

    def test_amb_ronda_oberta_la_vigent_es_la_de_la_ronda(self):
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        de_la_ronda = r.tasques.get()
        self.assertFalse(self._dades()['es_vigent'])
        self.assertTrue(self._dades(de_la_ronda)['es_vigent'])
        self.assertEqual(self._dades(de_la_ronda)['ronda_seq'], 2)
        self.assertIsNone(self._dades()['ronda_seq'], 'la ronda 1 és implícita: seq null')

    def test_la_filla_diu_de_qui_es_filla(self):
        # S-20 — la correcció ja no obre volta: el contracte que es fixa aquí és la GENEALOGIA
        # (`mare` + `motiu`), que és el que la UI llegeix, i aquell no ha canviat.
        _, tasques = obrir_correccio(self.model, ['pom'])
        d = self._dades(tasques[0])
        self.assertEqual(d['mare'], self.task.pk)
        self.assertEqual(d['motiu'], Ronda.MOTIU_CORRECCIO)
        self.assertIsNone(d['ronda_seq'], 'una correcció de la volta 1 no inventa cap volta')

    # ── obert_per: el TRAM, no l'assignee ────────────────────────────────────
    def test_obert_per_es_null_si_ningu_hi_treballa(self):
        self.assertIsNone(self._dades()['obert_per'])

    def test_obert_per_diu_qui_hi_es_DE_DEBO_no_qui_la_te_assignada(self):
        """La lliçó de F1.5: `assignee` és planificació i el tram és realitat. Si el contracte
        digués `assignee`, el modal de F2.1 acusaria la persona equivocada."""
        ModelTask.objects.filter(pk=self.task.pk).update(assignee=self.b)
        self.task.refresh_from_db()
        transition_task(self.task, 'InProgress', self.a)   # qui hi treballa és A
        d = self._dades()
        self.assertEqual(d['obert_per'], self.a.pk)
        self.assertEqual(d['obert_per_nom'], self.a.nom_complet)
        self.assertEqual(d['assignee'], self.b.pk, 'premissa: assignada a B')

    def test_obert_per_torna_a_null_en_pausar(self):
        transition_task(self.task, 'InProgress', self.a)
        transition_task(self.task, 'Paused', self.a)
        self.assertIsNone(self._dades()['obert_per'])

    # ── albaranada: la paret de D-5, precalculada ────────────────────────────
    def test_albaranada_es_fals_sense_albara(self):
        self.assertFalse(self._dades()['albaranada'])

    def test_un_albara_DRAFT_no_tapia(self):
        """DRAFT encara es pot desfer esborrant-lo: no és la paret."""
        from fhort.commerce.models import DeliveryNote, DeliveryNoteLine
        dn = DeliveryNote.objects.create(customer=self.customer, status='DRAFT')
        DeliveryNoteLine.objects.create(delivery_note=dn, model_task=self.task,
                                        line_kind='TASK', quantity=1, unit_price=0, position=1)
        self.assertFalse(self._dades()['albaranada'])

    def test_un_albara_EMES_tapia(self):
        from fhort.commerce.models import DeliveryNote, DeliveryNoteLine
        dn = DeliveryNote.objects.create(customer=self.customer, status='DRAFT')
        DeliveryNoteLine.objects.create(delivery_note=dn, model_task=self.task,
                                        line_kind='TASK', quantity=1, unit_price=0, position=1)
        DeliveryNote.objects.filter(pk=dn.pk).update(status='ISSUED')
        self.assertTrue(self._dades()['albaranada'])

    # ── es_lliurable · tipus_extern ──────────────────────────────────────────
    def _tasca_fresca(self):
        """`update()` escriu a BD però no invalida la FK ja carregada: cal rellegir la tasca
        perquè el serializer vegi el `task_type` nou."""
        return ModelTask.objects.select_related('task_type').get(pk=self.task.pk)

    def test_es_lliurable_ve_del_tipus(self):
        TaskType.objects.filter(pk=self.tt.pk).update(es_lliurable=True)
        self.assertTrue(self._dades(self._tasca_fresca())['es_lliurable'])

    def test_tipus_extern_marca_les_que_admeten_temps_declarat(self):
        self.assertFalse(self._dades()['tipus_extern'])
        TaskType.objects.filter(pk=self.tt.pk).update(tipus='Externa-lliure')
        self.assertTrue(self._dades(self._tasca_fresca())['tipus_extern'])

    # ── ronda_oberta al serializer del model ─────────────────────────────────
    def test_el_model_diu_quina_volta_te_oberta(self):
        from fhort.models_app.serializers import ModelDetailSerializer
        self.assertIsNone(ModelDetailSerializer(self.model).data['ronda_oberta'])
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        d = ModelDetailSerializer(self.model).data['ronda_oberta']
        self.assertEqual(d['seq'], 2)
        self.assertEqual(d['motiu'], Ronda.MOTIU_NOVA_MOSTRA)
        self.assertEqual(d['id'], r.pk)
