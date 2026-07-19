"""Sembra de GradingRules LOSAN SS27 — Fase 1 · Part 2 (addendum B3-estès).

Sembra les regles per-POM dels contenidors COMPLETS i PARCIALS de
`fhort/pom/seed_data/grading_rules_losan_ss27_v1.json` sobre els GradingRuleSet ja creats
(resolts per IDENTITAT NATURAL: customer LOS + size_system + garment_type_item + fit REGULAR).

Convencions (calcades del precedent LOS ruleset 104, motor NO tocat):
  - logica = LINEAR sempre.
  - talla_base = la talla MÉS PETITA (ordre 1) del size_system del contenidor. Els increments
    del JSON s'expressen acumulatius des de la talla petita cap amunt (break parcial).
    (⚠️ La talla base/sample formal està pendent de Montse; s'usa la convenció LOS existent.)
  - increment_base del JSON. Si la regla porta increment_break → també, amb talla_break_label
    del contenidor (el motor resol el break PER ETIQUETA contra el run del model; talla_break_pos
    queda NULL, és cache opcional no usat pel motor canònic — pom/services.py:747).
  - increment (escalar legacy) = increment_base (convenció 104; el motor canònic no el llegeix
    quan increment_base està poblat, però es manté coherent per a grading_utils).

Validació: cada codi POMMaster es resol contra BD. Codi inexistent → NO crea la regla; la
llista a l'informe (POMs no resolts). Les "sense_regla_pendents" NO es sembren (a l'informe).

Idempotent (update_or_create per clau natural rule_set+pom). --dry-run per defecte.

    python manage.py seed_losan_rules                # DRY-RUN
    python manage.py seed_losan_rules --no-dry-run   # escriu
"""
import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import (GradingRuleSet, GradingRule, POMMaster, SizeSystem,
                              SizeDefinition, FitType)
from fhort.tasks.models import GarmentTypeItem, Customer
from fhort.pom.seed_data import losan_ss27 as CFG

JSON_PATH = Path(__file__).resolve().parents[2] / 'seed_data' / 'grading_rules_losan_ss27_v1.json'


def dec(v):
    return Decimal(str(v))


class Command(BaseCommand):
    help = 'Sembra GradingRules LOSAN SS27 (contenidors complets + parcials del JSON).'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        schema = opts['schema']
        head = 'DRY-RUN (cap escriptura)' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(f'=== seed_losan_rules · schema={schema} · {head} ==='))

        data = json.loads(JSON_PATH.read_text(encoding='utf-8'))
        contenidors = data['contenidors_complets'] + data['contenidors_parcials']

        self.log = []
        self.unresolved = []      # (contenidor_nom, alias_fitxa, pom_code)
        self.pendents = []        # (contenidor_nom, alias_fitxa, motiu)
        self.per_contenidor = []  # (nom, n_creades, n_actualitzades, n_skip)

        try:
            with schema_context(schema), transaction.atomic():
                los = Customer.objects.filter(codi=CFG.CUSTOMER_CODI).first()
                fit = FitType.objects.filter(codi=CFG.FIT_TYPE_CODI).first()
                if not los or not fit:
                    raise CommandError('Customer LOS o FitType REGULAR no existeix.')

                for c in contenidors:
                    self._seed_contenidor(c, los, fit, dry)

                # pendents (només registre, no es sembren)
                for c in contenidors:
                    for p in c.get('sense_regla_pendents', []):
                        self.pendents.append((c['nom'], p.get('alias_fitxa', '?'), p.get('motiu', '')))

                if dry:
                    transaction.set_rollback(True)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'STOP · {type(e).__name__}: {e}'))
            raise

        # ── informe ──
        for line in self.log:
            self.stdout.write(line)
        self.stdout.write('\n── RECOMPTE PER CONTENIDOR ──')
        total = 0
        for nom, nc, nu, ns in self.per_contenidor:
            total += nc + nu
            self.stdout.write(f'  {nom}: {nc} creades · {nu} actualitzades · {ns} skip')
        self.stdout.write(f'  TOTAL regles sembrades (creades+actualitzades): {total}')

        self.stdout.write('\n── POMs NO RESOLTS (no sembrats) ──')
        if not self.unresolved:
            self.stdout.write('  (cap — tots els codis POMMaster resolts)')
        for nom, alias, code in self.unresolved:
            self.stdout.write(f'  {nom} · alias {alias} · POM {code!r} INEXISTENT')

        self.stdout.write(f'\n── PENDENTS (sense_regla_pendents, NO sembrats): {len(self.pendents)} ──')
        for nom, alias, motiu in self.pendents:
            self.stdout.write(f'  {nom} · {alias} · {motiu}')

        self.stdout.write(self.style.SUCCESS(f'\n=== FET ({head}) ==='))

    def _seed_contenidor(self, c, los, fit, dry):
        ss = SizeSystem.objects.filter(codi=c['size_system']).first()
        if not ss:
            raise CommandError(f'SizeSystem {c["size_system"]} no existeix ({c["nom"]}).')
        item = GarmentTypeItem.objects.filter(code=c['item']).first()
        if not item:
            raise CommandError(f'Item {c["item"]} no existeix ({c["nom"]}).')
        rs = GradingRuleSet.objects.filter(
            customer=los, size_system=ss, garment_type_item=item, fit_type=fit,
            origen=GradingRuleSet.ORIGEN_CLIENT_RUN).first()
        if not rs:
            raise CommandError(f'Contenidor no trobat per identitat: LOS/{c["size_system"]}/'
                               f'{c["item"]}/REGULAR ({c["nom"]}). Cal executar seed_losan_ss27 abans.')
        # talla_base = talla més petita (ordre mínim)
        base = ss.talles.order_by('ordre').first()
        if not base:
            raise CommandError(f'SizeSystem {c["size_system"]} sense talles ({c["nom"]}).')
        break_label = c.get('talla_break_label')

        nc = nu = ns = 0
        for r in c['regles']:
            code = r['pom']
            pom = POMMaster.objects.filter(codi_client=code).first()
            if not pom:
                self.unresolved.append((c['nom'], r.get('alias_fitxa', '?'), code))
                ns += 1
                continue
            ib = dec(r['increment_base'])
            has_break = 'increment_break' in r
            ibreak = dec(r['increment_break']) if has_break else None
            defaults = {
                'talla_base': base,
                'logica': GradingRule.LOGICA_LINEAR,
                'increment': ib,                       # convenció 104
                'increment_base': ib,
                'increment_break': ibreak,
                'talla_break_label': (break_label if has_break else None),
                'talla_break_pos': None,               # cache opcional, motor resol per etiqueta
                'valors_step': None,
                'actiu': True,
            }
            obj, created = GradingRule.objects.update_or_create(
                rule_set=rs, pom=pom, defaults=defaults)
            if created:
                nc += 1
            else:
                nu += 1
        self.log.append(
            f'  [{c["nom"]}] ss={c["size_system"]} base={base.etiqueta!r} '
            f'break={break_label!r} → {nc} creades, {nu} actualitzades, {ns} skip')
        self.per_contenidor.append((c['nom'], nc, nu, ns))
