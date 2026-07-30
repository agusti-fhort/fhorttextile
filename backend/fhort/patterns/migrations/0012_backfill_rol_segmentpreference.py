"""I1/T4 — les preferències de tram passen a parlar en slugs del catàleg.

`SegmentPreference.rol` és, des de W1, «el nom de la peça normalitzat»: el que el CAD va
escriure, no un rol canònic. Al material real això dona 'BACK' i 'TATE_BACK' com si fossin
dues coses diferents, i el que s'aprèn d'una esquena no viatja cap a l'altra. Amb el
catàleg d'I1 ja hi ha un vocabulari on dir-ho una sola vegada.

TRES REGLES, EN AQUEST ORDRE:
  1. normalitzar (retallar espais, majúscules);
  2. treure el prefix del model quan el coneixem (`TATE_`);
  3. buscar al diccionari LITERAL de sota.

**El que no es pot mapar es queda com està i es diu.** Inventar un slug per a un nom que
no reconeixem seria pitjor que deixar-lo: una preferència mal etiquetada viatja cap a una
peça que no li toca i el taller aprèn una cosa falsa.

**Reverse = noop**, com la sembra de tasques (`tasks.0025`): revertir un esquema no ha de
desfer dades. El valor antic no es podria reconstruir de totes maneres —el mapatge és de
molts a un— i pretendre el contrari seria una marxa enrere que menteix.
"""
from django.db import migrations

#: Prefixos de model que se sap que el CAD anteposa al nom de la peça. Només el TATE, que
#: és l'únic verificat contra un PatternFile real; afegir-ne d'especulatius faria que un
#: nom legítim que hi comencés perdés mitja identitat.
PREFIXOS = ('TATE_',)

#: Nom normalitzat i SENSE prefix → slug del catàleg (`pom.PatternPieceRole`).
MAPA = {
    'BACK': 'back',
    'FRONT': 'front',
    'SLEEVE': 'sleeve',
    'MID SLEEVE': 'sleeve',
    'FRONT_YOKE': 'yoke',
    # La vista del canesú és una VISTA: el seu rol és el que fa, no on va. Queda al costat
    # de FRONT_FACING, i està bé que hi quedi — el rol diu QUÈ és una peça; QUINA és ho
    # diran l'ordinal i el nom, que són camps de la peça i no del catàleg.
    'FACING_YOKE': 'facing',
    'FRONT_FACING': 'facing',
    'NECK_BAND': 'neckband',
    # L'entretela de la tira de coll és una entretela.
    'NECK_BAND_INTERLINING': 'interlining',
}


def slug_del_rol(valor: str) -> str:
    """Nom de peça → slug del catàleg, o `''` si no el sabem mapar."""
    nom = (valor or '').strip().upper()
    for prefix in PREFIXOS:
        if nom.startswith(prefix):
            nom = nom[len(prefix):]
            break
    return MAPA.get(nom, '')


def backfill(apps, schema_editor):
    SegmentPreference = apps.get_model('patterns', 'SegmentPreference')
    schema = schema_editor.connection.schema_name

    canviats = colisions = intactes = 0
    no_mapejats: dict[str, int] = {}

    for pref in SegmentPreference.objects.all().order_by('id'):
        slug = slug_del_rol(pref.rol)
        if not slug:
            no_mapejats[pref.rol] = no_mapejats.get(pref.rol, 0) + 1
            continue
        if pref.rol == slug:
            intactes += 1
            continue

        # La clau és (rol, accio, t_inici, t_fi): en unificar dos noms cap al mateix slug,
        # dues files poden xocar. Guanya la MÉS RECENT —és el judici humà més nou sobre el
        # mateix tram— i la vella se'n va, dita en veu alta.
        germana = (
            SegmentPreference.objects
            .filter(rol=slug, accio=pref.accio, t_inici=pref.t_inici, t_fi=pref.t_fi)
            .exclude(pk=pref.pk)
            .order_by('-actualitzat_at')
            .first()
        )
        if germana is not None:
            vella, nova = sorted(
                (pref, germana), key=lambda p: (p.actualitzat_at, p.pk))
            print(f'    [{schema}] COL·LISIÓ a «{slug}» {pref.accio} '
                  f'[{pref.t_inici:.6f}–{pref.t_fi:.6f}]: es conserva id={nova.pk} '
                  f'(rol {nova.rol!r}, {nova.actualitzat_at:%Y-%m-%d %H:%M}) i s\'esborra '
                  f'id={vella.pk} (rol {vella.rol!r}, '
                  f'{vella.actualitzat_at:%Y-%m-%d %H:%M})')
            colisions += 1
            if vella.pk == pref.pk:
                pref.delete()
                continue
            vella.delete()

        pref.rol = slug
        pref.save(update_fields=['rol'])
        canviats += 1

    total = SegmentPreference.objects.count()
    if total or canviats:
        print(f'    [{schema}] SegmentPreference: {canviats} reetiquetades · '
              f'{intactes} ja eren slug · {colisions} col·lisions · {total} files ara')
    for nom, n in sorted(no_mapejats.items()):
        print(f'    [{schema}] NO MAPEJAT (es deixa com està): {nom!r} × {n}')


def enrere(apps, schema_editor):
    """Noop deliberat: v. docstring del mòdul."""


class Migration(migrations.Migration):

    dependencies = [
        ('patterns', '0011_patternpiece_estat_peca_patternpiece_lateralitat_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, enrere),
    ]
