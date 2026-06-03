"""
Sprint Excel-Map · PAS 1 — extend the global POM catalog with 10 new POMs.

NON-DESTRUCTIVE and idempotent: uses update_or_create per codi (no .delete()).
The existing 106 POMGlobal / POMMaster / 365 GarmentPOMMap are left untouched.

Because `pom` lives in both SHARED and TENANT apps, pom_pomglobal exists in BOTH
the public schema and each tenant schema. The app resolves POMGlobal from the
tenant copy (POMMaster.pom_global FK), so we write the new POMGlobal to public
AND to the tenant, then clone one POMMaster per new POMGlobal in the tenant
(1:1, like reseed_tenant_fhort STEP A) without touching the existing rows.

Run:  python manage.py extend_pom_catalog            # default tenant 'fhort'
      python manage.py extend_pom_catalog --schema fhort
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import POMGlobal, POMMaster, POMCategory


# 10 new POMs. Measurement details PROPOSED for review (start/end/scope/state/etc.).
# Fields mirror POMGlobal. nom_es left blank, unitat 'cm', iso_ref '' as in the catalog.
NEW_POMS = [
    # ── 4 new concepts ──────────────────────────────────────────────────────
    {
        'codi': 'POM-029', 'nom_en': 'Front yoke length (center)',
        'nom_ca': 'Llargada de canesú (centre)', 'categoria': 'Upper body',
        'abbreviation': 'YK L',
        'descripcio_en': 'Measure vertically from the HPS (or neck seam) down to the yoke seam, along the center, garment laid flat.',
        'descripcio_ca': 'Mesura vertical des de HPS (o costura de coll) fins a la costura del canesú, pel centre. Peça plana.',
        'start_point': 'HPS / neck seam', 'end_point': 'Yoke seam', 'reference_point': 'Along center front/back',
        'scope': 'FULL', 'orientation': 'VERTICAL', 'state': 'FLAT', 'line': 'STRAIGHT', 'body_section': 'FRONT',
        'tol_prod_cm': 0.5, 'tol_samp_cm': 0.25,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    {
        'codi': 'POM-074', 'nom_en': 'Flounce width',
        'nom_ca': 'Ample de volant', 'categoria': 'Hem / Finish',
        'abbreviation': 'FLO W',
        'descripcio_en': 'Measure straight across the flounce/ruffle at its widest, relaxed and laid flat, edge to edge.',
        'descripcio_ca': "Mesura horitzontal del volant al seu punt més ample, relaxat i pla, de vora a vora.",
        'start_point': 'Flounce edge (left)', 'end_point': 'Flounce edge (right)', 'reference_point': 'Across flounce, relaxed and laid flat',
        'scope': 'HALF', 'orientation': 'HORIZONTAL', 'state': 'RELAXED', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 1.0, 'tol_samp_cm': 0.5,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    {
        'codi': 'POM-075', 'nom_en': 'Flounce extended',
        'nom_ca': 'Volant estès', 'categoria': 'Hem / Finish',
        'abbreviation': 'FLO EXT',
        'descripcio_en': 'Measure the flounce/ruffle fully extended (opened out flat), edge to edge.',
        'descripcio_ca': 'Mesura el volant totalment estès (obert i pla), de vora a vora.',
        'start_point': 'Flounce edge (left)', 'end_point': 'Flounce edge (right)', 'reference_point': 'Across flounce, fully extended',
        'scope': 'HALF', 'orientation': 'HORIZONTAL', 'state': 'STRETCHED', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 1.5, 'tol_samp_cm': 1.0,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    {
        'codi': 'POM-076', 'nom_en': 'Flounce location',
        'nom_ca': 'Posició del volant', 'categoria': 'Placement',
        'abbreviation': 'FLO POS',
        'descripcio_en': 'Measure the distance from the stated reference seam to the flounce attachment seam, along center front.',
        'descripcio_ca': "Mesura la distància des de la costura de referència fins a la costura d'unió del volant, pel centre davanter.",
        'start_point': 'Reference seam (waist/yoke/hem)', 'end_point': 'Flounce attachment seam', 'reference_point': 'Along center front',
        'scope': 'FULL', 'orientation': 'VERTICAL', 'state': 'FLAT', 'line': 'STRAIGHT', 'body_section': 'FRONT',
        'tol_prod_cm': 0.5, 'tol_samp_cm': 0.5,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': False,
    },
    # ── 6 state-pair completions (relaxed / stretched) ──────────────────────
    {
        'codi': 'POM-140', 'nom_en': 'Across front (stretched)',
        'nom_ca': 'Ample davanter mig (estès)', 'categoria': 'Upper body',
        'abbreviation': 'AC FR STR',
        'descripcio_en': 'Measure straight across the front from armhole edge to armhole edge, fully stretched, at a specified distance below HPS.',
        'descripcio_ca': "Mesura horitzontal del davanter de vora de sisa a vora de sisa, totalment estès, a distància especificada sota HPS.",
        'start_point': 'Armhole edge (left)', 'end_point': 'Armhole edge (right)', 'reference_point': 'Specified distance below HPS, fully stretched',
        'scope': 'FULL', 'orientation': 'HORIZONTAL', 'state': 'STRETCHED', 'line': 'STRAIGHT', 'body_section': 'FRONT',
        'tol_prod_cm': 1.0, 'tol_samp_cm': 0.5,
        'applies_woven': False, 'applies_knit': True, 'applies_swim': True,
    },
    {
        'codi': 'POM-141', 'nom_en': 'Across back (stretched)',
        'nom_ca': 'Ample posterior mig (estès)', 'categoria': 'Upper body',
        'abbreviation': 'AC BK STR',
        'descripcio_en': 'Measure straight across the back from armhole edge to armhole edge, fully stretched, at a specified distance below HPS.',
        'descripcio_ca': "Mesura horitzontal de l'esquena de vora de sisa a vora de sisa, totalment estès, a distància especificada sota HPS.",
        'start_point': 'Armhole edge (left)', 'end_point': 'Armhole edge (right)', 'reference_point': 'Specified distance below HPS, fully stretched',
        'scope': 'FULL', 'orientation': 'HORIZONTAL', 'state': 'STRETCHED', 'line': 'STRAIGHT', 'body_section': 'BACK',
        'tol_prod_cm': 1.0, 'tol_samp_cm': 0.5,
        'applies_woven': False, 'applies_knit': True, 'applies_swim': True,
    },
    {
        'codi': 'POM-142', 'nom_en': 'Hip width (relaxed)',
        'nom_ca': 'Ample de maluc (relaxat)', 'categoria': 'Lower body',
        'abbreviation': 'HI RLX',
        'descripcio_en': 'Measure straight across at the fullest hip, garment relaxed and laid flat, side seam to side seam.',
        'descripcio_ca': 'Mesura horitzontal al punt més ample del maluc, peça relaxada i plana, de costura lateral a costura lateral.',
        'start_point': 'Side seam', 'end_point': 'Side seam', 'reference_point': 'At fullest hip, relaxed',
        'scope': 'HALF', 'orientation': 'HORIZONTAL', 'state': 'RELAXED', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 1.0, 'tol_samp_cm': 0.5,
        'applies_woven': True, 'applies_knit': True, 'applies_swim': True,
    },
    {
        'codi': 'POM-143', 'nom_en': 'Hip width (stretched)',
        'nom_ca': 'Ample de maluc (estès)', 'categoria': 'Lower body',
        'abbreviation': 'HI STR',
        'descripcio_en': 'Measure straight across at the fullest hip, fully stretched, side seam to side seam.',
        'descripcio_ca': 'Mesura horitzontal al punt més ample del maluc, totalment estès, de costura lateral a costura lateral.',
        'start_point': 'Side seam', 'end_point': 'Side seam', 'reference_point': 'At fullest hip, fully stretched',
        'scope': 'HALF', 'orientation': 'HORIZONTAL', 'state': 'STRETCHED', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 1.5, 'tol_samp_cm': 1.0,
        'applies_woven': False, 'applies_knit': True, 'applies_swim': True,
    },
    {
        'codi': 'POM-144', 'nom_en': 'Leg opening (stretched)',
        'nom_ca': 'Obertura de cama (estès)', 'categoria': 'Lower body',
        'abbreviation': 'LEG OP STR',
        'descripcio_en': 'Measure straight across the leg opening, fully stretched, inseam edge to outseam edge.',
        'descripcio_ca': "Mesura horitzontal de la boca de cama, totalment estès, de vora d'entrecuix a vora exterior.",
        'start_point': 'Inseam edge', 'end_point': 'Outseam edge', 'reference_point': 'At leg opening, fully stretched',
        'scope': 'HALF', 'orientation': 'HORIZONTAL', 'state': 'STRETCHED', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 1.0, 'tol_samp_cm': 0.5,
        'applies_woven': False, 'applies_knit': True, 'applies_swim': True,
    },
    {
        'codi': 'POM-145', 'nom_en': 'Elastic waist (stretched)',
        'nom_ca': "Ample d'elàstic de cintura (estès)", 'categoria': 'Waistband',
        'abbreviation': 'EL WA STR',
        'descripcio_en': 'Measure straight across the elastic waistband, fully stretched, side seam to side seam.',
        'descripcio_ca': "Mesura horitzontal de l'elàstic de cintura, totalment estès, de costura lateral a costura lateral.",
        'start_point': 'Side seam', 'end_point': 'Side seam', 'reference_point': 'At elastic waistband, fully stretched',
        'scope': 'HALF', 'orientation': 'HORIZONTAL', 'state': 'STRETCHED', 'line': 'STRAIGHT', 'body_section': 'BOTH',
        'tol_prod_cm': 1.5, 'tol_samp_cm': 1.0,
        'applies_woven': False, 'applies_knit': True, 'applies_swim': True,
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
    help = 'PAS 1 · afegeix 10 POMGlobal nous (idempotent, no destructiu) + clona POMMaster al tenant'

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort',
                            help='Schema del tenant on clonar els POMMaster (default: fhort)')

    def handle(self, *args, **opts):
        tenant = opts['schema']
        schemas_global = ['public'] + ([tenant] if tenant != 'public' else [])

        # 1) POMGlobal a public + tenant (update_or_create per codi; mai delete).
        for sch in schemas_global:
            with schema_context(sch):
                with transaction.atomic():
                    created = updated = 0
                    for row in NEW_POMS:
                        _, was_created = POMGlobal.objects.update_or_create(
                            codi=row['codi'], defaults=_pomglobal_defaults(row),
                        )
                        created += int(was_created); updated += int(not was_created)
                self.stdout.write(f'  [{sch}] POMGlobal — creats: {created}, actualitzats: {updated}, '
                                  f'total ara: {POMGlobal.objects.count()}')

        # 2) POMMaster al tenant (1 per POMGlobal nou; update_or_create per pom_global; mai delete).
        with schema_context(tenant):
            with transaction.atomic():
                cat_by_codi = {c.codi: c for c in POMCategory.objects.filter(actiu=True)}
                pm_created = pm_updated = 0
                cat_missing = set()
                for row in NEW_POMS:
                    pg = POMGlobal.objects.get(codi=row['codi'])
                    cat = cat_by_codi.get(row['categoria'])
                    if cat is None:
                        cat_missing.add(row['categoria'])
                    _, was_created = POMMaster.objects.update_or_create(
                        pom_global=pg,
                        defaults={
                            'codi_client': pg.abbreviation or pg.codi,
                            'nom_client': pg.nom_en,
                            'actiu': True,
                            'categoria': cat,
                            'notes': '',
                        },
                    )
                    pm_created += int(was_created); pm_updated += int(not was_created)
            self.stdout.write(f'  [{tenant}] POMMaster — creats: {pm_created}, actualitzats: {pm_updated}, '
                              f'total ara: {POMMaster.objects.count()}')
            if cat_missing:
                self.stdout.write(self.style.WARNING(
                    f'  Categories sense POMCategory match al tenant: {sorted(cat_missing)}'))

        self.stdout.write(self.style.SUCCESS(f'\n✓ Catàleg ampliat amb {len(NEW_POMS)} POMs (idempotent).'))
