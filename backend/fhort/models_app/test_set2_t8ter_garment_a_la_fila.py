"""SET-2/T8-ter — EL GARMENT BAIXA A LA FILA: un import, N peces (2026-08-16).

**REOBERTURA CONSCIENT DE T8** (Agus, Patró C). T8 va decidir «un import = una prenda» i va
posar el garment a `ImportSession`; la decisió era correcta amb el que hi havia, perquè llavors
la fila no tenia transport per a cap eix propi. L'Onada 3 (14/08) el va construir —capa i
instància viatgen a la fila i sobreviuen del pas 2 al confirm— i amb ell la premissa ha caducat:
el garment era **l'últim eix que quedava a la sessió** i baixa a la fila pel mateix camí.

EL FET QUE HO MOTIVA, i és de la Brumà de debò (sessió 113, 16/08): un sol document porta la
FALDILLA i el SHORT. Amb el garment a la sessió, «G1 · Bottom height» de la faldilla i
«M1 · Bottom hem height» del short —**el mateix POMMaster 962**— voldrien ocupar la mateixa
cel·la, i el detector del pas 2 les declarava en col·lisió. La sortida que va quedar gravada a
staging va ser inventar-li una instància al short (`instancia='relaxed'`), que **no descriu res**
d'una alçada de baix: era l'únic eix lliure per separar dues files que en realitat es
distingeixen per la PEÇA. Amb l'eix bo, les dues recuperen `instancia=''` i diuen la veritat.

ELS VERMELLS QUE AQUEST FITXER VIGILA
  1 · Dues files del mateix POM amb la MATEIXA capa i instància, en peces diferents, s'han
      d'escriure com a DUES mesures. Amb la clau escalar el confirm en desava una i l'altra es
      perdia sense dir res (`update_or_create` sobre la mateixa clau).
  2 · El detector del pas 2 NO les pot declarar en col·lisió: són cel·les diferents.
  3 · La col·lisió de debò —identitat sencera **i la mateixa peça**— ha de seguir mossegant.
      És el control que trenca la coincidència: sense ell, un detector que sempre digués «no hi
      ha col·lisió» passaria el vermell 2 i semblaria bo.
  4 · Les tres podes del confirm resolen per PECES ANOMENADES, en plural. Un import que porta
      faldilla i short no pot deixar el short fora de la poda (les seves files ràncies
      sobreviurien en silenci) ni deixar que els POMs del short protegeixin els de la faldilla.

EL CONTROL de no-regressió és `ImportSensePeçaALaFilaTest`: una tramesa on cap fila declara res
s'ha de comportar EXACTAMENT com abans d'aquesta peça —totes les files a la peça de la sessió—,
que és el 100% del corpus viu (16 sessions al tenant `fhort`, totes amb `garment=''`).
"""
from fhort.models_app.extraction_views import (
    _garment_de, _identitat, _pla_de_resolucions, _proposta_de_peca)
from fhort.models_app.models import BaseMeasurement, ModelGarment

from fhort.models_app.test_set2_t8_import_per_prenda import (
    MARE, SEGONA, _BaseImportPerPrendaTest)


class ElHelperDeLEixTest(_BaseImportPerPrendaTest):
    """`_garment_de` — el predicat és `is None`, i la diferència no és teòrica."""

    PREFIX = 'T8T0'

    def test_absent_hereta_el_de_la_sessio(self):
        self.assertEqual(_garment_de({}, SEGONA), SEGONA)
        self.assertEqual(_garment_de({'capa': 'folre'}, SEGONA), SEGONA)

    def test_buit_explicit_es_una_decisio_i_diu_la_mare(self):
        """El vermell d'`or`: amb `or` no es podria dir mai «mare» dins d'un import obert des
        d'una peça, que és exactament el gest que el desdoblament necessita."""
        self.assertEqual(_garment_de({'garment': ''}, SEGONA), MARE)

    def test_el_seu_mana_sobre_el_de_la_sessio(self):
        self.assertEqual(_garment_de({'garment': SEGONA}, MARE), SEGONA)

    def test_la_identitat_porta_quatre_eixos(self):
        ident = _identitat({'pom_master_id': 7, 'capa': 'folre', 'instancia': 'left'}, SEGONA)
        self.assertEqual(ident, (7, 'folre', 'left', SEGONA))


class DuesPecesAlMateixImportTest(_BaseImportPerPrendaTest):
    """EL VERMELL PRINCIPAL — el cas Brumà, reduït a la seva forma.

    El MATEIX POM, la MATEIXA capa, la MATEIXA instància (la única, `''`), en dues peces. Són
    dues mesures i han de ser dues files.
    """

    PREFIX = 'T8T1'

    def _sessio_dues_peces(self):
        """Una tramesa amb l'eix DECLARAT A LA FILA: la primera a la mare, la segona a la 02."""
        s = self._sessio(garment=MARE, poms=[self.pit])
        s.poms_extrets = [
            {'codi_fitxa': 'G1', 'descripcio': 'Bottom height',
             'pom_master_id': self.pit.id, 'actiu': True, 'ordre': 0, 'garment': MARE},
            {'codi_fitxa': 'M1', 'descripcio': 'Bottom hem height',
             'pom_master_id': self.pit.id, 'actiu': True, 'ordre': 1, 'garment': SEGONA},
        ]
        # Els valors parlen per FILA (`ordre`), que és el contracte de l'Onada 3.
        s.resultat = {**s.resultat, 'mesures': [
            {'pom_master_id': self.pit.id, 'ordre': 0, 'talla_label': et, 'valor': v,
             'capa': 'exterior', 'instancia': '', 'garment': MARE}
            for et, v in (('S', 8.0), ('M', 9.0), ('L', 10.0))
        ] + [
            {'pom_master_id': self.pit.id, 'ordre': 1, 'talla_label': et, 'valor': v,
             'capa': 'exterior', 'instancia': '', 'garment': SEGONA}
            for et, v in (('S', 3.0), ('M', 4.0), ('L', 5.0))
        ]}
        s.save()
        return s

    def test_el_mateix_pom_a_dues_peces_son_dues_files(self):
        res = self._confirmar(self._sessio_dues_peces())
        self.assertEqual(res.status_code, 201, res.data)

        files = BaseMeasurement.objects.filter(model=self.model, pom=self.pit)
        self.assertEqual(files.count(), 2, 'una de les dues s\'ha perdut al confirm')
        self.assertEqual({f.garment for f in files}, {MARE, SEGONA})

    def test_cada_fila_es_queda_el_SEU_valor(self):
        """El dany silenciós: amb la clau escalar la segona trepitjava la primera i el model
        quedava amb un sol valor, sense error i amb la fitxa aparentment bé."""
        self._confirmar(self._sessio_dues_peces())
        self.assertEqual(
            BaseMeasurement.objects.get(model=self.model, pom=self.pit, garment=MARE).base_value_cm,
            9.0)
        self.assertEqual(
            BaseMeasurement.objects.get(model=self.model, pom=self.pit, garment=SEGONA).base_value_cm,
            4.0)

    def test_cap_de_les_dues_necessita_una_instancia_inventada(self):
        """La cicatriu que aquest tram esborra: a staging el short va acabar amb
        `instancia='relaxed'` per no xocar amb la faldilla. Amb l'eix bo, totes dues a `''`."""
        self._confirmar(self._sessio_dues_peces())
        for f in BaseMeasurement.objects.filter(model=self.model, pom=self.pit):
            self.assertEqual(f.instancia, '', 'ha calgut inventar una instància per separar-les')


class ElDetectorNoConfonPecesTest(_BaseImportPerPrendaTest):
    """El detector del pas 2: la peça entra a la clau, i la col·lisió es fa PRECISA."""

    PREFIX = 'T8T2'

    def _fila(self, ordre, garment, pid=None):
        return {'ordre': ordre, 'pom_master_id': pid or self.pit.id, 'actiu': True,
                'garment': garment, 'codi_fitxa': f'X{ordre}'}

    def test_mateixa_identitat_en_peces_diferents_no_es_colisio(self):
        poms = [self._fila(0, MARE)]
        pla, errors = _pla_de_resolucions(
            poms + [{'ordre': 1, 'garment': SEGONA}],
            [{'ordre': 1, 'accio': 'vincula', 'pom_master_id': self.pit.id,
              'garment': SEGONA}],
            MARE)
        self.assertEqual(errors, [], 'dues cel·les diferents declarades en col·lisió')
        self.assertEqual(pla[0]['garment'], SEGONA)

    def test_la_colisio_real_segueix_mossegant(self):
        """EL CONTROL QUE TRENCA LA COINCIDÈNCIA. Mateixa identitat sencera **i la mateixa
        peça**: dues mesures que sí que voldrien la mateixa cel·la. Sense aquest test, un
        detector que sempre digués «endavant» passaria el vermell de dalt."""
        poms = [self._fila(0, SEGONA)]
        pla, errors = _pla_de_resolucions(
            poms + [{'ordre': 1, 'garment': SEGONA}],
            [{'ordre': 1, 'accio': 'vincula', 'pom_master_id': self.pit.id,
              'garment': SEGONA}],
            MARE)
        self.assertEqual(pla, [])
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['error'], 'pom_ja_usat')
        self.assertEqual(errors[0]['garment'], SEGONA)


class LaPodaRespectaLesFronteresTest(_BaseImportPerPrendaTest):
    """Les tres podes del confirm, ara amb PECES ANOMENADES en plural (llei del #12b, 3r cop)."""

    PREFIX = 'T8T3'

    def test_els_poms_d_una_peca_no_protegeixen_els_de_l_altra(self):
        """EL VERMELL DE LA PODA PER PECES.

        La tramesa anomena LES DUES peces: `cintura` a la mare i `pit` al short. La mare, doncs,
        SÍ que és candidata — i la seva fila rància del POM `pit`, que aquest document ja no li
        atribueix, ha de sortir a la llista.

        Amb un `confirmed_pom_ids` PLA (el codi d'abans) el `pit` hi era —el confirma el short— i
        la fila rància de la MARE quedava protegida per una confirmació que parlava d'una altra
        peça: sobrevivia en silenci a un document que ja no la diu.
        """
        rancia = self._mesura(self.pit, garment=MARE, valor=55.0)

        s = self._sessio(garment=MARE, poms=[self.pit, self.cintura])
        s.poms_extrets = [
            {'codi_fitxa': 'WA', 'descripcio': 'x', 'pom_master_id': self.cintura.id,
             'actiu': True, 'ordre': 0, 'garment': MARE},
            {'codi_fitxa': 'M1', 'descripcio': 'x', 'pom_master_id': self.pit.id,
             'actiu': True, 'ordre': 1, 'garment': SEGONA},
        ]
        s.save()

        res = self._confirmar(s)
        self.assertEqual(res.status_code, 409, res.data)
        self.assertEqual(res.data['tipus'], 'poms_no_mencionats')
        # La fila rància de la MARE hi és, i la resposta diu de quina peça és.
        orfes = {(o['pom_id'], o['garment']) for o in res.data['poms']}
        self.assertIn((self.pit.id, MARE), orfes)

        rancia.refresh_from_db()
        self.assertTrue(rancia.is_active, 'ha podat sense preguntar')

    def test_una_peca_que_l_import_no_anomena_no_es_candidata(self):
        """L'altra meitat de la llei: qui no surt a la llista cau NOMÉS si la seva peça és una
        de les que la llista anomena."""
        ModelGarment.objects.create(model=self.model, codi='03', nom='Tercera', ordre=2)
        forana = self._mesura(self.cintura, garment='03', valor=42.0)

        s = self._sessio(garment=MARE, poms=[self.pit])
        s.poms_extrets = [{'codi_fitxa': 'A', 'descripcio': 'x', 'pom_master_id': self.pit.id,
                           'actiu': True, 'ordre': 0, 'garment': SEGONA}]
        s.save()
        self._confirmar(s, poda_choice='desactivar')

        forana.refresh_from_db()
        self.assertTrue(forana.is_active, 'ha podat una peça que aquest import no anomena')
        self.assertEqual(forana.base_value_cm, 42.0)


class ImportSensePecaALaFilaTest(_BaseImportPerPrendaTest):
    """EL CONTROL DE NO-REGRESSIÓ — el 100% del corpus viu.

    Cap fila declara `garment`: totes han d'anar a la peça de la SESSIÓ, exactament com abans
    d'aquesta peça. És la meitat de la parella que fa creïble tota la resta.
    """

    PREFIX = 'T8T4'

    def test_sense_declarar_res_totes_les_files_van_a_la_peca_de_la_sessio(self):
        res = self._confirmar(self._sessio(garment=SEGONA))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(self._files(SEGONA).count(), 1)
        self.assertEqual(self._files(MARE).count(), 0)

    def test_a_la_mare_tambe(self):
        res = self._confirmar(self._sessio(garment=MARE))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(self._files(MARE).count(), 1)
        self.assertEqual(self._files(SEGONA).count(), 0)


class LaPropostaDeSeccioTest(_BaseImportPerPrendaTest):
    """F2 · el rètol del document proposa la peça — i PROPOSA, no decideix."""

    PREFIX = 'T8T5'

    def _files(self, *seccions):
        return [{'ordre': i, 'seccio': s, 'codi_fitxa': f'X{i}'}
                for i, s in enumerate(seccions)]

    def test_el_retol_del_document_troba_la_peca_pel_nom(self):
        """El cas Brumà: la secció «SHORT» i la peça batejada «Short»."""
        self.peca.nom = 'Short'
        self.peca.save(update_fields=['nom'])
        poms = self._files(None, 'SHORT', 'SHORT')

        traca = _proposta_de_peca(self.model, poms)

        self.assertNotIn('garment_proposat', poms[0], 'una fila sense secció no es proposa')
        self.assertEqual(poms[1]['garment_proposat'], SEGONA)
        self.assertEqual(poms[2]['garment_proposat'], SEGONA)
        self.assertEqual(traca['n_proposades'], 2)
        self.assertEqual(traca['seccions_sense_peca'], [])

    def test_tambe_pel_codi_i_amb_el_retol_titulat(self):
        self.peca.nom = 'Short'
        self.peca.save(update_fields=['nom'])
        poms = self._files('02', 'Short measurements')
        _proposta_de_peca(self.model, poms)
        self.assertEqual(poms[0]['garment_proposat'], SEGONA)
        self.assertEqual(poms[1]['garment_proposat'], SEGONA)

    def test_una_seccio_sense_peca_es_DIU_i_no_aterra_enlloc(self):
        """L'absència que s'ha de dir: un document amb secció SHORT sobre un model que no en
        té peça vol dir que falta crear-la. El silenci hi deixaria set files a la mare."""
        poms = self._files('SHORT', 'CAPUTXA')
        traca = _proposta_de_peca(self.model, poms)

        self.assertEqual(traca['n_proposades'], 0)
        self.assertEqual(sorted(traca['seccions_sense_peca']), ['CAPUTXA', 'SHORT'])
        for p in poms:
            self.assertNotIn('garment_proposat', p)

    def test_la_proposta_NO_es_la_decisio(self):
        """`garment_proposat` és una clau separada de `garment`: mentre ningú la confirmi, la
        fila segueix sense eix propi i el confirm hi escriu el de la sessió."""
        self.peca.nom = 'Short'
        self.peca.save(update_fields=['nom'])
        poms = self._files('SHORT')
        _proposta_de_peca(self.model, poms)

        self.assertEqual(poms[0]['garment_proposat'], SEGONA)
        self.assertNotIn('garment', poms[0])
        self.assertEqual(_garment_de(poms[0], MARE), MARE)
