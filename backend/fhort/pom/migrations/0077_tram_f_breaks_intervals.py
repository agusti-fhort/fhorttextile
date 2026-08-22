"""TRAM F · MULTI-BREAK PER INTERVALS — el camp, i NOMÉS el camp (2026-08-21).

ADDITIVA I BUIDA. Afegeix `GradingRule.breaks` (JSON, NULL) i no toca ni una fila: **cap
backfill**. Les 433 regles LINEAR actives d'staging (i les ~1.850 de PROD) segueixen dient la
seva llei amb el parell `(talla_break_label, increment_break)`, i el motor les llegeix com
l'interval `[talla_break_label .. última talla del sistema]` — equivalència provada cel·la a
cel·la sobre el banc 1383 (105/105) ABANS de tocar el motor.

🚨 L'OFF-BY-ONE QUE AQUESTA MIGRACIÓ NO FA, I ÉS A POSTA. L'ordre del sprint deia que en migrar
un break a interval calia desplaçar l'etiqueta una posició («la vella marca l'última talla del
delta petit»). Això és cert de la convenció de DOCUMENT i FALS de la BD: la BD ja desa la
convenció de MOTOR. Aplicar-hi el desplaçament la desplaçaria una segona vegada i mouria **33
cel·les de 105** al mateix banc (contra-experiment a `docs/ordres/equiv_intervals_1383.py`).
Com que aquí no es migra res, el parany queda tancat per construcció.

`pom` és app SHARED: aquesta migració corre a `public` I a cada tenant.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0076_translationcache'),
    ]

    operations = [
        migrations.AddField(
            model_name='gradingrule',
            name='breaks',
            field=models.JSONField(blank=True, null=True),
        ),
    ]
