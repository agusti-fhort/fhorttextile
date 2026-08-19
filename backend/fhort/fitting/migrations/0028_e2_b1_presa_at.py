"""E2/B1 — LA MARCA DEL GEST a `PieceFittingLine.presa_at`.

`linia_te_contingut` decidia «algú ha mesurat aquesta cel·la?» comparant `valor_real` amb
`valor_teoric`, i la línia NEIX amb els dos iguals (`create_piece_fitting`). El predicat, doncs,
només veia les preses que **per casualitat** no coincidien amb la teòrica.

E2b posa la teòrica a la cel·la en FANTASMA i deixa que l'usuari la confirmi tal qual. Aquest
gest produeix exactament l'estat del naixement, i cap predicat derivat de valors el pot
distingir: calia una marca que digui el GEST, no el número.

ADDITIVA I SENSE BACKFILL, a posta: les files existents queden a `NULL` i
`linia_te_contingut` les segueix resolent pel predicat de sempre (la marca es mira primera; la
inferència queda darrere). **Cap fila canvia de veredicte per aquesta migració.** Un backfill
seria pitjor que no fer-ne: hauria d'endevinar quines de les files velles van ser un gest, que
és precisament el que no es pot saber i el motiu del camp.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitting', '0027_set2_12_retirada_comportes_garment'),
    ]

    operations = [
        migrations.AddField(
            model_name='piecefittingline',
            name='presa_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
