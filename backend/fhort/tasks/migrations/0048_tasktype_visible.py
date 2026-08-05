"""T1 · `visible` al catàleg de tasques, i les dues que avui no toquen.

`visible` NO és `active`. Desactivar un tipus el retira: les seves tasques vives queden
penjades d'un tipus mort i cap porta les torna a obrir. El que calia era més fluix — «vàlid,
però la UI encara no l'ofereix»— i per això és un camp propi amb default True: tot el catàleg
existent es queda exactament com estava.

Les dues que s'amaguen surten del dump real dels dos tenants (T0.1), no d'una llista escrita
de memòria:

  · `bom`   · Definició BOM      · Interna · eina `fitxa`/`bom` · sense pantalla
  · `audit` · Auditoria de model · Externa-lliure               · sense pantalla

Cap de les dues té superfície on treballar, i totes dues tornaran. **No s'esborren i no es
desactiven**: `visible=False` i prou.

Idempotent i per tenant (`tasks_tasktype` no existeix a `public`, v. 0046). Explícit als DOS
sentits —les dues a False, la resta a True— perquè la migració deixi el catàleg en un estat
CONEGUT i no només hi afegeixi marques: si algú l'ha corregut a mitges, tornar-la a córrer el
deixa igual.
"""
from django.db import migrations, models

AMAGADES = ['bom', 'audit']


def amaga(apps, schema_editor):
    TaskType = apps.get_model('tasks', 'TaskType')
    TaskType.objects.filter(code__in=AMAGADES).update(visible=False)
    TaskType.objects.exclude(code__in=AMAGADES).update(visible=True)


def desfes(apps, schema_editor):
    """Tot torna a ser oferible: és el default del camp i l'estat d'abans d'aquest tram."""
    TaskType = apps.get_model('tasks', 'TaskType')
    TaskType.objects.update(visible=True)


class Migration(migrations.Migration):

    dependencies = [('tasks', '0047_timerentrada_origen')]

    operations = [
        migrations.AddField(
            model_name='tasktype',
            name='visible',
            field=models.BooleanField(
                default=True,
                help_text="El catàleg l'ofereix a la UI. False = vàlid però no oferible (encara)."),
        ),
        migrations.RunPython(amaga, desfes),
    ]
