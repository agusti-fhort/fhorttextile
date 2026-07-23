"""
Management command: reconcile_consumption
Sprint 4 — Meritació retroactiva (backfill N10).

Troba models amb activitat real (tasca InProgress/Done/Paused) però sense
consumption_started_at (forats N10: models anteriors al hook 4.2 o amb
fallada transitòria de facturació). Per a cada forat, reconstrueix el
merited_at com el MIN(TaskTransition.at where to_status='InProgress') de
totes les seves tasques, i fa la triple escriptura atòmica:
  1. Model.consumption_started_at (TENANT)
  2. ConsumptionRecord (TENANT)
  3. ModelConsumptionEvent (PUBLIC) — via schema_context('public')

Idempotent: un model ja meritat (consumption_started_at IS NOT NULL)
mai es torna a tocar, fins i tot si la comanda es re-executa.
Ús: manage.py reconcile_consumption [--dry-run] [--tenant SCHEMA]

LLEI — DUES FACTURACIONS SEPARADES (DECISIONS.md §4, 2026-07-07)
Aquesta comanda pertany a la facturació **backoffice→tenant** (ús de la plataforma)
i NO pot barrejar-se amb **studio→tercers** (mòdul comercial tenant-side). Fronteres:
  1. Entitats — no comparteixen models. Res de `commerce` (WorkOrder, DeliveryNote...).
  2. Imports — `fhort.backoffice` MAI importa `fhort.commerce` (ni transitivament).
  3. Transacció — cap escriptura de commerce dins l'atomic que merita (D1, T1).
  4. Reconciliació — cada facturació té la SEVA comanda de backfill.
El germà d'aquesta comanda a l'altra banda de la frontera és
`manage.py reconcile_work_orders` (app `commerce`). Els imports de `tasks`/`models_app`
que hi ha aquí SÍ són feina pròpia: el llibre de meritació es construeix llegint
l'activitat del tenant. La llei prohibeix `commerce`, no llegir el tenant.
"""
import uuid
import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context, get_tenant_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill meritation for models with activity but no ConsumptionRecord (N10 gaps).'

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

        total_ok = 0
        total_skip = 0
        total_err = 0

        for tenant in tenants:
            self.stdout.write(f"\n{'[DRY-RUN] ' if dry_run else ''}Tenant: {tenant.schema_name} ({tenant.codi_tenant})")

            with schema_context(tenant.schema_name):
                from fhort.models_app.models import Model, ConsumptionRecord
                from fhort.tasks.signals import model_consumption_started

                # Forats: models amb activitat real i sense marca de meritació
                gaps = (
                    Model.objects
                    .filter(
                        consumption_started_at__isnull=True,
                        model_tasks__status__in=['InProgress', 'Done', 'Paused'],
                    )
                    .distinct()
                    .select_related('customer')
                )

                if not gaps.exists():
                    self.stdout.write('  No gaps found.')
                    continue

                for model in gaps:
                    # Reconstruir merited_at = MIN(→InProgress) de totes les tasques del model
                    from django.db.models import Min
                    from fhort.tasks.models import TaskTransition
                    agg = TaskTransition.objects.filter(
                        model_task__model=model,
                        to_status='InProgress',
                    ).aggregate(first=Min('at'))
                    merited_at = agg['first']

                    if merited_at is None:
                        # Cas patològic: activitat sense transició →InProgress registrada
                        self.stdout.write(
                            self.style.WARNING(
                                f'  SKIP model {model.codi_intern} (pk={model.pk}): '
                                f'no InProgress transition found — cannot reconstruct merited_at.'
                            )
                        )
                        total_skip += 1
                        continue

                    period = merited_at.strftime('%Y-%m')
                    codi_client = model.customer.codi if model.customer else tenant.codi_tenant

                    if dry_run:
                        self.stdout.write(
                            f'  [DRY-RUN] WOULD MERIT model {model.codi_intern} (pk={model.pk}) '
                            f'| merited_at={merited_at.isoformat()} | period={period} | codi_client={codi_client}'
                        )
                        total_ok += 1
                        continue

                    # Triple escriptura atòmica (igual que el hook 4.2)
                    try:
                        with transaction.atomic():
                            # Guard idempotència (per si concurrència o re-execució)
                            rows = Model.objects.filter(
                                pk=model.pk,
                                consumption_started_at__isnull=True,
                            ).update(consumption_started_at=merited_at)

                            if not rows:
                                # Ja meritat per una altra execució concurrent — saltar net
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'  SKIP model {model.codi_intern}: already merited (concurrent run).'
                                    )
                                )
                                total_skip += 1
                                continue

                            ref = uuid.uuid4()
                            record = ConsumptionRecord.objects.create(
                                model=model,
                                code_snapshot=model.codi_intern,
                                name_snapshot=model.nom_prenda or '',
                                period=period,
                                opaque_ref=ref,
                                merited_at=merited_at,
                            )
                            # Event a public via senyal (receiver fa schema_context('public'))
                            model_consumption_started.send(
                                sender=Model,
                                codi_client=codi_client,
                                period=period,
                                opaque_ref=ref,
                                merited_at=merited_at,
                                # P4 — ACTOR: el schema del tenant que es reconcilia.
                                actor_schema=tenant.schema_name,
                            )

                        self.stdout.write(
                            self.style.SUCCESS(
                                f'  OK model {model.codi_intern} (pk={model.pk}) '
                                f'| merited_at={merited_at.isoformat()} | period={period}'
                            )
                        )
                        total_ok += 1

                    except Exception as e:
                        logger.exception(
                            'reconcile_consumption failed for model=%s tenant=%s',
                            model.pk, tenant.schema_name
                        )
                        self.stdout.write(
                            self.style.ERROR(
                                f'  ERROR model {model.codi_intern} (pk={model.pk}): {e}'
                            )
                        )
                        total_err += 1

        self.stdout.write(
            f"\n{'[DRY-RUN] ' if dry_run else ''}Done: {total_ok} merited, "
            f"{total_skip} skipped, {total_err} errors."
        )
