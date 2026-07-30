"""C1/T1 — CATÀLEG de capes de mesura (`MeasurementLayer`).

Només l'estructura. La sembra del contingut és la comanda `seed_measurement_layers`
(idempotent, `update_or_create` per slug, mai `delete`), com a `PatternPieceRole`: un
catàleg de sistema no neix d'una migració de dades que després ningú no pot tornar a
passar. Revertir aquesta migració esborra la taula, no el criteri.

Viu a `pom` perquè `fhort.pom` és l'única app que és a SHARED **i** a TENANT alhora: la
taula existirà a `public` i a cada tenant, que és el que demanen les vuit taules de mesura
que en referenciaran els slugs (escampades entre `models_app`, `fitting` i el propi `pom`).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0051_patternpiecerole'),
    ]

    operations = [
        migrations.CreateModel(
            name='MeasurementLayer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(max_length=20, unique=True)),
                ('nom_en', models.CharField(max_length=120)),
                ('nom_ca', models.CharField(max_length=120)),
                ('nom_es', models.CharField(max_length=120)),
                ('is_system', models.BooleanField(default=False)),
                ('pendent_revisio', models.BooleanField(default=False)),
                ('origen', models.CharField(choices=[('SEED', 'Sembra'), ('MANUAL', 'Manual'), ('IMPORT', 'Importació')], default='MANUAL', max_length=10)),
                ('display_order', models.PositiveSmallIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Capa de mesura',
                'verbose_name_plural': 'Capes de mesura',
                'ordering': ['display_order', 'slug'],
            },
        ),
    ]
