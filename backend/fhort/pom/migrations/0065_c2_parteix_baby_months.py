# C2 (2026-08-07) — BABY_MONTHS: separar els dos jocs barrejats (D4 del cens, §7.1).
#
# `BABY_MONTHS` porta DOS jocs dins d'un: el PUNTUAL (NB·0M·1M·3M…) i un de RANGS
# (0M-1M·1M-3M…) que és una còpia exacta de `BABY_MONTHS_COM`. Els `ordre` dels dos jocs
# es trepitgen 1..5, i per tant el run es llegeix desordenat — que és el defecte que fa mal:
# un run desordenat és un grading incorrecte.
#
# Es queda el PUNTUAL. Les files de rang NO es migren enlloc: ja existeixen, idèntiques i
# amb els mesos ben posats, a `BABY_MONTHS_COM` del MATEIX schema — i això es comprova aquí
# dins abans d'esborrar res. Si la còpia no hi és, la migració no toca res i ho diu.
#
# Els `age_months_*` del joc puntual estaven desplaçats dues posicions (24M deia 96-144
# mesos). Es recalculen amb la convenció que la casa ja fa servir a `BABY_MONTHS_COM`:
# **l'etiqueta és el mes d'INICI**, i el final és l'inici de la següent talla.
# El màxim de l'ÚLTIMA talla no té següent: v. el report §C2, esperant validació.
from django.db import migrations

CODI = 'BABY_MONTHS'
CODI_RANGS = 'BABY_MONTHS_COM'


def _mes_de(etiqueta):
    """El mes d'inici que declara una etiqueta puntual. 'NB' és el naixement = 0."""
    t = (etiqueta or '').strip().upper()
    if t == 'NB':
        return 0
    digits = ''.join(c for c in t if c.isdigit())
    return int(digits) if digits else None


def parteix(apps, schema_editor):
    SizeSystem = apps.get_model('pom', 'SizeSystem')
    SizeDefinition = apps.get_model('pom', 'SizeDefinition')

    ss = SizeSystem.objects.filter(codi=CODI).first()
    if ss is None:
        return

    # ── 1 · treure el joc de RANGS, i NOMÉS si ja viu sencer a BABY_MONTHS_COM ────────
    com = SizeSystem.objects.filter(codi=CODI_RANGS).first()
    if com is not None:
        etiquetes_com = set(com.talles.values_list('etiqueta', flat=True))
        sobrants = list(ss.talles.filter(etiqueta__in=etiquetes_com)) if etiquetes_com else []
        # Cap fila amb res penjat: `SizeDefinition` té tres FK entrants i totes han de ser 0.
        # No és zel — és la diferència entre partir un joc i trencar una graduació.
        if sobrants:
            ids = [t.pk for t in sobrants]
            ItemBaseSet = apps.get_model('pom', 'ItemBaseSet')
            GradingRule = apps.get_model('pom', 'GradingRule')
            GarmentTypeItem = apps.get_model('tasks', 'GarmentTypeItem')
            penjats = (
                ItemBaseSet.objects.filter(base_size_definition_id__in=ids).count()
                + GradingRule.objects.filter(talla_base_id__in=ids).count()
            )
            taules = schema_editor.connection.introspection.table_names()
            if GarmentTypeItem._meta.db_table in taules:
                penjats += GarmentTypeItem.objects.filter(base_size_definition_id__in=ids).count()
            if penjats == 0:
                SizeDefinition.objects.filter(pk__in=ids).delete()

    # ── 2 · `ordre` únic i seqüencial sobre el que queda ──────────────────────────────
    talles = sorted(ss.talles.all(), key=lambda t: (_mes_de(t.etiqueta) if _mes_de(t.etiqueta) is not None else 0, t.pk))
    if not talles:
        return
    if [t.ordre for t in talles] != list(range(1, len(talles) + 1)):
        for i, t in enumerate(talles, start=1):
            SizeDefinition.objects.filter(pk=t.pk).update(ordre=1000 + i)
        for i, t in enumerate(talles, start=1):
            SizeDefinition.objects.filter(pk=t.pk).update(ordre=i)

    # ── 3 · `age_months_*` coherents amb les etiquetes ────────────────────────────────
    mesos = [_mes_de(t.etiqueta) for t in talles]
    if any(m is None for m in mesos):
        return
    for i, t in enumerate(talles):
        minim = mesos[i]
        seguent = next((m for m in mesos[i + 1:] if m > minim), None)
        if seguent is None:
            # L'última no té següent: es continua el pas local (l'últim tram real).
            anteriors = [m for m in mesos[:i] if m < minim]
            seguent = minim + (minim - anteriors[-1]) if anteriors else minim
        if t.age_months_min != minim or t.age_months_max != seguent:
            SizeDefinition.objects.filter(pk=t.pk).update(
                age_months_min=minim, age_months_max=seguent,
            )


def enrere(apps, schema_editor):
    """Buida a posta: tornar-hi voldria dir refabricar un joc duplicat i uns mesos que menteixen."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0064_c1_repara_toddler_eu'),
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(parteix, enrere),
    ]
