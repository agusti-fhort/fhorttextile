"""PEÇA 0 del master_delta — completa el catàleg POM ABANS de sembrar les 4 cel·les noves.

Els 7 codis que no resolien es tanquen aquí (decisió Agus 19/07, descripcions literals de
L27SH0101_LEVANTE.xlsx amb LENGHT→LENGTH normalitzat):
  · V.2 → ÀLIES al POM existent S.35 'COLLAR PIECE WIDTH' (equivalència exacta per descripció).
  · 5 POMs LOS-local NOUS (patró consolidate_pom_catalog: POMMaster + POMGlobal `LOSPOM-<id>`
    categoria LOSAN + àlies · pendent_revisio=True · pom_global LOCAL, mai canònic POM-xxx).
    H.12 rep DOS àlies (H.12 i H12: mateixa mesura, notació amb i sense punt).

Cerca per descripció feta abans (cap equivalent per als 5 nous → es creen). Idempotent
(get_or_create per codi_client / client_code). --dry-run per defecte.

    python manage.py seed_master_delta_catalog                # DRY-RUN
    python manage.py seed_master_delta_catalog --no-dry-run   # escriu
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import POMMaster, POMGlobal, CustomerPOMAlias
from fhort.tasks.models import Customer
from fhort.pom.seed_data import consolidate_pom_los as CFG

ORIGEN = 'LOS màster delta v1'

# (client_code, codi_client del POM existent, nom_guard|None) — només àlies, cap POM nou.
# U.1: hi ha DOS POMMaster amb codi_client 'U1' (pom 'JETTING WIDTH' via àlies LOS · pom 'Height
# sequins piece (CF)' per codi directe). El guard de nom desambigua cap al correcte (deute latent de
# nomenclatura del catàleg anotat: qualsevol resolució que caigui a codi_client 'U1' hi tornarà a topar).
ALIES_A_EXISTENT = [
    ('V.2', 'S.35', None),
    ('U.1', 'U1', 'JETTING WIDTH'),
]

# (codi_pom, nom_client EN literal de la fitxa, [àlies a crear])
POMS_NOUS = [
    ('G.3',  'SLEEVE SHORT LENGTH',   ['G.3']),
    ('H.12', 'SLEEVE SHORT OPENING',  ['H.12', 'H12']),
    ('O.8',  'CHEST POCKET OPENING',  ['O.8']),
    ('E.9',  'BOTTOM MOTIVE LOCATION', ['E.9']),
    ('S.42', 'FRONT VENT WIDTH',      ['S.42']),
]


class Command(BaseCommand):
    help = 'Completa el catàleg POM per al master_delta (1 àlies + 5 POMs LOS-local nous).'

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=CFG.TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        head = 'DRY-RUN (cap escriptura)' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(f'=== seed_master_delta_catalog · {head} ==='))

        with schema_context(opts['schema']), transaction.atomic():
            los = Customer.objects.filter(codi=CFG.CUSTOMER_CODI).first()
            if not los:
                raise CommandError('Customer LOS no existeix.')

            # ── C.1 àlies a POM existent ──
            for client_code, pom_codi, nom_guard in ALIES_A_EXISTENT:
                qs = POMMaster.objects.filter(codi_client=pom_codi)
                if nom_guard:
                    qs = qs.filter(nom_client=nom_guard)
                if qs.count() != 1:
                    raise CommandError(f'POM {pom_codi!r} (guard nom={nom_guard!r}) ambigu/inexistent '
                                       f'(n={qs.count()}) per àlies {client_code}.')
                pom = qs.first()
                a, created = CustomerPOMAlias.objects.get_or_create(
                    customer=los, client_code=client_code, defaults={'pom': pom, 'origen': 'DICCIONARI'})
                self.stdout.write(f'  [ÀLIES] {client_code} → {pom.codi_client!r} '
                                  f"'{pom.nom_client}' · {'CREAT' if created else 'ja existia'}")

            # ── C.2 POMs LOS-local nous (patró consolidate) ──
            for codi, nom_en, alies in POMS_NOUS:
                pom, pom_created = POMMaster.objects.get_or_create(
                    codi_client=codi,
                    defaults={'nom_client': nom_en, 'actiu': True,
                              'pendent_revisio': True, 'origen_import': ORIGEN})
                if pom_created and pom.pom_global_id is None:
                    pg = POMGlobal.objects.create(
                        codi=f'LOSPOM-{pom.id}', nom_en=nom_en, nom_ca='', categoria='LOSAN')
                    pom.pom_global = pg
                    pom.save(update_fields=['pom_global'])
                gl = pom.pom_global and pom.pom_global.codi
                self.stdout.write(f'  [POM] {codi} \'{nom_en}\' · {"CREAT" if pom_created else "ja existia"} '
                                  f'· global={gl} · pendent_revisio={pom.pendent_revisio}')
                for ac in alies:
                    a, created = CustomerPOMAlias.objects.get_or_create(
                        customer=los, client_code=ac, defaults={'pom': pom, 'origen': 'DICCIONARI'})
                    self.stdout.write(f'      àlies {ac} → {codi} · {"CREAT" if created else "ja existia"}')

            if dry:
                transaction.set_rollback(True)
                self.stdout.write('  (dry-run: rollback, res tocat)')

        self.stdout.write(self.style.SUCCESS(f'=== FET ({head}) ==='))
