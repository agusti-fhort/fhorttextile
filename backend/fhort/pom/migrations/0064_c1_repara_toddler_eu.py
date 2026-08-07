# C1 (2026-08-07) — reparació de TODDLER_EU (D3 del cens, REPORT_NIT_CAPES §7.1).
#
# Tres defectes alhora en un run del catàleg `public`, i per tant present a més d'un schema.
# La reparació és **dirigida per les DADES, no pel schema**: cada defecte es detecta abans de
# tocar-lo i només s'escriu on hi és. Això no és zel: a `public` la sèrie de contorns és
# coherent (26·28·30·32·34) i a `fhort` no (53·54·55·56·57 i després un 34), o sigui que una
# escriptura cega dels valors de `fhort` CORROMPRIA `public`. Idempotent per construcció: un
# segon pas no troba res a reparar.
#
# El detall dels valors triats —i el que s'ha deixat expressament sense tocar— viu a
# `docs/diagnosis/REPORT_CATALEG_TALLES.md` §C1, perquè els validin l'Agus i la Montse.
from django.db import migrations

from fhort.pom.size_labels import conflicte_tipus_escala, dedueix_tipus_escala

CODI = 'TODDLER_EU'

#: L'invers de `size_labels.BASE_UNIT_A_TIPUS` per als tipus que tenen UNA sola base_unit.
#: 'MESOS' no hi és a posta: li corresponen dues (`MONTHS` i `AGE_YEARS`) i triar-ne una
#: seria inventar-se domini.
TIPUS_A_BASE_UNIT = {'ALPHA': 'ALPHA', 'NUM': 'NUMERIC_EU', 'ALTURA': 'CM_HEIGHT'}

#: Les dues columnes que el brief autoritza a recalcular a la talla de fora de sèrie.
#: `body_bust_cm` NO hi és: v. el report (també està fora de sèrie, i és decisió d'Agus).
COLUMNES = ('body_waist_cm', 'body_hip_cm')


def _clau_ordre(t):
    """Alçada de referència, i si no n'hi ha, el número de l'etiqueta."""
    if t.body_height_cm is not None:
        return float(t.body_height_cm)
    digits = ''.join(c for c in t.etiqueta if c.isdigit())
    return float(digits) if digits else 0.0


def repara(apps, schema_editor):
    SizeSystem = apps.get_model('pom', 'SizeSystem')
    SizeDefinition = apps.get_model('pom', 'SizeDefinition')

    ss = SizeSystem.objects.filter(codi=CODI).first()
    if ss is None:
        return

    talles = sorted(ss.talles.all(), key=_clau_ordre)
    etiquetes = [t.etiqueta for t in talles]

    # ── 1 · base_unit coherent amb les etiquetes ──────────────────────────────────────
    # L'etiqueta MANA sobre `base_unit` (llei de N1). Aquí es paga el deute §7.4.3 en dades:
    # el camp deia AGE_YEARS i les etiquetes són alçades en cm.
    if etiquetes and conflicte_tipus_escala(etiquetes, ss.base_unit):
        tipus, _font = dedueix_tipus_escala(etiquetes, '')
        nova = TIPUS_A_BASE_UNIT.get(tipus)
        if nova:
            SizeSystem.objects.filter(pk=ss.pk).update(base_unit=nova, tipus_escala=tipus)

    if not talles:
        return

    # ── 2 · `ordre` desdoblat → seqüència 1..n neta, per alçada ───────────────────────
    # En DUES passades amb un offset alt: la unicitat d'(ordre, size_system) que C4 posa
    # just després faria petar una renumeració in-place, i aquesta migració ha de seguir
    # sent re-executable DESPRÉS d'aquella constraint.
    if [t.ordre for t in talles] != list(range(1, len(talles) + 1)):
        offset = 1000
        for i, t in enumerate(talles, start=1):
            SizeDefinition.objects.filter(pk=t.pk).update(ordre=offset + i)
        for i, t in enumerate(talles, start=1):
            SizeDefinition.objects.filter(pk=t.pk).update(ordre=i)

    # ── 3 · l'última talla que se surt de la sèrie ────────────────────────────────────
    # No hi ha veïna PER SOBRE (116 és l'última), o sigui que això és una EXTRAPOLACIÓ, no
    # una interpolació: es continua el pas local (l'últim tram) de cada columna. El guard és
    # la monotonia — a `public` la sèrie puja i no s'hi toca res.
    if len(talles) < 3:
        return
    ultima, previa, anterior = talles[-1], talles[-2], talles[-3]
    canvis = {}
    for col in COLUMNES:
        val, ant, ant2 = (getattr(ultima, col), getattr(previa, col), getattr(anterior, col))
        if val is None or ant is None or ant2 is None:
            continue
        if val >= ant:                      # la sèrie puja: aquí no hi ha res trencat
            continue
        canvis[col] = ant + (ant - ant2)    # pas local de l'últim tram
    if canvis:
        SizeDefinition.objects.filter(pk=ultima.pk).update(**canvis)


def enrere(apps, schema_editor):
    """Buida a posta: desfer-ho tornaria a escriure un `base_unit` que menteix, un `ordre`
    duplicat i un contorn impossible. La reparació és el terra, no un pas reversible."""


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0063_n1_classifica_tipus_escala'),
    ]

    operations = [
        migrations.RunPython(repara, enrere),
    ]
