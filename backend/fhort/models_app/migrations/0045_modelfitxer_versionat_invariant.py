from django.db import migrations, models


def backfill_is_current_and_normalize_versio(apps, schema_editor):
    """Backfill de la invariant de cadena i normalització de `versio` a numèric.

    - is_current = True si el registre NO és apuntat per cap altre via versio_anterior
      (és cap de cadena); False si ha estat superat per una versió posterior.
    - versio: passa de string ("002"/"2") a string numèric net abans del canvi de tipus
      a PositiveIntegerField (la conversió de columna a integer la fa l'AlterField següent).
    """
    ModelFitxer = apps.get_model('models_app', 'ModelFitxer')

    superseded_ids = set(
        ModelFitxer.objects
        .exclude(versio_anterior__isnull=True)
        .values_list('versio_anterior_id', flat=True)
    )

    for obj in ModelFitxer.objects.all():
        try:
            num = int(str(obj.versio).strip())
        except (TypeError, ValueError):
            num = 1
        if num < 1:
            num = 1
        obj.versio = str(num)
        obj.is_current = obj.id not in superseded_ids
        obj.save(update_fields=['versio', 'is_current'])


def noop_reverse(apps, schema_editor):
    # Camps additius; el rollback de l'esquema el gestionen les operacions inverses.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('models_app', '0044_watchpoint_dades'),
    ]

    operations = [
        migrations.AddField(
            model_name='modelfitxer',
            name='is_current',
            field=models.BooleanField(default=True, db_index=True),
        ),
        migrations.AddField(
            model_name='modelfitxer',
            name='checksum',
            field=models.CharField(blank=True, default='', max_length=64),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='modelfitxer',
            name='mimetype',
            field=models.CharField(blank=True, default='', max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='modelfitxer',
            name='origen',
            field=models.CharField(
                choices=[
                    ('upload', 'Pujada manual'),
                    ('ia_escalat', "IA d'escalat"),
                    ('ia_marcada', 'IA de marcada'),
                    ('ia_ocr', 'IA OCR'),
                ],
                default='upload',
                max_length=20,
            ),
        ),
        migrations.RunPython(
            backfill_is_current_and_normalize_versio,
            noop_reverse,
        ),
        migrations.AlterField(
            model_name='modelfitxer',
            name='versio',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
