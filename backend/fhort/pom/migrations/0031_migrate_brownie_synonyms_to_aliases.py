"""N2-4a — Migra el bloc "Brownie positional POMs" (abans hardcodejat a _POM_SYNONYMS) a
CustomerPOMAlias del customer BRW (origen=MIGRACIO).

DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08: era nomenclatura de CLIENT disfressada de sinònim
canònic. Aquí es materialitza com a àlies. El diccionari de sinònims perd el bloc a la mateixa
peça (codi). (Nota històrica: quan es va escriure aquesta migració el matcher encara no
llegia els àlies; des de N3 sí que ho fa — estratègia (a) de find_pom_master.)

Resolució del POM: per la descripció OBJECTIU del sinònim (nom_client / pom_global.nom_en,
icontains, id més baix). Les entrades que no resolen a cap POM NO es migren i es reporten.
Guardada del schema public (Customer/POMMaster reals viuen als tenants).
"""
from django.db import migrations
from django.db.models import Q

# {descripció Brownie (origen) : descripció canònica objectiu} — bloc mogut de _POM_SYNONYMS.
BROWNIE_ALIASES = {
    'waist position':                  'waist position distance',
    'hip position':                    'hip position distance',
    'straight back body length':       'body length back',
    'front armhole curve':             'armhole',
    'collar width':                    'neck tie length',
    'body zip length':                 'zip',
    'lining length at center front':   'lining',
    'lining length at center back':    'lining',
    'lining bottom width along hem':   'lining bottom',
}


def forwards(apps, schema_editor):
    conn = schema_editor.connection
    if conn.schema_name == 'public':
        return
    Customer = apps.get_model('tasks', 'Customer')
    POMMaster = apps.get_model('pom', 'POMMaster')
    CustomerPOMAlias = apps.get_model('pom', 'CustomerPOMAlias')
    brw = Customer.objects.filter(codi='BRW').first()
    if brw is None:
        print(f"[N2-4a @ {conn.schema_name}] cap customer BRW; res a migrar")
        return
    created = exists = 0
    unresolved = []
    for src, tgt in BROWNIE_ALIASES.items():
        pom = (POMMaster.objects
               .filter(Q(nom_client__icontains=tgt) | Q(pom_global__nom_en__icontains=tgt), actiu=True)
               .order_by('id').first())
        if pom is None:
            unresolved.append((src, tgt))
            continue
        if CustomerPOMAlias.objects.filter(customer_id=brw.id, client_code=src).exists():
            exists += 1
            continue
        CustomerPOMAlias.objects.create(
            customer_id=brw.id, pom_id=pom.id,
            client_code=src, client_description=src,
            origen='MIGRACIO', pendent_revisio=False)
        created += 1
    print(f"[N2-4a @ {conn.schema_name}] BRW aliases creats={created} ja_existents={exists} "
          f"NO_RESOLTS={unresolved}")


def reverse(apps, schema_editor):
    conn = schema_editor.connection
    if conn.schema_name == 'public':
        return
    Customer = apps.get_model('tasks', 'Customer')
    CustomerPOMAlias = apps.get_model('pom', 'CustomerPOMAlias')
    brw = Customer.objects.filter(codi='BRW').first()
    if brw is not None:
        CustomerPOMAlias.objects.filter(
            customer_id=brw.id, origen='MIGRACIO',
            client_code__in=list(BROWNIE_ALIASES)).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('pom', '0030_backfill_gradingruleset_customer'),
    ]
    operations = [
        migrations.RunPython(forwards, reverse),
    ]
