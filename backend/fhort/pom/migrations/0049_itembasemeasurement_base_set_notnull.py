"""B1 (2026-07-25) — base_set passa a NOT NULL: tota mesura base viu dins un set.

Escrita a mà: makemigrations demana un default interactiu perquè no sap que 0048 ja ha farcit la
columna. No n'hi ha cap de sensat (un set per defecte no existeix) i no en cal: auditat abans
d'aplicar, 0 files òrfenes als tres schemas (public 0/0, fhort 0/37, los 0/0).

Si en un desplegament futur alguna fila arribés aquí amb base_set NULL, aquesta migració HA de
petar: vol dir un item amb mesures base i sense món declarat (sense base_size_definition), i
inventar-li el set seria pitjor que aturar-se. Vegeu la capçalera de 0048.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0048_itembaseset_backfill'),
    ]

    operations = [
        migrations.AlterField(
            model_name='itembasemeasurement',
            name='base_set',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='measurements',
                to='pom.itembaseset',
            ),
        ),
    ]
