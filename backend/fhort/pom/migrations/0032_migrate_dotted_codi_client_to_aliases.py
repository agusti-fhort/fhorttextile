"""N2-4b — Migra els codis LLETRA.NÚMERO de POMMaster.codi_client a CustomerPOMAlias, atribuint
el customer per origen_import.

DIAGNOSI_NOMENCLATURA_ALIES_2026-07-08. `codi_client` NO es toca (display-legacy). Atribució:
  - origen_import = UUID → ImportSession(token) → model → customer
  - origen_import = "<nom> (<codi_intern>)" → Model(codi_intern) → customer
Els que no resolen a un customer NO es migren i es reporten (decisió humana). Guardada de public.
"""
import re
from django.db import migrations

DOTTED = re.compile(r'^[A-Za-z]+\.[0-9]')
UUID_RE = re.compile(r'^[0-9a-fA-F-]{36}$')
PARENS = re.compile(r'\(([^)]+)\)\s*$')


def _resolve_customer(origen, ImportSession, Model):
    origen = (origen or '').strip()
    if not origen:
        return None, 'sense_origen_import'
    if UUID_RE.match(origen):
        s = ImportSession.objects.filter(token=origen).first()
        if s is None:
            return None, 'sessio_no_trobada'
        if not s.model_id or not s.model.customer_id:
            return None, 'sessio_sense_model_o_customer'
        return s.model.customer, 'sessio->model->customer'
    m = PARENS.search(origen)
    if m:
        mod = Model.objects.filter(codi_intern=m.group(1)).first()
        if mod is None or not mod.customer_id:
            return None, 'model_no_trobat'
        return mod.customer, 'model(codi_intern)->customer'
    return None, 'format_desconegut'


def forwards(apps, schema_editor):
    conn = schema_editor.connection
    if conn.schema_name == 'public':
        return
    POMMaster = apps.get_model('pom', 'POMMaster')
    CustomerPOMAlias = apps.get_model('pom', 'CustomerPOMAlias')
    ImportSession = apps.get_model('models_app', 'ImportSession')
    Model = apps.get_model('models_app', 'Model')
    created = exists = 0
    not_migrated = []
    for pom in POMMaster.objects.filter(actiu=True):
        codi = (pom.codi_client or '').strip()
        if not DOTTED.match(codi):
            continue
        cust, via = _resolve_customer(pom.origen_import, ImportSession, Model)
        if cust is None:
            not_migrated.append((codi, via))
            continue
        if CustomerPOMAlias.objects.filter(customer_id=cust.id, client_code=codi).exists():
            exists += 1
            continue
        CustomerPOMAlias.objects.create(
            customer_id=cust.id, pom_id=pom.id,
            client_code=codi, client_description=(pom.nom_client or ''),
            origen='MIGRACIO', pendent_revisio=False)
        created += 1
    print(f"[N2-4b @ {conn.schema_name}] dotted->alias creats={created} ja_existents={exists} "
          f"NO_MIGRATS={len(not_migrated)}: {sorted(not_migrated)}")


def reverse(apps, schema_editor):
    conn = schema_editor.connection
    if conn.schema_name == 'public':
        return
    CustomerPOMAlias = apps.get_model('pom', 'CustomerPOMAlias')
    # Només els àlies dotted d'aquesta migració (els Brownie NO són LLETRA.NÚMERO).
    for a in CustomerPOMAlias.objects.filter(origen='MIGRACIO'):
        if DOTTED.match(a.client_code or ''):
            a.delete()


class Migration(migrations.Migration):
    dependencies = [
        ('pom', '0031_migrate_brownie_synonyms_to_aliases'),
    ]
    operations = [
        migrations.RunPython(forwards, reverse),
    ]
