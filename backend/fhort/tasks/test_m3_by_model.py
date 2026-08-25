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
from fhort.tasks.services_c import transition_task

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

    def _amb_r1(self, model):
        """Dona al model la seva R1 **com ho fa el producte** i hi lliga la feina que ja té.

        M5 · retroactiu — des del 25/08 **no existeix cap model amb feina i sense volta**: el
        retroactiu els va donar la R1 a tots i `ronda_del_gest` la crea al primer gest. Un test
        que fabriqui aquella forma mesura una població que el sistema ja no pot produir, i per
        això els casos que parlen de la VOLTA passen per aquí.

        (Els de `KanbanStateTest` que només mesuren la precedència de la feina viva no hi passen:
        aquella branca no consulta la volta i el fixture no els canvia la resposta. V. la 🚩 de
        l'acta d'M5-DIA.)
        """
        from fhort.tasks.services_r import ronda_del_gest
        ronda = ronda_del_gest(model)
        model.model_tasks.filter(ronda__isnull=True).update(ronda=ronda)
        return ronda

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

    def test_cap_tasca_viva_JA_NO_es_done_per_si_sol(self):
        """🔄 **LA PREMISSA D'AQUEST TEST S'HA INVERTIT, i és el que FASE 4 va canviar.**

        Deia «`done` vol dir EXACTAMENT cap tasca viva», i va seguir sent cert un temps més del
        que tocava: la CODA d'M3 va fer de `done` un **FET D'ENTREGA**, però va conservar la
        lectura vella per als models LLEGATS (sense cap volta) —i el fixture d'aquest test era
        justament un d'aquells. El retroactiu de M5 ha buidat aquella població i la branca s'ha
        retirat, o sigui que ara el test pot dir la llei sencera:

        **cap tasca viva NO és `done`.** Mana la volta, i una volta OBERTA vol el gest humà
        d'entregar. Qui mesura el `done` de debò és
        `QuiEntraAlBoardTest.test_volta_ENTREGADA_i_cap_oberta_ES_la_quarta_columna`.
        """
        m = self._model()
        self._tasca(m, status='Done')
        self._tasca(m, self.tt_fitxa, status='Done')
        self._amb_r1(m)                                  # la forma REAL: tot model amb feina en té
        self.assertEqual(self._fila(m, all='true')['kanban_state'], 'pending')

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


class BoardRondaAwareTest(BaseByModel):
    """M3 · FASE 4 + CODA — el board després del canvi: qui en surt, què diu cada fila i, des de
    la CODA, **a quina columna cau cadascú**.

    🚨 **I AQUELL «ELS 14 DE FASE 0b SEGUEIXEN VERDS» NO ERA CERT PER SEMPRE.** L'acta d'M3 va
    declarar que retirar l'excepció pre-llei era «una línia i un test»; en retirar-la (M5) en van
    caure **TRES**, i el tercer era precisament un dels 14: `test_done_nomes_quan_tot_es_done`,
    que fabricava un model sense volta i esperava `done`. Els altres 13 no consulten la volta i
    segueixen intactes. La lliçó queda escrita aquí perquè no s'hagi de tornar a descobrir."""

    def setUp(self):
        super().setUp()
        from fhort.accounts.models import UserProfile   # noqa: F401  (ja creat a la base)
        from fhort.tasks.services_r import obrir_ronda
        self._obrir_ronda = obrir_ronda

    def _acaba(self, model, motiu='acabat'):
        from fhort.models_app.services_cicle import tancar_model
        tancar_model(model, motiu=motiu, profile=self.prof)

    # ── QUI HI ÉS ────────────────────────────────────────────────────────────
    def test_un_model_ACABAT_surt_del_board(self):
        m = self._model()
        self._tasca(m, status='Pending')
        self.assertIsNotNone(self._fila(m))
        self._acaba(m)
        self.assertIsNone(self._fila(m, all='true'))

    def test_un_model_JUBILAT_tambe_en_surt(self):
        from fhort.models_app.services_cicle import jubilar_model
        m = self._model()
        self._tasca(m, status='Pending')
        self._acaba(m)
        jubilar_model(m, profile=self.prof)
        self.assertIsNone(self._fila(m, all='true'))

    def test_pero_es_poden_demanar_EXPLICITAMENT(self):
        """L'exclusió és el DEFAULT, no una paret: `?estat=acabat` els torna a ensenyar."""
        m = self._model()
        self._tasca(m, status='Pending')
        self._acaba(m)
        self.assertIsNotNone(self._fila(m, all='true', estat='acabat'))

    def test_un_estat_MAL_ESCRIT_no_obre_el_board_als_acabats(self):
        """El filtre és lenient amb un valor invàlid (l'ignora); l'exclusió, no: si un typo
        obrís el board als acabats, l'amagatall dependria de saber escriure."""
        m = self._model()
        self._tasca(m, status='Pending')
        self._acaba(m)
        self.assertIsNone(self._fila(m, all='true', estat='acabatt'))

    def test_reobrir_el_torna_al_board(self):
        from fhort.models_app.services_cicle import reobrir_model
        m = self._model()
        self._tasca(m, status='Pending')
        self._acaba(m)
        reobrir_model(m, profile=self.prof)
        self.assertIsNotNone(self._fila(m))

    # ── QUÈ DIU LA FILA ──────────────────────────────────────────────────────
    def test_sense_cap_volta_la_fila_ho_diu_amb_null(self):
        """Tot model llegat: `ronda` null no és una omissió, és «aquest model no en té»."""
        m = self._model()
        self._tasca(m, status='Pending')
        self.assertIsNone(self._fila(m)['ronda'])

    def test_amb_volta_oberta_la_fila_diu_seq_i_oberta(self):
        m = self._model()
        self._tasca(m, status='Pending')
        r = self._obrir_ronda(m, 'nova_mostra', ['pom'], profile=self.prof)
        fila = self._fila(m)
        self.assertEqual(fila['ronda'], {'seq': r.seq, 'estat': 'oberta'})

    def test_una_volta_ENTREGADA_es_distingeix_d_una_de_tancada_a_seques(self):
        """Les tres que la BD pot donar. Pintar «entregada» una volta tancada sense entrega
        seria mentir; és la mateixa distinció que M2 ja fa a la fitxa."""
        from fhort.tasks.services_r import informar_entrega, tancar_ronda
        entregat = self._model()
        self._tasca(entregat, status='Pending')
        r1 = self._obrir_ronda(entregat, 'nova_mostra', ['pom'], profile=self.prof)
        informar_entrega(r1, destinatari='Brumà SL', profile=self.prof)

        tancat = self._model()
        self._tasca(tancat, status='Pending')
        r2 = self._obrir_ronda(tancat, 'nova_mostra', ['pom'], profile=self.prof)
        tancar_ronda(r2, profile=self.prof)

        self.assertEqual(self._fila(entregat, all='true')['ronda']['estat'], 'entregada')
        self.assertEqual(self._fila(tancat, all='true')['ronda']['estat'], 'tancada')

    def test_la_fila_parla_de_la_DARRERA_volta_no_de_la_primera(self):
        from fhort.tasks.services_r import informar_entrega
        m = self._model()
        self._tasca(m, status='Pending')
        r1 = self._obrir_ronda(m, 'nova_mostra', ['pom'], profile=self.prof)
        informar_entrega(r1, destinatari='X', profile=self.prof)
        r2 = self._obrir_ronda(m, 'nova_mostra', ['pom'], profile=self.prof)
        fila = self._fila(m)
        self.assertEqual(fila['ronda'], {'seq': r2.seq, 'estat': 'oberta'})


class QuatreColumnesCodaTest(BaseByModel):
    """🔒 M3 · CODA — **LA 4a COLUMNA ÉS UN FET D'ENTREGA.**

    Els casos límit són els de la captura `m3_d1_board.png`, que va ser justament la que va
    ensenyar el problema: un model a «Entregats» amb el xip `R1 · volta oberta`."""

    def setUp(self):
        super().setUp()
        from fhort.models_app.services_cicle import tancar_model
        from fhort.tasks.services_r import informar_entrega, obrir_ronda, tancar_ronda
        self._obrir_ronda, self._entrega = obrir_ronda, informar_entrega
        self._tancar_ronda, self._tancar_model = tancar_ronda, tancar_model

    def _model_tot_done(self):
        """Un model amb feina, tota FETA. Cap comptador viu: la volta és qui decidirà."""
        m = self._model()
        self._tasca(m, status='Done')
        return m

    def _estat(self, model, **params):
        fila = self._fila(model, all='true', **params)
        return None if fila is None else fila['kanban_state']

    def test_volta_ENTREGADA_i_cap_oberta_ES_la_quarta_columna(self):
        m = self._model_tot_done()
        r = self._obrir_ronda(m, 'nova_mostra', ['pom'], profile=self.prof)
        for t in r.tasques.all():                       # la volta, treballada i acabada
            transition_task(t, 'InProgress', self.prof)
            transition_task(t, 'Done', self.prof)
        self._entrega(r, destinatari='Brumà SL', profile=self.prof)   # …i ENVIADA (tanca la volta)
        self.assertEqual(self._estat(m), 'done')
        self.assertEqual(self._fila(m, all='true')['ronda']['estat'], 'entregada')

    def test_tot_done_amb_la_volta_OBERTA_torna_a_les_columnes_de_feina(self):
        """🚨 EL CAS DE LA CAPTURA. Feina acabada i no enviada **és feina nostra**: el gest que
        falta és humà (entregar), no una tasca. El senyal de que ja es pot enviar el porta el
        badge LLIURABLE, que existeix des d'F2.7."""
        m = self._model_tot_done()
        r = self._obrir_ronda(m, 'nova_mostra', ['pom'], profile=self.prof)
        for t in r.tasques.all():
            transition_task(t, 'InProgress', self.prof)
            transition_task(t, 'Done', self.prof)
        fila = self._fila(m, all='true')
        self.assertEqual(fila['counts'], {'pending': 0, 'paused': 0, 'in_progress': 0, 'done': 2})
        self.assertEqual(fila['kanban_state'], 'pending')      # ← abans de la CODA: 'done'
        self.assertEqual(fila['ronda']['estat'], 'oberta')

    def test_una_volta_TANCADA_SENSE_entrega_tampoc_hi_entra(self):
        """Tancada ≠ entregada. Una volta que es va tancar sense declarar cap enviament no és
        un fet d'entrega, i el model segueix demanant un gest."""
        m = self._model_tot_done()
        r = self._obrir_ronda(m, 'nova_mostra', ['pom'], profile=self.prof)
        self._tancar_ronda(r, profile=self.prof)
        fila = self._fila(m, all='true')
        self.assertEqual(fila['kanban_state'], 'pending')
        self.assertEqual(fila['ronda']['estat'], 'tancada')

    def test_M5_un_model_amb_feina_SEMPRE_te_volta_i_mai_cau_a_done_per_defecte(self):
        """✅ **L'EXCEPCIÓ PRE-LLEI S'HA RETIRAT (M5, 25/08)**, i aquest test ocupa el lloc dels
        dos que la mesuraven (`test_EXCEPCIO_PRE_LLEI_…` i `test_i_l_excepcio_s_APAGA_SOLA_…`).

        Mentre va durar, un model sense cap `Ronda` conservava la lectura vella (tot Done → 4a
        columna). El retroactiu li ha donat la R1 a tot model amb feina —població pre-llei = 0,
        verificada per SQL— i la branca ja no trobava ningú. El que es guarda ara és la llei que
        queda: **amb la volta oberta i sense entrega, tot Done és `pending`, no `done`.**
        """
        m = self._model_tot_done()
        self._amb_r1(m)
        fila = self._fila(m, all='true')
        self.assertIsNotNone(fila['ronda'], 'M5: cap model amb feina es queda sense volta')
        self.assertEqual(fila['ronda']['estat'], 'oberta')
        self.assertEqual(fila['kanban_state'], 'pending')

    def test_la_feina_viva_segueix_manant_sobre_la_volta(self):
        """La precedència no s'ha tocat: una volta entregada no pinta «entregat» un model on
        algú està treballant ara mateix (feina nascuda al buit, posterior a l'entrega)."""
        m = self._model_tot_done()
        r = self._obrir_ronda(m, 'nova_mostra', ['pom'], profile=self.prof)
        for t in r.tasques.all():
            transition_task(t, 'InProgress', self.prof)
            transition_task(t, 'Done', self.prof)
        self._entrega(r, destinatari='Brumà SL', profile=self.prof)
        nova = self._tasca(m, self.tt_fitxa, status='Pending')       # feina del BUIT
        self.assertEqual(self._estat(m), 'pending')
        transition_task(nova, 'InProgress', self.prof)
        self.assertEqual(self._estat(m), 'open')

    def test_amb_volta_oberta_i_cap_tasca_viva_el_model_NO_s_amaga_per_defecte(self):
        """Conseqüència directa: si cau a una columna de feina, ha de ser a la llista per
        defecte. Una fila que existeix a la columna i no a la consulta seria un fantasma."""
        m = self._model_tot_done()
        self._obrir_ronda(m, 'nova_mostra', ['pom'], profile=self.prof)
        for t in ModelTask.objects.filter(model=m, status='Pending'):
            transition_task(t, 'InProgress', self.prof)
            transition_task(t, 'Done', self.prof)
        self.assertIsNotNone(self._fila(m))            # sense `all=true`
        self.assertEqual(self._fila(m)['kanban_state'], 'pending')

    def test_un_model_ENTREGAT_segueix_amagat_per_defecte(self):
        """…i el contrari es manté: la feina ENVIADA sí que és feina acabada, i el filtre per
        defecte («amaga el que ja està fet») l'ha de seguir traient."""
        m = self._model_tot_done()
        r = self._obrir_ronda(m, 'nova_mostra', ['pom'], profile=self.prof)
        for t in r.tasques.all():
            transition_task(t, 'InProgress', self.prof)
            transition_task(t, 'Done', self.prof)
        self._entrega(r, destinatari='Brumà SL', profile=self.prof)
        self.assertIsNone(self._fila(m))
        self.assertIsNotNone(self._fila(m, all='true'))
