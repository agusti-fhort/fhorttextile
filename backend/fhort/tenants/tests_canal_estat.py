"""RETORN-2 — el canal d'ESTAT, els dos sentits i les seves fronteres.

La federació v2 tenia UN transport, de creació i unidireccional (diagnosi §BLOC 4, R12: «cap
camí de retorn Studio→Brand», verificat per absència). Això vol dir que la peça podia estar en
dues fases alhora sense que ningú se n'assabentés (R2) i que la marca no sabia mai si el que
havia encomanat avançava.

El que defensen aquests tests:
  1. ESTUDI → MARCA: la fase i el resum de maduresa arriben al bessó. **L'estudi mana en la
     fase**: el bessó l'adopta, no la negocia.
  2. MARCA → ESTUDI: prioritat i data_objectiu arriben a CAMPS REALS del bessó. **La marca
     mana en aquests dos**: el que hi hagués a l'estudi es perd, i és la decisió.
  3. Sense vincle ACTIU no passa res, i no peta res: el canal calla.
  4. **CAP HORA, CAP TÈCNIC, CAP COST al payload** — test negatiu explícit sobre les claus
     reals del JSON, no sobre la intenció de qui l'escriu.

    cd backend && venv/bin/python manage.py test fhort.tenants.tests_canal_estat
"""
import datetime

from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_tenant_model, schema_context

from fhort.accounts.models import UserProfile
from fhort.models_app.models import Model
from fhort.tenants.federation_service import (SENTIT_MADURESA, SENTIT_PRIORITAT, resum_maduresa,
                                              sync_estat)
from fhort.tenants.models import Client, TenantLink
from fhort.tasks.models import Customer, ModelTask, TaskType

BRAND = 'BRF'
STUDIO = 'STF'
CODI = 'BRF-SS27-0900'
User = get_user_model()


class CanalEstatTest(TenantTestCase):
    """Tenant per defecte ('test') = ESTUDI. Segon tenant ('brf') = MARCA.

    Les dues cases tenen una fila amb el MATEIX `codi_intern`: és l'únic lligam que existeix
    entre elles (diagnosi §Resum executiu 3) i el que el canal fa servir per trobar el bessó.
    """

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Estudi F'
        tenant.codi_tenant = STUDIO
        tenant.tipologia = Client.TIPOLOGIA_ESTUDI
        tenant.email_facturacio = 'sf@x.com'
        return tenant

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        connection.set_schema_to_public()
        TenantModel = get_tenant_model()
        cls.brand = TenantModel(
            schema_name='brf', nom='Marca F', codi_tenant=BRAND,
            tipologia=Client.TIPOLOGIA_MARCA, email_facturacio='mf@x.com',
        )
        cls.brand.save(verbosity=0)
        cls.brand.domains.create(domain='brf.test.com', is_primary=True)
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

        # La MARCA: el model canònic, assignat a l'estudi.
        with schema_context('brf'):
            Model.objects.all().delete()
            Model.objects.create(
                codi_intern=CODI, codi_tenant=BRAND, any=2027, temporada='SS', sequencial=900,
                nom_prenda='Abric F', studio_assignat=STUDIO, prioritat=3,
            )

        # L'ESTUDI: el bessó EXTERN, amb tasques de veritat.
        with schema_context('test'):
            Model.objects.all().delete()
            cust, _ = Customer.objects.get_or_create(codi=BRAND, defaults={'nom': 'Marca F'})
            m = Model.objects.create(
                codi_intern=CODI, customer=cust, codi_tenant=BRAND, any=2027, temporada='SS',
                sequencial=900, nom_prenda='Abric F', origen=Model.ORIGEN_EXTERN,
                fase_actual='Proto', prioritat=3,
            )
            u, _ = User.objects.get_or_create(username='tecf', defaults={'email': 'tf@x.com'})
            prof, _ = UserProfile.objects.get_or_create(
                user=u, defaults={'nom_complet': 'Tècnic F', 'rol_nom': 'patronista'})
            # Dos tipus diferents: `uniq_prevista_model_tasktype` prohibeix dues previstes del
            # mateix tipus al mateix model (tasks/models.py:110-114).
            tt1, _ = TaskType.objects.get_or_create(code='PATR', defaults={'name': 'Patronatge'})
            tt2, _ = TaskType.objects.get_or_create(code='ESCA', defaults={'name': 'Escalat'})
            ModelTask.objects.create(model=m, task_type=tt1, status='Done', assignee=prof)
            ModelTask.objects.create(model=m, task_type=tt2, status='InProgress', assignee=prof)
            self.model_estudi_pk = m.pk

    def _model_estudi(self):
        return Model.objects.get(pk=self.model_estudi_pk)

    # ── Sentit ESTUDI → MARCA ────────────────────────────────────────────────────────────
    def test_l_estudi_publica_la_maduresa_i_mana_en_la_fase(self):
        with schema_context('test'):
            r = sync_estat(self._model_estudi(), SENTIT_MADURESA)
        self.assertTrue(r['ok'], r)

        with schema_context('brf'):
            bessó = Model.objects.get(codi_intern=CODI)
            # L'ESTUDI MANA EN LA FASE: el bessó l'adopta, no la negocia.
            self.assertEqual(bessó.fase_actual, 'Proto')
            tk = bessó.federacio_estat['tasques']
            self.assertEqual(tk['n_total'], 2)
            self.assertEqual(tk['n_done'], 1)
            self.assertEqual(tk['n_in_progress'], 1)
            self.assertFalse(tk['totes_acabades'])
            self.assertIn('actualitzat_at', bessó.federacio_estat)

    def test_un_model_intern_no_publica_res(self):
        """Un model nascut a casa no té bessó enlloc: no és cosa de ningú més."""
        with schema_context('test'):
            m = self._model_estudi()
            Model.objects.filter(pk=m.pk).update(origen=Model.ORIGEN_INTERN)
            r = sync_estat(self._model_estudi(), SENTIT_MADURESA)
        self.assertFalse(r['ok'])
        self.assertEqual(r['motiu'], 'model_intern')

    def test_una_peca_verge_no_diu_que_esta_llesta(self):
        """`n_total=0` NO és «tot acabat» — mateixa condició que `model_ready_for_gate`."""
        with schema_context('test'):
            ModelTask.objects.all().delete()
            resum = resum_maduresa(self._model_estudi())
        self.assertEqual(resum['tasques']['n_total'], 0)
        self.assertFalse(resum['tasques']['totes_acabades'])

    # ── Sentit MARCA → ESTUDI ────────────────────────────────────────────────────────────
    def test_la_marca_mana_en_prioritat_i_data_objectiu(self):
        with schema_context('test'):   # l'estudi s'havia posat la seva pròpia urgència
            Model.objects.filter(pk=self.model_estudi_pk).update(
                prioritat=5, data_objectiu=datetime.date(2027, 12, 31))

        with schema_context('brf'):
            m = Model.objects.get(codi_intern=CODI)
            Model.objects.filter(pk=m.pk).update(
                prioritat=1, data_objectiu=datetime.date(2027, 4, 1))
            r = sync_estat(Model.objects.get(pk=m.pk), SENTIT_PRIORITAT)
        self.assertTrue(r['ok'], r)

        with schema_context('test'):
            bessó = Model.objects.get(codi_intern=CODI)
            # Camps REALS, no JSON: el planificador de l'estudi ja els llegeix.
            self.assertEqual(bessó.prioritat, 1)
            self.assertEqual(bessó.data_objectiu, datetime.date(2027, 4, 1))

    def test_sense_studio_assignat_la_marca_no_parla(self):
        with schema_context('brf'):
            m = Model.objects.get(codi_intern=CODI)
            Model.objects.filter(pk=m.pk).update(studio_assignat='')
            r = sync_estat(Model.objects.get(pk=m.pk), SENTIT_PRIORITAT)
        self.assertFalse(r['ok'])
        self.assertEqual(r['motiu'], 'sense_studio_assignat')

    # ── Els disparadors (2d): el canal s'obre sol, ningú no l'ha de recordar ─────────────
    def test_el_signal_de_la_marca_dispara_el_sync_sol(self):
        """Un `save()` normal a la marca ha de bastar. El disparador viu al signal i no al
        serializer precisament perquè aquest camí —ORM pelat— també hi passi."""
        with schema_context('brf'):
            m = Model.objects.get(codi_intern=CODI)
            m.prioritat = 1
            m.data_objectiu = datetime.date(2027, 5, 20)
            m.save()
        with schema_context('test'):
            bessó = Model.objects.get(codi_intern=CODI)
            self.assertEqual(bessó.prioritat, 1)
            self.assertEqual(bessó.data_objectiu, datetime.date(2027, 5, 20))

    def test_transicio_de_tasca_publica_la_maduresa_sola(self):
        from fhort.tasks.services_c import transition_task

        with schema_context('test'):
            prof = UserProfile.objects.get(user__username='tecf')
            task = ModelTask.objects.get(model_id=self.model_estudi_pk, task_type__code='ESCA')
            transition_task(task, 'Done', prof)

        with schema_context('brf'):
            tk = Model.objects.get(codi_intern=CODI).federacio_estat['tasques']
            self.assertEqual(tk['n_done'], 2)
            self.assertEqual(tk['n_in_progress'], 0)
            self.assertTrue(tk['totes_acabades'])

    # ── Les fronteres ────────────────────────────────────────────────────────────────────
    def test_sense_vincle_actiu_es_no_op_i_no_peta(self):
        """El pont tancat no és un error: és una relació aturada. Ni excepció ni escriptura."""
        with schema_context('public'):
            TenantLink.objects.update(estat=TenantLink.ESTAT_ATURAT)
        with schema_context('test'):
            r = sync_estat(self._model_estudi(), SENTIT_MADURESA)
        self.assertFalse(r['ok'])
        self.assertEqual(r['motiu'], 'sense_vincle_actiu')
        with schema_context('brf'):
            self.assertIsNone(Model.objects.get(codi_intern=CODI).federacio_estat)

    def test_sense_besso_a_l_altra_banda_es_no_op(self):
        with schema_context('brf'):
            Model.objects.all().delete()
        with schema_context('test'):
            r = sync_estat(self._model_estudi(), SENTIT_MADURESA)
        self.assertFalse(r['ok'])
        self.assertEqual(r['motiu'], 'sense_besso')

    def test_cap_hora_ni_tecnic_al_payload(self):
        """TEST NEGATIU. La doctrina («el Brand no veu ni temps ni tècnics», views_encarrecs:6-8)
        s'ha de poder comprovar sobre les CLAUS REALS del JSON, no sobre la intenció de qui
        l'escriu. El que viatja és un RECOMPTE; qui, quant i quant costa no surten de casa."""
        with schema_context('test'):
            sync_estat(self._model_estudi(), SENTIT_MADURESA)
        with schema_context('brf'):
            payload = Model.objects.get(codi_intern=CODI).federacio_estat

        pla = repr(payload).lower()
        for prohibit in ('minut', 'hora', 'tecnic', 'tècnic', 'assignee', 'timer', 'cost',
                         'preu', 'estimated', 'welford', 'consumption'):
            self.assertNotIn(prohibit, pla, f"«{prohibit}» no pot travessar el canal d'estat")

        self.assertEqual(set(payload), {'fase_actual', 'tasques', 'actualitzat_at'})
        self.assertEqual(set(payload['tasques']),
                         {'n_total', 'n_done', 'n_in_progress', 'totes_acabades'})
