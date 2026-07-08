from django.db import migrations

# Unitat 'minute' — necessària per als serveis TIME_BASED (preu per minut, Product.sale_rate).
# Idempotent: get_or_create per code (mateix patró que 0002_seed_units).


def seed_minute(apps, schema_editor):
    Unit = apps.get_model('commerce', 'Unit')
    Unit.objects.get_or_create(code='minute', defaults={'name': 'Minute'})


def unseed_minute(apps, schema_editor):
    Unit = apps.get_model('commerce', 'Unit')
    Unit.objects.filter(code='minute').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('commerce', '0004_quote_quoteline'),
    ]

    operations = [
        migrations.RunPython(seed_minute, unseed_minute),
    ]
