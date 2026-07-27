"""RETORN-1 — l'enviament de FEINA de l'estudi a la marca.

La federació v2 movia 14 camps del `Model` i CAP fila de cap altra taula (diagnosi §Resum
executiu 1): la marca encomanava i després no tornava a veure res del que havia encomanat. El
canal de DADES és un ACTE HUMÀ (decisió del Patró C) i aquests tests defensen les seves lleis.

El que defensen:
  1. Enviament complet: mesures, regles i fitxers arriben al bessó amb origen 'FEDERAT'.
  2. Re-enviar és IDEMPOTENT: ni duplica mesures ni infla la cadena de versions dels fitxers
     (guarda per checksum).
  3. SOBIRANIA DEL DESTÍ: una mesura MANUAL de la marca no es trepitja mai; el TEMPLATE buit
     sí que s'omple. La regla resident de la marca tampoc es toca.
  4. POM no aparellat: NO viatja i s'informa (llei de CONFIG_KEYS, mai bloquejar).
  5. TEST NEGATIU: ni el `.ftt`, ni els patrons, ni les tasques entren mai al paquet.

    cd backend && venv/bin/python manage.py test fhort.tenants.tests_enviament_feina
"""
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model, schema_context

from fhort.accounts.models import UserProfile
from fhort.models_app.models import (BaseMeasurement, Model, ModelFitxer, ModelGradingRule,
                                     Watchpoint)
from fhort.models_app.services_fitxers import save_model_file
from fhort.pom.models import POMGlobal, POMMaster
from fhort.tasks.models import Customer, ModelTask, TaskType
from fhort.tenants.federation_service import FederacioError, envia_a_la_marca
from fhort.tenants.models import Client, TenantLink

BRAND = 'BRG'
STUDIO = 'STG'
CODI = 'BRG-SS27-1100'
User = get_user_model()


def _poms(prefix):
    """Catàleg mínim d'una casa. `POMGlobal.codi` és el diccionari CANÒNIC i és el que fa
    d'aparellador entre cases; `codi_client` és nomenclatura local i aquí es fa DIFERENT a
    posta, perquè el test comprovi que l'aparellament va pel global i no per casualitat."""
    poms = {}
    for codi_global, nom in (('CHEST', 'Chest'), ('WAIST', 'Waist')):
        pg, _ = POMGlobal.objects.get_or_create(
            codi=codi_global, defaults={'nom_en': nom, 'nom_ca': nom})
        poms[codi_global] = POMMaster.objects.create(
            pom_global=pg, codi_client=f'{prefix}-{codi_global}', nom_client=nom)
    return poms


class EnviamentFeinaTest(TenantTestCase):
    """Tenant per defecte ('test') = ESTUDI (qui envia). Segon tenant ('brg') = MARCA."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Estudi G'
        tenant.codi_tenant = STUDIO
        tenant.tipologia = Client.TIPOLOGIA_ESTUDI
        tenant.email_facturacio = 'sg@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connection.set_schema_to_public()
        TenantModel = get_tenant_model()
        cls.brand = TenantModel(
            schema_name='brg', nom='Marca G', codi_tenant=BRAND,
            tipologia=Client.TIPOLOGIA_MARCA, email_facturacio='mg@x.com',
        )
        cls.brand.save(verbosity=0)
        cls.brand.domains.create(domain='brg.test.com', is_primary=True)
        connection.set_tenant(cls.tenant)

    @classmethod
    def tearDownClass(cls):
        connection.set_schema_to_public()
        cls.brand.delete(force_drop=True)
        super().tearDownClass()

    def setUp(self):
        with schema_context('public'):
            TenantLink.objects.all().delete()
            TenantLink.objects.create(brand_codi_tenant=BRAND, studio_codi_tenant=STUDIO)

        # ── LA MARCA: el model canònic i el seu catàleg (nomenclatura pròpia).
        with schema_context('brg'):
            Watchpoint.objects.all().delete()
            BaseMeasurement.objects.all().delete()
            ModelGradingRule.objects.all().delete()
            ModelFitxer.objects.all().delete()
            Model.objects.all().delete()
            POMMaster.objects.all().delete()
            self.poms_marca = _poms('MK')
            Model.objects.create(
                codi_intern=CODI, codi_tenant=BRAND, any=2027, temporada='SS', sequencial=1100,
                nom_prenda='Vestit G', studio_assignat=STUDIO, base_size_label='M',
                size_run_model='S·M·L',
            )

        # ── L'ESTUDI: el bessó EXTERN amb la feina feta.
        with schema_context('test'):
            BaseMeasurement.objects.all().delete()
            ModelGradingRule.objects.all().delete()
            ModelFitxer.objects.all().delete()
            Model.objects.all().delete()
            POMMaster.objects.all().delete()
            poms = _poms('ST')
            # Un POM que la marca NO té al catàleg: no s'ha d'aparellar i no ha de viatjar.
            pg_orfe, _ = POMGlobal.objects.get_or_create(
                codi='HPS', defaults={'nom_en': 'HPS', 'nom_ca': 'HPS'})
            orfe = POMMaster.objects.create(pom_global=pg_orfe, codi_client='ST-HPS',
                                            nom_client='HPS')
            cust, _ = Customer.objects.get_or_create(codi=BRAND, defaults={'nom': 'Marca G'})
            m = Model.objects.create(
                codi_intern=CODI, customer=cust, codi_tenant=BRAND, any=2027, temporada='SS',
                sequencial=1100, nom_prenda='Vestit G', origen=Model.ORIGEN_EXTERN,
                base_size_label='M', size_run_model='S·M·L',
            )
            BaseMeasurement.objects.create(model=m, pom=poms['CHEST'], base_value_cm=52.0,
                                           origen='MANUAL', ordre=1)
            BaseMeasurement.objects.create(model=m, pom=poms['WAIST'], base_value_cm=41.5,
                                           origen='FITTED', ordre=2)
            BaseMeasurement.objects.create(model=m, pom=orfe, base_value_cm=18.0,
                                           origen='MANUAL', ordre=3)
            ModelGradingRule.objects.create(model=m, pom=poms['CHEST'], logica='LINEAR',
                                            increment_base=2, origen='MANUAL')
            # Fitxers: un que ha de viatjar i dos que no han de sortir mai de casa.
            save_model_file(m, ContentFile(b'<svg/>', name='x.svg'), tipus='SKETCH_SVG',
                            nom='x.svg')
            save_model_file(m, ContentFile(b'FTT-VIU', name='x.ftt'), tipus='TECHSHEET',
                            nom='x.ftt')
            save_model_file(m, ContentFile(b'DXF', name='x.dxf'), tipus='PATRO', nom='x.dxf')
            u, _ = User.objects.get_or_create(username='tecg', defaults={'email': 'tg@x.com'})
            prof, _ = UserProfile.objects.get_or_create(
                user=u, defaults={'nom_complet': 'Tècnic G', 'rol_nom': 'patronista'})
            tt, _ = TaskType.objects.get_or_create(code='PATG', defaults={'name': 'Patronatge'})
            ModelTask.objects.create(model=m, task_type=tt, status='Done', assignee=prof)
            self.model_pk = m.pk

    def _envia(self):
        with schema_context('test'):
            return envia_a_la_marca(Model.objects.get(pk=self.model_pk))

    # ── 1. Enviament complet ─────────────────────────────────────────────────────────────
    def test_enviament_complet(self):
        informe = self._envia()
        self.assertEqual(informe['viatjat']['mesures'], 2)
        self.assertEqual(informe['viatjat']['regles'], 1)
        self.assertEqual(informe['viatjat']['fitxers'], 1)

        with schema_context('brg'):
            twin = Model.objects.get(codi_intern=CODI)
            bms = {bm.pom.pom_global.codi: bm for bm in
                   BaseMeasurement.objects.filter(model=twin).select_related('pom__pom_global')}
            self.assertEqual(set(bms), {'CHEST', 'WAIST'})
            self.assertEqual(bms['CHEST'].base_value_cm, 52.0)
            # L'aparellament ha anat pel diccionari GLOBAL: el codi_client de les dues cases
            # és diferent a posta i la mesura ha caigut igualment al POM correcte.
            self.assertEqual(bms['CHEST'].pom.codi_client, 'MK-CHEST')
            # `FEDERAT` i no `MANUAL`: el valor és cert, però qui el va mesurar és l'altra casa.
            self.assertEqual(bms['CHEST'].origen, 'FEDERAT')
            self.assertEqual(ModelGradingRule.objects.filter(model=twin).count(), 1)
            self.assertEqual(ModelGradingRule.objects.get(model=twin).origen, 'FEDERAT')
            f = ModelFitxer.objects.get(model=twin)
            self.assertEqual(f.tipus, 'SKETCH_SVG')
            self.assertEqual(f.versio, 1)   # cadena PRÒPIA del destí, no la de l'estudi

    def test_l_informe_arriba_com_a_watchpoint_a_la_marca(self):
        self._envia()
        with schema_context('brg'):
            wp = Watchpoint.objects.get(model__codi_intern=CODI)
            self.assertEqual(wp.estat, 'open')
            # `dades=None` a posta: `recompute_import_watchpoint` reclama tot WP obert amb
            # task IS NULL i dades no-null i li reescriu el text.
            self.assertIsNone(wp.dades)
            self.assertIn('HPS (ST-HPS)', wp.text)   # el POM que no ha viatjat, dit pel seu nom

    # ── 2. Idempotència ──────────────────────────────────────────────────────────────────
    def test_re_enviar_no_duplica_res(self):
        self._envia()
        segon = self._envia()
        self.assertEqual(segon['viatjat']['mesures'], 0)   # ja hi eren: sobirania del destí
        self.assertEqual(segon['saltat']['fitxers'], 1)    # mateix checksum → cap versió nova
        with schema_context('brg'):
            twin = Model.objects.get(codi_intern=CODI)
            self.assertEqual(BaseMeasurement.objects.filter(model=twin).count(), 2)
            self.assertEqual(ModelGradingRule.objects.filter(model=twin).count(), 1)
            self.assertEqual(ModelFitxer.objects.filter(model=twin).count(), 1)

    # ── 3. Sobirania del destí ───────────────────────────────────────────────────────────
    def test_la_marca_es_sobirana_del_seu_schema(self):
        """Un MANUAL de la marca no es trepitja; un TEMPLATE buit sí que s'omple."""
        with schema_context('brg'):
            twin = Model.objects.get(codi_intern=CODI)
            BaseMeasurement.objects.create(model=twin, pom=self.poms_marca['CHEST'],
                                           base_value_cm=99.9, origen='MANUAL')
            BaseMeasurement.objects.create(model=twin, pom=self.poms_marca['WAIST'],
                                           base_value_cm=None, origen='TEMPLATE')
            ModelGradingRule.objects.create(model=twin, pom=self.poms_marca['CHEST'],
                                            logica='FIXED', origen='MANUAL')

        informe = self._envia()
        self.assertEqual(informe['saltat']['mesures'], 1)   # el MANUAL, intacte
        self.assertEqual(informe['saltat']['regles'], 1)
        self.assertEqual(informe['viatjat']['mesures'], 1)  # el TEMPLATE buit, omplert

        with schema_context('brg'):
            twin = Model.objects.get(codi_intern=CODI)
            chest = BaseMeasurement.objects.get(model=twin, pom=self.poms_marca['CHEST'])
            self.assertEqual(chest.base_value_cm, 99.9)
            self.assertEqual(chest.origen, 'MANUAL')
            waist = BaseMeasurement.objects.get(model=twin, pom=self.poms_marca['WAIST'])
            self.assertEqual(waist.base_value_cm, 41.5)
            self.assertEqual(waist.origen, 'FEDERAT')
            self.assertEqual(ModelGradingRule.objects.get(model=twin).logica, 'FIXED')

    def test_talles_divergents_envien_pertinenca_pero_cap_valor(self):
        """Un valor està expressat EN UNA TALLA. Guard transposat de `copiar_de_model_view`."""
        with schema_context('brg'):
            Model.objects.filter(codi_intern=CODI).update(base_size_label='L')
        informe = self._envia()
        self.assertEqual(informe['viatjat']['mesures'], 0)
        self.assertEqual(informe['viatjat']['pertinences'], 2)
        self.assertTrue(any('DIVERGENTS' in a for a in informe['avisos']))
        with schema_context('brg'):
            twin = Model.objects.get(codi_intern=CODI)
            for bm in BaseMeasurement.objects.filter(model=twin):
                self.assertIsNone(bm.base_value_cm)
                self.assertEqual(bm.origen, 'TEMPLATE')

    # ── 4. No aparellats ─────────────────────────────────────────────────────────────────
    def test_pom_no_aparellat_s_informa_i_no_viatja(self):
        informe = self._envia()
        self.assertEqual(informe['no_aparellat'], ['HPS (ST-HPS)'])
        with schema_context('brg'):
            twin = Model.objects.get(codi_intern=CODI)
            self.assertEqual(BaseMeasurement.objects.filter(model=twin).count(), 2)

    # ── 5. Les fronteres ─────────────────────────────────────────────────────────────────
    def test_ni_el_ftt_ni_els_patrons_ni_les_tasques_surten_de_casa(self):
        """TEST NEGATIU. El .ftt i les tasques són decisió del Patró C; el PATRÓ té la seva
        pròpia porta (patterns.ExportAcknowledgement) i no ha de sortir per aquesta."""
        self._envia()
        with schema_context('brg'):
            twin = Model.objects.get(codi_intern=CODI)
            tipus = set(ModelFitxer.objects.filter(model=twin).values_list('tipus', flat=True))
            self.assertNotIn('TECHSHEET', tipus)
            self.assertNotIn('PATRO', tipus)
            self.assertEqual(tipus, {'SKETCH_SVG'})
            self.assertEqual(ModelTask.objects.filter(model=twin).count(), 0)

    def test_un_model_intern_no_te_on_anar(self):
        with schema_context('test'):
            Model.objects.filter(pk=self.model_pk).update(origen=Model.ORIGEN_INTERN)
            with self.assertRaises(FederacioError) as ctx:
                envia_a_la_marca(Model.objects.get(pk=self.model_pk))
        self.assertEqual(ctx.exception.codi, 'model_no_extern')

    def test_sense_besso_a_la_marca_no_s_envia_res(self):
        with schema_context('brg'):
            Model.objects.all().delete()
        with self.assertRaises(FederacioError) as ctx:
            self._envia()
        self.assertEqual(ctx.exception.codi, 'besso_missing')

    def test_el_pont_tancat_atura_l_enviament(self):
        with schema_context('public'):
            TenantLink.objects.update(estat=TenantLink.ESTAT_ATURAT)
        with self.assertRaises(FederacioError) as ctx:
            self._envia()
        self.assertEqual(ctx.exception.codi, 'link_not_active')
