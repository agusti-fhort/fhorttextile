"""SOBIRANIA DEL POM · TRAM 4 — LA PORTA D'ESCRIPTURA DEL CATÀLEG.

🔴 QUÈ ERA `PATCH /api/v1/poms/<id>/` FINS AL 22/08: un `ModelViewSet` PELAT. `IsAuthenticated`
per a tot, `fields='__all__'`, i **`pom_global` ESCRIVIBLE**. Un tècnic —el rol més bàsic—
podia amb un sol PATCH re-enganxar un POM a qualsevol fila del catàleg global o desenganxar-
l'hi, sense decisió i sense traça. La separació és una LLEI del domini, no un camp de
formulari.

Aquests tests fixen les tres portes alhora:
  ① `pom_global` NO és escrivible per API (la separació la fa el copy-on-write);
  ② l'escriptura demana CONFIGURE, com la resta del catàleg;
  ③ editar un camp propi d'un POM lligat el SEPARA, i editar-ne un de ja propi no.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIClient

from fhort.accounts.models import UserProfile
from fhort.pom.models import POMCategory, POMGlobal, POMMaster
from fhort.pom.serializers import POMMasterWriteSerializer


class PortaCatalegTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Porta'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TPT'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        U = get_user_model()
        self.admin = U.objects.create_user(username='admin_tpt', password='x')
        self.tecnic = U.objects.create_user(username='tecnic_tpt', password='x')
        # `UserProfile` s'ADOPTA quan un signal ja l'ha creat (llei de la sembra S45).
        for user, rol in ((self.admin, 'admin'), (self.tecnic, 'technician')):
            perfil, _ = UserProfile.objects.get_or_create(user=user)
            perfil.rol_nom = rol
            perfil.save()

        self.cat = POMCategory.objects.create(codi='CAT_TPT', nom_ca='Tors', nom_en='Upper body')
        self.pg = POMGlobal.objects.create(
            codi='LOSPOM-548', nom_en='FRONT ARMHOLE', nom_ca='SISA DAVANTERA',
            categoria='Upper body', abbreviation='FR AH', unitat='cm',
            start_point='Shoulder point', end_point='Underarm point', scope='FULL',
            orientation='CURVED', state='FLAT', line='ALONG CURVE', body_section='FRONT',
        )
        self.lligat = POMMaster.objects.create(
            codi_client='SD', nom_client='Sisa davantera', pom_global=self.pg, actiu=True)
        self.propi = POMMaster.objects.create(
            codi_client='ZZ', nom_client='Mesura pròpia', actiu=True)

    def _client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    # ── ① pom_global no és escrivible ────────────────────────────────────────────────
    def test_pom_global_NO_ES_NI_CAMP(self):
        """Més fort que «read-only»: no existeix a l'entrada, i DRF ignora el que no és camp."""
        camps = POMMasterWriteSerializer().fields
        self.assertNotIn('pom_global', camps)
        self.assertNotIn('separat_de_global', camps)
        self.assertNotIn('separat_at', camps)

    def test_el_com_es_mesura_SI_es_escrivible(self):
        """🚨 El primer intent heretava de `POMMasterSerializer`, on aquests nou camps són
        `SerializerMethodField` —read-only sempre—: el formulari els hauria enviat, DRF els
        hauria descartat sense piular, i la pantalla hauria desat amb 200 OK sense que passés
        res. Es MESURA amb `fields`, no es dedueix de la llista d'escrivibles."""
        camps = POMMasterWriteSerializer().fields
        for c in ('unitat', 'start_point', 'end_point', 'reference_point', 'scope',
                  'orientation', 'state', 'line', 'body_section'):
            self.assertIn(c, camps, c)
            self.assertFalse(camps[c].read_only, f'{c} ha tornat a ser read-only')

    def test_un_PATCH_no_pot_re_enganxar_el_global(self):
        r = self._client(self.admin).patch(
            f'/api/v1/poms/{self.propi.id}/', {'pom_global': self.pg.id}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.propi.refresh_from_db()
        self.assertIsNone(self.propi.pom_global_id)   # ignorat, no aplicat

    # ── ② gating CONFIGURE ───────────────────────────────────────────────────────────
    def test_un_tecnic_no_pot_escriure_al_cataleg(self):
        r = self._client(self.tecnic).patch(
            f'/api/v1/poms/{self.propi.id}/', {'nom_client': 'Robat'}, format='json')
        self.assertEqual(r.status_code, 403)
        self.propi.refresh_from_db()
        self.assertEqual(self.propi.nom_client, 'Mesura pròpia')

    def test_un_tecnic_SI_pot_llegir_el_cataleg(self):
        """La lectura no es toca: cinc pantalles en beuen."""
        self.assertEqual(self._client(self.tecnic).get('/api/v1/poms/').status_code, 200)
        self.assertEqual(
            self._client(self.tecnic).get(f'/api/v1/poms/{self.propi.id}/').status_code, 200)

    # ── ③ la separació ───────────────────────────────────────────────────────────────
    def test_editar_un_POM_LLIGAT_el_SEPARA_i_copia_el_que_en_penjava(self):
        r = self._client(self.admin).patch(
            f'/api/v1/poms/{self.lligat.id}/', {'nom_client': 'Sisa del davant'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.lligat.refresh_from_db()
        self.assertIsNone(self.lligat.pom_global_id)
        self.assertEqual(self.lligat.separat_de_global, 'LOSPOM-548')
        self.assertIsNotNone(self.lligat.separat_at)
        self.assertEqual(self.lligat.nom_client, 'Sisa del davant')      # el canvi hi és
        self.assertEqual(self.lligat.start_point, 'Shoulder point')      # i el global, copiat
        self.assertEqual(self.lligat.body_section, 'FRONT')

    def test_el_valor_EDITAT_no_el_trepitja_la_copia(self):
        """L'ordre importa: separar PRIMER i escriure DESPRÉS, mai al revés."""
        r = self._client(self.admin).patch(
            f'/api/v1/poms/{self.lligat.id}/', {'start_point': "De l'espatlla"}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.lligat.refresh_from_db()
        self.assertEqual(self.lligat.start_point, "De l'espatlla")
        self.assertEqual(self.lligat.end_point, 'Underarm point')   # el que no s'ha tocat, del global

    def test_administrar_un_POM_lligat_NO_el_separa(self):
        """Desactivar-lo o anotar-hi una nota és administrar-lo, no redefinir-lo."""
        r = self._client(self.admin).patch(
            f'/api/v1/poms/{self.lligat.id}/', {'actiu': False, 'notes': 'en revisió'},
            format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.lligat.refresh_from_db()
        self.assertEqual(self.lligat.pom_global_id, self.pg.id)
        self.assertEqual(self.lligat.separat_de_global, '')

    def test_editar_un_POM_JA_PROPI_es_un_canvi_net(self):
        r = self._client(self.admin).patch(
            f'/api/v1/poms/{self.propi.id}/',
            {'nom_client': 'Mesura meva', 'unitat': 'cm', 'scope': 'HALF'}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.propi.refresh_from_db()
        self.assertEqual(self.propi.nom_client, 'Mesura meva')
        self.assertEqual(self.propi.scope, 'HALF')
        self.assertEqual(self.propi.separat_de_global, '')   # mai va estar lligat

    # ── el codi segueix sent únic, i amb un 400 ─────────────────────────────────────
    def test_un_codi_repetit_es_un_400_i_no_un_500(self):
        r = self._client(self.admin).patch(
            f'/api/v1/poms/{self.propi.id}/', {'codi_client': 'sd'}, format='json')
        self.assertEqual(r.status_code, 400, r.data)
        self.assertIn('codi_client', r.data)

    # ── la resposta segueix dient el mateix ────────────────────────────────────────
    def test_la_forma_de_la_resposta_no_canvia(self):
        """La resposta d'un PATCH és, camp per camp, la d'un GET: és el que la pantalla
        recarrega, i amb el codi i el «com es mesura» ja RESOLTS."""
        c = self._client(self.admin)
        abans = set(c.get(f'/api/v1/poms/{self.propi.id}/').data.keys())
        r = c.patch(f'/api/v1/poms/{self.propi.id}/', {'nom_client': 'X'}, format='json')
        self.assertEqual(abans, set(r.data.keys()))
        self.assertEqual(r.data['pom_code'], self.propi.codi_client)   # resolt, no cru
        self.assertEqual(r.data['name_en'], 'X')

    def test_el_vocabulari_del_com_es_mesura_te_UNA_font(self):
        """Va a `/api/v1/vocabulari/`, que existeix precisament perquè el front no se'ls
        escrigui a mà — no a un endpoint propi, que seria la mateixa falta amb un altre nom."""
        r = self._client(self.tecnic).get('/api/v1/vocabulari/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([f['codi'] for f in r.data['scopes_pom']], ['HALF', 'FULL', 'CALCULATED'])
        self.assertIn('CIRCUMFERENCE', [f['codi'] for f in r.data['orientacions_pom']])
        self.assertEqual([f['codi'] for f in r.data['unitats_pom']], ['cm', 'inch'])
        for clau in ('estats_pom', 'linies_pom', 'seccions_cos_pom'):
            self.assertTrue(r.data[clau])

    def test_l_endpoint_orfe_de_nomenclatura_ja_no_hi_es(self):
        r = self._client(self.admin).patch(
            f'/api/v1/poms/{self.propi.id}/nomenclatura/', {'codi_client': 'QQ'}, format='json')
        self.assertEqual(r.status_code, 404)
