"""R7 — una sola GradingVersion activa per SizeFitting, i que ho digui la BD.

L'invariant ja el respectava el codi: `bump_grading_version_and_generate`
(`pom/services.py:684`) desactiva TOTES les actives abans de crear la nova. Però era una
invariant de CORTESIA — viva només mentre tothom passés per allà—, i el motor de patrons
en depèn per saber quina versió mana. Una segona activa hauria fet que dues superfícies
llegissin talles diferents del mateix model: és exactament el bug que G6/T1 acaba de
tancar (`s6_views.py` servia una versió desactivada), i el que el fa possible és que la
BD no tingui cap opinió.

**Auditat abans d'aplicar** (G6-B2/T3, `SELECT` sobre staging, schema `fhort`):
`GradingVersion.objects.filter(is_active=True).values('size_fitting_id').annotate(n=Count)
.filter(n__gt=1)` → **cap duplicat**. La constraint entra sense violar cap fila viva.

**CAP constraint sobre `aprovada`**, i no és un oblit: l'historial d'aprovades és LEGÍTIM.
Un SizeFitting pot tenir moltes versions signades al llarg del temps (i n'ha de poder tenir:
un segell vell continua dient què es va signar aquell dia). El que no pot tenir és dues
versions vigents alhora — `aprovada` i `is_active` són ortogonals, i només la segona és una
invariant d'unicitat.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitting', '0015_fittingsession_finished_at_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='gradingversion',
            constraint=models.UniqueConstraint(
                fields=['size_fitting'],
                condition=models.Q(is_active=True),
                name='gradingversion_una_sola_activa_per_sf',
            ),
        ),
    ]
