"""
Sprint nadó-mesos · crea el GradingRuleSet 'EU Knit Baby Months' i les seves
GradingRule per al SizeSystem BABY_MONTHS_COM (talla base 0M-1M).

Idempotent (update_or_create). Les dades viuen al schema del tenant.

Run:  python manage.py seed_baby_months_grading --schema=fhort
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

SIZE_SYSTEM_CODE = 'BABY_MONTHS_COM'
BASE_SIZE_LABEL = '0M-1M'
RULE_SET_NAME = 'EU Knit Baby Months'

# (codi_client, logica, increment_cm)
RULES = [
    ('B',    'LINEAR', 1.0),
    ('BJ',   'LINEAR', 0.2),
    ('A.1',  'LINEAR', 1.0),
    ('A.2',  'LINEAR', 1.0),
    ('D.11', 'LINEAR', 1.5),
    ('D',    'LINEAR', 1.0),
    ('M',    'LINEAR', 4.0),
    ('L.3',  'LINEAR', 0.3),
    ('L.5',  'FIXED',  0.0),
    ('L.4',  'LINEAR', 0.2),
    ('K',    'LINEAR', 0.3),
    ('K.1',  'FIXED',  0.0),
    ('H.6',  'LINEAR', 0.5),
    ('G',    'LINEAR', 2.0),
    ('H',    'LINEAR', 0.5),
    ('H.11', 'LINEAR', 0.3),
    ('S.5',  'FIXED',  0.0),
    ('V.12', 'LINEAR', 0.5),
    ('D.20', 'LINEAR', 2.0),
    ('S.40', 'LINEAR', 0.5),
    ('S.39', 'LINEAR', 0.3),
    ('S.20', 'LINEAR', 0.5),
    ('S.19', 'LINEAR', 1.0),
    ('S.53', 'LINEAR', 0.5),
    ('S.11', 'LINEAR', 0.5),
    ('S.10', 'LINEAR', 1.0),
    ('S.56', 'FIXED',  0.0),
]


class Command(BaseCommand):
    help = "Seed GradingRuleSet 'EU Knit Baby Months' + regles per a BABY_MONTHS_COM."

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort',
                            help='Schema del tenant on escriure (default: fhort).')

    def handle(self, *args, **options):
        schema = options['schema']
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"seed_baby_months_grading · schema={schema}"))
        with schema_context(schema):
            self._run()

    @transaction.atomic
    def _run(self):
        from fhort.pom.models import (
            SizeSystem, SizeDefinition, GradingRuleSet, GradingRule, POMMaster,
        )

        # 1. Size system
        try:
            ss = SizeSystem.objects.get(codi=SIZE_SYSTEM_CODE)
        except SizeSystem.DoesNotExist:
            raise CommandError(f"SizeSystem '{SIZE_SYSTEM_CODE}' no existeix.")

        # 2. Talla base
        try:
            base_def = SizeDefinition.objects.get(size_system=ss, etiqueta=BASE_SIZE_LABEL)
        except SizeDefinition.DoesNotExist:
            raise CommandError(
                f"SizeDefinition '{BASE_SIZE_LABEL}' de {SIZE_SYSTEM_CODE} no existeix.")

        # 3. Rule set (idempotent)
        # PROVINENÇA: seed de catàleg propi de FHORT → CANONICAL (viatja a un tenant nou).
        rs, _ = GradingRuleSet.objects.update_or_create(
            nom=RULE_SET_NAME, size_system=ss,
            defaults={'actiu': True, 'version_number': 1,
                      'origen': GradingRuleSet.ORIGEN_CANONICAL},
        )

        # 4. Regles (talla_base és obligatori al model → base_def)
        created, skips = 0, []
        for codi, logica, increment in RULES:
            pm = POMMaster.objects.filter(codi_client=codi).first()
            if pm is None:
                skips.append(codi)
                self.stdout.write(self.style.WARNING(
                    f"  [skip] POM '{codi}' no trobat al catàleg"))
                continue
            GradingRule.objects.update_or_create(
                rule_set=rs, pom=pm,
                defaults={
                    'logica': logica,
                    'increment': increment,
                    'talla_base': base_def,
                    'actiu': True,
                },
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Creat GradingRuleSet id={rs.id} · {created} regles · {len(skips)} skips"))
        if skips:
            self.stdout.write(f"  skips: {', '.join(skips)}")
