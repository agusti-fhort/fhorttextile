"""L'ESTAT «extended» es diu «Extended», net.

DECISIÓ D'AGUS (reiterada): `extended` i `stretched` / `stretched out` **són el mateix estat**.
El nom canònic del diccionari és un de sol. El vocabulari del client (Brownie escriu «stretched
waist width») hi arriba pel seu camí —el codi oficial al `nom_fitxa` de la fila, o el
`CustomerPomAlias`—, no duplicant-lo dins del nom del diccionari.

Fins ara la fila deia `nom_en='Extended / stretched'`, i la barra sortia a la píndola i al modal
de la identitat de la fila.

QUÈ ES TOCA I QUÈ NO
  · **El `slug` NO es toca.** És el contracte: és el que desen les columnes `instancia` de les
    taules de mesura (llei G9, mai per PK) i el que `frontend/src/utils/capaInstancia.js`
    desmunta per guions. Canviar-lo seria una migració de dades de veritat, no un canvi de nom.
  · Només es reescriu el camp que **porta barra**. Un tenant que ja el tingui net —o que se
    l'hagi rebatejat a la seva manera— no es toca. Això és el que fa la migració IDEMPOTENT:
    la segona passada no troba cap barra i no escriu res.
  · `nom_ca`/`nom_es` ja diuen «Estirada» als tres schemes (`public`, `fhort`, `los`); la regla
    hi és igualment perquè el dia que en portin una, caiguin pel mateix costat.

ON CORRE: `fhort.pom` viu a SHARED **i** a TENANT alhora, o sigui que `migrate_schemas` passa
aquesta migració per `public` i per cada tenant tot sol. No cal `--schema` (i la llei del
CLAUDE.md el prohibeix).

NO ÉS REVERSIBLE cap enrere amb sentit: desfer-la voldria dir tornar a escriure un nom que
l'Agus ha decidit matar. El `reverse` és un no-op explícit perquè `migrate` cap enrere no peti,
no perquè el canvi es pugui desfer.

⚠️ La FONT del nom és `seed_measurement_instances.py`, que s'ha alineat al mateix commit. Sense
allò, la propera passada de la sembra tornaria a posar la barra i aquesta migració seria un
pedaç d'un dia.
"""
from django.db import migrations

SLUG = 'extended'
CAMPS = ('nom_en', 'nom_ca', 'nom_es')


def _primer_terme(valor: str) -> str:
    """«Extended / stretched» → «Extended». Sense barra, torna el mateix valor."""
    return valor.split('/')[0].strip()


def net(apps, schema_editor):
    Instancia = apps.get_model('pom', 'MeasurementInstance')
    for fila in Instancia.objects.filter(slug=SLUG):
        canvis = {}
        for camp in CAMPS:
            valor = getattr(fila, camp) or ''
            if '/' in valor:
                net_ = _primer_terme(valor)
                if net_ and net_ != valor:
                    canvis[camp] = net_
        if canvis:
            for camp, valor in canvis.items():
                setattr(fila, camp, valor)
            # `update_fields`: aquesta migració només té dret als noms. Res més de la fila
            # (el slug, el sufix, l'ordre, `is_system`) no hi pot caure per efecte secundari.
            fila.save(update_fields=list(canvis))


class Migration(migrations.Migration):

    dependencies = [
        ('pom', '0059_alies_instancia'),
    ]

    operations = [
        migrations.RunPython(net, migrations.RunPython.noop),
    ]
