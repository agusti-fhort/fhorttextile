"""F3.1b · fotografia de TaskTimeEstimate llegida DIRECTAMENT de la BD.

No fa servir cap sortida de `recompute_welford`: l'auditoria d'un command no pot ser
l'OK del propi command. Escriu una línia per cel·la, ordenada, per poder fer `diff`
entre l'abans i el després.

Ús:  python manage.py shell < scripts_tmp/f31b_snapshot_welford.py > fitxer.txt
"""
from django_tenants.utils import get_tenant_model, schema_context

from fhort.tasks.models import TaskTimeEstimate
from fhort.tasks.services_i import WELFORD_MIN_SAMPLES

for tenant in get_tenant_model().objects.exclude(schema_name='public').order_by('schema_name'):
    with schema_context(tenant.schema_name):
        files = list(TaskTimeEstimate.objects.select_related('task_type')
                     .order_by('garment_type_item_id', 'task_type__code'))
        print(f'== {tenant.schema_name} · {len(files)} cel·les ==')
        mana = 0
        per_tipus = {}
        for c in files:
            governa = c.n >= WELFORD_MIN_SAMPLES and c.mean_minutes > 0
            mana += 1 if governa else 0
            d = per_tipus.setdefault(c.task_type.code, [0, 0, 0.0])
            d[0] += 1
            d[1] += c.n
            d[2] += float(c.mean_minutes) * c.n
            print(f'  item={c.garment_type_item_id or "-":<6} {c.task_type.code:<16} '
                  f'n={c.n:<4} mean={float(c.mean_minutes):>10.2f} m2={float(c.m2):>14.4f} '
                  f'seed={c.estimated_minutes} {"MANA" if governa else ""}')
        print(f'  -- {tenant.schema_name}: {mana} cel·les governen (n>={WELFORD_MIN_SAMPLES})')
        print(f'  -- per TaskType (cel·les · n total · mitjana ponderada):')
        for code in sorted(per_tipus):
            celles, n, suma = per_tipus[code]
            pond = (suma / n) if n else 0.0
            print(f'     {code:<16} {celles:>4} cel·les · n={n:<5} · {pond:>10.2f} min')
