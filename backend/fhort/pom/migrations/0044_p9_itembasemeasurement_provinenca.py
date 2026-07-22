"""P9 — PROVINENÇA I AUTORIA a `ItemBaseMeasurement` (additiva).

Condició dura de **D-PROM** (DECISIONS.md §PAQUET ITEM-PLANTILLA): sense aquests camps una
promoció model→item és **irrecuperable i anònima**. Fins avui un valor de plantilla no deia
ni qui l'havia posat, ni quan, ni d'on venia (risc 9 de la DIAGNOSI_GTI_PLANTILLA).

  · `origen` — MANUAL | PROMOTED | IMPORTED. NOMÉS tres: els 8 de `BaseMeasurement` són
    estats d'INSTÀNCIA i no volen dir res a la capa de plantilla.
  · `created_at` / `updated_at` — `null=True` a propòsit: de les files que ja existeixen no
    sabem quan es van crear. `AddField` amb `auto_now_add` les estampa amb l'hora de la
    MIGRACIÓ, que és una data falsa; el `RunPython` les torna a NULL. Millor mudes que
    mentideres.
  · `updated_by` — SET_NULL: esborrar un usuari no s'ha d'endur el valor del taller.

BACKFILL d'`origen`: `AddField` amb `default='MANUAL'` ja estampa totes les files existents,
i és correcte — l'única superfície d'escriptura que ha existit mai és el ViewSet CONFIGURE,
o sigui, mà humana. El `RunPython` ho AUDITA i ho fa constar (cap migració que toca la taula
ha de ser silenciosa, mateixa disciplina que la 0042) i, a més, torna a NULL les dates falses
que l'AddField acaba de fabricar.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def backfill(apps, schema_editor):
    """Neteja les dates falses de les files preexistents i audita el backfill d'`origen`."""
    schema = schema_editor.connection.schema_name
    IBM = apps.get_model('pom', 'ItemBaseMeasurement')
    # `.order_by()` OBLIGATORI: el Meta.ordering del model ordena per `garment_type_item`, i
    # això força un JOIN a `tasks_garmenttypeitem` — taula que NO existeix a 'public' (`pom` és
    # app SHARED, `tasks` és només-tenant). Sense això la migració peta a l'esquema public.
    total = IBM.objects.order_by().count()
    manual = IBM.objects.order_by().filter(origen='MANUAL').count()
    per_item = {}
    for gti_id in IBM.objects.order_by().values_list('garment_type_item_id', flat=True):
        per_item[gti_id] = per_item.get(gti_id, 0) + 1
    print(f'\n[P9 · ItemBaseMeasurement] esquema "{schema}": {total} fila/es · '
          f'{manual} amb origen=MANUAL')
    # Les files que ja existien abans d'aquesta migració han rebut `created_at`/`updated_at`
    # = hora de la migració (efecte d'`auto_now_add`/`auto_now` a l'AddField). Això afirma una
    # cosa que no sabem. Es tornen a NULL: la data d'aquests 37 valors és desconeguda i el
    # camp ja està preparat per dir-ho.
    esborrades = IBM.objects.order_by().update(created_at=None, updated_at=None)
    for gti_id, n in sorted(per_item.items()):
        print(f'       garment_type_item={gti_id}: {n} fila/es')
    print(f'       dates preexistents posades a NULL (desconegudes): {esborrades}')


def noop(apps, schema_editor):
    """Res a desfer: els AddField els reverteix Django sol i s'enduen les columnes senceres."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0043_retire_gradingruleset_target_fk'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='itembasemeasurement',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='itembasemeasurement',
            name='origen',
            field=models.CharField(choices=[('MANUAL', 'Introduït manualment'), ('PROMOTED', "Promogut des d'un model"), ('IMPORTED', 'Importat de paquet')], default='MANUAL', max_length=20),
        ),
        migrations.AddField(
            model_name='itembasemeasurement',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddField(
            model_name='itembasemeasurement',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='item_base_measurements_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(backfill, noop),
    ]
