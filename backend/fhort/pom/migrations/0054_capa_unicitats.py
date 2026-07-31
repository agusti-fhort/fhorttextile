"""C1/T3 — les unicitats de `pom` incorporen la CAPA.

`AlterUniqueTogether` fa DROP de l'índex únic vell i ADD del nou en una sola operació.

SEGUR PER CONSTRUCCIÓ, no per sort: la clau nova té les mateixes columnes que la vella
**més una**, o sigui que és estrictament MÉS PERMISSIVA. No pot rebutjar cap fila que abans
passés, i no pot deixar entrar cap duplicat que abans es barrés. A més, avui totes les files
tenen `capa='exterior'` (constant), de manera que les dues claus classifiquen exactament
igual: 0 duplicats latents possibles.

Qui de debò impedeix una segona capa abans que C2/C3 hi adaptin els consumidors no és
aquesta clau sinó la COMPORTA de T4 (CHECK capa='exterior').

Cap canvi de comportament: cap escriptor pot produir avui una fila que la clau vella no
acceptés.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0053_capa_mesures'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='garmentpommap',
            unique_together={('garment_type_item', 'pom', 'capa')},
        ),
        migrations.AlterUniqueTogether(
            name='itembasemeasurement',
            unique_together={('base_set', 'pom', 'capa')},
        ),
    ]
