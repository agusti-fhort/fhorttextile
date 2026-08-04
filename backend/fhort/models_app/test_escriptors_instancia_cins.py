"""FASE_3 — HARNESS D'ESCRIPTORS: els camins d'escriptura estampen els dos eixos.

Els harnesses de FASE_2 (`test_lectors_capa_onada1`, `test_lectors_instancia_cins`) proven
que els LECTORS no col·lapsen quan hi ha files germanes. Aquest prova la cara que faltava, i
que cap dels altres pot provar: que quan un camí d'escriptura CREA files, les crea dient de
quina matèria i de quina repetició parlen.

**El fet estructural que aquesta fase mata** (dossier §II.10): *«cap escriptor de tot el repo
passa mai `capa` a un lookup ni a un `defaults`»*. Amb la comporta tancada això no petava mai
—tot queia als defaults i tot era exterior—, però deixava dues bombes armades:

  1. tota clau de lookup que en deia MENYS que la unicitat real: el dia que la comporta
     caigui, un `update_or_create` sobre una família de dues germanes o bé n'agafa una a
     l'atzar o bé peta amb `MultipleObjectsReturned`;
  2. tota propagació que copia una fila sense copiar-ne els eixos: la còpia neix orfe i
     xoca amb la seva germana.

Els casos alcen LES DUES comportes de les taules que toquen, dins d'un savepoint que sempre
es desfà, i comproven que el camí real —el de producció, no una imitació— fa el que ha de fer
amb dues germanes vives.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import datetime

from django.db import connection
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import (BaseMeasurement, MeasurementChangeLog, Model,
                                     SizeCheck, SizeCheckLine)
from fhort.models_app.test_lectors_instancia_cins import comportes_alcades
from fhort.pom.models import POMMaster

EXTERIOR = 'exterior'
FOLRE = 'folre'
LEFT = 'left'


class EscriptorsInstanciaCinsTest(TenantTestCase):

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
        from django.contrib.auth import get_user_model

        from fhort.accounts.models import UserProfile
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-F3', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )
        self.user, _ = get_user_model().objects.get_or_create(
            username='qa_f3', defaults={'email': 'qa@f3.test'})
        self.perfil, _ = UserProfile.objects.get_or_create(
            user=self.user, defaults={'nom_complet': 'QA FASE_3', 'rol_nom': 'QA'})

    def _tres_germanes(self):
        """Exterior/'' · folre/'' · exterior/'left'. Valors inconfusibles entre si."""
        ext = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, nom_fitxa='A-EXT')
        fol = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=98.0, ordre=2,
            nom_fitxa='A-FOL', capa=FOLRE)
        esq = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=40.0, ordre=3,
            nom_fitxa='A-ESQ', instancia=LEFT)
        return ext, fol, esq

    # ── El signal F1: el log diu de quina mesura parla ───────────────────────────────

    def test_el_signal_estampa_els_dos_eixos_de_la_mesura(self):
        """L'ÚNIC escriptor automàtic del log. Fins a FASE_3 deixava les files als defaults i
        les tres germanes hi aterraven juntes; la taula és append-only, o sigui que una fila
        mal atribuïda no es podia corregir després."""
        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog'):
            ext, fol, esq = self._tres_germanes()

            logs = {(l.capa, l.instancia): l.valor_nou
                    for l in MeasurementChangeLog.objects.filter(model=self.model)}
            self.assertEqual(logs, {(EXTERIOR, ''): 100.0,
                                    (FOLRE, ''): 98.0,
                                    (EXTERIOR, LEFT): 40.0},
                             'cada alta ha de deixar rastre a la SEVA fila del log')

            # I la branca de canvi de valor, no només la d'alta.
            esq.base_value_cm = 41.0
            esq.save()
            darrer = (MeasurementChangeLog.objects
                      .filter(model=self.model).order_by('-id').first())
            self.assertEqual((darrer.capa, darrer.instancia, darrer.valor_nou),
                             (EXTERIOR, LEFT, 41.0))

    def test_el_signal_estampa_tambe_la_poda(self):
        """Una baixa mal atribuïda diu que s'ha esborrat una mesura que segueix viva."""
        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog'):
            _ext, _fol, esq = self._tres_germanes()
            esq.is_active = False
            esq._desactivat = True
            esq.save()

            poda = (MeasurementChangeLog.objects
                    .filter(model=self.model, motiu='desactivacio').first())
            self.assertIsNotNone(poda, 'la poda ha de deixar rastre')
            self.assertEqual((poda.capa, poda.instancia), (EXTERIOR, LEFT))

    # ── El pitjor cas del cens: la materialització de línies de check ────────────────

    def test_la_materialitzacio_dona_linia_a_TOTES_les_germanes(self):
        """`_materialize_lines` aparellava per `pom_id` pelat: la primera germana que rebia
        línia bloquejava totes les altres, i la resta quedaven com a files inertes a
        l'editor —es veuen, però no es poden anotar."""
        from fhort.models_app.services_size_check import _materialize_lines

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog',
                               'models_app_sizecheckline'):
            self._tres_germanes()
            check = SizeCheck.objects.create(model=self.model, talla_base_label='M')

            n = _materialize_lines(check, self.model)

            self.assertEqual(n, 3, 'una línia per germana, no una per POM')
            linies = {(l.capa, l.instancia): l.valor_teoric
                      for l in SizeCheckLine.objects.filter(size_check=check)}
            self.assertEqual(linies, {(EXTERIOR, ''): 100.0,
                                      (FOLRE, ''): 98.0,
                                      (EXTERIOR, LEFT): 40.0})

    def test_la_materialitzacio_es_idempotent_per_germana(self):
        """La cara B: completar un check ja materialitzat no ha de duplicar res. Si el
        `ja_hi_son` hagués crescut i l'`exclude` no (o al revés), això crearia tres línies
        més i xocaria amb la unicitat."""
        from fhort.models_app.services_size_check import _materialize_lines

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog',
                               'models_app_sizecheckline'):
            self._tres_germanes()
            check = SizeCheck.objects.create(model=self.model, talla_base_label='M')
            _materialize_lines(check, self.model)

            self.assertEqual(_materialize_lines(check, self.model), 0)
            self.assertEqual(SizeCheckLine.objects.filter(size_check=check).count(), 3)

    # ── L'accident desarmat: l'upsert de GradedSpec ─────────────────────────────────

    def test_l_upsert_de_spec_no_reescriu_la_germana(self):
        """El node que armava l'accident de C4. La unicitat és de cinc columnes i el lookup
        en deia tres: dos specs germans es fonien en un, i quin sobrevivia ho decidia l'ordre
        d'escriptura."""
        from fhort.fitting.models import GradedSpec, GradingVersion, SizeFitting
        from fhort.pom.services import _upsert_graded_spec

        # `numero=2`: el model ja neix amb el seu primer SizeFitting (signal).
        sf = SizeFitting.objects.create(model=self.model, numero=2, codi='TST-SF-F3',
                                        tipus='PROTO', creat_per=self.perfil)
        gv = GradingVersion.objects.create(size_fitting=sf, is_active=True,
                                           version_number=1, creat_per=self.perfil)

        with comportes_alcades('fitting_gradedspec'):
            for capa, instancia, valor in ((EXTERIOR, '', 100.0),
                                           (FOLRE, '', 98.0),
                                           (EXTERIOR, LEFT, 40.0)):
                _upsert_graded_spec(
                    grading_version_id=gv.pk, pom_id=self.pom.id, size_label='M',
                    graded_value_cm=valor, grading_type_applied='LINEAR',
                    increment_applied_cm=0.0, capa=capa, instancia=instancia)

            specs = {(s.capa, s.instancia): s.graded_value_cm
                     for s in GradedSpec.objects.filter(grading_version=gv)}
            self.assertEqual(specs, {(EXTERIOR, ''): 100.0,
                                     (FOLRE, ''): 98.0,
                                     (EXTERIOR, LEFT): 40.0})

            # Idempotència: el segon upsert de la mateixa clau ACTUALITZA, no duplica.
            _upsert_graded_spec(
                grading_version_id=gv.pk, pom_id=self.pom.id, size_label='M',
                graded_value_cm=41.0, grading_type_applied='LINEAR',
                increment_applied_cm=1.0, capa=EXTERIOR, instancia=LEFT)
            self.assertEqual(GradedSpec.objects.filter(grading_version=gv).count(), 3)
            self.assertEqual(
                GradedSpec.objects.get(grading_version=gv, capa=EXTERIOR,
                                       instancia=LEFT).graded_value_cm, 41.0)

    # ── La propagació: la línia de fitting clona l'spec ─────────────────────────────

    def test_la_linia_de_fitting_hereta_els_eixos_de_l_spec(self):
        """Clonar un `GradedSpec` a una `PieceFittingLine` copiant només pom/talla/valor
        generava línies indistingibles que xoquen amb la unicitat de la línia."""
        from fhort.fitting.models import (FittingSession, GradedSpec, GradingVersion,
                                          PieceFitting, PieceFittingLine, SizeFitting)

        sf = SizeFitting.objects.create(model=self.model, numero=2, codi='TST-SF-F3b',
                                        tipus='PROTO', creat_per=self.perfil)
        gv = GradingVersion.objects.create(size_fitting=sf, is_active=True,
                                           version_number=1, creat_per=self.perfil)
        sessio = FittingSession.objects.create(
            model=self.model, fase=self.model.fase_actual,
            data=datetime.date(2026, 8, 2))

        with comportes_alcades('fitting_gradedspec', 'fitting_piecefittingline'):
            for capa, instancia, valor in ((EXTERIOR, '', 100.0),
                                           (FOLRE, '', 98.0),
                                           (EXTERIOR, LEFT, 40.0)):
                GradedSpec.objects.create(
                    grading_version=gv, pom=self.pom, size_label='M',
                    graded_value_cm=valor, grading_type_applied='LINEAR',
                    capa=capa, instancia=instancia)

            pf = PieceFitting.objects.create(
                session=sessio, model=self.model, grading_version=gv)
            # El camí real de clonatge, extret del cos de `crea_piece_fitting`.
            for spec in GradedSpec.objects.filter(grading_version=gv, is_active=True):
                PieceFittingLine.objects.create(
                    piece_fitting=pf, pom=spec.pom, size_label=spec.size_label,
                    capa=spec.capa, instancia=spec.instancia,
                    valor_teoric=spec.graded_value_cm, valor_real=spec.graded_value_cm)

            linies = {(l.capa, l.instancia): l.valor_teoric
                      for l in PieceFittingLine.objects.filter(piece_fitting=pf)}
            self.assertEqual(linies, {(EXTERIOR, ''): 100.0,
                                      (FOLRE, ''): 98.0,
                                      (EXTERIOR, LEFT): 40.0})

    # ── La federació: la clau natural i el versionat del paquet ────────────────────

    def test_la_clau_natural_de_federacio_te_quatre_trams(self):
        """Amb la clau de dos, dues mesures germanes emetien la MATEIXA clau: el destí en
        desava una i l'altra desapareixia sense que cap de les dues cases ho sabés."""
        from fhort.tenants.federation_service import (FORMAT_PATRIMONI, _clau_amb_eixos,
                                                      _llegeix_patrimoni, _clau_natural_pom)

        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog'):
            self._tres_germanes()
            patrimoni = _llegeix_patrimoni(self.model)

            self.assertEqual(patrimoni['format'], FORMAT_PATRIMONI,
                             'el paquet ha de dir de quin format és')
            claus = [tuple(m['clau']) for m in patrimoni['mesures']]
            self.assertEqual(len(claus), len(set(claus)),
                             'dues mesures no poden viatjar amb la mateixa clau natural')
            self.assertTrue(all(len(c) == 4 for c in claus))

            # ⚠️ El patrimoni s'ancora a l'exterior/'' des de FASE_2 (el forat #2): les tres
            # germanes hi són, però només la canònica viatja. El que aquest cas fixa és la
            # FORMA de la clau, no quantes en surten.
            self.assertEqual(claus, [_clau_natural_pom(self.pom, EXTERIOR, '')])

    def test_un_paquet_vell_es_llegeix_com_a_exterior_i_instancia_unica(self):
        """Compatibilitat cap enrere, i no és teòrica: els paquets ja enviats parlen, de fet
        i sense excepció, de l'única cosa que el sistema sabia escriure."""
        from fhort.tenants.federation_service import _clau_amb_eixos

        self.assertEqual(_clau_amb_eixos(('CH-01', 'CH')), ('CH-01', 'CH', EXTERIOR, ''))
        self.assertEqual(_clau_amb_eixos(('CH-01', 'CH', FOLRE, LEFT)),
                         ('CH-01', 'CH', FOLRE, LEFT))

    # ── El rastre: cap ───────────────────────────────────────────────────────────────

    def test_el_harness_no_deixa_rastre(self):
        """Deia «les comportes tornen a estar vives» i en comptava nou de cada família. C4/G1-G4
        les han retirades totes; el que segueix fent falta és que el harness deixi l'esquema
        EXACTAMENT com el va trobar. Pel NOM i no per recompte."""
        def noms_de_check():
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT conname FROM pg_constraint c "
                    "JOIN pg_namespace n ON n.oid = c.connamespace "
                    "WHERE n.nspname = %s AND c.contype = 'c'",
                    [connection.schema_name])
                return {row[0] for row in cur.fetchall()}

        abans = noms_de_check()
        with comportes_alcades('models_app_basemeasurement',
                               'models_app_measurementchangelog'):
            pass

        self.assertEqual(noms_de_check(), abans, 'el harness ha canviat l\'esquema')
        self.assertEqual(
            {c for c in abans if c.endswith(('_capa_gate_c1', '_instancia_gate_cins'))},
            set(), 'una comporta ha sobreviscut a C4')
