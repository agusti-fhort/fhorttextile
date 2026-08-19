"""Pas W2 · confirmació de POMs — el codi duplicat al catàleg no pot tombar l'import.

Incident PROD (27/07/2026): `import_session_poms_view` feia
`POMMaster.objects.get_or_create(pom_global=None, codi_client=codi)` sobre un catàleg que NO
té cap constraint d'unicitat en aquesta parella (`pom/models.py:183-185`: el `Meta` no en
declara cap). Amb dos POMMaster tenant-only del mateix codi, el `get_or_create` llança
`MultipleObjectsReturned` → 500 → sessió d'import descartada.

El que aquests tests defensen:

  1. **La porta és prèvia a l'escriptura.** Amb un codi duplicat no es crea RES: ni POMMaster,
     ni sessió desada, ni POM a mitges. Un 409 que hagués deixat catàleg brut seria pitjor que
     el 500 que substitueix.
  2. **Es reporten TOTS els codis conflictius alhora.** Petar al primer obligaria el tècnic a
     descobrir-los d'un en un, un import per duplicat.
  3. Els dos camins sans no canvien: count==0 crea, count==1 reutilitza.
"""
import datetime
import uuid

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.extraction_views import import_session_poms_view
from fhort.models_app.models import ImportSession
from fhort.pom.catalog_testing import desactiva_unicitat_codi_client
from fhort.pom.models import POMMaster


class _TenantBase(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant


class ImportPomsCodiDuplicatTest(_TenantBase):

    def setUp(self):
        super().setUp()
        # ⚠️ EL CATÀLEG DUPLICAT JA NO EL POT FABRICAR NINGÚ (migració `pom/0075`), i aquestes
        # proves l'han de poder muntar igualment: el que exerciten és el GUARD del 409, que
        # segueix viu al codi de producció. La constraint es treu NOMÉS aquí i NOMÉS dins de la
        # transacció de la prova; v. `fhort/pom/catalog_testing.py` per al perquè i per a la
        # decisió que hi queda oberta.
        desactiva_unicitat_codi_client()
        user = get_user_model().objects.create_user(username='tec', password='x')
        self.profile, _ = UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'patronista'})
        self.user = user
        self.factory = APIRequestFactory()

    # ── helpers ────────────────────────────────────────────────────────────────────
    def _sessio(self, files):
        """ImportSession a l'estat 'POMS' amb les files NO_MATCH indicades.
        `files` = [(ordre, codi_fitxa, descripcio)]."""
        return ImportSession.objects.create(
            token=uuid.uuid4(),
            estat='POMS',
            poms_extrets=[{
                'codi_fitxa': codi,
                'descripcio': desc,
                'pom_master_id': None,
                'values': {},
                'actiu': False,
                'ordre': ordre,
            } for ordre, codi, desc in files],
        )

    def _pom_tenant_only(self, codi, nom=None):
        return POMMaster.objects.create(
            pom_global=None, codi_client=codi, nom_client=nom or codi, actiu=True)

    def _patch(self, session, tenant_only, confirmats=None):
        req = self.factory.patch(
            f'/api/v1/import-sessions/{session.token}/poms/',
            {'poms_confirmats': confirmats or [], 'poms_tenant_only': tenant_only},
            format='json')
        force_authenticate(req, user=self.user)
        return import_session_poms_view(req, token=str(session.token))

    # ── 1. El cas de l'incident ────────────────────────────────────────────────────
    def test_codi_duplicat_al_cataleg_dona_409_i_no_crea_res(self):
        """Dos POMMaster tenant-only amb el MATEIX codi_client: abans → 500. Ara → 409 net."""
        self._pom_tenant_only('AA', 'Ample pit (vell)')
        self._pom_tenant_only('AA', 'Ample pit (duplicat)')
        session = self._sessio([(0, 'AA', '1/2 chest width')])

        resp = self._patch(session, tenant_only=[0])

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['error'], 'codi_duplicat')
        self.assertEqual(resp.data['codis'], ['AA'])

    def test_el_409_no_deixa_ni_pom_ni_sessio_a_mitges(self):
        """Atomicitat de veritat: cap POMMaster nou, la sessió es queda a 'POMS' i la fila
        NO_MATCH segueix sense pom_master_id. Un 409 que hagués escrit seria pitjor que el 500."""
        self._pom_tenant_only('AA')
        self._pom_tenant_only('AA')
        session = self._sessio([(0, 'AA', '1/2 chest width')])
        n_abans = POMMaster.objects.count()

        self._patch(session, tenant_only=[0])

        self.assertEqual(POMMaster.objects.count(), n_abans, 'no s\'ha de crear cap POMMaster')
        session.refresh_from_db()
        self.assertEqual(session.estat, 'POMS', 'la sessió no ha d\'avançar')
        self.assertIsNone(session.poms_extrets[0]['pom_master_id'])

    def test_el_409_porta_els_candidats_de_cada_codi(self):
        """R1 · sense candidats, l'única sortida de la UI era anar al catàleg. Amb ells, el
        conflicte es pot resoldre a la fila: cal veure QUI es disputa el codi i d'on ve."""
        vell = self._pom_tenant_only('E', 'Ample (vell)')
        nou = POMMaster.objects.create(
            pom_global=None, codi_client='E', nom_client='Ample (import)', actiu=True,
            pendent_revisio=True, origen_import='sessio-anterior')
        session = self._sessio([(0, 'E', 'chest')])

        resp = self._patch(session, tenant_only=[0])

        self.assertEqual(resp.status_code, 409)
        candidats = resp.data['candidats']['E']
        self.assertEqual([c['id'] for c in candidats], [vell.id, nou.id])
        self.assertEqual(candidats[1], {
            'id': nou.id, 'codi_client': 'E', 'nom_client': 'Ample (import)',
            'origen_import': 'sessio-anterior', 'pendent_revisio': True, 'actiu': True,
        })

    def test_reporta_TOTS_els_codis_conflictius_no_nomes_el_primer(self):
        """El tècnic ha de poder anar al catàleg UN cop i resoldre'ls tots."""
        for codi in ('AA', 'CC'):
            self._pom_tenant_only(codi)
            self._pom_tenant_only(codi)
        self._pom_tenant_only('BB')          # aquest és sa: NO ha de sortir a la llista
        session = self._sessio([(0, 'AA', 'chest'), (1, 'BB', 'waist'), (2, 'CC', 'hip')])

        resp = self._patch(session, tenant_only=[0, 1, 2])

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['codis'], ['AA', 'CC'])

    # ── 2. Els dos camins sans, sense canvi de comportament ────────────────────────
    def test_sense_cap_pom_al_cataleg_el_crea(self):
        session = self._sessio([(0, 'ZZ', 'nova mesura')])

        resp = self._patch(session, tenant_only=[0])

        self.assertEqual(resp.status_code, 200)
        pm = POMMaster.objects.get(pom_global=None, codi_client='ZZ')
        self.assertEqual(pm.nom_client, 'nova mesura')
        self.assertTrue(pm.pendent_revisio)
        self.assertEqual(pm.origen_import, str(session.token))
        session.refresh_from_db()
        self.assertEqual(session.estat, 'MESURES')
        self.assertEqual(session.poms_extrets[0]['pom_master_id'], pm.id)
        self.assertEqual(session.poms_extrets[0]['match_type'], 'tenant_only')

    def test_amb_un_de_sol_al_cataleg_el_reutilitza(self):
        existent = self._pom_tenant_only('YY', 'Ja existia')
        session = self._sessio([(0, 'YY', 'descripció del document')])
        n_abans = POMMaster.objects.count()

        resp = self._patch(session, tenant_only=[0])

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(POMMaster.objects.count(), n_abans, 'reutilitzar no és crear')
        session.refresh_from_db()
        self.assertEqual(session.poms_extrets[0]['pom_master_id'], existent.id)
        self.assertEqual(session.poms_extrets[0]['pom_nom'], 'Ja existia',
                         'mana el nom del catàleg, no el del document')

    def test_un_duplicat_no_marcat_com_a_tenant_only_no_bloqueja(self):
        """La porta mira NOMÉS les files que el tècnic vol crear. Un duplicat al catàleg que
        aquest import no toca no és problema seu."""
        self._pom_tenant_only('AA')
        self._pom_tenant_only('AA')
        session = self._sessio([(0, 'AA', 'chest'), (1, 'ZZ', 'nova')])

        resp = self._patch(session, tenant_only=[1])   # només la ZZ

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(POMMaster.objects.filter(pom_global=None, codi_client='ZZ').exists())
