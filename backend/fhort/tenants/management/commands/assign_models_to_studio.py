"""
Management command: assign_models_to_studio
Federació v2 (P6) — el Brand assigna (o revoca) un Studio com a RECURS sobre models concrets.

    manage.py assign_models_to_studio --brand LOS --studio FTT \
        --codis "LOS-SS27-0001,LOS-SS27-0002"  [o]  --fitxer <path>  [--revocar] [--commit]

LA LLEI: dues claus independents governen el traspàs. El TenantLink autoritza el PONT;
`Model.studio_assignat` autoritza CADA MODEL. Aquest command escriu la segona: l'assignació
parteix del contracte i és la palanca de sobirania del Brand sobre cada model. Amb el pont
obert però sense assignació, `instantiate_external_models` no mou res.

Escriu al schema del BRAND. Valida TenantLink ACTIU brand↔studio abans de res (mateix guard
que la instanciació: aturat/revocat → error dur). Idempotent. DRY-RUN per defecte.

`--revocar` buida l'assignació (studio_assignat='') en comptes d'assignar-la: el model queda
al Brand i fora del pròxim traspàs. Els codis no trobats es LLISTEN (un codi mal escrit no
passa en silenci).
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django_tenants.utils import schema_context

from fhort.tenants.models import Client, TenantLink


class Command(BaseCommand):
    help = 'El Brand assigna/revoca un Studio sobre models concrets (gated per TenantLink actiu).'

    def add_arguments(self, parser):
        parser.add_argument('--brand', required=True, help='codi_tenant del Brand (on viuen els models).')
        parser.add_argument('--studio', required=True, help='codi_tenant del Studio a assignar.')
        parser.add_argument('--codis', default='', help='codi_intern separats per comes.')
        parser.add_argument('--fitxer', default='', help='Path a un fitxer amb un codi_intern per línia.')
        parser.add_argument('--revocar', action='store_true',
                            help='Buida l\'assignació (treu el model del traspàs) en comptes d\'assignar.')
        parser.add_argument('--commit', action='store_true', help='Escriu de debò. Sense flag = DRY-RUN.')

    def handle(self, *args, **options):
        brand, studio = options['brand'], options['studio']
        revocar, commit = options['revocar'], options['commit']

        # El vincle mana (mateix guard que la instanciació).
        link = TenantLink.objects.filter(
            brand_codi_tenant=brand, studio_codi_tenant=studio).first()
        if link is None:
            raise CommandError(
                f'No hi ha cap TenantLink entre brand={brand} i studio={studio}. Cal sembrar-lo.')
        if not link.es_viu():
            raise CommandError(
                f'El TenantLink {brand}↔{studio} no és ACTIU (estat={link.estat}). El pont està tancat.')

        brand_client = Client.objects.filter(codi_tenant=brand).first()
        if brand_client is None:
            raise CommandError(f"No existeix cap tenant amb codi_tenant='{brand}'.")

        codis = self._recull_codis(options['codis'], options['fitxer'])
        if not codis:
            raise CommandError('Cap codi_intern indicat (--codis o --fitxer).')

        assignats, ja_estaven, no_trobats = self._aplica(
            brand_client.schema_name, studio, codis, revocar, commit)

        self._informe(brand, studio, revocar, commit, codis, assignats, ja_estaven, no_trobats)

    def _recull_codis(self, codis_arg, fitxer_arg):
        codis = []
        if codis_arg:
            codis += [c.strip() for c in codis_arg.split(',') if c.strip()]
        if fitxer_arg:
            path = Path(fitxer_arg)
            if not path.exists():
                raise CommandError(f'Fitxer no trobat: {fitxer_arg}')
            codis += [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
        # Dedup preservant l'ordre.
        vistos, unics = set(), []
        for c in codis:
            if c not in vistos:
                vistos.add(c)
                unics.append(c)
        return unics

    def _aplica(self, brand_schema, studio, codis, revocar, commit):
        from fhort.models_app.models import Model
        nou_valor = '' if revocar else studio
        assignats, ja_estaven, no_trobats = [], [], []
        with schema_context(brand_schema):
            existents = dict(
                Model.objects.filter(codi_intern__in=codis)
                .values_list('codi_intern', 'studio_assignat'))
            for codi in codis:
                if codi not in existents:
                    no_trobats.append(codi)
                elif existents[codi] == nou_valor:
                    ja_estaven.append(codi)
                else:
                    assignats.append(codi)
            if commit and assignats:
                Model.objects.filter(codi_intern__in=assignats).update(studio_assignat=nou_valor)
        return assignats, ja_estaven, no_trobats

    def _informe(self, brand, studio, revocar, commit, codis, assignats, ja_estaven, no_trobats):
        mode = 'COMMIT' if commit else 'DRY-RUN'
        accio = 'REVOCAR' if revocar else 'ASSIGNAR'
        verb = ('revocats' if revocar else 'assignats') if commit else \
               ('a revocar' if revocar else 'a assignar')
        self.stdout.write(f"\n[{mode}] {accio} {brand} → {studio}: {len(codis)} codi(s) demanat(s)")
        self.stdout.write(f"  {verb}: {len(assignats)}")
        self.stdout.write(f"  ja hi estaven: {len(ja_estaven)}")
        if no_trobats:
            self.stdout.write(self.style.WARNING(
                f"  NO trobats al Brand: {len(no_trobats)} (revisa'ls — no s'ha tocat res d'ells):"))
            for c in no_trobats:
                self.stdout.write(f"    · {c}")
        else:
            self.stdout.write("  NO trobats al Brand: 0")
        if not commit:
            self.stdout.write(self.style.NOTICE("\n  (DRY-RUN: res escrit. Afegeix --commit.)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n  Fet: {len(assignats)} models {verb}."))
