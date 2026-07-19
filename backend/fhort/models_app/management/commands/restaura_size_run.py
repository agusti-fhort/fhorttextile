"""restaura_size_run — escombrat de corrupció de `Model.size_run_model` (brief APARELLAMENT, punt b).

L'acció `alinear` (retirada) podia sobreescriure `Model.size_run_model` amb etiquetes del DOCUMENT
(p.ex. '3-6m·6-9m·…') en comptes de les etiquetes tenant del seu SizeSystem ('03/06·06/09·…').
Aquesta comanda audita TOTS els models amb size_system i restaura el run a la forma-tenant quan cada
etiqueta casa UNÍVOCAMENT (per forma canònica) amb una SizeDefinition del system. Les que no casen
es reporten com a NO RESTAURABLES (no s'endevinen).

Dry-run per defecte (només informe); `--apply` per escriure. Read-only sobre tot el que no sigui el
camp `size_run_model` dels models corromputs.
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context

from fhort.models_app.models import Model
from fhort.pom.models import SizeDefinition
from fhort.pom.size_labels import canonical_size_label


def _split_run(s):
    return [x.strip() for x in (s or '').replace(';', '·').split('·') if x.strip()]


class Command(BaseCommand):
    help = "Audita/restaura Model.size_run_model corromput a la forma-tenant (dry-run per defecte)."

    def add_arguments(self, parser):
        parser.add_argument('--schema', default='fhort')
        parser.add_argument('--apply', action='store_true', help='Escriu (default dry-run).')

    def handle(self, *args, **opts):
        schema = opts['schema']
        apply = opts['apply']
        restored, unrestorable, clean = [], [], 0

        with schema_context(schema):
            for m in Model.objects.filter(size_system__isnull=False).select_related('size_system'):
                run = _split_run(m.size_run_model)
                if not run:
                    continue
                sys_labels = list(SizeDefinition.objects.filter(size_system=m.size_system)
                                  .values_list('etiqueta', flat=True))
                canon_to_tenant = {}
                for e in sys_labels:
                    canon_to_tenant.setdefault(canonical_size_label(e), e)

                tenant_run, missing = [], []
                for lbl in run:
                    tgt = canon_to_tenant.get(canonical_size_label(lbl))
                    if tgt is None:
                        missing.append(lbl)
                    tenant_run.append(tgt if tgt is not None else lbl)

                if missing:
                    unrestorable.append((m, run, missing))
                elif tenant_run != run:
                    restored.append((m, run, tenant_run))
                    if apply:
                        m.size_run_model = '·'.join(tenant_run)
                        m.save(update_fields=['size_run_model'])
                else:
                    clean += 1

        mode = 'APPLY' if apply else 'DRY-RUN'
        self.stdout.write(self.style.SUCCESS(f'restaura_size_run · schema={schema} · {mode}'))
        self.stdout.write(f'  nets (ja en forma-tenant): {clean}')
        self.stdout.write(self.style.WARNING(f'  RESTAURATS ({len(restored)}):') if restored else '  restaurats: 0')
        for m, before, after in restored:
            self.stdout.write(f"    #{m.id} {m.codi_intern}: {'·'.join(before)}  →  {'·'.join(after)}")
        if unrestorable:
            self.stdout.write(self.style.ERROR(f'  NO RESTAURABLES ({len(unrestorable)}) — etiquetes sense casar:'))
            for m, run, missing in unrestorable:
                self.stdout.write(f"    #{m.id} {m.codi_intern}: run={'·'.join(run)} · sense casar={missing}")
        if not apply and restored:
            self.stdout.write('  (dry-run: cap escriptura; torna a executar amb --apply)')
