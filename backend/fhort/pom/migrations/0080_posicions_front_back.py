"""Les dues CARES de la posició: `front` (F) i `back` (B).

DECISIÓ D'AGUS (22-23/08): la POSICIÓ té DOS EIXOS —lateral (`left`/`right`) i CARA
(`front`/`back`)—. Dins d'un eix són excloents; entre eixos es combinen: `left`+`back`
existeix, `left`+`right` i `front`+`back` no.

Fins avui el diccionari només tenia la lateralitat, i «el davanter» i «l'esquena» no es podien
dir: qui volia partir una mesura per cares havia de batejar-la a mà i el sistema no en sabia
res. Aquestes dues files són el vocabulari que faltava.

IDEMPOTENT PER SLUG (`get_or_create`), com tota sembra de la casa: una segona passada no
duplica res, i una fila que un tenant ja s'hagi creat amb aquest slug **no es toca** (ni el seu
nom ni el seu `is_system`).

GUARDA (llei S44 · el sufix ha de ser ÚNIC dins de l'eix): abans de crear-les es mesura que cap
altra posició no ocupi ja `F` o `B`. Si `pom/0079` no hagués passat, `bottom` encara seria `B`
i aquesta migració ATURA en comptes de deixar dos sufixos iguals a l'eix —que és exactament el
dany que el rebateig de `bottom` ve a evitar.

ON CORRE: `fhort.pom` viu a SHARED **i** a TENANT alhora → `migrate_schemas` la passa per
`public` i per cada tenant. Mai `--schema`.

REVERSIBLE: esborra les dues files NOMÉS si són les que aquesta migració va crear
(`is_system=True`, `origen='SEED'`).

⚠️ La FONT és `seed_measurement_instances.py`, alineada al mateix commit.
"""
from django.db import migrations

EIX = 'POSICIO'
#: (slug, sufix, nom_en, nom_ca, nom_es, display_order). Els noms d'instància NO es tradueixen
#: (van en anglès canònic: allarguen el nom del POM i en componen el sufix) — els tres camps hi
#: són perquè el model els té, amb el mateix valor, com ja fan `cf` i `cb`.
CARES = [
    ('front', 'F', 'Front', 'Front', 'Front', 9),
    ('back',  'B', 'Back',  'Back',  'Back',  10),
]
SLUGS = [c[0] for c in CARES]
SUFIXOS = {c[1] for c in CARES}


def endavant(apps, schema_editor):
    Instancia = apps.get_model('pom', 'MeasurementInstance')

    ocupats = Instancia.objects.filter(eix=EIX, sufix__in=SUFIXOS).exclude(slug__in=SLUGS)
    if ocupats.exists():
        detall = ', '.join(f'{r.slug}={r.sufix!r}' for r in ocupats)
        raise RuntimeError(
            f'0080: el sufix de les cares ja és ocupat per una altra posició ({detall}). '
            f"Dos sufixos iguals a l'eix {EIX} farien que el codi proposat no digués de quina "
            f'cara parla. Passa `pom/0079` (bottom → BM) abans que aquesta.')

    for slug, sufix, en, ca, es, ordre in CARES:
        Instancia.objects.get_or_create(
            slug=slug,
            defaults={
                'nom_en': en, 'nom_ca': ca, 'nom_es': es,
                'eix': EIX, 'sufix': sufix,
                'is_system': True, 'pendent_revisio': False,
                'origen': 'SEED', 'display_order': ordre,
            },
        )


def enrere(apps, schema_editor):
    Instancia = apps.get_model('pom', 'MeasurementInstance')
    # Només les NOSTRES: una fila que un tenant hagi fet seva (`is_system=False`) es queda.
    Instancia.objects.filter(slug__in=SLUGS, is_system=True, origen='SEED').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0079_bottom_sufix_bm'),
    ]

    operations = [
        migrations.RunPython(endavant, enrere),
    ]
