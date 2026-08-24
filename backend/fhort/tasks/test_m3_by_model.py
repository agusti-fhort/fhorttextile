"""M3 · FASE 0b — EL BOARD PER-MODEL, FIXAT ABANS DE TOCAR-LO.

`by_model` (`/api/v1/model-task-items/by-model/`) i el seu `kanban_state` són, segons el cens
del 23/08, **un node sense cap test**: 200 línies que decideixen quins models entren al Board
del Dashboard, en quin ordre i a quina de les quatre columnes cauen — i cap garantia escrita.
M3 el toca (FASE 4: la 4a columna passa a ser ronda-aware i els models `acabat`/`jubilat` en
surten), i tocar un node sense xarxa és com es fabriquen les regressions que ningú no veu.

**Aquest fitxer s'escriu ABANS del canvi i ha de passar VERD contra el codi d'avui.** El que
fixa és el comportament ACTUAL, no el desitjat: cada test d'aquí que a FASE 4 hagi de canviar
es canvia amb el commit que el canvia, i llavors el diff diu exactament què s'ha mogut.

Convenció del repo: `python manage.py test fhort.tasks.test_m3_by_model` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, GarmentTypeItem, ModelTask, TaskType

URL = '/api/v1/model-task-items/by-model/'


class BaseByModel(TenantTestCase):
    """Banc mínim: un tenant, un tècnic que ho veu TOT (admin) i una fàbrica de models."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TBM'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='pmboard')
        # 🚨 EL ROL S'ESCRIU SOBRE `user.profile`, NO SOBRE UNA CÒPIA. El perfil el crea un
        # signal en néixer l'usuari, i `UserProfile.objects.get_or_create(user=...)` en torna
        # un objecte Python DIFERENT del que `user.profile` ja té cachejat. Escrivint-hi el rol,
        # la BD deia `admin` i la request seguia veient `technician` (cache del descriptor):
        # el scope es reduïa a «les meves tasques» i el board sortia BUIT, amb 200 i tot.
        UserProfile.objects.get_or_create(user=self.user)
        self.prof = self.user.profile
        # `admin` = totes les capacitats, i entre elles `view_team_tasks`: sense ella el
        # row-level scope (`scope_model_task_queryset`) només deixaria veure les tasques
        # pròpies i els comptadors d'aquest fitxer mesurarien la visibilitat, no el board.
        self.prof.rol_nom = 'admin'
        self.prof.save(update_fields=['rol_nom'])

        self.customer = Customer.objects.create(codi='CBM', nom='Client del board')
        gt = GarmentType.objects.create(codi_client='GTB', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_b', name='Item B')
        self.tt_pom, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.tt_fitxa, _ = TaskType.objects.get_or_create(
            code='tech_sheet', defaults={'name': 'Fitxa tècnica', 'fase': 'Dev. tècnic'})
        self._seq = 0
        self.Model = Model

    def _model(self, codi=None, **kw):
        self._seq += 1
        return self.Model.objects.create(
            codi_intern=codi or f'TBM-SS26-{self._seq:04d}', codi_tenant='TBM', any=2026,
            temporada='SS', sequencial=self._seq, customer=self.customer,
            garment_type_item=self.item, nom_prenda='Peça', **kw)

    def _tasca(self, model, tt=None, status='Pending', *, planificada=True, **kw):
        """Una tasca del model. `planificada=True` és el DEFAULT a posta: sense `planned_start`
        el model no entra al board (guard C4a), i cada test que no parli d'això vol el cas
        normal."""
        return ModelTask.objects.create(
            model=model, task_type=tt or self.tt_pom, status=status,
            planned_start=timezone.now() if planificada else None, **kw)

    def _client(self):
        c = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        c.force_authenticate(user=self.user)
        return c

    def _files(self, **params):
        resp = self._client().get(URL, params)
        self.assertEqual(resp.status_code, 200, resp.data)
        dades = resp.data
        return dades['results'] if isinstance(dades, dict) and 'results' in dades else dades

    def _fila(self, model, **params):
        for f in self._files(**params):
            if f['model_id'] == model.pk:
                return f
        return None


class KanbanStateTest(BaseByModel):
    """L'ESTAT-KANBAN DERIVAT — les quatre respostes d'avui i el seu ORDRE de precedència."""

    def test_in_progress_mana_sobre_tot(self):
        m = self._model()
        self._tasca(m, status='InProgress')
        self._tasca(m, self.tt_fitxa, status='Paused')
        self.assertEqual(self._fila(m)['kanban_state'], 'open')

    def test_paused_mana_sobre_pending(self):
        m = self._model()
        self._tasca(m, status='Paused')
        self._tasca(m, self.tt_fitxa, status='Pending')
        self.assertEqual(self._fila(m)['kanban_state'], 'paused')

    def test_pending_quan_no_hi_ha_res_viu_ni_pausat(self):
        m = self._model()
        self._tasca(m, status='Pending')
        self._tasca(m, self.tt_fitxa, status='Done')
        self.assertEqual(self._fila(m)['kanban_state'], 'pending')

    def test_done_nomes_quan_tot_es_done(self):
        """Avui `done` vol dir EXACTAMENT «cap tasca viva». Res més hi entra: ni ronda, ni
        entrega, ni estat del model. És el que FASE 4 canvia, i per això queda escrit."""
        m = self._model()
        self._tasca(m, status='Done')
        self._tasca(m, self.tt_fitxa, status='Done')
        self.assertEqual(self._fila(m, all='true')['kanban_state'], 'done')

    def test_els_comptadors_son_els_de_la_bd_no_una_mostra(self):
        m = self._model()
        self._tasca(m, status='Done')
        self._tasca(m, self.tt_fitxa, status='Pending')
        counts = self._fila(m)['counts']
        self.assertEqual(counts, {'pending': 1, 'paused': 0, 'in_progress': 0, 'done': 1})


class QuiEntraAlBoardTest(BaseByModel):
    """QUI HI ÉS I QUI NO — els dos guards que decideixen la població del board."""

    def test_un_model_sense_cap_tasca_planificada_no_hi_es(self):
        """C4a — «només els PLANIFICATS existeixen al Board»: sense `planned_start` enlloc,
        el model encara no ha entrat al pla."""
        m = self._model()
        self._tasca(m, status='Pending', planificada=False)
        self.assertIsNone(self._fila(m, all='true'))

    def test_per_defecte_els_models_tot_done_no_es_llisten(self):
        m = self._model()
        self._tasca(m, status='Done')
        self.assertIsNone(self._fila(m))
        self.assertIsNotNone(self._fila(m, all='true'))

    def test_un_model_sense_cap_tasca_no_hi_es_de_cap_manera(self):
        """L'agregació parteix de ModelTask: un model verge no hi surt ni amb `all=true`."""
        m = self._model()
        self.assertIsNone(self._fila(m, all='true'))


class ContracteDeFilaTest(BaseByModel):
    """LA FORMA DE LA FILA — el que el Dashboard llegeix de cada model."""

    def test_la_fila_porta_les_claus_que_el_dashboard_consumeix(self):
        m = self._model(prioritat=4, estat='Nou')
        self._tasca(m, status='Pending')
        fila = self._fila(m)
        for clau in ('model_id', 'model_codi', 'model_nom', 'fase', 'counts', 'kanban_state',
                     'prioritat', 'temporada', 'estat', 'data_objectiu', 'responsable_id',
                     'reanchored_by_start'):
            self.assertIn(clau, fila)
        self.assertEqual(fila['model_codi'], m.codi_intern)
        self.assertEqual(fila['prioritat'], 4)

    def test_la_fila_serveix_l_estat_del_model_tal_com_es(self):
        """`estat` viatja CRU des del model. Qui el llegeixi ha de saber que canvia amb FASE 1."""
        m = self._model()
        self._tasca(m, status='Pending')
        self.assertEqual(self._fila(m)['estat'], m.estat)


class FiltresIOrdreTest(BaseByModel):
    """FILTRES I ORDRE — el contracte que `ModelFilter` (font única, C1) hi posa."""

    def test_el_filtre_d_estat_del_model_es_exacte(self):
        """`?estat=` filtra pel valor EXACTE. Els codis surten de `Model.ESTAT_CHOICES` i no
        s'escriuen aquí: FASE 1 els canvia i un literal faria que aquest test provés el
        vocabulari vell contra el codi nou."""
        viu = self._model()
        self._tasca(viu, status='Pending')
        altres = [c for c, _ in self.Model.ESTAT_CHOICES if c != viu.estat]
        self.assertIsNotNone(self._fila(viu, estat=viu.estat))
        self.assertIsNone(self._fila(viu, estat=altres[0]))

    def test_un_valor_d_estat_invalid_s_ignora_i_no_filtra(self):
        """`.qs` d'un ModelFilter instanciat directament és LENIENT: un valor fora de les
        choices no peta i no filtra. És el comportament històric que `by_model` preserva a
        posta (v. la nota C1 a la vista), i queda escrit perquè no es perdi per accident."""
        viu = self._model()
        self._tasca(viu, status='Pending')
        self.assertIsNotNone(self._fila(viu, estat='__inexistent__'))

    def test_search_creua_codi_i_nom(self):
        m = self._model(codi='TBM-SS26-9999')
        self._tasca(m, status='Pending')
        self.assertIsNotNone(self._fila(m, search='9999'))
        self.assertIsNone(self._fila(m, search='no-hi-es'))

    def test_un_ordering_fora_de_la_whitelist_s_ignora_i_no_peta(self):
        m = self._model()
        self._tasca(m, status='Pending')
        self.assertIsNotNone(self._fila(m, ordering='__injeccio__'))
