"""C1-ins — la INSTÀNCIA a `fitting`: columna + clau + comporta, per a les dues taules.

`GradedSpec` (el resultat d'aplicar la regla a un valor base) i `PieceFittingLine` (la xifra
que la modista pren sobre la peça real). Si la fitxa demana la sisa dreta i l'esquerra, allà
hi ha d'haver dues línies i dos specs — la regla, en canvi, segueix sent una de sola
(decisió Montse, «gradúen igual»: `pom.GradingRule` no rep la columna).

L'ORDRE DE LES OPERACIONS és el que Django genera per a un camp que entra dins d'un
`unique_together`, i és el correcte: retirar la clau vella → afegir la columna → posar la
clau nova → tancar la comporta. Tot dins d'una sola transacció: la finestra sense unicitat
no existeix per a cap altra sessió.

`ADD COLUMN … DEFAULT '' NOT NULL` + `DROP DEFAULT` → **el default queda al MODEL, no a
Postgres**. Codi vell + esquema nou = `NotNullViolation`: cal reiniciar el servei després
de `migrate_schemas` (la lliçó de C1).

Cap backfill: el default de columna cobreix les files existents (fast-default de PG 11+).
Cap canvi de comportament: res llegeix la columna encara (això és FASE_2).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitting', '0019_capa_comporta_c1'),
        ('pom', '0055_capa_comporta_c1'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='gradedspec',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='piecefittingline',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='gradedspec',
            name='instancia',
            field=models.CharField(db_index=True, default='', help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). '' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).", max_length=60),
        ),
        migrations.AddField(
            model_name='piecefittingline',
            name='instancia',
            field=models.CharField(db_index=True, default='', help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). '' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).", max_length=60),
        ),
        migrations.AlterUniqueTogether(
            name='gradedspec',
            unique_together={('grading_version', 'pom', 'size_label', 'capa', 'instancia')},
        ),
        migrations.AlterUniqueTogether(
            name='piecefittingline',
            unique_together={('piece_fitting', 'pom', 'size_label', 'capa', 'instancia')},
        ),
        migrations.AddConstraint(
            model_name='gradedspec',
            constraint=models.CheckConstraint(condition=models.Q(('instancia', '')), name='fitting_gradedspec_instancia_gate_cins'),
        ),
        migrations.AddConstraint(
            model_name='piecefittingline',
            constraint=models.CheckConstraint(condition=models.Q(('instancia', '')), name='fitting_piecefittingline_instancia_gate_cins'),
        ),
    ]
