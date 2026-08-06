"""Sembra del diccionari canònic d'instàncies de mesura (`MeasurementInstance`, D-31.26).

Calca `seed_measurement_layers` fil per randa —**`update_or_create` per clau natural, mai
`delete`**, i el mateix contingut a `public` i a cada tenant— perquè les dues taules són
bessones i el mateix argument d'infraestructura les governa: `fhort.pom` viu a SHARED i a
TENANT alhora i l'app resol el catàleg des de la còpia del tenant.

Es pot executar tantes vegades com calgui: la segona passada actualitza i no duplica res.
Una instància que un tenant s'hagi creat pel seu compte (`is_system=False`) no la toca.

El contingut és el full INSTANCIES de `docs/BROWNIE_CATALEG_POM_v3.xlsx`: vuit POSICIONS i
dos ESTATS. **El full és la font, no aquest fitxer**; el que és contracte és el `slug`,
perquè és el que desen les columnes `instancia` (llei G9: mai per PK) i el que el front ja
desmunta per guions a `frontend/src/utils/capaInstancia.js`.

⚠️ ELS NOMS SÓN DE TREBALL, com els de les capes: pendents de la nomenclatura definitiva de
la Montse. Canviar un nom és tornar a passar aquesta sembra; canviar un slug seria una
migració de dades.

Ús:  python manage.py seed_measurement_instances
     python manage.py seed_measurement_instances --schema fhort   # només un schema
     python manage.py seed_measurement_instances --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django_tenants.utils import get_tenant_model, schema_context

from fhort.pom.models import MeasurementInstance as I

#: (slug, sufix, nom_en, nom_ca, nom_es). L'ordre DINS de cada eix és el `display_order`.
#:
#: El `sufix` és el que el sistema PROPOSA en compondre el codi de la germana (B→BT,
#: FS→FSCF), i va buit allà on el full diu que no en porta:
#:   · `waistband_seam` és un DATUM —punt d'unió de referència, precedent del sector: HPS—
#:     i es diu a la descripció, no al codi;
#:   · cap ESTAT no en porta: fan servir el codi oficial del client si existeix (B1 =
#:     «stretched waist width») o la descripció.
POSICIONS = [
    ('left',           'L',  'Left',            'Esquerra',           'Izquierda'),
    ('right',          'R',  'Right',           'Dreta',              'Derecha'),
    ('top',            'T',  'Top',             'Superior',           'Superior'),
    ('bottom',         'B',  'Bottom',          'Inferior',           'Inferior'),
    # CF/CB NO es tradueixen: són acrònims del sector, com HPS. Escriure'ls «Centre
    # davant» a la fitxa catalana els faria irreconeixibles per al fabricant.
    ('cf',             'CF', 'CF',              'CF',                 'CF'),
    ('cb',             'CB', 'CB',              'CB',                 'CB'),
    ('side',           'S',  'Side seam',       'Costura lateral',    'Costura lateral'),
    ('waistband_seam', '',   'Waistband seam',  'Costura de cinturilla', 'Costura de pretina'),
]

ESTATS = [
    ('relaxed',  '', 'Relaxed',  'Relaxada', 'Relajada'),
    # «Stretched» i «stretched out» dels documents de Brownie SÓN aquest mateix estat (decisió
    # d'Agus, reiterada). El nom canònic és un de sol i va NET: la barra el convertia en dos
    # noms dins d'un, i sortia així a la píndola i al modal de la identitat de la fila.
    #
    # El vocabulari del client hi arriba pel seu camí —el codi oficial al `nom_fitxa` de la fila
    # (B1 = «stretched waist width») o el `CustomerPomAlias`—, no duplicant-lo dins del nom del
    # diccionari ni afegint una segona fila per al mateix estat.
    #
    # Les dades ja sembrades les neteja `pom/0060_extended_net.py`. Les dues bandes han d'anar
    # juntes: sense aquesta línia, la propera passada d'aquesta sembra tornaria a posar la barra.
    ('extended', '', 'Extended', 'Estirada', 'Estirada'),
]

INSTANCIES = [(I.EIX_POSICIO, POSICIONS), (I.EIX_ESTAT, ESTATS)]


def sembra(schema: str, dry_run: bool = False) -> tuple[int, int]:
    """Sembra el diccionari en un schema. → (creades, actualitzades). MAI esborra."""
    files = [(eix, *f) for eix, grup in INSTANCIES for f in grup]
    creades = actualitzades = 0
    with schema_context(schema):
        if dry_run:
            existents = set(I.objects.values_list('slug', flat=True))
            noves = [f for f in files if f[1] not in existents]
            return len(noves), len(files) - len(noves)

        with transaction.atomic():
            for eix, grup in INSTANCIES:
                for ordre, (slug, sufix, en, ca, es) in enumerate(grup, start=1):
                    _, creada = I.objects.update_or_create(
                        slug=slug,
                        defaults={
                            'nom_en': en, 'nom_ca': ca, 'nom_es': es,
                            'eix': eix,
                            'sufix': sufix,
                            'is_system': True,
                            'pendent_revisio': False,
                            'origen': I.ORIGEN_SEED,
                            'display_order': ordre,
                        },
                    )
                    creades += int(creada)
                    actualitzades += int(not creada)
    return creades, actualitzades


class Command(BaseCommand):
    help = "Sembra el diccionari canònic d'instàncies de mesura (idempotent, mai esborra)."

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
            # `public` és una fila més de la taula de tenants: la llista ja els porta tots dos.
            schemas = list(
                get_tenant_model().objects.values_list('schema_name', flat=True))

        for sch in schemas:
            creades, actualitzades = sembra(sch, dry_run=dry)
            with schema_context(sch):
                total = I.objects.count()
                per_eix = {
                    eix: I.objects.filter(eix=eix).count()
                    for eix, _ in I.EIX_CHOICES
                }
            prefix = '[dry-run] ' if dry else ''
            self.stdout.write(
                f'  {prefix}[{sch}] creades: {creades} · actualitzades: {actualitzades} · '
                f'total ara: {total} ({per_eix[I.EIX_POSICIO]} posicions · '
                f'{per_eix[I.EIX_ESTAT]} estats)')

        if not dry:
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Diccionari d'instàncies sembrat a {len(schemas)} schema/es "
                f'({len(POSICIONS)} posicions + {len(ESTATS)} estats, idempotent).'))
