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

    def _reconcile_sets(self, tenant, dry_run, total_ok, total_skip, total_err):
        """SET-1 · A3 — forats de CONJUNT: un GarmentSet amb activitat a qualsevol peça i sense
        `consumption_started_at` AL SET.

        Mateix criteri que el punt de runtime (`tasks/services_c.py:_meritar_conjunt`), i els
        dos han de canviar sempre alhora: si el runtime deixés les germanes sense marca i aquí
        no es mirés el SET, cada peça compliria el criteri de forat de models sols i el conjunt
        meritaria N cops amb retard. Per això, a més de crear l'albarà únic, aquí també
        s'estampen totes les germanes.
        """
        from django.db.models import Min

        from fhort.models_app.models import ConsumptionRecord, GarmentSet, Model
        from fhort.tasks.models import TaskTransition
        from fhort.tasks.signals import model_consumption_started

        forats = (GarmentSet.objects
                  .filter(consumption_started_at__isnull=True,
                          peces__model_tasks__status__in=['InProgress', 'Done', 'Paused'])
                  .distinct())

        for gs in forats:
            merited_at = TaskTransition.objects.filter(
                model_task__model__garment_set=gs, to_status='InProgress',
            ).aggregate(first=Min('at'))['first']
            if merited_at is None:
                self.stdout.write(self.style.WARNING(
                    f'  SKIP set {gs.codi_base} (pk={gs.pk}): no InProgress transition found.'))
                total_skip += 1
                continue

            period = merited_at.strftime('%Y-%m')
            peca = Model.objects.filter(garment_set=gs).select_related('customer').first()
            codi_client = (peca.customer.codi if peca and peca.customer_id
                           else tenant.codi_tenant)

            if dry_run:
                self.stdout.write(
                    f'  [DRY-RUN] WOULD MERIT set {gs.codi_base} (pk={gs.pk}) '
                    f'| merited_at={merited_at.isoformat()} | period={period} '
                    f'| codi_client={codi_client}')
                total_ok += 1
                continue

            try:
                with transaction.atomic():
                    rows = GarmentSet.objects.filter(
                        pk=gs.pk, consumption_started_at__isnull=True,
                    ).update(consumption_started_at=merited_at)
                    # Sempre: cap germana sense marca (tanca el forat per als models sols).
                    Model.objects.filter(
                        garment_set=gs, consumption_started_at__isnull=True,
                    ).update(consumption_started_at=merited_at)
                    if not rows:
                        self.stdout.write(self.style.WARNING(
                            f'  SKIP set {gs.codi_base}: already merited (concurrent run).'))
                        total_skip += 1
                        continue

                    ref = uuid.uuid4()
                    ConsumptionRecord.objects.create(
                        garment_set=gs,
                        code_snapshot=gs.codi_base,
                        name_snapshot=gs.nom_comercial or '',
                        period=period, opaque_ref=ref, merited_at=merited_at,
                    )
                    model_consumption_started.send(
                        sender=Model, codi_client=codi_client, period=period,
                        opaque_ref=ref, merited_at=merited_at,
                        actor_schema=tenant.schema_name,
                    )
                self.stdout.write(self.style.SUCCESS(
                    f'  OK set {gs.codi_base} (pk={gs.pk}) '
                    f'| merited_at={merited_at.isoformat()} | period={period}'))
                total_ok += 1
            except Exception as e:
                logger.exception('reconcile_consumption failed for set=%s tenant=%s',
                                 gs.pk, tenant.schema_name)
                self.stdout.write(self.style.ERROR(
                    f'  ERROR set {gs.codi_base} (pk={gs.pk}): {e}'))
                total_err += 1

        return total_ok, total_skip, total_err

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

                # SET-1 · A3 — PRIMER els CONJUNTS. Un set amb activitat i sense marca AL SET
                # merita UN cop, ancorat al conjunt. Si això es fes després (o no es fes), les
                # peces d'un set caurien pel criteri de forat de sota i el set meritaria N cops.
                total_ok, total_skip, total_err = self._reconcile_sets(
                    tenant, dry_run, total_ok, total_skip, total_err)

                # Forats de models SOLS: activitat real i sense marca. `garment_set__isnull=True`
                # no és cosmètic — sense ell, una peça d'un conjunt ja meritat com a conjunt
                # (però amb la seva marca encara buida per qualsevol motiu) tornaria a meritar
                # pel seu compte i el set passaria a comptar 2.
                gaps = (
                    Model.objects
                    .filter(
                        consumption_started_at__isnull=True,
                        garment_set__isnull=True,
                        model_tasks__status__in=['InProgress', 'Done', 'Paused'],
                    )
                    .distinct()
                    .select_related('customer')
                )

                if not gaps.exists():
                    self.stdout.write('  No single-model gaps found.')
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
