"""G6-B · LA INTEGRITAT DEL SEGELL (DIAGNOSI_G6_DUAL_PATH, Fase 2 · R1 i R3).

Executat amb `python manage.py test fhort.pom` (el projecte NO fa servir pytest).

El segell MENTIA. El guard que hi havia protegia **crear v+1** sobre una versió aprovada, però
no protegia **escriure dins** la versió activa: sis endpoints hi reescrivien `GradedSpec`
in-place conservant `aprovada=True`. I el `GradingVersionViewSet` era un ModelViewSet obert:
qualsevol autenticat podia fer `PATCH {"aprovada": false}` o `DELETE`.

Els tests que valen són **els negatius**: els sis camins que han de fer 409 i les portes que
han de fer 405/403. El que tanca la sèrie és `IntegritatDelMotorTest`: la petja de la versió
segellada ha de ser **idèntica** abans i després d'un intent d'escriptura rebutjat. Aquesta és,
literalment, la raó per la qual el motor de patrons pot confiar en `gv.aprovada`.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
from fhort.models_app.models import BaseMeasurement, Model, ModelGradingOverride, ModelGradingRule
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem
from fhort.pom.services import (
    SealedGradingVersionError,
    generate_graded_specs,
    sealed_active_version,
)


class _SegellBase(TenantTestCase):
    """Un model que gradua, amb la versió vigent SEGELLADA (aprovada=True)."""

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
        from fhort.accounts.models import UserProfile
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create(username='segell')
        # ⚠️ Un signal ja crea el perfil en crear l'usuari, amb el rol PER DEFECTE (technician).
        # Un `get_or_create` amb defaults NO el canvia — i llavors l'admin d'aquests tests no
        # tindria CLOSE_GATES i tot serien 403 despistats. El rol s'assigna explícitament.
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'Segell'})
        self.profile.rol_nom = 'admin'
        self.profile.save(update_fields=['rol_nom'])
        # …i rellegir l'usuari: el signal ha deixat `user.profile` cachejat amb el rol vell, i
        # force_authenticate passa AQUESTA instància → el permís es resoldria contra el rol vell.
        self.user = get_user_model().objects.get(pk=self.user.pk)

        self.ss = SizeSystem.objects.create(codi='SS_SG', nom='SS segell', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        # TRES POMs: `confirmar-talla-base` (camí 6) exigeix un mínim de 3 mesures base abans
        # d'arribar a graduar. Amb un de sol, el 409 del guard no s'arribaria a exercir mai.
        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest width')
        self.pom2 = POMMaster.objects.create(codi_client='B', nom_client='Waist width')
        self.pom3 = POMMaster.objects.create(codi_client='C', nom_client='Hip width')

        self.model = Model.objects.create(
            codi_intern='TST-182', codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Model segellat', size_system=self.ss, size_run_model='S·M·L',
            base_size_label='M',
        )
        for pom in (self.pom, self.pom2, self.pom3):
            ModelGradingRule.objects.create(
                model=self.model, pom=pom, logica='LINEAR', increment_base=2,
                actiu=True, origen='MANUAL')
            BaseMeasurement.objects.create(
                model=self.model, pom=pom, base_value_cm=40, is_active=True)
        self.sf = SizeFitting.objects.create(
            model=self.model, numero=1, codi='SF-182', tipus='SizeSet', estat='Pendent',
            creat_per=self.profile)

        # Gradua una vegada (encara no segellada) i SEGELLA: la forma exacta de la gv 67 real.
        generate_graded_specs(self.sf.id)
        self.gv = GradingVersion.objects.get(size_fitting=self.sf, is_active=True)
        self.gv.aprovada = True
        self.gv.aprovada_per = self.profile
        self.gv.data_aprovacio = datetime.datetime(2026, 7, 1, tzinfo=datetime.timezone.utc)
        self.gv.save()

    def _specs(self, gv=None, pom=None):
        """Petja {talla: valor} d'una versió (per al POM 'A' si no se'n diu un altre)."""
        return {s.size_label: float(s.graded_value_cm)
                for s in GradedSpec.objects.filter(
                    grading_version=(gv or self.gv), pom=(pom or self.pom))}

    def _post(self, view, **kwargs):
        req = self.factory.post('/x/', kwargs.pop('data', {}), format='json')
        force_authenticate(req, user=self.user)
        return view(req, **kwargs)


class ElsSisCaminsTest(_SegellBase):
    """Els SIS camins censats per la diagnosi (§B4.2). Tots han de fer 409, cap ha d'escriure."""

    def test_cami_1_generar_grading_in_place(self):
        from fhort.models_app.views import generate_grading_view
        resp = self._post(generate_grading_view, model_id=self.model.id)   # new_version absent
        self._assert_409(resp)

    def test_cami_2_set_size_override(self):
        from fhort.models_app.views import set_size_override_view
        resp = self._post(set_size_override_view, model_id=self.model.id,
                          data={'pom_id': self.pom.id, 'size_label': 'L', 'valor': 99})
        self._assert_409(resp)
        # …i l'override NO s'ha desat: el rollback dins l'atòmic no és decoratiu.
        self.assertFalse(ModelGradingOverride.objects.filter(model=self.model).exists(),
                         "un 409 no pot deixar l'override desat alimentant la versió segellada")

    def test_cami_3_escalat_ajustar_talla(self):
        from fhort.models_app.views import escalat_ajustar_talla_view
        resp = self._post(escalat_ajustar_talla_view, model_id=self.model.id,
                          data={'pom_id': self.pom.id, 'talla': 'L', 'valor': 99})
        self._assert_409(resp)
        self.assertFalse(ModelGradingOverride.objects.filter(model=self.model).exists())

    def test_cami_4_regenerar_talles(self):
        from fhort.pom.grading_views import regenerate_sizes_view
        self._assert_409(self._post(regenerate_sizes_view, sf_id=self.sf.id))

    def test_cami_5_tancar_base(self):
        """close_base només crida el motor si el SizeFitting NO té cap spec: l'`exists()`
        cross-version el fa no-op altrament (R6 de la diagnosi, la peça 0c — NO és d'aquest
        sprint). Es buiden els specs per arribar de debò al motor i comprovar que el guard hi és:
        una versió segellada i buida NO es pot omplir per aquesta porta."""
        GradedSpec.objects.filter(grading_version=self.gv).delete()
        from fhort.pom.grading_views import close_base_view
        self._assert_409(self._post(close_base_view, sf_id=self.sf.id))

    def test_cami_6_confirmar_talla_base(self):
        """El que MÉS enganyava: aquest camí engolia l'error del motor amb un WARNING al log i
        retornava 200. Sobre una versió segellada, l'usuari hauria vist un OK."""
        from fhort.pom.wizard_views import confirm_base_size_view
        self._assert_409(self._post(confirm_base_size_view, model_id=self.model.id))

    def _assert_409(self, resp):
        self.assertEqual(resp.status_code, 409, f'esperava 409, ha fet {resp.status_code}')
        self.assertEqual(resp.data['error'], 'sealed')
        self.assertEqual(resp.data['codi'], 'GRADING_VERSION_SEALED')
        self.assertEqual(resp.data['version_number'], self.gv.version_number)
        # El 409 ha de DIR LA SORTIDA, no només que no.
        self.assertEqual(resp.data['sortida']['accio'], 'crear_nova_versio')
        self.assertTrue(resp.data['sortida']['body']['new_version'])


class IntegritatDelMotorTest(_SegellBase):
    """El test que resumeix per què existeix G6-B.

    El motor de patrons projecta confiant en `gv.aprovada` (guard dur a
    `patterns/engine/grading_projection.py`). Si el contingut d'una versió aprovada es pot
    reescriure, el flag pot ser cert **mentre les talles ja no són les que es van aprovar**: una
    projecció "aprovada" projectaria unes mesures que ningú no va aprovar mai.
    """

    def test_la_petja_de_la_versio_segellada_es_IDENTICA_despres_dun_rebuig(self):
        abans = self._specs()
        self.assertEqual(abans, {'S': 38.0, 'M': 40.0, 'L': 42.0})
        data_abans = self.gv.data_aprovacio

        # Els sis camins, un darrere l'altre, tots contra la mateixa versió segellada.
        from fhort.models_app.views import (escalat_ajustar_talla_view, generate_grading_view,
                                            set_size_override_view)
        from fhort.pom.grading_views import close_base_view, regenerate_sizes_view
        self._post(generate_grading_view, model_id=self.model.id)
        self._post(set_size_override_view, model_id=self.model.id,
                   data={'pom_id': self.pom.id, 'size_label': 'L', 'valor': 99})
        self._post(escalat_ajustar_talla_view, model_id=self.model.id,
                   data={'pom_id': self.pom.id, 'talla': 'L', 'valor': 99})
        self._post(regenerate_sizes_view, sf_id=self.sf.id)
        self._post(close_base_view, sf_id=self.sf.id)

        self.gv.refresh_from_db()
        self.assertEqual(self._specs(), abans, 'la versió aprovada ha canviat de contingut')
        self.assertTrue(self.gv.aprovada)
        self.assertEqual(self.gv.data_aprovacio, data_abans)
        self.assertEqual(GradingVersion.objects.filter(size_fitting=self.sf).count(), 1,
                         'cap auto-bump: un rebuig no crea versions per la porta del darrere')

    def test_la_sortida_legitima_funciona_i_la_nova_versio_es_editable(self):
        """Refusar sense sortida seria un cul-de-sac. El bump és la sortida, i deixa rastre."""
        from fhort.models_app.views import generate_grading_view

        resp = self._post(generate_grading_view, model_id=self.model.id,
                          data={'new_version': True, 'allow_reopen_sealed': True})

        self.assertEqual(resp.status_code, 200)
        nova = GradingVersion.objects.get(size_fitting=self.sf, is_active=True)
        self.assertEqual(nova.version_number, self.gv.version_number + 1)
        self.assertFalse(nova.aprovada, 'la versió nova neix SENSE segell')

        # La segellada es conserva intacta com a historial, i ja no és l'activa.
        self.gv.refresh_from_db()
        self.assertTrue(self.gv.aprovada)
        self.assertFalse(self.gv.is_active)
        self.assertEqual(self._specs(self.gv), {'S': 38.0, 'M': 40.0, 'L': 42.0})

        # I la nova SÍ que és editable: el guard ja no hi aplica.
        self.assertIsNone(sealed_active_version(self.sf.id))
        self.assertEqual(generate_graded_specs(self.sf.id), 9)

    def test_sense_segell_el_cami_normal_no_es_toca(self):
        """El guard no pot fer nosa a qui no ha segellat res."""
        GradingVersion.objects.filter(pk=self.gv.pk).update(aprovada=False)
        from fhort.pom.grading_views import regenerate_sizes_view

        resp = self._post(regenerate_sizes_view, sf_id=self.sf.id)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['graded_specs_actualitzats'], 9)   # 3 POMs × 3 talles


class CrudDelSegellTest(_SegellBase):
    """R3 — el CRUD REST obert sobre el segell."""

    def _api(self, method, data=None):
        """Per la RUTA real (el router). Un ReadOnlyModelViewSet ni tan sols té les accions
        d'escriptura: el 405 el dona el ROUTER, i és el 405 que veurà un client de debò."""
        from rest_framework.test import APIClient
        # SERVER_NAME: django-tenants resol el tenant pel HOST. Sense el domini del tenant de
        # test, la ruta ni tan sols existeix (404) i el 405 no voldria dir res.
        client = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        client.force_authenticate(user=self.user)
        url = f'/api/v1/grading-versions/{self.gv.pk}/'
        return getattr(client, method)(url, data or {}, format='json')

    def test_PATCH_aprovada_es_mor_amb_405(self):
        """Abans: qualsevol autenticat podia des-aprovar una versió segellada per REST."""
        resp = self._api('patch', {'aprovada': False})

        self.assertEqual(resp.status_code, 405)
        self.gv.refresh_from_db()
        self.assertTrue(self.gv.aprovada, 'el segell segueix posat')

    def test_PUT_i_DELETE_es_moren_amb_405(self):
        self.assertEqual(self._api('put', {'aprovada': False}).status_code, 405)
        self.assertEqual(self._api('delete').status_code, 405)
        self.assertTrue(GradingVersion.objects.filter(pk=self.gv.pk).exists())

    def test_GET_continua_viu(self):
        self.assertEqual(self._api('get').status_code, 200)


class ApproveActionTest(_SegellBase):
    """L'única escriptura que queda: aprovar. I és un gate."""

    def setUp(self):
        super().setUp()
        # Aquesta classe parteix d'una versió NO segellada (és el que anem a segellar).
        GradingVersion.objects.filter(pk=self.gv.pk).update(
            aprovada=False, aprovada_per=None, data_aprovacio=None)
        self.gv.refresh_from_db()

    def _approve(self, user):
        from rest_framework.test import APIClient
        client = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        client.force_authenticate(user=user)
        return client.post(f'/api/v1/grading-versions/{self.gv.pk}/approve/', {}, format='json')

    def test_sense_CLOSE_GATES_es_403(self):
        from fhort.accounts.models import UserProfile
        tecnic = get_user_model().objects.create(username='tecnic')
        prof, _ = UserProfile.objects.get_or_create(
            user=tecnic, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'technician'})
        prof.rol_nom = 'technician'      # el signal el crea amb el rol per defecte
        prof.save(update_fields=['rol_nom'])
        tecnic = get_user_model().objects.get(pk=tecnic.pk)

        resp = self._approve(tecnic)

        self.assertEqual(resp.status_code, 403)
        self.gv.refresh_from_db()
        self.assertFalse(self.gv.aprovada, 'un tècnic no pot segellar producció')

    def test_amb_CLOSE_GATES_el_segell_queda_COMPLET(self):
        """Els tres camps van junts: aprovada + qui + quan. A staging hi ha dues versions
        aprovades amb `aprovada_per=NULL` — el rastre d'un camí que escrivia el flag i prou."""
        resp = self._approve(self.user)   # admin → té CLOSE_GATES

        self.assertEqual(resp.status_code, 200)
        self.gv.refresh_from_db()
        self.assertTrue(self.gv.aprovada)
        self.assertEqual(self.gv.aprovada_per_id, self.profile.id)
        self.assertIsNotNone(self.gv.data_aprovacio)

    def test_es_idempotent_i_no_reescriu_qui_la_va_aprovar(self):
        from fhort.accounts.models import UserProfile
        altre = get_user_model().objects.create(username='altre_admin')
        prof, _ = UserProfile.objects.get_or_create(
            user=altre, defaults={'nom_complet': 'Altre', 'rol_nom': 'admin'})
        prof.rol_nom = 'admin'
        prof.save(update_fields=['rol_nom'])
        altre = get_user_model().objects.get(pk=altre.pk)

        self._approve(self.user)
        self.gv.refresh_from_db()
        primer_aprovador, primera_data = self.gv.aprovada_per_id, self.gv.data_aprovacio

        resp = self._approve(altre)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['ja_estava_aprovada'])
        self.gv.refresh_from_db()
        self.assertEqual(self.gv.aprovada_per_id, primer_aprovador)
        self.assertEqual(self.gv.data_aprovacio, primera_data)

    def test_una_versio_superada_no_es_pot_aprovar(self):
        """Aprovar una versió que ja no serveix ningú deixaria dues aprovades al mateix SF —
        i cap constraint no ho impedeix (R7)."""
        GradingVersion.objects.filter(pk=self.gv.pk).update(is_active=False)

        resp = self._approve(self.user)

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['error'], 'not_active')

    def test_des_aprovar_no_existeix(self):
        """No hi ha endpoint per des-segellar. Se supera creant-ne una de nova, no desdient-se."""
        from fhort.fitting.views import GradingVersionViewSet
        self.assertFalse(hasattr(GradingVersionViewSet, 'unapprove'))
        self.assertFalse(hasattr(GradingVersionViewSet, 'desaprovar'))
