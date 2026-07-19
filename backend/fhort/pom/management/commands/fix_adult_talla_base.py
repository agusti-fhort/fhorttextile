"""Correcció de la talla_base dels rulesets adults LOS (convenció confirmada per la Montse, 19/07).

Convenció: talla base = la més petita a tots els mons, EXCEPTE HOME = M/42 i DONA = S/38. Tres cel·les
quedaven a la talla més petita i s'han de pujar a la talla de convenció:

    LOS Woman Knit — Tops       XS → S
    LOS Woman Woven — Bottoms   36 → 38
    LOS Man Woven — Bottoms     38 → 42

`talla_base` viu NOMÉS a `GradingRule` (FK a SizeDefinition, una per regla); el GradingRuleSet no en
té. Totes les regles d'un ruleset comparteixen la mateixa base → s'actualitzen totes. La nova base es
resol DINS del size_system del ruleset (coherència). Guard: només toca regles que encara són a la base
antiga. Les altres 11 cel·les (ja a la més petita) NO es toquen. Idempotent. `--dry-run` per defecte.

    python manage.py fix_adult_talla_base                # DRY-RUN (compta, rollback)
    python manage.py fix_adult_talla_base --no-dry-run   # aplica + verifica
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import GradingRuleSet, GradingRule, SizeDefinition
from fhort.pom.seed_data import consolidate_pom_los as CFG

# (nom del ruleset, etiqueta base ANTIGA esperada, etiqueta base NOVA de convenció)
CORRECCIONS = [
    ('LOS Woman Knit — Tops',     'XS', 'S'),
    ('LOS Woman Woven — Bottoms', '36', '38'),
    ('LOS Man Woven — Bottoms',   '38', '42'),
]


class Command(BaseCommand):
    help = 'Corregeix la talla_base dels rulesets adults LOS (convenció Montse).'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        head = 'DRY-RUN' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(f'=== fix_adult_talla_base · {head} ==='))

        with schema_context(opts['schema']), transaction.atomic():
            total_updated = 0
            for nom, old, new in CORRECCIONS:
                rs = GradingRuleSet.objects.filter(nom=nom)
                if rs.count() != 1:
                    raise CommandError(f'Ruleset ambigu o inexistent: {nom!r} (n={rs.count()})')
                rs = rs.first()
                newdef = SizeDefinition.objects.filter(size_system=rs.size_system, etiqueta=new).first()
                if not newdef:
                    raise CommandError(f'{nom!r}: no hi ha SizeDefinition {new!r} al size_system '
                                       f'{rs.size_system and rs.size_system.codi}')

                rules = list(GradingRule.objects.filter(rule_set=rs).select_related('talla_base'))
                at_old = [r for r in rules if r.talla_base and r.talla_base.etiqueta == old]
                at_new = [r for r in rules if r.talla_base_id == newdef.id]
                other = [r for r in rules
                         if r.talla_base_id != newdef.id and not (r.talla_base and r.talla_base.etiqueta == old)]

                self.stdout.write(f'\n[{nom}] id={rs.id} · sys={rs.size_system and rs.size_system.codi} · regles={len(rules)}')
                self.stdout.write(f'   a base {old!r}: {len(at_old)} → passaran a {new!r} (id {newdef.id}) · '
                                  f'ja a {new!r}: {len(at_new)} · altres bases: {len(other)} '
                                  f'{[r.talla_base.etiqueta for r in other] if other else ""}')

                if not dry:
                    n = GradingRule.objects.filter(id__in=[r.id for r in at_old]).update(talla_base=newdef)
                    total_updated += n
                    still_old = GradingRule.objects.filter(
                        rule_set=rs, talla_base__etiqueta=old).count()
                    not_new = GradingRule.objects.filter(rule_set=rs).exclude(talla_base=newdef).count()
                    self.stdout.write(self.style.SUCCESS(
                        f'   ACTUALITZADES: {n} · VERIFICACIÓ regles a {old!r}: {still_old} · '
                        f'regles NO a {new!r}: {not_new}'))

            if dry:
                transaction.set_rollback(True)
                self.stdout.write('\n  (dry-run: rollback, res tocat)')
            else:
                self.stdout.write(self.style.SUCCESS(f'\n  TOTAL regles actualitzades: {total_updated}'))

        self.stdout.write(self.style.SUCCESS('=== FET ==='))
