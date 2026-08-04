"""C1-ins — la columna `instancia` a les taules de mesura de `models_app`.

Germana exacta de `0070_capa_mesures`, i pel mateix camí: cinc taules —la mesura base
(`BaseMeasurement`, la declaració canònica del camp), el seu log (`MeasurementChangeLog`),
l'override per talla (`ModelGradingOverride`), la línia de size check (`SizeCheckLine`) i la
col·locació de cota (`POMPlacement`).

`instancia` és el SEGON EIX, ortogonal a `capa`: la capa diu de quina MATÈRIA parla la
mesura, la instància diu de QUINA DE LES REPETICIONS del mateix POM sobre la mateixa matèria
(la sisa dreta i l'esquerra, el pit RELAXED i l'EXTENDED). `''` és la instància única —el que
fins avui era «la mesura», sense qualificar—, mai NULL.

⚠️ `ModelGradingRule` NO hi és, i tampoc és un oblit: decisió Montse, «gradúen igual». La
regla no travessa CAP dels dos eixos. Argumentat al seu docstring.

⚠️ `MeasurementChangeLog` és APPEND-ONLY i aquest `AddField` NO ho viola: és DDL, no DML.
Cap fila queda reescrita semànticament, i el 100% de la història parla de la instància única.

⚠️ EL PARANY DEL DEFAULT (memòria `ftt-c1-capa-mesures-comporta`): Django emet
`ADD COLUMN … DEFAULT '' NOT NULL` seguit de `DROP DEFAULT` → **el default acaba vivint al
MODEL, no a Postgres**. Codi vell + esquema nou = `NotNullViolation`. Per això, després de
`migrate_schemas`, cal `systemctl restart ftt-staging.service` abans de servir res.

BACKFILL: cap. El `DEFAULT ''` del `ADD COLUMN` cobreix totes les files existents
(fast-default de Postgres 11+, sense reescriure la taula).

Cap canvi de comportament: res llegeix aquesta columna encara (això és FASE_2).
"""
from django.db import migrations, models

HELP = ("Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). "
        "'' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).")


class Migration(migrations.Migration):

    dependencies = [
        ('models_app', '0072_capa_comporta_c1'),
    ]

    operations = [
        migrations.AddField(
            model_name='basemeasurement',
            name='instancia',
            field=models.CharField(db_index=True, default='', help_text=HELP, max_length=60),
        ),
        migrations.AddField(
            model_name='measurementchangelog',
            name='instancia',
            field=models.CharField(db_index=True, default='', help_text=HELP, max_length=60),
        ),
        migrations.AddField(
            model_name='modelgradingoverride',
            name='instancia',
            field=models.CharField(db_index=True, default='', help_text=HELP, max_length=60),
        ),
        migrations.AddField(
            model_name='pomplacement',
            name='instancia',
            field=models.CharField(db_index=True, default='', help_text=HELP, max_length=60),
        ),
        migrations.AddField(
            model_name='sizecheckline',
            name='instancia',
            field=models.CharField(db_index=True, default='', help_text=HELP, max_length=60),
        ),
    ]
