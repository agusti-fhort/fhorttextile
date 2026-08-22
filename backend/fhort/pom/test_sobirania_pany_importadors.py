"""SOBIRANIA DEL POM · TRAM 2 — EL PANY DELS IMPORTADORS.

🚨 EL QUE AQUEST TEST FA IMPOSSIBLE. `load_losan_package` i `extend_pom_catalog` fan UPSERT
sobre `codi_client` / `nom_client` / `actiu` / `pom_global`. Tots dos es diuen «idempotents»
—i ho són respecte del catàleg GLOBAL—, però són DESTRUCTIUS respecte del tenant: una
re-execució revertia en silenci la reparació feta a PROD, i ningú se n'assabentava perquè un
upsert que reescriu el que ja hi havia no falla mai.

La llei és **REPORTEN I NO TOQUEN**: mai un upsert silenciós sobre un POM que el tenant ha fet
seu. La marca que ho fa possible és `POMMaster.separat_de_global` (tram 3) — sense ella, un POM
nascut al tenant i un POM separat del global són indistingibles, perquè tots dos tenen
`pom_global` a NULL.

`test_corre_l_importador_despres_d_una_separacio_i_NO_la_desfa` és la seqüència sencera, en
ordre, contra la BD: sembra → separació → re-execució.
"""
import datetime

from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import POMCategory, POMGlobal, POMMaster
from fhort.pom.nomenclatura import separa_del_global


class PanyDelsImportadorsTest(TenantTestCase):
    """🔒 EL TEST DEL TRAM 2: córrer l'importador després d'una separació NO la desfà."""

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Sobirania'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TSB'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)
        return tenant

    def setUp(self):
        POMCategory.objects.get_or_create(codi='Upper body', defaults={'nom_en': 'Upper body'})
        self.pg = POMGlobal.objects.create(
            codi='POM-029', nom_en='Front yoke length (center)',
            nom_ca='Llargada de canesú (centre)', categoria='Upper body',
            abbreviation='YK L', start_point='HPS / neck seam', end_point='Yoke seam',
            scope='FULL', orientation='VERTICAL', state='FLAT', line='STRAIGHT',
            body_section='FRONT', unitat='cm',
        )

    def test_corre_l_importador_despres_d_una_separacio_i_NO_la_desfa(self):
        from django.core.management import call_command
        from io import StringIO

        # ① l'importador sembra el POM lligat al global
        call_command('extend_pom_catalog', schema=self.tenant.schema_name, stdout=StringIO())
        pom = POMMaster.objects.get(pom_global=self.pg)
        self.assertEqual(pom.codi_client, 'YK L')

        # ② el tenant el fa SEU: el rebateja i el separa (copy-on-write)
        separa_del_global(pom)
        pom.codi_client = 'CAN'
        pom.nom_client = 'Llargada de canesú'
        pom.save()
        self.assertIsNone(pom.pom_global_id)
        self.assertEqual(pom.separat_de_global, 'POM-029')
        # el copy-on-write li ha deixat el «com es mesura» del global
        self.assertEqual(pom.start_point, 'HPS / neck seam')

        # ③ 🔒 l'importador torna a córrer — i NO el toca
        out = StringIO()
        call_command('extend_pom_catalog', schema=self.tenant.schema_name, stdout=out)
        pom.refresh_from_db()
        self.assertEqual(pom.codi_client, 'CAN')
        self.assertEqual(pom.nom_client, 'Llargada de canesú')
        self.assertIsNone(pom.pom_global_id)
        self.assertEqual(pom.separat_de_global, 'POM-029')

        # ④ i ho REPORTA: un upsert silenciós hauria estat pitjor que una fallada
        text = out.getvalue()
        self.assertIn('sobirans', text)
        self.assertIn('POM-029', text)
        self.assertIn('CAN', text)

        # ⑤ i no n'ha fabricat un de nou al seu lloc (el pany no és un `continue` que duplica)
        self.assertEqual(POMMaster.objects.filter(pom_global=self.pg).count(), 0)
