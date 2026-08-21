"""TRAM F · MULTI-BREAK PER INTERVALS — el camp a la regla RESIDENT (2026-08-21).

Germana exacta de `pom/0077`: afegeix `ModelGradingRule.breaks` (JSON, NULL), additiva i sense
cap backfill. L'acta sencera viu allà i al camp del model.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('models_app', '0085_set2_t8_importsession_garment'),
    ]

    operations = [
        migrations.AddField(
            model_name='modelgradingrule',
            name='breaks',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
