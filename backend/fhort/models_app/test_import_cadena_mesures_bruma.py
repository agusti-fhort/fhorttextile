"""Onada 3 · LA CADENA DE MESURES SENCERA: el que la persona decideix al pas 2 arriba al disc.

EL CAS REAL (Agus, aturat a mig import, 14/08): fitxa BROWNIE BRUMA/RUFFLES. Tres files —B
«at the top», BB «at the bottom», B1 «stretched out»— són EL MATEIX POM B mesurat en tres
instàncies, i porten TRES VALORS DIFERENTS (30 · 31 · 40). El germà d'aquest fitxer,
`test_import_identitat_instancia.py`, defensa el PAS 2: que les tres files es puguin resoldre
sense que el detector cridi col·lisió. Però resoldre-les no serveix de res si el valor no
arriba: entre el pas 2 i el disc hi ha la CADENA DE MESURES, i tota ella indexava per
`pom_master_id` PELAT —una clau més curta que la identitat de la mesura.

El dany, i és el pitjor gènere (no crida): el pas 3 desa
`{pom_master_id, talla_label, valor}` i el pas 5 en fa `{pom_id: {talla: valor}}`. Amb tres
files al mateix POM, el diccionari en reté UNA (l'última que passa) i les tres files
s'escriuen amb el MATEIX valor. Cap error, cap avís: la fitxa queda amb el 40 repetit tres
cops i el 30 i el 31 no existeixen enlloc.

El que aquest fitxer defensa:

  1. **Els tres valors arriben a les tres files** (`test_els_tres_valors_de_la_bruma…`).
     És el guard que ha de veure's VERMELL abans de la peça: amb la cadena vella escriu
     30/30/30 o 40/40/40 segons quina fila guanyi el diccionari.
  2. **La cadena NOVA parla per FILA (`ordre`) i els eixos els HERETA de la fila**, mai del
     payload: la identitat la decideix el pas 2, i el pas 3 només diu valors. Si el pas 3
     pogués declarar capa/instància pel seu compte hi hauria dues fonts de veritat per a la
     mateixa cosa, i el dia que discrepessin guanyaria la darrera a escriure.
  3. **NO-REGRESSIÓ, i és el PRIMER guard, no l'últim**: el payload d'avui (un POM per fila,
     sense `ordre`) ha de fer EXACTAMENT el que fa avui. Tot el que aquesta peça afegeix és
     additiu; una sessió a mig fer amb el front vell ha de poder-se confirmar igual.
"""
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.extraction_views import (
    import_session_confirmar_view, import_session_grading_preview_view,
    import_session_mesures_view, import_session_poms_view)
from fhort.models_app.models import BaseMeasurement, ImportSession
from fhort.models_app.tests_sembra_grading import _BaseSembraTest
from fhort.pom.models import GradingRule, GradingRuleSet


class _BaseCadenaTest(_BaseSembraTest):
    """Un model amb sistema S·M·L i base M, i la sessió tal com el pas 1 la deixa."""

    def setUp(self):
        super().setUp()
        self.ss = self._size_system('BRUMA', talles=('S', 'M', 'L'))
        self.model = self._model(size_system=self.ss, base_size_label='M',
                                 size_run_model='S·M·L')
        self.factory = APIRequestFactory()

    # ── bastida ───────────────────────────────────────────────────────────────
    def _sessio(self, files):
        """`files` = [(ordre, codi_fitxa, descripcio)] — encara sense POM (pas 1 acabat)."""
        return ImportSession.objects.create(
            estat='POMS', model=self.model, garment='',
            poms_extrets=[{'codi_fitxa': codi, 'descripcio': desc, 'pom_master_id': None,
                           'values': {}, 'actiu': False, 'ordre': ordre}
                          for ordre, codi, desc in files],
            run_conciliat={'talla_mapping': [{'document': et, 'model': et}
                                             for et in ('S', 'M', 'L')]},
            resultat={'extraccio': {'sizes': ['S', 'M', 'L'], 'base_size': 'M'}},
        )

    def _pas2(self, session, resolucions):
        req = self.factory.patch(f'/api/v1/import-sessions/{session.token}/poms/',
                                 {'poms_confirmats': [], 'resolucions': resolucions},
                                 format='json')
        force_authenticate(req, user=self.user)
        return import_session_poms_view(req, token=str(session.token))

    def _pas3(self, session, mesures):
        req = self.factory.patch(f'/api/v1/import-sessions/{session.token}/mesures/',
                                 {'mesures': mesures}, format='json')
        force_authenticate(req, user=self.user)
        return import_session_mesures_view(req, token=str(session.token))

    def _pas5(self, session, **body):
        """El desament definitiu. `no_container`: la tria de contenidor és una altra llei."""
        body.setdefault('container_choice', 'no_container')
        req = self.factory.post(f'/api/v1/import-sessions/{session.token}/confirmar/',
                                body, format='json')
        force_authenticate(req, user=self.user)
        return import_session_confirmar_view(req, session.token)

    def _files_del_pom(self, pom):
        return {(bm.capa, bm.instancia): bm.base_value_cm
                for bm in BaseMeasurement.objects.filter(model=self.model, pom=pom)}


class CadenaDeMesuresBrumaTest(_BaseCadenaTest):
    """EL GUARD: tres instàncies del mateix POM, tres valors, i tots tres al disc."""

    PREFIX = 'BRUMA'

    def test_els_tres_valors_de_la_bruma_arriben_a_les_tres_files(self):
        b = self._pom('B')
        session = self._sessio([(0, 'B', 'at the top'),
                                (1, 'BB', 'at the bottom'),
                                (2, 'B1', 'stretched out')])

        # PAS 2 · la persona diu de quina instància parla cada fila.
        res = self._pas2(session, [
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': ''},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': 'bottom'},
            {'ordre': 2, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': 'extended'},
        ])
        self.assertEqual(res.status_code, 200, getattr(res, 'data', None))

        # PAS 3 · la taula. Cada fila porta el SEU valor, i parla per `ordre`: el payload no
        # torna a dir la identitat, que ja és decisió desada del pas 2.
        session.refresh_from_db()
        mesures = []
        for ordre, base in ((0, 30.0), (1, 31.0), (2, 40.0)):
            for et, delta in (('S', -2.0), ('M', 0.0), ('L', 2.0)):
                mesures.append({'ordre': ordre, 'talla_label': et, 'valor': base + delta})
        res = self._pas3(session, mesures)
        self.assertEqual(res.status_code, 200, getattr(res, 'data', None))

        # PAS 5 · el disc.
        session.refresh_from_db()
        res = self._pas5(session)
        self.assertEqual(res.status_code, 201, getattr(res, 'data', None))

        self.assertEqual(
            self._files_del_pom(b),
            {('exterior', ''): 30.0, ('exterior', 'bottom'): 31.0,
             ('exterior', 'extended'): 40.0},
            'les tres instàncies han d\'arribar al disc amb el SEU valor')

    def test_els_eixos_els_mana_la_fila_i_no_el_payload_de_mesures(self):
        """Una mesura que intenti declarar la seva pròpia instància no reescriu la decisió.

        La identitat es decideix al pas 2 i es desa a la fila. Si el pas 3 la pogués tornar a
        dir, dues fonts dirien la mateixa cosa i el dia que discrepessin guanyaria l'última.
        """
        b = self._pom('B')
        session = self._sessio([(0, 'B', 'at the top'), (1, 'BB', 'at the bottom')])
        self._pas2(session, [
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': ''},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': 'bottom'},
        ])
        session.refresh_from_db()

        mesures = []
        for ordre, base in ((0, 30.0), (1, 31.0)):
            for et, delta in (('S', -2.0), ('M', 0.0), ('L', 2.0)):
                # `instancia` mentidera al payload: la fila 1 diu que és la 'left'.
                mesures.append({'ordre': ordre, 'talla_label': et, 'valor': base + delta,
                                'instancia': 'left'})
        self._pas3(session, mesures)
        session.refresh_from_db()
        self.assertEqual(self._pas5(session).status_code, 201)

        self.assertEqual(self._files_del_pom(b),
                         {('exterior', ''): 30.0, ('exterior', 'bottom'): 31.0})


class CadenaNoRegressioTest(_BaseCadenaTest):
    """EL PRIMER GUARD: el payload d'avui fa exactament el d'avui."""

    PREFIX = 'BRUMAC'

    def test_un_pom_per_fila_amb_el_payload_vell_escriu_igual(self):
        """Sense `ordre` i sense instàncies: el camí de sempre, byte a byte."""
        pit = self._pom('CH')
        cintura = self._pom('WA')
        session = self._sessio([(0, 'CH', 'chest'), (1, 'WA', 'waist')])
        self._pas2(session, [
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': pit.id},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': cintura.id},
        ])
        session.refresh_from_db()

        mesures = []
        for pom, base in ((pit, 100.0), (cintura, 80.0)):
            for et, delta in (('S', -2.0), ('M', 0.0), ('L', 2.0)):
                mesures.append({'pom_master_id': pom.id, 'talla_label': et,
                                'valor': base + delta})
        self.assertEqual(self._pas3(session, mesures).status_code, 200)
        session.refresh_from_db()
        self.assertEqual(self._pas5(session).status_code, 201)

        self.assertEqual(self._files_del_pom(pit), {('exterior', ''): 100.0})
        self.assertEqual(self._files_del_pom(cintura), {('exterior', ''): 80.0})

    def test_el_payload_vell_amb_una_fila_que_declara_instancia_hi_arriba_igual(self):
        """Sessió a mig fer: el pas 2 ja parla d'instàncies i el front encara no.

        Una fila amb instància declarada i mesures SENSE `ordre` (front vell) ha de rebre el
        seu valor igualment: mentre el POM no es reparteixi entre dues files, la fila que el
        té és l'única que el pot voler. Sense aquesta herència, l'única cosa que la peça
        hauria aconseguit és que una sessió a mig camí es confirmés amb la mesura buida.
        """
        b = self._pom('B')
        session = self._sessio([(0, 'B', 'at the bottom')])
        self._pas2(session, [
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': 'bottom'},
        ])
        session.refresh_from_db()

        mesures = [{'pom_master_id': b.id, 'talla_label': et, 'valor': v}
                   for et, v in (('S', 28.0), ('M', 30.0), ('L', 32.0))]
        self.assertEqual(self._pas3(session, mesures).status_code, 200)
        session.refresh_from_db()
        self.assertEqual(self._pas5(session).status_code, 201)

        self.assertEqual(self._files_del_pom(b), {('exterior', 'bottom'): 30.0})

    def test_el_preview_respon_amb_la_mateixa_clau_amb_que_se_li_pregunta(self):
        """La TERCERA porta: `base_values`.

        Un objecte JSON no pot tenir clau composta, i per això la forma que sap parlar de
        tres files del mateix POM és una LLISTA. Si la resposta tornés per `pom_id`, les
        tres files de la Brumà s'omplirien amb la graduació d'una sola —el mateix col·lapse,
        una porta més enllà.
        """
        b = self._pom('B')
        rs = GradingRuleSet.objects.create(nom=self._codi('RS'), size_system=self.ss)
        GradingRule.objects.create(rule_set=rs, pom=b,
                                   talla_base=self.ss.talles.get(etiqueta='M'),
                                   logica=GradingRule.LOGICA_LINEAR, increment='2.00',
                                   actiu=True)
        self.model.grading_rule_set = rs
        self.model.save(update_fields=['grading_rule_set'])

        session = self._sessio([(0, 'B', 'at the top'), (1, 'B1', 'stretched out')])
        self._pas2(session, [
            {'ordre': 0, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': ''},
            {'ordre': 1, 'accio': 'vincula', 'pom_master_id': b.id, 'instancia': 'extended'},
        ])
        session.refresh_from_db()

        # FORMA NOVA · per fila.
        req = self.factory.post(f'/api/v1/import-sessions/{session.token}/grading-preview/',
                                {'base_values': [{'ordre': 0, 'valor': 30},
                                                 {'ordre': 1, 'valor': 40}]}, format='json')
        force_authenticate(req, user=self.user)
        res = import_session_grading_preview_view(req, token=str(session.token))
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['clau'], 'ordre')
        self.assertEqual(set(res.data['grading']), {'0', '1'})
        self.assertNotEqual(res.data['grading']['0']['S'], res.data['grading']['1']['S'])

        # FORMA D'AVUI · per POM, byte a byte com abans d'aquesta peça.
        req = self.factory.post(f'/api/v1/import-sessions/{session.token}/grading-preview/',
                                {'base_values': {str(b.id): 30}}, format='json')
        force_authenticate(req, user=self.user)
        res = import_session_grading_preview_view(req, token=str(session.token))
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['clau'], 'pom_master_id')
        self.assertEqual(set(res.data['grading']), {str(b.id)})

    def test_una_mesura_amb_ordre_desconegut_no_es_desa(self):
        """Un `ordre` que no és de cap fila no pot inventar-se una mesura sense identitat."""
        pit = self._pom('CH')
        session = self._sessio([(0, 'CH', 'chest')])
        self._pas2(session, [{'ordre': 0, 'accio': 'vincula', 'pom_master_id': pit.id}])
        session.refresh_from_db()

        res = self._pas3(session, [{'ordre': 99, 'talla_label': 'M', 'valor': 50.0}])
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['n_valors'], 0)
        session.refresh_from_db()
        self.assertEqual(session.resultat.get('mesures'), [])
