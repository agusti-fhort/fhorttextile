"""Talla base de BRW-CATALEG-v3: XXS → S (decisió d'Agus, 05/08/2026).

La talla base de Brownie ÉS la S, mandatori. El ruleset del catàleg v3 declarava XXS.

⚠️ AIXÒ ÉS UN RE-ETIQUETATGE, NO UN RECÀLCUL. Cap valor es mou, i és important saber per
què abans de córrer-ho:

  · El motor NO llegeix `GradingRule.talla_base`. `_apply_rule` ancora a
    `Model.base_size_label` (pom/services.py:138, `escala_del_model`), i les regles es
    carreguen per `rule_set_id` indexades per `pom_id` (`_load_grading_rules`), sense mirar
    l'ancoratge. El propi codi ho diu: «mer metadata del seed» (pom/grading_utils.py:70-71).
  · Els 40 models del ruleset ja tenen `base_size_label='S'`, i graduen amb regles
    RESIDENTS (`ModelGradingRule`), que ni tan sols tenen camp `talla_base`.
  · Els valors desats a `BaseMeasurement` ja són els de la S, i els `GradedSpec` existents
    (6 models, 3 versions segellades) ja estan calculats des de la S i quadren.

O sigui: el XXS era metadata morta a 114 files. El que es corregeix és el que la UI ensenya
(GradingRuleSets.jsx) i l'avís del wizard d'importació (extraction_views.py:902), que
comparava la base del model amb aquesta àncora i cridava una divergència que no existia.

Diagnosi completa: sessió Patró A del 05/08/2026 (Q1-Q4).

Es localitza el ruleset pel NOM, no per id: els ids no coincideixen entre staging i PROD.
Guard: només toca les regles que encara són a la base antiga → idempotent. Si algun dia
alguna regla del conjunt té una altra base, es reporta i NO es toca.

    python manage.py fix_brownie_talla_base                # DRY-RUN (compta, rollback)
    python manage.py fix_brownie_talla_base --no-dry-run   # aplica + verifica
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import GradingRuleSet, GradingRule, SizeDefinition
from fhort.pom.seed_data import consolidate_pom_los as CFG

RULESET_NOM = 'BRW-CATALEG-v3'
BASE_ANTIGA = 'XXS'
BASE_NOVA = 'S'


class Command(BaseCommand):
    help = 'Re-etiqueta la talla_base de BRW-CATALEG-v3 de XXS a S (metadata; cap valor es mou).'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        head = 'DRY-RUN' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(f'=== fix_brownie_talla_base · {head} ==='))

        with schema_context(opts['schema']), transaction.atomic():
            rs = GradingRuleSet.objects.filter(nom=RULESET_NOM)
            if rs.count() != 1:
                raise CommandError(f'Ruleset ambigu o inexistent: {RULESET_NOM!r} (n={rs.count()})')
            rs = rs.first()

            newdef = SizeDefinition.objects.filter(
                size_system=rs.size_system, etiqueta=BASE_NOVA).first()
            if not newdef:
                raise CommandError(
                    f'{RULESET_NOM!r}: no hi ha SizeDefinition {BASE_NOVA!r} al size_system '
                    f'{rs.size_system and rs.size_system.codi}')

            rules = list(GradingRule.objects.filter(rule_set=rs).select_related('talla_base'))
            at_old = [r for r in rules
                      if r.talla_base and r.talla_base.etiqueta == BASE_ANTIGA]
            at_new = [r for r in rules if r.talla_base_id == newdef.id]
            other = [r for r in rules
                     if r.talla_base_id != newdef.id
                     and not (r.talla_base and r.talla_base.etiqueta == BASE_ANTIGA)]

            self.stdout.write(
                f'\n[{RULESET_NOM}] id={rs.id} · sys={rs.size_system and rs.size_system.codi} '
                f'· regles={len(rules)}')
            self.stdout.write(
                f'   a base {BASE_ANTIGA!r}: {len(at_old)} → passaran a {BASE_NOVA!r} '
                f'(id {newdef.id}) · ja a {BASE_NOVA!r}: {len(at_new)} · altres bases: '
                f'{len(other)} {[r.talla_base.etiqueta for r in other] if other else ""}')

            if not dry:
                n = GradingRule.objects.filter(
                    id__in=[r.id for r in at_old]).update(talla_base=newdef)
                still_old = GradingRule.objects.filter(
                    rule_set=rs, talla_base__etiqueta=BASE_ANTIGA).count()
                not_new = GradingRule.objects.filter(rule_set=rs).exclude(
                    talla_base=newdef).count()
                self.stdout.write(self.style.SUCCESS(
                    f'   ACTUALITZADES: {n} · VERIFICACIÓ regles a {BASE_ANTIGA!r}: '
                    f'{still_old} · regles NO a {BASE_NOVA!r}: {not_new}'))
                if still_old or not_new:
                    raise CommandError(
                        f'Verificació FALLIDA: queden {still_old} regles a {BASE_ANTIGA!r} i '
                        f'{not_new} fora de {BASE_NOVA!r}. Rollback.')
            else:
                transaction.set_rollback(True)
                self.stdout.write('\n  (dry-run: rollback, res tocat)')

        self.stdout.write(self.style.SUCCESS('=== FET ==='))
