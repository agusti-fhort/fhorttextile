"""Q2 · ESCRIURE SOBRE UNA TASCA PAUSADA L'HA DE REOBRIR I OBRIR TRAM (F1.3).

EL SÍMPTOMA QUE HO VA DESTAPAR
------------------------------
Sortint de «Mesurar prenda» el modal deia **«total de la tasca: 0h 00m»** sobre una sessió que
havia durat mitja hora. El cens de staging va donar la mesura de fons:

    TRAMS totals: 240 · amb `last_heartbeat`: **3** · SENSE: **237**

O sigui que el batec de F1.3 —«escriure és el senyal»— pràcticament no ha marcat mai res. I això
no és cosmètic: el guard de tasca oblidada s'ancora a `last_heartbeat` **o a `inici` si no n'hi
ha hagut cap**, de manera que sense batec el guard compta des de l'obertura i pausa als 30
minuts **encara que la persona hi estigui escrivint**. A partir d'aquell moment la tasca és
`Paused`, el tram és tancat, i tota la feina que vingui després no la compta ningú fins que una
escriptura la reobri.

EL QUE AQUEST FITXER FIXA, i que ha de caure si algú re-ancora el batec:
  1. Escriure sobre una tasca **Paused** la reobre (`Paused → InProgress`) i **obre tram**.
  2. El tram neix amb `last_heartbeat` **estampat** — qui obre una tasca escrivint ja ha escrit,
     i sense el segell el guard el pausaria als 30 minuts comptant des de `inici`.
  3. Escriure sobre una **InProgress** renova el segell del tram obert (no n'obre un de nou).
  4. El camí SENCER, per la porta HTTP real de la superfície de presa
     (`PATCH /size-check-lines/<id>/`), i no només cridant el servei: el símptoma era d'una
     pantalla, i entre la pantalla i el servei hi ha una vista que pot no cridar-lo.
  5. Una tasca **Done** NO es reobre escrivint: reobrir és un acte humà (D-5).

Convenció del repo: `python manage.py test fhort.tasks.test_batec_sobre_pausada` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import Model, SizeCheck, SizeCheckLine
from fhort.pom.models import GarmentType, POMMaster
from fhort.tasks.models import Customer, GarmentTypeItem, ModelTask, TaskType, TimerEntrada
from fhort.tasks.services_batec import SUP_PRESA, batec_escriptura


class BatecSobrePausadaTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TBP'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        self.user = get_user_model().objects.create(username='tecbatec')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CBP', nom='Client')
        gt = GarmentType.objects.create(codi_client='GTB', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_b', name='Item B')
        # El `code` ha de ser el REAL (`size_check`): el batec resol per slug, i un slug de
        # fantasia faria passar el test sense provar el camí que la pantalla fa servir.
        # El `code` ha de ser el REAL i el catàleg de tasques el sembra a cada schema: es
        # reutilitza el que hi ha (`get_or_create`), mai un de fantasia.
        self.tt, _ = TaskType.objects.get_or_create(
            code=SUP_PRESA, defaults={'name': 'Mesurar prenda', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='TBP-SS26-0001', codi_tenant='TBP', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item,
            nom_prenda='Peça', base_size_label='S')

    def _tasca(self, status):
        return ModelTask.objects.create(model=self.model, task_type=self.tt, order=0,
                                        status=status, origen='prevista')

    def _trams_oberts(self, task):
        return TimerEntrada.objects.filter(model_task=task, fi__isnull=True, actiu=True)

    # ── 1 i 2 · el cas del brief ───────────────────────────────────────────────────

    def test_escriure_sobre_una_PAUSADA_la_reobre_i_obre_tram(self):
        task = self._tasca('Paused')
        out = batec_escriptura(self.model, SUP_PRESA, self.prof)

        self.assertEqual(out['accio'], 'oberta', out)
        task.refresh_from_db()
        self.assertEqual(task.status, 'InProgress',
                         'escriure sobre una tasca pausada no l\'ha reoberta: tota la feina '
                         'que vingui després no la comptarà ningú')
        self.assertEqual(self._trams_oberts(task).count(), 1,
                         'la tasca s\'ha reobert però sense tram: el rellotge no corre')

    def test_el_tram_que_neix_escrivint_ja_porta_el_segell(self):
        """Sense `last_heartbeat`, el guard de tasca oblidada compta des de `inici` i pausa als
        30 minuts a qui hi estigui treballant. El cens de staging: 237 de 240 trams sense segell."""
        task = self._tasca('Paused')
        batec_escriptura(self.model, SUP_PRESA, self.prof)
        tram = self._trams_oberts(task).first()
        self.assertIsNotNone(tram)
        self.assertIsNotNone(tram.last_heartbeat,
                             'el tram ha nascut sense segell: el guard el pausarà als 30 min '
                             'comptant des de l\'obertura, escrigui qui escrigui')

    # ── 3 · el batec normal ────────────────────────────────────────────────────────

    def test_escriure_sobre_una_EN_CURS_renova_el_segell_i_no_obre_un_segon_tram(self):
        task = self._tasca('Paused')
        batec_escriptura(self.model, SUP_PRESA, self.prof)
        primer = self._trams_oberts(task).first()
        segell_inicial = primer.last_heartbeat

        out = batec_escriptura(self.model, SUP_PRESA, self.prof)
        self.assertEqual(out['accio'], 'renovat', out)
        self.assertEqual(self._trams_oberts(task).count(), 1, 'se n\'ha obert un de segon')
        primer.refresh_from_db()
        self.assertGreaterEqual(primer.last_heartbeat, segell_inicial)

    # ── 5 · el que NO ha de fer ────────────────────────────────────────────────────

    def test_una_tasca_DONE_no_es_reobre_escrivint(self):
        """Reobrir és un acte humà i té la seva porta. El batec no hi insisteix.

        Abans SÍ que la reobria: `ALLOWED` permet `Done → InProgress` (la rectificació existeix),
        i el batec s'hi colava — un PATCH sobre una cel·la d'una tasca ja tancada la tornava a
        obrir, li obria tram i li reiniciava el rellotge, en silenci. El guard d'albarà només
        aturava les ja facturades."""
        task = self._tasca('Done')
        out = batec_escriptura(self.model, SUP_PRESA, self.prof)
        self.assertEqual(out['accio'], 'acabada', out)
        task.refresh_from_db()
        self.assertEqual(task.status, 'Done')
        self.assertEqual(self._trams_oberts(task).count(), 0)

    # ── 4 · EL CAMÍ SENCER, per la porta HTTP de la pantalla ───────────────────────

    def test_la_porta_real_de_la_presa_bat(self):
        """`PATCH /size-check-lines/<id>/` és el que la pantalla fa a cada cel·la. El símptoma
        era d'una PANTALLA: provar només el servei deixaria fora la vista que l'ha de cridar."""
        from fhort.models_app.views_size_check import SizeCheckLineViewSet

        task = self._tasca('Paused')
        pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        check = SizeCheck.objects.create(model=self.model, estat='Obert')
        linia = SizeCheckLine.objects.create(size_check=check, pom=pom, valor_teoric=50.0)

        req = APIRequestFactory().patch('/x/', {'valor_real': 51.0}, format='json')
        force_authenticate(req, user=self.user)
        vista = SizeCheckLineViewSet.as_view({'patch': 'partial_update'})
        resp = vista(req, pk=linia.pk)
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', resp))

        task.refresh_from_db()
        self.assertEqual(task.status, 'InProgress',
                         'anotar una mesura no ha reobert la tasca de presa')
        tram = self._trams_oberts(task).first()
        self.assertIsNotNone(tram, 'anotar una mesura no ha obert cap tram')
        self.assertIsNotNone(tram.last_heartbeat, 'anotar una mesura no ha deixat segell')

    # ── Q1 · LA PAUSA I EL MODAL DE SORTIDA ───────────────────────────────────────

    def test_PAUSED_a_DONE_directe_segueix_prohibida_i_el_modal_no_hi_arriba(self):
        """El símptoma d'Agus era «Transició no permesa: Paused → Paused» sortint de la presa.

        ⚠️ LA MÀQUINA D'ESTATS NO ÉS LA SOLUCIÓ, i no s'ha tocat: `Paused → Done` segueix
        PROHIBIDA per decisió de Patró C (Agus, 28/07 · `test_stop_encadenat`), i `Paused →
        Paused` no ha existit mai. Obrir-les hauria estat canviar una decisió humana per tapar
        un defecte de front.

        On es tanca de debò és A LA SORTIDA: `ModelSheet.exitEdit` demana la tasca FRESCA i
        només obre el modal si segueix `InProgress` —l'únic estat des del qual les DUES opcions
        del modal són legals—. Aquest test fixa el fet de backend del qual depèn aquell criteri:
        des de `Paused` no n'hi ha cap de legal, o sigui que oferir-les seria oferir un error."""
        from fhort.tasks.services_c import ALLOWED

        self.assertEqual(ALLOWED['Paused'], {'InProgress'})
        self.assertNotIn('Done', ALLOWED['Paused'])
        self.assertNotIn('Paused', ALLOWED['Paused'])
        # I des d'InProgress, que és l'únic estat on el modal s'obre, totes dues ho són.
        self.assertTrue({'Paused', 'Done'} <= ALLOWED['InProgress'])
