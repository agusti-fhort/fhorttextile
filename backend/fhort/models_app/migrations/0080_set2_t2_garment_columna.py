"""SET-2/T2 — la columna `garment` a les taules de mesura de `models_app`.

Germana exacta de `0070_capa_mesures` i `0073_instancia_mesures`, i pel mateix camí:
la mesura base (`BaseMeasurement`, la declaració canònica del camp), el seu log
(`MeasurementChangeLog`), l'override per talla (`ModelGradingOverride`) i la línia de
size check (`SizeCheckLine`). Les dues germanes de `fitting` (`GradedSpec` i
`PieceFittingLine`) van a `fitting/0025`, la seva parella d'aquesta mateixa onada.

`garment` és el TERCER EIX, ortogonal als dos anteriors: la capa diu de quina MATÈRIA
parla la mesura, la instància de quina de les REPETICIONS del mateix POM, i el garment
de quina PRENDA del model — el top i la calceta d'un bikini. `''` és la PEÇA MARE (el
que fins avui era «el model», sense qualificar), mai NULL.

⚠️ `ModelGradingRule` NO hi és EN AQUESTA MIGRACIÓ, i el motiu ha canviat respecte de
capa i instància: la clau SÍ que hi creixerà (D4, reobertura conscient de l'acta —una
peça pot tenir el seu propi `grading_rule_set`, o sigui que la llei d'increments pot
divergir entre peces). Però és una decisió pròpia i va al seu tram (T3), no aquí.
L'acta segueix sent certa dins d'una peça: la sisa dreta i l'esquerra gradúen igual.

⚠️ `POMPlacement` NO hi és, i aquest sí que és per CATEGORIA: `garment` és un eix DE
MODEL, i `POMPlacement` ancora a `ItemFitxer`, que penja de `GarmentTypeItem` — o sigui
CATÀLEG (`models.py:505`, `:517`). Posar-hi un eix de model seria error de categoria.
🚩 Conseqüència que queda OBERTA i no es toca aquí: amb un sol `garment_type_item` per
Model (decisió d'Agus, 2026-08-10: el GTI NO baixa a la peça en aquesta v1), dues peces
comparteixen el mateix `ItemFitxer` i la col·lisió de `view_slot` de F11 segueix viva,
tal com el propi codi ja la declara oberta a `models.py:1509-1512`.

⚠️ `MeasurementChangeLog` és APPEND-ONLY i aquest `AddField` NO ho viola: és DDL, no
DML. Cap fila queda reescrita semànticament, i el 100% de la història parla de la peça
mare. Hi entra en aquesta onada —i no en una de posterior— precisament perquè no té cap
unicitat: si l'eix no neix aquí, el lector no podrà dir mai de quina peça parlava un
canvi ja registrat, i aquesta pèrdua és IRREVERSIBLE.

⚠️ EL PARANY DEL DEFAULT (memòria `ftt-c1-capa-mesures-comporta`): Django emet
`ADD COLUMN … DEFAULT '' NOT NULL` seguit de `DROP DEFAULT` → **el default acaba vivint
al MODEL, no a Postgres**. Codi vell + esquema nou = `NotNullViolation`. Per això,
després de `migrate_schemas`, cal `systemctl restart ftt-staging.service`.

BACKFILL: cap. El `DEFAULT ''` del `ADD COLUMN` cobreix totes les files existents
(fast-default de Postgres 11+, sense reescriure la taula).

Cap canvi de comportament: **res llegeix aquesta columna encara.** Les claus l'ampliaran
i les comportes la congelaran a la migració següent d'aquesta onada.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('models_app', '0079_m3_derivat_de_rule_set'),
    ]

    operations = [
        migrations.AddField(
            model_name='basemeasurement',
            name='garment',
            field=models.CharField(db_index=True, default='', help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). '' és la peça mare, que és el Model mateix. Fins a la retirada de la comporta només s'admet '' (comporta CHECK a BD).", max_length=20),
        ),
        migrations.AddField(
            model_name='measurementchangelog',
            name='garment',
            field=models.CharField(db_index=True, default='', help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). '' és la peça mare, que és el Model mateix. Fins a la retirada de la comporta només s'admet '' (comporta CHECK a BD).", max_length=20),
        ),
        migrations.AddField(
            model_name='modelgradingoverride',
            name='garment',
            field=models.CharField(db_index=True, default='', help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). '' és la peça mare, que és el Model mateix. Fins a la retirada de la comporta només s'admet '' (comporta CHECK a BD).", max_length=20),
        ),
        migrations.AddField(
            model_name='sizecheckline',
            name='garment',
            field=models.CharField(db_index=True, default='', help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). '' és la peça mare, que és el Model mateix. Fins a la retirada de la comporta només s'admet '' (comporta CHECK a BD).", max_length=20),
        ),
    ]
