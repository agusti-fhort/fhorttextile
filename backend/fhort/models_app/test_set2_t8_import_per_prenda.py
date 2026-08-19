"""SET-2/T8 — L'IMPORT PER PRENDA: el pipeline guanya l'eix (2026-08-12).

Decisió Agus (Patró C): **un import = una prenda**, i s'inicia DES DE LA PEÇA. El garment
no es pregunta mai: viu a `ImportSession` des de la iniciació i el confirm hi escriu TOTES
les files.

Els vermells que aquest fitxer vigila són tots de la mateixa família —**danys que no
criden**— i n'hi ha de dos gèneres:

  1 · L'ESCRIPTURA QUE CAU ON NO TOCA. Fins avui `import_session_confirmar_view` declarava
      `garment=''` com a LITERAL: un import obert des del contenidor de la 02 hauria escrit
      les seves files sobre les de la mare, en silenci i amb la fitxa aparentment bé.

  2 · LES TRES PODES DE CONTEXT. El confirm no passa per `_poda_mesures` —té poda pròpia—,
      o sigui que la llei del #12b s'hi ha de tornar a escriure sencera: **una llista de
      files no és una ordre d'esborrar la feina d'una altra prenda**. Són tres consultes,
      no una: els POMs no mencionats, les files sense valor i el pre-flight de les MANUAL.
      Sense l'abast, importar a la Llaçada proposava podar el Pantaló sencer.

  3 · I EL GUARD DE LA BASE. Valida contra la talla base EFECTIVA de la peça
      (`services_garment.valor_efectiu`, el punt únic): amb la de la mare, una prenda amb
      base pròpia veuria rebutjada una fitxa bona.

El CONTROL és a `ImportALaMareTest`: sense garment al context, el comportament ha de ser el
d'abans d'aquest tram, i és la meitat de la parella que fa creïble la resta.
"""
from django.test import override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.models_app.extraction_views import (
    _efectiu, _nom_de_la_peca, _peca_de, import_session_confirmar_view,
    import_session_cribratge_view)
from fhort.models_app.models import (BaseMeasurement, ImportSession, MeasurementChangeLog,
                                     ModelGarment, ModelGradingRule)
from fhort.models_app.tests_sembra_grading import _BaseSembraTest

MARE = ''
SEGONA = '02'


class _BaseImportPerPrendaTest(_BaseSembraTest):
    """Un model amb DUES prendes, i una sessió d'import muntada a mà.

    La sessió es construeix amb l'estat que els passos 1-4 hi haurien deixat (aparellament
    de talles, POMs confirmats i valors), perquè el que es prova és el pas 5: on aterren
    les files. Els passos anteriors tenen les seves pròpies portes.
    """

    def setUp(self):
        super().setUp()
        self.ss = self._size_system('T8SYS', talles=('S', 'M', 'L'))
        self.model = self._model(size_system=self.ss, base_size_label='M',
                                 size_run_model='S·M·L')
        # La 02 NEIX SENSE OVERRIDES: NULL vol dir «hereta», que és el cas normal i el que
        # fa que aquests tests parlin de l'eix i no d'una configuració exòtica.
        self.peca = ModelGarment.objects.create(model=self.model, codi=SEGONA,
                                                nom='Llaçada', ordre=1)
        self.pit = self._pom('CH')
        self.cintura = self._pom('WA')

    # ── bastida ───────────────────────────────────────────────────────────────
    def _mesura(self, pom, garment=MARE, valor=100.0, origen='MANUAL', activa=True):
        return BaseMeasurement.objects.create(
            model=self.model, pom=pom, base_value_cm=valor, origen=origen,
            is_active=activa, ordre=1, nom_fitxa='PREVI', garment=garment)

    def _sessio(self, garment=MARE, poms=None, valors=None, run_doc=('S', 'M', 'L'), **extra):
        """La sessió tal com el pas 4 la deixa. `valors` = {pom: {talla: cm}}.

        `run_doc` són les columnes que el DOCUMENT porta, i ha de coincidir amb les
        etiquetes de `valors`: una taula amb columnes sense valor és una fitxa incompleta i
        té el seu propi 422 (llei 2026-07-08, bug 166), que no és el que aquí es prova.
        """
        poms = poms if poms is not None else [self.pit]
        valors = valors if valors is not None else {
            p: {'S': 98.0, 'M': 100.0, 'L': 102.0} for p in poms}
        mesures = [{'pom_master_id': p.id, 'talla_label': et, 'valor': v}
                   for p, files in valors.items() for et, v in files.items()]
        resultat = {'mesures': mesures,
                    'extraccio': {'sizes': list(run_doc), 'base_size': 'M'}}
        resultat.update(extra.pop('resultat', {}))
        return ImportSession.objects.create(
            estat='MESURES_OK', model=self.model, garment=garment,
            poms_extrets=[{'codi_fitxa': p.codi_client, 'descripcio': p.nom_client,
                           'pom_master_id': p.id, 'actiu': True} for p in poms],
            run_conciliat={'talla_mapping': [{'document': et, 'model': et}
                                             for et in run_doc]},
            resultat=resultat, **extra)

    def _confirmar(self, session, **body):
        """El pas 5. `no_container` per defecte: la tria del contenidor de client és una
        altra llei (D1) i té les seves proves; aquí no ha de decidir res."""
        body.setdefault('container_choice', 'no_container')
        req = APIRequestFactory().post(
            f'/api/v1/import-sessions/{session.token}/confirmar/', body, format='json')
        force_authenticate(req, user=self.user)
        return import_session_confirmar_view(req, session.token)

    def _files(self, garment):
        return BaseMeasurement.objects.filter(model=self.model, garment=garment)


class ImportALaPrendaTest(_BaseImportPerPrendaTest):
    """EL VERMELL PRINCIPAL: importar a la 02 escriu a la 02, i la mare no es mou."""

    PREFIX = 'T8A'

    def test_les_files_neixen_amb_la_prenda_i_la_mare_queda_intacta(self):
        """El mateix POM, viu a totes dues peces. Cap de les dues és l'altra."""
        previa = self._mesura(self.pit, garment=MARE, valor=77.0)

        res = self._confirmar(self._sessio(garment=SEGONA))
        self.assertEqual(res.status_code, 201, res.data)

        nova = self._files(SEGONA).get(pom=self.pit)
        self.assertEqual(nova.base_value_cm, 100.0)
        self.assertEqual(nova.origen, 'IMPORTED')

        # LA MARE, BYTE A BYTE: valor, origen i estat. Cap dels tres l'ha tocat l'import.
        previa.refresh_from_db()
        self.assertEqual(previa.base_value_cm, 77.0)
        self.assertEqual(previa.origen, 'MANUAL')
        self.assertTrue(previa.is_active)

    def test_el_resum_diu_de_quina_prenda_parla(self):
        res = self._confirmar(self._sessio(garment=SEGONA))
        self.assertEqual(res.data['garment'], SEGONA)
        self.assertEqual(res.data['garment_nom'], 'Llaçada')

    def test_les_regles_residents_neixen_amb_l_eix_de_la_prenda(self):
        """La graduació derivada de la fitxa és de la peça que s'ha importat."""
        self._confirmar(self._sessio(garment=SEGONA))
        residents = ModelGradingRule.objects.filter(model=self.model)
        self.assertTrue(residents.exists())
        self.assertEqual({r.garment for r in residents}, {SEGONA})

    def test_el_joc_de_regles_de_la_mare_no_es_mou(self):
        """`grading_rule_set` és un camp HERETABLE: el que decideix un import a la 02
        aterra a l'override de la peça, mai al model."""
        self._confirmar(self._sessio(garment=SEGONA))
        self.model.refresh_from_db()
        self.peca.refresh_from_db()
        self.assertIsNone(self.model.grading_rule_set_id)
        self.assertIsNone(self.peca.grading_rule_set_id)   # 'no_container' → sobirania


class PodesDelConfirmTest(_BaseImportPerPrendaTest):
    """LA TERCERA PORTA DE LA LLEI DEL #12b: el confirm poda pel seu compte.

    Les tres consultes que miren «què hi ha ja al model» han de mirar «què hi ha ja en
    AQUESTA prenda». Cadascuna té el seu vermell i cap d'elles crida en fallar.
    """

    PREFIX = 'T8B'

    def test_els_POMs_vius_d_una_altra_prenda_no_es_proposen_per_podar(self):
        """Una mesura viva de la MARE que el document no menciona no és candidata quan
        s'importa a la 02: aquell document no parla d'ella. Sense l'abast, el confirm
        hauria sortit amb un 409 proposant desactivar-la."""
        self._mesura(self.cintura, garment=MARE, valor=70.0)

        res = self._confirmar(self._sessio(garment=SEGONA, poms=[self.pit]))

        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(BaseMeasurement.objects.get(
            model=self.model, pom=self.cintura, garment=MARE).is_active)

    def test_els_POMs_vius_de_la_MATEIXA_prenda_si_es_proposen(self):
        """L'altra meitat: acotar no és emmudir. Dins de la prenda, la llei del soroll
        segueix sent la de sempre."""
        self._mesura(self.cintura, garment=SEGONA, valor=70.0)

        res = self._confirmar(self._sessio(garment=SEGONA, poms=[self.pit]))

        self.assertEqual(res.status_code, 409, res.data)
        self.assertEqual(res.data['tipus'], 'poms_no_mencionats')
        self.assertEqual([p['pom_id'] for p in res.data['poms']], [self.cintura.id])

    def test_les_files_sense_valor_d_una_altra_prenda_no_s_esborren(self):
        """La neteja de bastida de plantilla és un DELETE DUR: si no s'acota, un import a
        la mare esborra la plantilla que algú acabava de materialitzar a la 02."""
        buida = BaseMeasurement.objects.create(
            model=self.model, pom=self.cintura, base_value_cm=None,
            origen='TEMPLATE', garment=SEGONA, ordre=1)

        res = self._confirmar(self._sessio(garment=MARE, poms=[self.pit]))

        self.assertEqual(res.status_code, 201, res.data)
        self.assertTrue(BaseMeasurement.objects.filter(pk=buida.pk).exists())

    def test_les_MANUAL_d_una_altra_prenda_no_disparen_el_preflight(self):
        """El patrimoni escrit a mà al Pantaló no el trepitja un document de la Llaçada, i
        per tant tampoc n'ha de sortir una pregunta sobre files que ningú no tocarà."""
        self._mesura(self.pit, garment=SEGONA, valor=55.0, origen='MANUAL')

        res = self._confirmar(self._sessio(garment=MARE, poms=[self.pit]))

        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(BaseMeasurement.objects.get(
            model=self.model, pom=self.pit, garment=SEGONA).base_value_cm, 55.0)

    def test_la_poda_confirmada_registra_l_eix_al_log(self):
        """`MeasurementChangeLog` és APPEND-ONLY: una baixa mal atribuïda diu que s'ha
        esborrat una mesura d'una peça que segueix viva, i no es pot corregir després."""
        self._mesura(self.cintura, garment=SEGONA, valor=70.0)

        res = self._confirmar(self._sessio(garment=SEGONA, poms=[self.pit]),
                              poda_choice='desactivar')

        self.assertEqual(res.status_code, 201, res.data)
        # El log és APPEND-ONLY i la fila ja en tenia un del seu naixement: la baixa és
        # l'ÚLTIMA entrada, i és la que ha de portar l'eix.
        log = MeasurementChangeLog.objects.filter(
            model=self.model, pom=self.cintura).order_by('-id').first()
        self.assertIn('poda', log.motiu)
        self.assertEqual(log.garment, SEGONA)


class GuardDeLaBaseTest(_BaseImportPerPrendaTest):
    """(d) El guard de run-label: valida contra el RUN EFECTIU de la peça de destí."""

    PREFIX = 'T8C'

    def test_la_base_que_es_valida_es_la_de_la_prenda_no_la_de_la_mare(self):
        """La 02 declara base 'L'. Una fitxa amb valors a S i M —bona per a la mare— NO té
        la base d'aquesta prenda i ha de sortir amb el 422, dient 'L' i no 'M'."""
        self.peca.base_size_label = 'L'
        self.peca.save(update_fields=['base_size_label'])
        sessio = self._sessio(garment=SEGONA, run_doc=('S', 'M'),
                              valors={self.pit: {'S': 98.0, 'M': 100.0}})

        res = self._confirmar(sessio)

        self.assertEqual(res.status_code, 422, res.data)
        self.assertEqual(res.data['tipus'], 'base_size_absent')
        self.assertEqual(res.data['base_size'], 'L')

    def test_la_mateixa_fitxa_a_la_mare_passa(self):
        """El control del guard: amb la base de la mare ('M') aquella fitxa és correcta.
        Un guard que rebutgés totes dues no estaria acotant res, estaria trencat."""
        res = self._confirmar(self._sessio(
            garment=MARE, run_doc=('S', 'M'), valors={self.pit: {'S': 98.0, 'M': 100.0}}))
        self.assertEqual(res.status_code, 201, res.data)

    def test_valor_efectiu_es_el_punt_unic_i_hereta_quan_l_override_es_NULL(self):
        """La 02 sense override hereta: run i base són els del model. `is None` és el
        predicat, no la falsedat."""
        sessio = self._sessio(garment=SEGONA)
        self.assertEqual(_efectiu(sessio, 'base_size_label'), 'M')
        self.assertEqual(_efectiu(sessio, 'size_run_model'), 'S·M·L')
        self.assertEqual(_peca_de(sessio).codi, SEGONA)
        self.assertEqual(_nom_de_la_peca(sessio), 'Llaçada')


class ImportALaMareTest(_BaseImportPerPrendaTest):
    """EL CONTROL. Sense prenda al context, el comportament és el d'abans del tram."""

    PREFIX = 'T8D'

    def test_sense_garment_les_files_neixen_a_la_mare(self):
        res = self._confirmar(self._sessio(garment=MARE))
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(self._files(MARE).count(), 1)
        self.assertFalse(self._files(SEGONA).exists())

    def test_una_sessio_ANTERIOR_al_camp_escriu_a_la_mare(self):
        """El default de la columna és '': una sessió d'abans d'aquest tram —el 100% del
        corpus— no canvia de destí perquè hagi aparegut una columna nova."""
        sessio = self._sessio(garment=MARE)
        ImportSession.objects.filter(pk=sessio.pk).update(garment='')
        sessio.refresh_from_db()
        res = self._confirmar(sessio)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(self._files(MARE).get(pom=self.pit).origen, 'IMPORTED')

    def test_un_codi_de_prenda_desconegut_no_resol_a_cap_peca(self):
        """Una peça esborrada enmig d'un import no fa petar el pipeline: la sessió cau a la
        mare, que és el comportament d'abans del tram, en comptes de morir a mig camí."""
        sessio = self._sessio(garment=SEGONA)
        self.peca.delete()
        self.assertIsNone(_peca_de(sessio))
        self.assertEqual(_efectiu(sessio, 'base_size_label'), 'M')


class AvisMultiprendaTest(_BaseImportPerPrendaTest):
    """L'avís del document amb més d'un patró: INFORMA, i no barra mai."""

    PREFIX = 'T8E'

    def test_el_confirm_porta_l_avis_amb_el_NOM_de_la_peca(self):
        sessio = self._sessio(garment=SEGONA, resultat={'mes_duna_prenda': True})

        res = self._confirmar(sessio)

        # NO bloqueja: l'import s'ha fet i l'avís hi viatja al costat.
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['avis_multiprenda']['garment_nom'], 'Llaçada')
        self.assertEqual(self._files(SEGONA).count(), 1)

    def test_sense_senyal_no_hi_ha_avis(self):
        res = self._confirmar(self._sessio(garment=SEGONA))
        self.assertIsNone(res.data['avis_multiprenda'])


class IniciacioDeLaSessioTest(_BaseImportPerPrendaTest):
    """L'ÚNICA porta per on entra l'eix: la iniciació. Cap altra vista el pregunta."""

    PREFIX = 'T8F'

    @override_settings(ANTHROPIC_API_KEY='')
    def test_un_codi_de_prenda_que_no_es_del_model_es_400(self):
        """Escriure a la mare quan el client ha dit '99' seria exactament el dany que
        aquest tram tanca: val més un 400 que un silenci. Es valida ABANS de crear la
        sessió i abans de qualsevol crida pagada."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        req = APIRequestFactory().post('/api/v1/import-sessions/cribratge/', {
            'document': SimpleUploadedFile('fitxa.pdf', b'%PDF-1.4', 'application/pdf'),
            'model_id': self.model.id, 'garment': '99',
        }, format='multipart')
        force_authenticate(req, user=self.user)

        res = import_session_cribratge_view(req)

        self.assertEqual(res.status_code, 400, res.data)
        self.assertFalse(ImportSession.objects.filter(model=self.model).exists())
