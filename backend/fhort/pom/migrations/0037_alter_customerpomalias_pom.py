"""CustomerPOMAlias.pom → nullable (QA-S8-R1).

Un àlies SENSE pom és VOCABULARI DEL CLIENT PENDENT DE MAPAR: el client anomena una mesura i
encara no sabem a quin POM canònic correspon. És un estat legítim del domini, no una dada a
mitges — i és el que permet DESVINCULAR un mapatge fals (12 àlies de BRW apuntaven a un POM
que una altra mesura del mateix client ja reclamava) sense haver d'esborrar la nomenclatura,
que és informació bona del client.

Precondició de seguretat: `find_pom_master` (models_app/extraction_views.py) filtra els àlies
per `pom__isnull=False`. Un àlies sense destí no pot vincular res i el matcher no el mira.

Només afluixa una constraint (NOT NULL → NULL): no reescriu cap fila i és reversible mentre no
existeixi cap NULL. Cap dada existent en té: totes les files actuals conserven el seu pom.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0036_gradingruleset_origen'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customerpomalias',
            name='pom',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='client_aliases', to='pom.pommaster'),
        ),
    ]
