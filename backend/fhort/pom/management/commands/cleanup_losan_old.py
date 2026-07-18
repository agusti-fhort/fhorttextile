"""Neteja de material LOSAN antic — Fase 1 · ADDENDUM (Agus 2026-07-18).

Esborra (commit propi, separat de la creació) el material LOS orfe que no encaixa amb
l'estructura de Fase 1. Per CLAU NATURAL. --dry-run per defecte: LLISTA què esborraria.

    python manage.py cleanup_losan_old               # DRY-RUN (llista)
    python manage.py cleanup_losan_old --no-dry-run  # esborra

Objectius (config a losan_ss27.py):
  - Rulesets orfes (origen=None, item=None) per nom + customer LOS  → amb les seves GradingRule.
  - Size systems GIRL_LOS_02/_03 (germans duplicats de GIRL_LOS_01) → amb les seves SizeDefinition.
    Ordre: rulesets PRIMER (104 penja de GIRL_LOS_03 amb FK PROTECT), systems DESPRÉS.

GUARD DUR: abans de cada esborrat s'escanegen TOTES les relacions inverses. Si n'hi ha
cap de VIVA fora de les cascades pròpies de l'objecte (regles/scope del ruleset; talles del
system, i les seves refs) → STOP, no esborra res (cas no previst).

LÍMITS: només material customer/àmbit LOS. Res de BRW/canònic/FTT.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import GradingRuleSet, SizeSystem, SizeDefinition
from fhort.pom.seed_data import losan_ss27 as CFG

# Relacions inverses "pròpies" (cascada natural de l'objecte) — NO són referències externes.
OWNED_RULESET = {'regles', 'scope_nodes'}
OWNED_SYSTEM = {'talles'}
# Relacions inverses de SizeDefinition que SÍ són externes i cal comprovar (una talla no pot
# estar en ús per una regla d'un altre ruleset ni ser talla base d'un item).
SIZEDEF_EXTERNAL = {'regles_base', 'base_for_items'}


def scan_refs(obj, owned):
    """Retorna {accessor: count} de relacions inverses NO-pròpies amb count>0."""
    refs = {}
    for rel in obj._meta.related_objects:
        acc = rel.get_accessor_name()
        if acc in owned:
            continue
        try:
            n = getattr(obj, acc).count()
        except Exception:
            n = -1  # relació cross-schema no resoluble → tractar com a sospitosa
        if n != 0:
            refs[acc] = n
    return refs


class Command(BaseCommand):
    help = 'Esborra material LOSAN antic orfe (rulesets 104/111, systems GIRL_LOS_02/_03).'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--only-clean', action='store_true',
                            help='OPCIÓ 2: esborra NOMÉS el net (ruleset 111 + GIRL_LOS_02); '
                                 '104/GIRL_LOS_03 queden com a deute. Re-verifica refs; nova ref → STOP.')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        only_clean = opts['only_clean']
        schema = opts['schema']
        rulesets_nom = CFG.ONLY_CLEAN_RULESETS_BY_NOM if only_clean else CFG.DELETE_RULESETS_BY_NOM
        systems_codi = CFG.ONLY_CLEAN_SIZE_SYSTEMS_BY_CODI if only_clean else CFG.DELETE_SIZE_SYSTEMS_BY_CODI
        head = 'DRY-RUN (cap esborrat)' if dry else 'ESBORRANT'
        scope = ' · ONLY-CLEAN (net)' if only_clean else ''
        self.stdout.write(self.style.WARNING(f'=== cleanup_losan_old · schema={schema} · {head}{scope} ==='))
        deleted = []

        try:
            with schema_context(schema), transaction.atomic():
                # ── 1. Rulesets (primer) ──
                for nom in rulesets_nom:
                    qs = GradingRuleSet.objects.filter(nom=nom, customer__codi=CFG.CUSTOMER_CODI)
                    if not qs.exists():
                        self.stdout.write(f'  [ruleset] "{nom}": no trobat (customer LOS) — skip')
                        continue
                    for rs in qs:
                        # límit dur: només LOS, mai canònic/BRW/FTT
                        if not rs.customer_id or rs.customer.codi != CFG.CUSTOMER_CODI:
                            raise CommandError(f'Ruleset "{nom}" NO és de LOS — límit violat, STOP.')
                        refs = scan_refs(rs, OWNED_RULESET)
                        n_regles = rs.regles.count()
                        n_scope = rs.scope_nodes.count()
                        if refs:
                            raise CommandError(
                                f'STOP · ruleset "{nom}" (id={rs.pk}) té referències VIVES externes: '
                                f'{refs}. Cas no previst — no esborro res.')
                        self.stdout.write(
                            f'  [ruleset] "{nom}" (id={rs.pk}, ss={rs.size_system and rs.size_system.codi}) '
                            f'→ ESBORRAR + {n_regles} regles + {n_scope} scope-nodes (cap ref externa)')
                        deleted.append(('GradingRuleSet', rs.pk, nom, f'{n_regles} regles'))
                        if not dry:
                            rs.delete()

                # ── 2. Size systems (després) ──
                for codi in systems_codi:
                    ss = SizeSystem.objects.filter(codi=codi).first()
                    if not ss:
                        self.stdout.write(f'  [system] {codi}: no trobat — skip')
                        continue
                    if ss.customer_codi != CFG.CUSTOMER_CODI:
                        raise CommandError(f'System {codi} customer_codi={ss.customer_codi!r} ≠ LOS — STOP.')
                    refs = scan_refs(ss, OWNED_SYSTEM)
                    # refs de les talles (nivell més profund): cap regla externa ni item base.
                    talla_refs = {}
                    for sd in ss.talles.all():
                        r = scan_refs(sd, set())
                        # de SizeDefinition només ens importen les externes conegudes
                        r = {k: v for k, v in r.items() if k in SIZEDEF_EXTERNAL}
                        if r:
                            talla_refs[sd.etiqueta] = r
                    n_talles = ss.talles.count()
                    if refs or talla_refs:
                        raise CommandError(
                            f'STOP · system {codi} (id={ss.pk}) té referències VIVES: '
                            f'system={refs} talles={talla_refs}. Cas no previst — no esborro res.')
                    self.stdout.write(
                        f'  [system] {codi} (id={ss.pk}) → ESBORRAR + {n_talles} talles (cap ref externa)')
                    deleted.append(('SizeSystem', ss.pk, codi, f'{n_talles} talles'))
                    if not dry:
                        ss.delete()

                if dry:
                    transaction.set_rollback(True)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'{type(e).__name__}: {e}'))
            raise

        self.stdout.write('\n── RESUM ESBORRAT ──')
        if not deleted:
            self.stdout.write('  (res a esborrar)')
        for model, pk, key, extra in deleted:
            self.stdout.write(f'  {model} id={pk} · {key} · {extra}')
        self.stdout.write(self.style.SUCCESS(
            f'=== FET ({head}) — {"simulat" if dry else "esborrat aplicat"} ==='))
