"""C4 · G4 — EL CATÀLEG, I ÉS L'ÚLTIM A POSTA. 12 comportes → 0.

Grup 4 de 4. Amb aquesta migració les 40 comportes de C1/C1-ins han caigut totes.

`GarmentPOMMap` i `ItemBaseMeasurement` són la PLANTILLA: el que hi ha declarat aquí es
propaga a tots els models que en neixin (C-31.h, la sembra item→model). Per això van
l'últim i no el primer, tot i ser les taules més senzilles. Obrir el catàleg abans que les
superfícies del model sapiguessin llegir germanes hauria ESCAMPAT el problema a cada model
nou en comptes de contenir-lo; obrir-lo ara vol dir que una germana declarada al catàleg
arriba a un sistema que la sap llegir, escriure, graduar, mesurar i podar.

Són també les úniques d'aquest tram que viuen a `public` a més dels tenants: el catàleg és
compartit, i per això aquest grup en retira 12 (2 taules × 2 eixos × 3 schemas) i no 8.

⚠️ LES DUES INVARIANTS SOBREVIUEN, i ara són l'únic que queda:
`models_app_basemeasurement_instancia_exigeix_nom`, una per schema de tenant. No és bastida:
és la llei que fa que dues germanes siguin distingibles per a un humà. El recompte «42» que
corria pel projecte les hi comptava a dins; les comportes eren 40 i han caigut les 40.

⚠️ Parany del rollback: `ADD COLUMN … DEFAULT … NOT NULL` + `DROP DEFAULT` → el default viu
al MODEL de Django, no a Postgres. Rollback del codi sense rollback de l'esquema =
`NotNullViolation` a tota escriptura. O es desfan les dues coses o cap.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0056_instancia_cins'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='garmentpommap',
            name='pom_garmentpommap_capa_gate_c1',
        ),
        migrations.RemoveConstraint(
            model_name='garmentpommap',
            name='pom_garmentpommap_instancia_gate_cins',
        ),
        migrations.RemoveConstraint(
            model_name='itembasemeasurement',
            name='pom_itembasemeasurement_capa_gate_c1',
        ),
        migrations.RemoveConstraint(
            model_name='itembasemeasurement',
            name='pom_itembasemeasurement_instancia_gate_cins',
        ),
    ]
