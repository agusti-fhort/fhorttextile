"""FIXOS DE LA FORMACIÓ · 1a TANDA (26/08) — els noms resolts i el refús accionable.

Cobreix F1 (T1) i F3 (T4) de `docs/ordres/DIAGNOSI_FORMACIO_2026-08-26.md`.

## Per què aquests i no d'altres

Els dos defectes tenen **la mateixa arrel**: llegir `POMMaster.nom_client` CRU. Aquell camp és
buit a **103 dels 144 POMs actius** del schema `fhort` —tots amb `pom_global` poblat—, i el que
en sortia era una fila muda al wizard («B · ») i un refús tautològic a `gravar-pom` («BT ja és
BT al catàleg»). Un test que faci servir un POM amb `nom_client` ple **no veu cap dels dos**:
per això tots els bancs d'aquí neixen amb el camp BUIT, que és la població majoritària real.

La meitat pura (el resolutor i la frase) va sense BD a posta: es pot dir la llei sencera amb
objectes de mentida, i el dia que algú torni a llegir el camp cru canta aquí.
"""
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.pom.nomenclatura import frase_de_colisio


# ═══ PART 1 · LA FRASE DEL REFÚS (pura) ══════════════════════════════════════════════════

def _ctx(**kw):
    base = {'client_code': 'BT', 'pom_id': 907, 'pom_codi': 'BT',
            'pom_nom': 'Leg opening girth', 'origen': 'DICCIONARI',
            'origen_llegible': 'del diccionari del client', 'pendent_revisio': False,
            'es_instancia': False, 'description_en': '', 'description_local': '',
            'editat_at': None}
    base.update(kw)
    return base


class FraseDeColisioTest(SimpleTestCase):
    """El refús ha de dir AMB QUÈ xoca i QUÈ es pot fer. Les dues meitats es proven a part."""

    def test_diu_amb_que_xoca(self):
        f = frase_de_colisio('BT', _ctx(), 'BRW')
        self.assertIn('BT', f)
        self.assertIn('Leg opening girth', f)
        self.assertIn('diccionari', f)
        self.assertIn('BRW', f)

    def test_diu_que_es_pot_fer(self):
        f = frase_de_colisio('BT', _ctx(), 'BRW')
        self.assertIn('cercador', f)
        self.assertIn('nomenclatura diferent', f)

    def test_el_pendent_de_revisio_es_diu_I_obre_la_sortida_de_revisar(self):
        # El cas de PROD: un àlies de diccionari que ENCARA no ha validat ningú. Sense dir-ho,
        # «revisa'l» seria una endevinalla.
        f = frase_de_colisio('BT', _ctx(pendent_revisio=True), 'BRW')
        self.assertIn('pendent de revisió', f)
        self.assertIn('revisa', f.lower())

    def test_sense_pendent_NO_s_ofereix_revisar(self):
        # Oferir una sortida que no porta enlloc és pitjor que no oferir-ne cap.
        f = frase_de_colisio('BT', _ctx(pendent_revisio=False), 'BRW')
        self.assertNotIn('pendent de revisió', f)
        self.assertNotIn('revisa', f.lower())

    def test_diu_el_codi_AMB_LA_CAIXA_DEL_CLIENT(self):
        # La comparació és `iexact` i la unique de POMMaster és `upper(codi_client)`: qui escriu
        # «bt» ha de veure que el que ja hi ha es diu «BT», o el refús sembla que no parli del
        # que ell acaba de fer.
        f = frase_de_colisio('bt', _ctx(client_code='BT'), '')
        self.assertIn('«BT»', f)

    def test_el_codi_de_la_CASA_hi_surt_quan_es_diferent(self):
        # Qui hagi d'anar a buscar el POM al cercador el buscarà per aquell, no pel del client.
        f = frase_de_colisio('U1', _ctx(client_code='U1', pom_codi='BTN',
                                        pom_nom='Button spacing'), '')
        self.assertIn('BTN', f)

    def test_sense_context_no_peta(self):
        # Un refús no pot petar per una etiqueta que falta.
        self.assertIn('BT', frase_de_colisio('BT', None))


# ═══ PART 2 · EL NOM RESOLT I EL REFÚS, CONTRA LA BD ═════════════════════════════════════

class NomsResoltsIRefusTest(TenantTestCase):

    def setUp(self):
        from fhort.models_app.models import Model
        from fhort.pom.models import CustomerPOMAlias, POMGlobal, POMMaster
        from fhort.tasks.models import Customer, ModelTask, TaskType
        from fhort.accounts.models import UserProfile

        # 🚨 EL BANC ÉS LA POBLACIÓ MAJORITÀRIA REAL: `nom_client` BUIT i el nom al GLOBAL.
        # Amb el camp ple, cap dels dos defectes es reprodueix.
        self.glob = POMGlobal.objects.create(
            codi='GLB-BT', nom_en='Leg opening girth', nom_ca='Contorn de boca de camal',
            nom_es='Contorno de boca de pernera')
        self.pom = POMMaster.objects.create(
            codi_client='BT', nom_client='', pom_global=self.glob, actiu=True)
        # …i un SENSE CAP NOM ENLLOC: els 7 de `fhort` que feien el refús tautològic.
        self.pom_mut = POMMaster.objects.create(
            codi_client='ZZ', nom_client='', pom_global=None, actiu=True)

        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')
        # L'àlies del DICCIONARI, pendent de revisar: el cas exacte de PROD.
        CustomerPOMAlias.objects.create(
            customer=self.customer, pom=self.pom, client_code='BT',
            origen='DICCIONARI', pendent_revisio=True)

        self.model = Model.objects.create(
            codi_intern='TST-F1', codi_tenant='TST', any=2027, sequencial=77,
            temporada='FW27', size_run_model='XS·S·M', base_size_label='S',
            customer=self.customer)
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_f1', defaults={'email': 'qa@f1.test'})
        UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA F1', 'rol_nom': 'QA'})
        tt, _ = TaskType.objects.get_or_create(
            code='pom', defaults={'name': 'POM', 'default_order': 1})
        ModelTask.objects.get_or_create(
            model=self.model, task_type=tt, defaults={'status': 'Pending'})

        self.api = APIClient(SERVER_NAME=self.get_test_tenant_domain())
        self.api.force_authenticate(self.user)

    # ── F1 · EL NOM ARRIBA RESOLT ────────────────────────────────────────────────────────

    def test_f1_el_nom_resolt_cau_al_global_quan_el_tenant_no_bateja(self):
        from fhort.models_app.extraction_views import _nom_resolt
        self.assertEqual(_nom_resolt(self.pom), 'Leg opening girth')

    def test_f1_sense_pom_es_None_i_no_una_cadena_buida(self):
        # El contracte distingeix «no hi ha POM» de «el POM no té nom», i hi ha lectors que
        # se'n refien.
        from fhort.models_app.extraction_views import _nom_resolt
        self.assertIsNone(_nom_resolt(None))

    def test_f1_els_candidats_del_409_porten_el_nom_resolt(self):
        from fhort.models_app.extraction_views import _candidats_de_codi
        fila = _candidats_de_codi('BT')[0]
        self.assertEqual(fila['nom_en'], 'Leg opening girth')
        # …i `nom_client` es queda CRU al costat: saber si el TENANT l'ha batejat és una
        # pregunta legítima i té qui la faci.
        self.assertEqual(fila['nom_client'], '')

    # ── F3 · EL REFÚS ────────────────────────────────────────────────────────────────────

    def _grava(self, nom_fitxa):
        return self.api.post(
            f'/api/v1/models/{self.model.id}/gravar-pom/',
            {'measurements': [{'pom_id': self.pom_mut.id, 'base_value_cm': 40,
                               'nom_fitxa': nom_fitxa}]},
            format='json')

    def test_f3_el_refus_es_400_ESTRUCTURAT(self):
        r = self._grava('BT')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data['codi'], 'NOMENCLATURA_OCUPADA')
        self.assertEqual(len(r.data['colisions']), 1)

    def test_f3_el_refus_diu_tot_el_que_el_backend_sap(self):
        c = self._grava('BT').data['colisions'][0]
        self.assertEqual(c['client_code'], 'BT')
        self.assertEqual(c['pom_id'], self.pom.pk)
        self.assertEqual(c['pom_nom'], 'Leg opening girth')   # ← RESOLT, no `nom_client`
        self.assertEqual(c['origen'], 'DICCIONARI')
        self.assertTrue(c['pendent_revisio'])                 # ← el cas de PROD
        self.assertIn('cercador', c['message'])

    def test_f3_el_cas_ALIES_PENDENT_ofereix_revisar(self):
        c = self._grava('BT').data['colisions'][0]
        self.assertIn('pendent de revisió', c['message'])
        self.assertIn('revisa', c['message'].lower())

    def test_f3_MAI_MES_una_tautologia(self):
        # 🚨 EL VERMELL QUE ES VA VEURE A LA FORMACIÓ: «BT» ja és BT. Amb `nom_client` buit i
        # sense fallback, l'etiqueta queia al propi codi i el missatge no deia res.
        c = self._grava('BT').data['colisions'][0]
        self.assertNotEqual(c['pom_nom'], c['client_code'])

    def test_f3_conserva_errors_per_al_client_antic(self):
        # Qui només sàpiga aplanar `errors[]` ha de seguir llegint la MATEIXA frase.
        r = self._grava('BT')
        self.assertEqual(r.data['errors'], [r.data['colisions'][0]['message']])

    def test_f3_l_altre_400_de_la_vista_segueix_sent_el_de_sempre(self):
        # El segon dels dos únics 400 d'aquesta vista: cos buit. No s'ha tocat.
        r = self.api.post(f'/api/v1/models/{self.model.id}/gravar-pom/', {}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('measurements', r.data['error'])

    def test_f3_sense_colisio_el_gravat_passa(self):
        # El guard no pot barrar el camí normal: un codi lliure desa.
        r = self._grava('CODI-LLIURE')
        self.assertEqual(r.status_code, 200, getattr(r, 'data', None))
