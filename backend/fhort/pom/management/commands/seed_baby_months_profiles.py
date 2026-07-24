"""
Sprint nadó-mesos · crea SizingProfiles per a BABY_MONTHS_COM:
targets Baby Girl/Boy/Unisex + Knit + Regular → rule set 'EU Knit Baby Months'.

NOTA (desviació de l'spec): SizingProfile.garment_type és OBLIGATORI (NOT NULL,
PROTECT). L'spec demanava garment_type=None, però petaria amb IntegrityError;
s'usa un GarmentType de nadó ACTIU (BABY_ONEPIECES) en lloc de null.

Idempotent (update_or_create per target+construction+size_system).

Run:  python manage.py seed_baby_months_profiles --schema=fhort
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

SIZE_SYSTEM_CODE = 'BABY_MONTHS_COM'
RULE_SET_NAME = 'EU Knit Baby Months'
TARGET_CODES = ['NEWBORN_GIRL', 'NEWBORN_BOY', 'NEWBORN_UNISEX']


class Command(BaseCommand):
    help = "Seed SizingProfiles de nadó-mesos (BABY_MONTHS_COM)."

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort',
                            help='Schema del tenant on escriure (default: fhort).')

    def handle(self, *args, **options):
        schema = options['schema']
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"seed_baby_months_profiles · schema={schema}"))
        with schema_context(schema):
            self._run()

    @transaction.atomic
    def _run(self):
        from fhort.pom.models import (
            SizeSystem, GradingRuleSet, ConstructionType, FitType, Target,
            GarmentType, SizingProfile,
        )

        try:
            ss = SizeSystem.objects.get(codi=SIZE_SYSTEM_CODE)
        except SizeSystem.DoesNotExist:
            raise CommandError(f"SizeSystem '{SIZE_SYSTEM_CODE}' no existeix.")
        try:
            rs = GradingRuleSet.objects.get(nom=RULE_SET_NAME, size_system=ss)
        except GradingRuleSet.DoesNotExist:
            raise CommandError(
                f"GradingRuleSet '{RULE_SET_NAME}' no existeix. "
                "Executa primer seed_baby_months_grading.")

        construction = (ConstructionType.objects.filter(codi='KNIT').first()
                        or ConstructionType.objects.filter(nom_en__icontains='knit').first())
        if construction is None:
            raise CommandError("ConstructionType 'KNIT' no trobat.")

        fit_type = (FitType.objects.filter(codi='REGULAR').first()
                    or FitType.objects.filter(nom_en__icontains='regular').first())
        if fit_type is None:
            raise CommandError("FitType 'REGULAR' no trobat.")

        # garment_type és obligatori (NOT NULL) → un actiu de nadó.
        garment_type = (GarmentType.objects.filter(codi_client='BABY_ONEPIECES', actiu=True).first()
                        or GarmentType.objects.filter(actiu=True, nom_en__icontains='baby').first())
        if garment_type is None:
            raise CommandError(
                "Cap GarmentType de nadó actiu trobat (garment_type és obligatori).")

        targets = list(Target.objects.filter(codi__in=TARGET_CODES))
        if not targets:
            raise CommandError(f"Cap Target trobat per {TARGET_CODES}.")

        for target in targets:
            sp, created = SizingProfile.objects.update_or_create(
                target=target, construction=construction, size_system=ss,
                defaults={
                    'grading_rule_set': rs,
                    'fit_type': fit_type,
                    'garment_type': garment_type,
                    'is_default': True,
                },
            )
            self.stdout.write(self.style.SUCCESS(
                f"{'Creat' if created else 'Actualitzat'} SizingProfile "
                f"id={sp.id} target={target.nom_en}"))
