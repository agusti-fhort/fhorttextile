# N1 (2026-08-06 nit) — classificació idempotent dels runs existents.
#
# Dues passades, totes dues NOMÉS-OMPLE: no toquen cap fila que ja porti valor, i per tant
# es poden tornar a córrer sense conseqüències. Cap esborrat, cap camp existent sobreescrit
# (`base_unit` i `customer_codi` es queden exactament com estan, encara que menteixin).
#
# El que NO es dedueix sol es queda BUIT a posta i surt al report de la nit: un run sense
# etiquetes i sense `base_unit` no té cap senyal, i inventar-li una escala seria tornar a
# fer el que ja fa `base_unit` (afirmar sense saber).
from django.db import migrations

from fhort.pom.size_labels import dedueix_tipus_escala


def classifica(apps, schema_editor):
    SizeSystem = apps.get_model('pom', 'SizeSystem')

    for ss in SizeSystem.objects.all():
        if ss.tipus_escala:
            continue
        etiquetes = list(
            ss.talles.order_by('ordre', 'id').values_list('etiqueta', flat=True)
        )
        tipus, _font = dedueix_tipus_escala(etiquetes, ss.base_unit)
        if tipus:
            SizeSystem.objects.filter(pk=ss.pk).update(tipus_escala=tipus)

    # `customer_codi` (codi curt heretat) → FK `customer`. El codi es manté; la FK només hi
    # afegeix la relació. Si el schema no té taula de Customers (`public`: `tasks` és
    # tenant-only), no hi ha res a lligar i la passada se salta sencera. La comprovació és
    # per introspecció i NO per try/except: una consulta que peta avorta la transacció de la
    # migració sencera, i llavors ni el `return` la salva.
    Customer = apps.get_model('tasks', 'Customer')
    if Customer._meta.db_table not in schema_editor.connection.introspection.table_names():
        return
    per_codi = {c.codi: c.pk for c in Customer.objects.all()}

    for ss in SizeSystem.objects.filter(customer__isnull=True).exclude(customer_codi=''):
        pk = per_codi.get(ss.customer_codi)
        if pk:
            SizeSystem.objects.filter(pk=ss.pk).update(customer_id=pk)


def enrere(apps, schema_editor):
    """Reversible i buida a posta: desfer la classificació voldria dir esborrar dades que
    poden haver estat corregides a mà des d'aleshores. Els camps cauen amb la 0062."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0062_n1_run_capes'),
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(classifica, enrere),
    ]
