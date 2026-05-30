# Sprint 5B.5 — Retire the legacy fitting wizard (SFFitting/SFFittingLinia).
# Replaced by FittingSession / PieceFitting / PieceFittingLine (fitting 0008).
# 0 rows in production → direct DeleteModel, child (FK→SFFitting) first.
# (Lesson 5A: keep ONLY DeleteModel ops; the autodetector's RemoveField/
#  AlterUniqueTogether prelude was removed by hand.)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fitting', '0009_gradingversion_aprovada_per_and_more'),
    ]

    operations = [
        migrations.DeleteModel(
            name='SFFittingLinia',
        ),
        migrations.DeleteModel(
            name='SFFitting',
        ),
    ]
