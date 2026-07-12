"""
Management command: set_grading_origen
P-PROV / P3 — backfill de la procedència dels GradingRuleSet existents.

La CLASSIFICACIÓ és una decisió humana (Patró C): aquesta comanda no endevina res.
`--list` ensenya què queda per classificar; `--map` aplica el que el CTO decideix.

Llei PROVINENÇA (DECISIONS.md:348, versió mínima) + RUN-CLIENT (DECISIONS.md:304):
un GradingRuleSet derivat d'un client és secret industrial i MAI viatja a un tenant
nou. Sense l'eix `origen`, `bootstrap_tenant` no els sap distingir dels canònics.

Ús:
    manage.py set_grading_origen --list [--tenant SCHEMA] [--all]
    manage.py set_grading_origen --map "75:CANONICAL,76:CANONICAL,110:CLIENT_RUN"
    manage.py set_grading_origen --map "110:CLIENT_RUN:BRW"      # fixa també el customer
    manage.py set_grading_origen --map "..." --dry-run

`--map` és idempotent: re-executar-lo no canvia res (reporta "ja hi era"). Valida
els ids i els valors ABANS d'escriure; si una sola entrada és invàlida, no escriu res.
El customer es resol per `Customer.codi` dins del schema del tenant.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context, get_tenant_model


class Command(BaseCommand):
    help = 'Llista o fixa GradingRuleSet.origen (CANONICAL/CLIENT_RUN/IMPORT). Backfill de PROVINENÇA.'

    def add_arguments(self, parser):
        parser.add_argument('--list', action='store_true',
                            help='Llista els rulesets amb origen NULL (no classificats).')
        parser.add_argument('--all', action='store_true',
                            help='Amb --list: mostra TOTS, no només els no classificats.')
        parser.add_argument('--map', type=str, default=None,
                            help='"id:ORIGEN[:CODI_CUSTOMER],..." — p.ex. "110:CLIENT_RUN:BRW,75:CANONICAL".')
        parser.add_argument('--tenant', type=str, default='fhort',
                            help='Schema del tenant (default: fhort).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Amb --map: reporta sense escriure res.')

    # ---------------------------------------------------------------- parsing

    def _parse_map(self, raw, GradingRuleSet):
        """Converteix "id:ORIGEN[:CODI]" en [(id, origen, codi_or_None)]. Valida ids i valors."""
        valids = {c[0] for c in GradingRuleSet.ORIGEN_CHOICES}
        entrades = []
        for tros in [t.strip() for t in raw.split(',') if t.strip()]:
            parts = tros.split(':')
            if len(parts) not in (2, 3):
                raise CommandError(
                    f"Entrada mal formada: {tros!r}. Format: id:ORIGEN[:CODI_CUSTOMER]")
            sid, origen = parts[0].strip(), parts[1].strip().upper()
            codi = parts[2].strip() if len(parts) == 3 else None
            if not sid.isdigit():
                raise CommandError(f"Id no numèric a {tros!r}: {sid!r}")
            if origen not in valids:
                raise CommandError(
                    f"Origen invàlid a {tros!r}: {origen!r}. Valors: {sorted(valids)}")
            entrades.append((int(sid), origen, codi))
        if not entrades:
            raise CommandError('--map buit.')
        return entrades

    # ---------------------------------------------------------------- accions

    def _list(self, GradingRuleSet, mostrar_tots):
        qs = GradingRuleSet.objects.all()
        if not mostrar_tots:
            qs = qs.filter(origen__isnull=True)
        qs = qs.select_related('customer').order_by('id')

        if not qs.exists():
            self.stdout.write(self.style.SUCCESS(
                '  Cap ruleset sense classificar. Tots tenen origen.'))
            return

        self.stdout.write(
            f"\n  {'id':>4}  {'origen':<11} {'cust':<5} {'codi_sistema':<30} {'regles':>6}  nom")
        self.stdout.write(f"  {'-'*4}  {'-'*11} {'-'*5} {'-'*30} {'-'*6}  {'-'*40}")
        for rs in qs:
            self.stdout.write(
                f"  {rs.id:>4}  {(rs.origen or 'NULL'):<11} "
                f"{(rs.customer.codi if rs.customer else '-'):<5} "
                f"{(rs.codi_sistema or '-'):<30} {rs.regles.count():>6}  {rs.nom[:40]}")
        self.stdout.write(f"\n  {qs.count()} rulesets"
                          f"{'' if mostrar_tots else ' sense classificar (origen NULL)'}.")

    def _apply(self, GradingRuleSet, Customer, entrades, dry_run):
        # 1) Validació completa ABANS d'escriure: o entra tot, o no entra res.
        rulesets, customers = {}, {}
        for sid, origen, codi in entrades:
            rs = GradingRuleSet.objects.filter(pk=sid).select_related('customer').first()
            if rs is None:
                raise CommandError(f"GradingRuleSet id={sid} no existeix en aquest tenant.")
            rulesets[sid] = rs
            if codi is not None and codi not in customers:
                cu = Customer.objects.filter(codi=codi).first()
                if cu is None:
                    raise CommandError(f"Customer amb codi {codi!r} no existeix en aquest tenant.")
                customers[codi] = cu

        # 2) Aplicació idempotent.
        canviats, iguals = 0, 0
        with transaction.atomic():
            for sid, origen, codi in entrades:
                rs = rulesets[sid]
                nou_customer = customers[codi] if codi else rs.customer
                ja_hi_era = (rs.origen == origen and rs.customer_id == (
                    nou_customer.id if nou_customer else None))

                if ja_hi_era:
                    iguals += 1
                    self.stdout.write(f"  = id={sid:<4} ja era {origen}"
                                      f"{f' / {codi}' if codi else ''}")
                    continue

                abans = rs.origen or 'NULL'
                rs.origen = origen
                camps = ['origen']
                if codi:
                    rs.customer = nou_customer
                    camps.append('customer')
                if not dry_run:
                    rs.save(update_fields=camps)
                canviats += 1
                self.stdout.write(self.style.SUCCESS(
                    f"  {'[DRY-RUN] ' if dry_run else ''}~ id={sid:<4} {abans} → {origen}"
                    f"{f' · customer={codi}' if codi else ''}   {rs.nom[:40]}"))

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            f"\n  {'[DRY-RUN] ' if dry_run else ''}Done: {canviats} canviats, {iguals} ja hi eren.")

    # ---------------------------------------------------------------- handle

    def handle(self, *args, **options):
        if not options['list'] and not options['map']:
            raise CommandError('Cal --list o --map.')
        if options['list'] and options['map']:
            raise CommandError('--list i --map són excloents.')

        schema = options['tenant']
        TenantModel = get_tenant_model()
        if not TenantModel.objects.filter(schema_name=schema).exists():
            raise CommandError(f"Tenant '{schema}' no existeix.")

        self.stdout.write(f"\nTenant: {schema}")
        with schema_context(schema):
            from fhort.pom.models import GradingRuleSet
            from fhort.tasks.models import Customer

            if options['list']:
                self._list(GradingRuleSet, options['all'])
            else:
                entrades = self._parse_map(options['map'], GradingRuleSet)
                self._apply(GradingRuleSet, Customer, entrades, options['dry_run'])
