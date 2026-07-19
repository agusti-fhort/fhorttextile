"""PAS 2 recuperació master_delta — ESBORRAT ACOTAT dels 4 rulesets del delta (+ 90 regles + 4 profiles).

Motiu: la 1a sembra va quedar contaminada (5 regles a POM orfe/inactiu pel bug d'ordre del resolutor,
ja corregit). S'esborra el delta sencer per re-sembrar net. NO toca la PEÇA 0 (els POMs/àlies creats
són correctes i es reutilitzen): GradingRule.pom és PROTECT → esborrar regles NO esborra POMs.

GUARDS DURS (aborten la transacció si fallen):
  · exactament els 4 noms del delta · tots customer LOS · cap is_system_default · tots CLIENT_RUN
    (mai toca els 14 v3, ni ISO/canònic, ni BRW: se seleccionen NOMÉS per aquests 4 noms).
  · 0 Models dependents (grading_rule_set) — si n'hi ha, ABORTAR (evita SET_NULL silenciós).
    (GradedSpec penja de GradingVersion per-model → 0 models ⇒ 0 specs.)
  · recompte LOS rulesets: 19 → 15 (14 v3 + 1 legacy Kids Knit). Si no quadra → ABORTAR.

--dry-run per defecte.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import GradingRuleSet, GradingRule, SizingProfile
from fhort.models_app.models import Model
from fhort.tasks.models import Customer
from fhort.pom.seed_data import consolidate_pom_los as CFG

DELTA_NAMES = [
    'LOS Man Knit — Tops',
    'LOS Teen Girl Knit — Tops',
    'LOS Kids Boy Knit — Tops',
    'LOS Kids Girl Knit — Tops',
]
LOS_ABANS_ESPERAT = 19
LOS_DESPRES_ESPERAT = 15


class Command(BaseCommand):
    help = 'Esborra ACOTADAMENT els 4 rulesets del master_delta (recuperació). Guards durs.'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        head = 'DRY-RUN (cap escriptura)' if dry else 'ESBORRANT'
        self.stdout.write(self.style.WARNING(f'=== delete_master_delta_seed · {head} ==='))

        with schema_context(opts['schema']), transaction.atomic():
            los = Customer.objects.filter(codi=CFG.CUSTOMER_CODI).first()
            if not los:
                raise CommandError('Customer LOS no existeix.')
            rs = GradingRuleSet.objects.filter(nom__in=DELTA_NAMES)

            # ── GUARDS ──
            if rs.count() != len(DELTA_NAMES):
                raise CommandError(f'esperava {len(DELTA_NAMES)} rulesets, trobats {rs.count()} → ABORTAR')
            for r in rs:
                if r.customer_id != los.id:
                    raise CommandError(f'{r.nom!r}: NO és customer LOS → ABORTAR')
                if r.is_system_default:
                    raise CommandError(f'{r.nom!r}: is_system_default → ABORTAR')
                if r.origen != GradingRuleSet.ORIGEN_CLIENT_RUN:
                    raise CommandError(f'{r.nom!r}: origen {r.origen!r} ≠ CLIENT_RUN → ABORTAR')
            n_models = Model.objects.filter(grading_rule_set__in=rs).count()
            if n_models:
                raise CommandError(f'{n_models} Models depenen dels rulesets (SET_NULL silenciós) → ABORTAR')

            los_before = GradingRuleSet.objects.filter(customer=los).count()
            if los_before != LOS_ABANS_ESPERAT:
                raise CommandError(f'LOS rulesets abans={los_before} ≠ {LOS_ABANS_ESPERAT} esperat → ABORTAR')
            n_rules = GradingRule.objects.filter(rule_set__in=rs).count()
            n_prof = SizingProfile.objects.filter(grading_rule_set__in=rs).count()
            self.stdout.write(f'  a esborrar: {rs.count()} rulesets · {n_rules} regles · {n_prof} profiles')
            self.stdout.write(f'  LOS rulesets abans: {los_before}')
            for r in rs.order_by('nom'):
                self.stdout.write(f'    - {r.nom} (id={r.id})')

            # ── ESBORRAT (profiles PROTECT primer; després rulesets → regles+scope per CASCADE) ──
            SizingProfile.objects.filter(grading_rule_set__in=rs).delete()
            GradingRuleSet.objects.filter(nom__in=DELTA_NAMES).delete()

            los_after = GradingRuleSet.objects.filter(customer=los).count()
            self.stdout.write(f'  LOS rulesets després: {los_after} (esperat {LOS_DESPRES_ESPERAT})')
            if los_after != LOS_DESPRES_ESPERAT:
                raise CommandError(f'recompte després={los_after} ≠ {LOS_DESPRES_ESPERAT} → ABORTAR')

            if dry:
                transaction.set_rollback(True)
                self.stdout.write('  (dry-run: rollback, res esborrat)')

        self.stdout.write(self.style.SUCCESS(f'=== FET ({head}) ==='))
