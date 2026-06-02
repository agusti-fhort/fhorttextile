"""Pas 5B-fix — migració de dades: la fase 'Fit' s'elimina de FASE_CHOICES.
Qualsevol Model.fase_actual='Fit' o FittingSession.fase='Fit' → 'Proto' (defensiva)."""
from django.db import migrations


def fit_to_proto(apps, schema_editor):
    Model = apps.get_model('models_app', 'Model')
    Model.objects.filter(fase_actual='Fit').update(fase_actual='Proto')
    try:
        FittingSession = apps.get_model('fitting', 'FittingSession')
        FittingSession.objects.filter(fase='Fit').update(fase='Proto')
    except LookupError:
        pass  # fitting no instal·lat en aquest schema


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('models_app', '0026_alter_model_fase_actual'),
        ('fitting', '0012_alter_fittingsession_fase'),
    ]
    operations = [migrations.RunPython(fit_to_proto, noop)]
