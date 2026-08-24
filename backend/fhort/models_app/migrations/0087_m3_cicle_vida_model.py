"""M3 · FASE 1 · FIT-9 — el cicle de vida del model: `nou` / `acabat` / `jubilat`.

REPROPÒSIT, no ampliació. El vocabulari vell (`Nou/EnCurs/EnRevisio/Tancat`) era **mort**: el
cens d'M3 (FASE 0a) hi va trobar dos escriptors, tots dos de CREACIÓ i tots dos amb el mateix
valor, i **cap lector que en preguntés el valor** — ni una branca al backend, ni una al front
(l'únic component que en pintava etiquetes, `EstatBadge.jsx`, no el munta ningú, i la columna
«Estat» de `/models` pinta un guió a posta). A PROD tot estava a `'Nou'`.

Per això el backfill pot ser el que és: **tot a `nou`**, sense mapa de conversió. No hi ha cap
lectura que pugui notar la diferència entre un model que ahir deia `EnCurs` i un que deia `Nou`,
perquè ningú no ho llegia; i inventar-ne un («EnCurs→nou, Tancat→acabat») hauria escrit
història: hauria declarat ACABATS uns quants models que ningú no ha tancat mai amb l'acte que
FIT-10 exigeix.
"""

import django.db.models.deletion
from django.db import migrations, models


def tot_a_nou(apps, schema_editor):
    """Tot l'existent → `nou`. Compta i ho diu: un backfill mut no es pot auditar."""
    Model = apps.get_model('models_app', 'Model')
    n = Model.objects.exclude(estat='nou').update(estat='nou')
    if n:
        print(f'  [M3 · FIT-9] estat → \'nou\': {n} model(s) a l\'esquema '
              f'"{schema_editor.connection.schema_name}"')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_tenantconfig_legal_footer'),
        ('models_app', '0086_tram_f_breaks_intervals'),
    ]

    operations = [
        # L'ordre importa per a la LECTURA, no per a Postgres: primer es normalitza el que hi ha
        # i després es declara el vocabulari nou. `choices` no és una constraint de BD, o sigui
        # que l'`AlterField` no valida res: qui deixa la taula coherent és el `RunPython`.
        migrations.RunPython(tot_a_nou, migrations.RunPython.noop),
        migrations.AddField(
            model_name='model',
            name='motiu_tancament',
            field=models.CharField(blank=True, choices=[('acabat', 'Acabat'), ('tret_de_cataleg', 'Tret de catàleg')], max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='model',
            name='estat',
            field=models.CharField(choices=[('nou', 'Nou'), ('acabat', 'Acabat'), ('jubilat', 'Jubilat')], default='nou', max_length=20),
        ),
        # ⚠️ El REVERS és un no-op a posta: els valors vells s'han sobreescrit i no es poden
        # reconstruir. Desfer la migració torna les choices velles, no les dades.
        migrations.CreateModel(
            name='ModelEstatEsdeveniment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('de_estat', models.CharField(choices=[('nou', 'Nou'), ('acabat', 'Acabat'), ('jubilat', 'Jubilat')], max_length=20)),
                ('a_estat', models.CharField(choices=[('nou', 'Nou'), ('acabat', 'Acabat'), ('jubilat', 'Jubilat')], max_length=20)),
                ('motiu', models.CharField(blank=True, default='', help_text='Vocabulari de tancament cap a `acabat`; text lliure a la reobertura.', max_length=200)),
                ('quan', models.DateTimeField(auto_now_add=True)),
                ('model', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='esdeveniments_estat', to='models_app.model')),
                ('per', models.ForeignKey(blank=True, help_text='Qui ho ha decidit. SET_NULL: esborrar un usuari no esborra la història.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='esdeveniments_estat_model', to='accounts.userprofile')),
            ],
            options={
                'verbose_name': "Esdeveniment d'estat de model",
                'verbose_name_plural': "Esdeveniments d'estat de model",
                'ordering': ['-quan', '-id'],
                'indexes': [models.Index(fields=['model', '-quan'], name='models_app__model_i_46ae90_idx')],
            },
        ),
    ]
