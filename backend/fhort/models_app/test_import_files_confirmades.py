"""P2 · QUINES FILES ENTREN A LA TAULA — la pregunta és per FILA, no per POM.

El pas 2 marcava `actiu` així: `p['actiu'] = p['pom_master_id'] in confirmats_set`, i
`poms_confirmats` és una llista d'IDs de POM. Mentre un POM no podia ocupar més d'una fila, POM
i fila eren la mateixa cosa i la clau curta no feia mal. Des de l'Onada 3 sí que pot: la fitxa
de la Brumà en té TRES del mateix POM. Amb la clau vella, desmarcar-ne una **les desmarca totes
tres** —o cap—, i la persona no té manera de dir «aquesta sí i aquesta no».

`files_confirmades` és la mateixa pregunta feta per `ordre`. Quan hi és, MANA; quan no hi és, el
comportament és el d'avui, byte a byte. No substitueix `poms_confirmats`, que té una segona
feina que no és aquesta: incorporar POMs del catàleg que el document no menciona (els afegits a
mà), i aquests no tenen fila fins que el backend els la crea.

Els dos camps NO són redundants, doncs: un parla de FILES QUE JA HI SÓN i l'altre de POMS QUE
HI HAN D'ENTRAR.
"""
import uuid

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.extraction_views import import_session_poms_view
from fhort.models_app.models import ImportSession
from fhort.models_app.test_import_poms_duplicats import _TenantBase
from fhort.pom.models import POMMaster


class FilesConfirmadesTest(_TenantBase):

    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(username='tec-fc', password='x')
        UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'patronista'})
        self.user = user
        self.factory = APIRequestFactory()

    def _pom(self, codi):
        return POMMaster.objects.create(pom_global=None, codi_client=codi, nom_client=codi,
                                        actiu=True)

    def _sessio(self, files):
        return ImportSession.objects.create(
            token=uuid.uuid4(), estat='POMS',
            poms_extrets=[{'codi_fitxa': c, 'descripcio': d, 'pom_master_id': None,
                           'values': {}, 'actiu': False, 'ordre': o} for o, c, d in files])

    def _patch(self, session, **body):
        req = self.factory.patch(f'/api/v1/import-sessions/{session.token}/poms/', body,
                                 format='json')
        force_authenticate(req, user=self.user)
        return import_session_poms_view(req, token=str(session.token))

    def _actius(self, session):
        session.refresh_from_db()
        return [f['actiu'] for f in sorted(session.poms_extrets, key=lambda f: f['ordre'])]

    # ── 1 · LA PREGUNTA PER FILA ──────────────────────────────────────────────────
    def test_desmarcar_una_germana_no_desmarca_les_altres(self):
        """El vermell de P2: tres files del mateix POM i una decisió per a cadascuna."""
        b = self._pom('B')
        session = self._sessio([(0, 'B', 'at the top'), (1, 'BB', 'at the bottom'),
                                (2, 'B1', 'stretched out')])
        self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': o, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': i}
            for o, i in ((0, ''), (1, 'bottom'), (2, 'extended'))])
        self.assertEqual(self._actius(session), [True, True, True], 'les tres resoltes')

        # La persona en desmarca UNA i torna a desar.
        session.refresh_from_db()
        resp = self._patch(session, poms_confirmats=[b.id], files_confirmades=[0, 2])
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertEqual(self._actius(session), [True, False, True])

    def test_files_confirmades_buit_no_es_el_mateix_que_absent(self):
        """`[]` és una decisió («cap»), i `absent` és «no en parlo»."""
        b = self._pom('B')
        session = self._sessio([(0, 'B', 'chest'), (1, 'BB', 'bottom')])
        self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': o, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': i}
            for o, i in ((0, ''), (1, 'bottom'))])

        session.refresh_from_db()
        self._patch(session, poms_confirmats=[b.id], files_confirmades=[])
        self.assertEqual(self._actius(session), [False, False])

    # ── 2 · NO-REGRESSIÓ: sense el camp, el comportament d'avui ───────────────────
    def test_sense_el_camp_mana_poms_confirmats_com_sempre(self):
        pit = self._pom('CH')
        cintura = self._pom('WA')
        session = self._sessio([(0, 'CH', 'chest'), (1, 'WA', 'waist')])
        self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': pit.id},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': cintura.id}])

        session.refresh_from_db()
        resp = self._patch(session, poms_confirmats=[pit.id])
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        self.assertEqual(self._actius(session), [True, False])

    def test_un_pom_del_cataleg_que_el_document_no_menciona_segueix_entrant(self):
        """L'altra feina de `poms_confirmats`, que `files_confirmades` NO substitueix: un POM
        afegit a mà encara no té fila, i per tant no té `ordre` amb què demanar-lo."""
        pit = self._pom('CH')
        afegit = self._pom('EXTRA')
        session = self._sessio([(0, 'CH', 'chest')])
        self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': pit.id}])

        session.refresh_from_db()
        resp = self._patch(session, poms_confirmats=[pit.id, afegit.id], files_confirmades=[0])
        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        session.refresh_from_db()
        files = sorted(session.poms_extrets, key=lambda f: f['ordre'])
        self.assertEqual([f['pom_master_id'] for f in files], [pit.id, afegit.id])
        self.assertEqual([f['actiu'] for f in files], [True, True],
                         'la fila nova neix activa: demanar-la ÉS confirmar-la')
