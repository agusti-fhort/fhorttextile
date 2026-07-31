"""C1/T4 — LA COMPORTA a `fitting`: CHECK (capa = 'exterior').

Argument sencer a `models_app/0072_capa_comporta_c1`. En resum: C1 ensenya l'idioma de la
capa però no el deixa parlar; fins que C2/C3 no adapten la cadena de consumidors, una
segona capa escrita per accident es fondria en silenci dins les llistes de l'exterior. La BD
és l'únic lloc on cap camí d'escriptura no ho pot esquivar — i el motor de grading, que
escriu `GradedSpec` a milers, és exactament el camí que més hi hauria de perdre.

APLICACIÓ SEGURA: totes les files existents tenen `capa='exterior'` (default de columna de
T2), o sigui que la validació de Postgres en crear el constraint no pot fallar.

**C4 EL RETIRA PER MIGRACIÓ.** És bastida, no arquitectura.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitting', '0018_capa_unicitats'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='gradedspec',
            constraint=models.CheckConstraint(
                condition=models.Q(capa='exterior'),
                name='fitting_gradedspec_capa_gate_c1'),
        ),
        migrations.AddConstraint(
            model_name='piecefittingline',
            constraint=models.CheckConstraint(
                condition=models.Q(capa='exterior'),
                name='fitting_piecefittingline_capa_gate_c1'),
        ),
    ]
