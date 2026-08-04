"""C1/T4 — LA COMPORTA: cap escriptor pot crear una segona capa abans de C4.

C1 ensenya al sistema l'IDIOMA de la capa (catàleg + columna + claus) però NO el deixa
parlar-lo: la cadena de consumidors —serializers, motor de grading, UI, import, fitxa— encara
assumeix una mesura per (model, POM) i no s'adapta fins a C2/C3. Sense comporta, una fila
'folre' escrita per accident en aquesta finestra no petaria enlloc: es fondria dins les
llistes com si fos de l'exterior i corrompria en silenci mesures que són el producte.

El guard viu a la BD i no a l'aplicació a posta: és l'únic lloc que un `bulk_create`, un
`update()`, un loader de paquet o un `psql` a mà no poden esquivar. Aquests tests ho
verifiquen pel camí que de debò importa —l'`IntegrityError` de Postgres— i, a més, censen
que les NOU comportes hi són totes: una que faltés seria un forat silenciós.

C4 les retira per migració. Quan aquell sprint passi, aquest fitxer se'n va amb elles.

Convenció del repo: `python manage.py test fhort.models_app` (el projecte NO fa servir pytest).
"""
import datetime

from django.db import IntegrityError, connection, transaction
from django_tenants.test.cases import TenantTestCase

from fhort.models_app.models import (BaseMeasurement, Model, SizeCheck,
                                     SizeCheckLine)
from fhort.pom.models import POMMaster

#: Les nou comportes de C1, una per taula de T2. `models_app_modelgradingrule` NO hi és:
#: la regla de graduació no porta capa per decisió de domini (§3c, «mateixos deltes»).
COMPORTES = [
    'models_app_basemeasurement_capa_gate_c1',
    'models_app_measurementchangelog_capa_gate_c1',
    'models_app_modelgradingoverride_capa_gate_c1',
    'models_app_pomplacement_capa_gate_c1',
    'models_app_sizecheckline_capa_gate_c1',
    'fitting_gradedspec_capa_gate_c1',
    'fitting_piecefittingline_capa_gate_c1',
    'pom_garmentpommap_capa_gate_c1',
    'pom_itembasemeasurement_capa_gate_c1',
]


class ComportaCapaC1Test(TenantTestCase):

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
            codi_intern='TST-C1', codi_tenant='TST', any=2026, sequencial=1,
            temporada='SS26', size_run_model='S·M·L', base_size_label='M',
        )

    # ── La comporta barra ────────────────────────────────────────────────────────────

    def test_una_mesura_base_de_folre_no_entra(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            BaseMeasurement.objects.create(
                model=self.model, pom=self.pom, base_value_cm=100.0, capa='folre')

    def test_una_linia_de_size_check_de_folre_no_entra(self):
        check = SizeCheck.objects.create(model=self.model, talla_base_label='M')
        with self.assertRaises(IntegrityError), transaction.atomic():
            SizeCheckLine.objects.create(
                size_check=check, pom=self.pom, valor_teoric=100.0, capa='folre')

    def test_tampoc_hi_entra_per_update_massiu(self):
        """El camí que cap guard d'aplicació no cobriria: `queryset.update()` no passa per
        `save()`, ni pels signals, ni per cap serializer. La comporta sí que l'atura."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            BaseMeasurement.objects.filter(pk=bm.pk).update(capa='folre')

    # ── La comporta deixa passar el que ha de passar ─────────────────────────────────

    def test_exterior_entra_i_es_el_default(self):
        """La comporta no pot haver trencat el camí normal: qui no diu res escriu 'exterior'
        i entra. És la meitat de la feina d'un gate, i la que es dona per suposada."""
        bm = BaseMeasurement.objects.create(
            model=self.model, pom=self.pom, base_value_cm=100.0)
        bm.refresh_from_db()
        self.assertEqual(bm.capa, 'exterior')

    # ── El cens: cap forat ───────────────────────────────────────────────────────────

    def test_les_nou_comportes_existeixen_a_la_bd(self):
        """Una comporta que faltés seria un forat silenciós: la taula sense guard acceptaria
        la segona capa i ningú no se n'adonaria fins que les mesures ja fossin dolentes."""
        with connection.cursor() as cur:
            cur.execute(
                "SELECT conname FROM pg_constraint c "
                "JOIN pg_namespace n ON n.oid = c.connamespace "
                "WHERE n.nspname = %s AND c.contype = 'c' AND c.conname LIKE %s",
                [connection.schema_name, '%_capa_gate_c1'])
            trobades = {row[0] for row in cur.fetchall()}

        self.assertEqual(trobades, set(COMPORTES),
                         'falta (o sobra) alguna comporta de capa a la BD')

    def test_la_regla_de_grading_no_te_ni_capa_ni_comporta(self):
        """§3c: la regla es comparteix entre capes («mateixos deltes»). Si algú li afegeix
        `capa` sense passar per la decisió d'arquitectura, aquest test l'atura."""
        with connection.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s AND column_name = 'capa'",
                [connection.schema_name, 'models_app_modelgradingrule'])
            self.assertIsNone(cur.fetchone(),
                              'ModelGradingRule ha rebut una columna `capa`: és decisió '
                              "d'arquitectura (Patró C), no una peça d'sprint")
