"""PatternSegment guanya `origen` i `nom` (Taller de patró · W1).

La segmentació gir→gir és una PROPOSTA del CAD, no la veritat de la costura. `origen`
distingeix els trams DERIVATS (auto) dels DECLARATS pel patronista, que són els que de debò
es cusen. `nom` és l'etiqueta lliure del declarat ("costura lateral").

Els segments que ja hi ha són tots derivats: el `default='auto'` els hi deixa **sense
reescriure cap fila** (Django omple la columna nova amb el default a l'AddField). No hi ha
cap segment declarat encara — l'eina que els crea neix en aquest mateix paquet.

Només afegeix dues columnes: cap dada existent canvia de significat.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patterns', '0003_exportacknowledgement'),
    ]

    operations = [
        migrations.AddField(
            model_name='patternsegment',
            name='nom',
            field=models.CharField(blank=True, max_length=120, null=True),
        ),
        migrations.AddField(
            model_name='patternsegment',
            name='origen',
            field=models.CharField(choices=[('auto', 'Derivat (gir a gir)'), ('declarat', 'Declarat pel patronista')], default='auto', max_length=10),
        ),
    ]
