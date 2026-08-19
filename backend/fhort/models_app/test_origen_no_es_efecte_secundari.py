"""L'ORIGEN D'UNA MESURA NO ÉS EFECTE SECUNDARI D'UNA ALTRA ESCRIPTURA (Agus, 05/08/2026).

LA PROMESA QUE FIXA
-------------------
Una base que una sessió de size check ha deixat `CHECKED` **segueix sent `CHECKED`** després
que qualsevol de les dues portes d'escriptura massiva (`set_measurements_view` i
`gravar_pom_view`) hi torni a passar sense canviar-ne el valor. I les seves toleràncies
segueixen sent les seves, no les del catàleg.

EL QUE ES VA MESURAR ABANS D'ARREGLAR-HO
----------------------------------------
Les dues portes escrivien `origen='MANUAL'` i les DUES toleràncies del catàleg als `defaults`
de l'upsert, o sigui a **cada fila del payload**, hi hagués canviat el valor o no. N'hi havia
prou de reenviar la taula —moure una fila de capa, desar sense tocar cap xifra— perquè una
base `CHECKED` passés a `MANUAL` i les toleràncies afinades tornessin al defecte del catàleg.

PER QUÈ IMPORTA I NO ÉS COSMÈTICA
---------------------------------
Trenca la PRECEDÈNCIA TEMPORAL: l'última mesura escrita és la veritat i el seu origen ha de
ser el que li correspon. Un `MANUAL` fals afirma «això ho va teclejar algú» sobre una xifra
que ve d'una presa de proto. I no es pot desfer mirant la fila: `origen` el sobreescriu el
canvi següent (no és append-only). Qui després pregunti «qui va mesurar això» rep una
resposta falsa.

⚠️ EL CAS INVERS TAMBÉ ES FIXA, i és igual d'important: si l'escriptura **sí que canvia el
valor**, l'origen HA de passar a `MANUAL`. Algú acaba de teclejar una xifra nova i dir que
segueix venint d'un size check seria la mateixa mentida girada del revés.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.models import BaseMeasurement, Model
from fhort.models_app.test_c4_germanes_a_les_superficies import comportes_alcades
from fhort.pom.models import MeasurementLayer, POMMaster, SizeDefinition, SizeSystem

EXTERIOR = MeasurementLayer.SLUG_DEFECTE
TAULES = ('models_app_basemeasurement', 'models_app_measurementchangelog')


class OrigenNoEsEfecteSecundariTest(TenantTestCase):

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
        # Toleràncies de CATÀLEG deliberadament diferents de les que tindrà la fila: si el
        # guard es trenca, la fila torna a aquests valors i l'assert ho veu.
        self.pom = POMMaster.objects.create(
            codi_client='CH', nom_client='Pit',
            tolerancia_default_minus=0.5, tolerancia_default_plus=0.5)
        self.ss = SizeSystem.objects.create(codi='SS_W', nom='SS W', base_unit='ALPHA')
        for i, et in enumerate(['XS', 'S', 'M']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern='TST-O', codi_tenant='TST', any=2027, sequencial=8,
            temporada='FW27', size_system=self.ss,
            size_run_model='XS·S·M', base_size_label='S')
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_o', defaults={'email': 'qa@o.test'})
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA O', 'rol_nom': 'QA'})
        from fhort.tasks.models import ModelTask, TaskType
        tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'POM', 'default_order': 1})
        ModelTask.objects.get_or_create(
            model=self.model, task_type=tt, defaults={'status': 'Pending'})

    def _req(self, body):
        r = APIRequestFactory().post('/x/', body, format='json')
        force_authenticate(r, user=self.user)
        return r

    def _base_checked(self, valor=100.0):
        """La fila tal com la deixa resoldre un size check: CHECKED i amb tolerància pròpia."""
        return BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=valor, nom_fitxa='A',
            origen='CHECKED', tolerancia_minus=1.5, tolerancia_plus=2.5)

    def _fila(self):
        return BaseMeasurement.objects.get(
            model=self.model, pom=self.pom, capa=EXTERIOR, instancia='')

    def _mesura(self, valor, **extra):
        return {'pom_id': self.pom.id, 'capa': EXTERIOR, 'instancia': '',
                'base_value_cm': valor, 'nom_fitxa': 'A', **extra}

    # ── El cas del brief: una escriptura que NO mesura res no toca la procedència ─────

    def test_set_measurements_amb_el_mateix_valor_deixa_la_base_CHECKED(self):
        from fhort.models_app.views import set_measurements_view

        with comportes_alcades(*TAULES):
            self._base_checked()
            resp = set_measurements_view(
                self._req({'measurements': [self._mesura(100.0)],
                           'keep_mesures': [{'pom_id': self.pom.id, 'capa': EXTERIOR,
                                             'instancia': ''}]}),
                self.model.id)
            self.assertIn(resp.status_code, (200, 201), resp.data)
            bm = self._fila()
            self.assertEqual(bm.origen, 'CHECKED',
                             "una escriptura que no canvia el valor ha convertit CHECKED en "
                             f"{bm.origen}: la precedència temporal menteix")
            self.assertEqual(float(bm.tolerancia_minus), 1.5)
            self.assertEqual(float(bm.tolerancia_plus), 2.5)

    def test_gravar_pom_amb_el_mateix_valor_deixa_la_base_CHECKED(self):
        from fhort.models_app.views import gravar_pom_view

        with comportes_alcades(*TAULES):
            self._base_checked()
            resp = gravar_pom_view(
                self._req({'measurements': [self._mesura(100.0)],
                           'keep_pom_ids': [self.pom.id]}),
                self.model.id)
            self.assertIn(resp.status_code, (200, 201), resp.data)
            bm = self._fila()
            self.assertEqual(bm.origen, 'CHECKED', f'ha passat a {bm.origen}')
            self.assertEqual(float(bm.tolerancia_minus), 1.5)
            self.assertEqual(float(bm.tolerancia_plus), 2.5)

    # ── El cas INVERS: si l'escriptura mesura, l'origen li correspon ─────────────────

    def test_canviar_el_valor_SI_que_passa_l_origen_a_MANUAL(self):
        from fhort.models_app.views import set_measurements_view

        with comportes_alcades(*TAULES):
            self._base_checked()
            set_measurements_view(
                self._req({'measurements': [self._mesura(107.0)],
                           'keep_mesures': [{'pom_id': self.pom.id, 'capa': EXTERIOR,
                                             'instancia': ''}]}),
                self.model.id)
            bm = self._fila()
            self.assertEqual(bm.base_value_cm, 107.0)
            self.assertEqual(bm.origen, 'MANUAL',
                             'una xifra nova teclejada a mà ha de dir que és manual')
            # Les toleràncies segueixen sent de la FILA: canviar un valor no és rebatejar la
            # banda de tolerància que algú va afinar.
            self.assertEqual(float(bm.tolerancia_minus), 1.5)

    def test_el_payload_mana_sempre_si_ho_diu_explicitament(self):
        from fhort.models_app.views import set_measurements_view

        with comportes_alcades(*TAULES):
            self._base_checked()
            set_measurements_view(
                self._req({'measurements': [self._mesura(
                    112.0, origen='FITTED', tolerancia_minus=0.1, tolerancia_plus=0.2)],
                    'keep_mesures': [{'pom_id': self.pom.id, 'capa': EXTERIOR,
                                      'instancia': ''}]}),
                self.model.id)
            bm = self._fila()
            self.assertEqual(bm.origen, 'FITTED')
            self.assertEqual(float(bm.tolerancia_minus), 0.1)
            self.assertEqual(float(bm.tolerancia_plus), 0.2)

    # ── El naixement: una fila nova sí que neix MANUAL i amb el catàleg ─────────────

    def test_una_fila_NOVA_neix_MANUAL_i_amb_les_tolerancies_del_cataleg(self):
        from fhort.models_app.views import set_measurements_view

        with comportes_alcades(*TAULES):
            set_measurements_view(
                self._req({'measurements': [self._mesura(90.0)]}), self.model.id)
            bm = self._fila()
            self.assertEqual(bm.origen, 'MANUAL')
            self.assertEqual(float(bm.tolerancia_minus), 0.5)
            self.assertEqual(float(bm.tolerancia_plus), 0.5)
