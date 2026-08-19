# C4 (2026-08-07) — `SizeDefinition.ordre` únic per run (deute §7.4.4).
#
# Depèn de C1 i C2 a posta i no per ordre alfabètic: fins que aquelles dues no han corregut,
# `fhort` tenia 6 parells d'`ordre` duplicats (5 a BABY_MONTHS, 1 a TODDLER_EU) i aquesta
# constraint hauria petat la migració. Comprovat després d'aplicar-les: 0 duplicats als tres
# schemes. Un run desordenat és un grading incorrecte — el motor compta per POSICIÓ.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0066_c3_depuracio_runs_autoritzada'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='sizedefinition',
            unique_together={('size_system', 'etiqueta'), ('size_system', 'ordre')},
        ),
    ]
