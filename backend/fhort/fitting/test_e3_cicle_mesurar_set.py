"""E3b · EL CICLE SENCER DEL SET — crear presa → mesurar → segellar → llegir l'acta → crear-ne
una de NOVA.

Substrat: `docs/diagnosis/DIAGNOSI_QA_2054_REGRESSIO_O_FORAT.md` + les decisions d'Agus d'E3.

🚨 EL COR ÉS `test_el_cicle_sencer_i_els_seus_numeros`. La QA de les 20:54 va segellar la presa i,
a partir d'allà, TOT el que la pantalla oferia era mentida —perquè ningú havia recorregut mai el
cicle passat el segell. Aquest test el recorre sencer i deixa els números escrits a cada baula,
que és l'única manera que la baula següent no torni a néixer sense provar.

La segona meitat és `test_mesurar_set_sobre_una_ACTA_no_la_reobre`: la decisió d'Agus és que sobre
una presa tancada se'n crea una de NOVA, i l'acta es queda. Un `sessioDeFitting` que trobés la
tancada i s'hi enganxés seria la reobertura silenciosa d'una acta.

⚠️ Això prova el CAMÍ DE SERVEIS que el botó recorre (sessió → peça → presa → tancar → segellar →
llegir), no el JSX. La part de pantalla la cobreix `ops/qa/e3_gest_no_navega.mjs` i el
`npm run build`.
"""
import datetime

from fhort.fitting import services
from fhort.fitting.models import FittingSession, GradedSpec, PieceFitting, PieceFittingLine

from .test_e1_presa_escalat import BASE, MARE, SEGONA, TEORICS, PresaEscalatBase


class CicleMesurarSetTest(PresaEscalatBase):

    def setUp(self):
        super().setUp()
        # ⚠️ AQUEST FIXTURE NO POT FABRICAR LES LÍNIES A MÀ com fa el d'E1: el que aquí es prova
        # és el camí REAL de «Mesurar set», i la peça neix de clonar els `GradedSpec` actius
        # (`create_piece_fitting`). Sense specs, la peça neix amb 0 línies i tota la presa
        # contesta 404 `sense_linia` — que és exactament el que aquest banc va dir la primera
        # vegada que va córrer, i el motiu pel qual la sembra ha de ser explícita.
        for garment, base_val in ((MARE, TEORICS[BASE]), (SEGONA, 30.0)):
            for sl, v in TEORICS.items():
                GradedSpec.objects.create(
                    grading_version=self.gv, pom=self.pom, size_label=sl, garment=garment,
                    graded_value_cm=(v if garment == MARE else base_val + (v - TEORICS[BASE])),
                    grading_type_applied='LINEAR', is_active=True)

    def _obre_set(self, data):
        """El que fa «Mesurar set»: sessió VIVA + peça. Bessó de `sessioDeFitting` +
        `resolvePieceFitting` del front, pel mateix ordre i amb els mateixos serveis."""
        viva = (FittingSession.objects
                .filter(model=self.model, estat__in=services.SESSIONS_VIVES)
                .order_by('-data', '-id').first())
        if viva is None:
            viva = FittingSession.objects.create(
                model=self.model, fase='Dev', data=data, estat='Oberta')
        pf = PieceFitting.objects.filter(session=viva, model=self.model).first()
        if pf is None:
            pf, _ = services.create_piece_fitting(viva.id, self.model.id,
                                                  created_by_id=self.profile.id)
        return viva, pf

    def _preses_visibles(self):
        d = self._get().data
        return d, sum(1 for c in d['preses'].values() if c['real'] is not None)

    def test_el_cicle_sencer_i_els_seus_numeros(self):
        """🚨 EL COR. Cada baula amb el seu número, i el segell no deixa la pantalla cega."""
        # ── 0 · VERMELL DE PARTIDA: no hi ha res, i el POST ho diu amb 409.
        d, n = self._preses_visibles()
        self.assertEqual((d['presa_oberta'], d['presa_tancada'], n), (False, False, 0))
        self.assertEqual(self._post(pom_id=self.pom.id, talla='L', valor=53.4).status_code, 409)

        # ── 1 · «MESURAR SET»: crea sessió + peça. Les línies neixen de l'spec, no de zero.
        sessio, pf = self._obre_set(datetime.date(2026, 8, 17))
        n_linies = PieceFittingLine.objects.filter(piece_fitting=pf).count()
        self.assertGreater(n_linies, 0)
        d, n = self._preses_visibles()
        self.assertEqual((d['presa_oberta'], d['presa_tancada']), (True, False))
        # 🔑 EL NÚMERO QUE HO DIU TOT: la presa acaba de néixer i NO té cap mesura. Si en tingués,
        # seria la sembra fent-se passar per feina feta (la llei d'E2/B1: mana `presa_at`).
        self.assertEqual(n, 0)
        self.assertEqual(d['resum']['n_linies'], n_linies)

        # ── 2 · MESURAR: dues talles, per la porta de la presa.
        for talla, valor in (('L', 53.4), ('S', 47.5)):
            r = self._post(pom_id=self.pom.id, talla=talla, valor=valor)
            self.assertEqual(r.status_code, 200)
        d, n = self._preses_visibles()
        self.assertEqual(n, 2)
        self.assertEqual(d['preses'][self._clau(MARE, 'L')]['desviacio'], 1.4)
        self.assertEqual(sorted(d['resum']['talles_amb_presa']), ['L', 'S'])

        # ── 3 · DECIDIR a la base i TANCAR la peça (el gest del sub-tab «Decisió»).
        linia_base = PieceFittingLine.objects.get(piece_fitting=pf, garment=MARE,
                                                  size_label=BASE)
        PieceFittingLine.objects.filter(pk=linia_base.pk).update(
            valor_real=51.0, decisio='ACCEPTED',
            presa_at=datetime.datetime(2026, 8, 17, 10, 0, tzinfo=datetime.timezone.utc))
        services.close_piece_fitting(pf.id, user_profile_id=self.profile.id)

        # ── 4 · SEGELLAR. AQUÍ ÉS ON LA QA DE LES 20:54 ES VA QUEDAR CEGA.
        services.seal_session(sessio.id)
        sessio.refresh_from_db()
        self.assertIn(sessio.estat, services.SEALED_SESSION_ESTATS)

        d, n = self._preses_visibles()
        # L'acta TÉ NOM…
        self.assertEqual((d['presa_oberta'], d['presa_tancada']), (False, True))
        # …i DADES: abans d'E3a això era `session: null` i `preses: {}`.
        self.assertEqual(d['session']['id'], sessio.id)
        self.assertEqual(d['session']['estat'], sessio.estat)
        self.assertEqual(d['session']['data'], '2026-08-17')
        self.assertEqual(n, 3)                       # les 2 preses + la base decidida
        self.assertEqual(d['resum']['decidides_base'], 1)
        # …i segueix sent una acta: cap escriptura hi entra.
        r = self._post(pom_id=self.pom.id, talla='XL', valor=55.0)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.data['codi'], 'sense_presa_oberta')

        # ── 5 · «MESURAR SET» UN ALTRE COP → una presa NOVA, i l'acta es queda.
        nova, pf2 = self._obre_set(datetime.date(2026, 8, 18))
        self.assertNotEqual(nova.id, sessio.id)
        d, n = self._preses_visibles()
        self.assertEqual((d['presa_oberta'], d['presa_tancada']), (True, False))
        self.assertEqual(d['session']['id'], nova.id)
        self.assertEqual(n, 0)                       # la presa nova neix buida…
        # …i la vella segueix sencera a l'històric, amb els seus números intactes.
        self.assertEqual(FittingSession.objects.get(pk=sessio.id).estat, sessio.estat)
        self.assertEqual(
            float(PieceFittingLine.objects.get(piece_fitting=pf, garment=MARE,
                                               size_label='L').valor_real), 53.4)
        self.assertEqual(PieceFitting.objects.filter(model=self.model).count(), 2)
        self.assertNotEqual(pf2.id, pf.id)

        # ── 6 · I S'HI POT TORNAR A MESURAR: el cicle no és d'un sol ús.
        self.assertEqual(self._post(pom_id=self.pom.id, talla='L', valor=53.9).status_code, 200)
        _, n = self._preses_visibles()
        self.assertEqual(n, 1)

    def test_mesurar_set_sobre_una_ACTA_no_la_reobre(self):
        """La tancada NO és viva, i per això `sessioDeFitting` no se l'enganxa mai."""
        sessio, _ = self._obre_set(datetime.date(2026, 8, 17))
        services.seal_session(sessio.id)
        nova, _ = self._obre_set(datetime.date(2026, 8, 18))
        self.assertNotEqual(nova.id, sessio.id)
        self.assertIn(FittingSession.objects.get(pk=sessio.id).estat,
                      services.SEALED_SESSION_ESTATS)
        self.assertEqual(nova.estat, 'Oberta')

    def test_mesurar_set_amb_una_presa_VIVA_no_en_crea_cap_de_segona(self):
        """«entra a la viva si n'hi ha» — i idempotent: prémer dos cops no duplica res."""
        sessio, pf = self._obre_set(datetime.date(2026, 8, 17))
        altra, pf2 = self._obre_set(datetime.date(2026, 8, 18))
        self.assertEqual((altra.id, pf2.id), (sessio.id, pf.id))
        self.assertEqual(FittingSession.objects.filter(model=self.model).count(), 1)
        self.assertEqual(PieceFitting.objects.filter(model=self.model).count(), 1)

    def test_tancar_la_peça_CONSOLIDA_la_base_abans_del_segell(self):
        """El que fa que el segon cicle vulgui dir alguna cosa: la presa acceptada a la base passa
        a `BaseMeasurement`, i per tant la presa següent ja no mesura contra l'origen.

        ⚠️ LÍMIT MESURAT D'AQUEST FIXTURE, escrit perquè ningú no el confongui amb una troballa:
        `close_piece_fitting` retorna aquí `{'changed': 1, 'base_changed': True,
        'new_version': None}` — consolida la base però NO regenera els specs, perquè aquest banc
        sembra els `GradedSpec` a mà i no té la cadena de re-derivació muntada. En producció els
        specs es regeneren i el teòric de la presa següent ÉS la consolidació de l'anterior
        (llei de Q8). Assertar-ho aquí seria assertar el motor de grading amb un fixture que no
        el porta — i el motor és zona intocable. El que aquí es fixa és la baula d'E3: la
        consolidació passa ABANS del segell, i el segell no se l'endú.
        """
        sessio, pf = self._obre_set(datetime.date(2026, 8, 17))
        self.assertEqual(float(PieceFittingLine.objects.get(
            piece_fitting=pf, garment=MARE, size_label=BASE).valor_teoric), TEORICS[BASE])

        PieceFittingLine.objects.filter(piece_fitting=pf, garment=MARE, size_label=BASE).update(
            valor_real=51.0, decisio='ACCEPTED',
            presa_at=datetime.datetime(2026, 8, 17, 10, 0, tzinfo=datetime.timezone.utc))
        out = services.close_piece_fitting(pf.id, user_profile_id=self.profile.id)
        self.assertEqual((out['changed'], out['base_changed']), (1, True))

        # LA BASE DE LA MARE S'HA MOGUT; la de la 02, que ningú no va decidir, NO.
        self.assertEqual(dict(self._bases()).get(MARE), 51.0)
        self.assertEqual(dict(self._bases()).get(SEGONA), 30.0)

        # I el segell no desfà res del que la consolidació acaba d'escriure.
        services.seal_session(sessio.id)
        self.assertEqual(dict(self._bases()).get(MARE), 51.0)
        self.assertEqual(self._get().data['presa_tancada'], True)

    def test_la_segona_prenda_no_es_perd_pel_cami(self):
        """El 1379 té DUES prendes. Tot el cicle ha de continuar servint-les totes dues —és la
        FAMÍLIA DE TRES rondant (v. anotació 🚩 de l'acta: `PieceFitting.garment=None`)."""
        sessio, _ = self._obre_set(datetime.date(2026, 8, 17))
        self.assertEqual(self._post(pom_id=self.pom.id, talla='S', valor=27.5,
                                    garment=SEGONA).status_code, 200)
        services.seal_session(sessio.id)
        d = self._get().data
        self.assertEqual(d['presa_tancada'], True)
        self.assertEqual(d['preses'][self._clau(SEGONA, 'S')]['real'], 27.5)
        self.assertIsNone(d['preses'][self._clau(MARE, 'S')]['real'])
