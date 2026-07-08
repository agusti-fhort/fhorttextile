"""Correcció d'auditoria de CustomerPOMAlias (AUDITORIA_CUSTOMERPOMALIAS_COMPLETA_2026-07-08).

ARREL DE L'ERROR: la sembra de 0031 resolia el POM per la descripció OBJECTIU generica del
sinònim amb `icontains(target)` + `order_by('id').first()` (0031:44-46). Amb targets genèrics
('lining', 'armhole', …) això agafa el POM de MENOR id que conté el substring, no el correcte:
'lining length at center front' → target 'lining' → va resoldre a pom 383 ("Lining Length at
Center BACK", id més baix) en lloc de 429 ("Lining Length at Center Front", LF-M76).

⚠️ LLEI: cap re-sembra futura ha de resoldre POMs per substring. Match EXACTE o per `code`.

Aquesta migració de dades (idempotent, per-tenant; res al schema public):
  A1 — corregeix l'àlies BRW 'lining length at center front' → pom 429, NOMÉS si ara apunta
       a 383 (respecta correccions humanes prèvies: si ja és 429 o un altre valor, NO toca).
  A2 — esborra l'àlies BRW 'front armhole curve' (decisió Agus: un àlies erroni ACTIU és
       pitjor que cap; sense àlies el matcher demana resolució manual i el llaç de P2 el
       re-sembra bé). Idempotent: si no existeix, no fa res.

Reverse: NO-OP deliberat — no es re-crea l'error (ni el 383 d'A1 ni l'àlies d'A2).
"""
from django.db import migrations

A1_CLIENT_CODE = 'lining length at center front'
A1_WRONG_POM = 383      # "Lining Length at Center Back" (resolució errònia de 0031)
A1_RIGHT_POM = 429      # "Lining Length at Center Front" (LF-M76)
A2_CLIENT_CODE = 'front armhole curve'


def forwards(apps, schema_editor):
    conn = schema_editor.connection
    if conn.schema_name == 'public':
        return
    Customer = apps.get_model('tasks', 'Customer')
    POMMaster = apps.get_model('pom', 'POMMaster')
    CustomerPOMAlias = apps.get_model('pom', 'CustomerPOMAlias')

    brw = Customer.objects.filter(codi='BRW').first()
    if brw is None:
        print(f"[audit-alias @ {conn.schema_name}] cap customer BRW; res a corregir")
        return

    # A1 — correcció determinista, només si encara apunta al POM erroni (383).
    if not POMMaster.objects.filter(id=A1_RIGHT_POM).exists():
        print(f"[audit-alias @ {conn.schema_name}] POM {A1_RIGHT_POM} no existeix; A1 OMESA")
    else:
        n = (CustomerPOMAlias.objects
             .filter(customer_id=brw.id, client_code=A1_CLIENT_CODE, pom_id=A1_WRONG_POM)
             .update(pom_id=A1_RIGHT_POM))
        print(f"[audit-alias @ {conn.schema_name}] A1 corregits (383→429): {n}")

    # A2 — retirada de l'àlies erroni (idempotent).
    d, _ = (CustomerPOMAlias.objects
            .filter(customer_id=brw.id, client_code=A2_CLIENT_CODE).delete())
    print(f"[audit-alias @ {conn.schema_name}] A2 esborrats ('{A2_CLIENT_CODE}'): {d}")


def reverse(apps, schema_editor):
    # NO-OP: no es re-sembra l'error (ni A1→383 ni A2). Documentat a propòsit.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('pom', '0033_sizingprofile_customer'),
    ]
    operations = [
        migrations.RunPython(forwards, reverse),
    ]
