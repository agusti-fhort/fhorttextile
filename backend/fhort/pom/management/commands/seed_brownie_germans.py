"""Sembra dels ÀLIES D'INSTÀNCIA oficials de Brownie (full GERMANS_OFICIALS, D-31.26).

Un «germà oficial» és un codi que el document de nomenclatura del propi client declara com
a variant de la MATEIXA fila que un altre (columnes E/F del doc Nomenclaturas): A2 i A3 no
són dues amplades de pit noves, són l'amplada de pit dita tres vegades. La càrrega és un
`CustomerPOMAlias` del germà cap al POM BASE, marcat `es_instancia=True`.

**QUÈ ES DESA I QUÈ NO.** Es desa el vincle al POM i la marca. NO es desa quina cara és
—ni l'ordinal «2a/3a» ni l'eix estat/posició—, perquè aquesta és la pregunta que el full
MATCHER diu explícitament que no s'ha d'auto-respondre mai: el matcher resol el POM i deixa
la fila a «assignar instància». La regla del matcher NO s'implementa aquí; aquesta sembra
només deixa la dada preparada.

**EL POM BASE ES RESOL PER L'ÀLIES QUE JA HI HA A LA BD, NO PER CAP ID DE FULL.** Els
`pom_id` del full CATALEG són de PROD i no valen a staging (v.
`docs/diagnosis/DIAGNOSI_BROWNIE_V3_POM_ID.md`). El codi base del germà (A, B, R2…) ja és un
àlies viu de Brownie; el seu POM és la font. Si un germà JA existeix apuntant a un altre
POM, **no es repunta**: es reporta i es deixa estar. Repuntar un àlies viu en silenci és
precisament el dany que aquesta sembra ha d'evitar.

Idempotent: `update_or_create` per (customer, client_code), cap delete. --dry-run per defecte.

    python manage.py seed_brownie_germans                # DRY-RUN
    python manage.py seed_brownie_germans --no-dry-run   # escriu
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django_tenants.utils import schema_context

from fhort.pom.models import CustomerPOMAlias
from fhort.tasks.models import Customer

CUSTOMER_CODI = 'BRW'
TENANT = 'fhort'

#: (codi_germà, codi_base, mesura, què és la instància segons el doc oficial).
#: L'última columna és DOCUMENTACIÓ, no es desa: és la resposta que ha de donar una persona.
GERMANS = [
    ('A2',  'A',   'Chest width',     '2a instància'),
    ('A3',  'A',   'Chest width',     '3a instància'),
    ('B4',  'B',   'Waist width',     '2a instància'),
    ('B6',  'B',   'Waist width',     '3a instància'),
    # B1 JA existeix com a àlies de Brownie apuntant al mateix POM que B: el doc oficial en
    # diu «Stretched waist width», o sigui B en estat EXTENDED (decisió Agus 05/08). La
    # sembra només hi afegeix la marca; el vincle ja era correcte.
    ('B1',  'B',   'Waist width',     'estat EXTENDED'),
    ('B3',  'B',   'Waist width',     'EXTENDED · 2a instància'),
    ('B5',  'B',   'Waist width',     'EXTENDED · 3a instància'),
    ('UT2', 'UT1', 'Loops',           '2a instància'),
    ('R4',  'R2',  'Pocket width',    '2a butxaca'),
    ('R6',  'R2',  'Pocket width',    '3a butxaca'),
    ('R5',  'R3',  'Pocket length',   '2a butxaca'),
    ('R7',  'R3',  'Pocket length',   '3a butxaca'),
    ('TR1', 'TR',  'Placket height',  '2a instància'),
    ('V1',  'V',   'Ruffle height',   '2a instància'),
    ('V2',  'V',   'Ruffle height',   '3a instància'),
    ('JTL', 'JTA', 'Sleeve strap',    '2a instància'),
]

#: Els quatre germans del full que NO se sembren, i per què. Es reporten sempre: un germà
#: que falta en silenci és indistingible d'un germà que no s'ha declarat mai.
RETINGUTS = [
    ('PR2', 'PR1', 'Les DUES fonts es contradiuen. El full CATALEG el declara POM PROPI '
                   '(«Pocket position from waistband», ✅ RESTITUÏT · creat el 03/08 a la '
                   'reparació del 357, «NO es retira») i el full GERMANS_OFICIALS el declara '
                   '2a butxaca de PR1. Són lectures incompatibles del mateix codi, i la del '
                   'CATALEG té dada real al darrere (POMMaster 357 · PKT WB · Pocket '
                   'placement from waistband). Decisió d\'Agus.'),
    ('PR3', 'PR1', 'Retingut AMB PR2 i no per mèrit propi: si PR2 resulta ser un POM propi, '
                   'la parella PR2/PR3 del full s\'ha de rellegir sencera. Mig aplicar-la '
                   'deixaria una 3a butxaca sense 2a.'),
    ('G2',  'G1',  'Bloquejat pel rebateig G1↔D1 de F1, que encara no s\'ha fet. Avui '
                   'l\'àlies G1 de Brownie apunta al POMMaster 453 «Bottom hem / Bottom rib '
                   'height», que és el que ha de passar a dir-se D1; el «2n canalé» és '
                   'germà del G1 NOU (Rib height), que encara no existeix. Sembrar-lo ara el '
                   'lligaria al baix de la faldilla.'),
    ('G3',  'G1',  'Íd. G2 — 3r canalé.'),
]


class Command(BaseCommand):
    help = "Sembra els àlies d'instància oficials de Brownie (full GERMANS_OFICIALS)."

    def add_arguments(self, parser):
        parser.add_argument('--no-dry-run', action='store_true')
        parser.add_argument('--schema', default=TENANT)

    def handle(self, *args, **opts):
        dry = not opts['no_dry_run']
        schema = opts['schema']
        head = 'DRY-RUN (cap escriptura)' if dry else 'ESCRIVINT'
        self.stdout.write(self.style.WARNING(
            f'=== seed_brownie_germans · schema={schema} · {head} ==='))

        creats = actualitzats = 0
        base_absent, divergents = [], []
        linies = []

        with schema_context(schema), transaction.atomic():
            brw = Customer.objects.filter(codi=CUSTOMER_CODI).first()
            if not brw:
                raise CommandError(f'Customer {CUSTOMER_CODI} no existeix a {schema}.')

            bases = {
                a.client_code: a
                for a in CustomerPOMAlias.objects.filter(
                    customer=brw, client_code__in={b for _, b, _, _ in GERMANS})
                .select_related('pom')
            }

            for codi, base, mesura, instancia in GERMANS:
                b = bases.get(base)
                if not b or not b.pom_id:
                    base_absent.append((codi, base))
                    continue

                # Un germà que ja existeix apuntant a un altre POM NO es repunta.
                actual = CustomerPOMAlias.objects.filter(
                    customer=brw, client_code=codi).select_related('pom').first()
                if actual and actual.pom_id and actual.pom_id != b.pom_id:
                    divergents.append((codi, actual.pom_id, actual.pom.nom_client,
                                       b.pom_id, b.pom.nom_client))
                    continue

                _, creat = CustomerPOMAlias.objects.update_or_create(
                    customer=brw, client_code=codi,
                    defaults={
                        'pom': b.pom,
                        'es_instancia': True,
                        'origen': 'DICCIONARI',
                        'pendent_revisio': False,
                    },
                )
                creats += int(creat)
                actualitzats += int(not creat)
                linies.append(f'  {codi:4} → {base:4} · pom {b.pom_id} ({b.pom.nom_client}) '
                              f'· {mesura} · {instancia} · {"CREAT" if creat else "actualitzat"}')

            if dry:
                transaction.set_rollback(True)

        for l in linies:
            self.stdout.write(l)

        self.stdout.write(f'\n── RECOMPTE: {creats} creats · {actualitzats} actualitzats '
                          f'· {len(GERMANS)} declarats ──')

        self.stdout.write(f'\n── RETINGUTS (declarats al full, NO sembrats): {len(RETINGUTS)} ──')
        for codi, base, motiu in RETINGUTS:
            self.stdout.write(f'  {codi} (→ {base}): {motiu}')

        if base_absent:
            self.stdout.write(self.style.ERROR(
                f'\n── BASE ABSENT (germà no sembrat): {len(base_absent)} ──'))
            for codi, base in base_absent:
                self.stdout.write(f'  {codi}: l\'àlies base {base!r} no existeix o no té POM.')

        if divergents:
            self.stdout.write(self.style.ERROR(
                f'\n── DIVERGENTS (NO repuntats, decisió humana): {len(divergents)} ──'))
            for codi, pid, pnom, bid, bnom in divergents:
                self.stdout.write(f'  {codi}: apunta a {pid} ({pnom}); el full el vol a '
                                  f'{bid} ({bnom}). Es deixa com està.')

        self.stdout.write(self.style.SUCCESS(f'\n=== FET ({head}) ==='))
