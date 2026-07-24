"""
Management command: instantiate_external_models
Federació v2 (P3) — instancia al Studio, com a EXTERN, els models canònics del Brand.

    manage.py instantiate_external_models --brand LOS --studio FTT [--limit N] [--commit]

**LA LÒGICA JA NO VIU AQUÍ.** Des de P8 el domini és a `tenants/federation_service.py`,
perquè el mateix traspàs té ara una segona boca (`POST /api/v1/encarrecs/traspassar/`) i dues
còpies de la mateixa llei és com neixen les divergències: un guard que s'arregla en un camí i
no en l'altre, un informe que compta diferent. Aquest fitxer és el que sempre hauria d'haver
estat: llegir arguments, cridar el servei i **formatar l'informe per a un terminal**.

Si busques les lleis (l'EXTERN neix amb identitat i configuració però mai amb feina · el
vincle ACTIU mana · l'assignació per model és obligatòria · idempotència per `codi_intern` ·
config resolta per clau natural · dicts i mai ORM viu fora del context), són al servei.

El contracte de sortida es conserva íntegre: mateixos textos, mateixos números, mateix
DRY-RUN per defecte. Els tests de P3/P6 hi enganxen i han de seguir passant sense tocar-los.
"""
from django.core.management.base import BaseCommand, CommandError

from fhort.tenants.federation_service import FederacioError, traspassa


class Command(BaseCommand):
    help = 'Instancia al Studio, com a EXTERN, els models del Brand (gated per TenantLink actiu).'

    def add_arguments(self, parser):
        parser.add_argument('--brand', required=True, help='codi_tenant del Brand (origen canònic).')
        parser.add_argument('--studio', required=True, help='codi_tenant del Studio (destí).')
        parser.add_argument('--limit', type=int, default=None, help='Màxim de models a llegir (assaig).')
        parser.add_argument('--commit', action='store_true', help='Escriu de debò. Sense flag = DRY-RUN.')

    def handle(self, *args, **options):
        try:
            report = traspassa(
                brand_codi=options['brand'], studio_codi=options['studio'],
                commit=options['commit'], limit=options['limit'],
            )
        except FederacioError as e:
            # El servei parla de domini i no sap què és un terminal; el command el tradueix.
            raise CommandError(str(e))
        self._print_report(report)

    def _print_report(self, r):
        commit = r['commit']
        mode = 'COMMIT' if commit else 'DRY-RUN'
        verb = 'creats' if commit else 'a crear'
        brand, studio = r['brand_codi'], r['studio_codi']
        self.stdout.write(f"\n[{mode}] instantiate_external_models {brand} → {studio}")
        # N models al Brand, dels quals M assignats a aquest Studio: N-M existeixen però NO
        # viatgen (és el cas correcte — sense assignació, cap traspàs).
        self.stdout.write(f"  models al Brand   : {r['total_brand']} · assignats a {studio}: {r['n_assignats']}")
        self.stdout.write(f"  llegits (assignats): {r['n_llegits']}")
        self.stdout.write(f"  {verb:<17}: {len(r['creats'])}")
        self.stdout.write(f"  saltats (ja hi són): {len(r['saltats'])}")

        um = r['unmatched']
        total_um = sum(len(v) for v in um.values())
        if total_um:
            self.stdout.write(self.style.WARNING(
                f"  config NO aparellada: {total_um} referència/es (el model es crea amb el camp NULL)"))
            for tipus, codis in um.items():
                if codis:
                    unics = sorted(set(codis))
                    mostra = ', '.join(unics[:10]) + (' …' if len(unics) > 10 else '')
                    self.stdout.write(f"    · {tipus}: {len(unics)} → {mostra}")
        else:
            self.stdout.write("  config NO aparellada: 0")

        if not commit:
            self.stdout.write(self.style.NOTICE("\n  (DRY-RUN: no s'ha escrit res. Afegeix --commit per crear.)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n  Fet: {len(r['creats'])} models EXTERN creats al Studio {studio}."))
