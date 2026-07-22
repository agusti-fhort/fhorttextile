"""PROPOSTES d'àmbit (RuleSetScopeNode) derivades dels MODELS REALS que usen cada contenidor.

P4 del paquet ITEM-PLANTILLA (D-CONS, 2026-07-22). Material de treball per a la sessió amb la
Montse: l'eina proposa, la decisió node a node és humana (criteri de domini).

═══ PER QUÈ CAL, TENINT `backfill_ruleset_scope` ═══

Són GERMANS, no duplicats — el que canvia és la FONT:

  · `backfill_ruleset_scope` deriva l'àmbit de la IDENTITAT (`GradingRuleSet.garment_type_item`).
    És exacte i sense pèrdua... quan la identitat existeix. Al schema `fhort` només **1 ruleset de
    45** la té informada → per als altres 44 no pot fer res, i el seu propi docstring ho diu:
    "NO s'inventa cap node. Es llisten al report per completar-los a mà des de la UI."

  · aquesta comanda deriva l'àmbit de l'ÚS REAL: quins `garment_type_item` tenen els MODELS que
    apunten al contenidor. És exactament "completar-los a mà", però amb l'evidència ja recollida.

La diagnosi va provar que el backfill de la identitat en forma literal és IMPOSSIBLE: 13 dels 20
contenidors LOSAN serveixen un CONJUNT d'items, no un item — i una FK singular no ho pot
representar. L'àmbit multi-node sí. D'aquí que la proposta sigui sempre de nodes ITEM (N per
contenidor), mai un valor per a la identitat.

═══ QUÈ NO FA ═══

  · NO toca `GradingRuleSet.garment_type_item` (la IDENTITAT i `uniq_client_container_identity`
    queden intactes: això és NOMÉS disponibilitat).
  · NO toca els contenidors que JA tenen àmbit — ni per completar-lo. Qui ja té nodes, els té per
    decisió; sobreescriure-la seria inventar-se-la.
  · NO proposa res per als contenidors sense cap model: no hi ha evidència, i el silenci és la
    resposta honesta. Es llisten a part perquè es vegin.
  · NO escriu res sense `--apply`.

    python manage.py seed_scope_nodes_proposals                    # dry-run (default)
    python manage.py seed_scope_nodes_proposals --schema los
    python manage.py seed_scope_nodes_proposals --apply            # escriu els nodes ITEM
    python manage.py seed_scope_nodes_proposals --min-models 3     # només el que tingui prou aval
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context


class Command(BaseCommand):
    help = ("Proposa nodes d'àmbit ITEM per als contenidors amb regles i sense àmbit, derivats "
            "dels garment_type_item dels models que els usen. Dry-run per defecte.")

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort', help='Schema del tenant (default: fhort).')
        parser.add_argument('--apply', action='store_true',
                            help='Escriu els nodes proposats. Sense això: dry-run (default).')
        parser.add_argument('--min-models', type=int, default=1,
                            help='Nombre mínim de models que han d’avalar un item (default: 1).')

    def handle(self, *args, **opts):
        with schema_context(opts['schema']):
            self._run(opts['schema'], opts['apply'], opts['min_models'])

    def _run(self, schema, apply, min_models):
        from fhort.models_app.models import Model
        from fhort.pom.models import GradingRuleSet, RuleSetScopeNode
        from fhort.tasks.models import GarmentTypeItem

        w = self.stdout.write

        # Candidats: AMB regles (un contenidor buit no és assignable — R5/`amb_regles=1` del picker)
        # i SENSE cap node d'àmbit. Els que ja en tenen no es toquen mai.
        candidats = (GradingRuleSet.objects
                     .filter(regles__isnull=False, scope_nodes__isnull=True)
                     .distinct().order_by('id'))
        ja_amb_ambit = (GradingRuleSet.objects
                        .filter(scope_nodes__isnull=False).distinct().count())

        w('')
        w(f"╔══ PROPOSTES D'ÀMBIT · schema {schema!r} · "
          f"{'APPLY (escriu)' if apply else 'DRY-RUN (no escriu res)'} ══")
        w(f"║  contenidors amb àmbit ja definit (INTOCABLES): {ja_amb_ambit}")
        w(f"║  candidats (amb regles, sense àmbit):           {candidats.count()}")
        w(f"║  llindar d'aval: ≥ {min_models} model(s) per item")
        w('╚' + '═' * 66)

        amb_proposta, sense_evidencia, nodes_totals = [], [], 0

        for rs in candidats:
            models_rs = (Model.objects
                         .filter(grading_rule_set=rs, garment_type_item__isnull=False)
                         .values_list('garment_type_item_id', flat=True))
            compte = Counter(models_rs)
            proposats = sorted(
                ((iid, n) for iid, n in compte.items() if n >= min_models),
                key=lambda x: (-x[1], x[0]))

            n_models_total = Model.objects.filter(grading_rule_set=rs).count()
            if not proposats:
                sense_evidencia.append((rs, n_models_total))
                continue

            noms = dict(GarmentTypeItem.objects
                        .filter(pk__in=[i for i, _ in proposats])
                        .values_list('pk', 'code'))
            amb_proposta.append((rs, proposats, noms, n_models_total))
            nodes_totals += len(proposats)

        # ── El material de la sessió: contenidor → nodes proposats, amb l'aval ────────────
        if amb_proposta:
            w('')
            w('── AMB PROPOSTA ' + '─' * 50)
            for rs, proposats, noms, n_models_total in amb_proposta:
                cust = getattr(rs.customer, 'codi', None) or '—'
                ss = getattr(rs.size_system, 'codi', None) or '—'
                fit = getattr(rs.fit_type, 'codi', None) or '—'
                w('')
                w(f"  rs {rs.id} · {rs.nom}")
                w(f"      client={cust} · sistema={ss} · fit={fit} · "
                  f"regles={rs.regles.count()} · models={n_models_total}")
                for iid, n in proposats:
                    codi = noms.get(iid, '?')
                    w(f"      → ITEM {iid:<4} {codi:<24} avalat per {n} model(s)")

        # ── Sense evidència: es diuen, no es silencien ───────────────────────────────────
        if sense_evidencia:
            w('')
            w('── SENSE EVIDÈNCIA (cap proposta; decisió 100% humana) ' + '─' * 13)
            for rs, n_models_total in sense_evidencia:
                motiu = ('cap model l’usa' if n_models_total == 0
                         else f'{n_models_total} model(s), cap amb garment_type_item')
                w(f"  rs {rs.id:<5} {rs.nom[:46]:<46} {motiu}")

        w('')
        w(f"RESUM: {len(amb_proposta)} contenidor(s) amb proposta · {nodes_totals} node(s) ITEM · "
          f"{len(sense_evidencia)} sense evidència")

        if not apply:
            w('')
            w('DRY-RUN: no s’ha escrit res. Revisa node a node amb la Montse i, quan estigui '
              'validat, torna-hi amb --apply.')
            return

        creats = 0
        with transaction.atomic():
            for rs, proposats, _noms, _n in amb_proposta:
                for iid, _n_models in proposats:
                    _, nou = RuleSetScopeNode.objects.get_or_create(
                        rule_set=rs, node_type=RuleSetScopeNode.NODE_ITEM,
                        garment_type_item_id=iid)
                    creats += nou
        w('')
        w(f'APPLY: {creats} node(s) ITEM creat(s).')
