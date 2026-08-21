"""J · CONSULTA ≠ TREBALL — mirar no és treballar, i entrar no endú ni reobre.

Les tres regles del tram, cadascuna amb el seu invariant:

  R1 — sense escriptura, cap modal: en sortir, la tasca torna sola i el tram no compta.
  R2 — el temps de consulta surt de `TRAMS_SANS`, que és el punt únic del qual pengen Welford,
       albarà, consum i tots els agregadors.
  R3 — `open-task` no reobre una Feta ni s'endú la d'un altre sense el gest explícit.

🔒 EL QUE AQUESTS TESTS GUARDEN SOBRETOT és el TERCER ESTAT de `consulta`. `None` vol dir «no
jutjat» —tot l'històric, i els trams que el desplegament enxampi oberts— i ha de seguir comptant
exactament com sempre. Amb `Q(consulta=False)` en comptes de `~Q(consulta=True)`, la clàusula de
R2 hauria buidat el Welford, l'albarà i el consum de cop, en silenci i sense migració.
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.pom.models import GarmentType
from fhort.tasks.models import (Customer, GarmentTypeItem, ModelTask, TaskType, TimerEntrada)
from fhort.tasks.services_c import (AUTO_CONSULTA, TransitionError, _close_open_timer,
                                    _open_timer, transition_task)
from fhort.tasks.services_i import TRAMS_SANS, tram_compta


class BaseJ(TenantTestCase):
    """Un model, dos tècnics i les tasques que calen. Cada test munta el seu estat i el llegeix
    de la BD, mai de la instància en memòria."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant J'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TJC'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.u1 = get_user_model().objects.create(username='j_tec1')
        # ⚠️ El signal `create_user_profile` ja crea el UserProfile dins d'un tenant: s'ADOPTA,
        # mai se'n crea un de segon (petaria amb `accounts_userprofile_user_id_key`).
        self.p1, _ = UserProfile.objects.get_or_create(user=self.u1)
        self.u2 = get_user_model().objects.create(username='j_tec2')
        self.p2, _ = UserProfile.objects.get_or_create(user=self.u2)
        customer = Customer.objects.create(codi='CJC', nom='Client J')
        gt = GarmentType.objects.create(codi_client='GTJ', nom_client='Família J', grup='TOPS')
        item = GarmentTypeItem.objects.create(garment_type=gt, code='item_j', name='Item J')
        self.tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        # L'ALLOW-LIST D'EXECUCIÓ, que és una porta ANTERIOR a la de J: `open_model_task_view`
        # rebutja amb 403 `task_type_not_allowed` qui no té el `code` a `permisos['tasks']`.
        # Sense això els tests de R3 no arriben mai al guard que volen provar. Es dona als DOS
        # tècnics: el cas «la tasca d'un altre» necessita que l'altre també la pugui executar.
        for u, p in ((self.u1, self.p1), (self.u2, self.p2)):
            p.permisos = {**(p.permisos or {}), 'tasks': ['pom']}
            p.save(update_fields=['permisos'])
            # ⚠️ `get_allowed_task_types` llegeix `user.profile`, i aquell accessor CACHEJA la
            # instància: sense invalidar-la, la vista veu el perfil d'abans del `save` i respon
            # 403 amb l'allow-list buida. Costa una tarda de trobar-ho.
            u.refresh_from_db()
            if hasattr(u, '_profile_cache'):
                del u._profile_cache
        self.model = Model.objects.create(
            codi_intern='TJC-SS26-0001', codi_tenant='TJC', any=2026, temporada='SS',
            sequencial=1, customer=customer, garment_type_item=item, nom_prenda='Peça J')

    def tasca(self, status='Pending', assignee=None):
        return ModelTask.objects.create(model=self.model, task_type=self.tt, order=0,
                                        status=status, origen='prevista', assignee=assignee)

    def api(self, user):
        c = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        c.force_authenticate(user=user)
        return c


class TestMarcaDEscriptura(BaseJ):
    """La marca i el veredicte: dos camps amb feines diferents."""

    def test_un_tram_nou_neix_jutjable_i_sense_escriptura(self):
        task = self.tasca()
        tram = _open_timer(task, self.p1)
        self.assertIs(tram.consulta, False, 'neix jutjable, no jutjat')
        self.assertIsNone(tram.escriptura_at, 'i encara no s\'hi ha escrit')

    def test_tancar_sense_escriptura_el_marca_consulta(self):
        task = self.tasca()
        _open_timer(task, self.p1)
        _close_open_timer(task)
        tram = task.timers.first()
        self.assertIs(tram.consulta, True)
        self.assertFalse(tram_compta(tram))
        self.assertFalse(task.timers.filter(TRAMS_SANS).exists(),
                         'i l\'ORM ha de dir el mateix que el mirall Python')

    def test_tancar_AMB_escriptura_no_el_marca(self):
        task = self.tasca()
        tram = _open_timer(task, self.p1)
        TimerEntrada.objects.filter(pk=tram.pk).update(escriptura_at=timezone.now())
        _close_open_timer(task)
        tram.refresh_from_db()
        self.assertIs(tram.consulta, False)
        self.assertTrue(tram_compta(tram))
        self.assertTrue(task.timers.filter(TRAMS_SANS).exists())

    def test_EL_TERCER_ESTAT_un_tram_LLEGAT_no_es_jutja_mai(self):
        """🔒 L'invariant que protegeix tot l'històric.

        Un tram amb `consulta=None` és d'abans del camp (o el desplegament el va enxampar obert):
        va néixer sense la marca d'escriptura i condemnar-lo per no tenir-la seria inventar-se
        que no s'hi va treballar. Al tancament NO se'l jutja, i segueix comptant.
        """
        task = self.tasca()
        TimerEntrada.objects.create(model_task=task, tecnic=self.p1, inici=timezone.now(),
                                    actiu=True, consulta=None)
        _close_open_timer(task)
        tram = task.timers.first()
        self.assertIsNone(tram.consulta, 'un llegat es queda llegat')
        self.assertTrue(tram_compta(tram), 'i compta com sempre')
        self.assertTrue(task.timers.filter(TRAMS_SANS).exists())

    def test_el_mirall_python_i_lORM_no_divergeixen(self):
        """`tram_compta` i `TRAMS_SANS` són germans declarats i cap gate els compara."""
        task = self.tasca()
        casos = [
            dict(consulta=None, minuts=10),          # llegat sa
            dict(consulta=False, minuts=10),         # feina
            dict(consulta=True, minuts=10),          # consulta
            dict(consulta=None, minuts=99999),       # fuita
            dict(consulta=False, minuts=99999),      # fuita amb feina
        ]
        for c in casos:
            TimerEntrada.objects.create(model_task=task, tecnic=self.p1,
                                        inici=timezone.now(), fi=timezone.now(),
                                        actiu=False, **c)
        sans_orm = set(task.timers.filter(TRAMS_SANS).values_list('pk', flat=True))
        sans_py = {t.pk for t in task.timers.all() if tram_compta(t)}
        self.assertEqual(sans_orm, sans_py)


class TestSortidaSenseEscriptura(BaseJ):
    """R1 — sortir sense haver escrit torna la tasca en silenci."""

    def test_reverteix_i_el_tram_no_compta(self):
        task = self.tasca(status='Paused', assignee=self.p1)
        transition_task(task, 'InProgress', self.p1)
        r = self.api(self.u1).post(f'/api/v1/model-tasks/{task.pk}/sortir-sense-escriptura/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIs(r.data['revertit'], True)
        task.refresh_from_db()
        self.assertEqual(task.status, 'Paused', 'torna on era')
        tram = task.timers.order_by('-inici').first()
        self.assertIs(tram.consulta, True)
        self.assertFalse(tram_compta(tram))

    def test_la_transicio_va_MARCADA_com_a_tecnica(self):
        """La llei del log: `auto` null és un gest del tècnic, un slug és el sistema. Aquí el
        tècnic no ha decidit pausar res — ha sortit d'una pantalla on no havia tocat res."""
        task = self.tasca(status='Paused', assignee=self.p1)
        transition_task(task, 'InProgress', self.p1)
        self.api(self.u1).post(f'/api/v1/model-tasks/{task.pk}/sortir-sense-escriptura/')
        t = task.transitions.order_by('-id').first()
        self.assertEqual((t.from_status, t.to_status), ('InProgress', 'Paused'))
        self.assertEqual(t.auto, 'consulta_sense_escriptura')

    def test_amb_escriptura_NO_reverteix(self):
        task = self.tasca(status='Paused', assignee=self.p1)
        transition_task(task, 'InProgress', self.p1)
        TimerEntrada.objects.filter(model_task=task, fi__isnull=True).update(
            escriptura_at=timezone.now())
        r = self.api(self.u1).post(f'/api/v1/model-tasks/{task.pk}/sortir-sense-escriptura/')
        self.assertIs(r.data['revertit'], False)
        self.assertEqual(r.data['motiu'], 'amb_escriptura')
        task.refresh_from_db()
        self.assertEqual(task.status, 'InProgress', 'qui ha treballat decideix ell')

    def test_el_tram_dun_ALTRE_no_es_pot_tancar_des_daqui(self):
        """El rellotge de cadascú és seu: la mateixa llei que el batec."""
        task = self.tasca(status='Paused', assignee=self.p2)
        transition_task(task, 'InProgress', self.p2)
        r = self.api(self.u1).post(f'/api/v1/model-tasks/{task.pk}/sortir-sense-escriptura/')
        self.assertIs(r.data['revertit'], False)
        self.assertEqual(r.data['motiu'], 'sense_tram_meu')
        task.refresh_from_db()
        self.assertEqual(task.status, 'InProgress')

    def test_el_serializer_diu_si_shi_ha_escrit(self):
        task = self.tasca(status='Paused', assignee=self.p1)
        cli = self.api(self.u1)
        d = cli.get(f'/api/v1/model-task-items/{task.pk}/').data
        self.assertIsNone(d['sessio_amb_escriptura'], 'sense tram obert, no hi ha resposta')
        transition_task(task, 'InProgress', self.p1)
        d = cli.get(f'/api/v1/model-task-items/{task.pk}/').data
        self.assertIs(d['sessio_amb_escriptura'], False)
        TimerEntrada.objects.filter(model_task=task, fi__isnull=True).update(
            escriptura_at=timezone.now())
        d = cli.get(f'/api/v1/model-task-items/{task.pk}/').data
        self.assertIs(d['sessio_amb_escriptura'], True)


class TestEntrarNoEnduNiReobre(BaseJ):
    """R3 — el gest explícit, o 409 amb codi."""

    def obrir(self, cos=None):
        return self.api(self.u1).post(f'/api/v1/models/{self.model.pk}/open-task/',
                                      {'code': 'pom', **(cos or {})}, format='json')

    def test_una_FETA_no_es_reobre_per_entrada(self):
        task = self.tasca(status='Done', assignee=self.p1)
        r = self.obrir()
        self.assertEqual(r.status_code, 409, r.data)
        self.assertEqual(r.data['code'], 'tasca_feta')
        task.refresh_from_db()
        self.assertEqual(task.status, 'Done', 'i segueix feta')

    def test_amb_el_GEST_si_que_es_reobre(self):
        task = self.tasca(status='Done', assignee=self.p1)
        r = self.obrir({'reobrir': True})
        self.assertEqual(r.status_code, 200, r.data)
        task.refresh_from_db()
        self.assertEqual(task.status, 'InProgress')

    def test_la_dun_ALTRE_no_sendu_per_entrada(self):
        task = self.tasca(status='Paused', assignee=self.p2)
        transition_task(task, 'InProgress', self.p2)
        r = self.obrir()
        self.assertEqual(r.status_code, 409, r.data)
        self.assertEqual(r.data['code'], 'tasca_dun_altre')
        task.refresh_from_db()
        self.assertEqual(task.assignee_id, self.p2.pk, "NO se l'ha enduta")

    def test_amb_el_GEST_si_que_sendu(self):
        task = self.tasca(status='Paused', assignee=self.p2)
        transition_task(task, 'InProgress', self.p2)
        r = self.obrir({'handoff': True})
        self.assertEqual(r.status_code, 200, r.data)
        task.refresh_from_db()
        self.assertEqual(task.assignee_id, self.p1.pk)

    def test_el_cas_normal_no_demana_res(self):
        """⚠️ LA REGLA D'OR: R3 no pot posar fricció on no hi ha paret. La meva tasca pausada
        s'obre com sempre, sense cap gest."""
        task = self.tasca(status='Paused', assignee=self.p1)
        r = self.obrir()
        self.assertEqual(r.status_code, 200, r.data)
        task.refresh_from_db()
        self.assertEqual(task.status, 'InProgress')

    def test_ALBARANADA_mana_sobre_FETA(self):
        """Una tasca albaranada ha de dir que ho ESTÀ, i no «ja està feta»: són dues converses
        diferents i la segona amaga la primera. Mateixa precedència que `caraObrirTasca`."""
        from fhort.commerce.models import DeliveryNote, DeliveryNoteLine
        task = self.tasca(status='Done', assignee=self.p1)
        try:
            nota = DeliveryNote.objects.create(status='ISSUED')
            DeliveryNoteLine.objects.create(delivery_note=nota, model_task=task)
        except Exception:
            self.skipTest('DeliveryNote demana context comercial en aquest tenant')
        r = self.obrir()
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['code'], 'tasca_albaranada')


class TestTornadaExactaAPending(BaseJ):
    """J-bis · PEÇA 1 — `InProgress → Pending` existeix, i **només pel camí de consulta**.

    🔒 L'INVARIANT D'AQUESTA CLASSE ÉS QUE SER A `ALLOWED` NO ÉS SER PERMESA. La transició hi és
    perquè el camí de tornada d'una consulta la necessita; el guard demana les dues condicions
    alhora —marca `auto` i tram sense escriptura— i cap gest humà en porta cap de les dues.
    """

    def test_una_PENDING_consultada_torna_a_PENDING(self):
        task = self.tasca(status='Pending', assignee=self.p1)
        transition_task(task, 'InProgress', self.p1)
        task.refresh_from_db()
        self.assertIsNotNone(task.started_at, "l'entrada l'ha posat")
        r = self.api(self.u1).post(f'/api/v1/model-tasks/{task.pk}/sortir-sense-escriptura/')
        self.assertIs(r.data['revertit'], True, r.data)
        self.assertEqual(r.data['estat_entrada'], 'Pending')
        task.refresh_from_db()
        self.assertEqual(task.status, 'Pending', 'exactament on era')
        self.assertIsNone(task.started_at,
                          'i «exactament» inclou el started_at: una Pending no s\'ha començat mai')

    def test_una_PAUSED_consultada_segueix_tornant_a_PAUSED(self):
        """La peça 1 no canvia el cas que J ja resolia."""
        task = self.tasca(status='Paused', assignee=self.p1)
        transition_task(task, 'InProgress', self.p1)
        r = self.api(self.u1).post(f'/api/v1/model-tasks/{task.pk}/sortir-sense-escriptura/')
        self.assertEqual(r.data['estat_entrada'], 'Paused')
        task.refresh_from_db()
        self.assertEqual(task.status, 'Paused')

    # ── L'ALTRE SENTIT: el guard ─────────────────────────────────────────────
    def test_un_transition_task_HUMA_segueix_REBUTJAT(self):
        """Sense marca `auto`, `InProgress → Pending` és exactament tan il·legal com abans."""
        task = self.tasca(status='Pending', assignee=self.p1)
        transition_task(task, 'InProgress', self.p1)
        with self.assertRaises(TransitionError):
            transition_task(task, 'Pending', self.p1)
        task.refresh_from_db()
        self.assertEqual(task.status, 'InProgress', 'i no s\'ha mogut')

    def test_amb_una_marca_auto_QUALSEVOL_tambe_es_rebutja(self):
        """La clau és AQUESTA marca, no «portar-ne una»: un guard que passés amb qualsevol slug
        deixaria que `guard_30min` o `exclusio_inprogress` hi caiguessin per accident."""
        task = self.tasca(status='Pending', assignee=self.p1)
        transition_task(task, 'InProgress', self.p1)
        with self.assertRaises(TransitionError):
            transition_task(task, 'Pending', self.p1, auto='guard_30min')
        task.refresh_from_db()
        self.assertEqual(task.status, 'InProgress')

    def test_amb_la_marca_pero_AMB_ESCRIPTURA_es_rebutja(self):
        """La marca sola seria una paraula: qualsevol cridador podria escriure-la. El que no es
        pot fingir des de fora és `escriptura_at`, que només estampa `batec_escriptura`."""
        task = self.tasca(status='Pending', assignee=self.p1)
        transition_task(task, 'InProgress', self.p1)
        TimerEntrada.objects.filter(model_task=task, fi__isnull=True).update(
            escriptura_at=timezone.now())
        with self.assertRaises(TransitionError):
            transition_task(task, 'Pending', self.p1, auto=AUTO_CONSULTA)
        task.refresh_from_db()
        self.assertEqual(task.status, 'InProgress', 'qui ha treballat no torna a Pending')

    def test_la_resta_de_la_maquina_no_es_mou(self):
        """Cap altra transició s'ha obert de rebot."""
        # UNA sola tasca, reposicionada a mà: `uniq_prevista_model_tasktype` no en deixa dues
        # `prevista` del mateix (model, task_type), i aquí el que es prova és la TAULA, no la fila.
        task = self.tasca(status='Pending', assignee=self.p1)
        for frm, to in (('Pending', 'Paused'), ('Pending', 'Done'), ('Paused', 'Done'),
                        ('Paused', 'Pending'), ('Done', 'Paused'), ('Done', 'Pending')):
            ModelTask.objects.filter(pk=task.pk).update(status=frm)
            task.refresh_from_db()
            with self.assertRaises(TransitionError, msg=f'{frm} → {to}'):
                transition_task(task, to, self.p1, auto=AUTO_CONSULTA)

