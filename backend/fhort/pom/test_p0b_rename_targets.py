"""P0b (2026-07-24) — rename del vocabulari de targets (`rename_targets_p0b`).

Executat amb `python manage.py test fhort.pom` (el projecte NO fa servir pytest).

Per què mereix tests i no només un dry-run: el rename és una PERMUTACIÓ AMB COL·LISIONS
sobre una columna UNIQUE — `BABY_GIRL` és alhora origen (→NEWBORN_GIRL) i destí
(TODDLER_GIRL→). Dues coses hi poden anar malament en silenci i totes dues destrueixen
dades a PROD:
  · **A** — que l'ordre A→C→D no sigui el correcte i una fila aterri al codi equivocat
    (p. ex. que TODDLER_GIRL acabi a NEWBORN_GIRL, saltant-se una baula).
  · **B** — que el command no sigui idempotent: com que BABY_* existeix abans I després,
    una segona passada podria tornar a moure'l a NEWBORN_* i buidar la franja BABY.
  · **C** — que els FK/M2M es despengin. No haurien: apunten a `id`, no a `codi`. El test
    ho fixa perquè ningú converteixi mai `codi` en clau de relació.
"""
import datetime

from django.core.management import call_command
from django.core.management.base import CommandError
from django_tenants.test.cases import TenantTestCase

from fhort.pom.models import GradingRuleSet, SizeSystem, Target

# Estat de partida idèntic al de PROD/staging (public i fhort tenen aquestes 13 files).
VOCABULARI_VELL = [
    'WOMAN', 'MAN', 'UNISEX_ADULT',
    'BABY_GIRL', 'BABY_BOY', 'BABY_UNISEX',
    'TODDLER_GIRL', 'TODDLER_BOY',
    'GIRL', 'BOY',
    'TEEN_GIRL', 'TEEN_BOY',
    'MATERNITY',
]
ESPERAT = {
    'BOY': 'KID_BOY', 'GIRL': 'KID_GIRL',
    'TODDLER_BOY': 'BABY_BOY', 'TODDLER_GIRL': 'BABY_GIRL',
    'BABY_BOY': 'NEWBORN_BOY', 'BABY_GIRL': 'NEWBORN_GIRL',
    'BABY_UNISEX': 'NEWBORN_UNISEX',
}
INTACTES = ['WOMAN', 'MAN', 'UNISEX_ADULT', 'TEEN_GIRL', 'TEEN_BOY', 'MATERNITY']


class P0bRenameTargetsTest(TenantTestCase):

    @classmethod
    def setup_tenant(cls, tenant):
        tenant.nom = 'Test Tenant'
        tenant.tipologia = 'MARCA'
        tenant.codi_tenant = 'TST'
        tenant.vat_number = 'X0000000X'
        tenant.tipus_client = 'STANDARD'
        tenant.gratis_fins = datetime.date(2030, 1, 1)

    def setUp(self):
        Target.objects.all().delete()
        self.ids = {}
        for i, codi in enumerate(VOCABULARI_VELL):
            self.ids[codi] = Target.objects.create(
                codi=codi, nom_en=codi.title(), display_order=i).id

    def _run(self, **kw):
        # El schema del TenantTestCase; --apply escriu de veritat.
        call_command('rename_targets_p0b', schemas=[self.tenant.schema_name], **kw)

    # ── A — l'ordre és correcte: cada codi vell aterra al seu destí, per ID ──────
    def test_a_cada_fila_aterra_al_seu_desti(self):
        self._run(apply=True)
        for vell, nou in ESPERAT.items():
            self.assertEqual(
                Target.objects.get(id=self.ids[vell]).codi, nou,
                f'la fila que era {vell} hauria de ser {nou}')

    def test_a_els_intactes_no_es_mouen(self):
        self._run(apply=True)
        for codi in INTACTES:
            self.assertEqual(Target.objects.get(id=self.ids[codi]).codi, codi)

    def test_a_cap_temporal_supervivent_i_el_cens_es_conserva(self):
        self._run(apply=True)
        self.assertFalse(Target.objects.filter(codi__startswith='_TMP_').exists())
        self.assertEqual(Target.objects.count(), len(VOCABULARI_VELL))

    def test_a_els_noms_acompanyen_el_codi(self):
        # Si no, `NEWBORN_GIRL` es quedaria amb nom_en 'Baby Girl' i l'export CSV
        # (s8_views, que pinta target.nom_en en cru) mentiria.
        self._run(apply=True)
        self.assertEqual(Target.objects.get(codi='NEWBORN_GIRL').nom_en, 'Newborn Girl')
        self.assertEqual(Target.objects.get(codi='BABY_GIRL').nom_en, 'Baby Girl')

    # ── dry-run: informa però no escriu ─────────────────────────────────────────
    def test_dry_run_no_escriu(self):
        self._run()
        self.assertEqual(
            sorted(Target.objects.values_list('codi', flat=True)), sorted(VOCABULARI_VELL))

    # ── B — idempotència: la segona passada és un no-op, no un segon rename ─────
    def test_b_segona_passada_es_noop(self):
        self._run(apply=True)
        despres = dict(Target.objects.values_list('id', 'codi'))
        self._run(apply=True)
        self.assertEqual(dict(Target.objects.values_list('id', 'codi')), despres)

    def test_b_estat_mixt_atura(self):
        # Un rename a mitges (testimoni vell + testimoni nou alhora) ha de petar, no
        # "arreglar" el que trobi.
        Target.objects.filter(codi='GIRL').update(codi='KID_GIRL')
        with self.assertRaises(CommandError):
            self._run(apply=True)

    # ── C — les relacions apunten a id: el rename no en desenganxa cap ──────────
    def test_c_les_relacions_sobreviuen(self):
        ss = SizeSystem.objects.create(nom='P0b SS', codi='P0B_SS')
        ss.targets.set([self.ids['GIRL'], self.ids['TODDLER_GIRL']])
        rs = GradingRuleSet.objects.create(nom='P0b RS', codi_sistema='P0B_RS')
        rs.targets.set([self.ids['BABY_UNISEX']])

        self._run(apply=True)

        self.assertEqual(sorted(ss.targets.values_list('codi', flat=True)),
                         ['BABY_GIRL', 'KID_GIRL'])
        self.assertEqual(list(rs.targets.values_list('codi', flat=True)),
                         ['NEWBORN_UNISEX'])
        # I el filtre per codi nou troba el ruleset (és el que fa la cascada del front).
        self.assertIn(rs, GradingRuleSet.objects.filter(targets__codi='NEWBORN_UNISEX'))
