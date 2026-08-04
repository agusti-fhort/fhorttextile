"""Sembra del catàleg canònic de capes de mesura (`MeasurementLayer`).

Calca `seed_pattern_piece_roles`: **`update_or_create` per clau natural, mai `delete`**, i
el mateix contingut a `public` i a cada tenant, perquè `fhort.pom` viu a SHARED i a TENANT
alhora i l'app resol el catàleg des de la còpia del tenant.

Es pot executar tantes vegades com calgui: la segona passada actualitza i no duplica res.
Una capa que un tenant s'hagi creat pel seu compte (`is_system=False`) no la toca — la
sembra només mana sobre les seves.

⚠️ NOMS PROVISIONALS. Els tres noms de cada capa són de treball, **pendents de la
nomenclatura definitiva de la Montse**. El que és contracte és el `slug`: és el que
referencien les columnes `capa` de les taules de mesura (llei G9: mai per PK). Canviar un
nom és tornar a passar aquesta sembra; canviar un slug seria una migració de dades.

Ús:  python manage.py seed_measurement_layers
     python manage.py seed_measurement_layers --schema fhort   # només un schema
     python manage.py seed_measurement_layers --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import get_tenant_model, schema_context

from fhort.pom.models import MeasurementLayer as L

#: (slug, nom_en, nom_ca, nom_es). L'ordre de la llista ÉS el `display_order`.
#: `exterior` va primera i és EL DEFECTE de tot el sistema: el que fins avui era «la
#: mesura», sense adjectiu. Les altres cinc encara no les pot fer servir ningú — la
#: comporta CHECK de C1 les bloqueja a BD fins que C4 la retiri.
CAPES = [
    ('exterior',  'Shell',        'Exterior',  'Exterior'),
    ('folre',     'Lining',       'Folre',     'Forro'),
    ('entretela', 'Interfacing',  'Entretela', 'Entretela'),
    # `Relleno / Guata`: el castellà en porta dos perquè al taller es diuen les dues coses i
    # cap de les dues no és un sinònim de l'altra prou net per triar-ne una (D-31.22, Agus
    # 04/08). El nom és per als ulls; el contracte és el slug, que no es toca.
    ('farciment', 'Padding',      'Farciment', 'Relleno / Guata'),
    ('reforc',    'Underlining',  'Reforç',    'Refuerzo'),
    ('fornitura', 'Trim',         'Fornitura', 'Fornitura'),
]


def sembra(schema: str, dry_run: bool = False) -> tuple[int, int]:
    """Sembra el catàleg en un schema. → (creats, actualitzats). MAI esborra."""
    creats = actualitzats = 0
    with schema_context(schema):
        if dry_run:
            existents = set(L.objects.values_list('slug', flat=True))
            nous = [s for s, *_ in CAPES if s not in existents]
            return len(nous), len(CAPES) - len(nous)

        with transaction.atomic():
            for ordre, (slug, en, ca, es) in enumerate(CAPES, start=1):
                _, creat = L.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'nom_en': en, 'nom_ca': ca, 'nom_es': es,
                        'is_system': True,
                        'pendent_revisio': False,
                        'origen': L.ORIGEN_SEED,
                        'display_order': ordre,
                    },
                )
                creats += int(creat)
                actualitzats += int(not creat)
    return creats, actualitzats


class Command(BaseCommand):
    help = 'Sembra el catàleg canònic de capes de mesura (idempotent, mai esborra).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema', default='',
            help='Només aquest schema. Per defecte: public i tots els tenants.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Diu què faria, sense escriure res.')

    def handle(self, *args, **opts):
        dry = opts['dry_run']
        if opts['schema']:
            schemas = [opts['schema']]
        else:
            # `public` és una fila més de la taula de tenants, o sigui que la llista ja
            # els porta tots dos: el schema públic i cada client.
            schemas = list(
                get_tenant_model().objects.values_list('schema_name', flat=True))

        for sch in schemas:
            creats, actualitzats = sembra(sch, dry_run=dry)
            with schema_context(sch):
                total = L.objects.count()
            prefix = '[dry-run] ' if dry else ''
            self.stdout.write(
                f'  {prefix}[{sch}] creats: {creats} · actualitzats: {actualitzats} · '
                f'total ara: {total}')

        if not dry:
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Catàleg de capes de mesura sembrat a {len(schemas)} schema/es '
                f'({len(CAPES)} capes, idempotent).'))
