from django.db import migrations

# Unitats de venda/mesura comercial per defecte (nom canònic EN; display i18n a la UI).
# Idempotent: get_or_create per code. El tenant en pot afegir/desactivar més.
DEFAULT_UNITS = [
    ('piece', 'Piece'),
    ('hour', 'Hour'),
    ('shipment', 'Shipment'),
    ('set', 'Set'),
    ('meter', 'Meter'),
    ('kg', 'Kilogram'),
]


def seed_units(apps, schema_editor):
    Unit = apps.get_model('commerce', 'Unit')
    for code, name in DEFAULT_UNITS:
        Unit.objects.get_or_create(code=code, defaults={'name': name})


def unseed_units(apps, schema_editor):
    Unit = apps.get_model('commerce', 'Unit')
    Unit.objects.filter(code__in=[c for c, _ in DEFAULT_UNITS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('commerce', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_units, unseed_units),
    ]
