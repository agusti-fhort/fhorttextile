"""SET-2/T10 — L'ÀNCORA DE LA MARE ARRIBA TAMBÉ A LES REGLES, a les dues bandes.

L'acta de T5b (`federation_service._llegeix_patrimoni`) diu, en singular, «l'àncora creix amb
`garment=''`»… i només va créixer al bucle de `BaseMeasurement`. El de `ModelGradingRule` es
va quedar sense, i el `.exists()` de la banda d'escriptura tampoc no l'anomena.

EL PERQUÈ DE L'ÀNCORA, que no canvia: `_clau_natural_pom` **no sap dir la peça** —és una
tupla de quatre trams `(codi global, codi client, capa, instància)` i cap d'ells és el
garment—, o sigui que dues peces del mateix POM emetrien la MATEIXA clau i el destí en desaria
una. Mentre la clau natural no creixi i els paquets no es versionin —contracte EXTERN, decisió
humana— el patrimoni que viatja és el de la peça MARE. Es deixa de dir el que no se sap dir.

ELS DOS DANYS, i són distints:

  ① LECTURA (`_llegeix_patrimoni`) — sense àncora, la regla d'una peça filla entra al paquet.
    Com que viatja amb una clau que no sap dir de quina peça és, el destí la re-crea com a
    regla de la MARE: la llei d'una calceta aplicada al cos sencer, sense que cap de les dues
    cases se n'assabenti. És pitjor que el col·lapse de mesures, perquè una regla no és un
    valor sinó una LLEI que genera tota una corba.

  ② ESCRIPTURA (`_escriu_a_la_marca`) — el `.exists()` sense àncora mira si el destí té
    QUALSEVOL regla d'aquell POM, filla inclosa. Amb una regla filla present, la regla de la
    mare que arriba del paquet es compta com a «saltada» i no s'escriu mai: el destí es queda
    sense la llei de la seva peça principal i el comptador diu que tot ha anat bé.

Amb les comportes de T2 vives cap dels dos casos es pot construir: totes les files són
`garment=''`. S'alcen dins d'un savepoint que sempre es desfà.
"""
import contextlib
import datetime

from django.db import connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import BaseMeasurement, Model, ModelGradingRule
from fhort.pom.models import POMMaster, SizeDefinition, SizeSystem

MARE = ''
SEGONA = '02'
TAULES = ('models_app_basemeasurement', 'models_app_measurementchangelog',
          'models_app_modelgradingrule')


@contextlib.contextmanager
def comportes_garment_alcades(*taules):
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


class _T10Base(TenantTestCase):

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
        self.ss = SizeSystem.objects.create(codi='SS_T10', nom='SS T10', base_unit='ALPHA')
        for i, et in enumerate(['S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.ss, etiqueta=et, ordre=i)
        self.pom = POMMaster.objects.create(codi_client='CH', nom_client='Pit')
        self.model = Model.objects.create(
            codi_intern='TST-T10', codi_tenant='TST', any=2026, sequencial=1,
            nom_prenda='Pijama', size_system=self.ss, size_run_model='S·M·L',
            base_size_label='M',
        )


class LaLecturaDelPatrimoniNomesAgafaLaMareTest(_T10Base):
    """Dany ① — la regla d'una peça filla no pot entrar al paquet."""

    def _regles_del_paquet(self):
        from fhort.tenants.federation_service import _llegeix_patrimoni
        return _llegeix_patrimoni(self.model)['regles']

    def test_la_regla_duna_peca_filla_NO_viatja(self):
        with comportes_garment_alcades(*TAULES):
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1, garment=MARE)
            ModelGradingRule.objects.create(
                model=self.model, pom=self.pom, logica='LINEAR', increment_base=1.0,
                actiu=True, garment=MARE)
            # La llei de l'altra peça: un increment d'un altre ordre de magnitud, perquè si
            # es colés no fallés per un decimal.
            ModelGradingRule.objects.create(
                model=self.model, pom=self.pom, logica='LINEAR', increment_base=10.0,
                actiu=True, garment=SEGONA)

            regles = self._regles_del_paquet()

            self.assertEqual(len(regles), 1, 'ha viatjat la regla duna peça que no és la mare')
            self.assertEqual(float(regles[0]['increment_base']), 1.0,
                             'la regla que viatja ha de ser la de la MARE')

    def test_CAS_DE_CONTROL_un_model_duna_sola_peca_viatja_igual_que_sempre(self):
        """El 100% del corpus d'avui. L'àncora no pot fer desaparèixer res del que ja viatjava."""
        BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0, ordre=1)
        ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, logica='LINEAR', increment_base=1.0, actiu=True)

        regles = self._regles_del_paquet()

        self.assertEqual(len(regles), 1)
        self.assertEqual(float(regles[0]['increment_base']), 1.0)


class LescripturaMiraNOMESLaReglaDeLaMareTest(_T10Base):
    """Dany ② — una regla filla al destí no pot fer saltar la de la mare."""

    def _te_regla_de_la_mare(self, pom):
        """EL PREDICAT DE PRODUCCIÓ, no una còpia seva.

        ⚠️ La primera versió d'aquest test escrivia el `filter(...).exists()` aquí mateix i
        el comparava amb ell mateix: passava en verd contra el codi trencat, perquè no
        tocava producció enlloc. Un test que no crida el codi que diu vigilar no és un
        test. Per això el predicat es va extreure a `federation_service` amb nom propi:
        el bucle de `_escriu_a_la_marca` no és aïllable sense muntar dos tenants, i això
        sí que ho és.
        """
        from fhort.tenants.federation_service import _te_regla_resident_de_la_mare
        return _te_regla_resident_de_la_mare(self.model, pom)

    def test_una_regla_filla_al_desti_no_compta_com_a_regla_de_la_mare(self):
        with comportes_garment_alcades(*TAULES):
            ModelGradingRule.objects.create(
                model=self.model, pom=self.pom, logica='LINEAR', increment_base=10.0,
                actiu=True, garment=SEGONA)

            # Sense àncora, `filter(model, pom).exists()` diria True i la regla de la mare
            # que arriba del paquet es comptaria com a «saltada» sense escriure's mai.
            self.assertTrue(
                ModelGradingRule.objects.filter(model=self.model, pom=self.pom).exists(),
                'el fixture no reprodueix el cas: cal una regla filla al destí')
            self.assertFalse(self._te_regla_de_la_mare(self.pom),
                             'una regla de la 02 no és una regla de la mare')

    def test_CAS_DE_CONTROL_la_regla_de_la_mare_SI_que_compta(self):
        ModelGradingRule.objects.create(
            model=self.model, pom=self.pom, logica='LINEAR', increment_base=1.0, actiu=True)

        self.assertTrue(self._te_regla_de_la_mare(self.pom))
