"""M1 · L'ENTREGA, EL TANCAMENT FORÇAT I EL RASTRE — els quatre invariants del tram.

  FIT-1  — l'entrega és un ACTE informat (data, destinatari, descripció), no un artefacte
           controlat, i porta un `ok_client` manual i posterior.
  FIT-13 — informar-la TANCA la ronda, en la mateixa transacció. «Entregada» es DECLARA;
           `ronda_lliurable` es queda com el senyal previ que es dedueix.
  FIT-6  — tancar la ronda tanca TOTA la seva feina viva, pel mecanisme únic
           (`transition_task`), i cap tasca migra a cap ronda següent.
  FIT-2  — reobrir una tasca d'una ronda entregada segueix sent LEGAL (segell tou) i deixa
           rastre al log immutable.

🔒 EL QUE AQUESTS TESTS GUARDEN SOBRETOT és que el tancament forçat **no enverini el Welford**.
La llei d'Agus —«el Welford no mesura res d'una tasca que no s'ha executat»— no la imposa cap
guard nou: la imposen `_close_open_timer` (que marca `consulta=True` el tram sense escriptura),
`TRAMS_SANS` (que l'exclou) i el `if x <= 0` de `record_actual_time`. Si algú toca qualsevol
d'aquests tres, el tancament d'una ronda començaria a inventar mostres de feina que ningú no ha
fet, i el planificador se les creuria.
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.pom.models import GarmentType
from fhort.tasks.models import (Customer, Entrega, GarmentTypeItem, ModelTask, Ronda,
                                TaskTimeEstimate, TaskTransition, TaskType, TimerEntrada)
from fhort.tasks.services_c import transition_task
from fhort.tasks.services_r import (EntregaError, RondaError, informar_entrega,
                                    informar_ok_client, obrir_ronda, ronda_lliurable,
                                    tancar_ronda)


class BaseM1(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant M1'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TM1'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='tecm1')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CM1', nom='Client M1')
        gt = GarmentType.objects.create(codi_client='GTM', nom_client='Família M1', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_m1', name='Item M1')
        self.tt_pom, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.tt_fitxa, _ = TaskType.objects.get_or_create(
            code='tech_sheet', defaults={'name': 'Fitxa tècnica', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='TM1-SS26-0001', codi_tenant='TM1', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')
        # La volta 1, la implícita: feina de sempre amb `ronda` NULL.
        self.pom_r1 = ModelTask.objects.create(model=self.model, task_type=self.tt_pom,
                                               order=0, status='Done', origen='prevista')
        self.fitxa_r1 = ModelTask.objects.create(model=self.model, task_type=self.tt_fitxa,
                                                 order=1, status='Done', origen='prevista')

    def _ronda_amb_feina(self, codes=('pom', 'tech_sheet')):
        return obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, list(codes), profile=self.prof)

    def _entrega(self, ronda, **kw):
        kw.setdefault('destinatari', 'Compres · Brumà SL')
        kw.setdefault('descripcio', 'Fitxa PDF + patró DXF per correu')
        return informar_entrega(ronda, profile=self.prof, **kw)


# ── FIT-1 · L'ACTE ──────────────────────────────────────────────────────────────────────────

class EntregaActeTest(BaseM1):

    def test_l_entrega_desa_qui_quan_a_qui_i_que(self):
        r = self._ronda_amb_feina()
        e = self._entrega(r)
        e.refresh_from_db()
        self.assertEqual(e.ronda_id, r.pk)
        self.assertEqual(e.destinatari, 'Compres · Brumà SL')
        self.assertEqual(e.descripcio, 'Fitxa PDF + patró DXF per correu')
        self.assertEqual(e.qui_informa_id, self.prof.pk)
        self.assertIsNotNone(e.data)
        self.assertIsNotNone(e.created_at)
        self.assertIsNone(e.data_ok)

    def test_la_data_la_pot_aportar_qui_informa(self):
        """Informar dilluns una entrega de divendres és el cas normal."""
        divendres = timezone.now() - datetime.timedelta(days=3)
        e = self._entrega(self._ronda_amb_feina(), data=divendres)
        self.assertEqual(e.data, divendres)
        self.assertGreater(e.created_at, e.data)

    def test_sense_destinatari_no_hi_ha_entrega(self):
        r = self._ronda_amb_feina()
        with self.assertRaises(EntregaError):
            informar_entrega(r, destinatari='   ', profile=self.prof)
        self.assertFalse(Entrega.objects.exists())
        r.refresh_from_db()
        self.assertIsNone(r.tancada_el)      # i la ronda no s'ha tancat de rebot

    def test_una_volta_s_entrega_un_sol_cop(self):
        r = self._ronda_amb_feina()
        self._entrega(r)
        with self.assertRaises(EntregaError):
            self._entrega(r)
        self.assertEqual(Entrega.objects.filter(ronda=r).count(), 1)

    def test_l_entrega_no_lliga_cap_artefacte(self):
        """FIT-1: event informat, no artefacte controlat. Cap FK a fitxa/patró/ModelFitxer."""
        noms = {f.name for f in Entrega._meta.get_fields()}
        self.assertFalse(noms & {'fitxer', 'model_fitxer', 'fitxa', 'patro', 'document'})
        self.assertNotIn('data_prevista_retorn', noms)   # micro-decisió M1: no existeix

    def test_l_ok_del_client_es_manual_posterior_i_un_sol_cop(self):
        e = self._entrega(self._ronda_amb_feina())
        informar_ok_client(e, profile=self.prof)
        e.refresh_from_db()
        self.assertIsNotNone(e.data_ok)
        self.assertEqual(e.qui_informa_ok_id, self.prof.pk)
        with self.assertRaises(EntregaError):
            informar_ok_client(e, profile=self.prof)

    def test_l_ok_del_client_no_toca_la_ronda(self):
        r = self._ronda_amb_feina()
        e = self._entrega(r)
        r.refresh_from_db()
        tancada_abans = r.tancada_el
        informar_ok_client(e, profile=self.prof)
        r.refresh_from_db()
        self.assertEqual(r.tancada_el, tancada_abans)


# ── FIT-13 · L'ACTE TANCA LA RONDA ──────────────────────────────────────────────────────────

class EntregaTancaLaRondaTest(BaseM1):

    def test_informar_l_entrega_tanca_la_ronda(self):
        r = self._ronda_amb_feina()
        self.assertIsNone(r.tancada_el)
        self._entrega(r)
        r.refresh_from_db()
        self.assertIsNotNone(r.tancada_el)

    def test_entregada_no_es_dedueix_de_lliurable(self):
        """El senyal previ i el fet declarat són coses diferents, i cap implica l'altre."""
        r = self._ronda_amb_feina()
        self.assertFalse(ronda_lliurable(r))      # res Done encara
        self._entrega(r)                          # …i s'entrega igualment: s'entrega el que hi ha
        self.assertTrue(hasattr(r, 'entrega'))

    def test_despres_d_entregar_se_n_pot_obrir_una_altra(self):
        """La ronda queda tancada de debò: `obrir_ronda` ja no topa amb «n'hi ha una d'oberta»."""
        r = self._ronda_amb_feina(codes=('pom',))
        self._entrega(r)
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'], profile=self.prof)
        self.assertEqual(r2.seq, r.seq + 1)


# ── FIT-6 · EL TANCAMENT FORÇAT ─────────────────────────────────────────────────────────────

class TancamentForcatTest(BaseM1):

    def test_totes_les_tasques_de_la_ronda_queden_tancades(self):
        r = self._ronda_amb_feina()
        pom, fitxa = list(r.tasques.order_by('order'))
        transition_task(pom, 'InProgress', self.prof)
        transition_task(pom, 'Paused', self.prof)          # una Paused i una Pending
        self._entrega(r)
        for t in r.tasques.all():
            self.assertEqual(t.status, 'Done', f'{t.task_type.code} ha quedat viva')
            self.assertIsNotNone(t.finished_at)

    def test_es_tanquen_pel_mecanisme_unic_i_el_log_ho_veu(self):
        """Mai un UPDATE directe: si no hi ha fila a `TaskTransition`, la màquina no ho ha vist."""
        r = self._ronda_amb_feina(codes=('pom',))
        pom = r.tasques.get()
        self.assertEqual(TaskTransition.objects.filter(model_task=pom).count(), 0)
        self._entrega(r)
        salts = list(TaskTransition.objects.filter(model_task=pom).order_by('at', 'id')
                     .values_list('from_status', 'to_status'))
        # Dos salts, perquè `ALLOWED` no té Pending→Done i la màquina no es toca.
        self.assertEqual(salts, [('Pending', 'InProgress'), ('InProgress', 'Done')])

    def test_una_tasca_in_progress_es_tanca_amb_un_sol_salt(self):
        r = self._ronda_amb_feina(codes=('pom',))
        pom = r.tasques.get()
        transition_task(pom, 'InProgress', self.prof)
        n = TaskTransition.objects.filter(model_task=pom).count()
        self._entrega(r)
        pom.refresh_from_db()
        self.assertEqual(pom.status, 'Done')
        self.assertEqual(TaskTransition.objects.filter(model_task=pom).count(), n + 1)

    def test_cap_tasca_migra_a_cap_ronda_seguent(self):
        r = self._ronda_amb_feina()
        tasques_abans = set(ModelTask.objects.values_list('pk', flat=True))
        rondes_abans = set(Ronda.objects.values_list('pk', flat=True))
        self._entrega(r)
        self.assertEqual(set(ModelTask.objects.values_list('pk', flat=True)), tasques_abans)
        self.assertEqual(set(Ronda.objects.values_list('pk', flat=True)), rondes_abans)
        # I les de la volta hi segueixen: tancar no és desancorar.
        self.assertEqual(r.tasques.count(), 2)

    def test_les_tasques_de_fora_de_la_ronda_no_es_toquen(self):
        r = self._ronda_amb_feina(codes=('pom',))
        extra = ModelTask.objects.create(model=self.model, task_type=self.tt_fitxa,
                                         order=9, status='Pending', origen='ad_hoc')
        self._entrega(r)
        extra.refresh_from_db()
        self.assertEqual(extra.status, 'Pending')

    def test_sense_tecnic_i_amb_feina_viva_el_tancament_es_rebutja(self):
        """Tancar la feina d'algú és un ACTE: ha de tenir autor al log."""
        r = self._ronda_amb_feina(codes=('pom',))
        with self.assertRaises(RondaError):
            tancar_ronda(r)
        r.refresh_from_db()
        self.assertIsNone(r.tancada_el)          # ni la data: o tot o res

    def test_una_ronda_sense_feina_viva_es_tanca_sense_tecnic(self):
        r = self._ronda_amb_feina(codes=('pom',))
        pom = r.tasques.get()
        transition_task(pom, 'InProgress', self.prof)
        transition_task(pom, 'Done', self.prof)
        tancar_ronda(r)                          # idempotència d'abans, intacta
        r.refresh_from_db()
        self.assertIsNotNone(r.tancada_el)


# ── FIT-6 · I EL WELFORD NO S'ENVERINA ──────────────────────────────────────────────────────

class TancamentForcatWelfordTest(BaseM1):

    def _cella(self, tt):
        return TaskTimeEstimate.objects.filter(garment_type_item=self.item, task_type=tt).first()

    def test_una_pending_mai_executada_no_deixa_cap_mostra(self):
        r = self._ronda_amb_feina(codes=('pom',))
        self._entrega(r)
        self.assertIsNone(self._cella(self.tt_pom))

    def test_el_tram_del_salt_de_cortesia_queda_marcat_consulta(self):
        """És AIXÒ el que ho fa funcionar: neix `consulta=False` i es tanca sense escriptura."""
        r = self._ronda_amb_feina(codes=('pom',))
        pom = r.tasques.get()
        self._entrega(r)
        trams = list(TimerEntrada.objects.filter(model_task=pom))
        self.assertEqual(len(trams), 1)
        self.assertTrue(trams[0].consulta)
        self.assertIsNone(trams[0].escriptura_at)

    def test_una_tasca_amb_temps_real_si_que_alimenta(self):
        r = self._ronda_amb_feina(codes=('pom',))
        pom = r.tasques.get()
        ara = timezone.now()
        TimerEntrada.objects.create(model_task=pom, tecnic=self.prof,
                                    inici=ara - datetime.timedelta(minutes=30), fi=ara,
                                    minuts=30, actiu=False)
        self._entrega(r)
        cella = self._cella(self.tt_pom)
        self.assertIsNotNone(cella)
        self.assertEqual(cella.n, 1)
        self.assertEqual(int(cella.mean_minutes), 30)   # els 0 min del salt no dilueixen res


# ── FIT-2 · EL RASTRE DE REOBERTURA ─────────────────────────────────────────────────────────

class RastreReoberturaTest(BaseM1):

    def _reobre(self, task):
        transition_task(task, 'InProgress', self.prof)
        return (TaskTransition.objects.filter(model_task=task, from_status='Done',
                                              to_status='InProgress').order_by('-id').first())

    def test_reobrir_una_tasca_entregada_segueix_sent_legal_i_deixa_rastre(self):
        r = self._ronda_amb_feina(codes=('pom',))
        self._entrega(r)
        pom = r.tasques.get()
        salt = self._reobre(pom)
        pom.refresh_from_db()
        self.assertEqual(pom.status, 'InProgress')       # segell TOU: no es rebutja
        self.assertEqual(salt.nota, f"reoberta després d'entrega de R{r.seq}")
        self.assertIsNone(salt.auto)                     # és un gest HUMÀ, no un automatisme

    def test_sense_entrega_no_hi_ha_rastre(self):
        r = self._ronda_amb_feina(codes=('pom',))
        pom = r.tasques.get()
        transition_task(pom, 'InProgress', self.prof)
        transition_task(pom, 'Done', self.prof)
        self.assertIsNone(self._reobre(pom).nota)

    def test_una_tasca_de_la_volta_1_no_te_res_a_rastrejar(self):
        """`ronda` NULL és la volta implícita: no pertany a cap ronda entregable."""
        self.assertIsNone(self._reobre(self.pom_r1).nota)

    def test_la_nota_diu_el_numero_de_la_volta(self):
        r = self._ronda_amb_feina(codes=('pom',))
        self._entrega(r)
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'], profile=self.prof)
        self._entrega(r2)
        self.assertIn(f'R{r2.seq}', self._reobre(r2.tasques.get()).nota)


# ── LES PORTES ──────────────────────────────────────────────────────────────────────────────

class PortesEntregaTest(BaseM1):

    def _client(self):
        c = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        c.force_authenticate(user=self.user)
        return c

    def test_post_entrega_tanca_la_ronda_i_torna_l_acte(self):
        r = self._ronda_amb_feina()
        resp = self._client().post(f'/api/v1/rondes/{r.pk}/entrega/',
                                   {'destinatari': 'Brumà SL', 'descripcio': 'fitxa + patró'},
                                   format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['destinatari'], 'Brumà SL')
        r.refresh_from_db()
        self.assertIsNotNone(r.tancada_el)
        self.assertFalse(r.tasques.exclude(status='Done').exists())

    def test_post_entrega_sense_destinatari_dona_400_amb_codi(self):
        r = self._ronda_amb_feina()
        resp = self._client().post(f'/api/v1/rondes/{r.pk}/entrega/', {}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.data['code'], 'entrega_invalida')

    def test_post_entrega_sobre_una_ronda_inexistent_dona_404(self):
        self.assertEqual(self._client().post('/api/v1/rondes/999999/entrega/',
                                             {'destinatari': 'X'}, format='json').status_code, 404)

    def test_patch_ok_client(self):
        e = self._entrega(self._ronda_amb_feina())
        resp = self._client().patch(f'/api/v1/entregues/{e.pk}/ok-client/', {}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIsNotNone(resp.data['data_ok'])
        # El segon cop és un rebuig, no un toggle.
        self.assertEqual(self._client().patch(f'/api/v1/entregues/{e.pk}/ok-client/', {},
                                              format='json').status_code, 400)

    def test_get_rondes_del_model_serveix_l_entrega_niuada(self):
        r = self._ronda_amb_feina()
        self._entrega(r)
        resp = self._client().get(f'/api/v1/models/{self.model.pk}/rondes/')
        self.assertEqual(resp.status_code, 200)
        fila = [x for x in resp.data if x['id'] == r.pk][0]
        self.assertTrue(fila['entregada'])
        self.assertEqual(fila['entrega']['destinatari'], 'Compres · Brumà SL')
        self.assertIsNotNone(fila['tancada_el'])

    def test_una_ronda_sense_entrega_diu_entregada_false_i_entrega_null(self):
        r = self._ronda_amb_feina()
        resp = self._client().get(f'/api/v1/models/{self.model.pk}/rondes/')
        fila = [x for x in resp.data if x['id'] == r.pk][0]
        self.assertFalse(fila['entregada'])
        self.assertIsNone(fila['entrega'])
