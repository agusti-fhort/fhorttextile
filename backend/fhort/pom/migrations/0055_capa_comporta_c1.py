"""C1/T4 — LA COMPORTA a `pom`: CHECK (capa = 'exterior').

Argument sencer a `models_app/0072_capa_comporta_c1`. En resum: C1 ensenya l'idioma de la
capa però no el deixa parlar; fins que C2/C3 no adapten la cadena de consumidors, una
segona capa escrita per accident es fondria en silenci dins les llistes de l'exterior. La BD
és l'únic lloc on cap camí d'escriptura no ho pot esquivar.

APLICACIÓ SEGURA: totes les files existents tenen `capa='exterior'` (default de columna de
T2), o sigui que la validació de Postgres en crear el constraint no pot fallar.

⚠️ El catàleg `MeasurementLayer` (T1) NO porta comporta i se sembra sencer, amb les sis
capes: el vocabulari pot existir abans que el permís d'usar-lo. És justament la separació
que fa que C4 sigui una sola migració i no una sembra nova.

**C4 EL RETIRA PER MIGRACIÓ.** És bastida, no arquitectura.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0054_capa_unicitats'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='garmentpommap',
            constraint=models.CheckConstraint(
                condition=models.Q(capa='exterior'),
                name='pom_garmentpommap_capa_gate_c1'),
        ),
        migrations.AddConstraint(
            model_name='itembasemeasurement',
            constraint=models.CheckConstraint(
                condition=models.Q(capa='exterior'),
                name='pom_itembasemeasurement_capa_gate_c1'),
        ),
    ]
