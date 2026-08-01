"""C1-ins — la INSTÀNCIA a `pom`: columna + clau + comporta, per a les dues taules.

`GarmentPOMMap` (què reclama la plantilla de l'item) i `ItemBaseMeasurement` (amb quin valor
típic). Aquí la instància diu QUANTES VEGADES la plantilla demana el mateix POM: una
americana demana la sisa dues vegades —dreta i esquerra— i són DUES pertinences, no una. És
l'origen de tot: el que aquesta taula declara és el que la sembra item→model copiarà.

⚠️ APP **SHARED + TENANT**: `pom` viu als tres schemas, i la migració emet el mateix SQL a
`public`, `fhort` i `los` — com a C1. `migrate_schemas` (MAI `--schema`) i auditoria SQL
contra `pg_constraint`/`information_schema` schema per schema després: django-tenants pot
donar un OK enganyós.

⚠️ `pom.GradingRule` NO hi és, com no hi era a la cadena de capa, i ara el seu `Meta` ho
declara amb acta: una regla és una llei d'increments, i la sisa dreta i l'esquerra gradúen
igual (decisió Montse).

L'ordre de les operacions és el que Django genera per a un camp que entra dins d'un
`unique_together` —retirar la clau vella → afegir la columna → posar la clau nova → tancar
la comporta—, tot dins d'una sola transacció.

`ADD COLUMN … DEFAULT '' NOT NULL` + `DROP DEFAULT`: el default queda al MODEL, no a
Postgres. Cal reiniciar el servei després de migrar.
"""
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0055_capa_comporta_c1'),
        ('tasks', '0043_timerentrada_last_heartbeat'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='garmentpommap',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='itembasemeasurement',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='garmentpommap',
            name='instancia',
            field=models.CharField(db_index=True, default='', help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). '' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).", max_length=60),
        ),
        migrations.AddField(
            model_name='itembasemeasurement',
            name='instancia',
            field=models.CharField(db_index=True, default='', help_text="Instància del POM dins la capa: slug compost canònic (p.ex. 'left-relaxed'). '' és la instància única. Fins a C4-ins només s'admet '' (comporta CHECK a BD).", max_length=60),
        ),
        migrations.AlterUniqueTogether(
            name='garmentpommap',
            unique_together={('garment_type_item', 'pom', 'capa', 'instancia')},
        ),
        migrations.AlterUniqueTogether(
            name='itembasemeasurement',
            unique_together={('base_set', 'pom', 'capa', 'instancia')},
        ),
        migrations.AddConstraint(
            model_name='garmentpommap',
            constraint=models.CheckConstraint(condition=models.Q(('instancia', '')), name='pom_garmentpommap_instancia_gate_cins'),
        ),
        migrations.AddConstraint(
            model_name='itembasemeasurement',
            constraint=models.CheckConstraint(condition=models.Q(('instancia', '')), name='pom_itembasemeasurement_instancia_gate_cins'),
        ),
    ]
