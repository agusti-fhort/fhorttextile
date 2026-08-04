"""F1 · quina regla s'edita quan el codi de la URL casa amb més d'una (2026-08-01).

Els dos escriptors de regles de graduació muntats a `tasks/urls.py` —
`s2_views.update_grading_rule_view` i `s4_views.update_grading_rule_with_history_view` —
resolen la regla amb `Q(pom__pom_global__codi=codi) | Q(pom__codi_client=codi)` i es
quedaven el `.first()` d'una consulta SENSE `order_by`: el registre editat el triava el
pla de Postgres. No és hipotètic — a staging, el ruleset 217 té dues regles que responen
al codi 'BJ' (poms 514 i 418) amb increments 0.20 i 0.50.

El criteri fixat: guanya la regla el codi de la qual la llista MOSTRA per aquell POM
(`grading_rules_with_units_view`: codi global si n'hi ha, si no `codi_client`); empat →
`pk` més baix. Aquests tests fixen les dues meitats del criteri.
"""
import datetime

from django.contrib.auth import get_user_model
from django_tenants.test.cases import TenantTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from fhort.pom.models import (
    GradingRule,
    GradingRuleSet,
    POMGlobal,
    POMMaster,
    SizeDefinition,
    SizeSystem,
)
from fhort.pom.s2_views import update_grading_rule_view
from fhort.pom.s4_views import update_grading_rule_with_history_view


class OrdreDeterministaReglaGradingTest(TenantTestCase):
    """Dues regles del mateix ruleset casen amb el mateix codi: se n'edita UNA i sempre la mateixa."""

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
        super().setUp()
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(
            username='patronista', email='p@test.cat', password='x')
        sistema = SizeSystem.objects.create(codi='TST-ALPHA', nom='Test alpha')
        self.talla_base = SizeDefinition.objects.create(
            size_system=sistema, etiqueta='M', ordre=3)
        self.rs = GradingRuleSet.objects.create(nom='Test ruleset', is_system_default=False)

    def _pom(self, codi_client, codi_global=None):
        glob = None
        if codi_global:
            glob = POMGlobal.objects.create(
                codi=codi_global, nom_en=codi_global, nom_ca=codi_global, categoria='TEST')
        return POMMaster.objects.create(
            pom_global=glob, codi_client=codi_client, nom_client=f'POM {codi_client}')

    def _regla(self, pom, increment):
        return GradingRule.objects.create(
            rule_set=self.rs, pom=pom, talla_base=self.talla_base,
            logica=GradingRule.LOGICA_LINEAR, increment=increment)

    def _patch(self, vista, codi, increment, **extra_kwargs):
        req = self.factory.patch(
            f'/api/v1/grading-rule-sets/{self.rs.pk}/regles/{codi}/',
            {'increment': increment}, format='json')
        force_authenticate(req, user=self.user)
        return vista(req, rule_set_id=self.rs.pk, pom_codi=codi, **extra_kwargs)

    # ── El cas viu: un POM amb global i codi_client 'BJ' + un POM sense global 'BJ' ──
    #
    # La llista mostra 'BJ' NOMÉS per al segon (del primer n'emet el codi global). El POM
    # amb global es crea PRIMER a posta: té el `pk` més baix, o sigui que és el que un
    # `.first()` sense ordre retorna en un escaneig seqüencial. El test és vermell contra
    # el comportament anterior i verd amb el criteri del codi mostrat.

    def _corpus_bj(self):
        amb_global = self._pom('BJ', codi_global='LOSPOM-514')   # la llista n'emet 'LOSPOM-514'
        sense_global = self._pom('BJ')                            # la llista n'emet 'BJ'
        return (
            self._regla(amb_global, '0.20'),
            self._regla(sense_global, '0.50'),
        )

    def test_s2_edita_la_regla_que_la_llista_mostra_amb_aquell_codi(self):
        regla_altra, regla_bj = self._corpus_bj()
        self.assertLess(regla_altra.pk, regla_bj.pk)   # l'esquer: la falsa arriba primer

        resp = self._patch(update_grading_rule_view, 'BJ', 3.5)

        self.assertEqual(resp.status_code, 200)
        regla_bj.refresh_from_db()
        regla_altra.refresh_from_db()
        self.assertEqual(float(regla_bj.increment), 3.5)
        self.assertEqual(float(regla_altra.increment), 0.20)   # intacta

    def test_s4_edita_la_regla_que_la_llista_mostra_amb_aquell_codi(self):
        regla_altra, regla_bj = self._corpus_bj()

        resp = self._patch(update_grading_rule_with_history_view, 'BJ', 3.5)

        self.assertEqual(resp.status_code, 200)
        regla_bj.refresh_from_db()
        regla_altra.refresh_from_db()
        self.assertEqual(float(regla_bj.increment), 3.5)
        self.assertEqual(float(regla_altra.increment), 0.20)

    def test_el_codi_global_mana_sobre_el_codi_client_d_un_altre_pom(self):
        """Cas simètric del 'BJ': el codi de la URL és el codi GLOBAL d'un POM i, alhora,
        el `codi_client` d'un altre que ja mostra el SEU codi global. Guanya el primer."""
        aliena = self._regla(self._pom('CHEST', codi_global='LOSPOM-9'), '0.20')
        propia = self._regla(self._pom('PIT', codi_global='CHEST'), '0.50')
        self.assertLess(aliena.pk, propia.pk)

        resp = self._patch(update_grading_rule_view, 'CHEST', 3.5)

        self.assertEqual(resp.status_code, 200)
        propia.refresh_from_db()
        aliena.refresh_from_db()
        self.assertEqual(float(propia.increment), 3.5)
        self.assertEqual(float(aliena.increment), 0.20)

    def test_empat_pur_edita_sempre_la_regla_mes_antiga(self):
        """Dos POMs que MOSTREN el mateix codi: el criteri semàntic no desempata i mana
        el `pk` — la regla més antiga. Aquí el que es fixa és que no sigui aleatori."""
        antiga = self._regla(self._pom('BJ'), '0.20')
        nova = self._regla(self._pom('BJ'), '0.50')
        self.assertLess(antiga.pk, nova.pk)

        resp = self._patch(update_grading_rule_view, 'BJ', 3.5)

        self.assertEqual(resp.status_code, 200)
        antiga.refresh_from_db()
        nova.refresh_from_db()
        self.assertEqual(float(antiga.increment), 3.5)
        self.assertEqual(float(nova.increment), 0.50)
