"""Onada 3 · L'IMPORT APREN A DIR DE QUINA INSTÀNCIA PARLA CADA FILA.

EL CAS REAL QUE HO MOTIVA (Agus, aturat a mig import, 14/08): fitxa BROWNIE
BRUMA/RUFFLES. Tres files —B «at the top», BB «at the bottom», B1 «stretched out»— són
EL MATEIX POM B mesurat en tres instàncies/estats diferents. El wizard les tractava com a
col·lisió («Un POM no pot ser dues files») perquè el detector comparava per `pom_master_id`
PELAT (`extraction_views.py:1835`), que és una clau més curta que la identitat de la mesura.

La identitat d'una mesura a la casa són QUATRE eixos: `(pom, capa, instancia, garment)`. El
motor ja hi indexa (`extraction_views.py:2087`) i el `garment` ja viatja des de T8 —viu a la
SESSIÓ, perquè un import és una prenda. Els altres dos no viatjaven de cap manera: el confirm
els escrivia HARDCODEJATS (`capa=SLUG_DEFECTE, instancia=''`) i el comentari de
`extraction_views.py:2754` ho declarava en clar, anomenant aquest tram «l'Onada 3».

El que aquests tests defensen, i que és tot el que la peça promet:

  1. **Dues files amb el MATEIX POM i instàncies DIFERENTS no són cap col·lisió**, i totes
     dues s'escriuen. És el cas de la Brumà.
  2. **Dues files amb la MATEIXA identitat sencera SÍ que ho són.** La col·lisió no
     desapareix: es fa precisa. Sense això, la peça no hauria tancat el forat sinó obert-lo.
  3. **El comportament d'avui no es mou**: sense declarar instància, dues files al mateix POM
     segueixen sent l'error de sempre (el test que ho fixa viu a
     `test_import_poms_resolucions.py` i segueix verd; aquí es repeteix el cas mínim per
     llegir els tres junts).

NO hi ha suggeriment automàtic i és una decisió d'Agus (14/08): el lèxic que llegiria
«stretched out» → Extended és tram futur, quan hi hagi corpus d'imports reals que l'ensenyi.
Fins llavors mana la llei de l'import — el que no se sap segur, ho decideix l'humà.
"""
import uuid

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.accounts.models import UserProfile
from fhort.models_app.extraction_views import import_session_poms_view
from fhort.models_app.models import ImportSession
from fhort.models_app.test_import_poms_duplicats import _TenantBase
from fhort.pom.models import POMMaster


class IdentitatSenceraTest(_TenantBase):

    def setUp(self):
        super().setUp()
        user = get_user_model().objects.create_user(username='tec-ins', password='x')
        UserProfile.objects.get_or_create(
            user=user, defaults={'nom_complet': 'Tècnic', 'rol_nom': 'patronista'})
        self.user = user
        self.factory = APIRequestFactory()

    def _sessio(self, files):
        """`files` = [(ordre, codi_fitxa, descripcio)] — totes sense POM encara."""
        return ImportSession.objects.create(
            token=uuid.uuid4(), estat='POMS',
            poms_extrets=[{
                'codi_fitxa': codi, 'descripcio': desc, 'pom_master_id': None,
                'values': {}, 'actiu': False, 'ordre': ordre,
            } for ordre, codi, desc in files],
        )

    def _pom(self, codi, nom=None):
        return POMMaster.objects.create(pom_global=None, codi_client=codi,
                                        nom_client=nom or codi, actiu=True)

    def _patch(self, session, **body):
        req = self.factory.patch(f'/api/v1/import-sessions/{session.token}/poms/',
                                 body, format='json')
        force_authenticate(req, user=self.user)
        return import_session_poms_view(req, token=str(session.token))

    # ── 1 · EL CAS DE LA BRUMÀ ────────────────────────────────────────────────────
    def test_mateix_pom_amb_instancies_diferents_no_es_col_lisio(self):
        """B «at the top» · BB «at the bottom» · B1 «stretched out» → el mateix POM B."""
        b = self._pom('B', 'Bust')
        session = self._sessio([(0, 'B', 'at the top'),
                                (1, 'BB', 'at the bottom'),
                                (2, 'B1', 'stretched out')])

        resp = self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': ''},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': 'bottom'},
            {'ordre': 2, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': 'extended'},
        ])

        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        session.refresh_from_db()
        files = sorted(session.poms_extrets, key=lambda f: f['ordre'])
        self.assertEqual([f['pom_master_id'] for f in files], [b.id, b.id, b.id])
        # …i la identitat que la persona ha triat queda DESADA a la fila: sense això el
        # confirm tornaria a escriure les tres al mateix lloc i dues es perdrien.
        self.assertEqual([f.get('instancia') for f in files], ['', 'bottom', 'extended'])

    def test_la_capa_tambe_distingeix(self):
        """L'altre eix del parell. Exterior i folre del mateix POM no es trepitgen."""
        b = self._pom('B', 'Bust')
        session = self._sessio([(0, 'B', 'shell'), (1, 'B', 'lining')])

        resp = self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': b.id, 'capa': 'exterior'},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': b.id, 'capa': 'folre'},
        ])

        self.assertEqual(resp.status_code, 200, getattr(resp, 'data', None))
        session.refresh_from_db()
        files = sorted(session.poms_extrets, key=lambda f: f['ordre'])
        self.assertEqual([f.get('capa') for f in files], ['exterior', 'folre'])

    # ── 2 · LA COL·LISIÓ DE DEBÒ ──────────────────────────────────────────────────
    def test_identitat_sencera_repetida_si_que_es_col_lisio(self):
        b = self._pom('B', 'Bust')
        session = self._sessio([(0, 'B', 'at the top'), (1, 'B', 'també at the top')])

        resp = self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': 'left'},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': 'left'},
        ])

        self.assertEqual(resp.status_code, 409)
        self.assertEqual([e['error'] for e in resp.data['errors']], ['pom_ja_usat'])
        self.assertEqual(resp.data['errors'][0]['ordre'], 1)
        session.refresh_from_db()
        self.assertIsNone(session.poms_extrets[0]['pom_master_id'],
                          "tot o res: ni la bona s'escriu")

    def test_la_capa_repetida_amb_la_mateixa_instancia_tambe_col_lisiona(self):
        b = self._pom('B', 'Bust')
        session = self._sessio([(0, 'B', 'folre'), (1, 'B', 'folre altre cop')])

        resp = self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': b.id,
             'capa': 'folre', 'instancia': 'left'},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': b.id,
             'capa': 'folre', 'instancia': 'left'},
        ])
        self.assertEqual(resp.status_code, 409)
        self.assertEqual([e['error'] for e in resp.data['errors']], ['pom_ja_usat'])

    # ── 3 · EL CONTROL: sense instància, el comportament d'avui ───────────────────
    def test_sense_declarar_res_dues_files_al_mateix_pom_segueixen_col_lisionant(self):
        b = self._pom('B', 'Bust')
        session = self._sessio([(0, 'B', 'chest'), (1, 'B', 'chest 2')])

        resp = self._patch(session, poms_confirmats=[], resolucions=[
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': b.id},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': b.id},
        ])

        self.assertEqual(resp.status_code, 409)
        self.assertEqual([e['error'] for e in resp.data['errors']], ['pom_ja_usat'])
