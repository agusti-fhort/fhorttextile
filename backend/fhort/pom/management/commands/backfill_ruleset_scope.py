"""Backfill de l'ÀMBIT D'APLICABILITAT dels contenidors de client existents (sprint ÀMBIT, Fase C).

Migra els contenidors que van néixer amb la identitat d'ITEM ÚNIC (`garment_type_item`, llei
CONTENIDOR 2026-07-16 / migració 0039) a l'àmbit multi-node equivalent: **un item = àmbit d'un sol
node** (`RuleSetScopeNode(node_type=ITEM)`). Sense pèrdua: l'àmbit resultant expressa exactament el
que la identitat ja deia.

Contenidors SENSE `garment_type_item` (no se'n pot derivar l'àmbit): **NO s'inventa cap node**. Es
deixen sense àmbit i, per disseny, el matching hi fa FALLBACK al `garment_group` — exactament el
comportament d'avui (cap regressió). Es llisten al report per completar-los a mà des de la UI.
NOTA: el model `Watchpoint` s'ancora a un MODEL (FK obligatori), no a un GradingRuleSet → no és
representable un watchpoint de "contenidor sense àmbit"; per això es reporten aquí (i al doc).

Idempotent: un contenidor que JA té àmbit es SALTA (no es re-escriu ni es duplica). Tenant-scoped
(default fhort). DRY-RUN per defecte; `--commit` per escriure. Tot ORM.

    python manage.py backfill_ruleset_scope --schema fhort            # dry-run
    python manage.py backfill_ruleset_scope --schema fhort --commit   # escriu
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = "Backfill de l'àmbit (RuleSetScopeNode) des del garment_type_item dels contenidors. Dry-run per defecte."

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort', help='Schema del tenant (default: fhort).')
        parser.add_argument('--commit', action='store_true',
                            help='Escriu a la BD. Sense això: dry-run (default).')
        parser.add_argument('--dry-run', action='store_true',
                            help='No-op explícit (el dry-run ja és el comportament per defecte).')

    def handle(self, *args, **opts):
        with schema_context(opts['schema']):
            self._run(opts['commit'] and not opts['dry_run'], opts['schema'])

    def _run(self, commit, schema):
        from fhort.pom.models import GradingRuleSet, RuleSetScopeNode

        qs = GradingRuleSet.objects.filter(origen=GradingRuleSet.ORIGEN_CLIENT_RUN).order_by('id')
        total = qs.count()
        amb_scope_abans = (GradingRuleSet.objects
                           .filter(origen=GradingRuleSet.ORIGEN_CLIENT_RUN, scope_nodes__isnull=False)
                           .distinct().count())

        rows = []       # (pk, nom, resultat)
        n_fill = n_skip = n_noderiv = 0

        @transaction.atomic
        def execute():
            nonlocal n_fill, n_skip, n_noderiv
            sp = transaction.savepoint()

            for rs in qs.select_related('garment_group'):
                if rs.scope_nodes.exists():
                    rows.append((rs.pk, rs.nom, 'ja-té-àmbit'))
                    n_skip += 1
                    continue
                if not rs.garment_type_item_id:
                    rows.append((rs.pk, rs.nom, 'SENSE àmbit derivable (fallback garment_group; completar a mà)'))
                    n_noderiv += 1
                    continue
                RuleSetScopeNode.objects.create(
                    rule_set=rs, node_type=RuleSetScopeNode.NODE_ITEM,
                    garment_type_item_id=rs.garment_type_item_id)
                rows.append((rs.pk, rs.nom, f'àmbit ← ITEM:{rs.garment_type_item_id}'))
                n_fill += 1

            if commit:
                transaction.savepoint_commit(sp)
            else:
                transaction.savepoint_rollback(sp)

        execute()

        amb_scope_despres = (GradingRuleSet.objects
                             .filter(origen=GradingRuleSet.ORIGEN_CLIENT_RUN, scope_nodes__isnull=False)
                             .distinct().count())

        mode = 'COMMIT' if commit else 'DRY-RUN'
        self.stdout.write(f"\n=== backfill_ruleset_scope [{mode}] · schema={schema} ===")
        self.stdout.write(f"\n{'RS':<6} {'NOM':<34} RESULTAT")
        self.stdout.write('-' * 92)
        for pk, nom, res in rows:
            self.stdout.write(f"{pk:<6} {(nom or '')[:33]:<34} {res}")
        self.stdout.write('-' * 92)
        self.stdout.write(
            f"TOTALS: àmbit-omplert={n_fill} · ja-tenien={n_skip} · sense-derivable={n_noderiv} · "
            f"contenidors CLIENT_RUN={total}")
        self.stdout.write(
            f"AUDIT contenidors amb àmbit: abans={amb_scope_abans} · "
            f"{'després=' + str(amb_scope_despres) if commit else 'després(simulat)=' + str(amb_scope_abans + n_fill)}")
        if not commit:
            self.stdout.write("\n(dry-run: cap escriptura; tot revertit al savepoint. Afegeix --commit per escriure.)")
