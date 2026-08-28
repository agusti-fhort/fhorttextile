"""DECISIÓ 7 — LA NOMENCLATURA ÉS SOBIRANIA DEL MODEL.

La llei (Agus, 28/08): el bateig de nomenclatura (`BaseMeasurement.nom_fitxa`) s'edita al
model, per peça, i MAI contamina el catàleg. A l'import, sobre fila verge mana el DOCUMENT;
sobre fila existent mana la Montse. Unicitat dins de l'àmbit de la fila (model+garment+capa).

Els tres trams que aquest fitxer fixa, i el vermell que cadascun hauria vist:

  F1 · LA PORTA ÚNICA. `nom_fitxa` entra per l'endpoint auditat del llapis i SURT del PATCH
       genèric del viewset. Contra el codi vell, `test_f1_la_porta_ampla_ja_no_el_pot_escriure`
       és VERMELL: el camp era escrivible i el serializer el desava sense passar per cap
       comprovació, obrint de passada tota la fila (valor base, origen, toleràncies).

  F2 · LA UNICITAT QUE LA FITXA JA ASSUMEIX. El `TechSheetEditor` resol el lligam fletxa↔fila
       PEL TEXT de la nomenclatura i ho declara al seu comentari. Fins avui res no la
       garantia. Contra el codi vell els dos tests de col·lisió són VERMELLS: l'endpoint
       desava el duplicat amb un 200.

  F3 · L'IMPORT DEIXA DE REBATEJAR. `nom_fitxa` surt dels `defaults` de l'`update_or_create`
       i passa a `create_defaults`. Contra el codi vell,
       `test_f3_el_reimport_no_trepitja_el_bateig_del_tecnic` és VERMELL: el re-import
       substituïa el bateig pel codi del document, en silenci.

⚠️ EL CENS QUE CONDICIONA LA CONSTRAINT (28/08). A `fhort` hi ha 4 parelles vives que
comparteixen `nom_fitxa` dins de l'àmbit —bm 3389/3390 'SR', 2288/2289 i 2230/2231 'J1',
3386/3387 'B'—, totes el MATEIX POM en dues INSTÀNCIES. Són anteriors a la llei i precisament
el que ve a evitar, de manera que la constraint de BD **espera la neteja** i la comprovació
viu a la porta. `test_f2_re_desar_el_mateix_codi_no_es_colisio` és el que fa que aquestes
quatre files es puguin seguir editant mentrestant.
"""
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.extraction_views import import_session_confirmar_view  # noqa: F401
from fhort.models_app.models import BaseMeasurement
from fhort.models_app.serializers import BaseMeasurementSerializer
from fhort.models_app.test_set2_t8_import_per_prenda import (MARE, SEGONA,
                                                             _BaseImportPerPrendaTest)
from fhort.models_app.views import base_measurement_noms_view


class _PortaMixin:
    """El llapis, tal com el crida la graella."""

    def _noms(self, bm, **body):
        req = APIRequestFactory().patch(
            f'/api/v1/base-measurements/{bm.id}/noms/', body, format='json')
        force_authenticate(req, user=self.user)
        return base_measurement_noms_view(req, bm.id)


class PortaUnicaTest(_BaseImportPerPrendaTest, _PortaMixin):
    """F1 · una porta, auditada, per al nom I la nomenclatura."""

    def test_f1_el_llapis_escriu_la_nomenclatura(self):
        bm = self._mesura(self.pit)
        r = self._noms(bm, nom_fitxa='AH')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['nom_fitxa'], 'AH')
        bm.refresh_from_db()
        self.assertEqual(bm.nom_fitxa, 'AH')

    def test_f1_el_llapis_escriu_nom_i_nomenclatura_alhora(self):
        """Els tres camps són el mateix gest: el bateig de la fila."""
        bm = self._mesura(self.pit)
        r = self._noms(bm, nom_canonic_model='Armhole girth', nom_traduit_model='Sisa',
                       nom_fitxa='AH')
        self.assertEqual(r.status_code, 200)
        bm.refresh_from_db()
        self.assertEqual((bm.nom_canonic_model, bm.nom_traduit_model, bm.nom_fitxa),
                         ('Armhole girth', 'Sisa', 'AH'))

    def test_f1_la_porta_ampla_ja_no_el_pot_CANVIAR(self):
        """🚨 El tram d'F1. Contra el codi vell això era VERD i el camp es desava."""
        bm = self._mesura(self.pit)
        ser = BaseMeasurementSerializer(instance=bm, data={'nom_fitxa': 'ZZ'}, partial=True)
        self.assertTrue(ser.is_valid(), ser.errors)
        ser.save()
        bm.refresh_from_db()
        self.assertEqual(bm.nom_fitxa, 'PREVI')      # el de `_mesura`, intacte

    def test_f1_la_porta_ampla_encara_el_pot_escriure_en_NEIXER(self):
        """🚨 L'altra meitat d'F1, i sense ella el tram trencava el camí de PARTIR un POM.

        Una fila amb `instancia` i sense `nom_fitxa` la rebutja la comporta
        `instancia_exigeix_nom` (migració 0074). Si el CREATE no el pogués escriure, la
        germana d'una partició no podria néixer. La llei és la mateixa que F3 aplica a
        l'import: al néixer s'escriu, un cop existeix no es toca.
        """
        # `garment` s'omet: el serializer no accepta la cadena buida i el defecte del model
        # («la mare») és justament el que aquest cas vol.
        ser = BaseMeasurementSerializer(data={
            'model': self.model.id, 'pom': self.cintura.id, 'capa': 'exterior',
            'instancia': 'left', 'base_value_cm': 50.0, 'nom_fitxa': 'WA-L',
        })
        self.assertTrue(ser.is_valid(), ser.errors)
        bm = ser.save()
        self.assertEqual(bm.nom_fitxa, 'WA-L')

    def test_f1_el_limit_es_el_de_la_columna_i_no_el_dels_noms(self):
        """`nom_fitxa` és CharField(20); els dos noms, 160. Un sol màxim hauria deixat
        passar un codi de 30 i hauria petat a la BD amb un 500 mut."""
        bm = self._mesura(self.pit)
        r = self._noms(bm, nom_fitxa='X' * 21)
        self.assertEqual(r.status_code, 400)
        self.assertIn('20', r.data['error'])
        bm.refresh_from_db()
        self.assertEqual(bm.nom_fitxa, 'PREVI')

    def test_f1_buidar_la_nomenclatura_torna_la_fila_al_cataleg(self):
        bm = self._mesura(self.pit)
        self.assertEqual(self._noms(bm, nom_fitxa='').status_code, 200)
        bm.refresh_from_db()
        self.assertEqual(bm.nom_fitxa, '')


class UnicitatTest(_BaseImportPerPrendaTest, _PortaMixin):
    """F2 · dues files del mateix àmbit no comparteixen nomenclatura."""

    def test_f2_dues_files_del_mateix_ambit_no_comparteixen_codi(self):
        """🚨 El tram d'F2. Contra el codi vell això era un 200 i el duplicat es desava.

        ⚠️ La germana ha de partir d'un codi DIFERENT. `_mesura` neix amb 'PREVI' a totes
        dues, i llavors el que es demana no és una col·lisió sinó re-desar el mateix valor —
        que la porta deixa passar a posta (v. `test_f2_re_desar_el_mateix_codi_no_es_colisio`).
        La primera versió d'aquest test ho feia i donava 200: el vermell era del test.
        """
        self._mesura(self.pit)                                  # nom_fitxa='PREVI'
        altra = self._mesura(self.cintura)
        BaseMeasurement.objects.filter(pk=altra.pk).update(nom_fitxa='WA')
        altra.refresh_from_db()
        r = self._noms(altra, nom_fitxa='PREVI')
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['codi'], 'NOMENCLATURA_DUPLICADA')
        altra.refresh_from_db()
        self.assertEqual(altra.nom_fitxa, 'WA')                 # no s'ha desat res

    def test_f2_el_refus_diu_amb_que_xoca_i_que_pot_fer(self):
        """Estil `frase_de_colisio`: acccionable, i amb el POM germà pel seu nom."""
        germana = self._mesura(self.pit)
        self._noms(germana, nom_canonic_model='Chest girth', nom_fitxa='CH')
        altra = self._mesura(self.cintura)
        BaseMeasurement.objects.filter(pk=altra.pk).update(nom_fitxa='WA')
        altra.refresh_from_db()
        r = self._noms(altra, nom_fitxa='CH')
        self.assertEqual(r.status_code, 409)
        self.assertIn('CH', r.data['error'])
        self.assertIn('Chest girth', r.data['error'])
        self.assertIn('nomenclatura diferent', r.data['error'])
        self.assertEqual(r.data['conflicte']['fila_id'], germana.id)

    def test_f2_una_altra_peca_pot_repetir_el_codi(self):
        """L'àmbit és model+garment+capa: la mare i la 02 són àmbits diferents."""
        self._mesura(self.pit, garment=MARE)
        de_la_peca = self._mesura(self.cintura, garment=SEGONA)
        BaseMeasurement.objects.filter(pk=de_la_peca.pk).update(nom_fitxa='WA')
        de_la_peca.refresh_from_db()
        r = self._noms(de_la_peca, nom_fitxa='PREVI')
        self.assertEqual(r.status_code, 200)
        de_la_peca.refresh_from_db()
        self.assertEqual(de_la_peca.nom_fitxa, 'PREVI')

    def test_f2_re_desar_el_mateix_codi_no_es_colisio(self):
        """Les 4 parelles vives del cens han de poder seguir editant el NOM.

        Sense aquesta condició, obrir el llapis en una d'elles i desar sense tocar el codi
        es refusaria contra la seva pròpia germana.
        """
        self._mesura(self.pit)
        bessona = self._mesura(self.cintura)
        BaseMeasurement.objects.filter(pk=bessona.pk).update(nom_fitxa='PREVI')
        bessona.refresh_from_db()
        r = self._noms(bessona, nom_canonic_model='Waist', nom_fitxa='PREVI')
        self.assertEqual(r.status_code, 200)
        bessona.refresh_from_db()
        self.assertEqual(bessona.nom_canonic_model, 'Waist')

    def test_f2_buidar_no_xoca_amb_ningu(self):
        self._mesura(self.pit)
        altra = self._mesura(self.cintura)
        BaseMeasurement.objects.filter(pk=altra.pk).update(nom_fitxa='')
        self.assertEqual(self._noms(altra, nom_fitxa='').status_code, 200)


class ImportNoRebatejaTest(_BaseImportPerPrendaTest, _PortaMixin):
    """F3 · sobre fila verge mana el document; sobre fila existent, la Montse."""

    def test_f3_sobre_fila_verge_mana_el_document(self):
        """El control. Sense això, F3 podria haver tancat l'escriptura sencera."""
        r = self._confirmar(self._sessio(poms=[self.pit]))
        self.assertIn(r.status_code, (200, 201))
        fila = self._files(MARE).get(pom=self.pit)
        self.assertEqual(fila.nom_fitxa, self.pit.codi_client)

    def test_f3_el_reimport_no_trepitja_el_bateig_del_tecnic(self):
        """🚨 El tram d'F3. Contra el codi vell el bateig quedava substituït pel document."""
        self._confirmar(self._sessio(poms=[self.pit]))
        fila = self._files(MARE).get(pom=self.pit)
        self.assertEqual(self._noms(fila, nom_fitxa='SISA-D').status_code, 200)

        r = self._confirmar(self._sessio(
            poms=[self.pit],
            valors={self.pit: {'S': 90.0, 'M': 92.0, 'L': 94.0}}))
        self.assertIn(r.status_code, (200, 201))
        fila.refresh_from_db()
        self.assertEqual(fila.nom_fitxa, 'SISA-D')
        # …i el que l'import SÍ que ha de portar segueix arribant.
        self.assertEqual(float(fila.base_value_cm), 92.0)
