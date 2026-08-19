"""SET-2/R3 — EL GARMENT NO ÉS UN EIX DE GERMANOR: ÉS UNA FRONTERA.

Aquest arnès és **la condició que ha d'estar verda abans de retirar les comportes
`*_garment_gate_set2`** de T2. No és un test de cortesia: vigila l'única fuita del tram
que ESCRIU a dades reals i que ho faria en silenci.

EL MAL QUE VIGILA. `germanes_de` (`services_derivacio.py`) demanava «mateix (model, POM)»
i després «comparteixen instància O comparteixen capa». Dues files amb la MATEIXA capa i
la MATEIXA instància en peces DIFERENTS passaven **les dues** branques de la `Q`: el pit
del top i el pit de la calceta es declaraven germans l'un de l'altre. I com que `deriva()`
alimenta `aplica()`, que ESCRIU (`services_derivacio.py:124`, invocada des de
`services_size_check.py:255-257`), corregir el pit del top n'hi hauria sumat l'increment
al de la calceta: **el mateix valor, sense cap avís i creuant peces**. El lector no ho
podia detectar, perquè el resultat era una xifra plausible en una fila legítima.

PER QUÈ EL TEST ALÇA LA COMPORTA. Mentre les comportes de T2 visquin, `garment` és '' a
tota la BD i cap fila '02' pot existir — o sigui que la fuita és inobservable i el filtre
nou és un no-op. Per provar-lo cal el món que la comporta encara barra. S'alça dins d'un
savepoint que SEMPRE es desfà, exactament com ja fan `test_lectors_capa_onada1` i
`test_instancia_comporta_cins`: el `finally` no és decoratiu, i la comporta ha de tornar
igual encara que un assert peti a dins.
"""
import contextlib
import datetime

from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import BaseMeasurement, Model
from fhort.models_app.services_derivacio import deriva, germanes_de
from fhort.pom.models import POMMaster

MARE = ''
SEGONA = '02'
FOLRE = 'folre'

#: S'alcen DUES taules i no una. La segona és `MeasurementChangeLog`, i el motiu és el mateix
#: que `test_c3_b_dues_germanes` ja documenta per a la capa: el **signal F1 estampa l'eix de la
#: fila que s'escriu**, i aquella taula porta la SEVA pròpia comporta. Mentre el signal no
#: copiava el garment (abans de T5) n'hi havia prou amb la de la mesura; des que el copia
#: —que és el que ha de fer, perquè el log és append-only i una atribució errònia no es pot
#: corregir— escriure una mesura de la 02 fa néixer un apunt de la 02, i sense alçar aquesta
#: comporta el `create` peta amb CheckViolation. (2026-08-10)
TAULES = ('models_app_basemeasurement', 'models_app_measurementchangelog')


@contextlib.contextmanager
def comporta_garment_alcada(*taules):
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


class GermanesNoCreuenElGarmentTest(TenantTestCase):

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
            codi_intern='TST-R3', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    def _mesura(self, *, garment=MARE, capa='exterior', instancia='', valor=100.0,
                nom_fitxa='A'):
        return BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=valor, ordre=1,
            tolerancia_minus=0.5, tolerancia_plus=0.5, nom_fitxa=nom_fitxa,
            capa=capa, instancia=instancia, garment=garment,
        )

    def test_dues_peces_amb_la_mateixa_capa_i_instancia_NO_son_germanes(self):
        """El cas exacte de R3, i el que abans passava les DUES branques de la `Q`.

        Mateix model, mateix POM, mateixa capa i mateixa instància: l'única cosa que les
        separa és la peça. No són dues cares de la mateixa mesura; són dues mesures de dues
        prendes distintes.
        """
        with comporta_garment_alcada(*TAULES):
            mare = self._mesura(garment=MARE, nom_fitxa='A-MARE')
            segona = self._mesura(garment=SEGONA, valor=60.0, nom_fitxa='A-02')

            self.assertNotIn(segona, list(germanes_de(mare)),
                             'la peça 02 s\'ha colat com a germana de la mare')
            self.assertNotIn(mare, list(germanes_de(segona)),
                             'la mare s\'ha colat com a germana de la peça 02')

    def test_corregir_una_peca_no_mou_l_altra(self):
        """La cara que de debò fa mal: `deriva()` és el que alimenta l'escriptura.

        Si el creuament sobrevisqués, aquí sortiria una `Derivacio` apuntant a la fila de
        l'altra peça —i `aplica()` l'hi escriuria.
        """
        with comporta_garment_alcada(*TAULES):
            mare = self._mesura(garment=MARE, nom_fitxa='A-MARE')
            segona = self._mesura(garment=SEGONA, valor=60.0, nom_fitxa='A-02')

            fora = deriva(mare, 100.0, 103.0)

            self.assertEqual(
                [d.base_measurement_id for d in fora], [],
                'corregir la peça mare ha proposat moure una fila d\'una altra peça')
            segona.refresh_from_db()
            self.assertEqual(float(segona.base_value_cm), 60.0)

    def test_dins_d_una_mateixa_peca_les_germanes_segueixen_sent_germanes(self):
        """L'altra cara, i la que evita que el filtre nou es convertisca en un tap.

        El garment acota la germanor; no la suprimeix. Dins de la peça 02, la capa segueix
        sent un eix de germanor exactament com sempre —si això caigués, la derivació
        quedaria morta per a tota peça que no fos la mare, i el símptoma seria un silenci.
        """
        with comporta_garment_alcada(*TAULES):
            ext = self._mesura(garment=SEGONA, capa='exterior', nom_fitxa='B-EXT')
            fol = self._mesura(garment=SEGONA, capa=FOLRE, valor=98.0, nom_fitxa='B-FOL')

            self.assertIn(fol, list(germanes_de(ext)),
                          'la germana de capa de la MATEIXA peça s\'ha perdut')

            fora = deriva(ext, 100.0, 103.0)
            self.assertEqual([d.base_measurement_id for d in fora], [fol.pk])
            self.assertEqual(fora[0].valor_proposat, 101.0)
