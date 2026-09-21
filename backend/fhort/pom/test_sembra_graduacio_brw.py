"""Tests de `sembra_graduacio_brw` (COMMIT 3, sembra BRW denim+exterior, 21/09/2026).

Font canònica de dades: `ops/sembra_brw/graduacio_denim_exterior.json` (COMMIT 1). Aquests
tests NO l'usen directament — construeixen el seu propi JSON mínim (`_json_minim`) perquè
cada test aïlli EXACTAMENT el que vol provar, sense dependre de si el fitxer real canvia.

Escrits, NO executats (llei de suites d'aquesta casa): `python -m py_compile` ha de sortir
net; l'execució real la fa qui tingui accés a la BD de test.
"""
import io
import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import (
    POMMaster, CustomerPOMAlias, SizeSystem, SizeDefinition,
    GradingRuleSet, GradingRule, GarmentGroup,
)
from fhort.tasks.models import Customer


class _TenantBase(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'


def _json_minim(**overrides):
    """JSON mínim vàlid per a la comanda: 1 POM nou, 1 àlies, 1 regla exterior (delta
    uniforme), 1 regla denim FIXED i 1 regla denim amb break (per exercir totes dues
    formes sense arrossegar les 29 files reals). `overrides` reemplaça claus senceres."""
    data = {
        'poms_nous': [
            {'codi': 'ZZ1', 'nom_en': 'Test width', 'nom_es_referencia': 'x',
             'familia_referencia': 'Z', 'logica_referencia': 'lineal', 'origen_referencia': 'x',
             'nota': None},
        ],
        'alies': [
            {'codi_brw': 'ZZ1', 'avui_apunta_a_referencia': '— (no existeix)',
             'ha_dapuntar_a_referencia': 'ZZ1 · Test width (POM nou)',
             'pom_desti_codi': 'ZZ1', 'es_instancia': False,
             'accio': 'CREAR', 'motiu': 'test'},
        ],
        'jocs': [
            {
                'nom': 'ZZ Exterior Test',
                'sistema': 'ALPHA_EU_W',
                'sistema_crear_si_absent': False,
                'ambit_garment_group': 'OUTERWEAR',
                'talla_base': 'S',
                'crear_si_absent': True,
                'regles': [
                    {'pom': 'ZZ1', 'nom': 'Test width',
                     'deltes_per_pas': [1, 1, 1, 1],
                     'passos': ['XXS→XS', 'XS→S', 'S→M', 'M→L'],
                     'tolerancia': None, 'nota': None},
                ],
            },
            {
                'nom': 'ZZ Denim Test',
                'sistema': 'ZZ_SYS_01',
                'sistema_crear_si_absent': True,
                'sistema_talles': ['P', '32', '34', '36', '38', '40', '42'],
                'ambit_garment_group': 'BOTTOMS',
                'talla_base': '34',
                'crear_si_absent': True,
                'regles': [
                    {'pom': 'ZZ1', 'nom': 'Test width', 'valor_34_referencia': 10,
                     'deltes_per_pas': [0, 0, 0, 0, 0, 0],
                     'passos': ['P→32', '32→34', '34→36', '36→38', '38→40', '40→42'],
                     'tolerancia_referencia': {'minus': 0, 'plus': 0}, 'nota': 'FIX'},
                ],
            },
        ],
        'avisos_pas0': [],
        'pendents': [],
    }
    data.update(overrides)
    return data


class SembraGraduacioBrwTest(_TenantBase):

    def setUp(self):
        self.customer = Customer.objects.create(codi='BRW', nom='Brownie')
        # ALPHA_EU_W amb prou talles per a la regla exterior de test.
        self.alpha = SizeSystem.objects.create(codi='ALPHA_EU_W', nom='Alpha EU', base_unit='ALPHA')
        for i, etq in enumerate(['XXS', 'XS', 'S', 'M', 'L']):
            SizeDefinition.objects.create(size_system=self.alpha, etiqueta=etq, ordre=i)
        GarmentGroup.objects.get_or_create(codi='OUTERWEAR', defaults={'nom': 'Outerwear'})
        GarmentGroup.objects.get_or_create(codi='BOTTOMS', defaults={'nom': 'Bottoms'})

    def _fitxer(self, data):
        f = tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, dir=tempfile.gettempdir())
        json.dump(data, f)
        f.close()
        self.addCleanup(lambda: Path(f.name).unlink(missing_ok=True))
        return f.name

    def _run(self, data, apply=False, create_run=True, customer='BRW'):
        out = io.StringIO()
        kwargs = {'customer': customer, 'fitxer': self._fitxer(data), 'stdout': out}
        if apply:
            kwargs['apply'] = True
        if create_run:
            kwargs['create_run'] = True
        call_command('sembra_graduacio_brw', **kwargs)
        return out.getvalue()

    # ── Idempotència ─────────────────────────────────────────────────────────────────
    def test_apply_dues_vegades_la_segona_no_canvia_res(self):
        data = _json_minim()
        self._run(data, apply=True)
        n_poms_abans = POMMaster.objects.count()
        n_alies_abans = CustomerPOMAlias.objects.filter(customer=self.customer).count()
        n_regles_abans = GradingRule.objects.count()

        sortida2 = self._run(data, apply=True)

        self.assertEqual(POMMaster.objects.count(), n_poms_abans)
        self.assertEqual(CustomerPOMAlias.objects.filter(customer=self.customer).count(),
                         n_alies_abans)
        self.assertEqual(GradingRule.objects.count(), n_regles_abans)
        self.assertNotIn('ACTUALITZAT', sortida2)
        self.assertNotIn('CREAT', sortida2)

    def test_dry_run_no_escriu_res(self):
        data = _json_minim()
        self._run(data, apply=False)
        self.assertFalse(POMMaster.objects.filter(codi_client='ZZ1').exists())
        self.assertFalse(SizeSystem.objects.filter(codi='ZZ_SYS_01').exists())

    # ── POM existent amb atributs diferents ─────────────────────────────────────────
    def test_pom_existent_amb_nom_diferent_no_es_sobreescriu(self):
        POMMaster.objects.create(codi_client='ZZ1', nom_client='Nom ja existent i diferent')
        data = _json_minim()

        sortida = self._run(data, apply=True)

        pom = POMMaster.objects.get(codi_client='ZZ1')
        self.assertEqual(pom.nom_client, 'Nom ja existent i diferent',
                         'un POM amb nom diferent NO es sobreescriu sense --force')
        self.assertIn('DIVERGEIX', sortida)

    def test_pom_existent_amb_mateix_nom_es_iguala(self):
        POMMaster.objects.create(codi_client='ZZ1', nom_client='Test width')
        data = _json_minim()

        sortida = self._run(data, apply=True)

        self.assertEqual(POMMaster.objects.filter(codi_client='ZZ1').count(), 1)
        self.assertIn('IGUAL', sortida)

    # ── Àlies: repuntat i rastre ─────────────────────────────────────────────────────
    def test_alies_repuntat_deixa_rastre_origen_i_editat_at(self):
        pom_vell = POMMaster.objects.create(codi_client='ZZ0-VELL', nom_client='vell', actiu=False)
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='ZZ1', pom=pom_vell, origen='DICCIONARI')
        data = _json_minim()

        self._run(data, apply=True)

        alias.refresh_from_db()
        self.assertEqual(alias.pom.codi_client, 'ZZ1')
        self.assertEqual(alias.origen, 'SEMBRA0921')
        self.assertIsNotNone(alias.editat_at, "el repunt ha de deixar rastre a editat_at")

    def test_alies_ja_correcte_no_es_toca(self):
        pom_nou = POMMaster.objects.create(codi_client='ZZ1', nom_client='Test width')
        alias = CustomerPOMAlias.objects.create(
            customer=self.customer, client_code='ZZ1', pom=pom_nou, origen='DICCIONARI')
        data = _json_minim()

        self._run(data, apply=True)

        alias.refresh_from_db()
        self.assertEqual(alias.origen, 'DICCIONARI',
                         "un àlies ja correcte no es toca (l'origen no es reescriu en va)")

    # ── Exterior: 4 deltes iguals → LINEAR pur, sense breaks ────────────────────────
    def test_exterior_deltes_iguals_dona_linear_sense_breaks(self):
        data = _json_minim()
        self._run(data, apply=True)

        rs = GradingRuleSet.objects.get(nom='ZZ Exterior Test')
        regla = rs.regles.get(pom__codi_client='ZZ1')
        self.assertEqual(regla.logica, 'LINEAR')
        self.assertEqual(float(regla.increment_base), 1.0)
        self.assertIsNone(regla.breaks)

    def test_exterior_delta_no_uniforme_queda_pendent(self):
        data = _json_minim()
        data['jocs'][0]['regles'][0]['deltes_per_pas'] = [1, 1, 2, 1]  # no uniforme

        sortida = self._run(data, apply=True)

        self.assertFalse(GradingRuleSet.objects.get(nom='ZZ Exterior Test')
                         .regles.filter(pom__codi_client='ZZ1').exists())
        self.assertIn('PENDENT', sortida)

    # ── Denim: FIX = 0, logica FIXED ─────────────────────────────────────────────────
    def test_denim_deltes_zero_dona_fixed(self):
        data = _json_minim()
        self._run(data, apply=True)

        rs = GradingRuleSet.objects.get(nom='ZZ Denim Test')
        regla = rs.regles.get(pom__codi_client='ZZ1')
        self.assertEqual(regla.logica, 'FIXED')
        self.assertEqual(float(regla.increment_base), 0.0)
        self.assertIsNone(regla.breaks)

    # ── Denim: joc existent, mai en crea un altre ────────────────────────────────────
    def test_denim_usa_el_joc_existent_no_en_crea_un_altre(self):
        sistema = SizeSystem.objects.create(codi='ZZ_SYS_01', nom='ZZ', base_unit='NUMERIC_EU')
        for i, etq in enumerate(['P', '32', '34', '36', '38', '40', '42']):
            SizeDefinition.objects.create(
                size_system=sistema, etiqueta=etq, ordre=i,
                valor_numeric=int(etq) if etq.isdigit() else None)
        existent = GradingRuleSet.objects.create(
            nom='ZZ Denim Test', size_system=sistema, customer=self.customer,
            origen=GradingRuleSet.ORIGEN_CLIENT_RUN, actiu=True)
        data = _json_minim()

        self._run(data, apply=True, create_run=False)

        self.assertEqual(GradingRuleSet.objects.filter(nom='ZZ Denim Test').count(), 1)
        rs = GradingRuleSet.objects.get(nom='ZZ Denim Test')
        self.assertEqual(rs.id, existent.id, 'reutilitza el mateix joc, no en duplica un altre')

    def test_denim_sense_create_run_i_sistema_absent_atura(self):
        data = _json_minim()
        with self.assertRaises(CommandError):
            self._run(data, apply=False, create_run=False)

    def test_customer_inexistent_atura_amb_error(self):
        data = _json_minim()
        with self.assertRaises(CommandError):
            self._run(data, apply=False, customer='NO-EXISTEIX')
