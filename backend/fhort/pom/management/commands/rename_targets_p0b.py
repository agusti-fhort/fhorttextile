"""rename_targets_p0b — P0b (2026-07-24): renombra el vocabulari de targets als 3 schemas.

    BOY          → KID_BOY          GIRL         → KID_GIRL
    TODDLER_BOY  → BABY_BOY         TODDLER_GIRL → BABY_GIRL
    BABY_BOY     → NEWBORN_BOY      BABY_GIRL    → NEWBORN_GIRL
    BABY_UNISEX  → NEWBORN_UNISEX
    MAN / WOMAN / TEEN_* / UNISEX_ADULT / MATERNITY: SENSE CANVI.

PER QUÈ ÉS SEGUR: cap FK apunta a `codi`. Els tres referrers (SizingProfile.target FK,
SizeSystem.targets M2M, GradingRuleSet.targets M2M) apunten a `id`. Això és un rename de
VALOR dins d'una columna, no una re-identificació: cap fila penjada, cap CASCADE.

PER QUÈ CAL ORDRE: el rename és una PERMUTACIÓ amb col·lisions (BABY_GIRL és alhora origen
i destí). `codi` és UNIQUE → un rename directe xocaria. Es fa en 2 temps dins d'UNA
transacció: A/B mouen els que col·lisionen a `_TMP_*`, C renombra els lliures, D aterra
els temporals. Si res falla, cap schema queda a mitges.

DRY-RUN PER DEFECTE. Cal `--apply` per escriure.

    manage.py rename_targets_p0b                    # dry-run als 3 schemas
    manage.py rename_targets_p0b --apply            # aplica
    manage.py rename_targets_p0b --schemas public   # només un schema
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

# codi_vell → (codi_nou, nom_en, nom_cat, nom_es)
RENAMES = {
    'BOY':          ('KID_BOY',        'Kid Boy',        'Nen',         'Niño'),
    'GIRL':         ('KID_GIRL',       'Kid Girl',       'Nena',        'Niña'),
    'TODDLER_BOY':  ('BABY_BOY',       'Baby Boy',       'Baby nen',    'Baby niño'),
    'TODDLER_GIRL': ('BABY_GIRL',      'Baby Girl',      'Baby nena',   'Baby niña'),
    'BABY_BOY':     ('NEWBORN_BOY',    'Newborn Boy',    'Nadó nen',    'Bebé niño'),
    'BABY_GIRL':    ('NEWBORN_GIRL',   'Newborn Girl',   'Nadó nena',   'Bebé niña'),
    'BABY_UNISEX':  ('NEWBORN_UNISEX', 'Newborn Unisex', 'Nadó unisex', 'Bebé unisex'),
}
DESTINS = {new for (new, *_) in RENAMES.values()}
# Els que són alhora ORIGEN d'un rename i DESTÍ d'un altre: han de passar per temporal.
COLLISIONS = {old for old, (new, *_) in RENAMES.items() if new in RENAMES}
# BABY_* és alhora codi vell i codi nou, així que la seva PRESÈNCIA no diu res sobre si el
# rename ja s'ha fet. Els testimonis fiables són els codis que només viuen a UN dels dos
# vocabularis: KID_*/NEWBORN_* només existeixen DESPRÉS; BOY/GIRL/TODDLER_*/BABY_UNISEX
# només ABANS. Sense aquesta distinció el command no seria idempotent (una segona passada
# tornaria a moure BABY_*→NEWBORN_*, corrompent les dades).
TESTIMONIS_NOUS = DESTINS - set(RENAMES)
TESTIMONIS_VELLS = set(RENAMES) - DESTINS
TMP = '_TMP_'


class Command(BaseCommand):
    help = 'P0b: renombra els codis de Target als 3 schemas (dry-run per defecte).'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Escriu de veritat. Sense això només informa.')
        parser.add_argument('--schemas', nargs='+', default=['public', 'fhort', 'los'],
                            help='Schemas a tractar (per defecte: public fhort los).')

    def handle(self, *args, **opts):
        from fhort.pom.models import Target

        apply_ = opts['apply']
        mode = 'APLICANT' if apply_ else 'DRY-RUN (cap escriptura)'
        self.stdout.write(self.style.WARNING(f'== rename_targets_p0b — {mode} =='))

        for schema in opts['schemas']:
            self.stdout.write(f'\n-- schema {schema} --')
            with schema_context(schema):
                present = dict(Target.objects.values_list('codi', 'id'))
                if not present:
                    self.stdout.write('   (sense targets — res a fer)')
                    continue

                fet = sorted(TESTIMONIS_NOUS & present.keys())
                per_fer = sorted(TESTIMONIS_VELLS & present.keys())
                if fet and per_fer:
                    raise CommandError(
                        f'{schema}: estat MIXT — testimonis vells {per_fer} i nous {fet} '
                        f'conviuen. Atura\'t i mira-ho a mà.')
                if fet:
                    self.stdout.write(self.style.SUCCESS(
                        f'   ja renombrat (testimonis {fet}) — no-op'))
                    continue
                if not per_fer:
                    self.stdout.write('   (cap codi del vocabulari P0b — res a fer)')
                    continue

                pending = [c for c in RENAMES if c in present]

                for old in pending:
                    new = RENAMES[old][0]
                    via = f' (via {TMP}{new})' if old in COLLISIONS else ''
                    self.stdout.write(f'   {old:<14} → {new}{via}')

                if not apply_:
                    self.stdout.write(f'   [dry-run] {len(pending)} files es renombrarien')
                    continue

                with transaction.atomic():
                    # A/B — els que col·lisionen, a temporal (allibera el destí).
                    for old in pending:
                        if old in COLLISIONS:
                            Target.objects.filter(codi=old).update(codi=TMP + RENAMES[old][0])
                    # C — els que ja tenen el destí lliure, directes al codi + noms finals.
                    for old in pending:
                        if old not in COLLISIONS:
                            new, en, ca, es = RENAMES[old]
                            Target.objects.filter(codi=old).update(
                                codi=new, nom_en=en, nom_cat=ca, nom_es=es)
                    # D — els temporals aterren al codi + noms finals.
                    for old in pending:
                        if old in COLLISIONS:
                            new, en, ca, es = RENAMES[old]
                            Target.objects.filter(codi=TMP + new).update(
                                codi=new, nom_en=en, nom_cat=ca, nom_es=es)

                    leftovers = list(Target.objects.filter(codi__startswith=TMP)
                                     .values_list('codi', flat=True))
                    if leftovers:
                        raise CommandError(f'{schema}: temporals no aterrats {leftovers} — ROLLBACK')

                self.stdout.write(self.style.SUCCESS(f'   OK — {len(pending)} files renombrades'))

        if not apply_:
            self.stdout.write(self.style.WARNING('\nDRY-RUN. Torna-hi amb --apply per escriure.'))
