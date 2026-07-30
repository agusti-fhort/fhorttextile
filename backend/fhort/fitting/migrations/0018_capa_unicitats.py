"""C1/T3 — les unicitats de `fitting` incorporen la CAPA.

Mateix argument de seguretat que a `pom/0054_capa_unicitats`: la clau nova són les mateixes
columnes **més una**, o sigui estrictament més permissiva, i avui `capa` és constant
('exterior') a totes les files → 0 duplicats latents possibles.

El motor de grading (`generate_graded_specs`) NO es toca: segueix escrivint una fila per
(versió, POM, talla) i el default de columna hi posa la capa.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fitting', '0017_capa_mesures'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='gradedspec',
            unique_together={('grading_version', 'pom', 'size_label', 'capa')},
        ),
        migrations.AlterUniqueTogether(
            name='piecefittingline',
            unique_together={('piece_fitting', 'pom', 'size_label', 'capa')},
        ),
    ]
