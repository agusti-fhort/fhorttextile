"""
Sprint nadó · afegeix 9 POMGlobal nous (peu / entrecuix / elàstic / half moon).

Origen: fitxa real de pijama de nadó LNBUN0101_24002. Mesures de producte
(no normatives → iso_ref=''). Codis correlatius POM-146..POM-154 (màxim previ
del catàleg = POM-145).

Categories (taxonomia PLANA existent, no es crea cap POMCategory nova):
  Foot (4)           → 'Lower body'
  CROTCH LENGTH      → 'Rise'
  Elastic (3)        → 'Waistband'
  HALF MOON LENGTH   → 'Closure / Detail'

Patró idèntic a extend_pom_catalog (NON-DESTRUCTIU, idempotent):
  - update_or_create POMGlobal per codi a 'public' + tenant (mai .delete()).
  - clona 1 POMMaster per POMGlobal nou al tenant (els POMs nous només són
    visibles a l'app via POMMaster.pom_global).

Run:  python manage.py seed_baby_poms                       # dry-run, all
      python manage.py seed_baby_poms --no-dry-run          # escriu, all
      python manage.py seed_baby_poms --schema public --no-dry-run
      python manage.py seed_baby_poms --schema fhort --no-dry-run
"""
import argparse

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

ALL_SCHEMAS = ['public', 'fhort']

# 9 new POMs. Fields mirror POMGlobal (com a extend_pom_catalog).
NEW_POMS = [
    # ── Foot (pijama nadó amb peus) → 'Lower body' ──────────────────────────
    {
        'codi': 'POM-146', 'nom_en': 'Front foot length',
        'nom_ca': 'Llargada frontal del peu', 'categoria': 'Lower body',
        'abbreviation': 'FT FR L',
        'descripcio_en': 'Measure along the front (instep) of the foot from the ankle seam to the toe tip, garment laid flat.',
        'descripcio_ca': "Mesura per la part frontal (empenya) del peu des de la costura del turmell fins a la punta, peça plana.",
        'start_point': 'Ankle seam', 'end_point': 'Toe tip', 'reference_point': 'Along instep (front), laid flat',
        'scope': 'FULL', 'orientation': 'VERTICAL', 'state': 'FLAT', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 0.5, 'tol_samp_cm': 0.25,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    {
        'codi': 'POM-147', 'nom_en': 'Foot length',
        'nom_ca': 'Llargada del peu', 'categoria': 'Lower body',
        'abbreviation': 'FT L',
        'descripcio_en': 'Measure the total foot length from the back of the heel to the toe tip, sole laid flat.',
        'descripcio_ca': 'Mesura la llargada total del peu des del taló fins a la punta, sola plana.',
        'start_point': 'Heel (back)', 'end_point': 'Toe tip', 'reference_point': 'Along sole, laid flat',
        'scope': 'FULL', 'orientation': 'HORIZONTAL', 'state': 'FLAT', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 0.5, 'tol_samp_cm': 0.25,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    {
        'codi': 'POM-148', 'nom_en': 'Foot width',
        'nom_ca': 'Amplada del peu', 'categoria': 'Lower body',
        'abbreviation': 'FT W',
        'descripcio_en': 'Measure the foot width straight across at the widest point, laid flat. Size-step variants: S.20, S.20-2, S.20-3, S.20-4.',
        'descripcio_ca': "Mesura l'amplada del peu al punt més ample, plana. Variants d'escalat: S.20, S.20-2, S.20-3, S.20-4.",
        'start_point': 'Foot edge', 'end_point': 'Foot edge', 'reference_point': 'At widest point of the foot, laid flat (variants S.20/S.20-2/S.20-3/S.20-4)',
        'scope': 'HALF', 'orientation': 'HORIZONTAL', 'state': 'FLAT', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 0.3, 'tol_samp_cm': 0.2,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    {
        'codi': 'POM-149', 'nom_en': 'Foot width location',
        'nom_ca': "Localització de l'amplada del peu", 'categoria': 'Lower body',
        'abbreviation': 'FT W POS',
        'descripcio_en': 'Distance from the toe tip (or ankle seam) to the point where the foot width is measured, along the sole.',
        'descripcio_ca': "Distància des de la punta (o costura del turmell) fins al punt on es mesura l'amplada del peu, per la sola.",
        'start_point': 'Toe tip / ankle seam', 'end_point': 'Foot width measuring point', 'reference_point': 'Along sole',
        'scope': 'FULL', 'orientation': 'HORIZONTAL', 'state': 'FLAT', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 0.5, 'tol_samp_cm': 0.25,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    # ── Crotch → 'Rise' ─────────────────────────────────────────────────────
    {
        'codi': 'POM-150', 'nom_en': 'Crotch length',
        'nom_ca': "Llargada d'entrecuix", 'categoria': 'Rise',
        'abbreviation': 'CR L',
        'descripcio_en': 'Measure the crotch length from the front waist edge through the crotch to the back waist edge, along the seam, garment laid flat.',
        'descripcio_ca': "Mesura la llargada d'entrecuix des de la vora de cintura davantera, passant per l'entrecuix, fins a la posterior, per la costura, peça plana.",
        'start_point': 'Front waist edge', 'end_point': 'Back waist edge', 'reference_point': 'Through crotch, along seam',
        'scope': 'FULL', 'orientation': 'CURVED', 'state': 'FLAT', 'line': 'CURVED', 'body_section': 'BOTH',
        'tol_prod_cm': 0.5, 'tol_samp_cm': 0.25,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    # ── Elastic → 'Waistband' ───────────────────────────────────────────────
    {
        'codi': 'POM-151', 'nom_en': 'Elastic relaxed',
        'nom_ca': 'Elàstic en repòs', 'categoria': 'Waistband',
        'abbreviation': 'EL RLX',
        'descripcio_en': 'Measure the elastic straight across in its relaxed (un-stretched) state, edge to edge, laid flat.',
        'descripcio_ca': "Mesura l'elàstic en repòs (sense estirar), de vora a vora, pla.",
        'start_point': 'Elastic edge', 'end_point': 'Elastic edge', 'reference_point': 'Elastic relaxed, laid flat',
        'scope': 'HALF', 'orientation': 'HORIZONTAL', 'state': 'RELAXED', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 0.5, 'tol_samp_cm': 0.5,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    {
        'codi': 'POM-152', 'nom_en': 'Elastic extended',
        'nom_ca': 'Elàstic estès', 'categoria': 'Waistband',
        'abbreviation': 'EL EXT',
        'descripcio_en': 'Measure the elastic straight across fully extended (stretched to maximum), edge to edge.',
        'descripcio_ca': "Mesura l'elàstic totalment estès (estirat al màxim), de vora a vora.",
        'start_point': 'Elastic edge', 'end_point': 'Elastic edge', 'reference_point': 'Elastic fully extended',
        'scope': 'HALF', 'orientation': 'HORIZONTAL', 'state': 'STRETCHED', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 1.0, 'tol_samp_cm': 0.5,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    {
        'codi': 'POM-153', 'nom_en': 'Elastic location',
        'nom_ca': "Localització de l'elàstic", 'categoria': 'Waistband',
        'abbreviation': 'EL POS',
        'descripcio_en': 'Distance from the stated reference edge (waist/hem/cuff) to the elastic, indicating its position.',
        'descripcio_ca': "Distància des de la vora de referència (cintura/baix/puny) fins a l'elàstic, indicant-ne la posició.",
        'start_point': 'Reference edge (waist/hem/cuff)', 'end_point': 'Elastic', 'reference_point': 'Position of the elastic',
        'scope': 'FULL', 'orientation': 'VERTICAL', 'state': 'FLAT', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 0.5, 'tol_samp_cm': 0.25,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    # ── Half moon → 'Closure / Detail' ──────────────────────────────────────
    {
        'codi': 'POM-154', 'nom_en': 'Half moon length',
        'nom_ca': 'Llargada de la mitja lluna', 'categoria': 'Closure / Detail',
        'abbreviation': 'HM L',
        'descripcio_en': 'Measure the length of the half-moon piece (back-neck reinforcement / decorative detail) at its longest, laid flat.',
        'descripcio_ca': "Mesura la llargada de la peça de mitja lluna (reforç de coll posterior / detall decoratiu) al seu punt més llarg, plana.",
        'start_point': 'Half moon edge', 'end_point': 'Half moon edge', 'reference_point': 'Longest dimension of the half-moon detail',
        'scope': 'FULL', 'orientation': 'HORIZONTAL', 'state': 'FLAT', 'line': 'CURVED', 'body_section': 'BACK',
        'tol_prod_cm': 0.5, 'tol_samp_cm': 0.25,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
]


def _pomglobal_defaults(row):
    return {
        'nom_en': row['nom_en'], 'nom_ca': row['nom_ca'], 'nom_es': '',
        'categoria': row['categoria'],
        'descripcio_en': row['descripcio_en'], 'descripcio_ca': row['descripcio_ca'],
        'unitat': 'cm', 'actiu': True,
        'abbreviation': row['abbreviation'],
        'start_point': row['start_point'], 'end_point': row['end_point'],
        'reference_point': row['reference_point'],
        'scope': row['scope'], 'orientation': row['orientation'], 'state': row['state'],
        'line': row['line'], 'body_section': row['body_section'],
        'is_key': False,
        'tol_prod_cm': row['tol_prod_cm'], 'tol_samp_cm': row['tol_samp_cm'],
        'applies_woven': row['applies_woven'], 'applies_knit': row['applies_knit'],
        'applies_swim': row['applies_swim'],
        'notes': '', 'iso_ref': '',
    }


class Command(BaseCommand):
    help = 'Afegeix 9 POMGlobal de nadó (POM-146..154) + clona POMMaster al tenant (idempotent, no destructiu).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action=argparse.BooleanOptionalAction,
            default=True,
            help='Imprimeix què faria sense escriure res (default). Usa --no-dry-run per escriure.',
        )
        parser.add_argument(
            '--schema',
            choices=['public', 'fhort', 'all'],
            default='all',
            help='Schema on actuar: public | fhort | all (default: all).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        schema_opt = options['schema']
        schemas = ALL_SCHEMAS if schema_opt == 'all' else [schema_opt]

        mode = 'DRY-RUN (cap escriptura)' if dry_run else 'ESCRIPTURA REAL'
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'seed_baby_poms — mode: {mode} — schemas: {schemas} — POMs: {len(NEW_POMS)}'
        ))

        for schema in schemas:
            self._process_schema(schema, dry_run)

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(
                'DRY-RUN: no s\'ha escrit res. Torna a executar amb --no-dry-run per aplicar.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS('Fet.'))

    # ──────────────────────────────────────────────────────────────────────
    def _process_schema(self, schema, dry_run):
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO(f'━━━ schema: {schema} ━━━'))

        with schema_context(schema):
            from fhort.pom.models import POMGlobal, POMMaster, POMCategory

            is_tenant = schema != 'public'

            pg_new = pg_exist = 0
            for row in NEW_POMS:
                exists = POMGlobal.objects.filter(codi=row['codi']).exists()
                if exists:
                    pg_exist += 1
                    self.stdout.write(f"  [=] POMGlobal {row['codi']} ja existeix — update_or_create (no destructiu)")
                else:
                    pg_new += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"  [+] POMGlobal {row['codi']}  {row['nom_en']!r:24} → categoria {row['categoria']!r}  abbr={row['abbreviation']!r}"
                    ))
            self.stdout.write(f'  → POMGlobal: +{pg_new} nous (={pg_exist} ja hi eren) · total actual={POMGlobal.objects.count()}')

            # POMMaster només al tenant (public no en té; count=0).
            if is_tenant:
                cat_by_codi = {c.codi: c for c in POMCategory.objects.filter(actiu=True)}
                pm_new = pm_exist = 0
                cat_missing = set()
                for row in NEW_POMS:
                    cat = cat_by_codi.get(row['categoria'])
                    if cat is None:
                        cat_missing.add(row['categoria'])
                    # existència real només si el POMGlobal ja existeix
                    pg = POMGlobal.objects.filter(codi=row['codi']).first()
                    pm_exists = bool(pg) and POMMaster.objects.filter(pom_global=pg).exists()
                    if pm_exists:
                        pm_exist += 1
                    else:
                        pm_new += 1
                        cat_codi = cat.codi if cat else '∅(MISSING)'
                        self.stdout.write(
                            f"        [+] POMMaster {row['codi']} → codi_client={row['abbreviation']!r:10} categoria={cat_codi!r}"
                        )
                self.stdout.write(f'  → POMMaster (tenant): +{pm_new} nous (={pm_exist} ja hi eren)')
                if cat_missing:
                    self.stdout.write(self.style.ERROR(
                        f'  ⚠ Categories sense POMCategory match: {sorted(cat_missing)} — REVISAR'))

            if not dry_run:
                self._write_schema(POMGlobal, POMMaster, POMCategory, is_tenant)

    # ──────────────────────────────────────────────────────────────────────
    @transaction.atomic
    def _write_schema(self, POMGlobal, POMMaster, POMCategory, is_tenant):
        """Escriptura idempotent (només quan no és dry-run)."""
        for row in NEW_POMS:
            POMGlobal.objects.update_or_create(
                codi=row['codi'], defaults=_pomglobal_defaults(row),
            )
        if is_tenant:
            cat_by_codi = {c.codi: c for c in POMCategory.objects.filter(actiu=True)}
            for row in NEW_POMS:
                pg = POMGlobal.objects.get(codi=row['codi'])
                POMMaster.objects.update_or_create(
                    pom_global=pg,
                    defaults={
                        'codi_client': pg.abbreviation or pg.codi,
                        'nom_client': pg.nom_en,
                        'actiu': True,
                        'categoria': cat_by_codi.get(row['categoria']),
                        'notes': '',
                    },
                )
