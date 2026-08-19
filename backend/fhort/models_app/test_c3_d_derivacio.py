"""C3-D — el servei de derivació entre germanes, provat pels dos eixos.

LA REGLA (Agus, 02/08): l'exterior passa de 54 a 56 → el folre passa de 52 a 54. Es mou el
VALOR, mai el grading, i **la folgança es conserva sola perquè ningú no la toca**. Aquests
tests la comproven per resta: si en algun moment es propagués l'absolut en comptes de
l'increment, la folgança es faria zero i tots cauríen.

Amb les comportes de C1/C1-ins tancades no hi pot haver cap germana, o sigui que el servei és
inverificable sense alçar-les dins d'un savepoint que sempre es desfà (patró
`test_lectors_capa_onada1.py:36-52`, autoritzat per a aquesta feina).

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import contextlib
import datetime

from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import BaseMeasurement, Model
from fhort.models_app.services_derivacio import (EIX_CAPA, EIX_INSTANCIA, deriva,
                                                 germanes_de)
from fhort.pom.models import MeasurementLayer, POMMaster

FOLRE = 'folre'
ENTRETELA = 'entretela'
ESQUERRA = 'left'
DRETA = 'right'
EXTERIOR = MeasurementLayer.SLUG_DEFECTE

TAULES_DEL_CAMI = ('models_app_basemeasurement', 'models_app_measurementchangelog')


@contextlib.contextmanager
def comportes_alcades(*taules, eixos=('capa_gate_c1', 'instancia_gate_cins')):
    sid = transaction.savepoint()
    try:
        with connection.cursor() as cur:
            for taula in taules:
                for sufix in eixos:
                    # `IF EXISTS` — C4/G1-G4 (04/08) han retirat les 40 comportes: alçar-ne
                    # una que ja no hi és és el mateix estat, i el `finally` retorna igual.
                    cur.execute(
                        f'ALTER TABLE "{connection.schema_name}"."{taula}" '
                        f'DROP CONSTRAINT IF EXISTS "{taula}_{sufix}"'
                    )
        yield
    finally:
        transaction.savepoint_rollback(sid)


class DerivacioC3DTest(TenantTestCase):

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
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-C3D', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    def _bm(self, valor, **kw):
        kw.setdefault('nom_fitxa', 'A')
        return BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=valor, ordre=kw.pop('ordre', 1), **kw)

    # ── EL CAS CANÒNIC ───────────────────────────────────────────────────────────────

    def test_exterior_54_a_56_mou_el_folre_de_52_a_54(self):
        """El cas literal de la regla d'Agus, amb la folgança comprovada per resta."""
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = self._bm(54.0)
            fol = self._bm(52.0, capa=FOLRE, ordre=2, nom_fitxa='A-FOL')
            folganca_abans = ext.base_value_cm - fol.base_value_cm

            props = deriva(ext, 54.0, 56.0)

            self.assertEqual(len(props), 1)
            p = props[0]
            self.assertEqual(p.base_measurement_id, fol.pk)
            self.assertEqual(p.capa, FOLRE)
            self.assertEqual(p.eix, EIX_CAPA)
            self.assertEqual(p.increment, 2.0)
            self.assertEqual(p.valor_actual, 52.0)
            self.assertEqual(p.valor_proposat, 54.0)
            # La folgança es conserva SOLA: ningú no la declara enlloc.
            self.assertEqual(56.0 - p.valor_proposat, folganca_abans)

    def test_el_mateix_mecanisme_serveix_per_a_lEIX_INSTANCIA(self):
        with comportes_alcades(*TAULES_DEL_CAMI):
            esq = self._bm(40.0, instancia=ESQUERRA, nom_fitxa='A-ESQ')
            dre = self._bm(39.0, instancia=DRETA, ordre=2, nom_fitxa='A-DRE')

            props = deriva(esq, 40.0, 41.5)

            self.assertEqual(len(props), 1)
            self.assertEqual(props[0].base_measurement_id, dre.pk)
            self.assertEqual(props[0].eix, EIX_INSTANCIA)
            self.assertEqual(props[0].increment, 1.5)
            self.assertEqual(props[0].valor_proposat, 40.5)

    def test_un_decrement_tambe_es_propaga(self):
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = self._bm(54.0)
            self._bm(52.0, capa=FOLRE, ordre=2, nom_fitxa='A-FOL')

            props = deriva(ext, 54.0, 51.0)

            self.assertEqual(props[0].increment, -3.0)
            self.assertEqual(props[0].valor_proposat, 49.0)

    def test_diverses_germanes_reben_el_MATEIX_increment(self):
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = self._bm(54.0)
            self._bm(52.0, capa=FOLRE, ordre=2, nom_fitxa='A-FOL')
            self._bm(50.0, capa=ENTRETELA, ordre=3, nom_fitxa='A-ENT')

            props = deriva(ext, 54.0, 56.0)

            self.assertEqual({p.increment for p in props}, {2.0})
            self.assertEqual(sorted(p.valor_proposat for p in props), [52.0, 54.0])

    # ── EL QUE EL SERVEI NO HA DE FER ───────────────────────────────────────────────

    def test_no_inventa_una_germana_que_no_existeix(self):
        ext = self._bm(54.0)
        self.assertEqual(deriva(ext, 54.0, 56.0), [],
                         'si la fila no hi és, no hi és: la crea el tècnic o l\'import')

    def test_no_mou_una_germana_SENSE_valor(self):
        """Una fila materialitzada sense mesurar no té d'on partir."""
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = self._bm(54.0)
            self._bm(None, capa=FOLRE, ordre=2, origen='TEMPLATE', nom_fitxa='A-FOL')

            self.assertEqual(deriva(ext, 54.0, 56.0), [])

    def test_un_increment_zero_no_proposa_res(self):
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = self._bm(54.0)
            self._bm(52.0, capa=FOLRE, ordre=2, nom_fitxa='A-FOL')

            self.assertEqual(deriva(ext, 54.0, 54.0), [])

    def test_una_CREACIO_no_deriva(self):
        """Sense valor anterior no hi ha delta: el valor de la germana és mesura seva."""
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = self._bm(54.0)
            self._bm(52.0, capa=FOLRE, ordre=2, nom_fitxa='A-FOL')

            self.assertEqual(deriva(ext, None, 54.0), [])

    def test_una_fila_amb_els_DOS_eixos_diferents_no_es_germana(self):
        """El folre de la sisa esquerra no té folgança declarada amb l'exterior de la dreta."""
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = self._bm(54.0)                                     # (exterior, '')
            fol = self._bm(52.0, capa=FOLRE, ordre=2, nom_fitxa='A-FOL')   # un eix
            self._bm(30.0, capa=FOLRE, instancia=ESQUERRA, ordre=3, nom_fitxa='A-FE')  # dos

            ids = {p.base_measurement_id for p in deriva(ext, 54.0, 56.0)}

            self.assertEqual(ids, {fol.pk})

    def test_una_germana_INACTIVA_no_es_mou(self):
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = self._bm(54.0)
            self._bm(52.0, capa=FOLRE, ordre=2, is_active=False, nom_fitxa='A-FOL')

            self.assertEqual(deriva(ext, 54.0, 56.0), [])

    def test_el_servei_es_PUR_no_escriu_res(self):
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = self._bm(54.0)
            fol = self._bm(52.0, capa=FOLRE, ordre=2, nom_fitxa='A-FOL')

            deriva(ext, 54.0, 56.0)

            fol.refresh_from_db()
            ext.refresh_from_db()
            self.assertEqual(fol.base_value_cm, 52.0, 'la germana NO s\'ha tocat')
            self.assertEqual(ext.base_value_cm, 54.0)

    # ── L'enumeració de la família ──────────────────────────────────────────────────

    def test_germanes_de_no_inclou_la_fila_mateixa(self):
        with comportes_alcades(*TAULES_DEL_CAMI):
            ext = self._bm(54.0)
            fol = self._bm(52.0, capa=FOLRE, ordre=2, nom_fitxa='A-FOL')

            self.assertEqual([g.pk for g in germanes_de(ext)], [fol.pk])

    def test_germanes_de_no_creua_models_ni_POMs(self):
        with comportes_alcades(*TAULES_DEL_CAMI):
            altre_pom = POMMaster.objects.create(codi_client='WA', nom_client='Cintura')
            ext = self._bm(54.0)
            self._bm(52.0, capa=FOLRE, ordre=2, nom_fitxa='A-FOL')
            BaseMeasurement.objects.create(
                model=self.model, pom=altre_pom, base_value_cm=70.0, ordre=9,
                capa=FOLRE, nom_fitxa='B-FOL')

            self.assertEqual(len(list(germanes_de(ext))), 1)
