from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fitting', '0006_gradedspec_generated_from_version'),
    ]

    operations = [
        migrations.DeleteModel(name='FitCommentFitxer'),
        migrations.DeleteModel(name='FitComment'),
        migrations.DeleteModel(name='FittingLine'),
        migrations.DeleteModel(name='Fitting'),
        migrations.DeleteModel(name='GradedSpecLine'),
        migrations.DeleteModel(name='SessioFitting'),
    ]
