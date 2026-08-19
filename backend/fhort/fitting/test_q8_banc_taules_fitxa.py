"""Q8/QA — EL BANC MULTI-PEÇA DE LES TAULES DE LA FITXA, i el bolcat dels seus payloads.

🚨 PER QUÈ EXISTEIX AQUEST FIXTURE. El 17/08 es va censar el corpus viu del tenant `fhort` i
**no hi ha cap model amb fitting TANCAT i multi-peça**:

    1379 BRW-FW26-0002 · garments ['', '02'] · pf=40 amb 90 línies … sessió 155 **Oberta**,
                         gate Pendent, 0 decisions   → i és de LECTURA (mai escriptura)
    1380 QA-F1-GARMENT  · garments ['', '02'] · **cap** PieceFitting
                                                    → i és d'escriptura de la sessió E2

O sigui que les tres taules de Q8 —que llegeixen l'ÚLTIMA SESSIÓ TANCADA— no es podien exercir
contra cap dada real sense trepitjar feina aliena. El banc és propi i sintètic, viu dins d'un
`TenantTestCase` i no toca cap fila de ningú.

I A MÉS BOLCA ELS PAYLOADS. Les tres taules es construeixen al FRONT (`utils/taulesQ8.js`), i un
test de Django no pot exercir JavaScript. El que sí que pot és garantir que el que el front rebrà
és exactament això: el fitxer que aquest test escriu és l'entrada del banc de node
(`ops/qa/q8_taules_fitxa.mjs`), que hi corre els constructors REALS. Sense el bolcat, el banc de
node hauria de portar un payload escrit a mà — i un payload escrit a mà prova que el codi fa el
que el payload diu, no que el servidor el serveixi així.

    cd backend && venv/bin/python manage.py test fhort.fitting.test_q8_banc_taules_fitxa --keepdb
"""
import contextlib
import datetime
import json
import os

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.accounts.models import UserProfile
from fhort.fitting.models import (FittingSession, GradedSpec, GradingVersion, PieceFitting,
                                  PieceFittingLine, SizeFitting)
from fhort.fitting.serializers import PieceFittingGridSerializer
from fhort.models_app.models import BaseMeasurement, Model, ModelGarment
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem

MARE = ''
SEGONA = '02'
TALLES = ['XS', 'S', 'M']
BASE = 'S'

#: Les mateixes comportes que `test_set2_t5c_linies_per_garment` alça, i pel mateix motiu: amb
#: elles vives cap fila pot portar `garment != ''` i el cas multi-peça no es pot ni construir.
#: `models_app_measurementchangelog` hi és perquè crear una `BaseMeasurement` dispara el signal
#: que hi escriu — sense ella el fixture peta amb `CheckViolation` d'una taula que no s'anomena.
TAULES_COMPORTA = ('models_app_basemeasurement', 'fitting_piecefittingline',
                   'fitting_gradedspec', 'models_app_measurementchangelog')

#: On es deixa el bolcat perquè el banc de node el trobi. Fora de git (`ops/qa/_out/`).
SORTIDA = os.path.join(os.path.dirname(__file__), '..', '..', '..',
                       'ops', 'qa', '_out', 'q8_payloads.json')


@contextlib.contextmanager
def comportes_garment_alcades(*taules):
    """Alça les comportes `*_garment_gate_set2` dins d'un savepoint que SEMPRE es desfà."""
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            for taula in taules:
                cur.execute(
                    f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                    f'DROP CONSTRAINT IF EXISTS "{taula}_garment_gate_set2"'
                )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class BancQ8Test(TenantTestCase):
    """El model de banc: DUES prendes, sessió TANCADA, i preses a totes les talles."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        self.ss = SizeSystem.objects.create(codi='SS_Q8', nom='SS Q8', base_unit='ALPHA')
        for i, et in enumerate(TALLES):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.model = Model.objects.create(
            codi_intern='QA-Q8-TAULES', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_system=self.ss,
            size_run_model='·'.join(TALLES), base_size_label=BASE,
        )
        # LA SEGONA PRENDA AMB NOM: és l'únic contracte que el diu, i sense ell el grup de taules
        # sortiria sense rètols (`grupsDelFull` degrada a taula plana, mai a taula absent).
        self.garment = ModelGarment.objects.create(
            model=self.model, codi=SEGONA, nom='Short', ordre=1)
        # Un POM amb nom LLARG a posta: és el que ha d'estirar l'amplada de la columna del POM
        # fins a fer-hi cabre el nom en dues línies (`ampladaPerTextos`).
        self.poms = [
            POMMaster.objects.create(codi_client='CH', nom_client='Chest width'),
            POMMaster.objects.create(codi_client='WA', nom_client='Waist width at natural line'),
            POMMaster.objects.create(codi_client='HL', nom_client='Hem length'),
        ]
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_q8', defaults={'email': 'qa@q8.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA Q8', 'rol_nom': 'QA'})
        self.sf = SizeFitting.objects.create(
            model=self.model, numero=1, codi='SF-Q8', tipus='SizeSet', estat='Pendent',
            creat_per=self.perfil)
        self.gv = GradingVersion.objects.create(
            size_fitting=self.sf, version_number=1, is_active=True, creat_per=self.perfil)
        # LA SESSIÓ ÉS TANCADA, que és tota la gràcia: les tres taules de Q8 llegeixen l'última
        # TANCADA i amb una d'oberta no s'insereixen (la porta del panell les deixa en fade).
        self.session = FittingSession.objects.create(
            model=self.model, fase='Dev', data=datetime.date(2026, 8, 16), estat='Tancada')
        self.pf = PieceFitting.objects.create(
            session=self.session, model=self.model, grading_version=self.gv, gate='OK')

    # ── El banc ─────────────────────────────────────────────────────────────────────────────

    def _sembra(self):
        """Dues prendes × tres POMs × tres talles, amb preses de tota mena.

        Els CASOS que el banc ha de contenir, i cadascun prova una regla distinta de l'espec:
          · presa que S'APARTA de la teòrica  → Actual en vermell negreta i Dif amb signe
          · presa que COINCIDEIX              → Actual en negre i Dif a zero, també en negre
          · línia INTACTA (real == teòric i sense decisió ni nota) → Actual BUIT, mai «mesurat»
          · REJECTED                          → veredicte imprès, i el valor final segueix el teòric
          · nota sense desviació              → la nota SOLA ja és contingut
        """
        base_per = {(MARE, 'CH'): 50.0, (MARE, 'WA'): 40.0, (MARE, 'HL'): 60.0,
                    (SEGONA, 'CH'): 30.0, (SEGONA, 'WA'): 26.0, (SEGONA, 'HL'): 20.0}
        for ordre, (garment, pom) in enumerate(
                [(g, p) for g in (MARE, SEGONA) for p in self.poms]):
            valor = base_per[(garment, pom.codi_client)]
            BaseMeasurement.objects.create(
                model=self.model, pom=pom, base_value_cm=valor, ordre=ordre, garment=garment)
            for i, talla in enumerate(TALLES):
                teoric = valor + (i - TALLES.index(BASE)) * 2
                GradedSpec.objects.create(
                    grading_version=self.gv, pom=pom, size_label=talla,
                    graded_value_cm=teoric, garment=garment)
                # Els casos, repartits per POM perquè cada fila del full digui una cosa distinta.
                extra = {'valor_real': teoric, 'decisio': '', 'nota': ''}
                if pom.codi_client == 'CH':
                    extra = {'valor_real': teoric + 1.5, 'decisio': 'ADJUSTED',
                             'nota': 'obrir 1,5 al pit' if talla == BASE else ''}
                elif pom.codi_client == 'WA' and talla == BASE:
                    extra = {'valor_real': teoric, 'decisio': 'ACCEPTED', 'nota': 'queda bé'}
                elif pom.codi_client == 'HL' and talla == BASE:
                    extra = {'valor_real': teoric - 3, 'decisio': 'REJECTED', 'nota': ''}
                PieceFittingLine.objects.create(
                    piece_fitting=self.pf, pom=pom, size_label=talla,
                    valor_teoric=teoric, garment=garment, capa='', instancia='', **extra)

    # ── Les proves ──────────────────────────────────────────────────────────────────────────

    def test_el_banc_te_les_dues_prendes_a_totes_les_superficies(self):
        """Sense això, tota la resta de Q8 seria verd per absència: un sol grup sempre casa."""
        with comportes_garment_alcades(*TAULES_COMPORTA):
            self._sembra()
            grid = PieceFittingGridSerializer(self.pf).data
            garments = {l['garment'] for l in grid['lines']}
            self.assertEqual(garments, {MARE, SEGONA})
            self.assertEqual(len(grid['lines']), 2 * len(self.poms) * len(TALLES))
            self.assertEqual(grid['model']['base_size_label'], BASE)

    def test_una_linia_INTACTA_no_pot_semblar_una_presa(self):
        """El vermell que aquest banc guarda: `valor_real` neix copiat del teòric.

        La línia de `HL` a XS no l'ha tocat ningú —ni decisió, ni nota, ni número mogut—. Si el
        payload la servís amb `valor_real` i el front el llegís a pèl, el full diria que la peça
        física s'ha mesurat i que coincideix EXACTAMENT. Aquí es certifica l'estat del payload;
        que el front no l'hi cregui és el que prova `taulesQ8.test.js`.
        """
        with comportes_garment_alcades(*TAULES_COMPORTA):
            self._sembra()
            grid = PieceFittingGridSerializer(self.pf).data
            intacta = next(l for l in grid['lines']
                           if l['codi'] == 'HL' and l['size_label'] == 'XS'
                           and l['garment'] == MARE)
            self.assertEqual(float(intacta['valor_real']), float(intacta['valor_teoric']))
            self.assertEqual((intacta['decisio'], intacta['nota']), ('', ''))

    def test_els_tres_veredictes_hi_son_i_la_nota_viatja(self):
        with comportes_garment_alcades(*TAULES_COMPORTA):
            self._sembra()
            grid = PieceFittingGridSerializer(self.pf).data
            base = [l for l in grid['lines'] if l['size_label'] == BASE and l['garment'] == MARE]
            self.assertEqual({l['decisio'] for l in base}, {'ADJUSTED', 'ACCEPTED', 'REJECTED'})
            self.assertEqual({l['nota'] for l in base}, {'obrir 1,5 al pit', 'queda bé', ''})

    def test_bolca_els_payloads_per_al_banc_de_node(self):
        """El pont cap a `ops/qa/q8_taules_fitxa.mjs`, que hi corre els constructors REALS."""
        with comportes_garment_alcades(*TAULES_COMPORTA):
            self._sembra()
            grid = PieceFittingGridSerializer(self.pf).data
            from fhort.models_app.services_garment import peces_del_model
            payload = {
                'model': {'id': self.model.id, 'codi_intern': self.model.codi_intern,
                          'base_size_label': BASE, 'size_run_model': '·'.join(TALLES)},
                'grid': json.loads(json.dumps(grid, default=str)),
                'peces': json.loads(json.dumps(peces_del_model(self.model), default=str)),
            }
            os.makedirs(os.path.dirname(os.path.abspath(SORTIDA)), exist_ok=True)
            with open(os.path.abspath(SORTIDA), 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=1)
            self.assertTrue(os.path.exists(os.path.abspath(SORTIDA)))
