"""F2 · EL GARMENT AL `set_size_override_view` — el lookup s'alinea amb la unicitat real.

Executat amb `manage.py test fhort.models_app.test_f2_garment_override` (el projecte NO fa
servir pytest).

## El defecte que aquest banc fixa per escrit

`ModelGradingOverride` té una `unique` de SIS columnes
—`(model, pom, size_label, capa, instancia, garment)`— i `set_size_override_view` en deia CINC:
el `garment` no hi era ni al lookup ni al payload. Amb dues peces vives que comparteixin un POM,
el `filter` de cinc columnes casa DUES files:

  · `prev` (`.values_list(...).first()`) llegeix el valor de la peça que el planner triï, i el
    `MeasurementChangeLog` que en surt diu que s'ha canviat una mesura que ningú no ha tocat;
  · `update_or_create` peta amb `MultipleObjectsReturned` → 500.

Cens: `docs/ordres/CENS_INSTANCIES_POM_2026-08-25.md`, fila 9 del veredicte. La població que
l'exposa ja existeix a `fhort`: 1320/904, 1379/962, 1380/962.

## ⚠️ PER QUÈ AQUEST BANC CRIDA LA VISTA I NO UNA URL

**`set-size-override/` NO TÉ RUTA** des de D5 (21/07): `models_app/urls.py:238` la declara
jubilada i `fitting/test_e1_r2_estructural.py` és el guardià de frontera que comprova que segueix
sense resoldre. La vista es conserva com a VEHICLE dels bancs que hi proven lleis vives —el
segell G6 ja ho fa (`pom/test_g6_segell.py:117`)— i aquest és el mateix cas.

Això vol dir que el defecte **no és abastable per HTTP avui**: és un defecte de CODI VIU en una
porta desendollada. Es repara igualment perquè la vista és viva, perquè el guardià existeix
justament perquè re-endollar-la és previsible, i perquè un banc que la fa servir de vehicle
n'hereta el comportament. Aquest banc **no re-endolla res**: crida la funció, com el seu germà.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
from fhort.models_app.models import (
    BaseMeasurement, MeasurementChangeLog, Model, ModelGarment, ModelGradingOverride,
    ModelGradingRule,
)
from fhort.models_app.views import set_size_override_view
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem
from fhort.pom.services import generate_graded_specs

#: La peça MARE. No té fila a `ModelGarment` (convenció mandrosa, D3): els seus valors ja són
#: els del `Model`.
MARE = ''
#: La segona prenda. `'02'` és el codi que `ModelGarment` dona a la primera peça materialitzada.
SEGONA = '02'


class _BancDuesPeces(TenantTestCase):
    """Un model que gradua, amb el MATEIX POM mesurat a DUES peces i la versió NO segellada.

    És la forma exacta dels tres parells vius de `fhort` (1320/904, 1379/962, 1380/962), que és
    el que fa que aquest banc provi el defecte real i no una maqueta seva.
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
        from fhort.accounts.models import UserProfile
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create(username='f2')
        # El signal ja crea el perfil amb el rol per defecte (technician): el rol s'assigna
        # explícitament o `_ExecuteTasksCap` donaria 403 despistats. I es rellegeix l'usuari,
        # perquè `user.profile` queda cachejat amb el rol vell i `force_authenticate` passa
        # AQUESTA instància (mateixa lliçó que `pom/test_g6_segell.py`).
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'F2'})
        self.profile.rol_nom = 'admin'
        self.profile.save(update_fields=['rol_nom'])
        self.user = get_user_model().objects.get(pk=self.user.pk)

        self.ss = SizeSystem.objects.create(codi='SS_F2', nom='SS f2', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)

        # UN SOL POM, i és el nus del cas: el defecte només apareix quan DUES peces el
        # comparteixen. Els altres dos hi són perquè el model tingui gruix de mesures.
        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest width')
        self.pom2 = POMMaster.objects.create(codi_client='B', nom_client='Waist width')
        self.pom3 = POMMaster.objects.create(codi_client='C', nom_client='Hip width')

        self.model = Model.objects.create(
            codi_intern='TST-F2', codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Bikini (top + calceta)', size_system=self.ss,
            size_run_model='S·M·L', base_size_label='M',
        )
        # La segona prenda, materialitzada (la mare no en té fila, D3).
        ModelGarment.objects.create(model=self.model, codi=SEGONA, nom='Calceta', ordre=2)

        for pom in (self.pom, self.pom2, self.pom3):
            # La regla NO travessa la instància ni la capa, i SÍ el garment; la 02 no en té de
            # pròpia i hereta la de la mare (`_regla_de`). Això és el que es vol: la mateixa
            # llei d'increments, dues files de valor.
            ModelGradingRule.objects.create(
                model=self.model, pom=pom, logica='LINEAR', increment_base=2,
                actiu=True, origen='MANUAL')
            BaseMeasurement.objects.create(
                model=self.model, pom=pom, base_value_cm=40, is_active=True, garment=MARE)
        # …i el POM compartit, mesurat TAMBÉ a la segona peça, amb un valor DIFERENT: si les
        # dues files acabessin amb el mateix número, una trepitjada no es distingiria d'un encert.
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=30, is_active=True, garment=SEGONA,
            nom_fitxa='A-calceta')

        self.sf, _ = SizeFitting.objects.update_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-F2', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': self.profile},
        )
        generate_graded_specs(self.sf.id)
        self.gv = GradingVersion.objects.get(size_fitting=self.sf, is_active=True)
        # NO es segella: aquest banc vol que les escriptures passin (el 409 ja té el seu, G6).

    # ── helpers ────────────────────────────────────────────────────────────────────────
    def _post(self, **data):
        """Crida la VISTA, no una URL (v. la capçalera del mòdul: la ruta és jubilada)."""
        req = self.factory.post('/x/', data, format='json')
        force_authenticate(req, user=self.user)
        return set_size_override_view(req, model_id=self.model.id)

    def _ovr(self, garment):
        return ModelGradingOverride.objects.filter(
            model=self.model, pom=self.pom, size_label='L', garment=garment).first()


class DuesPecesDuesFilesTest(_BancDuesPeces):
    """EL CAS DEL BRIEF: override a cadascuna de les dues peces → dues files, cap trepitjada."""

    def test_override_a_cada_peca_deixa_DUES_files_amb_el_seu_valor(self):
        r1 = self._post(pom_id=self.pom.id, size_label='L', valor=51)                    # mare
        r2 = self._post(pom_id=self.pom.id, size_label='L', valor=33, garment=SEGONA)     # 02
        self.assertEqual(r1.status_code, 200, r1.data)
        self.assertEqual(r2.status_code, 200, r2.data)

        files = ModelGradingOverride.objects.filter(
            model=self.model, pom=self.pom, size_label='L')
        self.assertEqual(files.count(), 2, 'la segona peça ha de CREAR fila, no reescriure la mare')
        self.assertEqual({f.garment for f in files}, {MARE, SEGONA})
        self.assertEqual(float(self._ovr(MARE).value_cm), 51.0)
        self.assertEqual(float(self._ovr(SEGONA).value_cm), 33.0)

    def test_lordre_invers_dona_el_mateix(self):
        """Si el resultat depengués de qui escriu primer, seria una cursa i no un contracte."""
        self._post(pom_id=self.pom.id, size_label='L', valor=33, garment=SEGONA)
        self._post(pom_id=self.pom.id, size_label='L', valor=51)
        self.assertEqual(float(self._ovr(MARE).value_cm), 51.0)
        self.assertEqual(float(self._ovr(SEGONA).value_cm), 33.0)

    def test_EL_SIMPTOMA_PRIMARI_la_trepitjada_silenciosa(self):
        """El defecte tal com es manifesta PRIMER, i no és el que el cens deia.

        Sense el `garment` al lookup, la crida de la 02 no crea cap fila: `update_or_create`
        casa la de la MARE (el filtre no distingeix) i li reescriu el valor. Una sola fila, cap
        error, 200 OK — la trepitjada és **silenciosa**, que és el mode de fallada dolent.
        Mesurat: amb el lookup revertit, aquest test dona `1 != 2`.
        """
        self._post(pom_id=self.pom.id, size_label='L', valor=51)                  # mare
        self._post(pom_id=self.pom.id, size_label='L', valor=33, garment=SEGONA)   # 02
        self.assertEqual(
            ModelGradingOverride.objects.filter(
                model=self.model, pom=self.pom, size_label='L').count(), 2,
            'la segona peça ha de CREAR fila, no reescriure la de la mare')
        self.assertEqual(float(self._ovr(MARE).value_cm), 51.0,
                         'el valor de la mare no pot haver-lo escrit la 02')

    def test_EL_SEGON_SIMPTOMA_escriure_a_la_mare_segrestava_la_fila_de_la_02(self):
        """Amb NOMÉS la fila de la 02 viva, escriure a la MARE se n'enduia la fila de la 02.

        El `filter` de cinc columnes hi casava una sola fila —la de la 02— i `update_or_create`
        li feia UPDATE: la mare no arribava a tenir fila i la 02 es quedava amb el número de la
        mare. Mesurat amb el lookup revertit: `self._ovr(MARE)` és `None`.

        La fila prèvia de la 02 es fabrica per ORM perquè és el que hi deixa l'ALTRE camí, el
        germà `escalat_ajustar_talla_view`, que sí que sap dir el garment.
        """
        ModelGradingOverride.objects.create(
            model=self.model, pom=self.pom, size_label='L', garment=SEGONA,
            value_cm=33, motiu='Escalat · ajust talla (sense propagació)')
        resp = self._post(pom_id=self.pom.id, size_label='L', valor=51)
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', resp))
        self.assertIsNotNone(self._ovr(MARE), 'la mare ha de tenir fila PRÒPIA')
        self.assertEqual(float(self._ovr(MARE).value_cm), 51.0)
        self.assertEqual(float(self._ovr(SEGONA).value_cm), 33.0, 'la 02 no s\'ha de moure')

    def test_EL_TERCER_SIMPTOMA_amb_les_DUES_files_vives_petava(self):
        """I aquí sí, el `MultipleObjectsReturned`: vol les DUES files ja escrites.

        És la condició que aquesta porta tota sola **no podia fabricar mai** (mai no arribava a
        crear la segona); la deixa el germà d'Escalat escrivint la mare i la 02. Amb les dues
        vives, el `filter` de cinc columnes casa DUES files i el `get()` intern d'
        `update_or_create` peta. Sense el fix aquest test és un ERROR, no un FAIL.
        """
        for garment, valor in ((MARE, 50), (SEGONA, 33)):
            ModelGradingOverride.objects.create(
                model=self.model, pom=self.pom, size_label='L', garment=garment,
                value_cm=valor, motiu='Escalat · ajust talla (sense propagació)')
        resp = self._post(pom_id=self.pom.id, size_label='L', valor=51)
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', resp))
        self.assertEqual(float(self._ovr(MARE).value_cm), 51.0)
        self.assertEqual(float(self._ovr(SEGONA).value_cm), 33.0)

    def test_reescriure_una_peca_no_toca_la_germana(self):
        self._post(pom_id=self.pom.id, size_label='L', valor=51)
        self._post(pom_id=self.pom.id, size_label='L', valor=33, garment=SEGONA)
        self._post(pom_id=self.pom.id, size_label='L', valor=52)          # re-edita la mare
        self.assertEqual(
            ModelGradingOverride.objects.filter(
                model=self.model, pom=self.pom, size_label='L').count(), 2,
            'una re-edició és un UPDATE, no una fila nova')
        self.assertEqual(float(self._ovr(MARE).value_cm), 52.0)
        self.assertEqual(float(self._ovr(SEGONA).value_cm), 33.0)


class ElContracteDelSentinellaTest(_BancDuesPeces):
    """`''` per defecte: el comportament d'avui per a qui no diu el garment (llei no-NULL)."""

    def test_sense_garment_al_payload_escriu_a_la_MARE(self):
        self._post(pom_id=self.pom.id, size_label='L', valor=51)
        self.assertIsNotNone(self._ovr(MARE))
        self.assertIsNone(self._ovr(SEGONA))

    def test_un_None_explicit_val_com_no_dir_res(self):
        """`_identitat_de_mesura`: la columna és NOT NULL i un client que envia `null` vol dir
        «la de sempre». Sense això s'hi desaria el text «None»."""
        resp = self._post(pom_id=self.pom.id, size_label='L', valor=51, garment=None)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIsNotNone(self._ovr(MARE))
        self.assertEqual(
            ModelGradingOverride.objects.filter(model=self.model).exclude(garment=MARE).count(), 0)

    def test_la_resposta_diu_quina_peca_sha_escrit(self):
        self.assertEqual(self._post(pom_id=self.pom.id, size_label='L', valor=51).data['garment'],
                         MARE)
        self.assertEqual(
            self._post(pom_id=self.pom.id, size_label='L', valor=33, garment=SEGONA).data['garment'],
            SEGONA)


class ElRastreParlaDeLaPecaCorrectaTest(_BancDuesPeces):
    """El segon mig defecte: `prev` i el log. Una taula APPEND-ONLY no es pot corregir després."""

    def test_el_log_porta_el_garment_de_la_fila_tocada(self):
        self._post(pom_id=self.pom.id, size_label='L', valor=33, garment=SEGONA)
        log = MeasurementChangeLog.objects.filter(
            model=self.model, pom=self.pom, motiu='Override talla L').latest('id')
        self.assertEqual(log.garment, SEGONA)

    def test_el_valor_anterior_es_el_DAQUESTA_peca_i_no_el_de_la_germana(self):
        """Amb el filtre curt, `prev` podia agafar el valor de l'altra peça i el log mentia."""
        self._post(pom_id=self.pom.id, size_label='L', valor=51)                 # mare: None → 51
        self._post(pom_id=self.pom.id, size_label='L', valor=33, garment=SEGONA)  # 02: None → 33
        primer_de_la_02 = MeasurementChangeLog.objects.filter(
            model=self.model, pom=self.pom, garment=SEGONA).earliest('id')
        self.assertIsNone(primer_de_la_02.valor_anterior,
                          'la primera escriptura de la 02 no ve de cap valor: la mare no hi compta')

        self._post(pom_id=self.pom.id, size_label='L', valor=34, garment=SEGONA)  # 02: 33 → 34
        segon_de_la_02 = MeasurementChangeLog.objects.filter(
            model=self.model, pom=self.pom, garment=SEGONA).latest('id')
        self.assertAlmostEqual(float(segon_de_la_02.valor_anterior), 33.0)

    def test_la_lectura_de_retorn_no_torna_el_graded_de_la_germana(self):
        """`GradedSpec` també té sis columnes; el filtre de retorn en deia tres i el `.first()`
        sense `order_by` podia servir la fila de l'altra peça amb un 200 OK."""
        resp = self._post(pom_id=self.pom.id, size_label='L', valor=33, garment=SEGONA)
        esperat = (GradedSpec.objects
                   .filter(grading_version=self.gv, pom=self.pom, size_label='L',
                           garment=SEGONA)
                   .values_list('graded_value_cm', flat=True).first())
        self.assertIsNotNone(esperat, 'el motor ha d\'haver emès el spec de la 02')
        self.assertAlmostEqual(resp.data['graded_value_cm'], float(esperat))


class UnaSolaPecaComportamentIdenticTest(TenantTestCase):
    """El 100% del corpus d'avui: un model d'UNA peça. Res no pot canviar-hi."""

    @classmethod
    def setup_tenant(cls, tenant):
        return _BancDuesPeces.setup_tenant(tenant)

    def setUp(self):
        from fhort.accounts.models import UserProfile
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create(username='f2solo')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'F2 solo'})
        self.profile.rol_nom = 'admin'
        self.profile.save(update_fields=['rol_nom'])
        self.user = get_user_model().objects.get(pk=self.user.pk)

        self.ss = SizeSystem.objects.create(codi='SS_F2S', nom='SS f2 solo', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.pom = POMMaster.objects.create(codi_client='A', nom_client='Chest width')
        self.model = Model.objects.create(
            codi_intern='TST-F2S', codi_tenant='TST', any=2026, sequencial=2,
            nom_prenda='Samarreta', size_system=self.ss,
            size_run_model='S·M·L', base_size_label='M',
        )
        ModelGradingRule.objects.create(model=self.model, pom=self.pom, logica='LINEAR',
                                        increment_base=2, actiu=True, origen='MANUAL')
        BaseMeasurement.objects.create(model=self.model, pom=self.pom, base_value_cm=40,
                                       is_active=True)
        self.sf, _ = SizeFitting.objects.update_or_create(
            model=self.model, numero=1,
            defaults={'codi': 'SF-F2S', 'tipus': 'SizeSet', 'estat': 'Pendent',
                      'creat_per': self.profile})
        generate_graded_specs(self.sf.id)

    def _post(self, **data):
        req = self.factory.post('/x/', data, format='json')
        force_authenticate(req, user=self.user)
        return set_size_override_view(req, model_id=self.model.id)

    def test_dues_crides_seguides_son_UNA_fila_i_la_ultima_mana(self):
        """Idempotència: era per `(model, pom, size_label)` i ara ho és per `(…, garment)`.
        Amb una sola peça les dues frases descriuen exactament el mateix conjunt de files."""
        self.assertEqual(self._post(pom_id=self.pom.id, size_label='L', valor=51).status_code, 200)
        self.assertEqual(self._post(pom_id=self.pom.id, size_label='L', valor=52).status_code, 200)
        files = ModelGradingOverride.objects.filter(model=self.model, pom=self.pom, size_label='L')
        self.assertEqual(files.count(), 1)
        self.assertEqual(files.first().garment, MARE)
        self.assertEqual(float(files.first().value_cm), 52.0)

    def test_dues_talles_conviuen_com_sempre(self):
        """L'altra promesa del docstring de la vista: editar una 2a talla manté la 1a."""
        self._post(pom_id=self.pom.id, size_label='L', valor=51)
        self._post(pom_id=self.pom.id, size_label='S', valor=39)
        self.assertEqual(
            ModelGradingOverride.objects.filter(model=self.model, pom=self.pom).count(), 2)
