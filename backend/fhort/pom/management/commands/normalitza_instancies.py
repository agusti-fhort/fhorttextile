"""Normalitza els slugs d'instància a l'ordre canònic. Per omissió, NOMÉS MIRA.

    python manage.py normalitza_instancies --dry-run
    python manage.py normalitza_instancies --dry-run --esperades 4
    python manage.py normalitza_instancies --aplica          ← escriu

⚠️ Aquesta comanda i la migració de dades criden EL MATEIX codi (`pom/normalitza_instancies.py`):
el que es vegi aquí és exactament el que farà el tren.
"""
from django.apps import apps as registre
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from fhort.pom.normalitza_instancies import aplica, informe, planifica


class Command(BaseCommand):
    help = "Posa els slugs d'instància compostos en ordre canònic (llei 26/08)."

    def add_arguments(self, p):
        p.add_argument('--aplica', action='store_true',
                       help='Escriu. Sense això només mira (per defecte).')
        # Explícit encara que sigui el defecte: qui escriu `--dry-run` vol dir «no escriguis»,
        # i que la comanda l'accepti és el que fa que aquella frase no es quedi en un malentès.
        p.add_argument('--dry-run', action='store_true', dest='dry_run',
                       help='Només mira (és el defecte; es pot dir explícitament).')
        p.add_argument('--esperades', type=int, default=None,
                       help='Canari: atura si el nombre de canvis no és exactament aquest.')

    def handle(self, *a, **o):
        schema = getattr(connection, 'schema_name', '?')
        if o.get('dry_run') or not o['aplica']:
            canvis, colisions, saltades = planifica(registre)
            informe(schema, canvis, colisions, saltades, aplicat=False)
            self.stdout.write(f'[{schema}] canvis={len(canvis)} '
                              f'colisions={len(colisions)} saltades={len(saltades)}')
            for e, pk, v, n in canvis:
                self.stdout.write(f'    {e} pk={pk}  «{v}» → «{n}»')
            for e, pk, v, n, ocu in colisions:
                self.stdout.write(self.style.ERROR(
                    f'    COL·LISIÓ {e} pk={pk} «{v}»→«{n}» ja el té pk={ocu}'))
            for e, pk, v, motiu in saltades:
                self.stdout.write(self.style.WARNING(f'    SALTADA {e} pk={pk} «{v}» — {motiu}'))
            return
        with transaction.atomic():
            canvis, saltades = aplica(registre, schema, esperades=o['esperades'])
        self.stdout.write(self.style.SUCCESS(
            f'[{schema}] {len(canvis)} fila/es normalitzada/es · {len(saltades)} saltada/es'))
