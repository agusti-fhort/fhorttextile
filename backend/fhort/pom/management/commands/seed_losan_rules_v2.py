"""Sembra de GradingRules LOSAN SS27 — Fase 1 · Part 3 (config v2, resolució per ALIAS).

Igual que seed_losan_rules (Part 2) però les regles porten `alias` (codi_client del client),
NO codi POMMaster. Resolució: CustomerPOMAlias(customer=LOS, client_code=alias) → POMMaster.
Prova l'alias tal qual i, si falla, variants de puntuació (C4↔C.4, SR6↔S.R6). Alias no resolt
(o àlies sense pom mapat) → NO crea la regla; la llista a l'informe.

Config: `fhort/pom/seed_data/grading_rules_losan_ss27_v2.json`. AFEGEIX 7 contenidors als de v1.
Convencions idèntiques a la v1 (motor NO tocat): logica LINEAR · talla_base = talla més petita
(ordre 1) · increment=increment_base · break per etiqueta (talla_break_pos=NULL).

Idempotent (update_or_create per rule_set+pom). GUARD: si dos àlies del MATEIX contenidor
resolen al MATEIX POM, es crea només el primer i es reporta la col·lisió (no overwrite silenciós).

    python manage.py seed_losan_rules_v2                # DRY-RUN
    python manage.py seed_losan_rules_v2 --no-dry-run   # escriu
"""
import json
import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import (GradingRuleSet, GradingRule, CustomerPOMAlias, SizeSystem, FitType)
from fhort.tasks.models import GarmentTypeItem, Customer
from fhort.pom.seed_data import losan_ss27 as CFG

JSON_PATH = Path(__file__).resolve().parents[2] / 'seed_data' / 'grading_rules_losan_ss27_v2.json'


def dec(v):
    return Decimal(str(v))


def alias_variants(a):
    """Alias tal qual + variants de puntuació."""
    out = [a, a.replace('.', '')]
    out.append(re.sub(r'^([A-Z]+)(\d)', r'\1.\2', a))         # C4 -> C.4, D11 -> D.11
    out.append(re.sub(r'^([A-Z])([A-Z]+)(\d)', r'\1.\2\3', a))  # SR6 -> S.R6
    seen = []
    for x in out:
        if x not in seen:
            seen.append(x)
    return seen


class Command(BaseCommand):
    help = 'Sembra GradingRules LOSAN SS27 v2 (resolució per alias del diccionari LOS).'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        schema = opts['schema']
        head = 'DRY-RUN (cap escriptura)' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(f'=== seed_losan_rules_v2 · schema={schema} · {head} ==='))

        data = json.loads(JSON_PATH.read_text(encoding='utf-8'))
        self.log, self.unresolved, self.collisions, self.pendents, self.per = [], [], [], [], []

        try:
            with schema_context(schema), transaction.atomic():
                self.los = Customer.objects.filter(codi=CFG.CUSTOMER_CODI).first()
                self.fit = FitType.objects.filter(codi=CFG.FIT_TYPE_CODI).first()
                if not self.los or not self.fit:
                    raise CommandError('Customer LOS o FitType REGULAR no existeix.')
                for c in data['contenidors']:
                    self._seed(c)
                    for p in c.get('sense_regla_pendents', []):
                        self.pendents.append((c['nom'], p.get('alias', '?'), p.get('motiu', '')))
                if dry:
                    transaction.set_rollback(True)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'STOP · {type(e).__name__}: {e}'))
            raise

        for line in self.log:
            self.stdout.write(line)
        self.stdout.write('\n── RECOMPTE PER CONTENIDOR ──')
        tc = tu = 0
        for nom, nc, nu, ns in self.per:
            tc += nc; tu += nu
            self.stdout.write(f'  {nom}: {nc} creades · {nu} actualitzades · {ns} skip')
        self.stdout.write(f'  TOTAL creades={tc} actualitzades={tu}')

        self.stdout.write(f'\n── ALIES NO RESOLTS (no sembrats): {len(self.unresolved)} ──')
        for nom, alias, af in self.unresolved:
            self.stdout.write(f'  {nom} · alias {alias!r} (fitxa {af}) — sense POM al diccionari LOS')

        self.stdout.write(f'\n── COL·LISIONS INTRA-CONTENIDOR (2n àlies→mateix POM, no creat): {len(self.collisions)} ──')
        for nom, alias, pom, first in self.collisions:
            self.stdout.write(f'  {nom} · alias {alias!r} → POM {pom!r} ja ocupat per {first!r} (skip)')

        self.stdout.write(f'\n── PENDENTS (sense_regla_pendents del JSON): {len(self.pendents)} ──')
        for nom, alias, motiu in self.pendents:
            self.stdout.write(f'  {nom} · {alias} · {motiu}')

        self.stdout.write(self.style.SUCCESS(f'\n=== FET ({head}) ==='))

    def _resolve(self, alias):
        for v in alias_variants(alias):
            al = CustomerPOMAlias.objects.filter(
                customer=self.los, client_code=v, pom__isnull=False).first()
            if al:
                return al.pom, v
        return None, None

    def _seed(self, c):
        ss = SizeSystem.objects.filter(codi=c['size_system']).first()
        it = GarmentTypeItem.objects.filter(code=c['item']).first()
        if not ss or not it:
            raise CommandError(f'SizeSystem/Item inexistent per {c["nom"]}.')
        rs = GradingRuleSet.objects.filter(
            customer=self.los, size_system=ss, garment_type_item=it, fit_type=self.fit,
            origen=GradingRuleSet.ORIGEN_CLIENT_RUN).first()
        if not rs:
            raise CommandError(f'Contenidor no trobat: {c["nom"]} (cal seed_losan_ss27 abans).')
        base = ss.talles.order_by('ordre').first()
        if not base:
            raise CommandError(f'SizeSystem {c["size_system"]} sense talles.')
        break_label = c.get('talla_break_label')

        seen = {}   # pom.codi_client -> alias que l'ha ocupat en aquest contenidor
        nc = nu = ns = 0
        for r in c['regles']:
            alias = r['alias']
            pom, used = self._resolve(alias)
            if not pom:
                self.unresolved.append((c['nom'], alias, r.get('alias_fitxa', '?')))
                ns += 1
                continue
            if pom.codi_client in seen:
                self.collisions.append((c['nom'], alias, pom.codi_client, seen[pom.codi_client]))
                ns += 1
                continue
            seen[pom.codi_client] = alias
            ib = dec(r['increment_base'])
            has_break = 'increment_break' in r
            defaults = {
                'talla_base': base,
                'logica': GradingRule.LOGICA_LINEAR,
                'increment': ib,
                'increment_base': ib,
                'increment_break': (dec(r['increment_break']) if has_break else None),
                'talla_break_label': (break_label if has_break else None),
                'talla_break_pos': None,
                'valors_step': None,
                'actiu': True,
            }
            _, created = GradingRule.objects.update_or_create(rule_set=rs, pom=pom, defaults=defaults)
            nc += int(created)
            nu += int(not created)
        self.log.append(
            f'  [{c["nom"]}] ss={c["size_system"]} base={base.etiqueta!r} break={break_label!r} '
            f'→ {nc} creades, {nu} actualitzades, {ns} skip')
        self.per.append((c['nom'], nc, nu, ns))
