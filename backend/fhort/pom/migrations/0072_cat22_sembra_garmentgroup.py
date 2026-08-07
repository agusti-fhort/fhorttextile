# CAT2.2 (2026-08-07) — sembrar `GarmentGroup` allà on els `GarmentType` en citen i no hi són.
#
# La fila òrfena de `los` (`BUTTONED_TOPS` amb grup `'TOPS'`) mai va ser un problema de dades:
# era que **ningú havia creat els grups en aquell tenant**. El vocabulari existeix —el citen
# els propis `GarmentType`— però no tenia files. Amb el setup per marca s'han de crear igual.
#
# Per això la sembra no s'inventa un catàleg: **surt dels codis que els `GarmentType` del
# mateix schema ja fan servir**. Ni un grup de més ni un de menys. On el vocabulari ja està
# complet (`fhort`, `public`) això és un no-op exacte.
#
# El `nom` es pren del bessó global si el schema en té (`GarmentTypeGlobal`) i, si no, es queda
# el codi: inventar-hi una traducció seria afirmar sense saber, i el nom és presentació — la
# identitat és el codi.
from django.db import migrations


def sembra(apps, schema_editor):
    GarmentType = apps.get_model('pom', 'GarmentType')
    GarmentGroup = apps.get_model('pom', 'GarmentGroup')
    GarmentTypeGlobal = apps.get_model('pom', 'GarmentTypeGlobal')

    citats = {(c or '').strip() for c in GarmentType.objects.values_list('grup', flat=True)}
    citats.discard('')
    if not citats:
        return

    existents = set(GarmentGroup.objects.filter(codi__in=citats).values_list('codi', flat=True))
    a_crear = sorted(citats - existents)
    if not a_crear:
        return

    noms = {}
    if GarmentTypeGlobal._meta.db_table in schema_editor.connection.introspection.table_names():
        for codi in a_crear:
            g = GarmentTypeGlobal.objects.filter(grup=codi).first()
            if g is not None:
                noms[codi] = codi.replace('-', ' ').replace('_', ' ').title()

    GarmentGroup.objects.bulk_create(
        [GarmentGroup(codi=codi, nom=noms.get(codi, codi), actiu=True) for codi in a_crear],
        ignore_conflicts=True,
    )

    # ── Re-córrer el backfill de C6 amb el vocabulari ja complet ─────────────────────
    # `0068` va deixar `grup_ref` a NULL allà on el codi no existia. Ara existeix.
    per_codi = {g.codi: g.pk for g in GarmentGroup.objects.all()}
    for gt in GarmentType.objects.filter(grup_ref__isnull=True).exclude(grup=''):
        pk = per_codi.get((gt.grup or '').strip())
        if pk:
            GarmentType.objects.filter(pk=gt.pk).update(grup_ref_id=pk)

    # ── L'auditoria, dins la mateixa transacció ──────────────────────────────────────
    orfes = GarmentType.objects.filter(grup_ref__isnull=True).exclude(grup='').count()
    if orfes:
        detall = list(GarmentType.objects.filter(grup_ref__isnull=True).exclude(grup='')
                      .values_list('codi_client', 'grup')[:10])
        raise RuntimeError(
            f'CAT2.2 ATURA · queden {orfes} GarmentType amb grup i sense FK després de sembrar '
            f'el vocabulari: {detall}. El pas 2 de C6 (retirar el string) NO es pot fer.'
        )


def enrere(apps, schema_editor):
    """Buida a posta: esborrar els grups sembrats trencaria les FK que ara hi apunten."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0071_cat2_baby_months_24_36'),
    ]

    operations = [
        migrations.RunPython(sembra, enrere),
    ]
