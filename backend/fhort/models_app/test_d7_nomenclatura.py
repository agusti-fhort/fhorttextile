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

       ⚠️ **F2 HA CANVIAT DE VEREDICTE EL 01/09 (Decisió 8)**: de 409-i-no-desa a
       200-desa-i-avisa, i l'àmbit passa de 3 camps a 4 (hi entra `instancia`) i només és
       homonímia si el POM DIFEREIX. La classe `UnicitatTest` en porta l'acta sencera; el
       supòsit del `TechSheetEditor` deixa de ser «cert perquè es comprova» i torna a ser
       «cert perquè s'avisa i algú ho mira».

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
    """F2 · dues files homònimes del mateix àmbit **es desen i s'avisen** (Decisió 8, 01/09).

    🚨 AQUESTA CLASSE PROVAVA UN 409 I ARA PROVA UN 200. La D7 refusava i no desava; la D8 diu
    que la unicitat dins del model és ADVISORY. El que es prova, doncs, ja no és que la porta
    digui que no: és que **desi igualment i ho digui**, amb el mateix camp i la mateixa forma
    que `gravar-pom` (`avisos_nomenclatura`), perquè la pantalla els consumeixi igual.

    Els dos canvis d'àmbit hi van al costat i tenen test propi: hi entra `instancia` (4 camps)
    i només és homonímia si el POM DIFEREIX.
    """

    def test_f2_dues_files_del_mateix_ambit_ES_DESEN_i_avisen(self):
        """La meitat que importa és **desar**: un avís que perd feina és un refús mal educat."""
        self._mesura(self.pit)                                  # nom_fitxa='PREVI'
        altra = self._mesura(self.cintura)
        BaseMeasurement.objects.filter(pk=altra.pk).update(nom_fitxa='WA')
        altra.refresh_from_db()
        r = self._noms(altra, nom_fitxa='PREVI')
        self.assertEqual(r.status_code, 200)
        altra.refresh_from_db()
        self.assertEqual(altra.nom_fitxa, 'PREVI')              # ← s'HA desat (abans: 'WA')
        self.assertEqual(len(r.data['avisos_nomenclatura']), 1)

    def test_f2_l_avis_diu_l_ambit_i_els_dos_POMS(self):
        """Mateixa forma que la de `gravar-pom`: la pantalla ha de poder trobar-hi les files."""
        germana = self._mesura(self.pit)
        self._noms(germana, nom_canonic_model='Chest girth', nom_fitxa='CH')
        altra = self._mesura(self.cintura)
        BaseMeasurement.objects.filter(pk=altra.pk).update(nom_fitxa='WA')
        altra.refresh_from_db()
        avis = self._noms(altra, nom_fitxa='CH').data['avisos_nomenclatura'][0]
        self.assertEqual(avis['nom_fitxa'], 'CH')
        self.assertEqual((avis['garment'], avis['capa'], avis['instancia']),
                         (MARE, altra.capa, ''))
        self.assertEqual(sorted(avis['poms']), sorted([altra.pom_id, germana.pom_id]))
        # `ref` és la PK a aquesta porta (a `gravar-pom` és l'índex del payload): les dues
        # respostes són la mateixa forma amb el mateix SIGNIFICAT de `ref`.
        self.assertIn(germana.pk, avis['files'])

    def test_f2_ja_no_hi_ha_CAP_refus(self):
        """🚨 El contracte vell no ha de deixar rastre: qui el llegís es pensaria que no s'ha desat."""
        self._mesura(self.pit)
        altra = self._mesura(self.cintura)
        BaseMeasurement.objects.filter(pk=altra.pk).update(nom_fitxa='WA')
        altra.refresh_from_db()
        r = self._noms(altra, nom_fitxa='PREVI')
        self.assertNotEqual(r.status_code, 409)
        self.assertNotIn('conflicte', r.data)
        self.assertNotIn('error', r.data)

    def test_f2_una_altra_peca_pot_repetir_el_codi(self):
        """L'àmbit segueix incloent `garment`: la mare i la 02 són àmbits diferents."""
        self._mesura(self.pit, garment=MARE)
        de_la_peca = self._mesura(self.cintura, garment=SEGONA)
        BaseMeasurement.objects.filter(pk=de_la_peca.pk).update(nom_fitxa='WA')
        de_la_peca.refresh_from_db()
        r = self._noms(de_la_peca, nom_fitxa='PREVI')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['avisos_nomenclatura'], [])
        de_la_peca.refresh_from_db()
        self.assertEqual(de_la_peca.nom_fitxa, 'PREVI')

    # ── ELS DOS CANVIS D'ÀMBIT DE LA D8 ──────────────────────────────────────────────────

    def test_f2_D8_la_INSTANCIA_entra_a_l_ambit(self):
        """🚨 Amb els 3 camps de la D7 això era un 409; amb els 4 de la D8 no és res.

        ⚠️ I és la marxa enrere d'un argument EXPLÍCIT de la D7, que deixava `instancia` fora
        a posta perquè la sisa dreta i l'esquerra tinguessin noms diferents. Si algun dia es
        vol recuperar aquella vigilància, serà amb un avís PROPI d'una altra família — no
        tornant a tancar aquesta porta. El test és aquí perquè el canvi no passi desapercebut.
        """
        germana = self._mesura(self.pit)
        BaseMeasurement.objects.filter(pk=germana.pk).update(instancia='left')
        altra = self._mesura(self.cintura)
        BaseMeasurement.objects.filter(pk=altra.pk).update(instancia='right', nom_fitxa='WA')
        altra.refresh_from_db()
        r = self._noms(altra, nom_fitxa='PREVI')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['avisos_nomenclatura'], [])

    def test_f2_D8_el_mateix_POM_al_mateix_ambit_NO_POT_EXISTIR(self):
        """🚨 LA 3a EXIGÈNCIA DE LA D8 ÉS ESTRUCTURAL AQUÍ, NO UNA BRANCA DE CODI.

        La D8 demana que només sigui homonímia si el POM DIFEREIX. A `gravar-pom` aquella
        condició fa feina de debò —el payload pot dur dues entrades del mateix POM abans que cap
        índex hi digui res, i té test propi—, però **en aquesta porta no es pot arribar a
        exercir**: `UNIQUE (model_id, pom_id, capa, instancia, garment)` garanteix com a molt
        UNA fila per POM dins de cada àmbit de quatre camps, o sigui que tota germana que
        `avisos_de_rebateig` pugui trobar té per força un POM diferent.

        Es prova la invariant i no la branca, perquè és la invariant el que ho sosté: el dia que
        algú relaxi l'índex, aquest test cau i la condició passarà a fer feina també aquí.
        """
        from django.db import IntegrityError, transaction
        germana = self._mesura(self.pit)
        with self.assertRaises(IntegrityError), transaction.atomic():
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pit, base_value_cm=101.0, origen='MANUAL',
                is_active=True, ordre=2, nom_fitxa='WA', garment=germana.garment,
                capa=germana.capa, instancia=germana.instancia)

    def test_f2_D8_el_mateix_POM_en_una_ALTRA_instancia_no_avisa(self):
        """El cas de les 4 parelles vives, per l'altra banda: l'àmbit ja les separa.

        ⚠️ I aquesta és la cara que la D7 vigilava i la D8 deixa de veure (v. la nota d'
        `avisos_de_rebateig`): la sisa dreta i l'esquerra poden tornar a dir-se totes dues 'AH'
        sense que ningú digui res. `instancia_exigeix_nom` demana que en tinguin UN, no que en
        tinguin un de DIFERENT.
        """
        germana = self._mesura(self.pit)
        altra = BaseMeasurement.objects.create(
            model=self.model, pom=self.pit, base_value_cm=101.0, origen='MANUAL',
            is_active=True, ordre=2, nom_fitxa='WA', garment=germana.garment,
            capa=germana.capa, instancia='right')
        r = self._noms(altra, nom_fitxa=germana.nom_fitxa)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['avisos_nomenclatura'], [])
        altra.refresh_from_db()
        self.assertEqual(altra.nom_fitxa, germana.nom_fitxa)

    # ── EL QUE NO CANVIA ─────────────────────────────────────────────────────────────────

    def test_f2_re_desar_el_mateix_codi_no_es_pregunta(self):
        """Les 4 parelles vives del cens: tocar-los el nom llarg no ha de dir-los res.

        Amb l'àmbit de 4 camps ja no són homònimes de res (són el mateix POM en dues
        instàncies), però la condició «només si el valor CANVIA» es queda igualment: el que no
        s'ha tocat no s'ha de tornar a jutjar.
        """
        self._mesura(self.pit)
        bessona = self._mesura(self.cintura)
        BaseMeasurement.objects.filter(pk=bessona.pk).update(nom_fitxa='PREVI')
        bessona.refresh_from_db()
        r = self._noms(bessona, nom_canonic_model='Waist', nom_fitxa='PREVI')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['avisos_nomenclatura'], [])
        bessona.refresh_from_db()
        self.assertEqual(bessona.nom_canonic_model, 'Waist')

    def test_f2_buidar_no_xoca_amb_ningu(self):
        self._mesura(self.pit)
        altra = self._mesura(self.cintura)
        BaseMeasurement.objects.filter(pk=altra.pk).update(nom_fitxa='')
        r = self._noms(altra, nom_fitxa='')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['avisos_nomenclatura'], [])

    def test_f2_el_camp_hi_es_SEMPRE(self):
        """Mateix argument que a `gravar-pom`: el consumidor no ha de distingir «no n'hi ha»
        de «aquesta porta encara no ho serveix»."""
        bm = self._mesura(self.pit)
        r = self._noms(bm, nom_canonic_model='Chest')
        self.assertIn('avisos_nomenclatura', r.data)


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
