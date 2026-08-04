"""C4 · G2 — LA PRESA. La línia de size-check.

Grup 2 de 4. 28 comportes → 20.

Les dues taules d'aquest grup són on es MESURA de veritat: la línia de size-check i la línia
de fitting. Van juntes perquè són la mateixa cosa vista des de dues portes —una presa amb el
seu veredicte de tolerància— i perquè totes dues es SEMBREN des d'una font que ja parla els
dos eixos: `_materialize_lines` des de `BaseMeasurement`
(`models_app/services_size_check.py:64`) i el sembrat de peça des de `GradedSpec`
(`fitting/services.py:339`).

PER QUÈ ARA I NO DESPRÉS. Amb G1 retirat, ROSALIA (model 188 de staging) ja té germanes
vives, i el sembrat les respecta: crea una línia per mesura amb els seus eixos. Amb aquestes
comportes encara dretes, obrir un Size Check en aquell model NO donava una pantalla buida
sinó un `IntegrityError`:

    new row for relation "models_app_sizecheckline" violates check constraint
    "models_app_sizecheckline_instancia_gate_cins"
    DETAIL: Failing row contains (…, 284, 25, null, exterior, right)

Verificat dins d'una transacció revertida abans de tocar res. El fitting hauria fet igual per
`piecefittingline`. Retirar G1 sense G2 deixa el sistema en un estat en què el gest següent
peta, i per això aquests dos grups es toquen seguits.

⚠️ LES DUES INVARIANTS NO ES TOQUEN (v. la migració de G1).

⚠️ PARANY DEL ROLLBACK: `ADD COLUMN … DEFAULT … NOT NULL` + `DROP DEFAULT` → el default viu al
MODEL de Django, no a Postgres. Rollback del codi sense rollback de l'esquema =
`NotNullViolation` a tota escriptura. O es desfan les dues coses o cap.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('models_app', '0076_c4_g1_retira_comportes'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='sizecheckline',
            name='models_app_sizecheckline_capa_gate_c1',
        ),
        migrations.RemoveConstraint(
            model_name='sizecheckline',
            name='models_app_sizecheckline_instancia_gate_cins',
        ),
    ]
