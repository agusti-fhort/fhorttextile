"""T3 · EL CRONO DE TEMPS DECLARAT — el que la maqueta fixa, fixat també aquí.

La maqueta aprovada (`ops/maquetes/maqueta_temps_declarat_i_modal_v1.html`) diu quatre coses que
no són cosmètiques i que aquest fitxer protegeix:

  1. **Viu al servidor.** Engegar obre un `TimerEntrada` REAL amb `origen='declarat'`. Si això es
     tornés un cronòmetre de navegador, deixaria de sobreviure a un F5 i la peça perdria el sentit.
  2. **Sempre declarat**, també quan ve del crono: darrere no hi ha cap batec d'escriptura, i el
     corpus de D-3 no es pot contaminar amb temps sense evidència d'activitat.
  3. **El guard d'inactivitat no els toca.** No tenen batec per definició; la cron els mataria a
     mitja feina.
  4. **Desar temps no tanca la tasca.** Acabar-la és un gest propi (T4).

Convenció del repo: `python manage.py test fhort.tasks.test_crono_declarat` (no pytest).
"""
import datetime

from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from fhort.tasks.models import Customer, ModelTask, TaskType, TimerEntrada
from fhort.tasks.services_r import (TempsDeclaratError, atura_crono_declarat,
                                    corregeix_tram_declarat, descarta_tram_declarat,
                                    engega_crono_declarat)


class CronoDeclaratTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TCD'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        from django.contrib.auth import get_user_model
        from fhort.accounts.models import UserProfile
        from fhort.models_app.models import Model

        user = get_user_model().objects.create(username='qa_crono')
        # `get_or_create`: el tenant té un signal que ja crea el perfil en néixer l'usuari.
        self.profile, _ = UserProfile.objects.get_or_create(user=user)
        customer = Customer.objects.create(nom='QA', codi='QAC')
        self.model = Model.objects.create(
            codi_intern='QA-CRONO', codi_tenant='TCD', any=2027, sequencial=1,
            nom_prenda='QA crono', customer=customer)
        self.tt_extern = TaskType.objects.get(code='pattern_hand')     # Externa-lliure
        self.tt_intern = TaskType.objects.get(code='pom')              # Interna
        self.externa = ModelTask.objects.create(
            model=self.model, task_type=self.tt_extern, order=0, status='Pending')

    # ── 1 · El tram viu al servidor, i neix declarat ─────────────────────────
    def test_engegar_obre_un_tram_real_i_declarat(self):
        tram = engega_crono_declarat(self.externa, self.profile)
        self.externa.refresh_from_db()
        self.assertIsNone(tram.fi, 'un crono en marxa és un tram OBERT')
        self.assertTrue(tram.actiu)
        self.assertEqual(tram.origen, TimerEntrada.ORIGEN_DECLARAT)
        self.assertEqual(self.externa.status, 'InProgress')

    def test_engegar_dos_cops_no_obre_dos_trams(self):
        primer = engega_crono_declarat(self.externa, self.profile)
        segon = engega_crono_declarat(self.externa, self.profile)
        self.assertEqual(primer.pk, segon.pk)
        self.assertEqual(TimerEntrada.objects.filter(model_task=self.externa).count(), 1)

    def test_el_crono_no_es_per_a_tasques_internes(self):
        """Declarar hores sobre feina que l'eina SÍ que mesura seria inventar temps facturable."""
        interna = ModelTask.objects.create(
            model=self.model, task_type=self.tt_intern, order=1, status='Pending')
        with self.assertRaises(TempsDeclaratError):
            engega_crono_declarat(interna, self.profile)

    # ── 2 · Aturar tanca el tram i PAUSA, mai tanca la tasca ─────────────────
    def test_aturar_tanca_el_tram_i_deixa_la_tasca_pausada(self):
        engega_crono_declarat(self.externa, self.profile)
        tram = atura_crono_declarat(self.externa, self.profile)
        self.externa.refresh_from_db()
        self.assertIsNotNone(tram.fi)
        self.assertFalse(tram.actiu)
        self.assertEqual(tram.origen, TimerEntrada.ORIGEN_DECLARAT, 'segueix declarat en tancar')
        self.assertEqual(self.externa.status, 'Paused')
        self.assertNotEqual(self.externa.status, 'Done', 'desar temps no tanca la tasca')

    def test_aturar_sense_crono_es_un_error_explicat(self):
        with self.assertRaises(TempsDeclaratError):
            atura_crono_declarat(self.externa, self.profile)

    # ── 3 · Descartar i corregir ─────────────────────────────────────────────
    def test_descartar_esborra_el_tram_i_no_tanca_la_tasca(self):
        engega_crono_declarat(self.externa, self.profile)
        tram = atura_crono_declarat(self.externa, self.profile)
        descarta_tram_declarat(tram)
        self.externa.refresh_from_db()
        self.assertEqual(TimerEntrada.objects.filter(model_task=self.externa).count(), 0)
        self.assertEqual(self.externa.status, 'Paused')

    def test_no_es_descarta_un_crono_en_marxa(self):
        tram = engega_crono_declarat(self.externa, self.profile)
        with self.assertRaises(TempsDeclaratError):
            descarta_tram_declarat(tram)

    def test_corregir_accepta_durada_o_franja_pero_mai_les_dues(self):
        engega_crono_declarat(self.externa, self.profile)
        tram = atura_crono_declarat(self.externa, self.profile)

        corregeix_tram_declarat(tram, minuts=90)
        self.assertEqual(tram.minuts, 90)

        fi = timezone.now()
        inici = fi - datetime.timedelta(minutes=45)
        corregeix_tram_declarat(tram, inici=inici, fi=fi)
        self.assertEqual(tram.minuts, 45)

        with self.assertRaises(TempsDeclaratError):
            corregeix_tram_declarat(tram, minuts=10, inici=inici, fi=fi)
        with self.assertRaises(TempsDeclaratError):
            corregeix_tram_declarat(tram)

    def test_corregir_nomes_temps_declarat(self):
        interna = ModelTask.objects.create(
            model=self.model, task_type=self.tt_intern, order=2, status='Pending')
        mesurat = TimerEntrada.objects.create(
            model_task=interna, tecnic=self.profile, inici=timezone.now(),
            fi=timezone.now(), minuts=10, actiu=False)
        with self.assertRaises(TempsDeclaratError):
            corregeix_tram_declarat(mesurat, minuts=20)
        with self.assertRaises(TempsDeclaratError):
            descarta_tram_declarat(mesurat)

    # ── 4 · El guard d'inactivitat NO els toca ───────────────────────────────
    def test_el_guard_no_pausa_un_crono_declarat(self):
        """La prova que evita que la cron mati el tècnic a mitja feina: es fa vell el tram molt
        més enllà del llindar i el guard l'ha d'ignorar igualment."""
        from django.core.management import call_command

        tram = engega_crono_declarat(self.externa, self.profile)
        TimerEntrada.objects.filter(pk=tram.pk).update(
            inici=timezone.now() - datetime.timedelta(hours=5), last_heartbeat=None)

        call_command('pausa_tasques_oblidades', '--tenant', self.tenant.schema_name, verbosity=0)

        self.externa.refresh_from_db()
        tram.refresh_from_db()
        self.assertEqual(self.externa.status, 'InProgress', 'el crono declarat segueix viu')
        self.assertIsNone(tram.fi)

    def test_el_guard_SI_pausa_un_tram_mesurat_vell(self):
        """La contraprova: el guard no s'ha desactivat, només ha après a distingir."""
        from django.core.management import call_command
        from fhort.tasks.services_c import transition_task

        interna = ModelTask.objects.create(
            model=self.model, task_type=self.tt_intern, order=3, status='Pending')
        transition_task(interna, 'InProgress', self.profile)
        TimerEntrada.objects.filter(model_task=interna, fi__isnull=True).update(
            inici=timezone.now() - datetime.timedelta(hours=5), last_heartbeat=None)

        call_command('pausa_tasques_oblidades', '--tenant', self.tenant.schema_name, verbosity=0)

        interna.refresh_from_db()
        self.assertEqual(interna.status, 'Paused')
