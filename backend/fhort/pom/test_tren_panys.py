"""TREN DE PANYS · les portes que revertien sembres (22/08/2026).

Substrat: `docs/ordres/CENS_CATALEG_V5_STAGING.md` (C6, el cens dels 24 escriptors-creadors)
i la llei S44 de `docs/ordres/DECISIONS_snapshot_2026-08-22.md`.

── EL PRINCIPI QUE DEFENSEN TOTS ────────────────────────────────────────────────────────
Una comanda de sembra pot **CREAR el que falta**; no pot **REESCRIURE** nomenclatura,
`pom_global` ni famílies d'allò que ja existeix, si no és amb un flag explícit d'overwrite que
ho faci constar. I cap lookup d'idempotència per un camp rebatejable sense fallback + abort.

Cada classe és un pany, i cada pany té les dues cares que el brief demana:
  (a) el cas que el cens va documentar, REPRODUÏT i ara bloquejat;
  (b) el camí legítim (create-if-missing), que segueix verd.

  · `PanyP1LoadLosanPackageTest`  — `load_losan_package` no rebateja ni re-enganxa
  · `PanyP2ExtendPomCatalogTest`  — `extend_pom_catalog`, el mateix, i destí explícit
  · `PanyP3JocRebatejatTest`      — un joc rebatejat no en fabrica un SEGON
  · `PanyP4SetupFromExcelTest`    — sense CONFIGURE, 403 amb missatge

⚠️ Cap escriptura a cap BD viva: `TenantTestCase` corre sobre una BD de test pròpia.
"""
import json
import os
import tempfile
from io import StringIO

from django.core.management import call_command
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import POMCategory, POMGlobal, POMMaster


# ── El paquet LOSAN mínim ────────────────────────────────────────────────────────────────
# `load_losan_package._run_all()` obre dotze fitxers; el cas que es mesura només viu al
# tercer. La resta van buits A POSTA: un paquet real (1,2 MB, 962 models) faria la prova
# lenta i taparia el que mesura. Els blocs buits no són stubs del camí sota prova — el camí
# sota prova és `_load_pom_masters`, que corre sencer i contra la BD.
POM_GLOBAL = {
    'codi': 'POM-501', 'nom_en': 'Chest width', 'nom_ca': 'Ample de pit', 'nom_es': '',
    'categoria': 'Upper body', 'descripcio_en': '', 'descripcio_ca': '', 'unitat': 'cm',
    'actiu': True, 'abbreviation': 'CH', 'notes': '', 'iso_ref': '',
}
POM_MASTER = {
    'key': {'pom_global': 'POM-501', 'codi_client': 'CH'},
    'pom_global': 'POM-501', 'codi_client': 'CH', 'nom_client': 'Chest width',
    'categoria': None, 'notes': '', 'actiu': True, 'pendent_revisio': False,
    'origen_import': '', 'tolerancia_default_minus': '0.60', 'tolerancia_default_plus': '0.60',
}
CUSTOMER = {
    'codi': 'LOS', 'nom': 'Losan', 'active': True, 'is_self': False, 'rao_social': '',
    'nif': '', 'adreca_linia1': '', 'adreca_linia2': '', 'ciutat': '', 'codi_postal': '',
    'pais': '', 'email_facturacio': '', 'condicions_pagament': '', 'descompte_pct': 0,
    'persona_contacte': '', 'telefon_contacte': '', 'tax_regime': '', 'vat_number': '',
    'payment_method': '', 'logo': '', 'logo_asset': '',
}
PAQUET = {
    'manifest.json': {'commit': 'test', 'source_schema': 'los'},
    '01_customer.json': {'rows': [CUSTOMER]},
    '02_pom_globals.json': {'rows': [POM_GLOBAL]},
    '03_pom_masters.json': {'rows': [POM_MASTER]},
    '04_pom_aliases.json': {'rows': []},
    '05_garment_catalog.json': {'groups': [], 'types': [], 'items': []},
    '06_pom_maps.json': {'garment_pom_maps': [], 'item_base_measurements': []},
    '07_size_systems.json': {'size_systems': [], 'size_definitions': []},
    '08_rulesets.json': {'rulesets': [], 'scope_nodes': []},
    '09_rules.json': {'rows': []},
    '10_profiles.json': {'rows': []},
    '11_document_templates.json': {'rows': []},
}


class PanyP1LoadLosanPackageTest(TenantTestCase):
    """P1 · el paquet CREA el que falta i NO rebateja —ni re-enganxa— el que ja hi és.

    🚨 EL CAS DEL CENS. `_load_pom_masters` portava `pom_global`, `codi_client`, `nom_client` i
    `categoria` als defaults de l'UPDATE. Un POM que el tenant havia desenganxat del global i
    rebatejat tornava, a la correguda següent, al text i al lligam del paquet: la reparació
    desfeta en silenci, i sense cap fallada que ho digués. El pany de sobirania no hi arribava
    perquè només mira `separat_de_global`, i un POM desenganxat sense marca hi és invisible.
    """

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Panys'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TPY'
        return tenant

    def setUp(self):
        self.pkg = tempfile.mkdtemp(prefix='paquet_losan_test_')
        for nom, dades in PAQUET.items():
            with open(os.path.join(self.pkg, nom), 'w', encoding='utf-8') as fh:
                json.dump(dades, fh)

    def _run(self, **extra):
        out = StringIO()
        call_command('load_losan_package', schema_target=self.tenant.schema_name,
                     package_dir=self.pkg, apply=True, stdout=out, **extra)
        return out.getvalue()

    def _pom_desenganxat(self):
        """El POM que el tenant ha fet seu: mateix `codi_client` (per això el paquet el
        retroba), sense lligam al global i amb nom i família propis."""
        cat = POMCategory.objects.create(codi='E', nom_ca='Pit')
        return POMMaster.objects.create(
            codi_client='CH', nom_client='Ample de pit (nostre)',
            pom_global=None, categoria=cat)

    # ── (a) el cas del cens, ara bloquejat ────────────────────────────────────────────────
    def test_un_pom_desenganxat_no_es_re_enganxa(self):
        pom = self._pom_desenganxat()

        sortida = self._run()

        pom.refresh_from_db()
        self.assertIsNone(pom.pom_global_id)                      # NO re-enganxat
        self.assertEqual(pom.nom_client, 'Ample de pit (nostre)')  # NO rebatejat
        self.assertEqual(pom.categoria.codi, 'E')                  # família intacta
        # i cap segona fila al seu lloc: el pany no és un `continue` que duplica
        self.assertEqual(POMMaster.objects.filter(codi_client='CH').count(), 1)
        # i ho DIU: un upsert de nomenclatura que no es veu és pitjor que una fallada
        self.assertIn('nomenclatura PROTEGIDA', sortida)
        self.assertIn('pom_global', sortida)

    # ── (b) el camí legítim segueix verd ─────────────────────────────────────────────────
    def test_create_if_missing_segueix_viu(self):
        self.assertFalse(POMMaster.objects.filter(codi_client='CH').exists())

        self._run()

        pom = POMMaster.objects.get(codi_client='CH')
        self.assertEqual(pom.nom_client, 'Chest width')
        self.assertEqual(pom.pom_global.codi, 'POM-501')   # crear SÍ lliga

    def test_camps_no_de_nomenclatura_segueixen_actualitzant_se(self):
        """El pany protegeix el VOCABULARI, no congela la fila: el paquet segueix manant
        sobre l'estat (`notes`, `actiu`, toleràncies…)."""
        pom = self._pom_desenganxat()
        pom.notes = 'nota vella'
        pom.actiu = False
        pom.save(update_fields=['notes', 'actiu'])

        self._run()

        pom.refresh_from_db()
        self.assertEqual(pom.notes, '')      # el paquet mana sobre l'estat
        self.assertTrue(pom.actiu)
        self.assertEqual(pom.nom_client, 'Ample de pit (nostre)')   # …i no sobre el nom

    # ── el flag explícit: reescriu, i CONSTA ─────────────────────────────────────────────
    def test_overwrite_nomenclature_reescriu_i_ho_fa_constar(self):
        pom = self._pom_desenganxat()

        sortida = self._run(overwrite_nomenclature=True)

        pom.refresh_from_db()
        self.assertEqual(pom.pom_global.codi, 'POM-501')
        self.assertEqual(pom.nom_client, 'Chest width')
        self.assertIn('nomenclatura REESCRITA', sortida)
        self.assertIn('CH', sortida)
