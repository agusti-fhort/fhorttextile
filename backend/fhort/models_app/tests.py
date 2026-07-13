"""Tests de l'importador de fitxes (models_app).

Convenció del repo: `tests.py` pla dins de l'app, executat amb
`python manage.py test fhort.models_app` (el projecte NO fa servir pytest).

QA-S8 (DIAGNOSI_QA_S8_IMPORT): les dues portes de vinculació del camí d'import.
El que aquests tests defensen és una sola frase: **una mesura del document no pot
desaparèixer en silenci.**
"""
import datetime

from django_tenants.test.cases import TenantTestCase

from fhort.models_app.extraction_views import (
    _apply_many_to_one_guard,
    _apply_match_threshold,
    _match_rows,
)
from fhort.pom.models import CustomerPOMAlias, POMMaster
from fhort.tasks.models import Customer


class _TenantBase(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant


class PortesDeVinculacioTest(_TenantBase):
    """Les portes de `_match_rows`: llindar de confiança + guard many-to-one."""

    def setUp(self):
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')
        # Un POM del catàleg amb un codi d'UNA lletra: és el que fa que el matcher, com a
        # darrer recurs, hi rooteji els codis 'U2' i 'U3' (`root_code_match`, LOW).
        self.pom_u = POMMaster.objects.create(
            codi_client='U', nom_client='Width sequins piece')

    def _fila(self, codi, descripcio='', **kw):
        return {'codi_fitxa': codi, 'descripcio': descripcio, 'values': {'S': 10.0}, **kw}

    # ── El cas real que va obrir el sprint ───────────────────────────────────
    def test_dues_files_amb_la_mateixa_arrel_no_collapsen_sobre_un_pom(self):
        """El cas U2/U3 del Brownie: dues mesures distintes (First button / Last button) que
        el matcher rootejava totes dues cap al POM 'U'. `BaseMeasurement` és únic per
        (model, pom): la segona esborrava la primera **sense dir res**."""
        rows, stats = _match_rows(
            [self._fila('U2', 'First button measured from collar'),
             self._fila('U3', 'Last button measured from armhole')],
            self.customer,
        )

        # Cap de les dues no es vincula: totes dues a pendents.
        self.assertIsNone(rows[0]['pom_master_id'])
        self.assertIsNone(rows[1]['pom_master_id'])
        self.assertFalse(rows[0]['actiu'])
        self.assertFalse(rows[1]['actiu'])

        # I el suggeriment queda VISIBLE: la persona ha de veure què li proposaven.
        self.assertEqual(rows[0]['weak_suggestion_codi'], 'U')
        self.assertEqual(rows[1]['weak_suggestion_codi'], 'U')

    def test_una_sola_fila_amb_confianca_baixa_tampoc_auto_vincula(self):
        """El llindar és independent del guard: un LOW tot sol (sense col·lisió) també cau a
        pendents. `root_code_match` és el darrer recurs del matcher, no una certesa."""
        rows, stats = _match_rows([self._fila('U2', 'First button')], self.customer)

        self.assertEqual(rows[0]['confidence'], 'LOW')
        self.assertIsNone(rows[0]['pom_master_id'])
        self.assertFalse(rows[0]['actiu'])
        self.assertEqual(rows[0]['weak_suggestion_codi'], 'U')
        self.assertEqual(stats['n_low'], 1)

    # ── La decisió que divergeix de la germana de size_map ───────────────────
    def test_lalias_NO_queda_exempt_del_guard(self):
        """**La divergència deliberada amb `size_map_views.py:53`.**

        Allà l'àlies queda exempt (el destí és `GradingRule`, i dos codis hi poden compartir
        un POM). Aquí NO, perquè el destí és `BaseMeasurement`, únic per (model, pom): per
        legítim que sigui l'àlies, dues files no hi caben i la segona esborra la primera.

        No és teòric: al catàleg viu, BRW té els àlies 'F' (Centre FRONT length) i 'FF'
        (Centre BACK length) tots dos cap al MATEIX POM. Amb l'exempció posada, les dues
        files travessaven totes dues portes amb confiança HIGH i una mesura es perdia.
        """
        pom = POMMaster.objects.create(codi_client='M-M79', nom_client='TOTAL LENGTH')
        CustomerPOMAlias.objects.create(customer=self.customer, pom=pom, client_code='F')
        CustomerPOMAlias.objects.create(customer=self.customer, pom=pom, client_code='FF')

        rows, stats = _match_rows(
            [self._fila('F', 'Centre front length'),
             self._fila('FF', 'Centre back length')],
            self.customer,
        )

        # Els dos resolen per àlies amb confiança ALTA…
        self.assertEqual(rows[0]['match_type'], 'alias_match')
        self.assertEqual(rows[0]['confidence'], 'HIGH')
        # …i tot i així el guard els atura: no poden compartir el POM.
        self.assertIsNone(rows[0]['pom_master_id'])
        self.assertIsNone(rows[1]['pom_master_id'])
        self.assertTrue(rows[0]['many_to_one'])
        self.assertTrue(rows[1]['many_to_one'])
        self.assertEqual(stats['n_many_to_one'], 2)

    def test_un_alias_que_NO_collideix_vincula_amb_normalitat(self):
        """El guard només mossega quan hi ha col·lisió: un àlies sa continua vinculant."""
        pom = POMMaster.objects.create(codi_client='CH', nom_client='Chest width')
        CustomerPOMAlias.objects.create(customer=self.customer, pom=pom, client_code='A')

        rows, stats = _match_rows([self._fila('A', '1/2 chest width')], self.customer)

        self.assertEqual(rows[0]['pom_master_id'], pom.id)
        self.assertEqual(rows[0]['match_type'], 'alias_match')
        self.assertTrue(rows[0]['actiu'])
        self.assertIsNone(rows[0]['weak_suggestion'])
        self.assertEqual(stats['n_many_to_one'], 0)

    # ── El criteri únic dels dos camins ──────────────────────────────────────
    def test_actiu_equival_a_vincle_ferm(self):
        """`actiu ⇔ vincle ferm`. Abans la via ràpida d'Excel marcava actiu=True per a TOTES
        les files (fins i tot les sense match) i la via Opus actiu=bool(pm): dos criteris per
        a la mateixa cosa. Ara el matching és literalment la mateixa funció."""
        pom = POMMaster.objects.create(codi_client='CH', nom_client='Chest width')
        CustomerPOMAlias.objects.create(customer=self.customer, pom=pom, client_code='A')

        rows, _ = _match_rows(
            [self._fila('A', '1/2 chest width'),        # àlies sa    → vincula
             self._fila('U2', 'First button'),          # LOW         → pendent
             self._fila('ZZZ', 'no existeix al cataleg')],  # sense match → pendent
            self.customer,
        )

        for r in rows:
            self.assertEqual(
                r['actiu'], r['pom_master_id'] is not None,
                msg=f"fila {r['codi_fitxa']}: actiu i vincle no quadren",
            )

    def test_lordre_del_document_es_conserva(self):
        rows, _ = _match_rows(
            [self._fila('A'), self._fila('B'), self._fila('C')], self.customer)
        self.assertEqual([r['ordre'] for r in rows], [0, 1, 2])
        self.assertEqual([r['codi_fitxa'] for r in rows], ['A', 'B', 'C'])

    def test_el_codi_del_document_es_conserva_encara_que_no_vinculi(self):
        """El `codi_fitxa` és el que la persona té al paper: no es perd mai, ni quan la fila
        cau a pendents. És el que el pas 3 ha d'ensenyar."""
        rows, _ = _match_rows([self._fila('U2', 'First button')], self.customer)
        self.assertEqual(rows[0]['codi_fitxa'], 'U2')


class PortesUnitariesTest(_TenantBase):
    """Les dues portes, aïllades del matcher."""

    def test_el_llindar_deixa_passar_HIGH_i_MEDIUM(self):
        pom = POMMaster.objects.create(codi_client='CH', nom_client='Chest')
        for conf in ('HIGH', 'MEDIUM'):
            efectiu, suggeriment = _apply_match_threshold(pom, conf)
            self.assertEqual(efectiu, pom)
            self.assertIsNone(suggeriment)

    def test_el_llindar_atura_LOW_i_torna_el_suggeriment(self):
        pom = POMMaster.objects.create(codi_client='CH', nom_client='Chest')
        efectiu, suggeriment = _apply_match_threshold(pom, 'LOW')
        self.assertIsNone(efectiu)
        self.assertEqual(suggeriment, pom)

    def test_el_guard_no_toca_res_si_no_hi_ha_collisio(self):
        rows = [
            {'pom_master_id': 1, 'pom_codi': 'A', 'pom_nom': 'a',
             'match_type': 'x', 'actiu': True},
            {'pom_master_id': 2, 'pom_codi': 'B', 'pom_nom': 'b',
             'match_type': 'x', 'actiu': True},
        ]
        _apply_many_to_one_guard(rows)
        self.assertEqual([r['pom_master_id'] for r in rows], [1, 2])
        self.assertTrue(all(r['actiu'] for r in rows))

    def test_el_guard_desvincula_TOTES_les_files_en_collisio(self):
        """Cap de les dues, no «la primera guanya»: si el sistema no sap quina és la bona,
        no en tria una a l'atzar."""
        rows = [
            {'pom_master_id': 7, 'pom_codi': 'U', 'pom_nom': 'u',
             'match_type': 'x', 'actiu': True},
            {'pom_master_id': 7, 'pom_codi': 'U', 'pom_nom': 'u',
             'match_type': 'x', 'actiu': True},
            {'pom_master_id': 9, 'pom_codi': 'V', 'pom_nom': 'v',
             'match_type': 'x', 'actiu': True},
        ]
        _apply_many_to_one_guard(rows)

        self.assertIsNone(rows[0]['pom_master_id'])
        self.assertIsNone(rows[1]['pom_master_id'])
        self.assertTrue(rows[0]['many_to_one'] and rows[1]['many_to_one'])
        self.assertEqual(rows[0]['weak_suggestion_codi'], 'U')
        # La fila que no col·lidia no s'ha tocat.
        self.assertEqual(rows[2]['pom_master_id'], 9)
        self.assertTrue(rows[2]['actiu'])
