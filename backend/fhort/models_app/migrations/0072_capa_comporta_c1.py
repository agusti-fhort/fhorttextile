"""C1/T4 — LA COMPORTA a `models_app`: CHECK (capa = 'exterior').

El tancament de seguretat del pla de capes. C1 ensenya l'IDIOMA de la capa al sistema
(catàleg + columna + claus) però no el deixa parlar-lo: la cadena de consumidors
—serializers, motor de grading, UI, import, fitxa tècnica— continua assumint una mesura per
(model, POM) i no s'adapta fins a C2/C3. Entre C1 i C3 hi hauria, si no, una finestra en què
l'esquema ja admet una segona capa i el codi encara no la sap llegir: una fila 'folre'
escrita per accident no petaria enlloc, es fondria dins les llistes com si fos de l'exterior
i corrompria en silenci mesures que són el producte.

La BD és l'únic lloc on cap camí d'escriptura no ho pot esquivar: ni un `bulk_create`, ni un
`update()`, ni un loader de paquet, ni un `psql` a mà. Per això no hi ha cap guard
d'aplicació que l'acompanyi: no n'hi ha cap que ho iguali.

APLICACIÓ SEGURA: el 100% de les files existents tenen `capa='exterior'` (default de columna
de T2; auditat per SQL contra `pg_constraint`/`information_schema` a staging abans d'aplicar,
schema per schema), de manera que la validació que Postgres fa en crear el constraint no pot
fallar.

**C4 EL RETIRA PER MIGRACIÓ.** És bastida, no arquitectura.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('models_app', '0071_capa_unicitats'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='basemeasurement',
            constraint=models.CheckConstraint(
                condition=models.Q(capa='exterior'),
                name='models_app_basemeasurement_capa_gate_c1'),
        ),
        migrations.AddConstraint(
            model_name='measurementchangelog',
            constraint=models.CheckConstraint(
                condition=models.Q(capa='exterior'),
                name='models_app_measurementchangelog_capa_gate_c1'),
        ),
        migrations.AddConstraint(
            model_name='modelgradingoverride',
            constraint=models.CheckConstraint(
                condition=models.Q(capa='exterior'),
                name='models_app_modelgradingoverride_capa_gate_c1'),
        ),
        migrations.AddConstraint(
            model_name='pomplacement',
            constraint=models.CheckConstraint(
                condition=models.Q(capa='exterior'),
                name='models_app_pomplacement_capa_gate_c1'),
        ),
        migrations.AddConstraint(
            model_name='sizecheckline',
            constraint=models.CheckConstraint(
                condition=models.Q(capa='exterior'),
                name='models_app_sizecheckline_capa_gate_c1'),
        ),
    ]
