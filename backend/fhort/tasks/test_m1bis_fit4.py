"""M1-bis · FIT-4 — LA R1 NEIX SOLA, I LA VOLTA SEGÜENT HEREDA EL JOC.

Dues lleis, i cadascuna té la seva meitat de fitxer:

  · **R1 automàtica** — la volta 1 ja no és implícita. Neix del PRIMER GEST DE TREBALL, sigui
    quin sigui, amb `seq=1`. Hi ha un test per CADA punt del codi que crea una `ModelTask` de
    producte, perquè no n'hi ha cap de comú: si algú n'afegeix un de sisè i no hi enganxa
    `ronda_del_gest`, la feina naixerà orfe i **cap altre test ho veurà**.
  · **Replicació a R2+** — la volta nova neix amb el joc de tasques de l'anterior, per CODE.

🔒 EL QUE AQUESTS TESTS GUARDEN SOBRETOT és que l'obertura automàtica **només mira endavant**
(sub-decisió b d'Agus): cap tasca `ronda=NULL` preexistent s'adopta, i cap tasca canvia mai de
volta (FIT-6). El dia que algú ho «arregli» adoptant les velles, el retroactiu de M5 deixarà de
poder distingir la feina d'abans del canvi de llei.
"""
import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.pom.models import GarmentType
from fhort.tasks.models import (Customer, GarmentTypeItem, ModelTask, Ronda, TaskType)
from fhort.tasks.services_c import transition_task
from fhort.tasks.services_r import (codes_a_replicar, obrir_ronda, ronda_del_gest,
                                    tancar_ronda, tasca_vigent)


class BaseFit4(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant FIT4'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TF4'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        self.user = get_user_model().objects.create(username='pmfit4')
        self.prof, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'PM FIT4'})
        self.prof.rol_nom = 'admin'          # allow-list completa: el gest no és el que es prova
        self.prof.save(update_fields=['rol_nom'])
        # 🚨 `user.profile` CACHEJA. Sense rellegir l'usuari, `get_capabilities` i
        # `get_allowed_task_types` segueixen veient el perfil d'abans del `save` i tota la classe
        # rep 403 d'allow-list abans d'arribar a cap guard — la lliçó de J (`ftt-j-consulta...`).
        self.user = get_user_model().objects.get(pk=self.user.pk)

        self.customer = Customer.objects.create(codi='CF4', nom='Client FIT4')
        gt = GarmentType.objects.create(codi_client='GT4', nom_client='Família F4', grup='TOPS')
        self.item = GarmentTypeItem.objects.create(garment_type=gt, code='item_f4', name='Item F4')
        self.tt_pom, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'Definició POM', 'fase': 'Dev. tècnic'})
        self.tt_fitxa, _ = TaskType.objects.get_or_create(
            code='tech_sheet', defaults={'name': 'Fitxa tècnica', 'fase': 'Dev. tècnic'})
        self.model = Model.objects.create(
            codi_intern='TF4-SS26-0001', codi_tenant='TF4', any=2026, temporada='SS',
            sequencial=1, customer=self.customer, garment_type_item=self.item, nom_prenda='Peça')

    def _client(self, user=None):
        c = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        c.force_authenticate(user=user or self.user)
        return c

    def _r1(self):
        return Ronda.objects.filter(model=self.model, seq=1).first()


# ── R1 AUTOMÀTICA · UN TEST PER GEST ────────────────────────────────────────────────────────

class R1NeixDelGestTest(BaseFit4):

    def test_el_model_neix_sense_cap_ronda(self):
        """La R1 no la crea el model: la crea el GEST. Sense feina no hi ha volta."""
        self.assertFalse(Ronda.objects.filter(model=self.model).exists())

    def test_gest_define_tasks(self):
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/define-tasks/',
                                   {'task_type_ids': [self.tt_pom.pk, self.tt_fitxa.pk]},
                                   format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        r1 = self._r1()
        self.assertIsNotNone(r1, 'define-tasks no ha fet néixer la R1')
        self.assertEqual(r1.seq, 1)
        # Totes les del MATEIX gest van a la MATEIXA volta.
        self.assertEqual(ModelTask.objects.filter(model=self.model, ronda=r1).count(), 2)

    def test_gest_open_task(self):
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/open-task/',
                                   {'code': 'pom'}, format='json')
        self.assertIn(resp.status_code, (200, 201), resp.data)
        r1 = self._r1()
        self.assertIsNotNone(r1, 'open-task no ha fet néixer la R1')
        self.assertEqual(ModelTask.objects.get(model=self.model).ronda_id, r1.pk)

    def test_gest_crono_declarat(self):
        tt, _ = TaskType.objects.get_or_create(
            code='design_review',
            defaults={'name': 'Revisió disseny', 'fase': 'Dev. tècnic'})
        TaskType.objects.filter(pk=tt.pk).update(tipus='Externa-lliure')
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/crono/',
                                   {'code': 'design_review', 'accio': 'engegar'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        r1 = self._r1()
        self.assertIsNotNone(r1, 'el crono declarat no ha fet néixer la R1')
        self.assertEqual(ModelTask.objects.get(model=self.model).ronda_id, r1.pk)

    def test_gest_extra_off_recipe(self):
        from fhort.commerce.models import WorkOrder
        wo = WorkOrder.objects.create(kind='ORDER', status='OPEN', model=self.model,
                                      customer=self.customer)
        resp = self._client().post('/api/v1/model-task-items/extra/',
                                   {'work_order': wo.pk, 'model': self.model.pk,
                                    'task_type': self.tt_pom.pk}, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        r1 = self._r1()
        self.assertIsNotNone(r1, "l'extra off_recipe no ha fet néixer la R1")
        self.assertEqual(ModelTask.objects.get(model=self.model).ronda_id, r1.pk)

    def test_gest_assign_batch(self):
        from fhort.planning.plan_service import assign_batch
        from fhort.tasks.models import TaskTimeEstimate
        # `assign_batch` no crea res sense estimació («o té valor o demana»).
        TaskTimeEstimate.objects.update_or_create(
            garment_type_item=self.item, task_type=self.tt_pom,
            defaults={'estimated_minutes': 60})
        self.prof.permisos = {'tasks': ['pom']}
        self.prof.save(update_fields=['permisos'])
        self.prof.refresh_from_db()
        assign_batch(model_ids=[self.model.pk],
                     assignacions=[{'task_type_code': 'pom',
                                    'assignee_profile_id': self.prof.pk}])
        r1 = self._r1()
        self.assertIsNotNone(r1, "assign_batch no ha fet néixer la R1")
        self.assertEqual(ModelTask.objects.get(model=self.model).ronda_id, r1.pk)


class R1NoEsDuplicaTest(BaseFit4):

    def test_dos_gestos_seguits_no_creen_dues_R1(self):
        c = self._client()
        c.post(f'/api/v1/models/{self.model.pk}/open-task/', {'code': 'pom'}, format='json')
        c.post(f'/api/v1/models/{self.model.pk}/open-task/', {'code': 'tech_sheet'},
               format='json')
        self.assertEqual(Ronda.objects.filter(model=self.model).count(), 1)
        self.assertEqual(ModelTask.objects.filter(model=self.model,
                                                  ronda=self._r1()).count(), 2)

    def test_el_servei_es_idempotent(self):
        """Qui impedeix la segona R1 és `uniq_ronda_model_seq`, no un `if` optimista."""
        a = ronda_del_gest(self.model)
        b = ronda_del_gest(self.model)
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(Ronda.objects.filter(model=self.model).count(), 1)

    def test_la_constraint_hi_es_de_debo(self):
        from django.db import IntegrityError, transaction
        ronda_del_gest(self.model)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Ronda.objects.create(model=self.model, seq=1,
                                 motiu=Ronda.MOTIU_NOVA_MOSTRA)


class NomesMiraEndavantTest(BaseFit4):
    """Sub-decisions (b) i (c): res del que ja hi ha s'adopta."""

    def setUp(self):
        super().setUp()
        # Feina PRÈVIA, com la de qualsevol model d'abans del canvi de llei: `ronda` NULL.
        self.vella = ModelTask.objects.create(model=self.model, task_type=self.tt_pom,
                                              order=0, status='Done', origen='prevista')

    def test_el_primer_gest_nou_crea_la_R1_amb_nomes_la_tasca_nova(self):
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/open-task/',
                                   {'code': 'tech_sheet'}, format='json')
        self.assertIn(resp.status_code, (200, 201), resp.data)
        r1 = self._r1()
        self.assertIsNotNone(r1)
        self.assertEqual(list(r1.tasques.values_list('task_type__code', flat=True)),
                         ['tech_sheet'])
        self.vella.refresh_from_db()
        self.assertIsNone(self.vella.ronda_id, 'la feina vella s\'ha adoptat: prohibit fins a M5')

    def test_assignar_una_tasca_que_ja_existeix_no_li_toca_la_ronda(self):
        """Assignar no és crear. I moure-la seria migrar feina entre voltes (FIT-6)."""
        from fhort.planning.plan_service import assign_model
        ModelTask.objects.filter(pk=self.vella.pk).update(status='Pending')
        self.prof.permisos = {'tasks': ['pom']}
        self.prof.save(update_fields=['permisos'])
        assign_model(model_id=self.model.pk, assignee_id=self.prof.pk)
        self.vella.refresh_from_db()
        self.assertIsNone(self.vella.ronda_id)
        self.assertFalse(Ronda.objects.filter(model=self.model).exists())


class TascaLliureEntraALaVoltaVigentTest(BaseFit4):

    def test_una_tasca_nova_amb_ronda_oberta_hi_entra(self):
        """FIT-4: «es pot obrir una tasca lliure que ENTRA EN AQUESTA RONDA»."""
        self._client().post(f'/api/v1/models/{self.model.pk}/open-task/',
                            {'code': 'pom'}, format='json')
        r1 = self._r1()
        self._client().post(f'/api/v1/models/{self.model.pk}/open-task/',
                            {'code': 'tech_sheet'}, format='json')
        nova = ModelTask.objects.get(model=self.model, task_type=self.tt_fitxa)
        self.assertEqual(nova.ronda_id, r1.pk)

    def test_amb_totes_les_voltes_tancades_la_feina_nova_espera(self):
        """Cas 3 de `ronda_del_gest`: crear una R(n+1) sola contradiria «R2+ són explícites»."""
        self._client().post(f'/api/v1/models/{self.model.pk}/open-task/',
                            {'code': 'pom'}, format='json')
        tancar_ronda(self._r1(), profile=self.prof)
        self._client().post(f'/api/v1/models/{self.model.pk}/open-task/',
                            {'code': 'tech_sheet'}, format='json')
        nova = ModelTask.objects.get(model=self.model, task_type=self.tt_fitxa)
        self.assertIsNone(nova.ronda_id)
        self.assertEqual(Ronda.objects.filter(model=self.model).count(), 1)


# ── REPLICACIÓ A R2+ ────────────────────────────────────────────────────────────────────────

class ReplicacioTest(BaseFit4):

    def setUp(self):
        super().setUp()
        c = self._client()
        c.post(f'/api/v1/models/{self.model.pk}/define-tasks/',
               {'task_type_ids': [self.tt_pom.pk, self.tt_fitxa.pk]}, format='json')
        self.r1 = self._r1()
        for t in self.r1.tasques.all():          # la volta 1, treballada i tancada
            transition_task(t, 'InProgress', self.prof)
            transition_task(t, 'Done', self.prof)
        tancar_ronda(self.r1, profile=self.prof)

    def test_la_R2_neix_amb_el_joc_de_la_R1_sense_demanar_res(self):
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        self.assertEqual(r2.seq, 2)
        self.assertEqual(sorted(r2.tasques.values_list('task_type__code', flat=True)),
                         ['pom', 'tech_sheet'])

    def test_es_replica_per_CODE_i_no_per_pk(self):
        """G9. La prova és que les files són NOVES amb el mateix slug."""
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        pks_r1 = set(self.r1.tasques.values_list('pk', flat=True))
        pks_r2 = set(r2.tasques.values_list('pk', flat=True))
        self.assertFalse(pks_r1 & pks_r2)
        self.assertEqual(codes_a_replicar(self.r1), ['pom', 'tech_sheet'])

    def test_les_replicades_neixen_Pending_i_amb_el_temps_a_zero(self):
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        for t in r2.tasques.all():
            self.assertEqual(t.status, 'Pending')
            self.assertIsNone(t.started_at)
            self.assertIsNone(t.finished_at)
            self.assertEqual(t.timers.count(), 0)

    def test_no_s_hereta_l_assignacio_del_tecnic_de_la_volta_anterior(self):
        from fhort.accounts.models import UserProfile
        # 🚨 Un signal JA crea el `UserProfile` en crear l'usuari: s'ADOPTA, no se'n crea un altre
        # (`accounts_userprofile_user_id_key`). Mateixa llei que amb `SizeFitting`.
        altre, _ = UserProfile.objects.get_or_create(
            user=get_user_model().objects.create(username='altrefit4'),
            defaults={'nom_complet': 'Altre', 'rol_nom': 'technician'})
        self.r1.tasques.update(assignee=altre)
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        self.assertNotIn(altre.pk, set(r2.tasques.values_list('assignee_id', flat=True)))

    def test_la_R1_no_es_toca(self):
        """FIT-6: cap tasca migra entre voltes."""
        abans = dict(self.r1.tasques.values_list('pk', 'status'))
        obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        self.r1.refresh_from_db()
        self.assertEqual(dict(self.r1.tasques.values_list('pk', 'status')), abans)
        self.assertEqual(len(abans), 2)

    def test_els_codes_demanats_se_SUMEN_a_la_replica(self):
        tt_bom, _ = TaskType.objects.get_or_create(
            code='bom', defaults={'name': 'BOM', 'fase': 'Dev. tècnic'})
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['bom'], profile=self.prof)
        self.assertEqual(sorted(r2.tasques.values_list('task_type__code', flat=True)),
                         ['bom', 'pom', 'tech_sheet'])

    def test_un_code_replicat_desactivat_al_cataleg_s_omet_i_es_diu(self):
        TaskType.objects.filter(pk=self.tt_fitxa.pk).update(active=False)
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        self.assertEqual(list(r2.tasques.values_list('task_type__code', flat=True)), ['pom'])
        self.assertEqual(r2._codes_omesos, ['tech_sheet'])

    def test_un_code_DEMANAT_desconegut_segueix_sent_rebuig_dur(self):
        from fhort.tasks.services_r import RondaError
        with self.assertRaises(RondaError):
            obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['no_existeix'], profile=self.prof)

    def test_els_extres_off_recipe_no_es_repliquen(self):
        ModelTask.objects.create(model=self.model, task_type=self.tt_pom, order=9,
                                 status='Done', origen='ad_hoc', off_recipe=True,
                                 ronda=self.r1)
        tt_bom, _ = TaskType.objects.get_or_create(
            code='bom', defaults={'name': 'BOM', 'fase': 'Dev. tècnic'})
        ModelTask.objects.create(model=self.model, task_type=tt_bom, order=10,
                                 status='Done', origen='ad_hoc', off_recipe=True,
                                 ronda=self.r1)
        self.assertEqual(codes_a_replicar(self.r1), ['pom', 'tech_sheet'])   # `bom` fora

    def test_la_R3_replica_de_la_R2_i_no_de_la_R1(self):
        """La cadena no es trenca a la segona volta (l'`origen` no serveix de filtre: v. la nota
        de `_NO_ES_REPLICA`)."""
        tt_bom, _ = TaskType.objects.get_or_create(
            code='bom', defaults={'name': 'BOM', 'fase': 'Dev. tècnic'})
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['bom'], profile=self.prof)
        tancar_ronda(r2, profile=self.prof)
        r3 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        self.assertEqual(r3.seq, 3)
        self.assertEqual(sorted(r3.tasques.values_list('task_type__code', flat=True)),
                         ['bom', 'pom', 'tech_sheet'])

    def test_la_porta_http_diu_que_ha_replicat(self):
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/obrir-ronda/',
                                   {'motiu': Ronda.MOTIU_NOVA_MOSTRA, 'codes': []},
                                   format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(sorted(resp.data['codes_replicats']), ['pom', 'tech_sheet'])
        self.assertEqual(resp.data['seq'], 2)


class GenealogiaMareTest(ReplicacioTest):
    """CODA · DECISIÓ 3 — la `mare` apunta a la VOLTA ANTERIOR, no a la base.

    🚨 El defecte que aquests tests tanquen venia d'M1 i era invisible mentre no hi hagués una R3:
    amb totes les voltes tancades, `tasca_vigent` cau a la regla 2 i retorna la tasca `prevista`
    —la de la R1—, de manera que la `mare` de la R3 saltava la R2 sencera. El `help_text` del camp
    deia una cosa i el codi en feia una altra.
    """

    def _per_code(self, ronda):
        return {t.task_type.code: t for t in ronda.tasques.select_related('task_type')}

    def test_la_R2_te_per_mare_la_tasca_homologa_de_la_R1(self):
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        r1, filles = self._per_code(self.r1), self._per_code(r2)
        for code in ('pom', 'tech_sheet'):
            self.assertEqual(filles[code].mare_id, r1[code].pk, code)

    def test_la_cadena_R1_R2_R3_no_salta_cap_volta(self):
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        tancar_ronda(r2, profile=self.prof)
        r3 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)

        r1, dos, tres = self._per_code(self.r1), self._per_code(r2), self._per_code(r3)
        for code in ('pom', 'tech_sheet'):
            # El salt de la R3 va a la R2…
            self.assertEqual(tres[code].mare_id, dos[code].pk, code)
            # …i NO a la R1, que era el defecte.
            self.assertNotEqual(tres[code].mare_id, r1[code].pk, code)
        # I la cadena sencera es pot recórrer cap enrere fins a la R1.
        self.assertEqual(tres['pom'].mare.mare_id, r1['pom'].pk)
        self.assertIsNone(tres['pom'].mare.mare.mare_id)

    def test_un_code_que_la_volta_anterior_no_tenia_neix_sense_mare(self):
        """«No n'hi havia» és una dada. No s'encadena amb voltes més velles."""
        TaskType.objects.get_or_create(code='bom', defaults={'name': 'BOM',
                                                             'fase': 'Dev. tècnic'})
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['bom'], profile=self.prof)
        self.assertIsNone(self._per_code(r2)['bom'].mare_id)

    def test_un_code_que_neix_a_la_R2_encadena_a_la_R3(self):
        TaskType.objects.get_or_create(code='bom', defaults={'name': 'BOM',
                                                             'fase': 'Dev. tècnic'})
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['bom'], profile=self.prof)
        tancar_ronda(r2, profile=self.prof)
        r3 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        self.assertEqual(self._per_code(r3)['bom'].mare_id, self._per_code(r2)['bom'].pk)

    def test_un_model_LLEGAT_sense_cap_volta_conserva_la_mare_historica(self):
        """🚩 Desviació declarada de la lletra de la DECISIÓ 3, i el motiu és que la lletra hi
        esborrava genealogia CORRECTA.

        Un model d'abans del canvi de llei té tota la feina a `ronda=NULL` i **cap fila `Ronda`**.
        Allà no hi ha «volta anterior» per saltar-se: la feina històrica ÉS la volta anterior. Amb
        `mare=NULL` literal, el primer +Ronda d'aquests models perdria el lligam amb tot el que
        s'havia fet. Tres tests d'M1 ho van enxampar; aquest ho deixa dit en veu alta.
        """
        from fhort.models_app.models import Model
        llegat = Model.objects.create(
            codi_intern='TF4-SS26-0009', codi_tenant='TF4', any=2026, temporada='SS',
            sequencial=9, customer=self.customer, garment_type_item=self.item,
            nom_prenda='Llegat')
        historica = ModelTask.objects.create(model=llegat, task_type=self.tt_pom, order=0,
                                             status='Done', origen='prevista')
        self.assertFalse(Ronda.objects.filter(model=llegat).exists())

        r = obrir_ronda(llegat, Ronda.MOTIU_NOVA_MOSTRA, ['pom'], profile=self.prof)
        self.assertEqual(r.seq, 2)                      # la R1 llegada segueix sent implícita
        self.assertEqual(r.tasques.get().mare_id, historica.pk)
        historica.refresh_from_db()
        self.assertIsNone(historica.ronda_id)           # i no s'adopta: (b) segueix sencera

    def test_entre_una_correccio_i_la_seva_mare_mana_la_correccio(self):
        """Mateix criteri que la regla 4 de `tasca_vigent`: es repeteix l'esmena."""
        from fhort.tasks.services_r import obrir_correccio
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        _, correccions = obrir_correccio(self.model, ['pom'], profile=self.prof)
        esmena = correccions[0]
        self.assertEqual(esmena.ronda_id, r2.pk)      # la correcció viu dins de la volta
        tancar_ronda(r2, profile=self.prof)
        r3 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        self.assertEqual(self._per_code(r3)['pom'].mare_id, esmena.pk)


class AdopcioDelBuitTest(ReplicacioTest):
    """CODA · DECISIÓ 2 — la feina nascuda ENTRE dues voltes entra a la següent.

    🔒 I NOMÉS AQUESTA. La frontera és temporal i exacta (`created_at > R(n).tancada_el`): tot el
    que és anterior a la primera volta del model segueix `NULL` fins al retroactiu de M5. El dia
    que algú eixampli el filtre «perquè sembla lògic», la sub-decisió (b) cau i M5 ja no podrà
    distingir la feina d'abans del canvi de llei.
    """

    def _obre_al_buit(self, code):
        """Un gest de treball amb totes les voltes tancades: neix `ronda=NULL` i espera."""
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/open-task/',
                                   {'code': code}, format='json')
        self.assertIn(resp.status_code, (200, 201), resp.data)
        t = ModelTask.objects.get(pk=resp.data['task_id'])
        self.assertIsNone(t.ronda_id, 'la tasca del buit hauria de néixer sense volta')
        return t

    def test_una_tasca_nascuda_al_buit_l_adopta_la_volta_seguent(self):
        tt_bom, _ = TaskType.objects.get_or_create(
            code='bom', defaults={'name': 'BOM', 'fase': 'Dev. tècnic'})
        orfe = self._obre_al_buit('bom')
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        orfe.refresh_from_db()
        self.assertEqual(orfe.ronda_id, r2.pk)
        self.assertEqual(r2._codes_adoptats, ['bom'])

    def test_l_adopcio_nomes_escriu_la_ronda(self):
        """Entrar a una volta no és néixer-hi: ni motiu, ni mare, ni estat, ni order."""
        TaskType.objects.get_or_create(code='bom', defaults={'name': 'BOM',
                                                             'fase': 'Dev. tècnic'})
        orfe = self._obre_al_buit('bom')
        abans = (orfe.status, orfe.motiu, orfe.mare_id, orfe.order, orfe.origen,
                 orfe.created_at)
        obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        orfe.refresh_from_db()
        self.assertEqual((orfe.status, orfe.motiu, orfe.mare_id, orfe.order, orfe.origen,
                          orfe.created_at), abans)

    def test_el_code_adoptat_NO_es_replica_a_sobre(self):
        """La volta no pot quedar amb dos germans del mateix code, un de viu i un de buit.

        El cas és REAL i s'hi arriba sol: un code que a la volta anterior només va existir com a
        `ad_hoc` (creat per `obrir_ronda`) no deixa cap `prevista` enrere, o sigui que en tancar-se
        la volta `tasca_vigent` no en troba cap i `open-task` en CREA una de nova — al buit.
        """
        TaskType.objects.get_or_create(code='bom', defaults={'name': 'BOM',
                                                             'fase': 'Dev. tècnic'})
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, ['bom'], profile=self.prof)
        tancar_ronda(r2, profile=self.prof)
        orfe = self._obre_al_buit('bom')            # cap `prevista` de `bom`: se'n crea una

        r3 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        boms = list(r3.tasques.filter(task_type__code='bom'))
        self.assertEqual(len(boms), 1, 'la volta ha quedat amb dos `bom`')
        self.assertEqual(boms[0].pk, orfe.pk)
        self.assertNotIn('bom', r3._codes_replicats)
        # …i la resta del joc sí que es replica.
        self.assertEqual(sorted(r3.tasques.values_list('task_type__code', flat=True)),
                         ['bom', 'pom', 'tech_sheet'])

    def test_un_extra_off_recipe_del_buit_s_adopta_pero_no_tapa_la_recepta(self):
        """«Fora de la recepta» val als dos costats: no es replica, i tampoc no tapa la rèplica."""
        extra = ModelTask.objects.create(model=self.model, task_type=self.tt_pom, order=95,
                                         status='Pending', origen='ad_hoc', off_recipe=True)
        self.assertIsNone(extra.ronda_id)
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        extra.refresh_from_db()
        self.assertEqual(extra.ronda_id, r2.pk)                  # s'adopta…
        self.assertIn('pom', r2._codes_replicats)                # …i el `pom` de la recepta hi és
        self.assertEqual(r2.tasques.filter(task_type__code='pom').count(), 2)

    def test_una_tasca_ANTERIOR_a_la_primera_volta_no_es_toca(self):
        """La prohibició de backfill (sub-decisió b) segueix sencera."""
        vella = ModelTask.objects.create(model=self.model, task_type=self.tt_pom, order=90,
                                         status='Done', origen='ad_hoc')
        ModelTask.objects.filter(pk=vella.pk).update(
            created_at=self.r1.oberta_el - datetime.timedelta(days=30))
        obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        vella.refresh_from_db()
        self.assertIsNone(vella.ronda_id)

    def test_la_frontera_es_el_tancament_de_la_volta_anterior(self):
        """Una NULL creada MENTRE la volta anterior era viva tampoc no s'adopta."""
        durant = ModelTask.objects.create(model=self.model, task_type=self.tt_pom, order=91,
                                          status='Done', origen='ad_hoc')
        ModelTask.objects.filter(pk=durant.pk).update(
            created_at=self.r1.tancada_el - datetime.timedelta(seconds=5))
        obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        durant.refresh_from_db()
        self.assertIsNone(durant.ronda_id)

    def test_una_volta_nomes_amb_feina_adoptada_es_valida(self):
        """Amb tot el catàleg de la volta anterior desactivat, l'adopció sola ja és una ronda."""
        TaskType.objects.get_or_create(code='bom', defaults={'name': 'BOM',
                                                             'fase': 'Dev. tècnic'})
        orfe = self._obre_al_buit('bom')
        TaskType.objects.filter(pk__in=[self.tt_pom.pk, self.tt_fitxa.pk]).update(active=False)
        r2 = obrir_ronda(self.model, Ronda.MOTIU_NOVA_MOSTRA, [], profile=self.prof)
        orfe.refresh_from_db()
        self.assertEqual(orfe.ronda_id, r2.pk)
        self.assertEqual(sorted(r2._codes_omesos), ['pom', 'tech_sheet'])

    def test_la_porta_http_diu_que_ha_adoptat(self):
        TaskType.objects.get_or_create(code='bom', defaults={'name': 'BOM',
                                                             'fase': 'Dev. tècnic'})
        self._obre_al_buit('bom')
        resp = self._client().post(f'/api/v1/models/{self.model.pk}/obrir-ronda/',
                                   {'motiu': Ronda.MOTIU_NOVA_MOSTRA, 'codes': []},
                                   format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data['codes_adoptats'], ['bom'])


# ── LA CAPABILITY DE L'ENTREGA ──────────────────────────────────────────────────────────────

class CapabilityEntregaTest(BaseFit4):

    def setUp(self):
        super().setUp()
        self._client().post(f'/api/v1/models/{self.model.pk}/open-task/',
                            {'code': 'pom'}, format='json')
        self.r1 = self._r1()

    def _sense_capability(self):
        from fhort.accounts.models import UserProfile
        u = get_user_model().objects.create(username='mirona')
        p, _ = UserProfile.objects.get_or_create(user=u)   # el signal ja n'ha creat un: s'adopta
        p.rol_nom, p.nom_complet = 'technician', 'Mirona'
        p.permisos = {'revoke': ['execute_tasks']}         # capacitat efectiva = cap
        p.save(update_fields=['rol_nom', 'nom_complet', 'permisos'])
        return get_user_model().objects.get(pk=u.pk)       # `user.profile` cacheja: rellegeix

    def test_sense_execute_tasks_la_porta_d_entrega_dona_403(self):
        resp = self._client(self._sense_capability()).post(
            f'/api/v1/rondes/{self.r1.pk}/entrega/', {'destinatari': 'X'}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_sense_execute_tasks_l_ok_client_dona_403(self):
        from fhort.tasks.services_r import informar_entrega
        e = informar_entrega(self.r1, destinatari='X', profile=self.prof)
        resp = self._client(self._sense_capability()).patch(
            f'/api/v1/entregues/{e.pk}/ok-client/', {}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_amb_execute_tasks_la_porta_segueix_oberta(self):
        resp = self._client().post(f'/api/v1/rondes/{self.r1.pk}/entrega/',
                                   {'destinatari': 'Brumà SL'}, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
