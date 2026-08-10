"""SET-2/T2 — la columna `garment` a les dues taules de mesura de `fitting`.

Parella de `models_app/0080_set2_t2_garment_columna` dins de la mateixa onada, i pel
mateix camí que van fer `fitting/0018` (capa) i les seves germanes d'instància:
la sortida del motor (`GradedSpec`) i la línia de fitting (`PieceFittingLine`).
La declaració canònica del camp viu a `models_app.BaseMeasurement.garment`.

⚠️ LA VERSIÓ NO GUANYA CAP EIX, i és decisió de domini (D6, Agus 2026-08-10): «el
fitting afecta a totes les peces; quan el tècnic mesura, mesura el model sencer». Per
tant `SizeFitting`, `GradingVersion`, `FittingSession` i `SizeCheck` es queden ancorats
al MODEL i **no entren en aquesta onada**. Una sola `GradingVersion` conté els
`GradedSpec` de TOTES les peces del model, i el segell és del model per decisió.
Conseqüència que això SOSTÉ i que cal no desfer: quan es mou la base d'una peça, la
versió segellada queda estala **de debò** —perquè conté els specs d'aquella peça—, o
sigui que l'avís d'estalitud és CORRECTE i no contaminació entre peces.
Si una sessió futura proposa pujar l'eix a la versió, és contradicció de paradigma.

⚠️ EL PARANY DEL DEFAULT: v. la nota sencera a `models_app/0080`. Cal
`systemctl restart ftt-staging.service` després de `migrate_schemas`.

BACKFILL: cap (fast-default de Postgres 11+).
Cap canvi de comportament: res llegeix aquesta columna encara.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitting', '0024_d3121_decisio_piecefittingline'),
    ]

    operations = [
        migrations.AddField(
            model_name='gradedspec',
            name='garment',
            field=models.CharField(db_index=True, default='', help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). '' és la peça mare, que és el Model mateix. Fins a la retirada de la comporta només s'admet '' (comporta CHECK a BD).", max_length=20),
        ),
        migrations.AddField(
            model_name='piecefittingline',
            name='garment',
            field=models.CharField(db_index=True, default='', help_text="Peça (garment) dins del model: codi de ModelGarment ('02', '03'…). '' és la peça mare, que és el Model mateix. Fins a la retirada de la comporta només s'admet '' (comporta CHECK a BD).", max_length=20),
        ),
    ]
