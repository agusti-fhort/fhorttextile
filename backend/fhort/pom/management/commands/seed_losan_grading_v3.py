"""Re-sembra grading v3 LOSAN (PAS 3) — fases delete / rename / seed.

--dry-run per defecte. Config a `fhort/pom/seed_data/losan_grading_v3.py` + JSONs de regles.
Motor NO tocat. Idempotent.

    python manage.py seed_losan_grading_v3 --phase delete [--no-dry-run]
    python manage.py seed_losan_grading_v3 --phase rename [--no-dry-run]
    python manage.py seed_losan_grading_v3 --phase seed   [--no-dry-run]
"""
import json
import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from django_tenants.utils import schema_context
from fhort.pom.models import (GradingRuleSet, GradingRule, RuleSetScopeNode, SizingProfile,
                              SizeSystem, GarmentGroup, GarmentType, ConstructionType, FitType,
                              Target, CustomerPOMAlias, POMMaster)
from fhort.tasks.models import Customer, GarmentTypeItem
from fhort.pom.seed_data import losan_grading_v3 as CFG

SEED_DIR = Path(__file__).resolve().parents[2] / 'seed_data'


def variants(a):
    o = [a, a.replace('.', ''), re.sub(r'^([A-Z]+)(\d)', r'\1.\2', a),
         re.sub(r'^([A-Z])([A-Z]+)(\d)', r'\1.\2\3', a)]
    s = []
    for x in o:
        if x not in s:
            s.append(x)
    return s


def dec(v):
    return Decimal(str(v))


class Command(BaseCommand):
    help = 'Re-sembra grading v3 LOSAN (delete/rename/seed).'

    def add_arguments(self, parser):
        parser.add_argument('--phase', required=True, choices=['delete', 'rename', 'seed'])
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        self.dry = not opts['no_dry_run']
        head = 'DRY-RUN' if self.dry else 'ESCRIVINT'
        phase = opts['phase']
        self.stdout.write(self.style.WARNING(f'=== seed_losan_grading_v3 · {phase} · {head} ==='))
        try:
            with schema_context(opts['schema']), transaction.atomic():
                self.los = Customer.objects.get(codi=CFG.CUSTOMER_CODI)
                {'delete': self._delete, 'rename': self._rename, 'seed': self._seed}[phase]()
                if self.dry:
                    transaction.set_rollback(True)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'STOP · {type(e).__name__}: {e}'))
            raise
        self.stdout.write(self.style.SUCCESS(f'=== FET ({head}) ==='))

    # ── DELETE (18 rulesets rebutjats) ───────────────────────────────────────
    def _delete(self):
        qs = GradingRuleSet.objects.filter(
            customer=self.los, origen='CLIENT_RUN', nom__endswith='SS27')
        from fhort.models_app.models import Model as ModelModel
        nreg = sum(r.regles.count() for r in qs)
        nmod = sum(ModelModel.objects.filter(grading_rule_set=r).count() for r in qs)
        nsp = sum(r.sizing_profiles.count() for r in qs)
        if nsp:
            raise CommandError(f'{nsp} SizingProfiles apunten als rulesets a esborrar — STOP (cas no previst).')
        self.stdout.write(f'  A esborrar: {qs.count()} rulesets · {nreg} GradingRule · '
                          f'{nmod} Models.grading_rule_set → NULL (SET_NULL)')
        for r in qs:
            self.stdout.write(f'    - [{r.id}] {r.nom} (regles={r.regles.count()})')
        qs.delete()  # GradingRule CASCADE; Model.grading_rule_set SET_NULL

    # ── RENAME (10 size systems) ─────────────────────────────────────────────
    def _rename(self):
        for codi, nom in CFG.RENAME_SYSTEMS.items():
            s = SizeSystem.objects.filter(codi=codi).first()
            if not s:
                self.stdout.write(f'  {codi}: NO EXISTEIX — skip')
                continue
            old = s.nom
            s.nom = nom
            s.save(update_fields=['nom'])
            self.stdout.write(f'  {codi}: {old!r} → {nom!r}')

    # ── SEED (14 cel·les) ────────────────────────────────────────────────────
    def _seed(self):
        self.v1 = json.loads((SEED_DIR / 'grading_rules_losan_ss27_v1.json').read_text(encoding='utf-8'))
        self.v2 = json.loads((SEED_DIR / 'grading_rules_losan_ss27_v2.json').read_text(encoding='utf-8'))
        self.delta = json.loads((SEED_DIR / 'grading_rules_v3_delta.json').read_text(encoding='utf-8'))
        fit = FitType.objects.get(codi=CFG.FIT_CODI)
        unresolved = []
        totals = []
        for c in CFG.CELLS:
            n_rules, unres = self._seed_cell(c, fit)
            unresolved += unres
            totals.append((c['nom'], n_rules))
        self.stdout.write('\n  ── RECOMPTE PER CEL·LA ──')
        tot = 0
        for nom, n in totals:
            tot += n
            self.stdout.write(f'    {nom}: {n} regles')
        self.stdout.write(f'  TOTAL regles: {tot} · rulesets: {len(CFG.CELLS)} · SizingProfiles: {len(CFG.CELLS)}')
        self.stdout.write(f'  ALIES NO RESOLTS (omesos): {unresolved or "CAP"}')

    def _rules_for(self, c):
        """Retorna [(alias, inc_base, inc_break_or_None)] segons la font de la cel·la."""
        src = c['source']
        out = []
        if 'delta' in src:
            bloc = next(b for b in self.delta['blocs'] if b['cella'] == src['delta'])
            for r in bloc['regles']:
                out.append((r['alias'], dec(r['inc']), None))
        elif 'v1_item' in src:
            cont = next(x for x in self.v1['contenidors_complets'] if x['item'] == src['v1_item'])
            for r in cont['regles']:
                ib = dec(r['increment_base'])
                brk = dec(r['increment_break']) if 'increment_break' in r else None
                out.append((r['alias_fitxa'], ib, brk))
        elif 'v2' in src:
            sysc, item = src['v2']
            cont = next(x for x in self.v2['contenidors']
                        if x['size_system'] == sysc and x['item'] == item)
            for r in cont['regles']:
                ib = dec(r['increment_base'])
                brk = dec(r['increment_break']) if 'increment_break' in r else None
                out.append((r['alias'], ib, brk))
        return out

    def _resolve(self, alias):
        for v in variants(alias):
            a = CustomerPOMAlias.objects.filter(customer=self.los, client_code=v, pom__isnull=False).first()
            if a:
                return a.pom
        return None

    def _seed_cell(self, c, fit):
        ss = SizeSystem.objects.get(codi=c['system'])
        constr = ConstructionType.objects.get(codi=c['construction'])
        base = ss.talles.order_by('ordre').first()
        if not base:
            raise CommandError(f'{c["system"]} sense talles.')
        tgts = list(Target.objects.filter(codi__in=c['targets']))
        if len(tgts) != len(c['targets']):
            raise CommandError(f'Targets inexistents a {c["nom"]}.')
        ptarget = Target.objects.get(codi=c['profile_target'])
        gtype = GarmentType.objects.get(codi_client=c['garment_type'])
        group = None
        if 'group' in c['scope']:
            group = GarmentGroup.objects.get(codi=c['scope']['group'])

        # GradingRuleSet (identitat per nom; item=NULL)
        rs, _ = GradingRuleSet.objects.update_or_create(
            nom=c['nom'],
            defaults={
                'origen': GradingRuleSet.ORIGEN_CLIENT_RUN, 'customer': self.los,
                'size_system': ss, 'garment_type_item': None, 'fit_type': fit,
                'construction': constr, 'garment_group': group, 'target': ptarget,
                'is_system_default': False, 'actiu': True,
            })
        rs.targets.set(tgts)

        # ABAST: scope nodes (items) o garment_group (ja assignat sobre)
        if 'items' in c['scope']:
            rs.scope_nodes.all().delete()
            for code in c['scope']['items']:
                it = GarmentTypeItem.objects.get(code=code)
                RuleSetScopeNode.objects.create(
                    rule_set=rs, node_type=RuleSetScopeNode.NODE_ITEM, garment_type_item=it)

        # Regles
        n = 0
        unres = []
        for alias, ib, brk in self._rules_for(c):
            pom = self._resolve(alias)
            if not pom:
                unres.append(f'{c["nom"]}:{alias}')
                continue
            GradingRule.objects.update_or_create(
                rule_set=rs, pom=pom,
                defaults={
                    'talla_base': base, 'logica': GradingRule.LOGICA_LINEAR,
                    'increment': ib, 'increment_base': ib,
                    'increment_break': brk,
                    'talla_break_label': (c['break'] if brk is not None else None),
                    'talla_break_pos': None, 'valors_step': None, 'actiu': True,
                })
            n += 1

        # SizingProfile (idempotent per grading_rule_set + identitat)
        SizingProfile.objects.get_or_create(
            grading_rule_set=rs, target=ptarget, garment_type=gtype,
            construction=constr, fit_type=fit, size_system=ss,
            defaults={'is_default': False, 'customer': self.los})

        scope_desc = c['scope'].get('group') or ('items:' + ','.join(c['scope']['items']))
        self.stdout.write(f'  [{c["nom"]}] ss={c["system"]} constr={c["construction"]} '
                          f'targets={c["targets"]} abast={scope_desc} break={c["break"]} → {n} regles')
        return n, unres
