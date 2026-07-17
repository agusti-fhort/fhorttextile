"""
generate_invoices — genera les factures recurrents DRAFT d'un període (F-RECUR).

Mai emet: deixa DRAFTs perquè un humà els revisi i els emeti amb sèrie (F-FACT-B1).
Idempotent: re-executar un període no duplica (quota per client+període única; events
ja vinculats no re-entren).

    manage.py generate_invoices --period 2026-07
    manage.py generate_invoices --period 2026-07 --client LOS
    manage.py generate_invoices --period 2026-07 --dry-run
"""
from django.core.management.base import BaseCommand, CommandError

from fhort.backoffice.recurring_service import generate_invoices


class Command(BaseCommand):
    help = 'Genera les factures recurrents (quota + consum) en DRAFT per a un període.'

    def add_arguments(self, parser):
        parser.add_argument('--period', required=True, help="Període 'YYYY-MM'.")
        parser.add_argument('--client', default=None, help='Limita a un codi_tenant.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Informe sense persistir res.')

    def handle(self, *args, **o):
        period = o['period']
        if len(period) != 7 or period[4] != '-':
            raise CommandError("--period ha de ser 'YYYY-MM'.")

        dry = o['dry_run']
        reports = generate_invoices(period, codi_client=o['client'], dry_run=dry)

        head = f"{'[DRY-RUN] ' if dry else ''}generate_invoices · període {period}"
        self.stdout.write(self.style.MIGRATE_HEADING(f'\n{head}\n'))
        if not reports:
            self.stdout.write('  Cap client facturable (viu, no gratuït, amb contracte vigent).')
            return

        creades = 0
        for r in reports:
            self.stdout.write(self.style.HTTP_INFO(f"■ {r['codi_client']}"))
            if r.get('quota'):
                self.stdout.write(f"    quota:  {r['quota']}")
            c = r.get('consum')
            if c:
                self.stdout.write(
                    f"    consum: {c['events']} events · {c['inclosos']} inclosos · "
                    f"{c['facturats']} facturats × {c['tarifa']}")
            if r.get('exclosos'):
                self.stdout.write(f"    exclosos: {r['exclosos']} (no es facturen)")
            self.stdout.write(f"    total s/IVA: {r.get('total_sense_iva', 0)}")
            for a in r.get('avisos', []):
                self.stdout.write(self.style.WARNING(f"    · {a}"))
            if r.get('invoice_id'):
                estat = 'CREADA' if r.get('creada') else 'reaprofitada'
                self.stdout.write(self.style.SUCCESS(f"    DRAFT #{r['invoice_id']} ({estat})"))
                if r.get('creada'):
                    creades += 1

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"\n{'(res persistit)' if dry else f'{creades} DRAFT creades'} · "
            f"{len(reports)} clients processats\n"))
