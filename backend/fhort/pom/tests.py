"""Tests de la biblioteca de nomenclatura del client (pom).

Convenció del repo: `tests.py` pla dins de l'app, executat amb
`python manage.py test fhort.pom` (el projecte NO fa servir pytest).

QA-S8 (DIAGNOSI_QA_S8_D3_D4 · D4a): el guard d'aprenentatge d'àlies. El que aquests tests
defensen és una sola frase: **un POM que el client ja reclama amb un altre codi no s'aprèn
en silenci.**
"""
import datetime

from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import CustomerPOMAlias, POMMaster
from fhort.pom.services import maybe_learn_customer_alias
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


class GuardAprenentatgeAliasTest(_TenantBase):
    """`maybe_learn_customer_alias` no pot aprendre dos codis distints cap al mateix POM com
    si tots dos fossin bons.

    És la mateixa família de defecte que hi ha al catàleg viu de BRW: 'F' (FRONT total length)
    i 'FF' (BACK total length) tots dos sobre el POM 389 'TOTAL LENGTH', i 'U2' (1st BUTTON) /
    'U3' (LAST BUTTON) tots dos sobre el 439 'Width sequins piece' — mesures DISTINTES sobre
    un sol POM.

    El muntatge reprodueix el cas U2/U3, que és el que de debò passa pel camí d'APRENENTATGE:
    descripcions que el matcher NO sap resoldre sol (cap paraula en comú amb el nom del POM),
    de manera que arriba a sembrar l'àlies. Quan el matcher ja l'encerta sol (HIGH/MEDIUM),
    `maybe_learn_customer_alias` no sembra res per disseny i el guard no hi juga.
    """

    def setUp(self):
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')
        # El POM que al catàleg viu es va endur U, U2 i U3. El seu nom no té cap paraula en
        # comú amb '1st BUTTON'/'LAST BUTTON' → el matcher no els hi sap portar sol
        # (hi arriba per l'arrel del codi, 'U', amb confiança LOW).
        self.pom_u = POMMaster.objects.create(
            codi_client='U', nom_client='Width sequins piece')
        self.pom_altre = POMMaster.objects.create(
            codi_client='WA', nom_client='Waist width')

    def test_primer_codi_sapren_net(self):
        """Cap altre codi del client no reclama encara el POM → àlies normal, no pendent."""
        alias = maybe_learn_customer_alias(self.customer, 'U2', '1st BUTTON', self.pom_u)

        self.assertIsNotNone(alias)
        self.assertEqual(alias.pom_id, self.pom_u.id)
        self.assertFalse(
            alias.pendent_revisio,
            "El primer codi cap a un POM lliure no té res de sospitós: no s'ha de marcar.")

    def test_segon_codi_cap_al_mateix_pom_cau_a_pendent(self):
        """EL CAS F/FF (aquí, U2/U3). 'U2' ja reclama el POM; 'U3' és una mesura DISTINTA que
        hi torna a caure → s'ha de crear PENDENT DE REVISIÓ, no com un àlies bo."""
        maybe_learn_customer_alias(self.customer, 'U2', '1st BUTTON', self.pom_u)

        alias_u3 = maybe_learn_customer_alias(self.customer, 'U3', 'LAST BUTTON', self.pom_u)

        self.assertIsNotNone(alias_u3)
        self.assertEqual(alias_u3.pom_id, self.pom_u.id)
        self.assertTrue(
            alias_u3.pendent_revisio,
            "'U3' cau sobre un POM que 'U2' ja reclama: s'ha de marcar per revisar, no "
            "aprendre'l en silenci com si fos bo.")
        # I el primer no s'ha tocat: el guard no reescriu el passat.
        self.assertFalse(
            CustomerPOMAlias.objects.get(
                customer=self.customer, client_code='U2').pendent_revisio)

    def test_un_pom_lliure_no_queda_contaminat_pel_guard(self):
        """El guard mira el POM de DESTÍ, no el client sencer: un segon codi cap a un POM que
        ningú no reclama segueix essent un àlies net."""
        maybe_learn_customer_alias(self.customer, 'U2', '1st BUTTON', self.pom_u)

        alias_b = maybe_learn_customer_alias(self.customer, 'B', 'CINTURA', self.pom_altre)

        self.assertIsNotNone(alias_b)
        self.assertFalse(
            alias_b.pendent_revisio,
            'El POM WA no el reclama ningú: aquest àlies no té cap col·lisió.')

    def test_reaprendre_el_mateix_codi_no_el_marca(self):
        """Idempotència: re-sembrar el MATEIX codi cap al MATEIX POM no és una col·lisió (el
        guard exclou el propi codi), i per tant no ha de marcar-lo com a pendent."""
        maybe_learn_customer_alias(self.customer, 'U2', '1st BUTTON', self.pom_u)
        alias = maybe_learn_customer_alias(self.customer, 'U2', '1st BUTTON', self.pom_u)

        self.assertEqual(
            CustomerPOMAlias.objects.filter(
                customer=self.customer, client_code='U2').count(), 1)
        if alias is not None:  # si el matcher ja l'encerta sol, retorna None i no re-sembra
            self.assertFalse(alias.pendent_revisio)
