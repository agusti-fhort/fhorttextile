"""P1 diccionari del client — descripcions bilingües + origen DICCIONARI a CustomerPOMAlias.

Afegeix description_en (canònica internacional), description_local (idioma de l'empresa) i
language (ISO 639-1 del camp local). Amplia origen amb el choice 'DICCIONARI'.

Backfill (idempotent, per-tenant; res al schema public): el camp heretat client_description,
quan té valor PROPI (no duplica client_code), es bolca a description_en si aquest és buit.
client_description NO s'esborra (columna obsoleta amb TODO al model); no es re-escriu.
"""
from django.db import migrations, models


def backfill_desc(apps, schema_editor):
    if schema_editor.connection.schema_name == 'public':
        return
    CustomerPOMAlias = apps.get_model('pom', 'CustomerPOMAlias')
    n = 0
    for a in CustomerPOMAlias.objects.all():
        cd = (a.client_description or '').strip()
        if not cd:
            continue
        if cd.lower() == (a.client_code or '').strip().lower():
            continue  # duplicava el codi → no és descripció pròpia
        if (a.description_en or '').strip():
            continue  # ja té descripció canònica
        a.description_en = cd
        a.save(update_fields=['description_en'])
        n += 1
    print(f"[dict-fields @ {schema_editor.connection.schema_name}] description_en backfill: {n}")


def reverse_noop(apps, schema_editor):
    # NO-OP: no desfem el backfill (client_description es conserva intacte com a origen).
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('pom', '0034_fix_a1_remove_a2_customerpomalias'),
    ]

    operations = [
        migrations.AddField(
            model_name='customerpomalias',
            name='description_en',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='customerpomalias',
            name='description_local',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='customerpomalias',
            name='language',
            field=models.CharField(blank=True, default='', max_length=2),
        ),
        migrations.AlterField(
            model_name='customerpomalias',
            name='origen',
            field=models.CharField(
                choices=[('IMPORT', 'Import'), ('MANUAL', 'Manual'),
                         ('MIGRACIO', 'Migració'), ('DICCIONARI', 'Diccionari')],
                default='MANUAL', max_length=10),
        ),
        migrations.RunPython(backfill_desc, reverse_noop),
    ]
