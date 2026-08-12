"""SET-2/T5 — la poda i el registre saben de la peça (2026-08-10).

Els dos vermells de prioritat del tram, i tots dos són del gènere que aquest sprint
persegueix: **danys que no criden**.

  1 · `_poda_mesures`, branca de la CLAU CURTA. Desactiva (`is_active=False`) tot el que no
      sigui a `keep_pom_ids`, i el cridador que hi arriba només sap dir POMs. Ja s'acotava a
      l'exterior de la instància única; sense `garment=''` hauria donat de baixa les files de
      TOTES les peces del model. Ningú peta: les mesures simplement deixen de comptar.

  2 · **Signal F1**. `MeasurementChangeLog` és APPEND-ONLY i no té cap unicitat: una fila
      escrita sense l'eix NO es pot corregir després. Si el log no copia el `garment`, el
      lector no podrà dir mai de quina peça parlava un canvi ja registrat — i la secció
      «preses reescrites per regla de germana», que ha de néixer d'aquest registre, neixeria
      cega.

Les comportes es lleven dins d'un savepoint que sempre es desfà (patró
`test_lectors_capa_onada1`), perquè amb elles vives cap fila '02' pot existir.
"""
import contextlib
import datetime

from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import BaseMeasurement, MeasurementChangeLog, Model
from fhort.models_app.views import _poda_mesures
from fhort.pom.models import POMMaster

MARE = ''
SEGONA = '02'
TAULES = ('models_app_basemeasurement', 'models_app_measurementchangelog')


@contextlib.contextmanager
def comportes_alcades(*taules):
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            for taula in taules:
                cur.execute(
                    f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                    f'DROP CONSTRAINT IF EXISTS "{taula}_garment_gate_set2"'
                )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class PodaINoTocaLesAltresPecesTest(TenantTestCase):

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
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.altre = POMMaster.objects.create(codi_client='WA', nom_client='Cintura')
        self.model = Model.objects.create(
            codi_intern='TST-T5', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    def _mesura(self, pom, garment=MARE, valor=100.0, nom='A'):
        return BaseMeasurement.objects.create(
            model=self.model, pom=pom, base_value_cm=valor, ordre=1,
            nom_fitxa=nom, garment=garment)

    def test_una_poda_amb_clau_CURTA_no_toca_les_files_de_les_altres_peces(self):
        """EL VERMELL PRINCIPAL DE T5.

        `keep_pom_ids` és una llista de POMs: no diu res de peces. Podar amb ella ha de
        deixar la 02 EXACTAMENT com estava —encara que el seu POM no hi surti—, perquè una
        llista de POMs no és una ordre d'esborrar la feina d'una altra peça.
        """
        with comportes_alcades(*TAULES):
            mare_conserva = self._mesura(self.pom, MARE, nom='A-MARE')
            mare_poda = self._mesura(self.altre, MARE, valor=80.0, nom='B-MARE')
            segona = self._mesura(self.altre, SEGONA, valor=60.0, nom='B-02')

            _poda_mesures(self.model, None, [self.pom.pk])

            mare_conserva.refresh_from_db()
            mare_poda.refresh_from_db()
            segona.refresh_from_db()
            self.assertTrue(mare_conserva.is_active, 'el POM conservat de la mare ha caigut')
            self.assertFalse(mare_poda.is_active, 'el POM no conservat de la mare no ha caigut')
            self.assertTrue(
                segona.is_active,
                'LA PODA HA DESACTIVAT LA FILA DE LA PEÇA 02 amb una crida que no en parlava')

    def test_EL_CAS_DE_CONTROL_la_poda_dun_model_dUNA_pesa_fa_el_de_sempre(self):
        """Que l'eix no talli de més: el 100% del corpus d'avui és d'una sola peça i la
        poda hi ha de fer exactament el que feia."""
        mante = self._mesura(self.pom, MARE, nom='A')
        cau = self._mesura(self.altre, MARE, valor=80.0, nom='B')

        n = _poda_mesures(self.model, None, [self.pom.pk])

        mante.refresh_from_db()
        cau.refresh_from_db()
        self.assertEqual(n, 1)
        self.assertTrue(mante.is_active)
        self.assertFalse(cau.is_active)

    def test_la_poda_per_FILA_distingeix_les_peces(self):
        """L'altra branca: amb `keep_mesures` (que SÍ porta identitat), la poda distingeix les
        files DINS de la prenda de què parla el desat.

        ⚠️ REVISAT a SET-2/#12b (12/08). Aquest test afirmava el contrari —que desar la mare
        havia de fer caure la fila de la 02— perquè T5 llegia `keep_mesures` com «tot el que
        queda al MODEL». Amb la taula partida per peça (S2, pas 3) el client només pot enviar
        les files del SEU contenidor, o sigui que aquella lectura convertia cada desat de la
        mare en una baixa silenciosa de les altres prendes: mesurat contra dades vives, 1
        baixa i la fila de la 02 morta. Ara `keep_mesures` es llegeix com «tot el que queda al
        CONTENIDOR», i el que la llista no anomena no és ni candidat.
        """
        with comportes_alcades(*TAULES):
            mare_conserva = self._mesura(self.pom, MARE, nom='A-MARE')
            mare_poda = self._mesura(self.altre, MARE, valor=80.0, nom='B-MARE')
            segona = self._mesura(self.pom, SEGONA, valor=60.0, nom='A-02')

            n = _poda_mesures(self.model,
                              [{'pom_id': self.pom.pk, 'capa': 'exterior',
                                'instancia': '', 'garment': MARE}],
                              [])

            mare_conserva.refresh_from_db()
            mare_poda.refresh_from_db()
            segona.refresh_from_db()
            self.assertEqual(n, 1, 'la poda havia de caure NOMÉS sobre la fila de la mare')
            self.assertTrue(mare_conserva.is_active, 'la fila anomenada ha caigut')
            self.assertFalse(mare_poda.is_active,
                             'la fila de la MARE que no surt a la llista havia de caure')
            self.assertTrue(
                segona.is_active,
                'LA PODA HA MATAT LA FILA DE LA 02 amb un desat que només parlava de la mare')


class LAbastDeLaPodaEsElDelContenidorTest(TenantTestCase):
    """SET-2/#12b — el guard que S2 va veure vermell, i el seu cas de control.

    El forat el va mesurar S2 contra dades vives (amb rollback): amb la taula filtrada per
    peça, desar el contenidor de la mare enviava NOMÉS les files de la mare, i la poda —que
    mirava totes les files vives del model— donava de baixa les del Pantaló. Amb l'eix al
    payload i tot: no era que la informació hi faltés, és que l'abast era un altre.
    """

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
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.altre = POMMaster.objects.create(codi_client='WA', nom_client='Cintura')
        self.model = Model.objects.create(
            codi_intern='TST-12B', codi_tenant='TST', any=2026, sequencial=2,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    def _mesura(self, pom, garment=MARE, valor=100.0, nom='A'):
        return BaseMeasurement.objects.create(
            model=self.model, pom=pom, base_value_cm=valor, ordre=1,
            nom_fitxa=nom, garment=garment)

    def _fila(self, pom, garment):
        return {'pom_id': pom.pk, 'capa': 'exterior', 'instancia': '', 'garment': garment}

    def test_EL_GUARD_desar_la_mare_no_desactiva_les_files_del_pantalo(self):
        """El vermell. Desat del contenidor de la mare, amb la 02 viva i FORA del payload."""
        with comportes_alcades(*TAULES):
            mare = self._mesura(self.pom, MARE, nom='A-MARE')
            segona_a = self._mesura(self.pom, SEGONA, valor=60.0, nom='A-02')
            segona_b = self._mesura(self.altre, SEGONA, valor=61.0, nom='B-02')

            n = _poda_mesures(self.model, [self._fila(self.pom, MARE)], None)

            for fila in (mare, segona_a, segona_b):
                fila.refresh_from_db()
            self.assertEqual(n, 0)
            self.assertTrue(mare.is_active)
            self.assertTrue(segona_a.is_active, 'la 02 ha caigut amb un desat de la mare')
            self.assertTrue(segona_b.is_active, 'la 02 ha caigut amb un desat de la mare')

    def test_i_a_linreves_desar_el_pantalo_no_toca_la_mare(self):
        """La simetria: l'abast acota igual en les dues direccions."""
        with comportes_alcades(*TAULES):
            mare = self._mesura(self.pom, MARE, nom='A-MARE')
            segona_conserva = self._mesura(self.pom, SEGONA, valor=60.0, nom='A-02')
            segona_cau = self._mesura(self.altre, SEGONA, valor=61.0, nom='B-02')

            n = _poda_mesures(self.model, [self._fila(self.pom, SEGONA)], None)

            for fila in (mare, segona_conserva, segona_cau):
                fila.refresh_from_db()
            self.assertEqual(n, 1)
            self.assertTrue(mare.is_active, 'desar el Pantaló ha tocat la mare')
            self.assertTrue(segona_conserva.is_active)
            self.assertFalse(segona_cau.is_active,
                             'dins de la peça, el que no surt a la llista SÍ que ha de caure')

    def test_EL_CAS_DE_CONTROL_un_model_dUNA_pesa_es_comporta_EXACTAMENT_igual(self):
        """El 100% del corpus d'avui. Sense cap fila d'una altra prenda, l'abast derivat és
        {''} i la poda fa exactament el que feia abans d'aquest tram."""
        mante = self._mesura(self.pom, MARE, nom='A')
        cau = self._mesura(self.altre, MARE, valor=80.0, nom='B')

        n = _poda_mesures(self.model, [self._fila(self.pom, MARE)], None)

        mante.refresh_from_db()
        cau.refresh_from_db()
        self.assertEqual(n, 1)
        self.assertTrue(mante.is_active)
        self.assertFalse(cau.is_active)

    def test_un_contenidor_BUIT_no_endevina_de_qui_es_el_silenci(self):
        """Sense files i sense abast explícit no es pot saber de quina prenda parla el desat.
        D'un «no ho sé» no en surt cap baixa: el contrari seria decidir per un client que no
        ha dit res, que és el que tot aquest tram prohibeix."""
        with comportes_alcades(*TAULES):
            mare = self._mesura(self.pom, MARE, nom='A-MARE')
            segona = self._mesura(self.pom, SEGONA, valor=60.0, nom='A-02')

            n = _poda_mesures(self.model, [], None)

            mare.refresh_from_db()
            segona.refresh_from_db()
            self.assertEqual(n, 0)
            self.assertTrue(mare.is_active)
            self.assertTrue(segona.is_active)

    def test_el_contenidor_BUIT_que_diu_qui_es_SI_que_es_buida(self):
        """La vora d'abast explícit (`garments`): el contenidor que es desa buit diu de qui és
        i pot buidar-se sencer, sense tocar les altres prendes."""
        with comportes_alcades(*TAULES):
            mare = self._mesura(self.pom, MARE, nom='A-MARE')
            segona = self._mesura(self.pom, SEGONA, valor=60.0, nom='A-02')

            n = _poda_mesures(self.model, [], None, garments=[SEGONA])

            mare.refresh_from_db()
            segona.refresh_from_db()
            self.assertEqual(n, 1)
            self.assertTrue(mare.is_active, "buidar el Pantaló ha tocat la mare")
            self.assertFalse(segona.is_active)


class LAbastDeLaPodaAGravarPomTest(TenantTestCase):
    """SET-2/#12b — el MATEIX guard, per l'altra porta: `gravar-pom`.

    El forat era UN i tenia dues portes. La llei viu a `_poda_mesures` i les dues hi passen,
    o sigui que el fix no es duplica; el que sí que cal per duplicat és la PROVA que cada
    porta li dóna el payload sencer —que el `garments` del cos hi arriba i que l'abast derivat
    no s'hi perd pel camí—. Aquesta és, a més, la pantalla del dany original: la definició de
    POM és on la tècnica desa la taula per primer cop.

    ✅ SET-2/#12c (12/08) — LA MITIGACIÓ DELS FIXTURES ESTÀ RETIRADA. Aquests guards es van
    escriure amb cada prenda en un POM diferent per esquivar un segon forat que llavors era
    viu: l'upsert d'aquesta mateixa porta resolia sense el `garment`, i amb la mare i la 02
    al mateix POM el `.first()` podia caure sobre la fila de l'altra prenda. Aquell forat ja
    no hi és —l'eix entra a `prepared` i a la resolució— i el cas del POM compartit el cobreix
    ara `LEscripturaDeGravarPomPortaLEixTest`. Els POMs separats d'aquí es queden perquè
    mesuren una altra cosa: que la poda no travessi la frontera de prenda.
    """

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
        from django.contrib.auth import get_user_model
        from fhort.accounts.models import UserProfile
        from fhort.tasks.models import ModelTask, TaskType

        self.mare_pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.altre_mare = POMMaster.objects.create(codi_client='WA', nom_client='Cintura')
        self.pom_02 = POMMaster.objects.create(codi_client='HP', nom_client='Maluc')
        self.altre_02 = POMMaster.objects.create(codi_client='TH', nom_client='Cuixa')
        self.model = Model.objects.create(
            codi_intern='TST-12BG', codi_tenant='TST', any=2026, sequencial=3,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_12b', defaults={'email': 'qa@12b.test'})
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA 12b', 'rol_nom': 'QA'})
        # `gravar_pom_view` tanca la tasca POM del model i falla si no n'hi ha cap.
        tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'POM', 'default_order': 1})
        ModelTask.objects.get_or_create(
            model=self.model, task_type=tt, defaults={'status': 'Pending'})

    def _req(self, body):
        from rest_framework.test import APIRequestFactory, force_authenticate
        r = APIRequestFactory().post('/x/', body, format='json')
        force_authenticate(r, user=self.user)
        return r

    def _mesura(self, pom, garment=MARE, valor=100.0, nom='A'):
        return BaseMeasurement.objects.create(
            model=self.model, pom=pom, base_value_cm=valor, ordre=1,
            nom_fitxa=nom, garment=garment)

    def _fila(self, pom, garment, valor=None):
        d = {'pom_id': pom.pk, 'capa': 'exterior', 'instancia': '', 'garment': garment}
        if valor is not None:
            d['base_value_cm'] = valor
        return d

    def _gravar(self, body):
        from fhort.models_app.views import gravar_pom_view
        return gravar_pom_view(self._req(body), self.model.id)

    def test_EL_GUARD_gravar_pom_de_la_mare_no_desactiva_les_files_del_pantalo(self):
        """El vermell de S2, per la porta de la definició de POM."""
        with comportes_alcades(*TAULES):
            mare = self._mesura(self.mare_pom, MARE, nom='A-MARE')
            segona = self._mesura(self.pom_02, SEGONA, valor=60.0, nom='C-02')

            resp = self._gravar({
                'measurements': [self._fila(self.mare_pom, MARE, valor=111.0)],
                'keep_mesures': [self._fila(self.mare_pom, MARE)],
            })

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            self.assertEqual(resp.data['deactivated'], 0, resp.data)
            mare.refresh_from_db()
            segona.refresh_from_db()
            self.assertTrue(mare.is_active)
            self.assertTrue(
                segona.is_active,
                'GRAVAR-POM DE LA MARE HA MATAT LA FILA DE LA 02')

    def test_gravar_pom_del_pantalo_no_toca_la_mare(self):
        """La simetria, i que dins de la prenda la poda segueix podant."""
        with comportes_alcades(*TAULES):
            mare = self._mesura(self.mare_pom, MARE, nom='A-MARE')
            segona_conserva = self._mesura(self.pom_02, SEGONA, valor=60.0, nom='C-02')
            segona_cau = self._mesura(self.altre_02, SEGONA, valor=61.0, nom='D-02')

            resp = self._gravar({
                'measurements': [self._fila(self.pom_02, SEGONA, valor=66.0)],
                'keep_mesures': [self._fila(self.pom_02, SEGONA)],
            })

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            self.assertEqual(resp.data['deactivated'], 1, resp.data)
            for fila in (mare, segona_conserva, segona_cau):
                fila.refresh_from_db()
            self.assertTrue(mare.is_active, 'desar el Pantaló ha tocat la mare')
            self.assertTrue(segona_conserva.is_active)
            self.assertFalse(segona_cau.is_active,
                             'dins de la peça, el que no surt a la llista SÍ que ha de caure')

    def test_EL_CAS_DE_CONTROL_un_model_dUNA_pesa_es_comporta_EXACTAMENT_igual(self):
        """El 100% del corpus d'avui passa per aquí i no ha de notar res."""
        mante = self._mesura(self.mare_pom, MARE, nom='A')
        cau = self._mesura(self.altre_mare, MARE, valor=80.0, nom='B')

        resp = self._gravar({
            'measurements': [self._fila(self.mare_pom, MARE, valor=111.0)],
            'keep_mesures': [self._fila(self.mare_pom, MARE)],
        })

        self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
        self.assertEqual(resp.data['deactivated'], 1, resp.data)
        mante.refresh_from_db()
        cau.refresh_from_db()
        self.assertTrue(mante.is_active)
        self.assertFalse(cau.is_active)

    def test_labast_EXPLICIT_del_cos_arriba_tambe_per_aquesta_porta(self):
        """`garments` no és decoració d'una vista sola: la porta l'ha de passar avall.

        El desat parla de la mare, però declara que està podant la 02 —el gest del contenidor
        que es buida—: la 02 cau sencera i la mare no és ni candidata.
        """
        with comportes_alcades(*TAULES):
            mare = self._mesura(self.mare_pom, MARE, nom='A-MARE')
            altra_mare = self._mesura(self.altre_mare, MARE, valor=80.0, nom='B-MARE')
            segona = self._mesura(self.pom_02, SEGONA, valor=60.0, nom='C-02')

            resp = self._gravar({
                'measurements': [self._fila(self.mare_pom, MARE, valor=111.0)],
                'keep_mesures': [self._fila(self.mare_pom, MARE)],
                'garments': [SEGONA],
            })

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            self.assertEqual(resp.data['deactivated'], 1, resp.data)
            for fila in (mare, altra_mare, segona):
                fila.refresh_from_db()
            self.assertTrue(mare.is_active)
            self.assertTrue(altra_mare.is_active,
                            "l'abast explícit deia '02': cap fila de la mare era candidata")
            self.assertFalse(segona.is_active)

    def test_per_aquesta_porta_el_desat_BUIT_no_arriba_ni_a_la_poda(self):
        """L'asimetria entre les dues portes, escrita perquè no sorprengui ningú.

        `set-measurements` accepta un desat sense mesures (i per això li calia la vora del
        contenidor buit); `gravar-pom` el rebutja abans amb un 400 —«cal introduir almenys una
        mida base»—, o sigui que per aquí el cas del contenidor buit no existeix.
        """
        with comportes_alcades(*TAULES):
            segona = self._mesura(self.pom_02, SEGONA, valor=60.0, nom='C-02')

            resp = self._gravar({'measurements': [], 'keep_mesures': [], 'garments': [MARE]})

            self.assertEqual(resp.status_code, 400, getattr(resp, 'data', None))
            segona.refresh_from_db()
            self.assertTrue(segona.is_active, 'una petició rebutjada no ha de podar res')


class LEscripturaDeGravarPomPortaLEixTest(TenantTestCase):
    """SET-2/#12c — el contracte d'ESCRIPTURA de `gravar-pom` guanya la prenda.

    El germà gros del forat de la poda, i a la mateixa porta. `gravar_pom_view` LLEGIA el
    `garment` per rebutjar dues mesures del mateix request sobre la mateixa fila
    (`views.py:2364`) i tot seguit el LLENÇAVA: no entrava a `prepared` (`:2399`) i l'upsert
    resolia per `(model, pom, capa, instancia)` sense l'eix (`:2441`). Amb la mare i la 02 al
    MATEIX POM —el cas normal: el pit del top i el pit de la calceta són el mateix POM— el
    `.first()` podia caure sobre la fila de l'altra prenda i sobreescriure-la, i les files
    noves naixien totes a la mare.

    Aquests guards fan servir EL MATEIX POM per a les dues prendes a posta: és exactament el
    cas que els fixtures de `LAbastDeLaPodaAGravarPomTest` esquivaven mentre el forat era
    viu.
    """

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
        from django.contrib.auth import get_user_model
        from fhort.accounts.models import UserProfile
        from fhort.tasks.models import ModelTask, TaskType

        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-12C', codi_tenant='TST', any=2026, sequencial=4,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_12c', defaults={'email': 'qa@12c.test'})
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA 12c', 'rol_nom': 'QA'})
        tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'POM', 'default_order': 1})
        ModelTask.objects.get_or_create(
            model=self.model, task_type=tt, defaults={'status': 'Pending'})

    def _req(self, body):
        from rest_framework.test import APIRequestFactory, force_authenticate
        r = APIRequestFactory().post('/x/', body, format='json')
        force_authenticate(r, user=self.user)
        return r

    def _gravar(self, files):
        from fhort.models_app.views import gravar_pom_view
        return gravar_pom_view(self._req({'measurements': files}), self.model.id)

    def _fila(self, garment, valor, nom):
        return {'pom_id': self.pom.pk, 'capa': 'exterior', 'instancia': '',
                'garment': garment, 'base_value_cm': valor, 'nom_fitxa': nom}

    def _vives(self):
        return {bm.garment: float(bm.base_value_cm)
                for bm in BaseMeasurement.objects.filter(
                    model=self.model, pom=self.pom, is_active=True)}

    def test_escriure_la_02_NO_sobreescriu_la_fila_de_la_mare(self):
        """EL VERMELL. Mateix POM, dues prendes: cadascuna a la seva fila."""
        with comportes_alcades(*TAULES):
            mare = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-MARE', garment=MARE)

            resp = self._gravar([self._fila(SEGONA, 66.0, 'A-02')])

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            mare.refresh_from_db()
            self.assertEqual(float(mare.base_value_cm), 100.0,
                             'ESCRIURE LA 02 HA SOBREESCRIT LA FILA DE LA MARE')
            self.assertEqual(mare.garment, MARE, "la fila de la mare ha canviat de prenda")
            self.assertEqual(self._vives(), {MARE: 100.0, SEGONA: 66.0})

    def test_una_fila_nova_neix_amb_la_seva_prenda(self):
        """Sense cap fila prèvia: la que neix ha de portar l'eix del payload, no el default."""
        with comportes_alcades(*TAULES):
            resp = self._gravar([self._fila(SEGONA, 66.0, 'A-02')])

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            nova = BaseMeasurement.objects.get(model=self.model, pom=self.pom, is_active=True)
            self.assertEqual(nova.garment, SEGONA,
                             'LA FILA NOVA HA NASCUT A LA MARE amb un payload que deia 02')

    def test_i_la_02_ja_existent_es_torna_a_trobar_no_es_duplica(self):
        """L'altra cara: amb l'eix a la resolució, desar dos cops la 02 ACTUALITZA la seva
        fila. Sense l'eix això requeia a la mare; amb l'eix mal posat duplicaria."""
        with comportes_alcades(*TAULES):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-MARE', garment=MARE)
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=60.0, ordre=2,
                nom_fitxa='A-02', garment=SEGONA)

            resp = self._gravar([self._fila(SEGONA, 66.0, 'A-02')])

            self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
            self.assertEqual(resp.data['created'], 0, resp.data)
            self.assertEqual(resp.data['updated'], 1, resp.data)
            self.assertEqual(self._vives(), {MARE: 100.0, SEGONA: 66.0})

    def test_EL_CAS_DE_CONTROL_un_desat_dUNA_pesa_fa_el_de_sempre(self):
        """El 100% del corpus d'avui: sense `garment` al payload, tot va a la mare."""
        mare = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='A')

        resp = self._gravar([{'pom_id': self.pom.pk, 'base_value_cm': 111.0,
                              'nom_fitxa': 'A'}])

        self.assertIn(resp.status_code, (200, 201), getattr(resp, 'data', None))
        mare.refresh_from_db()
        self.assertEqual(float(mare.base_value_cm), 111.0)
        self.assertEqual(self._vives(), {MARE: 111.0})


class ElRegistreCopiaLaPecaTest(TenantTestCase):
    """Signal F1 — append-only i sense unicitat: el que no s'escrigui aquí es perd per sempre."""

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
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-T5L', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    def test_un_canvi_de_valor_a_la_02_queda_registrat_A_LA_02(self):
        """Sense això, el registre diria que el canvi va ser de la peça mare — i com que la
        taula és append-only, la mentida seria permanent."""
        with comportes_alcades(*TAULES):
            bm = BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=50.0, ordre=1,
                nom_fitxa='A-02', garment=SEGONA)
            bm.base_value_cm = 55.0
            bm.save()

            apunts = list(MeasurementChangeLog.objects
                          .filter(model=self.model, pom=self.pom)
                          .values_list('garment', 'valor_nou'))
            self.assertIn((SEGONA, 55.0), apunts,
                          "el registre no ha copiat el garment del canvi de valor")

    def test_EL_CAS_DE_CONTROL_un_canvi_a_la_mare_segueix_dient_el_de_sempre(self):
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='A')
        bm.base_value_cm = 103.0
        bm.save()

        apunts = list(MeasurementChangeLog.objects
                      .filter(model=self.model, pom=self.pom)
                      .values_list('garment', 'valor_nou'))
        self.assertIn((MARE, 103.0), apunts)


class LaCopiaCopiaLaPecaTest(TenantTestCase):
    """T5b — els col·lapses silenciosos: la còpia model→model i la materialització del check.

    Tots dos seguien un rastre que ja hi era («la còpia COPIA: els eixos surten de la fila
    d'origen, no de cap literal») i només els faltava el tercer eix.
    """

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
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-T5C', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    def test_la_materialitzacio_del_check_no_deixa_cap_peca_fora(self):
        """`_materialize_lines` aparellava per (pom, capa, instancia): la PRIMERA peça
        bloquejava la materialització de les altres i la seva fila quedava INERTA a
        l'editor —el tècnic la veia i no la podia omplir—.

        EL CAS DE CONTROL TRENCA LA COINCIDÈNCIA: les dues files són del MATEIX POM, la
        MATEIXA capa i la MATEIXA instància. L'única cosa que les separa és la peça, o sigui
        que si l'aparellament no la mira, la segona no es materialitza.
        """
        from fhort.models_app.models import SizeCheck, SizeCheckLine
        from fhort.models_app.services_size_check import _materialize_lines

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog',
                               'models_app_sizecheckline'):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1,
                nom_fitxa='A-MARE', garment=MARE)
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=60.0, ordre=2,
                nom_fitxa='A-02', garment=SEGONA)
            check = SizeCheck.objects.create(model=self.model, talla_base_label='M')
            # ⚠️ LA LÍNIA DE LA MARE JA HI ÉS. Sense això el test no provava res: `ja_hi_son`
            # es construeix de les línies EXISTENTS, i amb un check nou el conjunt és buit i
            # l'aparellament no s'arriba a consultar mai. Amb la línia de la mare present, la
            # clau curta la fa casar amb la fila de la 02 —mateix POM, mateixa capa, mateixa
            # instància— i la 02 es queda sense materialitzar. (Mutant supervivent caçat
            # 2026-08-10: el primer sospitós era el test, i ho era.)
            SizeCheckLine.objects.create(
                size_check=check, pom=self.pom, capa='exterior', instancia='',
                garment=MARE, valor_teoric=100.0)

            _materialize_lines(check, self.model)

            files = set(SizeCheckLine.objects
                        .filter(size_check=check)
                        .values_list('garment', 'valor_teoric'))
            self.assertEqual(
                files, {(MARE, 100.0), (SEGONA, 60.0)},
                'la primera peça ha bloquejat la materialització de la segona')
