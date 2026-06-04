"""
Reconcilia 19 POMMaster tenant-only (pom_global=None) del tenant fhort,
auto-importats de fitxes reals (M76 Olivia Dress, M79 SS26 Trousers Twill).

Pla acordat (NOMÉS aquests ids, cap altre camp tocat):
  - ids 387, 388 (FRONT/BACK RISE): duplicats redundants de POM-055/056
    canònics (que ja tenen el seu POMMaster id=321/322) i sense cap
    GarmentPOMMap → actiu=False (NO eliminar).
  - ids 379,380,381,382,383,384,385,386,389,390,391,392,393,394,395,396,397:
    tenant-only legítims → pendent_revisio=False (marca de revisió treta).

NO toca: cap pom_global FK, cap GarmentPOMMap, cap altre POMMaster, ni els
items baby_*/underwear (es treballen a part).

Idempotent: re-executar deixa l'estat igual. Guarda de seguretat: només actua
si el POMMaster existeix i és tenant-only (pom_global=None).

Run:  python manage.py reconcile_tenant_poms                 # dry-run
      python manage.py reconcile_tenant_poms --no-dry-run    # escriu
"""
import argparse

from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import schema_context

SCHEMA = 'fhort'

# ids → actiu=False (duplicats redundants, sense maps)
DEACTIVATE_IDS = [387, 388]

# ids → pendent_revisio=False (tenant-only legítims)
CLEAR_REVISIO_IDS = [
    379, 380, 381, 382, 383, 384, 385, 386,
    389, 390, 391, 392, 393, 394, 395, 396, 397,
]


class Command(BaseCommand):
    help = 'Reconcilia 19 POMMaster tenant-only del tenant fhort (actiu=False x2, pendent_revisio=False x17).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action=argparse.BooleanOptionalAction,
            default=True,
            help='Imprimeix què faria sense escriure res (default). Usa --no-dry-run per escriure.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        mode = 'DRY-RUN (cap escriptura)' if dry_run else 'ESCRIPTURA REAL'
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'reconcile_tenant_poms — mode: {mode} — schema: {SCHEMA}'
        ))

        with schema_context(SCHEMA):
            from fhort.pom.models import POMMaster

            planned = []  # (pom, field, current, target)

            self.stdout.write('')
            self.stdout.write(self.style.HTTP_INFO('━━━ [A] actiu=False (duplicats redundants) ━━━'))
            for pid in DEACTIVATE_IDS:
                pm = POMMaster.objects.filter(pk=pid).first()
                if not self._guard(pm, pid):
                    continue
                changed = pm.actiu is not False
                planned.append((pm, 'actiu', pm.actiu, False))
                flag = '→ canvia' if changed else '= ja a False (no-op)'
                self.stdout.write(
                    f"  id={pid} {pm.codi_client!r:12} {pm.nom_client!r:14} actiu: {pm.actiu} {flag}"
                )

            self.stdout.write('')
            self.stdout.write(self.style.HTTP_INFO('━━━ [B] pendent_revisio=False (tenant-only legítims) ━━━'))
            for pid in CLEAR_REVISIO_IDS:
                pm = POMMaster.objects.filter(pk=pid).first()
                if not self._guard(pm, pid):
                    continue
                changed = pm.pendent_revisio is not False
                planned.append((pm, 'pendent_revisio', pm.pendent_revisio, False))
                flag = '→ canvia' if changed else '= ja a False (no-op)'
                self.stdout.write(
                    f"  id={pid} {pm.codi_client!r:12} {pm.nom_client!r:38} pendent_revisio: {pm.pendent_revisio} {flag}"
                )

            real_changes = [p for p in planned if p[2] != p[3]]
            self.stdout.write('')
            self.stdout.write(
                f"  → resum: {len(DEACTIVATE_IDS)} ids actiu=False · {len(CLEAR_REVISIO_IDS)} ids pendent_revisio=False "
                f"· canvis reals a aplicar: {len(real_changes)}"
            )

            if not dry_run:
                self._write(planned)

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY-RUN: no s'ha escrit res. Torna a executar amb --no-dry-run per aplicar."
            ))
        else:
            self.stdout.write(self.style.SUCCESS('Fet.'))

    def _guard(self, pm, pid):
        """Només actua si existeix i és tenant-only (pom_global=None)."""
        if pm is None:
            self.stdout.write(self.style.ERROR(f"  id={pid} NO EXISTEIX — skip"))
            return False
        if pm.pom_global_id is not None:
            self.stdout.write(self.style.ERROR(
                f"  id={pid} NO és tenant-only (pom_global={pm.pom_global_id}) — skip per seguretat"))
            return False
        return True

    @transaction.atomic
    def _write(self, planned):
        for pm, field, _current, target in planned:
            setattr(pm, field, target)
            pm.save(update_fields=[field])
