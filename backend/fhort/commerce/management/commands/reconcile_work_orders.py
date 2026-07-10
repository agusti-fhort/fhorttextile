"""
Management command: reconcile_work_orders
D2 — Backfill d'assignació d'encàrrecs (regla B4a).

Troba tasques amb activitat real (InProgress/Done/Paused) i model amb customer,
però sense `work_order` (forats d'assignació: tasques anteriors al hook B4a, o
amb fallada transitòria de l'assignació). Per a cada forat, reconstrueix el
moment com el MIN(TaskTransition.at where to_status='InProgress') de la tasca i
aplica la MATEIXA regla que el hook: `assign_work_order(task, when)`.

Idempotent: `assign_work_order` no fa res si la tasca ja té work_order.
Ús: manage.py reconcile_work_orders [--dry-run] [--tenant SCHEMA]

LLEI — DUES FACTURACIONS SEPARADES (DECISIONS.md §4, 2026-07-07)
Aquesta comanda pertany a la facturació **studio→tercers** (mòdul comercial
tenant-side) i NO pot barrejar-se amb **backoffice→tenant** (ús de la plataforma).
Fronteres:
  1. Entitats — no comparteixen models. Res de `backoffice` (ModelConsumptionEvent,
     Invoice, TenantContract...).
  2. Imports — `fhort.commerce` MAI importa `fhort.backoffice`.
  3. Transacció — l'assignació d'encàrrec no comparteix atomic amb la meritació SaaS
     (D1, T1): un error aquí no pot revertir una meritació ja escrita.
  4. Reconciliació — cada facturació té la SEVA comanda de backfill.
El germà d'aquesta comanda a l'altra banda de la frontera és
`manage.py reconcile_consumption` (app `backoffice`). Aquesta comanda va néixer
extreta d'allà: vivia dins el reconcile de meritació i el feia dependre de commerce.
"""
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Min
from django.utils import timezone
from django_tenants.utils import schema_context, get_tenant_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill work_order assignment for tasks with activity but no encàrrec (B4a gaps).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be done without writing anything.'
        )
        parser.add_argument(
            '--tenant', type=str, default=None,
            help='Schema name of the tenant to process (default: all tenants).'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        tenant_filter = options['tenant']
        TenantModel = get_tenant_model()

        tenants = TenantModel.objects.exclude(schema_name='public')
        if tenant_filter:
            tenants = tenants.filter(schema_name=tenant_filter)
            if not tenants.exists():
                raise CommandError(f"Tenant '{tenant_filter}' not found.")

        total_wo = 0
        total_err = 0

        for tenant in tenants:
            self.stdout.write(f"\n{'[DRY-RUN] ' if dry_run else ''}Tenant: {tenant.schema_name} ({tenant.codi_tenant})")

            with schema_context(tenant.schema_name):
                from fhort.tasks.models import ModelTask, TaskTransition
                from fhort.tasks.services_c import assign_work_order

                # B4a — ENCÀRREC: tasques amb activitat però sense work_order. S'assignen
                # amb la MATEIXA regla del hook, però amb when = MIN(→InProgress) de cada tasca.
                wo_gaps = (
                    ModelTask.objects
                    .filter(work_order__isnull=True,
                            status__in=['InProgress', 'Done', 'Paused'],
                            model__customer__isnull=False)
                    .select_related('model', 'model__customer', 'task_type')
                )

                if not wo_gaps.exists():
                    self.stdout.write('  No gaps found.')
                    continue

                for task in wo_gaps:
                    first = TaskTransition.objects.filter(
                        model_task=task, to_status='InProgress').aggregate(f=Min('at'))['f']
                    when = first or task.started_at or timezone.now()

                    if dry_run:
                        self.stdout.write(
                            f"  [DRY-RUN] WOULD ASSIGN work_order task pk={task.pk} "
                            f"model={task.model.codi_intern} period={when.strftime('%Y-%m')}")
                        total_wo += 1
                        continue

                    try:
                        with transaction.atomic():
                            assign_work_order(task, when)
                        task.refresh_from_db(fields=['work_order'])
                        if task.work_order_id:
                            self.stdout.write(self.style.SUCCESS(
                                f"  OK task pk={task.pk} model={task.model.codi_intern} "
                                f"→ work_order={task.work_order_id}"))
                            total_wo += 1
                        else:
                            self.stdout.write(self.style.WARNING(
                                f"  SKIP task pk={task.pk}: no work_order resolt "
                                f"(col·lector del mes tancat?)"))
                    except Exception as e:
                        logger.exception('reconcile work_order failed task=%s', task.pk)
                        self.stdout.write(self.style.ERROR(f'  ERROR task pk={task.pk}: {e}'))
                        total_err += 1

        self.stdout.write(
            f"\n{'[DRY-RUN] ' if dry_run else ''}Done: {total_wo} work_orders assigned, "
            f"{total_err} errors."
        )
