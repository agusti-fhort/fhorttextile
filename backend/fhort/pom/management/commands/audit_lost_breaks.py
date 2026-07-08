"""Auditoria READ-ONLY de possibles breaks perduts a GradingRuleSets persistits.

DIAGNOSI_ETIQUETES_TALLA_2026-07-08: una talla desalineada (XXL vs 2XL) es descartava i la regla
es derivava amb els deltes restants → un break a la talla perduda desapareixia i la regla degradava
a LINEAR en silenci. Els valors per talla NO es persisteixen, així que aquesta auditoria és
HEURÍSTICA (senyals estructurals), no una prova. NO corregeix res: només llista.

Senyals:
  - ALTA: el run té talles altes (2XL+) i CAP regla del ruleset té break, tot i haver-hi regles
    LINEAR → sospita que TOTS els breaks s'han perdut a l'alineació.
  - MITJANA: el ruleset SÍ té breaks (l'estructura de break existeix en aquest run) i, a més, hi ha
    regles LINEAR sense break → aquestes són candidates a haver perdut el seu break.
"""
import re
from django.core.management.base import BaseCommand
from django_tenants.utils import get_tenant_model, schema_context
from fhort.pom.size_labels import canonical_size_label

HIGH = re.compile(r'^[2-9]X[LS]$')  # forma canònica de talla alta: 2XL, 3XL, 2XS...


class Command(BaseCommand):
    help = ("Llista rulesets amb possibles breaks perduts (heurístic, read-only). "
            "Reporta rs104 i rs111 explícitament. No modifica res.")

    def add_arguments(self, parser):
        parser.add_argument('--schema', default=None,
                            help="Un sol tenant (per defecte, tots els no-public).")

    def handle(self, *args, **opts):
        from fhort.pom.models import GradingRuleSet, GradingRule
        TenantModel = get_tenant_model()
        schemas = ([opts['schema']] if opts['schema'] else
                   list(TenantModel.objects.exclude(schema_name='public')
                        .values_list('schema_name', flat=True)))
        SEMPRE = {104, 111}

        for schema in schemas:
            with schema_context(schema):
                self.stdout.write(f"\n=== TENANT {schema} ===")
                sospitosos = 0
                # Els rulesets ISO sembrats (is_system_default) NO passen per l'extracció de
                # document → no els afecta la desalineació XXL/2XL; s'exclouen de la sospita (però
                # rs104/rs111 es reporten igual si cauen a SEMPRE).
                seeds_exclosos = GradingRuleSet.objects.filter(is_system_default=True).count()
                for rs in GradingRuleSet.objects.all().order_by('id'):
                    if rs.is_system_default and rs.id not in SEMPRE:
                        continue
                    run = (list(rs.size_system.talles.order_by('ordre')
                                .values_list('etiqueta', flat=True))
                           if rs.size_system_id else [])
                    rules = list(GradingRule.objects.filter(rule_set=rs).select_related('pom'))
                    lin_nb = [r for r in rules
                              if r.logica == 'LINEAR' and r.increment_break is None]
                    n_break = sum(1 for r in rules if r.increment_break is not None)
                    high = [s for s in run if HIGH.match(canonical_size_label(s))]

                    susp = None
                    if high and n_break == 0 and lin_nb:
                        susp = (f"ALTA — run amb talles altes {high} i CAP break; "
                                f"{len(lin_nb)} regles LINEAR (possible pèrdua total de breaks)")
                    elif run and n_break > 0 and lin_nb:
                        susp = (f"MITJANA — ruleset amb {n_break} breaks; "
                                f"{len(lin_nb)} regles LINEAR sense break són candidates")

                    if not susp and rs.id not in SEMPRE:
                        continue
                    if susp:
                        sospitosos += 1
                    cust = rs.customer.codi if rs.customer_id else '—'
                    self.stdout.write(f"  rs{rs.id} [{cust}] {rs.nom!r}")
                    self.stdout.write(f"     run={run}")
                    self.stdout.write(f"     n={len(rules)} LINEAR_sense_break={len(lin_nb)} "
                                      f"amb_break={n_break} talles_altes={high}")
                    if susp:
                        self.stdout.write(f"     ⚠ SOSPITA {susp}")
                        self.stdout.write("     candidates (pom): "
                                          f"{[(r.pom.codi_client if r.pom_id else '?') for r in lin_nb]}")
                    else:
                        self.stdout.write("     (sense sospita per l'heurística; "
                                          "llistat perquè s'ha demanat explícitament)")
                self.stdout.write(f"  → rulesets sospitosos a {schema}: {sospitosos} "
                                  f"(exclosos {seeds_exclosos} seeds ISO is_system_default)")

        self.stdout.write(self.style.WARNING(
            "\nAuditoria READ-ONLY (heurística; els valors per talla no es persisteixen). "
            "No s'ha modificat res."))
