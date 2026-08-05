"""F1.1 · LA RONDA — la sortida de D-5, i el cas §S-4 convertit en test positiu.

Una tasca amb línia en albarà EMÈS no es pot reobrir (`transition_task`, guard `tasca_albaranada`).
Fins avui això deixava el model tapiat: 7× 409 en dues hores sobre el model 188 i tota la feina
posterior sense rellotge. La sortida no és aixecar el guard —el que s'ha facturat s'ha facturat—
sinó obrir una VOLTA nova amb tasques pròpies, germanes de les velles per `mare`.

El cas que aquest fitxer converteix en garantia és el §S-4 de `DIAGNOSI_PREF1_CICLE_TASCA.md`:

> «`_close_pom_task_for_model` agafa `order_by('id').first()` — LA MÉS ANTIGA. Amb dues tasques
>  `pom`, «Gravar POM» de la ronda 2 tancaria la ronda 1.»

Aquí es comprova que ja no: `tasca_vigent` resol la de la ronda, i tancar-la deixa la ronda 1
INTACTA.

Convenció del repo: `python manage.py test fhort.tasks.test_ronda` (no pytest).
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GarmentType
from fhort.tasks.models import Customer, GarmentTypeItem, ModelTask, Ronda, TaskType
from fhort.tasks.services_r import (RondaError, obrir_ronda, ronda_lliurable, tancar_ronda,
                                    tasca_vigent)


class RondaTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TRO'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='tecronda')
        self.prof, _ = UserProfile.objects.get_or_create(user=self.user)
        self.customer = Customer.objects.create(codi='CRO', nom='Client de prova')
        gt = GarmentType.objects.create(codi_client='GTR', nom_client='Família', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_r', name='Item R')
        # El tenant de test ja arriba amb el catàleg canònic sembrat: es REUSA, no es duplica
        # (`code` és unique). Provar contra els codes reals també és més honest.
        self.tt_pom, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.tt_fitxa, _ = TaskType.objects.get_or_create(
            code='tech_sheet', defaults={'name': 'Fitxa tècnica', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='TRO-SS26-0001', codi_tenant='TRO', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')
        # La volta 1: la feina de sempre, sense ronda (ronda NULL = implícita).
        self.pom_r1 = ModelTask.objects.create(model=self.model, task_type=self.tt_pom,
                                               order=0, status='Done', origen='prevista')
        self.fitxa_r1 = ModelTask.objects.create(model=self.model, task_type=self.tt_fitxa,
                                                 order=1, status='Done', origen='prevista')

    # ── L'obertura ───────────────────────────────────────────────────────────
    def test_obrir_ronda_crea_seq_2_i_les_tasques_ad_hoc(self):
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom', 'tech_sheet'])
        self.assertEqual(r.seq, 2)
        self.assertIsNone(r.tancada_el)
        self.assertEqual(r.tasques.count(), 2)
        for t in r.tasques.all():
            self.assertEqual(t.origen, 'ad_hoc')
            self.assertEqual(t.status, 'Pending')
            self.assertEqual(t.motiu, Ronda.MOTIU_NOVA_MOSTRA)

    def test_la_filla_apunta_a_la_mare_homonima(self):
        """La genealogia ha de dir de QUINA tasca és repetició, no només que ho és."""
        r = obrir_ronda(self.model, Ronda.MOTIU_CORRECCIO, ['pom', 'tech_sheet'])
        pom_r2 = r.tasques.get(task_type=self.tt_pom)
        fitxa_r2 = r.tasques.get(task_type=self.tt_fitxa)
        self.assertEqual(pom_r2.mare, self.pom_r1)
        self.assertEqual(fitxa_r2.mare, self.fitxa_r1)
        self.assertEqual(list(self.pom_r1.filles.all()), [pom_r2])

    def test_la_unique_parcial_deixa_conviure_prevista_i_ad_hoc(self):
        """Si això peta, la constraint no era parcial i tota la ronda cau."""
        obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        self.assertEqual(
            ModelTask.objects.filter(model=self.model, task_type=self.tt_pom).count(), 2)

    def test_no_es_poden_obrir_dues_rondes_alhora(self):
        obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        with self.assertRaises(RondaError):
            obrir_ronda(self.model, Ronda.MOTIU_CORRECCIO, ['pom'])

    def test_ronda_amb_code_inexistent_es_rebutja_sencera(self):
        with self.assertRaises(RondaError):
            obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom', 'no_existeix'])
        self.assertEqual(Ronda.objects.filter(model=self.model).count(), 0)
        self.assertEqual(ModelTask.objects.filter(origen='ad_hoc').count(), 0)

    def test_motiu_desconegut_es_rebutja(self):
        with self.assertRaises(RondaError):
            obrir_ronda(self.model, 'perque_si', ['pom'])

    # ── §S-4, com a garantia ─────────────────────────────────────────────────
    def test_tasca_vigent_resol_la_de_la_ronda_oberta(self):
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        self.assertEqual(tasca_vigent(self.model, 'pom'), r.tasques.get())

    def test_la_ronda_no_cobreix_tots_els_codes_i_la_resta_cau_a_la_prevista(self):
        """Regla 2: una ronda de només `pom` no pot deixar `tech_sheet` sense tasca vigent."""
        obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        self.assertEqual(tasca_vigent(self.model, 'tech_sheet'), self.fitxa_r1)

    def test_S4_el_desat_de_la_ronda_2_NO_toca_la_ronda_1(self):
        """EL CAS EXACTE DE §S-4. Amb el criteri vell (`order_by('id').first()`) el desat de la
        volta 2 hauria resolt la tasca de la volta 1 — i, aleshores, l'hauria TANCADA."""
        from fhort.models_app.views import _assegura_pom_task_oberta

        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        pom_r2 = r.tasques.get(task_type=self.tt_pom)
        pom_r1_updated_abans = ModelTask.objects.get(pk=self.pom_r1.pk).updated_at

        res = _assegura_pom_task_oberta(self.model, self.prof)

        self.assertEqual(res.get('task_id'), pom_r2.pk,
                         'El desat ha resolt una tasca que no és la de la ronda oberta.')
        pom_r1_ara = ModelTask.objects.get(pk=self.pom_r1.pk)
        self.assertEqual(pom_r1_ara.updated_at, pom_r1_updated_abans,
                         'La ronda 1 s\'ha tocat: exactament el dany que §S-4 anunciava.')
        self.assertEqual(pom_r1_ara.status, 'Done')

    def test_el_desat_obre_la_tasca_i_no_la_tanca(self):
        """F1.2 · D-2 en una línia: desar deixa la tasca EN CURS, mai Done."""
        from fhort.models_app.views import _assegura_pom_task_oberta

        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        pom_r2 = r.tasques.get(task_type=self.tt_pom)
        self.assertEqual(pom_r2.status, 'Pending')

        res = _assegura_pom_task_oberta(self.model, self.prof)

        pom_r2.refresh_from_db()
        self.assertTrue(res['oberta'])
        self.assertEqual(pom_r2.status, 'InProgress')

    def test_el_desat_es_idempotent_sobre_una_tasca_ja_oberta(self):
        """El ping-pong es mesurava en transicions repetides. Desar dos cops no n'ha d'escriure
        cap de nova."""
        from fhort.tasks.models import TaskTransition
        from fhort.models_app.views import _assegura_pom_task_oberta

        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        pom_r2 = r.tasques.get(task_type=self.tt_pom)
        _assegura_pom_task_oberta(self.model, self.prof)
        n = TaskTransition.objects.filter(model_task=pom_r2).count()

        _assegura_pom_task_oberta(self.model, self.prof)
        _assegura_pom_task_oberta(self.model, self.prof)

        self.assertEqual(TaskTransition.objects.filter(model_task=pom_r2).count(), n)

    def test_tancar_ronda_torna_la_vigencia_a_la_prevista(self):
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        tancar_ronda(r)
        self.assertIsNotNone(r.tancada_el)
        self.assertEqual(tasca_vigent(self.model, 'pom'), self.pom_r1)

    def test_la_ronda_3_es_numera_despres_de_la_2_tancada(self):
        tancar_ronda(obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom']))
        self.assertEqual(obrir_ronda(self.model, Ronda.MOTIU_CORRECCIO, ['pom']).seq, 3)

    # ── El lliurable, abans que el flag existeixi (F1.6) ─────────────────────
    def test_ronda_lliurable_es_fals_mentre_no_hi_hagi_flag(self):
        """`es_lliurable` neix a F1.6. Fins llavors res no és lliurable — i sobretot, això no
        pot petar amb FieldError."""
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom', 'tech_sheet'])
        self.assertFalse(ronda_lliurable(r))
