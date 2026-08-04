"""C1/T2 — la columna `capa` a les taules de mesura de `models_app`.

Cinc taules: la mesura base (`BaseMeasurement`, la declaració canònica del camp), el seu
log (`MeasurementChangeLog`), l'override per talla (`ModelGradingOverride`), la línia de
size check (`SizeCheckLine`) i la col·locació de cota (`POMPlacement`).

⚠️ `ModelGradingRule` NO hi és, i no és un oblit: la regla de graduació es comparteix entre
capes («mateixos deltes») — decisió de domini, argumentada al seu docstring.

⚠️ `MeasurementChangeLog` és APPEND-ONLY i aquest `AddField` NO ho viola: és DDL, no DML.
Cap fila queda reescrita semànticament; el default no els atribueix res que no diguessin ja,
perquè el 100% de la història d'aquesta taula parla de l'única capa que el sistema sabia
mesurar. El guard d'app (`save()`/`delete()`) no es toca.

BACKFILL: cap. `default='exterior'` a nivell de columna cobreix totes les files existents
(fast-default de Postgres 11+, sense reescriure la taula).

Cap canvi de comportament: res llegeix aquesta columna encara (això és C2).
"""
from django.db import migrations, models

HELP = ("Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
        "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).")


class Migration(migrations.Migration):

    dependencies = [
        ('models_app', '0069_basemeasurement_nom_canonic_model_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='basemeasurement',
            name='capa',
            field=models.CharField(db_index=True, default='exterior', help_text=HELP, max_length=20),
        ),
        migrations.AddField(
            model_name='measurementchangelog',
            name='capa',
            field=models.CharField(db_index=True, default='exterior', help_text=HELP, max_length=20),
        ),
        migrations.AddField(
            model_name='modelgradingoverride',
            name='capa',
            field=models.CharField(db_index=True, default='exterior', help_text=HELP, max_length=20),
        ),
        migrations.AddField(
            model_name='pomplacement',
            name='capa',
            field=models.CharField(db_index=True, default='exterior', help_text=HELP, max_length=20),
        ),
        migrations.AddField(
            model_name='sizecheckline',
            name='capa',
            field=models.CharField(db_index=True, default='exterior', help_text=HELP, max_length=20),
        ),
    ]
