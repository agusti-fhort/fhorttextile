"""FIX-3 (DIAGNOSI_MESURES_TEA_205) — un check Pendent no es queda amb files inertes.

`open_size_check` materialitzava les línies TOT-O-RES: només si el check no en tenia CAP.
Un POM nascut DESPRÉS d'obrir el check (típicament un import que amplia la fitxa) no rebia
mai SizeCheckLine, i a l'editor sortia com una fila que es veu però no es pot anotar.

Ara `open` COMPLETA: crea les línies que falten, amb el valor_teoric d'ARA, i no toca cap
línia existent (ni el seu teòric ni el que el tècnic hi hagi anotat).

═══ ACTA · «UNA LÍNIA PER GERMANA, NO UNA PER POM» (Agus, 2026-08-02, tram C3-E) ═══
Decisió de domini: al size check es mostren **les dues línies** quan un POM té germanes,
perquè són DUES MESURES — l'exterior i el folre no es validen amb la mateixa vara, i ensenyar-ne
una sola voldria dir demanar al tècnic que signi un valor que no ha vist.

Aquesta acta queda escrita aquí perquè la diagnosi C3 §A8 va llegir els recomptes d'aquest
fitxer (`n == 1`, `n == 2`) com si afirmessin «una línia per POM», i els va declarar en
contradicció amb `test_escriptors_instancia_cins.py:132` («una línia per germana, no una per
POM»). **No hi ha cap contradicció, i no s'ha girat res.** Els recomptes d'aquest fitxer
compten POMs DISTINTS sobre un fixture que només té una mesura per POM: amb una germana per
POM, «una per germana» i «una per POM» donen el mateix número. `_materialize_lines` ja itera
`BaseMeasurement` i clava per `(pom_id, capa, instancia)` des de FASE_3/C1-ins — o sigui que la
llei ja s'aplicava; el que faltava era un test que ho FIXÉS en comptes de deixar-ho a
interpretació. És `test_un_pom_amb_germanes_rep_UNA_LINIA_PER_GERMANA`, a baix.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import BaseMeasurement, Model, SizeCheck, SizeCheckLine
from fhort.models_app.services_size_check import open_size_check
from fhort.pom.models import MeasurementLayer, POMMaster


@contextlib.contextmanager
def _comportes_alcades(*taules, eixos=('capa_gate_c1', 'instancia_gate_cins')):
    """Alça les comportes dins d'un savepoint que SEMPRE es desfà (patró d'Onada 1)."""
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            # El `setUp` d'aquesta classe ja ha escrit una `BaseMeasurement`, i les FK de
            # Django són DEFERRABLE INITIALLY DEFERRED: Postgres refusa un ALTER TABLE amb
            # «pending trigger events» a sobre. Es buiden abans de tocar res. Els harnesses
            # germans (Onada 1, C1-ins) no ho necessiten perquè creen les files DINS del bloc.
            cur.execute('SET CONSTRAINTS ALL IMMEDIATE')
            for taula in taules:
                for sufix in eixos:
                    cur.execute(
                        f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                        f'DROP CONSTRAINT "{taula}_{sufix}"'
                    )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class OpenSizeCheckCompletaLiniesTest(TenantTestCase):

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
        self.model = Model.objects.create(
            codi_intern='TST-SC', codi_tenant='TST', any=2026, sequencial=7,
            temporada='SS27', size_run_model='XXS·XS·S·M·L', base_size_label='S',
        )
        self.pom_a = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        BaseMeasurement.objects.create(model=self.model, pom=self.pom_a, ordre=1,
                                       base_value_cm=46.0, origen='IMPORT')

    def _importa_pom(self, codi, valor):
        """Un POM que entra a la fitxa DESPRÉS (el que fa un import que l'amplia)."""
        pom = POMMaster.objects.create(codi_client=codi, nom_client=codi)
        BaseMeasurement.objects.create(model=self.model, pom=pom, ordre=9,
                                       base_value_cm=valor, origen='IMPORT')
        return pom

    def test_un_pom_amb_germanes_rep_UNA_LINIA_PER_GERMANA(self):
        """L'acta del capçal, feta pin. Dues mesures = dues línies que validar.

        Els altres recomptes d'aquest fitxer donen «una per POM» només perquè el fixture té
        una sola mesura per POM. Aquest crea la germana i separa les dues lectures.
        """
        with _comportes_alcades('models_app_basemeasurement', 'models_app_measurementchangelog',
                                'models_app_sizecheckline'):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom_a, ordre=2, base_value_cm=44.0,
                origen='IMPORT', capa='folre', nom_fitxa='A-FOL')

            sc, n = open_size_check(self.model.id)

            self.assertEqual(n, 2, 'una línia per GERMANA: exterior i folre són dues mesures')
            eixos = set(SizeCheckLine.objects.filter(size_check=sc, pom=self.pom_a)
                        .values_list('capa', 'instancia'))
            self.assertEqual(eixos, {(MeasurementLayer.SLUG_DEFECTE, ''), ('folre', '')})
            teorics = set(SizeCheckLine.objects.filter(size_check=sc, pom=self.pom_a)
                          .values_list('valor_teoric', flat=True))
            self.assertEqual(teorics, {46.0, 44.0},
                             'cada línia porta el teòric de la SEVA mesura, no el de la veïna')

    def test_un_pom_nascut_despres_rep_linia(self):
        sc, n = open_size_check(self.model.id)
        self.assertEqual(n, 1)

        pom_b = self._importa_pom('WA', 80.0)
        sc2, n2 = open_size_check(self.model.id)

        self.assertEqual(sc2.pk, sc.pk, 'ha de reusar el mateix Pendent, no crear-ne un altre')
        self.assertEqual(n2, 2)
        self.assertTrue(SizeCheckLine.objects.filter(size_check=sc, pom=pom_b).exists())

    def test_el_teoric_de_la_linia_nova_es_lACTUAL(self):
        """El «REAL (PROTO)» no pot néixer contra un teòric caducat."""
        sc, _ = open_size_check(self.model.id)
        pom_b = self._importa_pom('WA', 80.0)
        # La base es mou ABANS de tornar a obrir: la línia nova ha de néixer contra 82, no 80.
        bm = BaseMeasurement.objects.get(model=self.model, pom=pom_b)
        bm.base_value_cm = 82.0
        bm.save()

        open_size_check(self.model.id)
        linia = SizeCheckLine.objects.get(size_check=sc, pom=pom_b)
        self.assertEqual(linia.valor_teoric, 82.0)

    def test_no_toca_les_linies_ja_anotades(self):
        """Completar no pot trepitjar feina del tècnic — ni el valor_real ni el teòric pactat."""
        sc, _ = open_size_check(self.model.id)
        linia = SizeCheckLine.objects.get(size_check=sc, pom=self.pom_a)
        linia.valor_real = 45.2
        linia.decisio = 'tolerancia_acceptada'
        linia.nota = 'mesurat al taller'
        linia.save()
        # La base del POM ja anotat es mou: la seva línia NO s'ha de re-snapshotar.
        bm = BaseMeasurement.objects.get(model=self.model, pom=self.pom_a)
        bm.base_value_cm = 47.0
        bm.save()

        self._importa_pom('WA', 80.0)
        open_size_check(self.model.id)

        linia.refresh_from_db()
        self.assertEqual(linia.valor_real, 45.2)
        self.assertEqual(linia.valor_teoric, 46.0, 'el teòric pactat de la línia viva no es mou')
        self.assertEqual(linia.decisio, 'tolerancia_acceptada')
        self.assertEqual(linia.nota, 'mesurat al taller')

    def test_un_pendent_orfe_es_segueix_reomplint(self):
        """Comportament que ja hi era i es conserva: 0 línies → es reomple sencer."""
        sc, _ = open_size_check(self.model.id)
        SizeCheckLine.objects.filter(size_check=sc).delete()
        _sc, n = open_size_check(self.model.id)
        self.assertEqual(n, 1)

    def test_un_check_RESOLT_no_es_toca(self):
        """Un check completat és història: ni se li afegeixen línies ni es reobre."""
        sc, _ = open_size_check(self.model.id)
        sc.estat = 'Acceptat'
        sc.save(update_fields=['estat'])
        self._importa_pom('WA', 80.0)

        sc2, n2 = open_size_check(self.model.id)

        self.assertNotEqual(sc2.pk, sc.pk, "el resolt no es reusa: se n'obre un de nou")
        self.assertEqual(SizeCheckLine.objects.filter(size_check=sc).count(), 1,
                         'el check resolt es queda exactament amb les línies que tenia')
        self.assertEqual(n2, 2, 'el check NOU sí que neix amb tots els POMs vigents')

    def test_un_pom_sense_valor_de_base_no_genera_linia(self):
        """Regla que ja hi era: sense base_value_cm no hi ha res contra què mesurar."""
        pom_c = POMMaster.objects.create(codi_client='HI', nom_client='Maluc')
        BaseMeasurement.objects.create(model=self.model, pom=pom_c, ordre=5,
                                       base_value_cm=None, origen='TEMPLATE')
        _sc, n = open_size_check(self.model.id)
        self.assertEqual(n, 1)

    def test_un_pom_desactivat_no_reapareix(self):
        sc, _ = open_size_check(self.model.id)
        pom_b = self._importa_pom('WA', 80.0)
        BaseMeasurement.objects.filter(model=self.model, pom=pom_b).update(is_active=False)
        _sc, n = open_size_check(self.model.id)
        self.assertEqual(n, 1)
        self.assertFalse(SizeCheckLine.objects.filter(size_check=sc, pom=pom_b).exists())
