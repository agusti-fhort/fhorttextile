"""C1/T2 — la columna `capa` a les taules de mesura de `fitting`.

`GradedSpec` (sortida del motor de grading, un valor per (versió, POM, talla)) i
`PieceFittingLine` (teòric vs real d'una prova). Tots dos són VALORS, i un valor és d'una
capa; la REGLA que els genera no en té (v. `models_app.ModelGradingRule`).

El motor (`generate_graded_specs`) NO es toca a C1: escriu el default de columna i prou.

BACKFILL: cap. `default='exterior'` cobreix totes les files existents (fast-default de
Postgres 11+, sense reescriure la taula).

Cap canvi de comportament: res llegeix aquesta columna encara (això és C2).
"""
from django.db import migrations, models

HELP = ("Capa de mesura: slug de pom.MeasurementLayer (per SLUG, mai per PK). "
        "Fins a C4 només s'admet 'exterior' (comporta CHECK a BD).")


class Migration(migrations.Migration):

    dependencies = [
        ('fitting', '0016_gradingversion_una_sola_activa'),
    ]

    operations = [
        migrations.AddField(
            model_name='gradedspec',
            name='capa',
            field=models.CharField(db_index=True, default='exterior', help_text=HELP, max_length=20),
        ),
        migrations.AddField(
            model_name='piecefittingline',
            name='capa',
            field=models.CharField(db_index=True, default='exterior', help_text=HELP, max_length=20),
        ),
    ]
