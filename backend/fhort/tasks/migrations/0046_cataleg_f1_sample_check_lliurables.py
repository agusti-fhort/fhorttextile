"""F1.6 · EL CATÀLEG DE TASQUES, POSAT AL DIA.

Tres coses, totes idempotents, totes per TENANT (`tasks_tasktype` no existeix a `public`:
`to_regclass('public.tasks_tasktype')` → NULL, verificat).

1. **`sample_check` neix.** El cens de la diagnosi pre-F1 el va buscar als tres schemes i al codi
   sencer: `grep -rn "sample_check" --include=*.py` → 0 coincidències, i cap fila a cap
   `tasks_tasktype`. La costura grading ↔ mostra no tenia tasca.

2. **`es_lliurable` se sembra.** Cert per als PRODUCTES que el client rep —la fitxa i el patró—,
   fals per a la feina intermèdia. És el que fa operatiu `services_r.ronda_lliurable`.

3. **`patronatge` marxa d'on hi sigui.** Viu NOMÉS a `fhort` (no a `los`), amb `default_order=0`
   —o sigui primer de tota llista ordenada, per sobre de `pattern_digit`— i **cap sembra del codi
   el crea**: `grep patronatge` sobre `backend/fhort/` només troba comentaris de `patterns/`. És
   una fila entrada a mà que fa divergir el catàleg canònic entre tenants (§S-8).

   El delete va GUARDAT per `count() == 0`: si algun tenant hi té feina penjada, la fila es queda
   i la migració ho diu. `TaskType.instances` és `PROTECT` — sense el guard, un tenant amb dades
   faria petar la migració a mitges.
"""
from django.db import migrations

LLIURABLES = ['tech_sheet', 'pattern_cad', 'pattern_digit', 'scaling', 'marking']

SAMPLE_CHECK = {
    'code': 'sample_check',
    'name': 'Sample check',
    'fase': 'Dev. tècnic',
    'tipus': 'Interna',
    'eina': 'escalat',
    'mode': 'presa',
    'facturable': True,
    'default_order': 47,      # entre `grading` (46) i `tech_sheet` (50)
    'active': True,
    'es_lliurable': False,
}


def sembra(apps, schema_editor):
    TaskType = apps.get_model('tasks', 'TaskType')
    ModelTask = apps.get_model('tasks', 'ModelTask')

    # 1 · sample_check (get_or_create: si ja hi és, no se li toca res)
    TaskType.objects.get_or_create(
        code=SAMPLE_CHECK['code'],
        defaults={k: v for k, v in SAMPLE_CHECK.items() if k != 'code'})

    # 2 · es_lliurable — explícit als dos sentits: la migració ha de deixar el catàleg en un
    # estat CONEGUT, no només afegir-hi marques.
    TaskType.objects.filter(code__in=LLIURABLES).update(es_lliurable=True)
    TaskType.objects.exclude(code__in=LLIURABLES).update(es_lliurable=False)

    # 3 · patronatge — només si ningú no hi ha penjat feina.
    orfe = TaskType.objects.filter(code='patronatge')
    if orfe.exists() and not ModelTask.objects.filter(task_type__code='patronatge').exists():
        orfe.delete()


def desfes(apps, schema_editor):
    """Reversible pel que es pot desfer: `es_lliurable` torna al default i `sample_check` marxa
    si ningú no l'ha fet servir. `patronatge` NO es recrea: era una fila espúria i tornar-la a
    sembrar seria reintroduir el problema."""
    TaskType = apps.get_model('tasks', 'TaskType')
    ModelTask = apps.get_model('tasks', 'ModelTask')
    TaskType.objects.update(es_lliurable=False)
    sc = TaskType.objects.filter(code='sample_check')
    if sc.exists() and not ModelTask.objects.filter(task_type__code='sample_check').exists():
        sc.delete()


class Migration(migrations.Migration):

    dependencies = [('tasks', '0045_tasktype_es_lliurable')]

    operations = [migrations.RunPython(sembra, desfes)]
