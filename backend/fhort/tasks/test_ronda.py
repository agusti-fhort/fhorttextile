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
from fhort.tasks.services_r import (RondaError, obrir_correccio, obrir_ronda,
                                    ronda_lliurable, tancar_ronda,
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
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom', 'tech_sheet'])
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
            obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])

    def test_el_refus_de_la_segona_ronda_diu_QUINA_volta_bloqueja(self):
        """M2 · CODA-BIS — el missatge és el que arriba a l'usuari, i ha de ser accionable.

        El guard ja hi era; el que no hi era és QUÈ fer-hi. Deia només «tanca-la», i això amagava
        la sortida normal —una volta es tanca **entregant-la** (FIT-13), i «tancar» sol no té cap
        porta pròpia— i tampoc deia QUINA volta bloqueja, que en un model amb història és
        justament el que no se sap. Aquest text viatja fins al toast de «+ Nova ronda», que és
        visible sempre precisament perquè el motiu el digui el servidor.
        """
        oberta = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        with self.assertRaises(RondaError) as cm:
            obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        missatge = str(cm.exception)
        self.assertIn(f'R{oberta.seq}', missatge,
                      'El refús no diu quina volta bloqueja.')
        self.assertIn('entrega', missatge.lower(),
                      'El refús no diu la sortida normal (entregar-la).')
        # …i el refús no ha deixat cap volta nova a mitges.
        self.assertEqual(Ronda.objects.filter(model=self.model).count(), 1)

    def test_obrir_ronda_ja_no_accepta_una_correccio(self):
        """S-20 — la correcció té porta pròpia; per aquí ja no passa."""
        with self.assertRaises(RondaError):
            obrir_ronda(self.model, Ronda.MOTIU_CORRECCIO, ['pom'])
        self.assertEqual(Ronda.objects.filter(model=self.model).count(), 0)

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
        # M1 · FIT-6 — tancar la ronda ara TANCA la feina que hi penja, i tancar feina és un
        # acte amb autor: la volta té una `pom` Pending viva, o sigui que cal un tècnic.
        tancar_ronda(r, profile=self.prof)
        self.assertIsNotNone(r.tancada_el)
        self.assertEqual(tasca_vigent(self.model, 'pom'), self.pom_r1)

    def test_la_ronda_3_es_numera_despres_de_la_2_tancada(self):
        tancar_ronda(obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom']),
                     profile=self.prof)
        self.assertEqual(obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom']).seq, 3)

    # ── El lliurable, abans que el flag existeixi (F1.6) ─────────────────────
    def test_ronda_lliurable_es_fals_mentre_no_hi_hagi_flag(self):
        """`es_lliurable` neix a F1.6. Fins llavors res no és lliurable — i sobretot, això no
        pot petar amb FieldError."""
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom', 'tech_sheet'])
        self.assertFalse(ronda_lliurable(r))


class RondaLliurableTest(RondaTest):
    """F1.6 · el flag `es_lliurable` ja hi és i `ronda_lliurable` deixa de ser sempre fals."""

    def _fes_lliurable(self, *codes):
        TaskType.objects.filter(code__in=codes).update(es_lliurable=True)
        TaskType.objects.exclude(code__in=codes).update(es_lliurable=False)

    def test_sense_cap_tasca_lliurable_la_ronda_no_es_lliurable(self):
        """«No hi ha res per lliurar» no és «ja està lliurat»: un avís al PM sobre el buit és
        soroll."""
        self._fes_lliurable('tech_sheet')
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        self.assertFalse(ronda_lliurable(r))

    def test_la_ronda_no_es_lliurable_mentre_el_producte_no_estigui_fet(self):
        self._fes_lliurable('tech_sheet')
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom', 'tech_sheet'])
        self.assertFalse(ronda_lliurable(r))

    def test_la_ronda_es_lliurable_amb_el_producte_fet_i_la_feina_intermedia_oberta(self):
        """Els lliurables són els PRODUCTES, no la feina de suport: el POM pot quedar obert."""
        self._fes_lliurable('tech_sheet')
        r = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom', 'tech_sheet'])
        r.tasques.filter(task_type=self.tt_fitxa).update(status='Done')
        self.assertTrue(ronda_lliurable(r))
        self.assertEqual(r.tasques.get(task_type=self.tt_pom).status, 'Pending')

    def test_rondes_lliurables_diu_seq_motiu_i_data(self):
        """F2.7 — sense data, un badge que digui «lliurable» no diu si va passar avui o al març."""
        from django.utils import timezone
        from fhort.tasks.services_r import rondes_lliurables

        self._fes_lliurable('tech_sheet')
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['tech_sheet'])
        self.assertEqual(rondes_lliurables(self.model), [])

        r2.tasques.update(status='Done', finished_at=timezone.now())
        fora = rondes_lliurables(self.model)
        self.assertEqual(len(fora), 1)
        self.assertEqual(fora[0]['seq'], 2)
        self.assertEqual(fora[0]['motiu'], Ronda.MOTIU_NOVA_MOSTRA)
        self.assertIsNotNone(fora[0]['lliurat_el'])

    def test_sample_check_existeix_al_cataleg(self):
        """El cens el va buscar als tres schemes i al codi sencer: no existia enlloc."""
        tt = TaskType.objects.get(code='sample_check')
        self.assertTrue(tt.active)
        self.assertEqual(tt.default_order, 47)
        self.assertFalse(tt.es_lliurable)

    def test_patronatge_ja_no_hi_es(self):
        self.assertFalse(TaskType.objects.filter(code='patronatge').exists())


class CorreccioSenseRondaTest(RondaTest):
    """S-20 (05/08) · `Ronda.seq` compta MOSTRES, no correccions.

    Fins avui una correcció obria ronda i el comptador pujava: un model amb tres esmenes
    nostres semblava que hagués fet tres mostres al client. `seq` és el número que el PM llegeix
    i el que billing consultarà per a les voltes pactades — no pot comptar dues coses.

    Ara una correcció és una tasca nova lligada a la mare, amb `motiu='correccio'`, que HERETA
    la ronda de la mare (NULL quan la mare és la prevista, que és la volta 1 implícita).
    """

    def test_la_correccio_no_crea_ronda_i_hereta_la_de_la_mare(self):
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        original = r2.tasques.get(task_type=self.tt_pom)   # abans: ara la volta en tindrà DUES
        rondes_abans = Ronda.objects.filter(model=self.model).count()

        ronda, tasques = obrir_correccio(self.model, ['pom'])

        self.assertEqual(Ronda.objects.filter(model=self.model).count(), rondes_abans)
        self.assertEqual(ronda, r2)
        self.assertEqual(len(tasques), 1)
        correccio = tasques[0]
        self.assertEqual(correccio.ronda, r2)
        self.assertEqual(correccio.mare, original)
        # La volta 2 té ara la tasca original i la seva esmena, totes dues seves.
        self.assertEqual(r2.tasques.filter(task_type=self.tt_pom).count(), 2)
        self.assertEqual(correccio.motiu, Ronda.MOTIU_CORRECCIO)
        self.assertEqual(correccio.origen, 'ad_hoc')

    def test_la_correccio_sobre_la_prevista_no_te_ronda(self):
        """La volta 1 és implícita: la seva correcció també viu amb `ronda=NULL`."""
        ronda, tasques = obrir_correccio(self.model, ['pom'])
        self.assertIsNone(ronda)
        self.assertIsNone(tasques[0].ronda)
        self.assertEqual(tasques[0].mare, self.pom_r1)
        self.assertEqual(Ronda.objects.filter(model=self.model).count(), 0)

    def test_corregir_no_topa_amb_la_ronda_oberta(self):
        """Corregir DINS de la volta que s'està treballant és el cas normal, no una excepció."""
        obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        ronda, tasques = obrir_correccio(self.model, ['pom'])   # no ha d'aixecar RondaError
        self.assertEqual(len(tasques), 1)

    def test_tres_correccions_seguides_no_mouen_el_comptador_de_mostres(self):
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        for _ in range(3):
            obrir_correccio(self.model, ['pom'])
        self.assertEqual(list(Ronda.objects.filter(model=self.model)
                              .values_list('seq', flat=True)), [r2.seq])

    def test_no_hi_ha_correccio_sense_res_a_corregir(self):
        """Corregir vol dir REFER alguna cosa: sense mare, el que toca és obrir la tasca."""
        ModelTask.objects.filter(model=self.model, task_type=self.tt_pom).delete()
        with self.assertRaises(RondaError):
            obrir_correccio(self.model, ['pom'])

    # ── El resolutor amb dues tasques del mateix code a la mateixa volta ─────
    def test_tasca_vigent_prefereix_la_correccio_dins_la_ronda(self):
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        original = r2.tasques.get(task_type=self.tt_pom)
        _, tasques = obrir_correccio(self.model, ['pom'])

        vigent = tasca_vigent(self.model, 'pom')
        self.assertEqual(vigent, tasques[0])
        self.assertNotEqual(vigent, original)

    def test_tasca_vigent_prefereix_la_correccio_MES_RECENT(self):
        obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['pom'])
        obrir_correccio(self.model, ['pom'])
        _, segona = obrir_correccio(self.model, ['pom'])
        self.assertEqual(tasca_vigent(self.model, 'pom'), segona[0])

    def test_tasca_vigent_veu_la_correccio_de_la_prevista(self):
        """Sense ronda, la correcció neix amb `ronda=NULL` i `origen='ad_hoc'`: si el resolutor
        filtrés només per `origen='prevista'`, no la trobaria mai."""
        _, tasques = obrir_correccio(self.model, ['pom'])
        self.assertEqual(tasca_vigent(self.model, 'pom'), tasques[0])
