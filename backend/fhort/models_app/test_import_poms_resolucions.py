"""Pas W2 · `resolucions` — el conflicte es resol A LA FILA, i el backend no tria mai sol.

R2. Fins ara el pas 2 només tenia dos verbs: "confirma aquests POMs" i "crea'm aquests altres
amb el codi que porti el document". Quan el codi del document ja existia dues vegades al
catàleg, l'única sortida era un 409 global i un viatge al catàleg (incident PROD 27/07/2026,
tenant `los`, fitxa DALIA, codi 'E').

`resolucions` afegeix el tercer verb, per fila i explícit:
  · `vincula` → aquesta fila és AQUEST POM del catàleg (l'ha triat una persona);
  · `crea`    → POMMaster tenant-only amb el codi i el nom que la persona ha escrit.

El que aquests tests defensen:

  1. **Mai un duplicat nou.** `crea` amb un codi que ja existeix NO crea res: torna els
     candidats, com el 409 de R1. La resolució del duplicat segueix sent humana.
  2. **Ni un POM per dues files.** Dues files del mateix import apuntant al mateix POMMaster
     és un error de fila, no un 500 ni una fila que se'n menja l'altra.
  3. **Tot o res.** Una resolució dolenta no deixa escrites les bones: l'atomic no s'obre.
  4. **El contracte antic no es mou.** Sense `resolucions`, el PATCH fa exactament el mateix.
"""
import uuid

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.extraction_views import import_session_poms_view
from fhort.models_app.models import ImportSession
from fhort.models_app.test_import_poms_duplicats import _TenantBase
from fhort.pom.catalog_testing import desactiva_unicitat_codi_client
from fhort.pom.models import POMMaster


class ImportPomsResolucionsTest(_TenantBase):

    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(username='tec2', password='x')
        UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'patronista'})
        self.user = user
        self.factory = APIRequestFactory()

    # ── helpers ────────────────────────────────────────────────────────────────────
    def _sessio(self, files):
        """`files` = [(ordre, codi_fitxa, descripcio, pom_master_id|None)]."""
        return ImportSession.objects.create(
            token=uuid.uuid4(),
            estat='POMS',
            poms_extrets=[{
                'codi_fitxa': codi, 'descripcio': desc, 'pom_master_id': pid,
                'values': {}, 'actiu': bool(pid), 'ordre': ordre,
            } for ordre, codi, desc, pid in files],
        )

    def _pom(self, codi, nom=None, actiu=True):
        return POMMaster.objects.create(
            pom_global=None, codi_client=codi, nom_client=nom or codi, actiu=actiu)

    def _patch(self, session, **body):
        req = self.factory.patch(f'/api/v1/import-sessions/{session.token}/poms/',
                                 body, format='json')
        force_authenticate(req, user=self.user)
        return import_session_poms_view(req, token=str(session.token))

    # ── 1. Els dos verbs nous, en verd ─────────────────────────────────────────────
    def test_vincula_la_fila_pren_el_pom_triat(self):
        # El catàleg duplicat ja no el pot fabricar cap camí viu (`pom/0075`); aquesta
        # prova el munta a mà perquè és justament el conflicte que la resolució resol.
        desactiva_unicitat_codi_client()
        bo = self._pom('E', 'Ample pit (el bo)')
        self._pom('E', 'Ample pit (el vell)')          # el duplicat que va provocar el 409
        session = self._sessio([(0, 'E', 'chest width', None)])

        resp = self._patch(session, poms_confirmats=[],
                           resolucions=[{'ordre': 0, 'accio': 'vincula', 'pom_master_id': bo.id}])

        self.assertEqual(resp.status_code, 200)
        session.refresh_from_db()
        fila = session.poms_extrets[0]
        self.assertEqual(fila['pom_master_id'], bo.id)
        self.assertEqual(fila['pom_nom'], 'Ample pit (el bo)')
        self.assertTrue(fila['actiu'])
        self.assertEqual(session.estat, 'MESURES')

    def test_crea_fa_servir_el_codi_i_el_nom_DONATS_no_els_del_document(self):
        """La diferència amb `poms_tenant_only`: allà el codi és el del document a cegues;
        aquí el tècnic l'ha pogut corregir abans d'enviar-lo."""
        session = self._sessio([(0, 'E', 'chest width', None)])

        resp = self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'crea', 'codi': 'E2', 'nom': 'Ample pit (davant)'}])

        self.assertEqual(resp.status_code, 200)
        pm = POMMaster.objects.get(pom_global=None, codi_client='E2')
        self.assertEqual(pm.nom_client, 'Ample pit (davant)')
        self.assertTrue(pm.pendent_revisio)
        self.assertEqual(pm.origen_import, str(session.token))
        session.refresh_from_db()
        self.assertEqual(session.poms_extrets[0]['pom_master_id'], pm.id)
        self.assertEqual(session.poms_extrets[0]['match_type'], 'tenant_only')

    def test_vincula_pot_CANVIAR_un_vincle_que_ja_hi_havia(self):
        """«Canvia el vincle» a una fila amb match: el POM antic queda lliure, no bloqueja."""
        vell, nou = self._pom('AA', 'match automàtic'), self._pom('BB', 'el que toca')
        session = self._sessio([(0, 'AA', 'chest', vell.id)])

        resp = self._patch(session, poms_confirmats=[vell.id],
                           resolucions=[{'ordre': 0, 'accio': 'vincula', 'pom_master_id': nou.id}])

        self.assertEqual(resp.status_code, 200)
        session.refresh_from_db()
        self.assertEqual(session.poms_extrets[0]['pom_master_id'], nou.id)

    # ── 2. Els errors de fila ──────────────────────────────────────────────────────
    def test_crea_amb_codi_existent_torna_els_candidats_i_no_crea_res(self):
        vell = self._pom('E', 'Ample pit (vell)')
        session = self._sessio([(0, 'E', 'chest width', None)])
        n_abans = POMMaster.objects.count()

        resp = self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'crea', 'codi': 'E', 'nom': 'Ample pit'}])

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['error'], 'resolucions_invalides')
        err = resp.data['errors'][0]
        self.assertEqual((err['ordre'], err['error'], err['codi']), (0, 'codi_existent', 'E'))
        self.assertEqual([c['id'] for c in err['candidats']], [vell.id])
        self.assertEqual(POMMaster.objects.count(), n_abans, 'mai un duplicat nou')
        session.refresh_from_db()
        self.assertEqual(session.estat, 'POMS')

    def test_dues_files_al_mateix_pom_master_es_error_de_fila(self):
        pm = self._pom('E', 'Ample pit')
        session = self._sessio([(0, 'E', 'chest width', None), (1, 'E', 'chest width 2', None)])

        resp = self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': pm.id},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': pm.id}])

        self.assertEqual(resp.status_code, 409)
        self.assertEqual([e['error'] for e in resp.data['errors']], ['pom_ja_usat'])
        self.assertEqual(resp.data['errors'][0]['ordre'], 1)
        session.refresh_from_db()
        self.assertIsNone(session.poms_extrets[0]['pom_master_id'], 'ni la bona no s\'escriu')

    def test_una_resolucio_dolenta_no_deixa_escrites_les_bones(self):
        bo = self._pom('AA', 'ok')
        session = self._sessio([(0, 'AA', 'chest', None), (1, 'ZZ', 'waist', None)])
        n_abans = POMMaster.objects.count()

        resp = self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': bo.id},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': 999999}])

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['errors'][0]['error'], 'pom_no_valid')
        self.assertEqual(POMMaster.objects.count(), n_abans)
        session.refresh_from_db()
        self.assertEqual(session.estat, 'POMS')
        self.assertIsNone(session.poms_extrets[0]['pom_master_id'])

    def test_vincula_a_un_pom_inactiu_es_error_no_500(self):
        mort = self._pom('XX', 'jubilat', actiu=False)
        session = self._sessio([(0, 'XX', 'chest', None)])

        resp = self._patch(session, poms_confirmats=[],
                           resolucions=[{'ordre': 0, 'accio': 'vincula', 'pom_master_id': mort.id}])

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.data['errors'][0]['error'], 'pom_no_valid')

    # ── 3. El contracte antic ──────────────────────────────────────────────────────
    def test_sense_resolucions_el_contracte_antic_no_es_mou(self):
        session = self._sessio([(0, 'ZZ', 'nova mesura', None)])

        resp = self._patch(session, poms_confirmats=[], poms_tenant_only=[0])

        self.assertEqual(resp.status_code, 200)
        pm = POMMaster.objects.get(pom_global=None, codi_client='ZZ')
        self.assertEqual(pm.nom_client, 'nova mesura')
        session.refresh_from_db()
        self.assertEqual(session.poms_extrets[0]['pom_master_id'], pm.id)
        self.assertEqual(session.estat, 'MESURES')

    def test_la_resolucio_mana_sobre_poms_tenant_only_de_la_mateixa_fila(self):
        """La fila 0 va marcada com a tenant-only I resolta: mana la resolució, i el codi del
        document ('E', duplicat al catàleg) no arriba mai a la porta del 409."""
        # El catàleg duplicat ja no el pot fabricar cap camí viu (`pom/0075`); aquesta
        # prova el munta a mà perquè és justament el conflicte que la resolució resol.
        desactiva_unicitat_codi_client()
        self._pom('E', 'duplicat 1')
        self._pom('E', 'duplicat 2')
        session = self._sessio([(0, 'E', 'chest width', None)])

        resp = self._patch(session, poms_confirmats=[], poms_tenant_only=[0], resolucions=[
            {'ordre': 0, 'accio': 'crea', 'codi': 'E-DAV', 'nom': 'Ample pit davant'}])

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(POMMaster.objects.filter(codi_client='E-DAV').exists())
        self.assertEqual(POMMaster.objects.filter(codi_client='E').count(), 2, 'el catàleg no es toca')
