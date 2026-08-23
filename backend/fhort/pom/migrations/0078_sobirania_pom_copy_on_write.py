"""SOBIRANIA DEL POM — el tenant pot fer seu un POM del catàleg global (22/08).

ADDITIVA I REVERSIBLE. Onze columnes noves a `pom_pommaster`, totes amb default buit:
cap fila canvia de valor, cap lector canvia de resposta fins que algú les ompli, i
`POMGlobal` **no es toca** (és de la casa global i el comparteixen tots els tenants).

  · `separat_de_global` + `separat_at` — LA MARCA DE SOBIRANIA. Un POM nascut al tenant i un
    POM separat del global tenen tots dos `pom_global IS NULL`: sense marca són
    indistingibles, i els importadors —que resolen per `pom_global.codi`— tornarien a
    enganxar el global i desfarien en silenci la reparació feta a PROD.

  · les nou del «com es mesura» (`unitat`, `start_point`, `end_point`, `reference_point`,
    `scope`, `orientation`, `state`, `line`, `body_section`) — fins avui NOMÉS vivien a
    `POMGlobal`, i per això «complementar la informació d'un POM propi» era impossible: la
    pantalla del catàleg les pintava com a «no lligat» i no hi havia on escriure-les.

`pom` és SHARED i TENANT alhora (`settings.py:55,68`): `migrate_schemas` (MAI `--schema`)
la posa a `public` i a cada tenant.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0077_tram_f_breaks_intervals'),
    ]

    operations = [
        migrations.AddField(
            model_name='pommaster',
            name='body_section',
            field=models.CharField(blank=True, choices=[('FRONT', 'Front'), ('BACK', 'Back'), ('SIDE', 'Side'), ('SLEEVE', 'Sleeve'), ('BOTH', 'Both'), ('HEAD', 'Head')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='pommaster',
            name='end_point',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='pommaster',
            name='line',
            field=models.CharField(blank=True, choices=[('STRAIGHT', 'Straight'), ('CURVED', 'Curved'), ('ALONG CURVE', 'Along curve'), ('ANGLED', 'Angled')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='pommaster',
            name='orientation',
            field=models.CharField(blank=True, choices=[('HORIZONTAL', 'Horizontal'), ('VERTICAL', 'Vertical'), ('CIRCUMFERENCE', 'Circumference'), ('CURVED', 'Curved'), ('DIAGONAL', 'Diagonal')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='pommaster',
            name='reference_point',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='pommaster',
            name='scope',
            field=models.CharField(blank=True, choices=[('HALF', 'Half'), ('FULL', 'Full'), ('CALCULATED', 'Calculated')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='pommaster',
            name='separat_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Data de separació'),
        ),
        migrations.AddField(
            model_name='pommaster',
            name='separat_de_global',
            field=models.CharField(blank=True, default='', help_text='Codi del POMGlobal del qual aquest POM es va separar (buit = mai lligat). Marca de SOBIRANIA: els importadors no hi poden tornar a enganxar el global.', max_length=80, verbose_name='Separat del global'),
        ),
        migrations.AddField(
            model_name='pommaster',
            name='start_point',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='pommaster',
            name='state',
            field=models.CharField(blank=True, choices=[('FLAT', 'Flat'), ('RELAXED', 'Relaxed'), ('STRETCHED', 'Stretched'), ('ON_BODY', 'On body')], default='', max_length=20),
        ),
        migrations.AddField(
            model_name='pommaster',
            name='unitat',
            field=models.CharField(blank=True, choices=[('cm', 'cm'), ('inch', 'inch')], default='', help_text="Buit = la del global si n'hi ha, cm si no.", max_length=4),
        ),
    ]
