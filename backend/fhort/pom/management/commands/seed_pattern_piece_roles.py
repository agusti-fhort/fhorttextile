"""Sembra del catàleg canònic de rols de peça de patró (`PatternPieceRole`).

Calca `extend_pom_catalog`: **`update_or_create` per clau natural, mai `delete`**, i el
mateix contingut a `public` i a cada tenant, perquè `fhort.pom` viu a SHARED i a TENANT
alhora i l'app resol el catàleg des de la còpia del tenant.

Es pot executar tantes vegades com calgui: la segona passada actualitza i no duplica res.
Un rol que un tenant s'hagi creat pel seu compte (`is_system=False`) no el toca — la
sembra només mana sobre els seus.

Ús:  python manage.py seed_pattern_piece_roles
     python manage.py seed_pattern_piece_roles --schema fhort   # només un schema
     python manage.py seed_pattern_piece_roles --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import get_tenant_model, schema_context

from fhort.pom.models import PatternPieceRole as R

#: (slug, classe, nom_en, nom_ca, nom_es). L'ordre de la llista ÉS el `display_order`.
ROLS = [
    ('front',         R.CLASSE_COS,        'Front',         'Davant',              'Delantero'),
    ('back',          R.CLASSE_COS,        'Back',          'Esquena',             'Espalda'),
    ('body',          R.CLASSE_COS,        'Body',          'Cos',                 'Cuerpo'),
    ('sleeve',        R.CLASSE_MANIGA,     'Sleeve',        'Màniga',              'Manga'),
    ('cuff',          R.CLASSE_BANDA,      'Cuff',          'Puny',                'Puño'),
    ('collar',        R.CLASSE_BANDA,      'Collar',        'Coll',                'Cuello'),
    ('collar_stand',  R.CLASSE_BANDA,      'Collar stand',  'Peu de coll',         'Pie de cuello'),
    ('neckband',      R.CLASSE_BANDA,      'Neckband',      'Tira de coll',        'Tira de cuello'),
    ('yoke',          R.CLASSE_COS,        'Yoke',          'Canesú',              'Canesú'),
    ('facing',        R.CLASSE_COMPLEMENT, 'Facing',        'Vista',               'Vista'),
    ('lining',        R.CLASSE_COMPLEMENT, 'Lining',        'Folre',               'Forro'),
    ('interlining',   R.CLASSE_COMPLEMENT, 'Interlining',   'Entretela',           'Entretela'),
    ('pocket',        R.CLASSE_COMPLEMENT, 'Pocket',        'Butxaca',             'Bolsillo'),
    ('pocket_flap',   R.CLASSE_COMPLEMENT, 'Pocket flap',   'Tapeta de butxaca',   'Tapa de bolsillo'),
    ('pocket_facing', R.CLASSE_COMPLEMENT, 'Pocket facing', 'Vista de butxaca',    'Vista de bolsillo'),
    ('waistband',     R.CLASSE_BANDA,      'Waistband',     'Cinturilla',          'Pretina'),
    ('belt_loop',     R.CLASSE_TIRA,       'Belt loop',     'Trava',               'Trabilla'),
    ('fly',           R.CLASSE_COMPLEMENT, 'Fly',           'Bragueta',            'Bragueta'),
    ('zip_guard',     R.CLASSE_COMPLEMENT, 'Zip guard',     'Guarda cremallera',   'Tapa cremallera'),
    ('placket',       R.CLASSE_BANDA,      'Placket',       'Tapeta',              'Tapeta'),
    ('panel',         R.CLASSE_PANELL,     'Panel',         'Panell',              'Panel'),
    ('ruffle',        R.CLASSE_TIRA,       'Ruffle',        'Volant',              'Volante'),
    ('skirt',         R.CLASSE_COS,        'Skirt',         'Faldilla',            'Falda'),
    ('tie',           R.CLASSE_TIRA,       'Tie',           'Llaçada',             'Lazada'),
    ('strap',         R.CLASSE_TIRA,       'Strap',         'Tirant',              'Tirante'),
    ('binding',       R.CLASSE_TIRA,       'Binding',       'Biaix',               'Bies'),
    ('piping',        R.CLASSE_TIRA,       'Piping',        'Vivet',               'Vivo'),
    ('knee_patch',    R.CLASSE_COMPLEMENT, 'Knee patch',    'Genollera',           'Rodillera'),
    ('lace_strip',    R.CLASSE_TIRA,       'Lace strip',    'Tira de punta',       'Tira de encaje'),
    ('template',      R.CLASSE_COMPLEMENT, 'Template',      'Plantilla',           'Plantilla'),
]


def sembra(schema: str, dry_run: bool = False) -> tuple[int, int]:
    """Sembra el catàleg en un schema. → (creats, actualitzats). MAI esborra."""
    creats = actualitzats = 0
    with schema_context(schema):
        if dry_run:
            existents = set(R.objects.values_list('slug', flat=True))
            nous = [s for s, *_ in ROLS if s not in existents]
            return len(nous), len(ROLS) - len(nous)

        with transaction.atomic():
            for ordre, (slug, classe, en, ca, es) in enumerate(ROLS, start=1):
                _, creat = R.objects.update_or_create(
                    slug=slug,
                    defaults={
                        'nom_en': en, 'nom_ca': ca, 'nom_es': es,
                        'classe': classe,
                        'is_system': True,
                        'pendent_revisio': False,
                        'origen': R.ORIGEN_SEED,
                        'display_order': ordre * 10,
                    },
                )
                creats += int(creat)
                actualitzats += int(not creat)
    return creats, actualitzats


class Command(BaseCommand):
    help = 'Sembra el catàleg canònic de rols de peça de patró (idempotent, mai esborra).'

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
                total = R.objects.count()
            prefix = '[dry-run] ' if dry else ''
            self.stdout.write(
                f'  {prefix}[{sch}] creats: {creats} · actualitzats: {actualitzats} · '
                f'total ara: {total}')

        if not dry:
            self.stdout.write(self.style.SUCCESS(
                f'\n✓ Catàleg de rols sembrat a {len(schemas)} schema/es '
                f'({len(ROLS)} rols, idempotent).'))
