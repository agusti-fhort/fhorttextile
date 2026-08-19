"""F1.5 · D-6 / D-7 / D-8 — L'EXCLUSIÓ ANCORADA A QUI TREBALLA, I EL RELLEU VISIBLE.

L'exclusió «una sola InProgress per tècnic» existia, però mirava `assignee` (camp de
PLANIFICACIÓ) mentre el rellotge s'ancora a `TimerEntrada.tecnic` (qui hi és de debò). Com que
`transition_task` només escriu `assignee` si és `None`, els dos eixos divergien sols i la
invariant queia sempre que actor ≠ assignat. Hi ha el cas real a la BD: timers 116 i 117, tècnic
1, 24/06, solapats — 122 minuts i 0 minuts imputats en paral·lel.

I el relleu (endur-se una tasca d'un altre) reassignava sense tancar el tram de l'anterior: el
rellotge seguia corrent per a qui ja no hi era, el nou treballava sense timer propi, i al log no
en quedava ni una fila.

D-8 hi entra per la porta del darrere: **mateix model sí, mateixa tasca mai**. No es construeix
cap mutex de model — la garantia surt sola del fet que un tram obert és d'un sol tècnic.

Convenció del repo: `python manage.py test fhort.tasks.test_exclusio_handoff` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import (Customer, GarmentTypeItem, ModelTask, TaskTransition, TaskType,
                                TimerEntrada)
from fhort.tasks.services_c import traspassa_tram, transition_task


class ExclusioHandoffTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TEX'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.a_user = get_user_model().objects.create(username='tecA')
        self.a, _ = UserProfile.objects.get_or_create(user=self.a_user)
        self.b_user = get_user_model().objects.create(username='tecB')
        self.b, _ = UserProfile.objects.get_or_create(user=self.b_user)
        self.customer = Customer.objects.create(codi='CEX', nom='Client de prova')
        gt = GarmentType.objects.create(codi_client='GTE', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_e', name='Item E')
        self.tt1 = TaskType.objects.create(code='tt_ex_1', name='TT 1', fase='Dev. tècnic')
        self.tt2 = TaskType.objects.create(code='tt_ex_2', name='TT 2', fase='Dev. tècnic')
        self.Model = Model
        self._seq = 0

    def _model(self):
        self._seq += 1
        return self.Model.objects.create(
            codi_intern=f'TEX-SS26-{self._seq:04d}', codi_tenant='TEX', any=2026, temporada='SS',
            sequencial=self._seq, customer=self.customer, garment_type_item=self.item,
            nom_prenda='Peça')

    def _tasca(self, model=None, tt=None, assignee=None):
        return ModelTask.objects.create(model=model or self._model(), task_type=tt or self.tt1,
                                        order=0, status='Pending', assignee=assignee)

    def _trams_oberts(self, prof):
        return TimerEntrada.objects.filter(tecnic=prof, fi__isnull=True, actiu=True)

    # ── D-6 · l'exclusió mira qui treballa ───────────────────────────────────
    def test_un_tecnic_dos_models_nomes_te_un_tram_obert(self):
        t1, t2 = self._tasca(), self._tasca()
        transition_task(t1, 'InProgress', self.a)
        transition_task(t2, 'InProgress', self.a)
        t1.refresh_from_db()
        self.assertEqual(self._trams_oberts(self.a).count(), 1)
        self.assertEqual(t1.status, 'Paused')

    def test_EL_CAS_REAL_actor_diferent_d_assignee_ja_no_esquiva_l_exclusio(self):
        """Timers 116/117: la tasca tenia `assignee` = un altre mentre el tècnic 1 hi treballava,
        de manera que `filter(assignee=...)` no la veia i el tècnic acabava amb dos trams."""
        primera = self._tasca(assignee=self.b)       # assignada a B...
        transition_task(primera, 'InProgress', self.a)   # ...però qui hi treballa és A
        primera.refresh_from_db()
        self.assertEqual(primera.assignee, self.b, 'premissa: assignee segueix sent B')
        self.assertEqual(self._trams_oberts(self.a).count(), 1)

        segona = self._tasca()
        transition_task(segona, 'InProgress', self.a)

        self.assertEqual(self._trams_oberts(self.a).count(), 1,
                         'dos trams oberts del mateix tècnic: la invariant ha tornat a caure')
        primera.refresh_from_db()
        self.assertEqual(primera.status, 'Paused')

    def test_l_exclusio_marca_la_pausa_com_a_automatica(self):
        t1, t2 = self._tasca(), self._tasca()
        transition_task(t1, 'InProgress', self.a)
        transition_task(t2, 'InProgress', self.a)
        self.assertTrue(TaskTransition.objects
                        .filter(model_task=t1, auto='exclusio_inprogress').exists())

    # ── D-8 · mateix model sí, mateixa tasca mai ─────────────────────────────
    def test_dos_tecnics_al_mateix_model_en_tasques_diferents_conviuen(self):
        model = self._model()
        ta = self._tasca(model=model, tt=self.tt1)
        tb = self._tasca(model=model, tt=self.tt2)
        transition_task(ta, 'InProgress', self.a)
        transition_task(tb, 'InProgress', self.b)
        ta.refresh_from_db(); tb.refresh_from_db()
        self.assertEqual(ta.status, 'InProgress')
        self.assertEqual(tb.status, 'InProgress')
        self.assertEqual(self._trams_oberts(self.a).count(), 1)
        self.assertEqual(self._trams_oberts(self.b).count(), 1)

    def test_una_tasca_mai_te_dos_trams_oberts(self):
        task = self._tasca()
        transition_task(task, 'InProgress', self.a)
        traspassa_tram(task, self.b)
        self.assertEqual(
            TimerEntrada.objects.filter(model_task=task, fi__isnull=True, actiu=True).count(), 1)

    # ── D-7 · el relleu és conscient ─────────────────────────────────────────
    def test_el_handoff_tanca_el_tram_de_l_anterior(self):
        task = self._tasca()
        transition_task(task, 'InProgress', self.a)
        tram_a = TimerEntrada.objects.get(model_task=task, tecnic=self.a)

        traspassa_tram(task, self.b)

        tram_a.refresh_from_db()
        self.assertIsNotNone(tram_a.fi, 'el tram de A ha quedat obert i li segueix imputant temps')
        self.assertFalse(tram_a.actiu)

    def test_el_handoff_obre_tram_al_nou(self):
        task = self._tasca()
        transition_task(task, 'InProgress', self.a)
        traspassa_tram(task, self.b)
        self.assertEqual(self._trams_oberts(self.b).filter(model_task=task).count(), 1)

    def test_el_handoff_deixa_fila_al_log(self):
        """El relleu era l'únic moviment del sistema que no deixava rastre."""
        task = self._tasca()
        transition_task(task, 'InProgress', self.a)
        traspassa_tram(task, self.b)
        fila = TaskTransition.objects.filter(model_task=task, auto='handoff').first()
        self.assertIsNotNone(fila)
        self.assertEqual(fila.by, self.b)
        self.assertEqual(fila.from_status, fila.to_status, "el relleu no canvia l'estat")

    def test_el_handoff_a_un_mateix_es_no_op(self):
        task = self._tasca()
        transition_task(task, 'InProgress', self.a)
        self.assertIsNone(traspassa_tram(task, self.a))
        self.assertFalse(TaskTransition.objects.filter(model_task=task, auto='handoff').exists())

    def test_handoff_sobre_tasca_sense_tram_no_escriu_log(self):
        """Agafar una tasca aturada no és un relleu: no hi ha rellotge de ningú per traspassar."""
        task = self._tasca()
        traspassa_tram(task, self.b)
        self.assertFalse(TaskTransition.objects.filter(model_task=task, auto='handoff').exists())

    # ── V3 (06/08) · D-6 TAMBÉ PER LA PORTA DEL RELLEU ───────────────────────
    # L'exclusió es va tancar a `transition_task`, i el relleu no hi passa: `claim` i la branca
    # de handoff d'`open-task` criden `traspassa_tram` SENSE transició —correctament, perquè el
    # relleu no canvia l'estat— i `_open_timer` només tanca els trams D'AQUESTA TASCA. Els cinc
    # tests de handoff d'aquí sobre parteixen sempre de B SENSE feina pròpia, i per això el forat
    # va sobreviure. Aquests tres parteixen de B ja treballant.

    def test_EL_FORAT_qui_fa_el_relleu_amb_feina_oberta_no_acaba_amb_dos_trams(self):
        """🔴 EL CAS. B treballa a la seva tasca i es queda la d'A: si l'exclusió no val per al
        relleu, B acaba amb DOS trams oberts i el temps torna a ser imputable a dos llocs
        alhora — exactament el mal que F1.5 va matar, per l'altra porta."""
        seva = self._tasca()
        transition_task(seva, 'InProgress', self.b)
        de_l_altre = self._tasca()
        transition_task(de_l_altre, 'InProgress', self.a)

        traspassa_tram(de_l_altre, self.b)

        self.assertEqual(self._trams_oberts(self.b).count(), 1,
                         'B ha quedat amb dos trams oberts: la invariant cau pel relleu')
        self.assertEqual(self._trams_oberts(self.b).get().model_task_id, de_l_altre.pk)
        seva.refresh_from_db(); de_l_altre.refresh_from_db()
        self.assertEqual(seva.status, 'Paused')
        self.assertEqual(de_l_altre.status, 'InProgress', "el relleu no canvia l'estat")

    def test_la_pausa_del_relleu_va_marcada_i_no_es_confon_amb_el_handoff(self):
        """Dos fets diferents, dues files diferents: la feina que B deixa queda marcada
        `exclusio_inprogress` (no és un gest seu sobre aquella tasca) i el relleu manté la seva
        `handoff`. Si es confonguessin, el log no podria dir per què va parar la primera."""
        seva = self._tasca()
        transition_task(seva, 'InProgress', self.b)
        de_l_altre = self._tasca()
        transition_task(de_l_altre, 'InProgress', self.a)

        traspassa_tram(de_l_altre, self.b)

        pausa = TaskTransition.objects.filter(model_task=seva, auto='exclusio_inprogress').get()
        self.assertEqual(pausa.by, self.b)
        self.assertEqual((pausa.from_status, pausa.to_status), ('InProgress', 'Paused'))
        relleu = TaskTransition.objects.filter(model_task=de_l_altre, auto='handoff').get()
        self.assertEqual(relleu.by, self.b)
        self.assertFalse(TaskTransition.objects
                         .filter(model_task=de_l_altre, auto='exclusio_inprogress').exists())

    def test_el_relleu_no_toca_la_feina_d_ALTRES_tecnics(self):
        """L'exclusió és PER TÈCNIC: que B es quedi una tasca no pot aturar el que fa C en una
        altra. D-8 segueix valent — el que no es pot és tenir-ne dues un mateix."""
        de_c = self._tasca()
        transition_task(de_c, 'InProgress', self.a)   # A fa de tercer tècnic aquí
        objectiu = self._tasca()

        traspassa_tram(objectiu, self.b)

        de_c.refresh_from_db()
        self.assertEqual(de_c.status, 'InProgress')
        self.assertEqual(self._trams_oberts(self.a).count(), 1)
