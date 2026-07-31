"""C1/T2 — la columna `capa` a les taules de mesura de `pom`.

`GarmentPOMMap` (pertinença POM de la plantilla de l'item) i `ItemBaseMeasurement` (el
valor típic d'aquella plantilla). Referència al catàleg PER SLUG, mai per PK (llei G9):
un CharField, no un FK — el catàleg és SHARED+TENANT i aquestes taules creuen schemas.

BACKFILL: cap. `default='exterior'` a nivell de columna cobreix el 100% de les files
existents (fast-default de Postgres 11+, sense reescriure la taula), i és la veritat: fins
avui totes les mesures del sistema eren de l'exterior perquè no n'hi havia cap altra.

Cap canvi de comportament: res llegeix aquesta columna encara (això és C2).
"""
from django.db import migrations, models

HELP = ("Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
        "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).")


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0052_measurementlayer'),
    ]

    operations = [
        migrations.AddField(
            model_name='garmentpommap',
            name='capa',
            field=models.CharField(db_index=True, default='exterior', help_text=HELP, max_length=20),
        ),
        migrations.AddField(
            model_name='itembasemeasurement',
            name='capa',
            field=models.CharField(db_index=True, default='exterior', help_text=HELP, max_length=20),
        ),
    ]
