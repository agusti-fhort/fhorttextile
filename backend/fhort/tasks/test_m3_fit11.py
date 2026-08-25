"""M3 · FIT-11 — LA PARET DE LA VOLTA: `Done→InProgress` només sobre la DARRERA volta.

Llei dura d'Agus (24/08): **obrir una ronda nova ELIMINA l'opció de rectificar l'anterior.**
El que s'ha de refer es fa a la volta nova —que té identitat, genealogia i comptador propis—,
no reobrint una tasca de dues voltes enrere i deixant el rastre repartit entre les dues.

FIT-2 **segueix viu i no s'ha tocat**: sobre la darrera volta, rectificar és legal i deixa nota
(«reoberta després d'entrega de R{n}»). Aquest fitxer guarda les dues meitats alhora: la que es
tanca i la que ha de seguir oberta.

Convenció del repo: `python manage.py test fhort.tasks.test_m3_fit11` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, GarmentTypeItem, ModelTask, Ronda, TaskType
from fhort.tasks.services_c import TransitionError, hi_ha_volta_posterior, transition_task
from fhort.tasks.services_r import informar_entrega, obrir_ronda, tancar_ronda


class BaseFit11(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant F11'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'T11'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='tec11')
        UserProfile.objects.get_or_create(user=self.user)
        self.prof = self.user.profile
        self.customer = Customer.objects.create(codi='C11', nom='Client F11')
        gt = GarmentType.objects.create(codi_client='G11', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_11', name='Item 11')
        self.tt_pom, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='T11-SS26-0001', codi_tenant='T11', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')
        # La feina LLEGADA: `ronda` NULL. A la BD ja no en queda cap (el retroactiu de M5 la va
        # adoptar tota, 25/08), però el FIXTURE la conserva a posta: el que aquest test mesura és
        # que `mare_homologa` sap encadenar la genealogia quan la volta anterior no té fila, i
        # aquell camí segueix viu al codi per a qualsevol tenant que encara no hagi passat el
        # retroactiu.
        self.llegada = ModelTask.objects.create(model=self.model, task_type=self.tt_pom,
                                                order=0, status='Done', origen='prevista')

    def _volta(self, codes=('pom',)):
        return obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, list(codes), profile=self.prof)

    def _tasca_done_de(self, ronda):
        t = ronda.tasques.get(task_type=self.tt_pom)
        transition_task(t, 'InProgress', self.prof)
        transition_task(t, 'Done', self.prof)
        t.refresh_from_db()
        return t

    def _reobre(self, task):
        return transition_task(task, 'InProgress', self.prof)


class LaDarreraVoltaSeguixObertaTest(BaseFit11):
    """FIT-2 intacte: sobre la volta VIGENT, rectificar és legal."""

    def test_rectificar_la_darrera_volta_es_legal(self):
        r = self._volta()
        t = self._tasca_done_de(r)
        self._reobre(t)
        t.refresh_from_db()
        self.assertEqual(t.status, 'InProgress')

    def test_i_segueix_deixant_la_nota_d_FIT_2_quan_ja_s_havia_entregat(self):
        r = self._volta()
        t = self._tasca_done_de(r)
        informar_entrega(r, destinatari='Brumà SL', profile=self.prof)
        t.refresh_from_db()
        self._reobre(t)
        nota = t.transitions.order_by('-id').first().nota
        self.assertIn(f'R{r.seq}', nota)

    def test_una_tasca_llegada_sense_cap_volta_al_model_es_reobre(self):
        """Un model sense cap `Ronda` no té «volta posterior»: la paret no hi arriba."""
        self._reobre(self.llegada)
        self.llegada.refresh_from_db()
        self.assertEqual(self.llegada.status, 'InProgress')


class LaVoltaAnteriorEsTancaTest(BaseFit11):
    """La llei dura: amb una volta posterior oberta, la vella ja no es rectifica."""

    def test_obrir_la_volta_seguent_tanca_la_rectificacio_de_l_anterior(self):
        r2 = self._volta()
        t2 = self._tasca_done_de(r2)
        informar_entrega(r2, destinatari='Brumà SL', profile=self.prof)   # tanca la R2
        r3 = self._volta()
        t2.refresh_from_db()
        with self.assertRaises(TransitionError) as cm:
            self._reobre(t2)
        self.assertEqual(cm.exception.code, 'volta_posterior')
        self.assertIn(f'R{r3.seq}', str(cm.exception))
        t2.refresh_from_db()
        self.assertEqual(t2.status, 'Done')      # el rebuig no deixa la tasca a mitges

    def test_la_feina_LLEGADA_queda_enrere_quan_s_obre_una_volta(self):
        """`ronda` NULL anterior a la primera volta ÉS d'una volta anterior: la R1 explícita
        que neix després és posterior a ella, encara que la tasca no tingui fila de ronda."""
        r = self._volta()
        with self.assertRaises(TransitionError) as cm:
            self._reobre(self.llegada)
        self.assertEqual(cm.exception.code, 'volta_posterior')
        self.assertEqual(hi_ha_volta_posterior(self.llegada).pk, r.pk)

    def test_la_feina_del_BUIT_no_es_d_una_volta_anterior(self):
        """🔑 El cas que fa que això no es pugui escriure amb un `seq__gt` i prou. Una tasca
        nascuda ENTRE dues voltes també té `ronda` NULL, però no té cap volta posterior: el que
        les separa és el TEMPS, el mateix criteri que `tasques_del_buit` fa servir per adoptar-la."""
        r = self._volta()
        tancar_ronda(r, profile=self.prof)
        del_buit = ModelTask.objects.create(model=self.model, task_type=self.tt_pom,
                                            order=9, status='Done', origen='ad_hoc')
        self.assertIsNone(hi_ha_volta_posterior(del_buit))
        self._reobre(del_buit)
        del_buit.refresh_from_db()
        self.assertEqual(del_buit.status, 'InProgress')

    def test_force_salta_la_paret_com_salta_la_de_l_albara(self):
        """`force` és per a rutines internes que reprocessen històric: no estan rectificant res."""
        r2 = self._volta()
        t2 = self._tasca_done_de(r2)
        tancar_ronda(r2, profile=self.prof)
        self._volta()
        t2.refresh_from_db()
        transition_task(t2, 'InProgress', self.prof, force=True)
        t2.refresh_from_db()
        self.assertEqual(t2.status, 'InProgress')

    def test_la_paret_NOMES_toca_la_reobertura(self):
        """FIT-11 parla de RECTIFICAR (`Done→InProgress`), no de començar el que encara no
        s'ha fet: una `Pending` llegada segueix podent-se treballar tot i que després s'hagi
        obert una volta. Tancar-li el pas hauria condemnat feina que ningú no ha fet mai."""
        pendent = ModelTask.objects.create(model=self.model, task_type=self.tt_pom,
                                           order=5, status='Pending', origen='ad_hoc')
        self._volta()
        pendent.refresh_from_db()
        self.assertIsNotNone(hi_ha_volta_posterior(pendent))   # sí que en té, de posterior…
        transition_task(pendent, 'InProgress', self.prof)      # …i la paret no li toca
        pendent.refresh_from_db()
        self.assertEqual(pendent.status, 'InProgress')
