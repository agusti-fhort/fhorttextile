"""C4 · G1 — LA RETIRADA DE LA PRIMERA BASTIDA. Els specs que en deriven.

Les comportes de C1/C1-ins eren un dic explícit i temporal: l'esquema ja sabia dir «folre» i
«sisa esquerra», i la cadena de lectors i escriptors encara no. Els seus propis comentaris ho
deien —«C4 EL RETIRA PER MIGRACIÓ. És bastida, no arquitectura»— i això n'és el compliment.

GRUP 1 DE 4, i el grup és per SIGNAL, no per FK. `basemeasurement` i `measurementchangelog`
van juntes perquè el signal F1 escriu al log dins de la MATEIXA transacció que l'alta de la
mesura: separar-les deixaria una germana escrivint un apunt que la comporta del log
rebutjaria. I `fitting_gradedspec` hi va perquè escriure una base encadena cap al motor
(`generate_graded_specs`) dins de la mateixa crida — mesurat al commit `959147a5`, on
`escalat/ajustar-talla` va petar amb `CheckViolation` amb la mesura oberta i el spec tancat.

⚠️ LES DUES INVARIANTS NO ES TOQUEN. `models_app_basemeasurement_instancia_exigeix_nom` (una
per schema) NO és una comporta: és llei de domini —una instància sense nom de fitxa és
il·legal— i ha de SOBREVIURE C4. El recompte que corre pel projecte, «42», les hi compta a
dins; les comportes de debò són 40.

⚠️ PARANY DEL ROLLBACK. Les migracions de C1 van fer `ADD COLUMN … DEFAULT … NOT NULL` seguit
de `DROP DEFAULT`: el default de `capa`/`instancia` viu al MODEL de Django, no a Postgres.
Fer rollback del CODI sense fer rollback de l'ESQUEMA deixa tota escriptura amb
`NotNullViolation`. Si cal desfer això, es desfan les dues coses o cap.

EL QUE HABILITA: a partir d'aquí, dues germanes poden EXISTIR de veritat a la BD.

EL QUE HO SOSTÉ, i és el que s'ha de mirar si un dia això peta:
  · `test_c4_germanes_a_les_superficies` — les 10 superfícies de lectura, cap saltat
  · `test_c4_escriptura_germanes` — els sis escriptors i les dues podes
  · auditoria d'orfes: 0/0 a les 20 combinacions de taula × schema
  · golden `4e34859c3ed574a9a5779354ee9883c3`, byte-idèntic al T0 del 03/08
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fitting', '0021_pomalert_capa_pomalert_instancia'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='gradedspec',
            name='fitting_gradedspec_capa_gate_c1',
        ),
        migrations.RemoveConstraint(
            model_name='gradedspec',
            name='fitting_gradedspec_instancia_gate_cins',
        ),
    ]
